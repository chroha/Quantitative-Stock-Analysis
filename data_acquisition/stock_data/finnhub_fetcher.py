"""
Finnhub Data Fetcher (Forecasts & Sentiment)
"""
import requests
import time
from typing import Optional, Dict, Any, List
from .base_fetcher import BaseFetcher
from utils.logger import setup_logger
from config.settings import settings
from utils.http_utils import make_request
from utils.unified_schema import (
    ForecastData, AnalystTargets, CompanyProfile, 
    FieldWithSource, TextFieldWithSource,
    NewsItem, InsiderSentiment, InsiderTransaction, SentimentData
)

logger = setup_logger('finnhub_fetcher')

class FinnhubFetcher(BaseFetcher):
    """
    Fetches forecast data from Finnhub API.
    """
    def __init__(self, symbol: str):
        super().__init__(symbol, 'finnhub')
        self.api_key = settings.FINNHUB_API_KEY
        self.base_url = "https://finnhub.io/api/v1"
        self._circuit_broken = False

    def fetch_income_statements(self) -> list:
        """Not implemented for Finnhub (Forecast/Profile only)."""
        return []

    def fetch_balance_sheets(self) -> list:
        """Not implemented for Finnhub (Forecast/Profile only)."""
        return []

    def fetch_cash_flow_statements(self) -> list:
        """Not implemented for Finnhub (Forecast/Profile only)."""
        return []

    def fetch_forecast_data(self) -> Optional[ForecastData]:
        """
        Fetch forecast data (Surprises, Price Targets, Estimates, Metrics).
        Aggregated into ForecastData object.
        """
        if self._circuit_broken:
             logger.warning("Finnhub circuit broken, skipping forecast data.")
             return None

        forecast = ForecastData()
        has_data = False
        
        # 1. Price Targets
        targets = self.fetch_price_targets()
        if targets:
            forecast.std_price_target_low = targets.std_price_target_low
            forecast.std_price_target_high = targets.std_price_target_high
            forecast.std_price_target_avg = targets.std_price_target_avg
            forecast.std_price_target_consensus = targets.std_price_target_consensus
            forecast.std_number_of_analysts = targets.std_number_of_analysts
            has_data = True
        elif self._circuit_broken:
            return None # Stop if PT fetch broke the circuit
            
        # 2. Earnings Surprises
        surprises = self._fetch_earnings_surprises()
        if surprises:
            forecast.std_earnings_surprise_history = surprises
            has_data = True
        elif self._circuit_broken:
            return None
        
        # 3. EPS & Revenue Estimates
        estimates = self._fetch_eps_estimates()
        if estimates:
            # Current Year
            if estimates.get('epsAvg'):
                forecast.std_eps_estimate_current_year = FieldWithSource(
                    value=float(estimates['epsAvg'][0]['estimate']), 
                    source='finnhub'
                ) if estimates['epsAvg'] else None
            
            # Next Year (if available in array)
            if estimates.get('epsAvg') and len(estimates['epsAvg']) > 1:
                forecast.std_eps_estimate_next_year = FieldWithSource(
                    value=float(estimates['epsAvg'][1]['estimate']), 
                    source='finnhub'
                )
            
            # Revenue Estimates
            if estimates.get('revenueAvg'):
                forecast.std_revenue_estimate_current_year = FieldWithSource(
                    value=float(estimates['revenueAvg'][0]['estimate']), 
                    source='finnhub'
                ) if estimates['revenueAvg'] else None
                
                if len(estimates['revenueAvg']) > 1:
                    forecast.std_revenue_estimate_next_year = FieldWithSource(
                        value=float(estimates['revenueAvg'][1]['estimate']), 
                        source='finnhub'
                    )
            has_data = True
        elif self._circuit_broken:
            return None
            
        # 4. Forward Metrics (P/E, EPS)
        metrics = self._fetch_metrics()
        if metrics:
            # Forward P/E
            if metrics.get('metric', {}).get('forwardPeRatio'):
                forecast.std_forward_pe = FieldWithSource(
                    value=float(metrics['metric']['forwardPeRatio']), 
                    source='finnhub'
                )
            
            # Forward EPS (derived from current price / forward P/E if not directly available)
            # Note: Finnhub doesn't directly provide forward EPS in /stock/metric
            # It's usually calculated as: price / forwardPE
            # We'll leave this for Yahoo/FMP which have it directly
            has_data = True
        
        return forecast if has_data else None

    def fetch_quote(self) -> Optional['PriceData']:
        """
        Fetch real-time quote data.
        Returns PriceData object for the current/latest trading session.
        """
        if self._circuit_broken: return None
        # /quote?symbol=AAPL
        data = self._make_request('quote')
        if not data: return None
        
        try:
            from utils.unified_schema import PriceData
            from datetime import datetime
            
            # Finnhub Quote: c (Current), h, l, o, pc (Prev Close), t (timestamp)
            timestamp = data.get('t')
            if not timestamp: return None
            
            date = datetime.fromtimestamp(timestamp)
            
            return PriceData(
                std_date=date,
                std_open=FieldWithSource(value=float(data['o']), source='finnhub') if data.get('o') else None,
                std_high=FieldWithSource(value=float(data['h']), source='finnhub') if data.get('h') else None,
                std_low=FieldWithSource(value=float(data['l']), source='finnhub') if data.get('l') else None,
                std_close=FieldWithSource(value=float(data['c']), source='finnhub') if data.get('c') else None,
                std_adjusted_close=FieldWithSource(value=float(data['c']), source='finnhub') if data.get('c') else None, # Realtime is usually adj?
                std_volume=None # Quote endpoint doesn't usually have volume? Wait, docs say 'v' might be there? 
                # User sample response for trade showed 'v'. Quote endpoint response usually has: c, d, dp, h, l, o, pc, t.
                # Let's check debug output. Debug output showed: {'c': 255.78, 'd': -5.95, 'dp': -2.27, 'h': 262.23, 'l': 255.45, 'o': 262.01, 'pc': 261.73, 't': 1771016400}
                # No 'v' in quote.
            )
        except Exception as e:
            logger.warning(f"Failed to parse Finnhub quote: {e}")
            return None

    def fetch_profile(self) -> Optional[CompanyProfile]:
        """
        Fetch company profile.
        Combines data from `stock/profile2` (Basic Info) and `stock/metric` (Financial Ratios).
        """
        if self._circuit_broken: return None
        
        # 1. Basic Profile (stock/profile2)
        profile_data = self._make_request('stock/profile2')
        if not profile_data: 
            # If profile2 fails, we might still want metrics? usually not.
            return None
        
        # 2. Financial Metrics (stock/metric) - "Basic Financials"
        # Only fetch if profile succeeded to avoid wasting calls on bad symbols
        metrics_data = self._fetch_metrics()
        
        try:
            profile = CompanyProfile(
                std_symbol=profile_data.get('ticker'),
                std_company_name=TextFieldWithSource(value=profile_data.get('name'), source='finnhub'),
                std_industry=TextFieldWithSource(value=profile_data.get('finnhubIndustry'), source='finnhub'),
                std_sector=TextFieldWithSource(value=profile_data.get('finnhubIndustry'), source='finnhub'), 
                std_market_cap=FieldWithSource(value=float(profile_data.get('marketCapitalization', 0)), source='finnhub') if profile_data.get('marketCapitalization') else None,
                std_logo_url=TextFieldWithSource(value=profile_data.get('logo'), source='finnhub')
            )
            
            # Enrich with Metrics if available
            if metrics_data and 'metric' in metrics_data:
                m = metrics_data['metric']
                
                # Beta
                if m.get('beta'):
                    profile.std_beta = FieldWithSource(value=float(m['beta']), source='finnhub')
                
                # 52 Week Change
                if m.get('52WeekPriceReturnDaily'):
                     profile.std_52_week_change = FieldWithSource(value=float(m['52WeekPriceReturnDaily'])/100.0, source='finnhub') # Finnhub is %, we store decimal? CHECK SCHEMA. 
                     # UnifiedSchema: "52 Week Price Change (%)". Usually means value like 15.5 for 15.5%.
                     # wait, schema says "Percentage of shares" e.g. 0.80% -> 0.008? 
                     # Let's check schema for "std_52_week_change". 
                     # "52 Week Price Change (%)" usually implies 15.0 for 15%. 
                     # But Growth rates are "decimal". 
                     # Let's assume % value for now or check Yahoo mapper. 
                     # Yahoo "52WeekChange" is usually raw decimal (0.15).
                     # Finnhub "52WeekPriceReturnDaily": 101.96 (doubled). So it's percentage. 
                     # We should convert to decimal (1.0196) to match Yahoo's likely decimal format? 
                     # Let's look at output example: "4.63%" -> 0.0463.
                     # So if Finnhub sends 101, it is 101%. /100.
                     
                # S&P 52 Week Change (Bench) - Finnhub doesn't give S&P change relative to stock easily here?
                
                # Valuation / Ratios
                if m.get('peAnnual'): # Trailing PE
                    profile.std_pe_ratio = FieldWithSource(value=float(m['peAnnual']), source='finnhub')
                if m.get('pbAnnual'): 
                    profile.std_pb_ratio = FieldWithSource(value=float(m['pbAnnual']), source='finnhub')
                if m.get('psAnnual'):
                    profile.std_ps_ratio = FieldWithSource(value=float(m['psAnnual']), source='finnhub')
                
                if m.get('dividendYieldIndicatedAnnual'):
                    profile.std_dividend_yield = FieldWithSource(value=float(m['dividendYieldIndicatedAnnual'])/100.0, source='finnhub')
                
                if m.get('currentRatio'):
                    profile.std_current_ratio = FieldWithSource(value=float(m['currentRatio']), source='finnhub')
                if m.get('quickRatio'):
                     profile.std_quick_ratio = FieldWithSource(value=float(m['quickRatio']), source='finnhub')
                
                # Book Value
                if m.get('bookValuePerShareAnnual'):
                    profile.std_book_value_per_share = FieldWithSource(value=float(m['bookValuePerShareAnnual']), source='finnhub')
                
                # Revenue Per Share
                if m.get('revenuePerShareAnnual'):
                     profile.std_revenue_per_share = FieldWithSource(value=float(m['revenuePerShareAnnual']), source='finnhub')

            return profile
            
        except Exception as e:
            logger.warning(f"Failed to parse Finnhub profile: {e}")
            return None

    def fetch_price_targets(self) -> Optional[AnalystTargets]:
        """Fetch price targets."""
        if self._circuit_broken: return None
        data = self._make_request('stock/price-target')
        if not data: return None
        
        try:
            return AnalystTargets(
                std_price_target_low=FieldWithSource(value=float(data.get('targetLow', 0)), source='finnhub') if data.get('targetLow') else None,
                std_price_target_high=FieldWithSource(value=float(data.get('targetHigh', 0)), source='finnhub') if data.get('targetHigh') else None,
                std_price_target_avg=FieldWithSource(value=float(data.get('targetMean', 0)), source='finnhub') if data.get('targetMean') else None,
                std_price_target_consensus=FieldWithSource(value=float(data.get('targetMedian', 0)), source='finnhub') if data.get('targetMedian') else None,
            )
        except Exception as e:
            logger.warning(f"Failed to parse Finnhub price targets: {e}")
            return None

    def fetch_company_news(self, start_date: str, end_date: str) -> List[NewsItem]:
        """
        Fetch company news.
        :param start_date: YYYY-MM-DD
        :param end_date: YYYY-MM-DD
        """
        if self._circuit_broken: return []
        params = {'from': start_date, 'to': end_date}
        data = self._make_request('company-news', params)
        if not data or not isinstance(data, list): return []
        
        news_items = []
        for item in data:
            try:
                news_items.append(NewsItem(
                    id=str(item.get('id')),
                    category=item.get('category', 'company'),
                    datetime=item.get('datetime', 0),
                    headline=item.get('headline', ''),
                    source=item.get('source', ''),
                    url=item.get('url', ''),
                    summary=item.get('summary', ''),
                    image=item.get('image', ''),
                    related=item.get('related', '')
                ))
            except Exception as e:
                logger.warning(f"Failed to parse news item: {e}")
                continue
        return news_items

    def fetch_market_news(self, category: str = 'general') -> List[NewsItem]:
        """
        Fetch market news.
        :param category: general, forex, crypto, merger
        """
        if self._circuit_broken: return []
        params = {'category': category}
        data = self._make_request('news', params)
        if not data or not isinstance(data, list): return []

        news_items = []
        for item in data:
            try:
                news_items.append(NewsItem(
                    id=str(item.get('id')),
                    category=item.get('category', category),
                    datetime=item.get('datetime', 0),
                    headline=item.get('headline', ''),
                    source=item.get('source', ''),
                    url=item.get('url', ''),
                    summary=item.get('summary', ''),
                    image=item.get('image', ''),
                    related=item.get('related', '')
                ))
            except Exception:
                continue
        return news_items

    def fetch_peers(self) -> List[str]:
        """Fetch company peers."""
        if self._circuit_broken: return []
        data = self._make_request('stock/peers')
        if not data or not isinstance(data, list): return []
        # Filter out the symbol itself if present
        return [p for p in data if p != self.symbol]

    def fetch_sentiment(self) -> Optional[SentimentData]:
        """Fetch insider sentiment and transactions."""
        if self._circuit_broken: return None
        
        sentiment_data = SentimentData()
        
        # 1. Insider Sentiment (stock/insider-sentiment)
        # Parameters: symbol, from (optional), to (optional). 
        # Finnhub sentiment data is usually monthly.
        # Let's fetch last 6 months implicit (default) or specify simple range?
        # Docs: /stock/insider-sentiment?symbol=AAPL&from=2021-01-01
        import datetime
        start_date = (datetime.date.today() - datetime.timedelta(days=180)).strftime('%Y-%m-%d')
        
        sent_resp = self._make_request('stock/insider-sentiment', {'from': start_date})
        if sent_resp and isinstance(sent_resp, dict) and 'data' in sent_resp:
            for item in sent_resp['data']:
                try:
                    sentiment_data.insider_sentiment.append(InsiderSentiment(
                        year=item.get('year'),
                        month=item.get('month'),
                        change=float(item.get('change', 0)),
                        mspr=float(item.get('mspr', 0))
                    ))
                except Exception: continue
                
        # 2. Insider Transactions (stock/insider-transactions)
        # Limit to recent 10?
        trans_resp = self._make_request('stock/insider-transactions', {'limit': 10})
        if trans_resp and isinstance(trans_resp, dict) and 'data' in trans_resp:
             for item in trans_resp['data']:
                try:
                    sentiment_data.insider_transactions.append(InsiderTransaction(
                        name=item.get('name', ''),
                        share=int(item.get('share', 0)),
                        change=int(item.get('change', 0)),
                        filing_date=item.get('filingDate', ''),
                        transaction_date=item.get('transactionDate', ''),
                        transaction_price=float(item.get('transactionPrice', 0.0)),
                        transaction_code=item.get('transactionCode', '')
                    ))
                except Exception: continue
                
        # Return object if we got anything
        if not sentiment_data.insider_sentiment and not sentiment_data.insider_transactions:
            return None
            
        return sentiment_data

    def _fetch_earnings_surprises(self) -> List[Dict]:
        """Fetch earnings surprises history."""
        if self._circuit_broken: return []
        # /stock/earnings?symbol=AAPL
        logger.info(f"Fetching earnings surprises for {self.symbol}...")
        data = self._make_request('stock/earnings')
        if not data or not isinstance(data, list): 
            return []
            
        # Finnhub returns list of dicts: {actual, estimate, period, quarter, symbol, year}
        # We need to map this to our schema or return raw list if schema expects raw?
        # ForecastData.std_earnings_surprise_history expects List[Dict] or List[Object]?
        # Checking unified_schema... usually List[Any] or List[Dict] for complex extensions.
        # Let's return the raw list for now, normalized if needed.
        return data

    def _fetch_eps_estimates(self) -> Optional[Dict]:
        """
        Fetch analyst EPS and Revenue estimates.
        Endpoint: /stock/estimates?symbol=AAPL&freq=quarterly
        Returns: {epsAvg: [{estimate, period}], revenueAvg: [{estimate, period}], ...}
        """
        if self._circuit_broken: return None
        logger.info(f"Fetching EPS/Revenue estimates for {self.symbol}...")
        data = self._make_request('stock/estimates', {'freq': 'quarterly'})
        if not data:
            return None
        
        return data
    
    def _fetch_metrics(self) -> Optional[Dict]:
        """
        Fetch key financial metrics including forward P/E.
        Endpoint: /stock/metric?symbol=AAPL&metric=all
        Returns: {metric: {forwardPeRatio, ...}, series: {...}}
        """
        if self._circuit_broken: return None
        logger.info(f"Fetching financial metrics for {self.symbol}...")
        data = self._make_request('stock/metric', {'metric': 'all'})
        if not data:
            return None
            
        return data

    def _make_request(self, endpoint: str, params: Dict = {}) -> Optional[Any]:
        if self._circuit_broken:
             return None
        
        # Max rotation attempts = number of keys configured
        max_rotations = settings.get_key_count('FINNHUB')
        attempts = 0
        
        while attempts <= max_rotations:
            if not self.api_key:
                logger.warning("Finnhub API key missing")
                return None
                
            url = f"{self.base_url}/{endpoint}"
            current_params = params.copy()
            current_params['token'] = self.api_key
            current_params['symbol'] = self.symbol
            
            try:
                # Use a shorter timeout and fewer retries
                response = requests.get(url, params=current_params, timeout=5)
                
                if response.status_code == 403:
                    logger.warning(f"Finnhub 403 Forbidden for {endpoint}. Your plan may not support this endpoint.")
                    # Do NOT rotate keys for 403 - it's likely a permission issue.
                    return None
                        
                if response.status_code == 429:
                     logger.warning(f"Finnhub 429 Rate Limit for {endpoint}.")
                     attempts += 1
                     if attempts < max_rotations:
                        logger.info(f"Rotating Finnhub API key due to rate limit...")
                        settings.rotate_keys()
                        self.api_key = settings.FINNHUB_API_KEY
                        continue
                     else:
                        logger.warning("All Finnhub keys rate limited.")
                        return None
                
                # Check for API error messages disguised as 200 OK HTML
                content_type = response.headers.get('Content-Type', '')
                if 'application/json' not in content_type:
                    logger.warning(f"Finnhub returned non-JSON content ({content_type}) for {endpoint}. Likely restricted.")
                    return None

                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                # Log but maybe retry with current key?
                # Actually, Finnhub is prone to timeouts.
                if "Read timed out" in str(e) or "Connect timed out" in str(e):
                     logger.warning(f"Finnhub request failed: {endpoint}. Enabling circuit breaker for this session.")
                     self._circuit_broken = True
                     return None
                
                # Other errors
                logger.error(f"Finnhub request failed: {e}")
                return None
            except ValueError as e: # Catch JSON decoding errors
                logger.warning(f"Finnhub invalid JSON response for {endpoint}: {e}")
                return None
            
            # If we fall through
            break
            
        return None

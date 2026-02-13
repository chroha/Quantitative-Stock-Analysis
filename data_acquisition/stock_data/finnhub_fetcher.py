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
    FieldWithSource, TextFieldWithSource
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
            
        # 2. Earnings Surprises
        surprises = self._fetch_earnings_surprises()
        if surprises:
            forecast.std_earnings_surprise_history = surprises
            has_data = True
        
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

    def fetch_profile(self) -> Optional[CompanyProfile]:
        """Fetch basic company profile (Sector/Industry)."""
        data = self._make_request('stock/profile2')
        if not data: return None
        
        try:
            return CompanyProfile(
                std_symbol=data.get('ticker'),
                std_company_name=TextFieldWithSource(value=data.get('name'), source='finnhub'),
                std_industry=TextFieldWithSource(value=data.get('finnhubIndustry'), source='finnhub'),
                std_sector=TextFieldWithSource(value=data.get('finnhubIndustry'), source='finnhub'), # Finnhub puts sector in industry field often
                std_market_cap=FieldWithSource(value=float(data.get('marketCapitalization', 0)), source='finnhub') if data.get('marketCapitalization') else None,
                std_logo_url=TextFieldWithSource(value=data.get('logo'), source='finnhub')
            )
        except Exception as e:
            logger.warning(f"Failed to parse Finnhub profile: {e}")
            return None

    def fetch_price_targets(self) -> Optional[AnalystTargets]:
        """Fetch price targets."""
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

    def _fetch_earnings_surprises(self) -> List[Dict]:
        """Fetch earnings surprises history."""
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
        logger.info(f"Fetching financial metrics for {self.symbol}...")
        data = self._make_request('stock/metric', {'metric': 'all'})
        if not data:
            return None
            
        return data

    def _make_request(self, endpoint: str, params: Dict = {}) -> Optional[Any]:
        """
        Delegates to utils.http_utils.make_request.
        """
        if not self.api_key:
            logger.warning("Finnhub API key missing")
            return None
            
        url = f"{self.base_url}/{endpoint}"
        params = params.copy()
        params['token'] = self.api_key
        params['symbol'] = self.symbol
        
        return make_request(url, params=params, source_name="Finnhub")

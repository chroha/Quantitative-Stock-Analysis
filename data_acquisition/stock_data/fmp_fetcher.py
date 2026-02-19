"""
FMP (Financial Modeling Prep) data fetcher.
Used to supplement Yahoo data with analyst targets and company profile.
[INTERNAL PROCESS MODULE] - This module is used by StockDataLoader, do not call directly.

[INTERNAL PROCESS MODULE] - This module is used by StockDataLoader, do not call directly.

NOTE: FMP uses /stable/ endpoints with query parameters.
Correct format: https://financialmodelingprep.com/stable/{endpoint}?symbol=AAPL&apikey=***
"""

import requests
from typing import Optional
from config.settings import settings
from config import constants
from utils.logger import setup_logger
from utils.unified_schema import (
    AnalystTargets, CompanyProfile, FieldWithSource, TextFieldWithSource, FMP_FIELD_MAPPING,
    ForecastData
)
from utils.field_registry import DataSource
from data_acquisition.stock_data.base_fetcher import BaseFetcher

logger = setup_logger('fmp_fetcher')


class FMPFetcher(BaseFetcher):
    """
    Fetches supplementary data from FMP API.
    Uses /stable/ endpoints with query parameters.
    """
    
    BASE_URL = constants.FMP_BASE_URL
    
    def __init__(self, symbol: str):
        """
        Initialize FMP fetcher for a specific symbol.
        
        Args:
            symbol: Stock ticker symbol
        """

        super().__init__(symbol, DataSource.FMP)
        self.api_key = settings.FMP_API_KEY
        self._free_tier_blocked = False  # Track if free tier limit hit
        self._circuit_broken = False # Track if circuit is broken due to timeouts/errors
        logger.info(f"Initializing FMP fetcher for {self.symbol} (API key: {settings.get_masked_fmp_key()})")
    
    def _make_request(self, endpoint: str, extra_params: dict = None) -> Optional[dict]:
        """
        Make API request to FMP with automatic key rotation on failure.
        """
        # Skip if already blocked by free tier or circuit breaker
        # Note: We might want to RESET circuit breaker if we rotate keys?
        # For now, if circuit is broken, we assume it's broken for the session unless we rotate.
        if self._free_tier_blocked:
            return None
            
        # If circuit was broken due to timeout on previous key, maybe we should try new key?
        # But if it was timeout, likely all keys will timeout if it's network. 
        # If it was 403, we definitely want to rotate.
        
        # Max rotation attempts = number of keys configured
        max_rotations = settings.get_key_count('FMP')
        attempts = 0
        
        while attempts <= max_rotations:
            # If circuit broken, check if we can rotate to fix it (only if it was 403?)
            # Actually, let's just try request.
            
            url = f"{self.BASE_URL}/{endpoint}"
            params = {
                'symbol': self.symbol,
                'apikey': self.api_key
            }
            if extra_params:
                params.update(extra_params)
            
            try:
                logger.debug(f"Requesting FMP endpoint: {endpoint} (Key: {settings.get_masked_fmp_key()})")
                
                # Shorter timeout for FMP since it can hang
                response = requests.get(url, params=params, timeout=5)
                
                # Handle 403 specifically for rotation
                if response.status_code == 403:
                    logger.warning(f"FMP 403 Forbidden for {endpoint} with current key.")
                    attempts += 1
                    if attempts < max_rotations:
                        logger.info(f"Rotating FMP API key and retrying ({attempts}/{max_rotations})...")
                        settings.rotate_keys()
                        self.api_key = settings.FMP_API_KEY # Update local key reference
                        continue # Retry loop
                    else:
                        logger.error("All FMP API keys exhausted or failed.")
                        self._circuit_broken = True
                        return None
                
                response.raise_for_status()
                
                data = response.json()
                
                # Check for FMP error messages (sometimes 200 OK but error in body)
                if isinstance(data, dict) and 'Error Message' in data:
                    msg = data['Error Message']
                    logger.error(f"FMP API error: {msg}")
                    if "Invalid API KEY" in msg or "Limit Reach" in msg:
                        # Treat as 403 logic
                        attempts += 1
                        if attempts < max_rotations:
                            logger.info(f"Rotating FMP API key due to error message and retrying...")
                            settings.rotate_keys()
                            self.api_key = settings.FMP_API_KEY
                            continue
                    return None
                
                logger.debug(f"Successfully fetched data from {endpoint}")
                return data
            
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 402:
                    # Free tier limit - log once and skip remaining calls
                    if not self._free_tier_blocked:
                        self._free_tier_blocked = True
                        print(f"          (FMP free tier - skipping)")
                        logger.warning(f"FMP free tier does not support {self.symbol} - skipping FMP data")
                    return None
                elif e.response.status_code == 403:
                    # Handled above
                    pass 
                else:
                    logger.error(f"FMP HTTP error for {endpoint}: {e}")
                return None
            
            except requests.exceptions.RequestException as e:
                logger.error(f"FMP request failed for {endpoint}: {e}")
                if "Read timed out" in str(e) or "Connect timed out" in str(e):
                     logger.warning(f"FMP Timeout on {endpoint}. Enabling circuit breaker.")
                     self._circuit_broken = True
                return None
            
            except ValueError as e:
                logger.error(f"FMP JSON parsing error for {endpoint}: {e}")
                return None
                
            # If we get here (and didn't continue/return), break loop
            break
            
        return None
    
    def fetch_analyst_targets(self) -> Optional[AnalystTargets]:
        """Fetch analyst price target consensus."""
        if self._circuit_broken: return None
        data = self._make_request(constants.FMP_ENDPOINTS['price_target'])
        
        if not data or not isinstance(data, list) or len(data) == 0:
            logger.warning(f"No analyst target data available for {self.symbol}")
            return None
        
        # Get the first item (should be only one)
        latest = data[0]
        
        try:
            targets = AnalystTargets(
                std_price_target_low=FieldWithSource(value=float(latest['targetLow']), source='fmp') if latest.get('targetLow') else None,
                std_price_target_high=FieldWithSource(value=float(latest['targetHigh']), source='fmp') if latest.get('targetHigh') else None,
                std_price_target_avg=FieldWithSource(value=float(latest['targetConsensus']), source='fmp') if latest.get('targetConsensus') else None,
                std_price_target_consensus=FieldWithSource(value=float(latest['targetMedian']), source='fmp') if latest.get('targetMedian') else None,
                std_number_of_analysts=None  # Not provided in consensus endpoint
            )
            
            logger.info(f"Fetched analyst targets for {self.symbol} from FMP")
            return targets
        
        except (ValueError, KeyError) as e:
            logger.error(f"Failed to parse analyst targets from FMP: {e}")
            return None
    
    def fetch_profile(self) -> Optional[CompanyProfile]:
        """Fetch company profile."""
        if self._circuit_broken: return None
        data = self._make_request(constants.FMP_ENDPOINTS['profile'])
        
        if not data or not isinstance(data, list) or len(data) == 0:
            logger.warning(f"No profile data available for {self.symbol} from FMP")
            return None
        
        profile_data = data[0]
        
        try:
            profile = CompanyProfile(
                std_symbol=profile_data.get('symbol'),
                std_company_name=TextFieldWithSource(value=profile_data.get('companyName'), source='fmp'),
                std_industry=TextFieldWithSource(value=profile_data.get('industry'), source='fmp'),
                std_sector=TextFieldWithSource(value=profile_data.get('sector'), source='fmp'),
                std_market_cap=FieldWithSource(value=float(profile_data.get('mktCap')), source='fmp') if profile_data.get('mktCap') else None,
                std_description=TextFieldWithSource(value=profile_data.get('description'), source='fmp'),
                std_website=TextFieldWithSource(value=profile_data.get('website'), source='fmp'),
                std_ceo=TextFieldWithSource(value=profile_data.get('ceo'), source='fmp'),
                std_beta=FieldWithSource(value=float(profile_data.get('beta')), source='fmp') if profile_data.get('beta') else None,
                
                # Valuation Ratios - FMP Profile endpoint is limited, setting to None or mapping if available
                # Note: FMP often puts these in 'key-metrics' endpoint, not profile.
                std_pe_ratio=None, 
                std_pb_ratio=None,
                std_ps_ratio=None,
                std_eps=None, 
                std_book_value_per_share=None,
                std_dividend_yield=None, # profile has 'lastDiv' (amount) but not yield %
                
                # Forward/Trailing EPS - Not in FMP profile
                std_forward_eps=None,
                std_trailing_eps=None,
                std_forward_pe=None,
                std_peg_ratio=None,
                std_earnings_growth=None
            )
            
            logger.info(f"Fetched company profile for {self.symbol} from FMP")
            return profile
        
        except (ValueError, KeyError) as e:
            logger.error(f"Failed to parse profile from FMP: {e}")
            return None
    
    
    def fetch_income_statements(self, limit: int = 6) -> list:
        """Fetch income statements."""
        if self._circuit_broken: return []
        from utils.unified_schema import IncomeStatement
        from utils.schema_mapper import SchemaMapper
        from utils.field_registry import DataSource as RegistryDataSource
        
        data = self._make_request(constants.FMP_ENDPOINTS['income_statement'])
        
        if not data or not isinstance(data, list):
            logger.warning(f"No income statement data from FMP for {self.symbol}")
            return []
        
        statements = []
        # Apply slice if limit is provided
        processed_data = data[:limit] if limit else data
        
        for item in processed_data:
            try:
                period_str = item.get('date')
                if not period_str: continue
                
                # Map fields using SchemaMapper
                mapped_fields = SchemaMapper.map_statement(
                    item, 
                    'income', 
                    RegistryDataSource.FMP
                )
                
                stmt = IncomeStatement(std_period=period_str, **mapped_fields)
                statements.append(stmt)
            except (ValueError, KeyError) as e:
                logger.warning(f"Failed to parse FMP income statement for period {item.get('date')}: {e}")
                continue
        
        logger.info(f"Fetched {len(statements)} income statements from FMP for {self.symbol}")
        return statements
    
    def fetch_balance_sheets(self, limit: int = 6) -> list:
        """Fetch balance sheets (Annual + Quarterly)."""
        if self._circuit_broken: return []
        from utils.unified_schema import BalanceSheet
        from utils.schema_mapper import SchemaMapper
        from utils.field_registry import DataSource as RegistryDataSource
        
        # Helper to process raw data list
        def process_data(data_list):
            stmts = []
            if not data_list: return stmts
            for item in data_list:
                try:
                    period_str = item.get('date')
                    if not period_str: continue
                    
                    mapped_fields = SchemaMapper.map_statement(
                        item, 
                        'balance', 
                        RegistryDataSource.FMP
                    )
                    
                    stmt = BalanceSheet(std_period=period_str, **mapped_fields)
                    stmts.append(stmt)
                except (ValueError, KeyError) as e:
                    continue
            return stmts

        # 1. Fetch Annual
        annual_data = self._make_request(constants.FMP_ENDPOINTS['balance_sheet'])
        
        # Apply limit to annual data. If limit is None, take all.
        sliced_annual = annual_data[:limit] if (limit and annual_data) else annual_data
        
        annual_stmts = process_data(sliced_annual) if sliced_annual else []

        # 2. Fetch Quarterly (latest 4 is enough to get the recent one)
        # If limit is massive (Full Scan), maybe we want more quarterly?
        # For now, stick to standard logic for quarterly to ensure TTM calculation works
        if not self._circuit_broken:
            quarterly_data = self._make_request(constants.FMP_ENDPOINTS['balance_sheet'], {'period': 'quarter', 'limit': 4})
            quarterly_stmts = process_data(quarterly_data) if quarterly_data else []
        else:
            quarterly_stmts = []

        # 3. Merge and Deduplicate
        merged = {s.std_period: s for s in annual_stmts}
        for s in quarterly_stmts:
             # If date not present, add it. (Quarterly is usually newer or same date as annual)
             if s.std_period not in merged:
                 merged[s.std_period] = s
        
        final_list = list(merged.values())
        final_list.sort(key=lambda x: x.std_period, reverse=True)
        
        logger.info(f"Fetched {len(final_list)} balance sheets (Annual+Quarterly) from FMP")
        return final_list
    
    def fetch_cash_flow_statements(self, limit: int = 6) -> list:
        """Fetch cash flow statements."""
        if self._circuit_broken: return []
        from utils.unified_schema import CashFlow
        from utils.schema_mapper import SchemaMapper
        from utils.field_registry import DataSource as RegistryDataSource
        
        data = self._make_request(constants.FMP_ENDPOINTS['cash_flow'])
        
        if not data or not isinstance(data, list):
            logger.warning(f"No cash flow data from FMP for {self.symbol}")
            return []
        
        statements = []
        # Apply slice if limit is provided
        processed_data = data[:limit] if limit else data

        for item in processed_data:
            try:
                period_str = item.get('date')
                if not period_str: continue

                mapped_fields = SchemaMapper.map_statement(
                    item, 
                    'cashflow', 
                    RegistryDataSource.FMP
                )

                stmt = CashFlow(std_period=period_str, **mapped_fields)
                statements.append(stmt)
            except (ValueError, KeyError) as e:
                logger.warning(f"Failed to parse FMP cash flow for period {item.get('date')}: {e}")
                continue
        
        logger.info(f"Fetched {len(statements)} cash flows from FMP for {self.symbol}")
        return statements
    
    def fetch_all(self) -> dict:
        """Fetch all available data from FMP."""
        logger.info(f"Starting FMP data fetch for {self.symbol}")
        
        return {
            'analyst_targets': self.fetch_analyst_targets(),
            'profile': self.fetch_profile(),
            'income_statements': self.fetch_income_statements(),
            'balance_sheets': self.fetch_balance_sheets(),
            'cash_flows': self.fetch_cash_flows(),
        }

    def fetch_ratios(self) -> Optional[CompanyProfile]:
        """Fetch valuation ratios."""
        if self._circuit_broken: return None
        data = self._make_request(constants.FMP_ENDPOINTS['ratios'], {'limit': 1})
        if not data: return None
        
        try:
            item = data[0]
            return CompanyProfile(
                std_pe_ratio=FieldWithSource(value=float(item.get('peRatioTTM') or 0), source='fmp'),
                std_pb_ratio=FieldWithSource(value=float(item.get('priceToBookRatioTTM') or 0), source='fmp'),
                std_ps_ratio=FieldWithSource(value=float(item.get('priceToSalesRatioTTM') or 0), source='fmp'),
                std_dividend_yield=FieldWithSource(value=float(item.get('dividendYielTTM') or 0), source='fmp') if item.get('dividendYielTTM') else None,
                std_peg_ratio=FieldWithSource(value=float(item.get('pegRatioTTM') or 0), source='fmp') if item.get('pegRatioTTM') else None,
            )
        except (ValueError, IndexError, KeyError) as e:
            logger.warning(f"Failed to parse FMP ratios: {e}")
            return None

    def fetch_key_metrics(self) -> Optional[CompanyProfile]:
        """Fetch key metrics (Market Cap, BVPS, etc)."""
        if self._circuit_broken: return None
        data = self._make_request(constants.FMP_ENDPOINTS['key_metrics'], {'limit': 1})
        if not data: return None
        
        try:
            item = data[0]
            return CompanyProfile(
                std_market_cap=FieldWithSource(value=float(item.get('marketCap') or 0), source='fmp'),
                std_book_value_per_share=FieldWithSource(value=float(item.get('bookValuePerShare') or 0), source='fmp'),
                std_eps=FieldWithSource(value=float(item.get('netIncomePerShare') or 0), source='fmp')
            )
        except (ValueError, IndexError, KeyError) as e:
             logger.warning(f"Failed to parse FMP key metrics: {e}")
             return None

    def fetch_forecast_data(self) -> Optional[ForecastData]:
        """Fetch comprehensive forecast data from FMP."""
        if self._circuit_broken: return None
        forecast = ForecastData()
        has_data = False
        
        # 1. Fetch analyst estimates (EPS/Revenue estimates)
        logger.info(f"Fetching analyst estimates for {self.symbol}...")
        # FMP stable requires 'period' parameter (annual is free, quarter is premium)
        # Revert to standard endpoint with query params
        estimates_data = self._make_request(
            constants.FMP_ENDPOINTS['analyst_estimates'], 
            {'limit': 1, 'period': 'annual'}
        )
        if estimates_data and len(estimates_data) > 0:
            try:
                item = estimates_data[0]
                
                # EPS estimates
                if eps_avg := item.get('estimatedEpsAvg'):
                    forecast.std_eps_estimate_current_year = FieldWithSource(
                        value=float(eps_avg), source='fmp'
                    )
                    has_data = True
                
                # Revenue estimates
                if rev_avg := item.get('estimatedRevenueAvg'):
                    forecast.std_revenue_estimate_current_year = FieldWithSource(
                        value=float(rev_avg), source='fmp'
                    )
                    has_data = True
                    
                # Number of analysts
                if num_analysts := item.get('numberAnalystEstimatedRevenue'):
                    forecast.std_number_of_analysts = FieldWithSource(
                        value=float(num_analysts), source='fmp'
                    )
                    has_data = True
                    
                logger.info(f"  ✓ Got analyst estimates for {self.symbol}")
            except (ValueError, KeyError) as e:
                logger.warning(f"Failed to parse analyst estimates: {e}")
        elif self._circuit_broken:
            return None # Stop if broke
        
        # 2. Fetch price targets
        logger.info(f"Fetching price targets for {self.symbol}...")
        targets_data = self._make_request(constants.FMP_ENDPOINTS['price_target'])
        if targets_data and len(targets_data) > 0:
            try:
                target = targets_data[0]
                
                if target_low := target.get('targetLow'):
                    forecast.std_price_target_low = FieldWithSource(value=float(target_low), source='fmp')
                    has_data = True
                    
                if target_high := target.get('targetHigh'):
                    forecast.std_price_target_high = FieldWithSource(value=float(target_high), source='fmp')
                    has_data = True
                    
                if target_mean := target.get('targetMean'):
                    forecast.std_price_target_avg = FieldWithSource(value=float(target_mean), source='fmp')
                    has_data = True
                    
                if target_consensus := target.get('targetConsensus'):
                    forecast.std_price_target_consensus = FieldWithSource(value=float(target_consensus), source='fmp')
                    has_data = True
                    
                logger.info(f"  ✓ Got price targets for {self.symbol}")
            except (ValueError, KeyError) as e:
                logger.warning(f"Failed to parse price targets: {e}")
        elif self._circuit_broken:
            return None
        
        # 3. Fetch analyst ratings distribution (if endpoint exists)
        # Note: FMP may have this in 'grade' or 'rating' endpoints - check API docs
        # For now, skip if not available in free tier
        
        # 4. Fetch financial growth (for growth estimates)
        logger.info(f"Fetching growth estimates for {self.symbol}...")
        growth_data = self._make_request(constants.FMP_ENDPOINTS['financial_growth'], {'limit': 1})
        if growth_data and len(growth_data) > 0:
            try:
                item = growth_data[0]
                
                # EPS growth
                if eps_growth := item.get('epsgrowth'):
                    forecast.std_earnings_growth_current_year = FieldWithSource(
                        value=float(eps_growth), source='fmp'
                    )
                    has_data = True
                    
                # Revenue growth
                if rev_growth := item.get('revenueGrowth'):
                    forecast.std_revenue_growth_next_year = FieldWithSource(
                        value=float(rev_growth), source='fmp'
                    )
                    has_data = True
                    
                logger.info(f"  ✓ Got growth estimates for {self.symbol}")
            except (ValueError, KeyError) as e:
                logger.warning(f"Failed to parse growth estimates: {e}")
        
        if has_data:
            logger.info(f"Successfully fetched forecast data for {self.symbol} from FMP")
            return forecast
        else:
            logger.warning(f"No forecast data available for {self.symbol} from FMP")
            return None
    
    
    # DEPRECATED: Old methods kept for backward compatibility
    def fetch_analyst_estimates(self) -> Optional[CompanyProfile]:
        """DEPRECATED: Use fetch_forecast_data() instead."""
        forecast = self.fetch_forecast_data()
        if not forecast or not forecast.std_eps_estimate_current_year:
            return None
        # Convert to old format for compatibility
        return CompanyProfile(
            std_forward_eps=forecast.std_eps_estimate_current_year
        )
    
    def fetch_financial_growth(self) -> Optional[CompanyProfile]:
        """DEPRECATED: Use fetch_forecast_data() instead."""
        forecast = self.fetch_forecast_data()
        if not forecast or not forecast.std_earnings_growth_current_year:
            return None
        # Convert to old format
        return CompanyProfile(
            std_earnings_growth=forecast.std_earnings_growth_current_year
        )
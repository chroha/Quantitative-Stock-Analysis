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
    AnalystTargets, CompanyProfile, FieldWithSource, TextFieldWithSource, FMP_FIELD_MAPPING
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
        logger.info(f"Initializing FMP fetcher for {self.symbol} (API key: {settings.get_masked_fmp_key()})")
    
    def _make_request(self, endpoint: str, extra_params: dict = None) -> Optional[dict]:
        """
        Make API request to FMP.
        
        Args:
            endpoint: API endpoint name (e.g., 'profile', 'price-target-consensus')
            extra_params: Additional query parameters
            
        Returns:
            JSON response or None if request fails
        """
        # Skip if already blocked by free tier
        if self._free_tier_blocked:
            return None
            
        url = f"{self.BASE_URL}/{endpoint}"
        params = {
            'symbol': self.symbol,
            'apikey': self.api_key
        }
        if extra_params:
            params.update(extra_params)
        
        try:
            logger.debug(f"Requesting FMP endpoint: {endpoint}")
            response = requests.get(url, params=params, timeout=constants.FMP_TIMEOUT_SECONDS)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for FMP error messages
            if isinstance(data, dict) and 'Error Message' in data:
                logger.error(f"FMP API error: {data['Error Message']}")
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
                logger.warning(f"FMP 403 Forbidden for {endpoint} - check API plan")
            else:
                logger.error(f"FMP HTTP error for {endpoint}: {e}")
            return None
        
        except requests.exceptions.RequestException as e:
            logger.error(f"FMP request failed for {endpoint}: {e}")
            return None
        
        except ValueError as e:
            logger.error(f"FMP JSON parsing error for {endpoint}: {e}")
            return None
    
    def fetch_analyst_targets(self) -> Optional[AnalystTargets]:
        """
        Fetch analyst price target consensus.
        Uses /stable/price-target-consensus endpoint.
        
        Returns:
            AnalystTargets object or None if fetch fails
        """
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
        """
        Fetch company profile from /stable/profile endpoint.
        
        NOTE: If you add new fields here, you MUST update CompanyProfile in utils/unified_schema.py.
        Otherwise, the data will be dropped during the save process.
        注意: 如果在此处添加新字段，必须同步更新 utils/unified_schema.py 中的 CompanyProfile 定义。
        否则，数据将在保存过程中被丢弃。
        
        Returns:
            CompanyProfile object or None if fetch fails
        """
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
    
    
    def fetch_income_statements(self) -> list:
        """
        Fetch income statements from FMP /stable/income-statement endpoint.
        
        Returns:
            List of IncomeStatement objects
        """
        from utils.unified_schema import IncomeStatement
        from utils.schema_mapper import SchemaMapper
        from utils.field_registry import DataSource as RegistryDataSource
        
        data = self._make_request(constants.FMP_ENDPOINTS['income_statement'])
        
        if not data or not isinstance(data, list):
            logger.warning(f"No income statement data from FMP for {self.symbol}")
            return []
        
        statements = []
        for item in data[:6]:  # Fetch up to 6 years
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
    
    def fetch_balance_sheets(self) -> list:
        """
        Fetch balance sheets (Annual + Quarterly).
        """
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
        annual_stmts = process_data(annual_data[:6]) if annual_data else []

        # 2. Fetch Quarterly (latest 4 is enough to get the recent one)
        quarterly_data = self._make_request(constants.FMP_ENDPOINTS['balance_sheet'], {'period': 'quarter', 'limit': 4})
        quarterly_stmts = process_data(quarterly_data) if quarterly_data else []

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
    
    def fetch_cash_flow_statements(self) -> list:
        """
        Fetch cash flow statements from FMP /stable/cash-flow-statement endpoint.
        
        Returns:
            List of CashFlow objects
        """
        from utils.unified_schema import CashFlow
        from utils.schema_mapper import SchemaMapper
        from utils.field_registry import DataSource as RegistryDataSource
        
        data = self._make_request(constants.FMP_ENDPOINTS['cash_flow'])
        
        if not data or not isinstance(data, list):
            logger.warning(f"No cash flow data from FMP for {self.symbol}")
            return []
        
        statements = []
        for item in data[:6]:
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
        """
        Fetch all available data from FMP.
        
        Returns:
            Dictionary with analyst_targets, profile, and financial statements
        """
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

    def fetch_financial_growth(self) -> Optional[CompanyProfile]:
        """Fetch financial growth metrics."""
        data = self._make_request(constants.FMP_ENDPOINTS['financial_growth'], {'limit': 1})
        if not data: return None
        
        try:
            item = data[0]
            return CompanyProfile(
                 std_earnings_growth=FieldWithSource(value=float(item.get('epsgrowth') or 0), source='fmp')
            )
        except (ValueError, IndexError, KeyError) as e:
             logger.warning(f"Failed to parse FMP growth: {e}")
             return None

    def fetch_analyst_estimates(self) -> Optional[CompanyProfile]:
        """Fetch analyst estimates (Forward EPS)."""
        data = self._make_request(constants.FMP_ENDPOINTS['analyst_estimates'], {'limit': 1})
        if not data: return None
        
        try:
            item = data[0]
            return CompanyProfile(
                std_forward_eps=FieldWithSource(value=float(item.get('estimatedEpsAvg') or 0), source='fmp')
            )
        except (ValueError, IndexError, KeyError) as e:
             logger.warning(f"Failed to parse FMP estimates: {e}")
             return None
"""
Alpha Vantage Data Fetcher - Third-tier data source for financial statements.
Used as fallback when Yahoo and FMP data is incomplete.

API Endpoints:
- INCOME_STATEMENT: Annual and quarterly income statements
- BALANCE_SHEET: Annual and quarterly balance sheets  
- CASH_FLOW: Annual and quarterly cash flow statements
- OVERVIEW: Company profile and key metrics

Rate Limits (Free Tier):
- 25 requests/day
- 5 requests/minute
"""

import time
import requests
from typing import Optional, List, Dict, Any
from datetime import datetime

from config.settings import settings
from utils.logger import setup_logger
from utils.unified_schema import (
    IncomeStatement, BalanceSheet, CashFlow, CompanyProfile,
    FieldWithSource, TextFieldWithSource
)
from data_acquisition.stock_data.base_fetcher import BaseFetcher, DataSource, FetcherRegistry

logger = setup_logger('alphavantage_fetcher')





class AlphaVantageFetcher(BaseFetcher):
    """
    Fetches financial data from Alpha Vantage API.
    Used as third-tier fallback data source.
    """
    
    BASE_URL = "https://www.alphavantage.co/query"
    
    # Rate limiting - Alpha Vantage free tier: 5 requests/minute, 500/day
    # For single stock (3 requests), 1.5s interval is safe and fast
    # For batch processing, caller should add delays between stocks
    _last_request_time = 0
    MIN_REQUEST_INTERVAL = 1.5  # 1.5 seconds between requests (conservative for 3-call batches)
    
    def __init__(self, symbol: str):
        from utils.field_registry import DataSource as RegistryDataSource
        super().__init__(symbol, RegistryDataSource.ALPHAVANTAGE)
        self.api_key = settings.ALPHAVANTAGE_API_KEY
        
        if not self.api_key:
            logger.warning("Alpha Vantage API key not configured")
    
    def _rate_limit(self):
        """Enforce rate limiting between API calls."""
        now = time.time()
        elapsed = now - AlphaVantageFetcher._last_request_time
        
        if elapsed < self.MIN_REQUEST_INTERVAL:
            sleep_time = self.MIN_REQUEST_INTERVAL - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)
        
        AlphaVantageFetcher._last_request_time = time.time()
    
    def _make_request(self, function: str) -> Optional[Dict[str, Any]]:
        """
        Make API request with rate limiting and error handling.
        
        Args:
            function: Alpha Vantage function name (e.g., 'INCOME_STATEMENT')
            
        Returns:
            JSON response dict or None on failure
        """
        if not self.api_key:
            logger.error("Cannot make request: Alpha Vantage API key not configured")
            return None
        
        self._rate_limit()
        
        params = {
            'function': function,
            'symbol': self.symbol,
            'apikey': self.api_key
        }
        
        try:
            logger.info(f"Fetching {function} for {self.symbol} from Alpha Vantage")
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API errors
            if 'Error Message' in data:
                logger.error(f"Alpha Vantage API error: {data['Error Message']}")
                return None
            
            if 'Note' in data:
                # Rate limit exceeded
                logger.warning(f"Alpha Vantage rate limit: {data['Note']}")
                return None
            
            if 'Information' in data:
                # API info message (usually rate limit warning)
                logger.warning(f"Alpha Vantage notice: {data['Information']}")
                return None
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Alpha Vantage request failed: {e}")
            return None
        except ValueError as e:
            logger.error(f"Alpha Vantage JSON parse error: {e}")
            return None
    
    def _create_field_with_source(self, value: Any) -> Optional[FieldWithSource]:
        """Create FieldWithSource from raw value."""
        if value is None or value == 'None' or value == '':
            return None
        
        try:
            numeric_value = float(value)
            return FieldWithSource(value=numeric_value, source='alphavantage')
        except (ValueError, TypeError):
            return None
    
    def _parse_period(self, date_str: str) -> str:
        """Parse fiscal date to unified format (YYYY-MM-DD)."""
        if not date_str:
            return 'unknown'
        
        # Return the date string directly as YYYY-MM-DD is the new standard
        return date_str
    
    def fetch_profile(self) -> Optional[CompanyProfile]:
        """
        Fetch company overview/profile.
        
        NOTE: If you add new fields here, you MUST update CompanyProfile in utils/unified_schema.py.
        Otherwise, the data will be dropped during the save process.
        注意: 如果在此处添加新字段，必须同步更新 utils/unified_schema.py 中的 CompanyProfile 定义。
        否则，数据将在保存过程中被丢弃。
        """
        data = self._make_request('OVERVIEW')
        
        if not data or 'Symbol' not in data:
            return None
        
        logger.info(f"Fetched company overview for {self.symbol} from Alpha Vantage")
        
        return CompanyProfile(
            std_symbol=self.symbol,
            std_company_name=TextFieldWithSource(value=data.get('Name'), source='alphavantage'),
            std_industry=TextFieldWithSource(value=data.get('Industry'), source='alphavantage'),
            std_sector=TextFieldWithSource(value=data.get('Sector'), source='alphavantage'),
            std_market_cap=self._create_field_with_source(data.get('MarketCapitalization')),
            std_description=TextFieldWithSource(value=data.get('Description'), source='alphavantage'),
            std_website=None, # Not provided in OVERVIEW
            std_beta=self._create_field_with_source(data.get('Beta')),
            
            # Valuation Ratios (New Mappings 2026-01-20)
            std_pe_ratio=self._create_field_with_source(data.get('PERatio') or data.get('TrailingPE')),
            std_pb_ratio=self._create_field_with_source(data.get('PriceToBookRatio')),
            std_ps_ratio=self._create_field_with_source(data.get('PriceToSalesRatioTTM')),
            std_eps=self._create_field_with_source(data.get('EPS')),
            std_book_value_per_share=self._create_field_with_source(data.get('BookValue')),
            std_dividend_yield=self._create_field_with_source(data.get('DividendYield')),
            
            # Existing mappings
            std_forward_eps=self._create_field_with_source(data.get('ForwardEPS') or data.get('EPS')), # Fallback to EPS if forward missing
            std_trailing_eps=self._create_field_with_source(data.get('EPS')),
            std_forward_pe=self._create_field_with_source(data.get('ForwardPE')),
            std_peg_ratio=self._create_field_with_source(data.get('PEGRatio')),
            std_earnings_growth=self._create_field_with_source(data.get('QuarterlyEarningsGrowthYOY'))
        )


    
    def fetch_income_statements(self) -> List[IncomeStatement]:
        """Fetch annual income statements."""
        from utils.schema_mapper import SchemaMapper
        from utils.field_registry import DataSource as RegistryDataSource
        
        data = self._make_request('INCOME_STATEMENT')
        
        if not data or 'annualReports' not in data:
            return []
        
        statements = []
        annual_reports = data.get('annualReports', [])
        
        logger.info(f"Fetched {len(annual_reports)} income statements for {self.symbol} from Alpha Vantage")
        
        for report in annual_reports[:5]:  # Limit to 5 years
            try:
                mapped_fields = SchemaMapper.map_statement(
                    report, 
                    'income', 
                    RegistryDataSource.ALPHAVANTAGE
                )
                
                stmt = IncomeStatement(
                    std_period=self._parse_period(report.get('fiscalDateEnding')),
                    **mapped_fields
                )
                statements.append(stmt)
            except (ValueError, KeyError) as e:
                continue
        
        return statements
    
    def fetch_balance_sheets(self) -> List[BalanceSheet]:
        """Fetch balance sheets (Annual + Quarterly)."""
        data = self._make_request('BALANCE_SHEET')
        
        if not data:
            return []
        
        def process_reports(reports):
            stmts = []
            for report in reports:
                # Calculate total debt from short-term and long-term
                short_debt = report.get('shortTermDebt') or report.get('currentDebt')
                long_debt = report.get('longTermDebt') or report.get('longTermDebtNoncurrent')
                
                total_debt = None
                if short_debt and long_debt:
                    try:
                        total_debt = float(short_debt) + float(long_debt)
                    except (ValueError, TypeError):
                        pass
                elif short_debt:
                    try:
                        total_debt = float(short_debt)
                    except (ValueError, TypeError):
                        pass
                elif long_debt:
                    try:
                        total_debt = float(long_debt)
                    except (ValueError, TypeError):
                        pass
                
                stmt = BalanceSheet(
                    std_period=self._parse_period(report.get('fiscalDateEnding')), # Note: _parse_period adds -FY, we might want to check this behavior
                    std_total_assets=self._create_field_with_source(report.get('totalAssets')),
                    std_current_assets=self._create_field_with_source(report.get('totalCurrentAssets')),
                    std_cash=self._create_field_with_source(
                        report.get('cashAndCashEquivalentsAtCarryingValue') or 
                        report.get('cashAndShortTermInvestments')
                    ),
                    std_accounts_receivable=self._create_field_with_source(report.get('currentNetReceivables')),
                    std_inventory=self._create_field_with_source(report.get('inventory')),
                    std_total_liabilities=self._create_field_with_source(report.get('totalLiabilities')),
                    std_current_liabilities=self._create_field_with_source(report.get('totalCurrentLiabilities')),
                    std_total_debt=FieldWithSource(value=total_debt, source='alphavantage') if total_debt else None,
                    std_shareholder_equity=self._create_field_with_source(report.get('totalShareholderEquity')),
                )
                stmts.append(stmt)
            return stmts

        annual_reports = data.get('annualReports', [])
        quarterly_reports = data.get('quarterlyReports', [])
        
        annual_stmts = process_reports(annual_reports[:5])
        # _parse_period currently appends -FY to everything if it looks like a date. 
        # We need to ensure quarterly reports get their specific date or a different suffix?
        # Let's check _parse_period implementation. 
        # It takes YYYY-MM-DD and makes it YYYY-FY. That's bad for quarterly merging.
        # I should probably update _parse_period or bypass it here.
        # For now, let's bypass it for now by setting std_period directly to date string if possible?
        # Actually, let's look at _parse_period again.
        
        # Override _parse_period behavior here by manually setting std_period to date string for quarterly
        quarterly_stmts = []
        for report in quarterly_reports[:4]:
             # Copy-paste logic from process_reports but with direct date for period
                short_debt = report.get('shortTermDebt') or report.get('currentDebt')
                long_debt = report.get('longTermDebt') or report.get('longTermDebtNoncurrent')
                total_debt = None
                if short_debt and long_debt:
                    try: total_debt = float(short_debt) + float(long_debt)
                    except: pass
                elif short_debt:
                    try: total_debt = float(short_debt)
                    except: pass
                elif long_debt:
                    try: total_debt = float(long_debt)
                    except: pass
                
                stmt = BalanceSheet(
                    std_period=report.get('fiscalDateEnding'), # Use direct date string for Quarterly
                    std_total_assets=self._create_field_with_source(report.get('totalAssets')),
                    std_current_assets=self._create_field_with_source(report.get('totalCurrentAssets')),
                    std_cash=self._create_field_with_source(report.get('cashAndCashEquivalentsAtCarryingValue') or report.get('cashAndShortTermInvestments')),
                    std_accounts_receivable=self._create_field_with_source(report.get('currentNetReceivables')),
                    std_inventory=self._create_field_with_source(report.get('inventory')),
                    std_total_liabilities=self._create_field_with_source(report.get('totalLiabilities')),
                    std_current_liabilities=self._create_field_with_source(report.get('totalCurrentLiabilities')),
                    std_total_debt=FieldWithSource(value=total_debt, source='alphavantage') if total_debt else None,
                    std_shareholder_equity=self._create_field_with_source(report.get('totalShareholderEquity')),
                )
                quarterly_stmts.append(stmt)

        # Merge
        merged = {s.std_period: s for s in annual_stmts}
        for s in quarterly_stmts:
            if s.std_period and s.std_period not in merged:
                merged[s.std_period] = s
        
        final_list = list(merged.values())
        final_list.sort(key=lambda x: x.std_period if x.std_period else "", reverse=True)
        
        logger.info(f"Fetched {len(final_list)} balance sheets (Annual+Quarterly) from Alpha Vantage")
        return final_list
    
    def fetch_cash_flows(self) -> List[CashFlow]:
        """Fetch annual cash flow statements."""
        from utils.schema_mapper import SchemaMapper
        from utils.field_registry import DataSource as RegistryDataSource
        
        data = self._make_request('CASH_FLOW')
        
        if not data or 'annualReports' not in data:
            return []
        
        statements = []
        annual_reports = data.get('annualReports', [])
        
        logger.info(f"Fetched {len(annual_reports)} cash flow statements for {self.symbol} from Alpha Vantage")
        
        for report in annual_reports[:5]:  # Limit to 5 years
            try:
                mapped_fields = SchemaMapper.map_statement(
                    report, 
                    'cashflow', 
                    RegistryDataSource.ALPHAVANTAGE
                )
                
                # Manual Free Cash Flow Calculation
                # FCF = OCF - Capex
                ocf_val = report.get('operatingCashflow')
                capex_val = report.get('capitalExpenditures')
                
                if ocf_val and capex_val:
                    try:
                        ocf = float(ocf_val)
                        capex = float(capex_val)
                        # Capex is usually negative. FCF is cash generated after spending on assets.
                        # So FCF = OCF + Capex (if capex is negative)
                        # To be safe: FCF = OCF - abs(Capex)
                        fcf = ocf - abs(capex)
                        mapped_fields['std_free_cash_flow'] = FieldWithSource(value=fcf, source='alphavantage')
                    except: pass

                stmt = CashFlow(
                    std_period=self._parse_period(report.get('fiscalDateEnding')),
                    **mapped_fields
                )
                statements.append(stmt)
            except (ValueError, KeyError):
                continue
        
        return statements


# Register this fetcher
FetcherRegistry.register(DataSource.ALPHAVANTAGE, AlphaVantageFetcher)

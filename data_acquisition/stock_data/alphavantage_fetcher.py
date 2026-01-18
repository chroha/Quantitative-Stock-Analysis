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


# Field mappings from Alpha Vantage to unified schema
AV_INCOME_MAPPING = {
    'totalRevenue': 'std_revenue',
    'costOfRevenue': 'std_cost_of_revenue',
    'costofGoodsAndServicesSold': 'std_cost_of_revenue',  # Alternative name
    'grossProfit': 'std_gross_profit',
    'operatingExpenses': 'std_operating_expenses',
    'operatingIncome': 'std_operating_income',
    'incomeBeforeTax': 'std_pretax_income',
    'incomeTaxExpense': 'std_income_tax_expense',
    'netIncome': 'std_net_income',
    'ebitda': 'std_ebitda',
    'ebit': 'std_ebit',  # May need to add this to schema if needed
}

AV_BALANCE_MAPPING = {
    'totalAssets': 'std_total_assets',
    'totalCurrentAssets': 'std_current_assets',
    'cashAndCashEquivalentsAtCarryingValue': 'std_cash',
    'cashAndShortTermInvestments': 'std_cash',  # Alternative
    'currentNetReceivables': 'std_accounts_receivable',
    'inventory': 'std_inventory',
    'totalLiabilities': 'std_total_liabilities',
    'totalCurrentLiabilities': 'std_current_liabilities',
    'shortTermDebt': 'std_total_debt',  # Will combine with longTermDebt
    'longTermDebt': 'std_long_term_debt',
    'totalShareholderEquity': 'std_shareholder_equity',
}

AV_CASHFLOW_MAPPING = {
    'operatingCashflow': 'std_operating_cash_flow',
    'cashflowFromInvestment': 'std_investing_cash_flow',
    'cashflowFromFinancing': 'std_financing_cash_flow',
    'capitalExpenditures': 'std_capex',
    'dividendPayout': 'std_dividends_paid',
    'dividendPayoutCommonStock': 'std_dividends_paid',  # Alternative
}


class AlphaVantageFetcher(BaseFetcher):
    """
    Fetches financial data from Alpha Vantage API.
    Used as third-tier fallback data source.
    """
    
    BASE_URL = "https://www.alphavantage.co/query"
    
    # Rate limiting
    _last_request_time = 0
    MIN_REQUEST_INTERVAL = 12.1  # ~5 requests per minute = 12 seconds between requests
    
    def __init__(self, symbol: str):
        super().__init__(symbol)
        self.api_key = settings.ALPHAVANTAGE_API_KEY
        
        if not self.api_key:
            logger.warning("Alpha Vantage API key not configured")
    
    @property
    def source(self) -> DataSource:
        return DataSource.ALPHAVANTAGE
    
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
        """Parse fiscal date to period string (e.g., '2024-FY')."""
        if not date_str:
            return 'unknown'
        
        try:
            # Alpha Vantage uses YYYY-MM-DD format
            date = datetime.strptime(date_str, '%Y-%m-%d')
            # For annual reports, usually end in Q4 (Sept-Dec for most companies)
            return f"{date.year}-FY"
        except ValueError:
            return date_str
    
    def fetch_profile(self) -> Optional[CompanyProfile]:
        """Fetch company overview/profile."""
        data = self._make_request('OVERVIEW')
        
        if not data or 'Symbol' not in data:
            return None
        
        logger.info(f"Fetched company overview for {self.symbol} from Alpha Vantage")
        
        return CompanyProfile(
            std_symbol=self.symbol,
            std_company_name=TextFieldWithSource(
                value=data.get('Name'), 
                source='alphavantage'
            ),
            std_sector=TextFieldWithSource(
                value=data.get('Sector'),
                source='alphavantage'
            ),
            std_industry=TextFieldWithSource(
                value=data.get('Industry'),
                source='alphavantage'
            ),
            std_description=TextFieldWithSource(
                value=data.get('Description'),
                source='alphavantage'
            ),
            std_market_cap=self._create_field_with_source(data.get('MarketCapitalization')),
            std_beta=self._create_field_with_source(data.get('Beta')),
        )
    
    def fetch_income_statements(self) -> List[IncomeStatement]:
        """Fetch annual income statements."""
        data = self._make_request('INCOME_STATEMENT')
        
        if not data or 'annualReports' not in data:
            return []
        
        statements = []
        annual_reports = data.get('annualReports', [])
        
        logger.info(f"Fetched {len(annual_reports)} income statements for {self.symbol} from Alpha Vantage")
        
        for report in annual_reports[:5]:  # Limit to 5 years
            stmt = IncomeStatement(
                std_period=self._parse_period(report.get('fiscalDateEnding')),
                std_revenue=self._create_field_with_source(report.get('totalRevenue')),
                std_cost_of_revenue=self._create_field_with_source(
                    report.get('costOfRevenue') or report.get('costofGoodsAndServicesSold')
                ),
                std_gross_profit=self._create_field_with_source(report.get('grossProfit')),
                std_operating_expenses=self._create_field_with_source(report.get('operatingExpenses')),
                std_operating_income=self._create_field_with_source(report.get('operatingIncome')),
                std_pretax_income=self._create_field_with_source(report.get('incomeBeforeTax')),
                std_income_tax_expense=self._create_field_with_source(report.get('incomeTaxExpense')),
                std_net_income=self._create_field_with_source(report.get('netIncome')),
                std_ebitda=self._create_field_with_source(report.get('ebitda')),
                # EPS not directly in income statement from AV, would need company overview
            )
            statements.append(stmt)
        
        return statements
    
    def fetch_balance_sheets(self) -> List[BalanceSheet]:
        """Fetch annual balance sheets."""
        data = self._make_request('BALANCE_SHEET')
        
        if not data or 'annualReports' not in data:
            return []
        
        statements = []
        annual_reports = data.get('annualReports', [])
        
        logger.info(f"Fetched {len(annual_reports)} balance sheets for {self.symbol} from Alpha Vantage")
        
        for report in annual_reports[:5]:  # Limit to 5 years
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
                std_period=self._parse_period(report.get('fiscalDateEnding')),
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
            statements.append(stmt)
        
        return statements
    
    def fetch_cash_flows(self) -> List[CashFlow]:
        """Fetch annual cash flow statements."""
        data = self._make_request('CASH_FLOW')
        
        if not data or 'annualReports' not in data:
            return []
        
        statements = []
        annual_reports = data.get('annualReports', [])
        
        logger.info(f"Fetched {len(annual_reports)} cash flow statements for {self.symbol} from Alpha Vantage")
        
        for report in annual_reports[:5]:  # Limit to 5 years
            # Calculate free cash flow if not directly provided
            operating_cf = report.get('operatingCashflow')
            capex = report.get('capitalExpenditures')
            
            free_cash_flow = None
            if operating_cf and capex:
                try:
                    # CAPEX is usually negative, so add it
                    op_cf = float(operating_cf)
                    cap = float(capex)
                    # If capex is positive, subtract it; if negative, adding gives correct result
                    if cap > 0:
                        free_cash_flow = op_cf - cap
                    else:
                        free_cash_flow = op_cf + cap
                except (ValueError, TypeError):
                    pass
            
            stmt = CashFlow(
                std_period=self._parse_period(report.get('fiscalDateEnding')),
                std_operating_cash_flow=self._create_field_with_source(report.get('operatingCashflow')),
                std_investing_cash_flow=self._create_field_with_source(report.get('cashflowFromInvestment')),
                std_financing_cash_flow=self._create_field_with_source(report.get('cashflowFromFinancing')),
                std_capex=self._create_field_with_source(report.get('capitalExpenditures')),
                std_free_cash_flow=FieldWithSource(value=free_cash_flow, source='alphavantage') if free_cash_flow else None,
                std_dividends_paid=self._create_field_with_source(
                    report.get('dividendPayout') or report.get('dividendPayoutCommonStock')
                ),
            )
            statements.append(stmt)
        
        return statements


# Register this fetcher
FetcherRegistry.register(DataSource.ALPHAVANTAGE, AlphaVantageFetcher)

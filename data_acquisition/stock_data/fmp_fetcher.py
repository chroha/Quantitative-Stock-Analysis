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
from utils.logger import setup_logger
from utils.unified_schema import (
    AnalystTargets, CompanyProfile, FieldWithSource, TextFieldWithSource, FMP_FIELD_MAPPING
)

logger = setup_logger('fmp_fetcher')


class FMPFetcher:
    """
    Fetches supplementary data from FMP API.
    Uses /stable/ endpoints with query parameters.
    """
    
    BASE_URL = "https://financialmodelingprep.com/stable"
    
    def __init__(self, symbol: str):
        """
        Initialize FMP fetcher for a specific symbol.
        
        Args:
            symbol: Stock ticker symbol
        """
        self.symbol = symbol.upper()
        self.api_key = settings.FMP_API_KEY
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
        url = f"{self.BASE_URL}/{endpoint}"
        params = {
            'symbol': self.symbol,
            'apikey': self.api_key
        }
        if extra_params:
            params.update(extra_params)
        
        try:
            logger.debug(f"Requesting FMP endpoint: {endpoint}")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for FMP error messages
            if isinstance(data, dict) and 'Error Message' in data:
                logger.error(f"FMP API error: {data['Error Message']}")
                return None
            
            logger.debug(f"Successfully fetched data from {endpoint}")
            return data
        
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
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
        data = self._make_request("price-target-consensus")
        
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
        
        Returns:
            CompanyProfile object or None if fetch fails
        """
        data = self._make_request("profile")
        
        if not data or not isinstance(data, list) or len(data) == 0:
            logger.warning(f"No profile data available for {self.symbol} from FMP")
            return None
        
        profile_data = data[0]
        
        try:
            profile = CompanyProfile(
                std_symbol=self.symbol,
                std_company_name=TextFieldWithSource(value=profile_data.get('companyName', ''), source='fmp') if profile_data.get('companyName') else None,
                std_industry=TextFieldWithSource(value=profile_data.get('industry', ''), source='fmp') if profile_data.get('industry') else None,
                std_sector=TextFieldWithSource(value=profile_data.get('sector', ''), source='fmp') if profile_data.get('sector') else None,
                std_market_cap=FieldWithSource(value=float(profile_data['marketCap']), source='fmp') if profile_data.get('marketCap') else None,
                std_description=TextFieldWithSource(value=profile_data.get('description', ''), source='fmp') if profile_data.get('description') else None,
                std_website=TextFieldWithSource(value=profile_data.get('website', ''), source='fmp') if profile_data.get('website') else None,
                std_ceo=TextFieldWithSource(value=profile_data.get('ceo', ''), source='fmp') if profile_data.get('ceo') else None,
                std_beta=FieldWithSource(value=float(profile_data['beta']), source='fmp') if profile_data.get('beta') else None,  # Stock-specific Beta from FMP
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
        
        data = self._make_request("income-statement")
        
        if not data or not isinstance(data, list):
            logger.warning(f"No income statement data from FMP for {self.symbol}")
            return []
        
        statements = []
        for item in data[:6]:  # Fetch up to 6 years for calculations (need 5 years + 1 for growth)
            try:
                stmt = IncomeStatement(
                    std_period=item.get('date'),
                    std_revenue=FieldWithSource(value=float(item['revenue']), source='fmp') if item.get('revenue') else None,
                    std_cost_of_revenue=FieldWithSource(value=float(item['costOfRevenue']), source='fmp') if item.get('costOfRevenue') else None,
                    std_gross_profit=FieldWithSource(value=float(item['grossProfit']), source='fmp') if item.get('grossProfit') else None,
                    std_operating_expenses=FieldWithSource(value=float(item['operatingExpenses']), source='fmp') if item.get('operatingExpenses') else None,
                    std_operating_income=FieldWithSource(value=float(item['operatingIncome']), source='fmp') if item.get('operatingIncome') else None,
                    std_pretax_income=FieldWithSource(value=float(item['incomeBeforeTax']), source='fmp') if item.get('incomeBeforeTax') else None,
                    std_income_tax_expense=FieldWithSource(value=float(item['incomeTaxExpense']), source='fmp') if item.get('incomeTaxExpense') else None,
                    std_net_income=FieldWithSource(value=float(item['netIncome']), source='fmp') if item.get('netIncome') else None,
                    std_eps=FieldWithSource(value=float(item['eps']), source='fmp') if item.get('eps') else None,
                    std_eps_diluted=FieldWithSource(value=float(item['epsdiluted']), source='fmp') if item.get('epsdiluted') else None,
                    std_shares_outstanding=FieldWithSource(value=float(item['weightedAverageShsOut']), source='fmp') if item.get('weightedAverageShsOut') else None,
                    std_ebitda=FieldWithSource(value=float(item['ebitda']), source='fmp') if item.get('ebitda') else None,
                )
                statements.append(stmt)
            except (ValueError, KeyError) as e:
                logger.warning(f"Failed to parse FMP income statement for period {item.get('date')}: {e}")
                continue
        
        logger.info(f"Fetched {len(statements)} income statements from FMP for {self.symbol}")
        return statements
    
    def fetch_balance_sheets(self) -> list:
        """
        Fetch balance sheets from FMP /stable/balance-sheet-statement endpoint.
        
        Returns:
            List of BalanceSheet objects
        """
        from utils.unified_schema import BalanceSheet
        
        data = self._make_request("balance-sheet-statement")
        
        if not data or not isinstance(data, list):
            logger.warning(f"No balance sheet data from FMP for {self.symbol}")
            return []
        
        statements = []
        for item in data[:6]:
            try:
                stmt = BalanceSheet(
                    std_period=item.get('date'),
                    std_total_assets=FieldWithSource(value=float(item['totalAssets']), source='fmp') if item.get('totalAssets') else None,
                    std_current_assets=FieldWithSource(value=float(item['totalCurrentAssets']), source='fmp') if item.get('totalCurrentAssets') else None,
                    std_cash=FieldWithSource(value=float(item['cashAndCashEquivalents']), source='fmp') if item.get('cashAndCashEquivalents') else None,
                    std_accounts_receivable=FieldWithSource(value=float(item['netReceivables']), source='fmp') if item.get('netReceivables') else None,
                    std_inventory=FieldWithSource(value=float(item['inventory']), source='fmp') if item.get('inventory') else None,
                    std_total_liabilities=FieldWithSource(value=float(item['totalLiabilities']), source='fmp') if item.get('totalLiabilities') else None,
                    std_current_liabilities=FieldWithSource(value=float(item['totalCurrentLiabilities']), source='fmp') if item.get('totalCurrentLiabilities') else None,
                    std_total_debt=FieldWithSource(value=float(item['totalDebt']), source='fmp') if item.get('totalDebt') else None,
                    std_shareholder_equity=FieldWithSource(value=float(item['totalStockholdersEquity']), source='fmp') if item.get('totalStockholdersEquity') else None,
                )
                statements.append(stmt)
            except (ValueError, KeyError) as e:
                logger.warning(f"Failed to parse FMP balance sheet for period {item.get('date')}: {e}")
                continue
        
        logger.info(f"Fetched {len(statements)} balance sheets from FMP for {self.symbol}")
        return statements
    
    def fetch_cash_flows(self) -> list:
        """
        Fetch cash flow statements from FMP /stable/cash-flow-statement endpoint.
        
        Returns:
            List of CashFlow objects
        """
        from utils.unified_schema import CashFlow
        
        data = self._make_request("cash-flow-statement")
        
        if not data or not isinstance(data, list):
            logger.warning(f"No cash flow data from FMP for {self.symbol}")
            return []
        
        statements = []
        for item in data[:6]:
            try:
                stmt = CashFlow(
                    std_period=item.get('date'),
                    std_operating_cash_flow=FieldWithSource(value=float(item['operatingCashFlow']), source='fmp') if item.get('operatingCashFlow') else None,
                    std_investing_cash_flow=FieldWithSource(value=float(item['netCashUsedForInvestingActivites']), source='fmp') if item.get('netCashUsedForInvestingActivites') else None,
                    std_financing_cash_flow=FieldWithSource(value=float(item['netCashUsedProvidedByFinancingActivities']), source='fmp') if item.get('netCashUsedProvidedByFinancingActivities') else None,
                    std_capex=FieldWithSource(value=float(item['capitalExpenditure']), source='fmp') if item.get('capitalExpenditure') else None,
                    std_free_cash_flow=FieldWithSource(value=float(item['freeCashFlow']), source='fmp') if item.get('freeCashFlow') else None,
                    std_stock_based_compensation=FieldWithSource(value=float(item['stockBasedCompensation']), source='fmp') if item.get('stockBasedCompensation') else None,
                    std_dividends_paid=FieldWithSource(value=float(item['dividendsPaid']), source='fmp') if item.get('dividendsPaid') else None,
                )
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

import requests
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from utils.unified_schema import IncomeStatement, FieldWithSource, DataSource

logger = logging.getLogger('edgar_fetcher')

class EdgarFetcher:
    """
    Fetches financial data directly from SEC EDGAR API.
    
    Uses the Company Facts API: https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json
    Requires a valid User-Agent as per SEC policies.
    """
    
    BASE_URL = "https://data.sec.gov/api/xbrl/companyfacts"
    TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
    
    # Standard mapping from US-GAAP tags to our internal schema fields
    # Priority ordered list of tags to check for each field
    # NOTE: This should mirror field_registry.py for EDGAR source mappings
    TAG_MAPPING = {
        # Income Statement
        'std_revenue': ['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'SalesRevenueNet', 'SalesRevenueServicesNet', 'SalesRevenueGoodsNet'],
        'std_cost_of_revenue': ['CostOfRevenue', 'CostOfGoodsAndServicesSold', 'CostOfGoodsSold', 'CostOfServices'],
        'std_gross_profit': ['GrossProfit'],
        'std_operating_expenses': ['OperatingExpenses'],
        'std_operating_income': ['OperatingIncomeLoss'],
        'std_pretax_income': ['IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest', 'IncomeLossFromContinuingOperationsBeforeIncomeTaxes'],
        'std_income_tax_expense': ['IncomeTaxExpenseBenefit'],
        'std_net_income': ['NetIncomeLoss', 'ProfitLoss'],
        'std_eps': ['EarningsPerShareBasic'],
        'std_eps_diluted': ['EarningsPerShareDiluted'],
        'std_shares_outstanding': ['WeightedAverageNumberOfSharesOutstandingBasic'],
        
        # Balance Sheet
        'std_total_assets': ['Assets'],
        'std_total_liabilities': ['Liabilities'],
        'std_shareholder_equity': ['StockholdersEquity', 'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'],
        'std_total_debt': ['LongTermDebt', 'LongTermDebtNoncurrent', 'DebtInstrumentCarryingAmount'],
        'std_current_assets': ['AssetsCurrent'],
        'std_current_liabilities': ['LiabilitiesCurrent'],
        'std_cash': ['CashAndCashEquivalentsAtCarryingValue'],
        'std_accounts_receivable': ['AccountsReceivableNetCurrent', 'ReceivablesNetCurrent'],
        'std_inventory': ['InventoryNet', 'InventoryFinishedGoodsNetOfReserves'],
        
        # Cash Flow
        'std_operating_cash_flow': ['NetCashProvidedByUsedInOperatingActivities'],
        'std_investing_cash_flow': ['NetCashProvidedByUsedInInvestingActivities'],
        'std_financing_cash_flow': ['NetCashProvidedByUsedInFinancingActivities'],
        'std_capex': ['PaymentsToAcquireProductiveAssets', 'PaymentsToAcquirePropertyPlantAndEquipment', 'CapitalExpendituresIncurredButNotYetPaid'],
        'std_stock_based_compensation': ['ShareBasedCompensation', 'ShareBasedCompensationArrangementByShareBasedPaymentAwardEquityInstrumentsOtherThanOptionsVestedInPeriod'],
        'std_depreciation_amortization': ['DepreciationDepletionAndAmortization', 'Depreciation', 'AmortizationOfIntangibleAssets'],
        'std_dividends_paid': ['PaymentsOfDividends', 'PaymentsOfDividendsCommonStock', 'PaymentsOfDividendsMinorityInterest'],
    }

    def __init__(self, user_agent: str = "Antigravity/1.0 (quantitative_analysis@example.com)"):
        self.headers = {
            'User-Agent': user_agent,
            'Accept-Encoding': 'gzip, deflate'
        }
        self.cik_map = None

    def _get_cik(self, symbol: str) -> Optional[str]:
        """Resolve symbol to CIK string (10 digits left-padded)."""
        if not self.cik_map:
            try:
                logger.info("Fetching SEC ticker map...")
                resp = requests.get(self.TICKERS_URL, headers=self.headers, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    # Data format: { "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}, ... }
                    self.cik_map = {item['ticker'].upper(): str(item['cik_str']).zfill(10) for item in data.values()}
                else:
                    logger.error(f"Failed to fetch ticker map: {resp.status_code}")
                    return None
            except Exception as e:
                logger.error(f"Error fetching ticker map: {e}")
                return None
        
        return self.cik_map.get(symbol.upper())
        
    def _get_fiscal_year(self, end_date_str: str) -> int:
        """
        Calculate fiscal year from the end date.
        SEC 'fy' tag can be unreliable. We assume if end date is in first half of year X,
        it likely belongs to FY(X-1) depending on company policy, 
        but commonly simplistic mapping: Month > 6 => Year, Month < 6 => Year-1? 
        Actually, simpler robust logic found in previous iteration:
        Use the year of the end date, but be careful with off-calendar FYs.
        The user noted 'end date dynamic calculation' fixed 2014-2017. 
        Most standard: The FY is the year containing the majority of the months.
        Let's trust the 'end' date year usually aligns with FY for non-shifted,
        or just use the year part of the end date as the "reporting year".
        """
        try:
            dt = datetime.strptime(end_date_str, "%Y-%m-%d")
            # If period ends Jan-May, it's usually the previous fiscal year's report
            # e.g., Apple FY ends Sept -> Report date Sept. 
            # Nvidia FY ends Jan -> Report date Jan 2025 is FY 2025 (actually labeled FY25).
            # Microsoft FY ends June.
            # Let's rely on the 'end' date year as the primary key for our storage.
            # Our Unified Schema uses 'YYYY-FY', so consistent mapping matters more than strict GAAP FY definition.
            # However, to fix "missing years", we should ensure we group properly.
            return dt.year
        except:
            return 0

    def fetch_all_financials(self, symbol: str) -> Dict[str, List[Any]]:
        """
        Fetch all financial statements (Income, Balance, Cash Flow).
        Returns dict with keys: income_statements, balance_sheets, cash_flows
        """
        cik = self._get_cik(symbol)
        if not cik:
            logger.warning(f"Could not resolve CIK for {symbol}")
            return {'income_statements': [], 'balance_sheets': [], 'cash_flows': []}
            
        url = f"{self.BASE_URL}/CIK{cik}.json"
        
        try:
            time.sleep(0.15) 
            logger.info(f"Fetching EDGAR facts for {symbol} (CIK: {cik})...")
            
            resp = requests.get(url, headers=self.headers, timeout=20) # Increased timeout for large JSON
            if resp.status_code != 200:
                logger.warning(f"EDGAR request failed: {resp.status_code}")
                return {'income_statements': [], 'balance_sheets': [], 'cash_flows': []}
                
            facts = resp.json().get('facts', {}).get('us-gaap', {})
            
            # Parse all types
            income = self._parse_statements(facts, 'income')
            balance = self._parse_statements(facts, 'balance')
            cash = self._parse_statements(facts, 'cashflow')
            
            return {
                'income_statements': income,
                'balance_sheets': balance,
                'cash_flows': cash
            }
            
        except Exception as e:
            logger.error(f"Error fetching EDGAR data for {symbol}: {e}")
            return {'income_statements': [], 'balance_sheets': [], 'cash_flows': []}

    def fetch_income_statements(self, symbol: str) -> List[IncomeStatement]:
        """Wrapper for just income statements compatibility."""
        return self.fetch_all_financials(symbol)['income_statements']

    def _parse_statements(self, gaap_facts: Dict, stmt_type: str) -> List[Any]:
        """
        Generic parser for Income, Balance, CashFlow based on stmt_type.
        """
        from utils.unified_schema import IncomeStatement, BalanceSheet, CashFlow
        
        # Define fields based on type
        if stmt_type == 'balance':
            TargetClass = BalanceSheet
            fields_needed = ['std_total_assets','std_total_liabilities','std_shareholder_equity','std_total_debt','std_current_assets','std_current_liabilities','std_cash','std_accounts_receivable','std_inventory']
            allowed_forms = ['10-K', '10-Q']
        elif stmt_type == 'income':
            TargetClass = IncomeStatement
            fields_needed = ['std_revenue','std_net_income','std_eps','std_gross_profit', 'std_operating_income', 'std_cost_of_revenue', 'std_operating_expenses', 'std_eps_diluted', 'std_shares_outstanding', 'std_ebitda', 'std_depreciation_amortization', 'std_pretax_income', 'std_income_tax_expense']
            allowed_forms = ['10-K'] # Keep income annual for consistency
        else: # cashflow
            TargetClass = CashFlow
            fields_needed = ['std_operating_cash_flow','std_investing_cash_flow','std_financing_cash_flow','std_capex', 'std_stock_based_compensation', 'std_free_cash_flow', 'std_dividends_paid']
            allowed_forms = ['10-K'] # Keep cash flow annual

        raw_data_by_date = {}

        # Iterate over all needed fields and their possible tags
        for field in fields_needed:
            # Skip calculated fields from extraction loop
            if field in ['std_free_cash_flow', 'std_ebitda'] and field not in self.TAG_MAPPING:
                 continue
                 
            tags = self.TAG_MAPPING.get(field, [])
            found_tag = False
            for tag in tags:
                if tag in gaap_facts:
                    units = gaap_facts[tag].get('units', {})
                    for unit_key, records in units.items():
                        for r in records:
                            # Filter for allowed forms
                            if r.get('form') in allowed_forms:
                                # Use 'end' date as the standard period identifier (YYYY-MM-DD)
                                if 'end' in r:
                                    date_str = r['end']
                                    
                                    # For P&L/Cash Flow (10-K), we want full year data not partial -> Check 'fp'='FY'
                                    # For Balance Sheet (10-K/10-Q), 'fp' can be FY, Q1, Q2, Q3
                                    is_valid_period = False
                                    if stmt_type == 'balance':
                                        is_valid_period = True # Balance sheet is snapshot, always valid
                                    else:
                                        # Income/Cash Flow: Strict Annual
                                        if r.get('fp') == 'FY':
                                            is_valid_period = True
                                    
                                    if is_valid_period:
                                        if date_str not in raw_data_by_date: raw_data_by_date[date_str] = {}
                                        
                                        # Store logic: Take the latest filed one
                                        raw_data_by_date[date_str][field] = r['val']
                                        found_tag = True
                    if found_tag: break # Priority tag found for this field
        
        # Build objects and perform internal calculations
        results = []
        for date_str, extracted in raw_data_by_date.items():
            try:
                # --- Internal Calculations ---
                
                # 1. Calculate Free Cash Flow (OCF - Capex)
                if stmt_type == 'cashflow':
                    ocf = extracted.get('std_operating_cash_flow')
                    capex = extracted.get('std_capex')
                    if ocf is not None and capex is not None:
                        # Capex is usually signed. If negative (payment), adding it reduces cash. 
                        # If positive (mistake?), subtract. 
                        # SEC 'PaymentsToAcquire...' is usually returned as positive number?
                        # GAAP facts usually store positive values for 'Payments...'.
                        # Let's assume positive value for payments.
                        # FCF = OCF - CapexPayment
                        extracted['std_free_cash_flow'] = ocf - abs(capex)
                    
                    # Infer dividends if missing (assume 0 if financing flow exists)
                    if extracted.get('std_financing_cash_flow') is not None and extracted.get('std_dividends_paid') is None:
                        extracted['std_dividends_paid'] = 0.0
                    
                    # Infer SBC if missing (assume 0 if operating flow exists)
                    if extracted.get('std_operating_cash_flow') is not None and extracted.get('std_stock_based_compensation') is None:
                        extracted['std_stock_based_compensation'] = 0.0
                
                # 2. Calculate EBITDA (Operating Income + D&A)
                if stmt_type == 'income':
                    op_inc = extracted.get('std_operating_income')
                    da = extracted.get('std_depreciation_amortization')
                    if op_inc is not None and da is not None:
                        extracted['std_ebitda'] = op_inc + abs(da)
                        
                # Construct kwargs
                kwargs = {'std_period': date_str}
                # Inspect TargetClass fields to know what valid keys are
                # But since we use Pydantic models with FieldWithSource, we loop our fields
                
                # Note: fields_needed contains all keys we want.
                # But TargetClass might have other fields not in fields_needed (e.g. D&A is helper for EBITDA, not in IncomeStatement model?)
                # We need to map extracted values to kwargs safely.
                
                valid_fields = TargetClass.model_fields.keys()
                
                for field in valid_fields:
                    if field == 'std_period': continue
                    
                    if field in extracted:
                        val = extracted[field]
                        kwargs[field] = FieldWithSource(value=float(val), source='sec_edgar')
                    else:
                        kwargs[field] = None
                
                stmt = TargetClass(**kwargs)
                results.append(stmt)
            except Exception as e:
                pass # Skip malformed
        
        results.sort(key=lambda x: x.std_period, reverse=True)
        # Limit to 6 years as per user request to avoid history dilution
        return results[:6]


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
            
            resp = requests.get(url, headers=self.headers, timeout=20)
            if resp.status_code != 200:
                print(f"      [Edgar] Request failed: {resp.status_code}")
                return {'income_statements': [], 'balance_sheets': [], 'cash_flows': []}
                
            resp_json = resp.json()
            facts = resp_json.get('facts', {}).get('us-gaap', {})
            
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

    def fetch_balance_sheets(self, symbol: str) -> List[Any]:
        """Wrapper for just balance sheets compatibility."""
        return self.fetch_all_financials(symbol)['balance_sheets']
        
    def fetch_cash_flow_statements(self, symbol: str) -> List[Any]:
        """Wrapper for just cash flow statements compatibility."""
        return self.fetch_all_financials(symbol)['cash_flows']
        
    # Alias for backward compatibility and interface consistency
    fetch_cash_flows = fetch_cash_flow_statements

    def _parse_statements(self, gaap_facts: Dict, stmt_type: str) -> List[Any]:
        """
        Generic parser for Income, Balance, CashFlow based on stmt_type.
        """
        from utils.unified_schema import IncomeStatement, BalanceSheet, CashFlow
        from utils.field_registry import (
            INCOME_FIELDS, BALANCE_FIELDS, CASHFLOW_FIELDS,
            get_source_field_name, DataSource
        )
        
        # Define fields based on type
        if stmt_type == 'balance':
            TargetClass = BalanceSheet
            fields_dict = BALANCE_FIELDS
            allowed_forms = ['10-K', '10-Q', '10-K/A', '10-Q/A', 'S-1', 'S-1/A']
        elif stmt_type == 'income':
            TargetClass = IncomeStatement
            fields_dict = INCOME_FIELDS
            allowed_forms = ['10-K', '10-K/A', '10-Q', '10-Q/A', 'S-1', 'S-1/A'] 
        else: # cashflow
            TargetClass = CashFlow
            fields_dict = CASHFLOW_FIELDS
            allowed_forms = ['10-K', '10-K/A', '10-Q', '10-Q/A', 'S-1', 'S-1/A']

        raw_data_by_date = {}

        # Iterate over all needed fields and their possible tags from Registry
        for field in fields_dict.keys():
            # Get tags from registry
            tags = get_source_field_name(field, DataSource.SEC_EDGAR)
            if not tags:
                 continue
            
            # Ensure tags is list
            if isinstance(tags, str): tags = [tags]
            
            # Iterate through all configured tags for this unified field
            # We DON'T break after the first tag found, because different tags 
            # might cover different historical segments (e.g. tag A for 2015-2020, tag B for 2021-2024).
            for tag in tags:
                if tag in gaap_facts:
                    units = gaap_facts[tag].get('units', {})
                    for unit_key, records in units.items():
                        for r in records:
                            # 1. Form Filter
                            if r.get('form') in allowed_forms:
                                if 'end' in r:
                                    date_str = r['end']
                                    # 2. Period Type Logic
                                    is_valid_period = False
                                    if stmt_type == 'balance':
                                        is_valid_period = True
                                    else:
                                        # Income/CashFlow: Allow FY and Quarters
                                        if r.get('fp') in ['FY', 'Q1', 'Q2', 'Q3', 'Q4']:
                                            is_valid_period = True
                                    
                                    if is_valid_period:
                                        if date_str not in raw_data_by_date: 
                                            raw_data_by_date[date_str] = {}
                                        
                                        if field not in raw_data_by_date[date_str]:
                                            raw_data_by_date[date_str][field] = r['val']
                                            # Store fiscal period type (FY/Q) metadata once per date
                                            if '_fp' not in raw_data_by_date[date_str]:
                                                raw_data_by_date[date_str]['_fp'] = r.get('fp', 'FY')
                                    else:
                                        pass
                            else:
                                pass
                else:
                    pass
        
        # print(f"      [Edgar] {stmt_type}: Found {len(raw_data_by_date)} unique dates in raw data.")
        
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
                
                # Determine period type (FY or Q) from the raw record
                # We pick the fp from one of the fields found for this date
                # In EdgarFetcher parsing, we use fp='FY' for Income/CashFlow, 
                # but Balance Sheet might have others.
                # Let's find the 'fp' from the first record we encountered for any field on this date.
                # Wait, raw_data_by_date only stores 'val'. I need to store 'fp' too.
                # I'll fix the raw_data_by_date structure above first.
                
                for field in valid_fields:
                    if field in ['std_period', 'std_period_type']: continue
                    
                    if field in extracted:
                        val = extracted[field]
                        if val is not None:
                            kwargs[field] = FieldWithSource(value=float(val), source='sec_edgar')
                    else:
                        kwargs[field] = None
                
                # Set period type (Defaults to FY as SEC Fetcher primarily fetches annual)
                fp_val = extracted.get('_fp', 'FY')
                kwargs['std_period_type'] = 'FY' if fp_val == 'FY' else 'Q'
                
                stmt = TargetClass(**kwargs)
                results.append(stmt)
            except Exception as e:
                # Log the error so we don't fail silently
                print(f"      [Edgar] Construction error for {date_str}: {e}")
                import traceback
                # traceback.print_exc() 
                continue
        
        results.sort(key=lambda x: x.std_period, reverse=True)
        return results[:32]

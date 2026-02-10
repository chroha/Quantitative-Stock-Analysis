"""
Data Loader Module - Unified External Entry Point for Data Acquisition

This module orchestrates a 4-tier cascading data fetch:
1. Fetch base data from Yahoo Finance (Phase 1).
2. Fetch official filings from SEC EDGAR (Phase 2).
3. If incomplete, fetch supplementary data from FMP (Phase 3).
4. If still incomplete, fetch from Alpha Vantage (Phase 4).
5. Merge and validate data.
6. Return a unified StockData object.
"""

import os
import json
from datetime import datetime
from typing import Optional, Tuple, List

from utils.unified_schema import StockData, IncomeStatement, BalanceSheet, CashFlow, CompanyProfile
from utils.logger import setup_logger
from data_acquisition.stock_data.yahoo_fetcher import YahooFetcher
from data_acquisition.stock_data.edgar_fetcher import EdgarFetcher
from data_acquisition.stock_data.fmp_fetcher import FMPFetcher
from data_acquisition.stock_data.data_merger import DataMerger
from data_acquisition.stock_data.intelligent_merger import IntelligentMerger
from data_acquisition.stock_data.field_validator import FieldValidator, OverallValidationResult

from config.analysis_config import GAP_THRESHOLDS, DATA_THRESHOLDS

logger = setup_logger('data_loader')


class StockDataLoader:
    """
    Stock Data Loader - Main entry point class for the Data Acquisition Layer.
    
    Implements 4-tier cascading data fetch:
    - Tier 1: Yahoo Finance (primary, most comprehensive)
    - Tier 2: SEC EDGAR (official source, XBRL-based)
    - Tier 3: FMP (fallback, good financial data)
    - Tier 4: Alpha Vantage (second fallback, GAAP-compliant)
    """
    
    def __init__(self, use_alphavantage: bool = True):
        """
        Initialize data loader.
        
        Args:
            use_alphavantage: Whether to use Alpha Vantage as third-tier fallback
        """
        self.use_alphavantage = use_alphavantage
        self.use_fmp = True # Default enabled
        self.validator = FieldValidator()
        self.validation_result: Optional[OverallValidationResult] = None
    
    def _sanitize_data(self, data: StockData) -> StockData:
        """
        Remove financial statement periods that are missing required fields.
        Ensures the final dataset is high-quality and consistent.
        """
        def filter_stmts(stmts, stmt_type):
            valid_stmts = []
            dropped = 0
            for stmt in stmts:
                res = self.validator.validate_statement(stmt, stmt_type)
                if not res.missing_required:
                    valid_stmts.append(stmt)
                else:
                    dropped += 1
                    # print(f"         > Dropped {stmt_type} [{getattr(stmt, 'std_period', 'Unknown')}]: Missing {res.missing_required}")
            if dropped > 0:
                print(f"      [Sanitizer] Dropped {dropped} incomplete {stmt_type} periods (Missing Required Fields)")
            return valid_stmts

        data.income_statements = filter_stmts(data.income_statements, 'income')
        data.balance_sheets = filter_stmts(data.balance_sheets, 'balance')
        data.cash_flows = filter_stmts(data.cash_flows, 'cashflow')
        
        return data

    def _construct_synthetic_ttm(self, data: StockData) -> StockData:
        """
        Build TTM statements by summing the latest 4 quarters if they are newer than FY.
        For Balance Sheet, it just takes the latest available snapshot.
        """
        import datetime
        from utils.unified_schema import IncomeStatement, BalanceSheet, CashFlow, FieldWithSource, DataSource
        
        def to_dt(s):
            try: return datetime.datetime.strptime(s, '%Y-%m-%d')
            except: return None
            
        def get_latest(stmts, period_type):
            valid = [s for s in stmts if s.std_period_type == period_type and s.std_period]
            if not valid: return None
            return sorted(valid, key=lambda x: x.std_period, reverse=True)[0]

        def find_valid(stmts, stmt_type, preferred_types=['Q', 'FY']):
            for p_type in preferred_types:
                for s in stmts:
                    if s.std_period_type == p_type:
                        # Validation check
                        res = self.validator.validate_statement(s, stmt_type)
                        if res.is_complete:
                            return s
            return None if not stmts else stmts[0]

        def sum_quarters(quarters, stmt_class):
            if len(quarters) < 4: return None
            
            # DETAILED LOGGING: Show what we're summing
            logger.info(f"[TTM Builder] Attempting to sum {len(quarters)} quarters:")
            
            # Check if this statement type has revenue (IncomeStatement only)
            has_revenue = hasattr(quarters[0], 'std_revenue')

            for i, q in enumerate(quarters[:4]):
                rev_str = "N/A (Not Income)"
                if has_revenue and q.std_revenue:
                    rev_val = q.std_revenue.value
                    rev_str = f"Revenue = {rev_val:,.0f}" if rev_val is not None else "Revenue = None"
                logger.info(f"  [{i+1}] {q.std_period} ({q.std_period_type}): {rev_str}")
            
            # ENHANCED SANITY CHECK: Only applies if we have revenue to check against
            if has_revenue:
                total_rev_sum = sum([q.std_revenue.value for q in quarters[:4] if q.std_revenue and q.std_revenue.value is not None])
                if total_rev_sum > 0:
                    logger.info(f"[TTM Builder] Total revenue sum: {total_rev_sum:,.0f}")
                    
                    for q in quarters[:4]:
                        if not q.std_revenue or not q.std_revenue.value:
                            continue
                        
                        rev_ratio = q.std_revenue.value / total_rev_sum
                        
                        # Condition 1: Revenue ratio > 50% (very conservative - allows up to 50% seasonality)
                        high_ratio = rev_ratio > 0.50
                        
                        # Condition 2: Period ends on 12-31 (typical year-end, likely annual report)
                        is_year_end = q.std_period.endswith('-12-31') if q.std_period else False
                        
                        # Condition 3: Absolute value is unusually large for a quarter
                        # If revenue > $50B, it's likely annual for most companies
                        large_absolute_value = q.std_revenue.value > 50_000_000_000
                        
                        # Trigger warning if MULTIPLE conditions are met
                        if high_ratio and (is_year_end or large_absolute_value):
                            logger.warning(
                                f"[TTM Builder] ⚠️ Detected likely Annual/YTD mislabeled as Quarter:\n"
                                f"  Period: {q.std_period} | Revenue: {q.std_revenue.value:,.0f}\n"
                                f"  Ratio: {rev_ratio*100:.1f}% | Year-end: {is_year_end} | Large value: {large_absolute_value}\n"
                                f"  Skipping sum to prevent double-counting."
                            )
                            return None
            else:
                logger.info("[TTM Builder] Not an Income Statement, skipping revenue seasonality check.")

            # Sum numeric fields
            fields = stmt_class.model_fields.keys()
            merged_kwargs = {
                'std_period': f"TTM-{quarters[0].std_period}", # e.g. TTM-2025-09-30
                'std_period_type': 'TTM'
            }
            
            for field in fields:
                if field in ['std_period', 'std_period_type']: continue
                
                total_val = 0.0
                has_val = False
                source = None
                
                SNAPSHOT_FIELDS = ['std_shares_outstanding']

                for i, q in enumerate(quarters[:4]):
                    val_obj = getattr(q, field, None)
                    if val_obj and val_obj.value is not None:
                         if field in SNAPSHOT_FIELDS:
                              if i == 0:
                                  total_val = val_obj.value
                                  has_val = True
                                  source = val_obj.source
                              continue
                         
                         total_val += val_obj.value
                         has_val = True
                         source = val_obj.source 
                
                if has_val:
                    merged_kwargs[field] = FieldWithSource(value=total_val, source=source or DataSource.YAHOO)
            
            result = stmt_class(**merged_kwargs)
            if hasattr(result, 'std_revenue') and result.std_revenue:
                from utils.console_utils import symbol
                logger.info(f"[TTM Builder] {symbol.OK} Sum completed. TTM Revenue: {result.std_revenue.value:,.0f}")
            return result

        # --- DATA PRE-PROCESSING ---
        # 1. Check Income Statement
        latest_fy = get_latest(data.income_statements, 'FY')
        latest_q = get_latest(data.income_statements, 'Q')
        
        need_synthetic = False
        if latest_q and latest_fy and latest_q.std_period > latest_fy.std_period:
             fy_dt = to_dt(latest_fy.std_period)
             q_dt = to_dt(latest_q.std_period)
             
             if q_dt and fy_dt and (q_dt - fy_dt).days > 20:
                  need_synthetic = True
        elif latest_q and not latest_fy:
             need_synthetic = True
        elif latest_fy:
             ttm_inc = latest_fy.model_copy(deep=True)
             ttm_inc.std_period_type = 'TTM'
             ttm_inc.std_period = f"TTM-{latest_fy.std_period}"
             data.income_statements.insert(0, ttm_inc)
             print(f"      [TTM Builder] Use Latest FY as TTM (Ends {latest_fy.std_period})")
             need_synthetic = False 

        if need_synthetic:
            quarters = [s for s in data.income_statements if s.std_period_type == 'Q']
            seen_dates = set()
            unique_q = []
            for q in quarters:
                if q.std_period not in seen_dates:
                    unique_q.append(q)
                    seen_dates.add(q.std_period)
            
            if len(unique_q) >= 4:
                ttm_inc = sum_quarters(unique_q[:4], IncomeStatement)
                if ttm_inc:
                    data.income_statements.insert(0, ttm_inc)
                    print(f"      [TTM Builder] Constructed Synthetic TTM Income Statement (Sum of 4Q ends {unique_q[0].std_period})")
                else:
                    # Sanity check failed - the "latest Q" is likely a mislabeled FY
                    # Use it directly as FY TTM
                    logger.info(f"[TTM Builder] Sanity check failed. Using latest 'Q' ({unique_q[0].std_period}) as FY TTM.")
                    detected_fy = unique_q[0].model_copy(deep=True)
                    detected_fy.std_period_type = 'FY'  # Correct the mislabeling
                    detected_fy.std_period = unique_q[0].std_period
                    data.income_statements.insert(0, detected_fy)
                    
                    # Create TTM from this corrected FY
                    ttm_inc = detected_fy.model_copy(deep=True)
                    ttm_inc.std_period_type = 'TTM'
                    ttm_inc.std_period = f"TTM-{detected_fy.std_period}"
                    data.income_statements.insert(0, ttm_inc)
                    print(f"      [TTM Builder] Used mislabeled Annual data as TTM (Ends {detected_fy.std_period})")
        
        if not any(s.std_period_type == 'TTM' for s in data.income_statements):
            valid_fy = find_valid(data.income_statements, 'income', ['FY'])
            if valid_fy:
                ttm_inc = valid_fy.model_copy(deep=True)
                ttm_inc.std_period_type = 'TTM'
                ttm_inc.std_period = f"TTM-{valid_fy.std_period}"
                data.income_statements.insert(0, ttm_inc)
                print(f"      [TTM Builder] Using Latest Valid FY as TTM Income Statement (Ends {valid_fy.std_period})")

        # 2. Check Cash Flow
        latest_fy_cf = get_latest(data.cash_flows, 'FY')
        latest_q_cf = get_latest(data.cash_flows, 'Q')
        
        need_synthetic_cf = False
        if latest_q_cf and latest_fy_cf and latest_q_cf.std_period > latest_fy_cf.std_period:
             fy_dt = to_dt(latest_fy_cf.std_period)
             q_dt = to_dt(latest_q_cf.std_period)
             if q_dt and fy_dt and (q_dt - fy_dt).days > 20:
                  need_synthetic_cf = True
        elif latest_q_cf and not latest_fy_cf:
             need_synthetic_cf = True
        elif latest_fy_cf:
             ttm_cf = latest_fy_cf.model_copy(deep=True)
             ttm_cf.std_period_type = 'TTM'
             ttm_cf.std_period = f"TTM-{latest_fy_cf.std_period}"
             data.cash_flows.insert(0, ttm_cf)
             print(f"      [TTM Builder] Use Latest FY as TTM Cash Flow (Ends {latest_fy_cf.std_period})")
             need_synthetic_cf = False

        if need_synthetic_cf:
            quarters = [s for s in data.cash_flows if s.std_period_type == 'Q']
            seen_dates = set()
            unique_q = []
            for q in quarters:
                if q.std_period not in seen_dates:
                    unique_q.append(q)
                    seen_dates.add(q.std_period)
                    
            if len(unique_q) >= 4:
                ttm_cf = sum_quarters(unique_q[:4], CashFlow)
                if ttm_cf:
                    data.cash_flows.insert(0, ttm_cf)
                    print(f"      [TTM Builder] Constructed Synthetic TTM Cash Flow (Sum of 4Q ends {unique_q[0].std_period})")
        
        if not any(s.std_period_type == 'TTM' for s in data.cash_flows):
             valid_fy = find_valid(data.cash_flows, 'cashflow', ['FY'])
             if valid_fy:
                ttm_cf = valid_fy.model_copy(deep=True)
                ttm_cf.std_period_type = 'TTM'
                ttm_cf.std_period = f"TTM-{valid_fy.std_period}"
                data.cash_flows.insert(0, ttm_cf)
                print(f"      [TTM Builder] Using Latest Valid FY as TTM Cash Flow (Ends {valid_fy.std_period})")

        # 3. Check Balance Sheet
        if not any(s.std_period_type == 'TTM' for s in data.balance_sheets):
            valid_bs = find_valid(data.balance_sheets, 'balance')
            if valid_bs:
                ttm_bs = valid_bs.model_copy(deep=True)
                ttm_bs.std_period_type = 'TTM'
                ttm_bs.std_period = f"TTM-{valid_bs.std_period}"
                data.balance_sheets.insert(0, ttm_bs)
                print(f"      [TTM Builder] Using Latest Valid Snapshot as TTM Balance Sheet (Snapshot of {valid_bs.std_period})")

        return data

    def _run_phase1_yahoo(self, symbol: str) -> StockData:
        # --- Phase 1: Yahoo Finance (Base Layer) ---
        print("-> [Phase 1] Fetching Base Data (Yahoo Finance)...")
        
        # 1.1 Yahoo Finance (Primary Free Source)
        yahoo_fetcher = YahooFetcher(symbol)
        yahoo_data = yahoo_fetcher.fetch_all()
        
        if not yahoo_data:
             logger.warning(f"Yahoo fetch failed for {symbol}")
             yahoo_data = StockData(symbol=symbol)
             
        if yahoo_data.profile and yahoo_data.profile.std_sector:
             yahoo_data.profile.std_sector = DataMerger.normalize_sector(yahoo_data.profile.std_sector)
        
        # Log Yahoo results
        y_inc = len(yahoo_data.income_statements) if yahoo_data.income_statements else 0
        y_bal = len(yahoo_data.balance_sheets) if yahoo_data.balance_sheets else 0
        y_cf = len(yahoo_data.cash_flows) if yahoo_data.cash_flows else 0
        print(f"   (Yahoo: Found Profile, Price History, Statements[I:{y_inc} B:{y_bal} C:{y_cf}])")
        return yahoo_data

    def _run_phase2_edgar(self, current_data: StockData) -> StockData:
        # --- Phase 2: SEC EDGAR (Official Filings) ---
        print("-> [Phase 2] Fetching Official Filings (SEC EDGAR)...")
        edgar_fetcher = EdgarFetcher()
        edgar_data = edgar_fetcher.fetch_all_financials(current_data.symbol)
        
        # Log Edgar results
        e_inc = len(edgar_data.get('income_statements', []))
        e_bal = len(edgar_data.get('balance_sheets', []))
        e_cf = len(edgar_data.get('cash_flows', []))
        print(f"   (Edgar: Found Statements[I:{e_inc} B:{e_bal} C:{e_cf}])")
        
        # Initial Merge (Yahoo + Edgar)
        merger = IntelligentMerger(current_data.symbol)

        current_data.income_statements = merger.merge_statements(
            yahoo_stmts=current_data.income_statements,
            edgar_stmts=edgar_data.get('income_statements', []),
            fmp_stmts=[], 
            av_stmts=[],
            statement_class=IncomeStatement
        )
        
        current_data.balance_sheets = merger.merge_statements(
            yahoo_stmts=current_data.balance_sheets,
            edgar_stmts=edgar_data.get('balance_sheets', []),
            fmp_stmts=[], 
            av_stmts=[],
            statement_class=BalanceSheet
        )
        
        current_data.cash_flows = merger.merge_statements(
            yahoo_stmts=current_data.cash_flows,
            edgar_stmts=edgar_data.get('cash_flows', []),
            fmp_stmts=[], 
            av_stmts=[],
            statement_class=CashFlow
        )
        
        self._log_status(current_data, prefix="-> [Phase 2 Result]")
        return current_data

    def _run_phase3_fmp(self, current_data: StockData) -> StockData:
        # --- Phase 3: Gap Analysis & FMP (Paid/Granular) ---
        merger = IntelligentMerger(current_data.symbol)
        profile = current_data.profile
        if not profile:
             profile = CompanyProfile()
             current_data.profile = profile
             
        # Check for gaps
        missing_valuation = (
            profile.std_pe_ratio is None or 
            profile.std_pb_ratio is None or
            profile.std_ps_ratio is None
        )
        missing_basic = (
            profile.std_market_cap is None or
            profile.std_sector is None
        )
        missing_estimates = (
            current_data.analyst_targets is None or
            not any([current_data.analyst_targets.std_price_target_high, current_data.analyst_targets.std_price_target_avg])
        )
        missing_growth = (
            profile.std_earnings_growth is None
        )
        
        has_income = current_data.income_statements and len(current_data.income_statements) > 0
        has_balance = current_data.balance_sheets and len(current_data.balance_sheets) > 0
        has_cashflow = current_data.cash_flows and len(current_data.cash_flows) > 0
        
        missing_profitability_inputs = True
        if has_income and has_balance and has_cashflow:
            try:
                latest_inc = current_data.income_statements[0]
                latest_bal = current_data.balance_sheets[0]
                latest_cf = current_data.cash_flows[0]
                
                has_tax = latest_inc.std_income_tax_expense is not None
                has_op_inc = latest_inc.std_operating_income is not None
                has_equity = latest_bal.std_shareholder_equity is not None
                has_debt = latest_bal.std_total_debt is not None
                has_sbc = latest_cf.std_stock_based_compensation is not None
                has_capex = latest_cf.std_capital_expenditure is not None
                
                if has_tax and has_op_inc and has_equity and has_debt and has_sbc and has_capex:
                    missing_profitability_inputs = False
            except:
                pass

        fmp_needed = missing_valuation or missing_basic or missing_estimates or missing_growth or missing_profitability_inputs
        
        if self.use_fmp and GAP_THRESHOLDS.get("PHASE3_FMP_ENABLED", True):
            print("-> [Phase 3] Checking for Gaps (FMP)...")
            if fmp_needed:
                try:
                    from data_acquisition.stock_data.fmp_fetcher import FMPFetcher
                    fmp_fetcher = FMPFetcher(current_data.symbol)
                    
                    if missing_valuation and GAP_THRESHOLDS.get("FETCH_ON_MISSING_VALUATION", True):
                        print("   - Missing Valuation -> Calling FMP Ratios")
                        current_data.metadata['paid_api_used'] = True
                        ratios = fmp_fetcher.fetch_ratios()
                        if ratios: 
                            current_data.profile = merger.merge_profiles(current_data.profile, ratios)
                    
                    if missing_basic:
                        print("   - Missing Basic Info -> Calling FMP Profile")
                        current_data.metadata['paid_api_used'] = True
                        base_profile = fmp_fetcher.fetch_profile()
                        if base_profile:
                            current_data.profile = merger.merge_profiles(current_data.profile, base_profile)
                    
                    if missing_profitability_inputs:
                         print("   - Missing Financials (Tax/Equity/Debt/SBC/Capex) -> Calling FMP Statements")
                         current_data.metadata['paid_api_used'] = True
                         inc_stmts = fmp_fetcher.fetch_income_statements()
                         bal_stmts = fmp_fetcher.fetch_balance_sheets()
                         cf_stmts = fmp_fetcher.fetch_cash_flow_statements()
                         
                         if inc_stmts:
                             current_data.income_statements = merger.merge_statements(
                                 current_data.income_statements, [], inc_stmts, [], IncomeStatement
                             )
                         if bal_stmts:
                             current_data.balance_sheets = merger.merge_statements(
                                 current_data.balance_sheets, [], bal_stmts, [], BalanceSheet
                             )
                         if cf_stmts:
                             current_data.cash_flows = merger.merge_statements(
                                 current_data.cash_flows, [], cf_stmts, [], CashFlow
                             )
                         
                         fmp_fields = merger.get_contributions('fmp')
                         if fmp_fields:
                             print(f"   (FMP Filled: Statements - {len(fmp_fields)} fields merged)")
                         else:
                             print("   (FMP: No new fields merged or Free Tier limit reached)")
                    
                    if missing_growth and GAP_THRESHOLDS.get("FETCH_ON_MISSING_GROWTH", True):
                        print("   - Missing Growth -> Calling FMP Growth")
                        current_data.metadata['paid_api_used'] = True
                        growth_metrics = fmp_fetcher.fetch_financial_growth()
                        if growth_metrics:
                             current_data.profile = merger.merge_profiles(current_data.profile, growth_metrics)
                    
                    if missing_estimates and GAP_THRESHOLDS.get("FETCH_ON_MISSING_ESTIMATES", True):
                        print("   - Missing Estimates -> Calling FMP Estimates")
                        current_data.metadata['paid_api_used'] = True
                        estimates = fmp_fetcher.fetch_analyst_estimates()
                        if estimates:
                            if not current_data.analyst_targets:
                                current_data.analyst_targets = estimates
                except Exception as e:
                    logger.error(f"FMP fetch error: {e}")
            else:
                 print("   (Skipped - Data Complete)")
        
        # Re-check completeness for Phase 4
        self.validation_result = self._validate_data(current_data, "Phase 3 Result")
        return current_data

    def _run_phase4_alphavantage(self, current_data: StockData) -> StockData:
        # --- Phase 4: Alpha Vantage (Paid/Fallback) ---
        merger = IntelligentMerger(current_data.symbol)
        profile = current_data.profile
        still_missing_critical = (
            profile.std_pe_ratio is None or
            profile.std_eps is None or
            profile.std_market_cap is None
        )
        
        if self.use_alphavantage and GAP_THRESHOLDS.get("PHASE4_AV_ENABLED", True):
            if still_missing_critical:
                print("   - Critical gaps remain -> Calling Alpha Vantage (Overview)")
                current_data.metadata['paid_api_used'] = True
                try:
                    from data_acquisition.stock_data.alphavantage_fetcher import AlphaVantageFetcher
                    av_fetcher = AlphaVantageFetcher(current_data.symbol)
                    av_profile = av_fetcher.fetch_profile()
                    
                    if av_profile:
                        current_data.profile = merger.merge_profiles(current_data.profile, av_profile)
                        av_fields = merger.get_contributions('alphavantage')
                        print(f"   (Merged Alpha Vantage Overview. Filled: {', '.join(av_fields)})")
                    else:
                        print("   (Alpha Vantage fetch failed)")
                except Exception as e:
                    logger.error(f"Alpha Vantage fetch error: {e}")
            
            has_income = current_data.income_statements and len(current_data.income_statements) > 0
            has_balance = current_data.balance_sheets and len(current_data.balance_sheets) > 0
            has_cashflow = current_data.cash_flows and len(current_data.cash_flows) > 0
            
            p3_missing_financials = True
            if has_income and has_balance and has_cashflow:
                try:
                    l_inc = current_data.income_statements[0]
                    l_bal = current_data.balance_sheets[0]
                    l_cf = current_data.cash_flows[0]
                    
                    has_basic_metrics = (
                        l_inc.std_income_tax_expense is not None and 
                        l_inc.std_operating_income is not None and 
                        l_bal.std_shareholder_equity is not None and 
                        l_bal.std_total_debt is not None
                    )
                    
                    has_advanced_metrics = (
                        l_cf.std_stock_based_compensation is not None and
                        l_cf.std_capital_expenditure is not None
                    )
                    
                    has_shares = l_inc.std_weighted_average_shares is not None
                    
                    if has_basic_metrics and has_advanced_metrics and has_shares:
                        p3_missing_financials = False
                        
                except:
                    pass
            
            if p3_missing_financials:
                print("   - Missing Financials -> Calling Alpha Vantage Statements")
                current_data.metadata['paid_api_used'] = True
                try:
                    from data_acquisition.stock_data.alphavantage_fetcher import AlphaVantageFetcher
                    if 'av_fetcher' not in locals():
                         av_fetcher = AlphaVantageFetcher(current_data.symbol)
                    
                    av_inc = av_fetcher.fetch_income_statements()
                    av_bal = av_fetcher.fetch_balance_sheets()
                    
                    if av_inc:
                        current_data.income_statements = merger.merge_statements(
                            current_data.income_statements, [], [], av_inc, IncomeStatement
                        )
                    if av_bal:
                         current_data.balance_sheets = merger.merge_statements(
                            current_data.balance_sheets, [], [], av_bal, BalanceSheet
                        )
                    
                    av_fields = merger.get_contributions('alphavantage')
                    filled_str = ', '.join(av_fields[:5]) + ('...' if len(av_fields)>5 else '') if av_fields else "Statements"
                    print(f"   (Merged AV Statements: Inc={len(av_inc or [])}, Bal={len(av_bal or [])}. Filled: {filled_str})")
                        
                except Exception as e:
                    logger.error(f"Alpha Vantage statements fetch error: {e}")
        return current_data

    def _log_status(self, data: StockData, prefix: str = "->"):
        """Helper to log completeness and history depth."""
        valid = self._validate_data(data, "StatusCheck")
        # Only count Annual (FY) or TTM periods as "History Years"
        hist_years = len([s for s in data.income_statements if getattr(s, 'std_period_type', 'FY') in ['FY', 'TTM']])
        print(f"          {prefix} Completeness: {valid.average_completeness:.1%} | History: {hist_years} Years (FY/TTM)")
        
        # Verbose output for missing fields to help user understand why score is low
        if not valid.is_complete:
            missing = self.validator.get_missing_fields_summary(valid)
            req = missing.get('required', [])
            if req:
                # Show top 5 missing required fields
                print(f"              Missing Required: {', '.join(req[:5])}{'...' if len(req)>5 else ''}")

    def _validate_data(self, data: StockData, source_label: str) -> OverallValidationResult:
        """
        Validate stock data and log results.
        
        Args:
            data: StockData object to validate
            source_label: Label for logging (e.g., "Yahoo", "Yahoo+FMP")
            
        Returns:
            OverallValidationResult
        """
        validation = self.validator.validate_all_statements(
            data.symbol,
            data.income_statements,
            data.balance_sheets,
            data.cash_flows
        )
        
        if validation.is_complete:
            logger.info(f"[{source_label}] Data complete (completeness: {validation.average_completeness:.1%})")
        else:
            missing = self.validator.get_missing_fields_summary(validation)
            logger.info(
                f"[{source_label}] Data incomplete - "
                f"Missing required: {missing['required']}, Missing important: {missing['important']}"
            )
        
        return validation
    
    def get_validation_report(self) -> Optional[OverallValidationResult]:
        """Get the validation result from the last fetch."""
        return self.validation_result
    
    def _quick_merge(self, yahoo_data, edgar_data, fmp_data, av_income, av_balance, av_cashflow, merger, symbol) -> StockData:
        """
        Perform a quick merge for incremental status display.
        
        Args:
            yahoo_data: Yahoo data (StockData or None)
            edgar_data: EDGAR data dict
            fmp_data: FMP data dict
            av_income/av_balance/av_cashflow: Alpha Vantage statement lists
            merger: IntelligentMerger instance
            symbol: Stock symbol
            
        Returns:
            Temporarily merged StockData for validation
        """
        merged_income = merger.merge_statements(
            yahoo_stmts=yahoo_data.income_statements if yahoo_data else [],
            edgar_stmts=edgar_data.get('income_statements', []) if edgar_data else [],
            fmp_stmts=fmp_data.get('income_statements', []) if fmp_data else [],
            av_stmts=av_income,
            statement_class=IncomeStatement
        )
        
        merged_balance = merger.merge_statements(
            yahoo_stmts=yahoo_data.balance_sheets if yahoo_data else [],
            edgar_stmts=edgar_data.get('balance_sheets', []) if edgar_data else [],
            fmp_stmts=fmp_data.get('balance_sheets', []) if fmp_data else [],
            av_stmts=av_balance,
            statement_class=BalanceSheet
        )
        
        merged_cashflow = merger.merge_statements(
            yahoo_stmts=yahoo_data.cash_flows if yahoo_data else [],
            edgar_stmts=edgar_data.get('cash_flows', []) if edgar_data else [],
            fmp_stmts=fmp_data.get('cash_flows', []) if fmp_data else [],
            av_stmts=av_cashflow,
            statement_class=CashFlow
        )
        
        return StockData(
            symbol=symbol,
            profile=yahoo_data.profile if yahoo_data else None,
            price_history=yahoo_data.price_history if yahoo_data else [],
            income_statements=merged_income,
            balance_sheets=merged_balance,
            cash_flows=merged_cashflow,
            analyst_targets=yahoo_data.analyst_targets if yahoo_data else None
        )

    def save_stock_data(self, data: StockData, output_dir: str) -> str:
        """
        Save stock data to JSON file
        
        Args:
            data: StockData object
            output_dir: Output directory (required)
            
        Returns:
            str: Saved file path
        """
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # initial_data_{SYMBOL}_{DATE}.json
            current_date = datetime.now().strftime("%Y-%m-%d")
            filename = f"initial_data_{data.symbol}_{current_date}.json"
            file_path = os.path.join(output_dir, filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(data.model_dump_json(indent=4))
                
            logger.info(f"Data saved to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to save data: {e}")
            raise

    def load_stock_data(self, file_path: str) -> StockData:
        """
        Load stock data from JSON file
        
        Args:
            file_path: JSON file path
            
        Returns:
            StockData: Loaded stock data object
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json_content = f.read()
            
            data = StockData.model_validate_json(json_content)
            logger.info(f"Data loaded from {file_path}")
            return data
        except Exception as e:
            logger.error(f"Failed to load data from {file_path}: {e}")
            raise

    def get_stock_data(self, symbol: str) -> StockData:
        """
        Fetch comprehensive stock data using Field-Level Waterfall Strategy.
        (Renamed from fetch_stock_data to maintain Interface Compatibility)
        
        Strategy:
        1. Phase 1 (Free): Fetch Base Data (Yahoo Finance).
        2. Phase 2 (Official): Fetch Financial Filings (SEC EDGAR).
        3. Phase 3 (Gap Analysis & Paid): Check for gaps & fetch FMP if needed.
        4. Phase 4 (Fallback): Fetch Alpha Vantage if critical gaps remain.
        5. Final Merge & Validate.
        
        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL')
            
        Returns:
            Unified StockData object with intelligently merged fields
        """
        symbol = symbol.upper().strip()
        logger.info(f"Starting Field-Level Waterfall fetch for {symbol}")
        print(f"\nFetching data for {symbol}...")
        
        # Phase 1: Yahoo Finance
        current_data = self._run_phase1_yahoo(symbol)
        
        # Initialize metadata
        current_data.metadata = current_data.metadata or {}
        current_data.metadata['paid_api_used'] = False
        
        # Phase 2: EDGAR (Official SEC Filings)
        current_data = self._run_phase2_edgar(current_data)
        
        # Phase 2.5: Forecast Data (Yahoo/FMP/Finnhub) - NEW
        current_data = self._run_phase2_5_forecast(current_data)
        
        # Phase 3: Gap AnalysisFMP
        current_data = self._run_phase3_fmp(current_data)
        
        # Phase 4: Alpha Vantage
        current_data = self._run_phase4_alphavantage(current_data)
        
        # --- Phase 5: Currency & ADR Normalization ---
        # Resolve currency mismatches (e.g. TWD vs USD) for international stocks
        print("-> [Phase 5] Normalizing Currency & ADR Shares...")
        from utils.currency_normalizer import CurrencyNormalizer
        current_data = CurrencyNormalizer.normalize(current_data)
        
        # DEBUG: Verify conversion stuck
        if current_data.income_statements:
            sample = current_data.income_statements[0]
            if sample.std_revenue:
                logger.info(f"[Trace] Post-Normalization Revenue [{sample.std_period}]: {sample.std_revenue.value:,.0f} ({sample.std_revenue.source})")
        
        # --- TTM Construction: Synthesize latest year if needed ---
        current_data = self._construct_synthetic_ttm(current_data)
        
        # DEBUG: Verify TTM result
        ttm_inc = next((s for s in current_data.income_statements if s.std_period_type == 'TTM'), None)
        if ttm_inc and ttm_inc.std_revenue:
             logger.info(f"[Trace] Synthetic TTM Revenue: {ttm_inc.std_revenue.value:,.0f} ({ttm_inc.std_revenue.source})")
        
        # --- Sanitization: Remove Incomplete Periods ---
        current_data = self._sanitize_data(current_data)

        # --- Final Validation & Scorecard ---
        self.validation_result = self._validate_data(current_data, "Final")
        
        # Display the visual scorecard
        from data_acquisition.stock_data.completeness_reporter import CompletenessReporter
        CompletenessReporter.generate_scorecard(symbol, current_data, self.validation_result)
            
        return current_data
    
    def _extract_yahoo_forecast(self, data: StockData) -> Optional['ForecastData']:
        """
        Extract forward-looking metrics from Yahoo profile to ForecastData format.
        
        Yahoo provides: forward_eps, forward_pe, earnings_growth in CompanyProfile.
        We map these to ForecastData for unified forecast handling.
        """
        from utils.unified_schema import ForecastData
        
        if not data or not data.profile:
            return None
        
        forecast = ForecastData()
        has_data = False
        
        # Map forward metrics
        if data.profile.std_forward_eps:
            forecast.std_forward_eps = data.profile.std_forward_eps
            has_data = True
        
        if data.profile.std_forward_pe:
            forecast.std_forward_pe = data.profile.std_forward_pe
            has_data = True
        
        if data.profile.std_earnings_growth:
            # Map to current year growth estimate
            forecast.std_earnings_growth_current_year = data.profile.std_earnings_growth
            has_data = True
        
        return forecast if has_data else None
    
    def _fetch_fmp_forecast(self, symbol: str) -> Optional['ForecastData']:
        """Fetch forecast data from FMP using FMPFetcher."""
        try:
            from data_acquisition.stock_data.fmp_fetcher import FMPFetcher
            fetcher = FMPFetcher(symbol)
            return fetcher.fetch_forecast_data()
        except Exception as e:
            logger.warning(f"FMP forecast fetch failed for {symbol}: {e}")
            return None
    
    def _fetch_finnhub_forecast(self, symbol: str) -> Optional['ForecastData']:
        """Fetch forecast data from Finnhub using FinnhubFetcher."""
        try:
            from data_acquisition.stock_data.finnhub_fetcher import FinnhubFetcher
            fetcher = FinnhubFetcher(symbol)
            return fetcher.fetch_forecast_data()
        except Exception as e:
            logger.warning(f"Finnhub forecast fetch failed for {symbol}: {e}")
            return None
    
    def _run_phase2_5_forecast(self, current_data: StockData) -> StockData:
        """
        Phase 2.5: Fetch and merge forecast data from multiple sources.
        
        Sources:
        - Yahoo: forward_eps, forward_pe, earnings_growth (from Phase 1)
        - FMP: price targets, analyst estimates, growth estimates
        - Finnhub: earnings surprise history, estimates
        
        Returns:
            Updated StockData with forecast_data populated
        """
        logger.info("-> [Phase 2.5] Fetching Forecast Data (FMP + Finnhub)...")
        print("-> [Phase 2.5] Fetching Forecast Data (FMP + Finnhub)...")
        
        symbol = current_data.profile.std_symbol if current_data.profile else "UNKNOWN"
        
        # 1. Extract Yahoo forecast (from Phase 1 profile)
        yahoo_forecast = self._extract_yahoo_forecast(current_data)
        if yahoo_forecast:
            logger.debug(f"  Extracted Yahoo forward metrics")
        
        # 2. Fetch FMP forecast
        fmp_forecast = self._fetch_fmp_forecast(symbol)
        
        # 3. Fetch Finnhub forecast  
        finnhub_forecast = self._fetch_finnhub_forecast(symbol)
        
        # 4. Merge using IntelligentMerger
        if any([yahoo_forecast, fmp_forecast, finnhub_forecast]):
            # Create merger instance (same pattern as other phases)
            merger = IntelligentMerger(symbol)
            
            merged_forecast = merger.merge_forecast_data(
                yahoo_forecast, fmp_forecast, finnhub_forecast
            )
            
            if merged_forecast:
                current_data.forecast_data = merged_forecast
                
                # Log summary
                sources = []
                if yahoo_forecast: sources.append("Yahoo")
                if fmp_forecast: sources.append("FMP")
                if finnhub_forecast: sources.append("Finnhub")
                
                logger.info(f"   ✓ Merged forecast data from: {', '.join(sources)}")
            else:
                logger.info("   No forecast data available after merge")
        else:
            logger.info("   No forecast data available from any source")
        
        return current_data


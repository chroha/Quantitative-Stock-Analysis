"""
Data Loader Module - Unified External Entry Point for Data Acquisition

This module orchestrates a 3-tier cascading data fetch:
1. Fetch base data from Yahoo Finance, calculate completeness.
2. If incomplete, fetch supplementary data from FMP.
3. If still incomplete (or missing key fields), fetch from Alpha Vantage.
4. Merge and validate data.
5. Return a unified StockData object.
"""

import os
import json
from datetime import datetime
from typing import Optional, Tuple, List

from utils.unified_schema import StockData, IncomeStatement, BalanceSheet, CashFlow
from utils.logger import setup_logger
from data_acquisition.stock_data.yahoo_fetcher import YahooFetcher
from data_acquisition.stock_data.edgar_fetcher import EdgarFetcher
from data_acquisition.stock_data.fmp_fetcher import FMPFetcher
from data_acquisition.stock_data.data_merger import DataMerger
from data_acquisition.stock_data.intelligent_merger import IntelligentMerger
from data_acquisition.stock_data.field_validator import FieldValidator, OverallValidationResult

logger = setup_logger('data_loader')


class StockDataLoader:
    """
    Stock Data Loader - Main entry point class for the Data Acquisition Layer.
    
    Implements 3-tier cascading data fetch:
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
    
    def _log_status(self, data: StockData, prefix: str = "->"):
        """Helper to log completeness and history depth."""
        valid = self._validate_data(data, "StatusCheck")
        hist_years = len(data.income_statements)
        print(f"          {prefix} Completeness: {valid.average_completeness:.1%} | History: {hist_years} years")

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

    def save_stock_data(self, data: StockData, output_dir: str = "generated_data") -> str:
        """
        Save stock data to JSON file
        
        Args:
            data: StockData object
            output_dir: Output directory
            
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
        1. Phase 1 (Free): Fetch Yahoo (Base) and Edgar (Financials). Merge.
        2. Phase 2 (Gap Analysis): Check for missing critical fields (PE, MarketCap, etc.).
        3. Phase 2 (FMP Paid): Call specific FMP endpoints ONLY if fields are missing.
        4. Phase 3 (AV Paid): Fetch Alpha Vantage if gaps remain.
        5. Final Merge & Validate.
        
        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL')
            
        Returns:
            Unified StockData object with intelligently merged fields
        """
        symbol = symbol.upper().strip()
        logger.info(f"Starting Field-Level Waterfall fetch for {symbol}")
        print(f"\nFetching data for {symbol}...")
        
        # Track if we used paid APIs (FMP/AlphaVantage)
        paid_api_used = False
        
        # --- Phase 1: Free Tier (Yahoo + Edgar) ---
        print("-> [Phase 1] Fetching Free Sources (Yahoo + Edgar)...")
        
        # 1.1 Yahoo Finance (Primary Free Source)
        yahoo_fetcher = YahooFetcher(symbol)
        yahoo_data = yahoo_fetcher.fetch_all()
        
        # Yahoo fetch_all returns StockData. 
        # CAUTION: YahooFetcher.fetch_all() might return None if completely failed?
        # Checking implementation: usually returns StockData object even if partial.
        # But let's be safe.
        if not yahoo_data:
             logger.warning(f"Yahoo fetch failed for {symbol}")
             yahoo_data = StockData(symbol=symbol)
             
        if yahoo_data.profile and yahoo_data.profile.std_sector:
             yahoo_data.profile.std_sector = DataMerger.normalize_sector(yahoo_data.profile.std_sector)
            
        # 1.2 SEC EDGAR (Official Financials)
        print("   Fetching from SEC EDGAR...")
        edgar_fetcher = EdgarFetcher()
        edgar_data = edgar_fetcher.fetch_all_financials(symbol)
        
        # 1.3 Initial Merge (Free Tier)
        merger = IntelligentMerger(symbol)
        
        # We need to act on a 'current_data' object.
        current_data = yahoo_data
        
        # Merge Edgar Statements using quick_merge helper or direct?
        # Since we are refactoring, let's use the explicit logic I designed.
        # But IntelligentMerger needs lists.
        
        current_data.income_statements = merger.merge_statements(
            yahoo_stmts=current_data.income_statements,
            edgar_stmts=edgar_data.get('income_statements', []),
            fmp_stmts=[], av_stmts=[], statement_class=IncomeStatement
        )
        
        current_data.balance_sheets = merger.merge_statements(
            yahoo_stmts=current_data.balance_sheets,
            edgar_stmts=edgar_data.get('balance_sheets', []),
            fmp_stmts=[], av_stmts=[], statement_class=BalanceSheet
        )
        
        current_data.cash_flows = merger.merge_statements(
            yahoo_stmts=current_data.cash_flows,
            edgar_stmts=edgar_data.get('cash_flows', []),
            fmp_stmts=[], av_stmts=[], statement_class=CashFlow
        )
        
        self._log_status(current_data, prefix="-> [Phase 1 Result]")
        
        # --- Phase 2: Gap Analysis & FMP (Paid/Granular) ---
        # Check what's missing after free tier
        profile = current_data.profile
        if not profile:
             profile = CompanyProfile()
             current_data.profile = profile
             
        # Define Critical Fields for Valuation/Scoring
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
        
        # Decide if we need FMP
        fmp_needed = missing_valuation or missing_basic or missing_estimates or missing_growth
        
        fmp_updates = []
        if self.use_fmp and fmp_needed:
            print("-> [Phase 2] Critical gaps detected. Calling FMP (Granular)...")
            try:
                from data_acquisition.stock_data.fmp_fetcher import FMPFetcher
                fmp_fetcher = FMPFetcher(symbol)
                
                # Rule 1: Valuation Ratios
                if missing_valuation:
                    print("   - Missing Valuation -> Calling FMP Ratios")
                    ratios = fmp_fetcher.fetch_ratios()
                    if ratios: 
                        fmp_updates.append(ratios)
                        paid_api_used = True
                    
                # Rule 2: Basic Info
                if missing_basic:
                    print("   - Missing Basic Info -> Calling FMP Profile")
                    # Note: We fetch full profile only if basic info missing.
                    base_profile = fmp_fetcher.fetch_profile()
                    if base_profile:
                        fmp_updates.append(base_profile)
                        paid_api_used = True
                
                # Rule 3: Missing Financials (for ROIC/Scoring)
                # Check directly if we have the necessary statement lines
                has_income = current_data.income_statements and len(current_data.income_statements) > 0
                has_balance = current_data.balance_sheets and len(current_data.balance_sheets) > 0
                
                missing_profitability_inputs = True
                if has_income and has_balance:
                    latest_inc = current_data.income_statements[0]
                    # Check for Tax and Operating Income (vital for ROIC)
                    has_tax = latest_inc.std_income_tax_expense is not None
                    has_op_inc = latest_inc.std_operating_income is not None
                    
                    latest_bal = current_data.balance_sheets[0]
                    # Check for Equity and Debt (vital for ROIC)
                    has_equity = latest_bal.std_shareholder_equity is not None
                    has_debt = latest_bal.std_total_debt is not None
                    
                    if has_tax and has_op_inc and has_equity and has_debt:
                        missing_profitability_inputs = False
                        
                if missing_profitability_inputs:
                     print("   - Missing Financials (Tax/Equity/Debt) -> Calling FMP Statements")
                     inc_stmts = fmp_fetcher.fetch_income_statements()
                     bal_stmts = fmp_fetcher.fetch_balance_sheets()
                     
                     if inc_stmts:
                         fmp_updates.append(inc_stmts)
                     if bal_stmts:
                         fmp_updates.append(bal_stmts)
                     
                     if inc_stmts or bal_stmts:
                         paid_api_used = True
                    
                if profile.std_market_cap is None or profile.std_book_value_per_share is None:
                     print("   - Missing Key Metrics -> Calling FMP Key Metrics")
                     metrics = fmp_fetcher.fetch_key_metrics()
                     if metrics: 
                        fmp_updates.append(metrics)
                        paid_api_used = True
                
                # Rule 3: Forward Estimates
                if missing_estimates:
                    print("   - Missing Estimates -> Calling FMP Estimates")
                    estimates = fmp_fetcher.fetch_analyst_estimates()
                    if estimates: 
                        fmp_updates.append(estimates)
                        paid_api_used = True
    
                # Rule 4: Growth
                if missing_growth:
                    print("   - Missing Growth -> Calling FMP Growth")
                    growth = fmp_fetcher.fetch_financial_growth()
                    if growth: 
                        fmp_updates.append(growth)
                        paid_api_used = True
                    
            except Exception as e:
                logger.error(f"FMP fetch error: {e}")
        else:
             print("-> [Phase 2] No critical gaps detected. Skipping FMP to save API quota.")
        
        # Merge FMP Updates
        if fmp_updates:
            for update in fmp_updates:
                 current_data.profile = merger.merge_profiles(current_data.profile, update)
            print(f"   (Merged {len(fmp_updates)} FMP datasets)")

        # --- Phase 3: Alpha Vantage (Paid/Fallback) ---
        profile = current_data.profile # Update ref
        still_missing_critical = (
            profile.std_pe_ratio is None or
            profile.std_eps is None or
            profile.std_market_cap is None
        )
        
        if self.use_alphavantage:
            # Check for critical gaps (Overview)
            if still_missing_critical:
                print("-> [Phase 3] Critical gaps remain. Calling Alpha Vantage (Overview)...")
                try:
                    from data_acquisition.stock_data.alphavantage_fetcher import AlphaVantageFetcher
                    av_fetcher = AlphaVantageFetcher(symbol)
                    av_profile = av_fetcher.fetch_profile()
                    
                    if av_profile:
                        current_data.profile = merger.merge_profiles(current_data.profile, av_profile)
                        print("   (Merged Alpha Vantage Overview)")
                        paid_api_used = True
                    else:
                        print("   (Alpha Vantage fetch failed)")
                except Exception as e:
                    logger.error(f"Alpha Vantage fetch error: {e}")
            
            # Check for missing financials (Statements) if FMP didn't fill them
            # Re-check inputs after FMP phase
            has_income_av = current_data.income_statements and len(current_data.income_statements) > 0
            has_balance_av = current_data.balance_sheets and len(current_data.balance_sheets) > 0
            
            p3_missing_financials = True
            if has_income_av and has_balance_av:
                try:
                    l_inc = current_data.income_statements[0]
                    l_bal = current_data.balance_sheets[0]
                    if (l_inc.std_income_tax_expense is not None and 
                        l_inc.std_operating_income is not None and 
                        l_bal.std_shareholder_equity is not None and 
                        l_bal.std_total_debt is not None):
                        p3_missing_financials = False
                except:
                    pass
            
            if p3_missing_financials:
                print("-> [Phase 3] Missing Financials (Tax/Equity/Debt). Calling Alpha Vantage Statements...")
                try:
                    from data_acquisition.stock_data.alphavantage_fetcher import AlphaVantageFetcher
                    # Reuse fetcher if available, else init
                    if 'av_fetcher' not in locals():
                         av_fetcher = AlphaVantageFetcher(symbol)
                    
                    av_inc = av_fetcher.fetch_income_statements()
                    av_bal = av_fetcher.fetch_balance_sheets()
                    
                    if av_inc:
                        current_data.income_statements = merger.merge_statements(
                            current_data.income_statements, av_inc, 'std_period'
                        )
                    if av_bal:
                         current_data.balance_sheets = merger.merge_statements(
                            current_data.balance_sheets, av_bal, 'std_period'
                        )
                    
                    if av_inc or av_bal:
                        print(f"   (Merged AV Statements: Inc={len(av_inc)}, Bal={len(av_bal)})")
                        paid_api_used = True
                        
                except Exception as e:
                    logger.error(f"Alpha Vantage statements fetch error: {e}")
        
        # --- Final Validation ---
        self._log_status(current_data, prefix="-> [Final Status]")
        self.validation_result = self._validate_data(current_data, "Final")
        
        # Populate Source Metadata
        current_data.metadata = current_data.metadata or {}
        current_data.metadata['paid_api_used'] = paid_api_used
        
        return current_data

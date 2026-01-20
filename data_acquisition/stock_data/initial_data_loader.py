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
        Fetch complete data for a stock using intelligent field-level merging.
        
        This is the default data acquisition method. It collects raw data from all 
        sources first, then uses IntelligentMerger for field-level priority merging 
        based on field_registry.
        
        For debugging or comparison, use get_stock_data_legacy() which uses the 
        older incremental merge approach.
        
        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL')
            
        Returns:
            StockData: Unified StockData object with intelligently merged fields
        """
        symbol = symbol.upper().strip()
        logger.info(f"Starting intelligent data acquisition for: {symbol}")
        
        # =====================================================================
        # STEP 1: Collect raw data from all sources
        # =====================================================================
        
        # Yahoo Finance (Primary)
        print(f"    Fetching from Yahoo Finance...")
        yahoo_data = None
        try:
            yahoo_fetcher = YahooFetcher(symbol)
            yahoo_data = yahoo_fetcher.fetch_all()
            if yahoo_data.profile and yahoo_data.profile.std_sector:
                yahoo_data.profile.std_sector = DataMerger.normalize_sector(yahoo_data.profile.std_sector)
        except Exception as e:
            logger.error(f"Yahoo fetch failed: {e}")
        
        # EDGAR (Official Source)
        print(f"    [2/4] Fetching from SEC EDGAR...")
        edgar_data = {'income_statements': [], 'balance_sheets': [], 'cash_flows': []}
        try:
            edgar_fetcher = EdgarFetcher()
            edgar_data = edgar_fetcher.fetch_all_financials(symbol)
        except Exception as e:
            logger.error(f"EDGAR fetch failed: {e}")
        
        # FMP (Supplementary)
        print(f"    [3/4] Fetching from FMP...")
        fmp_data = {'income_statements': [], 'balance_sheets': [], 'cash_flows': [], 'profile': None, 'analyst_targets': None}
        try:
            fmp_fetcher = FMPFetcher(symbol)
            fmp_data = fmp_fetcher.fetch_all()
        except Exception as e:
            logger.error(f"FMP fetch failed: {e}")
        
        # Alpha Vantage (Final Fallback)
        av_income, av_balance, av_cashflow = [], [], []
        if self.use_alphavantage:
            print(f"    [4/4] Fetching from Alpha Vantage...")
            try:
                from data_acquisition.stock_data.alphavantage_fetcher import AlphaVantageFetcher
                av_fetcher = AlphaVantageFetcher(symbol)
                av_income = av_fetcher.fetch_income_statements()
                av_balance = av_fetcher.fetch_balance_sheets()
                av_cashflow = av_fetcher.fetch_cash_flows()
            except Exception as e:
                logger.error(f"Alpha Vantage fetch failed: {e}")
        
        # =====================================================================
        # STEP 2: Intelligent field-level merging
        # =====================================================================
        print(f"    Merging data with field-level priority...")
        merger = IntelligentMerger(symbol)
        
        # Merge income statements
        merged_income = merger.merge_statements(
            yahoo_stmts=yahoo_data.income_statements if yahoo_data else [],
            edgar_stmts=edgar_data.get('income_statements', []),
            fmp_stmts=fmp_data.get('income_statements', []),
            av_stmts=av_income,
            statement_class=IncomeStatement
        )
        
        # Merge balance sheets
        merged_balance = merger.merge_statements(
            yahoo_stmts=yahoo_data.balance_sheets if yahoo_data else [],
            edgar_stmts=edgar_data.get('balance_sheets', []),
            fmp_stmts=fmp_data.get('balance_sheets', []),
            av_stmts=av_balance,
            statement_class=BalanceSheet
        )
        
        # Merge cash flows
        merged_cashflow = merger.merge_statements(
            yahoo_stmts=yahoo_data.cash_flows if yahoo_data else [],
            edgar_stmts=edgar_data.get('cash_flows', []),
            fmp_stmts=fmp_data.get('cash_flows', []),
            av_stmts=av_cashflow,
            statement_class=CashFlow
        )
        
        # Merge profile (Yahoo > FMP > AV)
        merged_profile = yahoo_data.profile if yahoo_data else None
        if fmp_data.get('profile') and not merged_profile:
            merged_profile = fmp_data['profile']
        
        # Merge analyst targets (Yahoo > FMP)
        analyst_targets = yahoo_data.analyst_targets if yahoo_data else None
        if fmp_data.get('analyst_targets') and not analyst_targets:
            analyst_targets = fmp_data['analyst_targets']
        
        # =====================================================================
        # STEP 3: Create final merged StockData
        # =====================================================================
        merged_data = StockData(
            symbol=symbol,
            profile=merged_profile,
            price_history=yahoo_data.price_history if yahoo_data else [],
            income_statements=merged_income,
            balance_sheets=merged_balance,
            cash_flows=merged_cashflow,
            analyst_targets=analyst_targets
        )
        
        # Validate and log
        validation = self._validate_data(merged_data, "IntelligentMerge")
        self._log_status(merged_data)
        self.validation_result = validation
        
        # Log merge statistics
        stats = merger.get_merge_statistics()
        if stats:
            stats_str = ", ".join(f"{k}:{v}" for k, v in stats.items())
            logger.info(f"Merge statistics: {stats_str}")
        
        return merged_data

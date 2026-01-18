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

from utils.unified_schema import StockData
from utils.logger import setup_logger
from data_acquisition.stock_data.yahoo_fetcher import YahooFetcher
from data_acquisition.stock_data.fmp_fetcher import FMPFetcher
from data_acquisition.stock_data.data_merger import DataMerger
from data_acquisition.stock_data.field_validator import FieldValidator, OverallValidationResult

logger = setup_logger('data_loader')


class StockDataLoader:
    """
    Stock Data Loader - Main entry point class for the Data Acquisition Layer.
    
    Implements 3-tier cascading data fetch:
    - Tier 1: Yahoo Finance (primary, most comprehensive)
    - Tier 2: FMP (fallback, good financial data)
    - Tier 3: Alpha Vantage (second fallback, GAAP-compliant)
    
    Reserved for future: SEC EDGAR as Tier 4 (official source)
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
    
    def get_stock_data(self, symbol: str) -> StockData:
        """
        Fetch complete data for a stock with cascading fallback and field validation.

        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL')

        Returns:
            StockData: Unified StockData object
        """
        symbol = symbol.upper().strip()
        logger.info(f"Starting data acquisition for: {symbol}")
        
        # =====================================================================
        # TIER 1: Yahoo Finance (Primary Source)
        # =====================================================================
        print(f"    Fetching from Yahoo Finance...")
        logger.info("Fetching data from Yahoo Finance...")
        yahoo_fetcher = YahooFetcher(symbol)
        yahoo_data = yahoo_fetcher.fetch_all()
        
        # Validate Yahoo data
        validation = self._validate_data(yahoo_data, "Yahoo")
        
        # =====================================================================
        # TIER 2: FMP (Supplementary Source) - Always fetch for analyst targets
        # =====================================================================
        print(f"    Fetching from FMP (Supplementary)...")
        logger.info("Fetching data from FMP...")
        fmp_data = None
        try:
            fmp_fetcher = FMPFetcher(symbol)
            fmp_data = fmp_fetcher.fetch_all()
        except Exception as e:
            logger.error(f"Failed to fetch FMP data: {e}")
            fmp_data = {'analyst_targets': None, 'profile': None}
        
        # Merge Yahoo and FMP data
        logger.info("Merging Yahoo and FMP data...")
        merged_data = DataMerger.merge_and_validate(yahoo_data, fmp_data)
        
        # Re-validate after FMP merge
        validation = self._validate_data(merged_data, "Yahoo+FMP")
        
        # =====================================================================
        # TIER 3: Alpha Vantage (Second Fallback)
        # Trigger if: missing required fields OR completeness < 100%
        # =====================================================================
        needs_alphavantage = (
            not validation.is_complete or 
            validation.average_completeness < 1.0
        )
        
        if self.use_alphavantage and needs_alphavantage:
            trigger_reason = "missing required fields" if not validation.is_complete else f"completeness {validation.average_completeness:.1%} < 100%"
            print(f"    Data incomplete ({validation.average_completeness:.1%}), fetching from Alpha Vantage...")
            logger.info(f"Attempting Alpha Vantage fetch ({trigger_reason})...")
            
            try:
                from data_acquisition.stock_data.alphavantage_fetcher import AlphaVantageFetcher
                
                av_fetcher = AlphaVantageFetcher(symbol)
                
                # Get missing field summary to decide what to fetch
                missing_summary = self.validator.get_missing_fields_summary(validation)
                
                # Fetch from Alpha Vantage based on what's missing
                av_profile = None
                av_income = []
                av_balance = []
                av_cashflow = []
                
                # Check if profile fields are missing
                if not merged_data.profile or not merged_data.profile.std_sector or not merged_data.profile.std_sector.value:
                    av_profile = av_fetcher.fetch_profile()
                
                # Check if income statement fields are missing or incomplete
                needs_income = any(
                    r.statement_type == 'income' and (not r.is_complete or r.completeness_score < 1.0)
                    for r in validation.period_results
                )
                if needs_income:
                    av_income = av_fetcher.fetch_income_statements()
                    logger.info(f"Fetched {len(av_income)} income statements from Alpha Vantage")
                
                # Check if balance sheet fields are missing or incomplete
                needs_balance = any(
                    r.statement_type == 'balance' and (not r.is_complete or r.completeness_score < 1.0)
                    for r in validation.period_results
                )
                if needs_balance:
                    av_balance = av_fetcher.fetch_balance_sheets()
                    logger.info(f"Fetched {len(av_balance)} balance sheets from Alpha Vantage")
                
                # Check if cash flow fields are missing or incomplete
                needs_cashflow = any(
                    r.statement_type == 'cashflow' and (not r.is_complete or r.completeness_score < 1.0)
                    for r in validation.period_results
                )
                if needs_cashflow:
                    av_cashflow = av_fetcher.fetch_cash_flows()
                    logger.info(f"Fetched {len(av_cashflow)} cash flow statements from Alpha Vantage")
                
                # Merge Alpha Vantage data
                if av_profile or av_income or av_balance or av_cashflow:
                    print(f"    Fetched supplemental data from Alpha Vantage")
                    merged_data = self._merge_alphavantage_data(
                        merged_data, av_profile, av_income, av_balance, av_cashflow
                    )
                    
                    # Final validation
                    validation = self._validate_data(merged_data, "Yahoo+FMP+AV")
                    
            except ImportError as e:
                logger.warning(f"Alpha Vantage fetcher not available: {e}")
            except Exception as e:
                logger.error(f"Alpha Vantage fetch failed: {e}")
        
        # Store final validation result
        self.validation_result = validation
        
        # Log final completeness status
        if validation.is_complete:
            logger.info(f"{symbol}: Data acquisition complete (completeness: {validation.average_completeness:.1%})")
        else:
            logger.warning(
                f"{symbol}: Data acquisition finished with gaps - "
                f"{validation.incomplete_periods}/{validation.total_periods_validated} periods incomplete"
            )
        
        return merged_data
    
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
    
    def _merge_alphavantage_data(
        self,
        merged_data: StockData,
        av_profile: Optional[any],
        av_income: List[any],
        av_balance: List[any],
        av_cashflow: List[any]
    ) -> StockData:
        """
        Merge Alpha Vantage data into existing merged data.
        Only fills in missing fields, does not overwrite existing data.
        
        Args:
            merged_data: Existing merged StockData
            av_profile: Alpha Vantage profile
            av_income: Alpha Vantage income statements
            av_balance: Alpha Vantage balance sheets
            av_cashflow: Alpha Vantage cash flow statements
            
        Returns:
            StockData with Alpha Vantage data merged in
        """
        # Merge profile
        if av_profile:
            merged_data.profile = DataMerger.merge_profile(
                merged_data.profile, None, av_profile
            )
        
        # Merge financial statements by matching periods
        if av_income:
            merged_data.income_statements = self._merge_statement_list(
                merged_data.income_statements, av_income
            )
        
        if av_balance:
            merged_data.balance_sheets = self._merge_statement_list(
                merged_data.balance_sheets, av_balance
            )
        
        if av_cashflow:
            merged_data.cash_flows = self._merge_statement_list(
                merged_data.cash_flows, av_cashflow
            )
        
        return merged_data
    
    def _extract_fiscal_year(self, period: str) -> Optional[int]:
        """
        Extract fiscal year from various period formats.
        
        Handles:
        - '2025-09-30' -> 2025
        - '2025-FY' -> 2025
        - '2025' -> 2025
        """
        if not period:
            return None
        
        # Try to extract 4-digit year
        import re
        match = re.search(r'(\d{4})', period)
        if match:
            return int(match.group(1))
        return None
    
    def _merge_statement_list(self, existing: List[any], new_data: List[any]) -> List[any]:
        """
        Merge statement lists by matching periods and filling missing fields.
        Matches by fiscal year to handle different period formats.
        
        Args:
            existing: Existing statements
            new_data: New statements from Alpha Vantage
            
        Returns:
            Merged list with missing fields filled (no duplicates)
        """
        if not new_data:
            return existing
        
        if not existing:
            return new_data
        
        # Create lookup by FISCAL YEAR (not exact period string)
        existing_by_year = {}
        for stmt in existing:
            period = getattr(stmt, 'std_period', None)
            year = self._extract_fiscal_year(period)
            if year:
                existing_by_year[year] = stmt
        
        filled_count = 0
        skipped_count = 0
        
        # Fill missing fields from new data (match by year)
        for new_stmt in new_data:
            new_period = getattr(new_stmt, 'std_period', None)
            new_year = self._extract_fiscal_year(new_period)
            
            if not new_year:
                continue
            
            if new_year in existing_by_year:
                # Fill missing fields in existing statement (matched by year)
                existing_stmt = existing_by_year[new_year]
                DataMerger._fill_missing_fields_in_stmt(existing_stmt, new_stmt)
                filled_count += 1
            else:
                # Skip - don't add periods that don't exist in primary data
                # (avoid creating duplicates with different naming)
                skipped_count += 1
        
        if filled_count > 0:
            logger.info(f"  Filled {filled_count} periods with Alpha Vantage data")
        if skipped_count > 0:
            logger.debug(f"  Skipped {skipped_count} AV periods (no matching year in existing data)")
        
        return existing
    
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

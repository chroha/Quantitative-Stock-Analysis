"""
Data merger - combines data from multiple sources with intelligent prioritization.
Priority: Yahoo > FMP > Alpha Vantage > Manual
[INTERNAL PROCESS MODULE] - This module is used by StockDataLoader, do not call directly.
"""

from typing import Optional, Tuple, List, Any
from utils.logger import setup_logger
from utils.unified_schema import (
    StockData, CompanyProfile, AnalystTargets, FieldWithSource, TextFieldWithSource,
    IncomeStatement, BalanceSheet, CashFlow
)

logger = setup_logger('data_merger')

# Sector name normalization mapping
# Maps variations from different data sources to standardized GICS sector names
SECTOR_NORMALIZATION_MAP = {
    "Financial Services": "Financials",
    "Basic Materials": "Materials",
    "Telecommunication Services": "Communication Services",
    "Consumer Cyclical": "Consumer Discretionary",
    "Consumer Defensive": "Consumer Staples",
    # Add more mappings as encountered
}

class ValidationReport:
    """Container for validation results."""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.missing_fields = []
        self.warnings = []
        self.errors = []
        self.is_valid = True
    
    def add_missing(self, field_name: str, category: str):
        """Add a missing field."""
        self.missing_fields.append({
            'field': field_name,
            'category': category
        })
    
    def add_warning(self, message: str):
        """Add a warning."""
        self.warnings.append(message)
        logger.warning(message)
    
    def add_error(self, message: str):
        """Add an error."""
        self.errors.append(message)
        self.is_valid = False
        logger.error(message)


class DataValidator:
    """Validates stock data completeness and consistency."""
    
    @staticmethod
    def _check_field(field: Optional[FieldWithSource], field_name: str, 
                     report: ValidationReport, category: str, required: bool = False):
        """
        Check if a field has data.
        """
        if not field or field.value is None:
            if required:
                report.add_error(f"Required field missing: {field_name}")
            else:
                report.add_missing(field_name, category)
    
    @staticmethod
    def validate(stock_data: StockData) -> ValidationReport:
        """
        Validate stock data for completeness and consistency.
        """
        logger.info(f"Starting validation for {stock_data.symbol}")
        report = ValidationReport(stock_data.symbol)
        
        # Validate profile
        if stock_data.profile:
            profile = stock_data.profile
            DataValidator._check_field(profile.std_company_name, 'Company Name', report, 'Profile', required=True)
            DataValidator._check_field(profile.std_industry, 'Industry', report, 'Profile')
            DataValidator._check_field(profile.std_sector, 'Sector', report, 'Profile')
            DataValidator._check_field(profile.std_market_cap, 'Market Cap', report, 'Profile')
        else:
            report.add_error("Company profile is completely missing")
        
        # Validate price history
        if not stock_data.price_history or len(stock_data.price_history) == 0:
            report.add_error("No price history data available")
        else:
            logger.info(f"Price history: {len(stock_data.price_history)} days")
        
        # Validate income statements
        if not stock_data.income_statements or len(stock_data.income_statements) == 0:
            report.add_warning("No income statement data available")
        else:
            logger.info(f"Income statements: {len(stock_data.income_statements)} periods")
            # Check key fields in most recent statement
            latest = stock_data.income_statements[0]
            DataValidator._check_field(latest.std_revenue, 'Revenue', report, 'Income Statement', required=True)
            DataValidator._check_field(latest.std_net_income, 'Net Income', report, 'Income Statement', required=True)
            DataValidator._check_field(latest.std_eps, 'EPS', report, 'Income Statement')
        
        # Validate balance sheets
        if not stock_data.balance_sheets or len(stock_data.balance_sheets) == 0:
            report.add_warning("No balance sheet data available")
        else:
            logger.info(f"Balance sheets: {len(stock_data.balance_sheets)} periods")
            latest = stock_data.balance_sheets[0]
            DataValidator._check_field(latest.std_total_assets, 'Total Assets', report, 'Balance Sheet', required=True)
            DataValidator._check_field(latest.std_total_liabilities, 'Total Liabilities', report, 'Balance Sheet')
            DataValidator._check_field(latest.std_shareholder_equity, 'Shareholder Equity', report, 'Balance Sheet')
            
            # Check balance sheet equation: Assets = Liabilities + Equity
            if (latest.std_total_assets and latest.std_total_assets.value and 
                latest.std_total_liabilities and latest.std_total_liabilities.value and
                latest.std_shareholder_equity and latest.std_shareholder_equity.value):
                
                assets = latest.std_total_assets.value
                liabilities = latest.std_total_liabilities.value
                equity = latest.std_shareholder_equity.value
                
                expected = liabilities + equity
                diff_pct = abs(assets - expected) / assets * 100 if assets else 0
                
                if diff_pct > 1.0:  # Allow 1% tolerance
                    report.add_warning(
                        f"Balance sheet equation mismatch: Assets={assets:.2f}, "
                        f"Liabilities+Equity={expected:.2f} (diff: {diff_pct:.2f}%)"
                    )
        
        # Validate cash flows
        if not stock_data.cash_flows or len(stock_data.cash_flows) == 0:
            report.add_warning("No cash flow data available")
        else:
            logger.info(f"Cash flows: {len(stock_data.cash_flows)} periods")
            latest = stock_data.cash_flows[0]
            DataValidator._check_field(latest.std_operating_cash_flow, 'Operating Cash Flow', report, 'Cash Flow')
            DataValidator._check_field(latest.std_free_cash_flow, 'Free Cash Flow', report, 'Cash Flow')
        
        # Validate analyst targets
        if stock_data.analyst_targets:
            targets = stock_data.analyst_targets
            DataValidator._check_field(targets.std_price_target_avg, 'Avg Price Target', report, 'Analyst Targets')
        else:
            report.add_missing('Analyst Price Targets', 'Analyst Targets')
        
        logger.info(f"Validation completed: {len(report.missing_fields)} missing, "
                   f"{len(report.warnings)} warnings, {len(report.errors)} errors")
        
        return report


class DataMerger:
    """
    智能合并多源数据并进行验证。
    Intelligently merges data from multiple sources and validates it.
    """
    
    #_validator = DataValidator() # Removed instance, using static methods

    
    @staticmethod
    def check_data_sufficiency(yahoo_data: StockData) -> Tuple[bool, list[str]]:
        """
        Check if Yahoo data is sufficient or if FMP data is needed.
        
        Args:
            yahoo_data: Yahoo data object
            
        Returns:
            Tuple[bool, list]: (is_sufficient, missing_reasons)
            True if sufficient (NO FMP needed), False if FMP needed.
            NOTE: The previous logic returned 'need_fmp', so be careful with boolean flip.
            Let's return (need_fmp, reasons) to match previous logic flow.
        """
        reasons = []
        
        # 检查分析师目标价 / Check for Analyst Targets
        if not yahoo_data.analyst_targets:
            reasons.append("Missing Analyst Targets")

        # 检查公司资料 / Check for Company Profile
        if yahoo_data.profile:
            if not yahoo_data.profile.std_company_name or not yahoo_data.profile.std_company_name.value:
                reasons.append("Missing Company Name")
            if not yahoo_data.profile.std_industry or not yahoo_data.profile.std_industry.value:
                reasons.append("Missing Industry")
            if not yahoo_data.profile.std_sector or not yahoo_data.profile.std_sector.value:
                reasons.append("Missing Sector")
        else:
            reasons.append("Missing Entire Profile")
            
        # 检查财务数据深度 / Check Financials Depth (Optional but good)
        if len(yahoo_data.income_statements) < 5:
             reasons.append(f"Insufficient Financial History ({len(yahoo_data.income_statements)} < 5 years)")
            
        need_fmp = len(reasons) > 0
        return need_fmp, reasons

    @staticmethod
    def merge_and_validate(
        yahoo_data: StockData,
        fmp_data: dict,
        manual_data: Optional[dict] = None
    ) -> StockData:
        """
        Merges data and validates it. Main processing entry point.
        """
        # 1. 执行合并 / Execute Merge
        merged_data = DataMerger._merge_logic(yahoo_data, fmp_data, manual_data)
        
        # 2. Execute Validation
        logger.info("Validating merged data...")
        # report = DataMerger._validator.validate(merged_data)
        report = DataValidator.validate(merged_data)
        
        # Log validation results
        if report.is_valid:
            logger.info("Data validation passed")
        else:
            logger.warning(f"Data validation found issues: {len(report.errors)} Errors, {len(report.warnings)} Warnings")
        
        if report.missing_fields:
            logger.debug(f"Missing fields: {report.missing_fields}")
            
        return merged_data

    @staticmethod
    def _merge_logic(
        yahoo_data: StockData,
        fmp_data: dict,
        manual_data: Optional[dict] = None
    ) -> StockData:
        """
        Internal merge logic.
        Priority: Yahoo > FMP > Manual
        Strategy:
        1. Base on Yahoo data (usually verified).
        2. Backfill older years from FMP.
        3. Fill missing fields in Yahoo periods from FMP.
        """
        from datetime import datetime, timedelta

        logger.info(f"Merging data for {yahoo_data.symbol} from all sources")
        
        # Merge profile
        merged_profile = DataMerger.merge_profile(
            yahoo_data.profile,
            fmp_data.get('profile')
        )
        
        # Merge analyst targets: Priority Yahoo > FMP
        analyst_targets = None
        if yahoo_data.analyst_targets:
            analyst_targets = yahoo_data.analyst_targets
            logger.info("Using analyst targets from Yahoo Finance")
        elif fmp_data.get('analyst_targets'):
            analyst_targets = fmp_data.get('analyst_targets')
            logger.info("Using analyst targets from FMP (Yahoo unavailable)")
        else:
            logger.warning("No analyst targets available from any source")
        
        # Merge financial statements
        def combine_statement_lists(yahoo_stmts, fmp_stmts):
            """
            Combine statement lists with priority: Yahoo > FMP.
            Aligns dates (fuzzy match within 15 days) to ensure correct merging.
            Backfills older years from FMP.
            Fills missing fields in Yahoo periods using FMP data.
            """
            if not yahoo_stmts: yahoo_stmts = []
            if not fmp_stmts: fmp_stmts = []
            
            # --- pre-process: Align FMP dates to Yahoo dates ---
            # Yahoo is the source of truth for "Period Date". 
            # If FMP has a date close to Yahoo's (within 15 days), we assume it's the same period
            # and temporarily rename the FMP period to match Yahoo's strict string for the dict merge.
            
            # Create a list of (date_obj, date_str) for Yahoo to allow date math
            y_dates = []
            for s in yahoo_stmts:
                if s.std_period:
                    try:
                        dt = datetime.strptime(s.std_period, "%Y-%m-%d")
                        y_dates.append((dt, s.std_period))
                    except ValueError:
                        pass # specific format issues?
            
            # We will modify fmp_stmts mostly in-memory (or copy/modify the objects?)
            # Since these are Pydantic models, we can just update the field.
            # But we should be careful not to persist this if we needed the original FMP data elsewhere.
            # Here it's fine.
            
            for f_stmt in fmp_stmts:
                if not f_stmt.std_period: continue
                try:
                    f_dt = datetime.strptime(f_stmt.std_period, "%Y-%m-%d")
                    
                    # Find closest Yahoo date
                    best_match = None
                    min_diff = timedelta(days=999)
                    
                    for y_dt, y_str in y_dates:
                        diff = abs(f_dt - y_dt)
                        if diff < min_diff:
                            min_diff = diff
                            best_match = y_str
                    
                    # If match within 15 days, align!
                    if min_diff <= timedelta(days=15) and best_match:
                        # logger.debug(f"Aligning FMP date {f_stmt.std_period} to Yahoo {best_match} (diff {min_diff.days} days)")
                        f_stmt.std_period = best_match
                        
                except ValueError:
                    pass

            # --- standard merge logic (now that dates are aligned) ---
            
            # Map by date string
            y_map = {s.std_period: s for s in yahoo_stmts if s.std_period}
            f_map = {s.std_period: s for s in fmp_stmts if s.std_period}
            
            # Get all unique periods
            all_periods = sorted(set(y_map.keys()) | set(f_map.keys()), reverse=True)
            
            combined = []
            for period in all_periods:
                if period in y_map:
                    # Primary: Yahoo
                    stmt = y_map[period]
                    source_label = "Yahoo"
                    
                    # Check if we can fill missing fields from FMP
                    if period in f_map:
                        fmp_stmt = f_map[period]
                        filled_count = DataMerger._fill_missing_fields_in_stmt(stmt, fmp_stmt)
                        if filled_count > 0:
                            source_label += f" + FMP fill({filled_count})"
                    
                    combined.append(stmt)
                    # logger.debug(f"  Period {period}: {source_label}")
                    
                elif period in f_map:
                    # Backfill: FMP (only if Yahoo doesn't have it)
                    # Use FMP statement directly
                    stmt = f_map[period]
                    combined.append(stmt)
                    # logger.debug(f"  Period {period}: FMP (Backfill)")
            
            # Limit to most recent 6 periods
            final_list = combined[:6]
            logger.info(f"  Merged {len(final_list)} periods (Yahoo: {len(y_map)}, FMP: {len(f_map)})")
            return final_list

        logger.info("Merging Income Statements...")
        income_statements = combine_statement_lists(yahoo_data.income_statements, fmp_data.get('income_statements'))
        
        logger.info("Merging Balance Sheets...")
        balance_sheets = combine_statement_lists(yahoo_data.balance_sheets, fmp_data.get('balance_sheets'))
        
        logger.info("Merging Cash Flows...")
        cash_flows = combine_statement_lists(yahoo_data.cash_flows, fmp_data.get('cash_flows'))
        
        # Create merged stock data
        merged = StockData(
            symbol=yahoo_data.symbol,
            profile=merged_profile,
            price_history=yahoo_data.price_history,
            income_statements=income_statements,
            balance_sheets=balance_sheets,
            cash_flows=cash_flows,
            analyst_targets=analyst_targets
        )
        
        logger.info("Data merge completed successfully")
        return merged

    @staticmethod
    def _fill_missing_fields_in_stmt(target_stmt, source_stmt) -> int:
        """
        Fill missing fields (None or Value=None) in target_stmt using values from source_stmt.
        Returns number of fields filled.
        """
        filled_count = 0
        
        # Iterate over all attributes of the unified schema object
        # We assume both are instances of IncomeStatement, BalanceSheet, or CashFlow (Pydantic models)
        if not target_stmt or not source_stmt:
            return 0
            
        # Get all fields
        fields = target_stmt.model_fields.keys()
        
        for field_name in fields:
            if field_name == 'std_period': 
                continue
                
            current_val = getattr(target_stmt, field_name)
            source_val = getattr(source_stmt, field_name)
            
            # Check if current is 'empty'
            is_empty = False
            if current_val is None:
                is_empty = True
            elif isinstance(current_val, FieldWithSource) and current_val.value is None:
                is_empty = True
                
            # If empty, try to fill from source
            if is_empty and source_val is not None:
                if isinstance(source_val, FieldWithSource) and source_val.value is not None:
                    # Assign it!
                    setattr(target_stmt, field_name, source_val)
                    filled_count += 1
        
        return filled_count
        
    @staticmethod
    def _merge_field(
        primary: Optional[FieldWithSource],
        secondary: Optional[FieldWithSource]
    ) -> Optional[FieldWithSource]:
        """Merge a single field, prioritizing primary source."""
        if primary and primary.value is not None:
            return primary
        if secondary and secondary.value is not None:
            return secondary
        return None
    
    @staticmethod
    def normalize_sector(sector_field: Optional[TextFieldWithSource]) -> Optional[TextFieldWithSource]:
        """
        Normalize sector name to standard GICS sector names.
        Maps common variations (e.g., 'Financial Services' -> 'Financials').
        
        Args:
            sector_field: TextFieldWithSource containing sector name
            
        Returns:
            Normalized TextFieldWithSource or original if no mapping found
        """
        if not sector_field or not sector_field.value:
            return sector_field
        
        normalized = SECTOR_NORMALIZATION_MAP.get(sector_field.value, sector_field.value)
        if normalized != sector_field.value:
            logger.info(f"Normalized sector '{sector_field.value}' -> '{normalized}'")
            return TextFieldWithSource(value=normalized, source=sector_field.source)
        return sector_field
    
    @staticmethod
    def merge_profile(
        yahoo_profile: Optional[CompanyProfile],
        fmp_profile: Optional[CompanyProfile],
        av_profile: Optional[CompanyProfile] = None
    ) -> CompanyProfile:
        """
        Merge company profiles from multiple sources.
        Priority: Yahoo > FMP > Alpha Vantage
        """
        profiles = [p for p in [yahoo_profile, fmp_profile, av_profile] if p is not None]
        
        if not profiles:
            logger.warning("No profile data from any source")
            return CompanyProfile()
        
        if len(profiles) == 1:
            profile = profiles[0]
            # Normalize sector before returning
            profile.std_sector = DataMerger.normalize_sector(profile.std_sector)
            return profile
        
        # Merge fields intelligently - use first available (priority order)
        def get_first_valid(*fields):
            for f in fields:
                if f and hasattr(f, 'value') and f.value is not None:
                    return f
            return None
        
        merged_sector = get_first_valid(
            yahoo_profile.std_sector if yahoo_profile else None,
            fmp_profile.std_sector if fmp_profile else None,
            av_profile.std_sector if av_profile else None
        )
        # Apply sector normalization
        merged_sector = DataMerger.normalize_sector(merged_sector)
        
        merged = CompanyProfile(
            std_symbol=(yahoo_profile or fmp_profile or av_profile).std_symbol,
            std_company_name=get_first_valid(
                yahoo_profile.std_company_name if yahoo_profile else None,
                fmp_profile.std_company_name if fmp_profile else None,
                av_profile.std_company_name if av_profile else None
            ),
            std_industry=get_first_valid(
                yahoo_profile.std_industry if yahoo_profile else None,
                fmp_profile.std_industry if fmp_profile else None,
                av_profile.std_industry if av_profile else None
            ),
            std_sector=merged_sector,
            std_market_cap=get_first_valid(
                yahoo_profile.std_market_cap if yahoo_profile else None,
                fmp_profile.std_market_cap if fmp_profile else None,
                av_profile.std_market_cap if av_profile else None
            ),
            std_description=get_first_valid(
                yahoo_profile.std_description if yahoo_profile else None,
                fmp_profile.std_description if fmp_profile else None,
                av_profile.std_description if av_profile else None
            ),
            std_website=get_first_valid(
                yahoo_profile.std_website if yahoo_profile else None,
                fmp_profile.std_website if fmp_profile else None,
            ),
            std_ceo=get_first_valid(
                yahoo_profile.std_ceo if yahoo_profile else None,
                fmp_profile.std_ceo if fmp_profile else None,
            ),
            std_beta=get_first_valid(
                yahoo_profile.std_beta if yahoo_profile else None,
                fmp_profile.std_beta if fmp_profile else None,
                av_profile.std_beta if av_profile else None
            ),
        )
        
        return merged


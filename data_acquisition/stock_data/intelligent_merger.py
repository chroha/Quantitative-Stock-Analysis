"""
Intelligent Data Merger - Field-level priority merging across data sources.

Uses the field_registry to determine merge priority per field.
Provides detailed logging of which source provided each field.

智能数据合并器 - 跨数据源的字段级优先级合并。
使用字段注册表确定每个字段的合并优先级。
"""

from typing import Optional, List, Dict, Any, Tuple
from utils.unified_schema import (
    FieldWithSource, StockData, IncomeStatement, BalanceSheet, CashFlow, CompanyProfile,
    ForecastData
)
from utils.field_registry import DataSource, get_merge_priority, get_all_fields
from utils.logger import setup_logger

logger = setup_logger('intelligent_merger')


def merge_field(
    values: Dict[DataSource, Optional[FieldWithSource]],
    field_name: str
) -> Tuple[Optional[FieldWithSource], Optional[DataSource]]:
    """
    Merge a single field using priority from field_registry.
    
    Args:
        values: Dict mapping DataSource to FieldWithSource (or None)
        field_name: Unified field name (e.g., 'std_revenue')
        
    Returns:
        Tuple of (merged FieldWithSource, source that provided it) or (None, None)
    """
    priority = get_merge_priority(field_name)
    
    for source in priority:
        field_value = values.get(source)
        if field_value is not None and field_value.value is not None:
            return field_value, source
    
    return None, None


def merge_statement_by_period(
    statements_by_source: Dict[DataSource, Optional[Any]],
    statement_class: type,
    period: str
) -> Tuple[Any, Dict[str, DataSource]]:
    """
    Merge a single period's statement from multiple sources.
    
    Args:
        statements_by_source: Dict mapping DataSource to statement object (or None)
        statement_class: Target class (IncomeStatement, BalanceSheet, CashFlow)
        period: Period string (e.g., '2024-12-31')
        
    Returns:
        Tuple of (merged statement object, dict of field->source that provided it)
    """
    field_sources = {}
    merged_kwargs = {'std_period': period}
    
    # Determine period type (FY/Q/TTM) - Default to FY if unknown
    # Priority: Yahoo > FMP > EDGAR > AV
    period_type = 'FY'
    for source in [DataSource.YAHOO, DataSource.FMP, DataSource.SEC_EDGAR, DataSource.ALPHAVANTAGE]:
        stmt = statements_by_source.get(source)
        if stmt and hasattr(stmt, 'std_period_type') and stmt.std_period_type:
             period_type = stmt.std_period_type
             break
    merged_kwargs['std_period_type'] = period_type
    
    # Get all fields for this statement type
    all_fields = statement_class.model_fields.keys()
    
    for field_name in all_fields:
        if field_name in ['std_period', 'std_period_type']:
            continue
        
        # Gather values from all sources for this field
        field_values = {}
        for source, stmt in statements_by_source.items():
            if stmt is None:
                continue
            field_value = getattr(stmt, field_name, None)
            if field_value is not None:
                field_values[source] = field_value
        
        # Merge using priority
        merged_value, winning_source = merge_field(field_values, field_name)
        merged_kwargs[field_name] = merged_value
        
        if winning_source:
            field_sources[field_name] = winning_source
    
    return statement_class(**merged_kwargs), field_sources


def log_merge_summary(symbol: str, statement_type: str, field_sources: Dict[str, DataSource]):
    """Log a summary of which sources contributed which fields."""
    if not field_sources:
        return
    
    # Group fields by source
    by_source: Dict[DataSource, List[str]] = {}
    for field, source in field_sources.items():
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(field)
    
    summary_parts = []
    for source, fields in by_source.items():
        summary_parts.append(f"{source.value}({len(fields)})")
    
    logger.debug(f"{symbol} {statement_type}: Sources = {', '.join(summary_parts)}")


class IntelligentMerger:
    """
    Intelligent merger that combines data from multiple sources using field-level priority.
    """
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.merge_log: List[Dict] = []  # Track all merge decisions
    
    def merge_statements(
        self,
        yahoo_stmts: List[Any],
        edgar_stmts: List[Any],
        fmp_stmts: List[Any],
        av_stmts: List[Any],
        statement_class: type
    ) -> List[Any]:
        """
        Merge statement lists from all sources using robust group-by-date logic.
        """
        from datetime import datetime
        
        def get_date(p_str):
            try: return datetime.strptime(p_str, '%Y-%m-%d')
            except: return None

        # 1. Collect everything into a flat list with source tag
        all_stmts = []
        if yahoo_stmts: all_stmts.extend([(DataSource.YAHOO, s) for s in yahoo_stmts if s])
        if edgar_stmts: all_stmts.extend([(DataSource.SEC_EDGAR, s) for s in edgar_stmts if s])
        if fmp_stmts: all_stmts.extend([(DataSource.FMP, s) for s in fmp_stmts if s])
        if av_stmts: all_stmts.extend([(DataSource.ALPHAVANTAGE, s) for s in av_stmts if s])
        
        # 2. Group by date windows (7 days)
        # We sort by date first to make grouping easier
        valid_stmts = [item for item in all_stmts if get_date(item[1].std_period)]
        valid_stmts.sort(key=lambda x: get_date(x[1].std_period), reverse=True)
        
        groups = []
        for src, stmt in valid_stmts:
            s_date = get_date(stmt.std_period)
            
            # Find an existing group
            found_group = None
            for group in groups:
                ref_date = get_date(group[0][1].std_period)
                if abs((s_date - ref_date).days) <= 7:
                    found_group = group
                    break
            
            if found_group is not None:
                found_group.append((src, stmt))
            else:
                groups.append([(src, stmt)])
                
        # 3. Merge each group
        merged_statements = []
        for group in groups[:30]: # Limit to 30 periods
            # For each group, we pick the BEST statement for each source
            # Priority: If a source has both FY and Q in the same window (unlikely but possible), preferred is usually Q for recent or FY for final.
            # But the 'merge_statement_by_period' logic handles field merging once we have one per source.
            
            statements_by_source = {
                DataSource.YAHOO: None,
                DataSource.SEC_EDGAR: None,
                DataSource.FMP: None,
                DataSource.ALPHAVANTAGE: None
            }
            
            # Use the most common/latest date from the group as the canonical period
            primary_period = group[0][1].std_period 
            
            for src, stmt in group:
                # If source already has one, keep the one with more fields or better period type
                existing = statements_by_source[src]
                if not existing:
                    statements_by_source[src] = stmt
                else:
                    # Preference: FY usually has more audit quality, Q is more granular. 
                    # For TTM, we need Qs. So if we have both in a 7-day window, 
                    # we should actually check the 'std_period_type'
                    if stmt.std_period_type == 'FY' and existing.std_period_type == 'Q':
                        # Keep FY for profile/annuals
                        statements_by_source[src] = stmt
                    elif stmt.std_period_type == 'Q' and existing.std_period_type == 'FY':
                         # If we are in the merger, we might want to keep the Q for TTM
                         # Actually, the merge logic should ideally split them, 
                         # but if they are within 7 days, they are likely the same report.
                         pass 
            
            merged_stmt, field_sources = merge_statement_by_period(
                statements_by_source, statement_class, primary_period
            )
            merged_statements.append(merged_stmt)
            
            # Log summary
            log_merge_summary(self.symbol, f"{statement_class.__name__}[{primary_period}]", field_sources)
            
        return merged_statements

    def merge_profiles(self, base_profile: Optional[CompanyProfile], supplementary_profile: Optional[CompanyProfile]) -> CompanyProfile:
        """
        Merge two CompanyProfile objects using field priority.
        Used for merging FMP/AV updates into the base Yahoo profile.
        
        Args:
            base_profile: The primary profile (e.g. from Yahoo)
            supplementary_profile: The secondary profile (e.g. from FMP)
            
        Returns:
            Merged CompanyProfile
        """
        from utils.unified_schema import CompanyProfile
        
        if not base_profile and not supplementary_profile:
            return CompanyProfile(std_symbol=self.symbol)
        
        if not base_profile:
            return supplementary_profile
            
        if not supplementary_profile:
            return base_profile
            
        merged_kwargs = {}
        field_sources = {}
        
        # Iterate over all fields in CompanyProfile
        for field_name in CompanyProfile.model_fields.keys():
            # Get values from both
            val1 = getattr(base_profile, field_name, None)
            val2 = getattr(supplementary_profile, field_name, None)
            
            # Map valid values to sources
            # Assuming val.source is available if it's a FieldWithSource
            # If val is just a string/float (unlikely in our schema), we can't easily track source unless wrapper is used
            # But our Schema uses FieldWithSource everywhere except symbol basically.
            
            values_map = {}
            if val1: values_map[val1.source if hasattr(val1, 'source') and val1.source else DataSource.YAHOO] = val1
            if val2: values_map[val2.source if hasattr(val2, 'source') and val2.source else DataSource.FMP] = val2
            
            # If standard field without source wrapper (like std_symbol just str), priority is harder.
            # Usually base wins for simple types.
            if not hasattr(val1, 'source') and not hasattr(val2, 'source'):
                merged_kwargs[field_name] = val1 if val1 else val2
                continue

            # Merge using priority
            # Note: We simplified logic here. merge_field requires Dict[DataSource, FieldWithSource]
            # But values_map keys are strings 'yahoo', 'fmp' etc. We need Enums.
            
            converted_map = {}
            for k, v in values_map.items():
                # Convert string source to Enum if needed
                try:
                    enum_source = DataSource(k)
                    converted_map[enum_source] = v
                except ValueError:
                    pass # Skip invalid sources
            
            merged_value, winning_source = merge_field(converted_map, field_name)
            merged_kwargs[field_name] = merged_value
            
            if winning_source:
                field_sources[field_name] = winning_source

        # Log merge decision
        self.merge_log.append({
            'period': 'Profile',
            'statement_type': 'CompanyProfile',
            'field_sources': field_sources
        })

        # Log summary
        log_merge_summary(self.symbol, "CompanyProfile", field_sources)
        
        return CompanyProfile(**merged_kwargs)
    
    def get_merge_statistics(self) -> Dict[str, int]:
        """Get statistics about which sources provided data."""
        stats = {}
        for entry in self.merge_log:
            for field, source in entry.get('field_sources', {}).items():
                source_name = source.value
                if source_name not in stats:
                    stats[source_name] = 0
                stats[source_name] += 1
        return stats

    def get_contributions(self, source: str) -> List[str]:
        """
        Get unique list of fields contributed by a specific source.
        Used for reporting what data was filled by FMP/AV.
        """
        fields = set()
        # Check statement merges
        for entry in self.merge_log:
            for field_name, src_enum in entry.get('field_sources', {}).items():
                if src_enum.value == source:
                    fields.add(field_name)
        return sorted(list(fields))
    
    def merge_forecast_data(
        self,
        yahoo_forecast: Optional[ForecastData],
        fmp_forecast: Optional[ForecastData],
        finnhub_forecast: Optional[ForecastData]
    ) -> Optional[ForecastData]:
        """
        Merge forecast data from multiple sources using field-level priority.
        
        Args:
            yahoo_forecast: Forward metrics from Yahoo (forward_eps, forward_pe, etc.)
            fmp_forecast: Price targets, estimates, growth from FMP
            finnhub_forecast: Earnings surprises and estimates from Finnhub
            
        Returns:
            Merged ForecastData object or None if all sources are empty
        
        Special handling:
            - earnings_surprise_history: Exclusive to Finnhub, take directly
            - Other fields: Use merge_field() with FORECAST_FIELDS priority
        """
        # Early exit if all sources are None
        if not any([yahoo_forecast, fmp_forecast, finnhub_forecast]):
            return None
        
        merged_kwargs = {}
        field_sources = {}
        
        # Get all forecast fields
        all_fields = ForecastData.model_fields.keys()
        
        for field_name in all_fields:
            # Skip last_updated (auto-generated)
            if field_name == 'last_updated':
                continue
            
            # Special handling for earnings_surprise_history (list, Finnhub-only)
            if field_name == 'std_earnings_surprise_history':
                if finnhub_forecast and finnhub_forecast.std_earnings_surprise_history:
                    merged_kwargs[field_name] = finnhub_forecast.std_earnings_surprise_history
                    field_sources[field_name] = DataSource.FINNHUB
                else:
                    merged_kwargs[field_name] = []
                continue
            
            # Gather values from all sources
            field_values = {}
            
            if yahoo_forecast:
                val = getattr(yahoo_forecast, field_name, None)
                if val is not None:
                    field_values[DataSource.YAHOO] = val
            
            if fmp_forecast:
                val = getattr(fmp_forecast, field_name, None)
                if val is not None:
                    field_values[DataSource.FMP] = val
            
            if finnhub_forecast:
                val = getattr(finnhub_forecast, field_name, None)
                if val is not None:
                    field_values[DataSource.FINNHUB] = val
            
            # Merge using priority from field_registry
            merged_value, winning_source = merge_field(field_values, field_name)
            merged_kwargs[field_name] = merged_value
            
            if winning_source:
                field_sources[field_name] = winning_source
        
        # Log merge decision
        self.merge_log.append({
            'period': 'Forecast',
            'statement_type': 'ForecastData',
            'field_sources': field_sources
        })
        
        # Log summary
        log_merge_summary(self.symbol, "ForecastData", field_sources)
        
        # Check if we have any actual data
        has_data = any(
            merged_kwargs.get(field) is not None 
            for field in all_fields 
            if field != 'last_updated'
        )
        
        if not has_data:
            logger.warning(f"{self.symbol}: No forecast data after merge")
            return None
        
        return ForecastData(**merged_kwargs)

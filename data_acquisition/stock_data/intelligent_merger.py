"""
Intelligent Data Merger - Field-level priority merging across data sources.

Uses the field_registry to determine merge priority per field.
Provides detailed logging of which source provided each field.

智能数据合并器 - 跨数据源的字段级优先级合并。
使用字段注册表确定每个字段的合并优先级。
"""

from typing import Optional, List, Dict, Any, Tuple
from utils.unified_schema import (
    FieldWithSource, StockData, IncomeStatement, BalanceSheet, CashFlow, CompanyProfile
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
    
    # Get all fields for this statement type
    all_fields = statement_class.model_fields.keys()
    
    for field_name in all_fields:
        if field_name == 'std_period':
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
        Merge statement lists from all sources.
        
        Args:
            yahoo_stmts: Statements from Yahoo
            edgar_stmts: Statements from EDGAR
            fmp_stmts: Statements from FMP
            av_stmts: Statements from Alpha Vantage
            statement_class: Target class
            
        Returns:
            List of merged statements (most recent 6 periods)
        """
        from datetime import datetime, timedelta
        
        # Build maps by period for each source
        def build_period_map(stmts: List[Any]) -> Dict[str, Any]:
            if not stmts:
                return {}
            return {s.std_period: s for s in stmts if s and s.std_period}
        
        yahoo_map = build_period_map(yahoo_stmts)
        edgar_map = build_period_map(edgar_stmts)
        fmp_map = build_period_map(fmp_stmts)
        av_map = build_period_map(av_stmts)
        
        # Get all unique periods
        all_periods = set()
        all_periods.update(yahoo_map.keys())
        all_periods.update(edgar_map.keys())
        all_periods.update(fmp_map.keys())
        all_periods.update(av_map.keys())
        
        # Sort periods descending (most recent first)
        sorted_periods = sorted(all_periods, reverse=True)
        
        # Merge each period
        merged_statements = []
        for period in sorted_periods[:6]:  # Limit to 6 periods
            statements_by_source = {
                DataSource.YAHOO: yahoo_map.get(period),
                DataSource.SEC_EDGAR: edgar_map.get(period),
                DataSource.FMP: fmp_map.get(period),
                DataSource.ALPHAVANTAGE: av_map.get(period),
            }
            
            merged_stmt, field_sources = merge_statement_by_period(
                statements_by_source, statement_class, period
            )
            
            merged_statements.append(merged_stmt)
            
            # Log merge decision
            self.merge_log.append({
                'period': period,
                'statement_type': statement_class.__name__,
                'field_sources': field_sources
            })
            
            log_merge_summary(self.symbol, f"{statement_class.__name__}[{period}]", field_sources)
        
        return merged_statements
    
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

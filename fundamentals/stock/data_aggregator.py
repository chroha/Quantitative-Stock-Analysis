"""
Data Aggregator for AI Commentary.
Aggregates financial, technical, and valuation data into a simplified format for AI analysis.
"""

from typing import Dict, Any, Optional
from .aggregator_core import AggregatorCore
from .context_builder import ContextBuilder

class DataAggregator:
    """Aggregates data from various scoring and valuation outputs."""
    
    def __init__(self, data_dir: str):
        """
        Initialize aggregator.
        
        Args:
            data_dir: Directory containing data files (required)
        """
        self.core = AggregatorCore(data_dir)
        self.builder = ContextBuilder()
        
    def aggregate(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Aggregate data for a specific symbol.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Simplified dictionary of aggregated data or None if critical data missing
        """
        # 1. Load Data Bundle
        bundle = self.core.load_data_bundle(symbol)
        if not bundle:
            return None
            
        # 2. Build Context
        context = self.builder.build_context(bundle)
        return context
    
    def get_raw_data_appendix(self, symbol: str) -> str:
        """
        Generate a markdown appendix with all raw data for reference.
        Format: English Name | Chinese Name | Value | Field ID
        Uses utils.metric_registry for standardized naming.
        """
        # 1. Load Data Bundle
        bundle = self.core.load_data_bundle(symbol)
        if not bundle:
            return ""
            
        # 2. Generate Appendix
        return self.builder.generate_appendix(bundle)

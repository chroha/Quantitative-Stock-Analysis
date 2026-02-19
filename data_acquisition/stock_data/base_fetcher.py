"""
Base Fetcher - Common utilities and protocol for all data fetchers.

Provides:
1. Standardized field creation with source tracking
2. Common helper methods for date parsing and value conversion
3. Registry-aware field lookups

基础数据获取器 - 所有数据获取器的通用工具和协议。
"""

import math
import pandas as pd
from abc import ABC, abstractmethod
from typing import Optional, Any, List, Dict
from utils.unified_schema import FieldWithSource, TextFieldWithSource
from utils.field_registry import DataSource, get_source_field_name, get_merge_priority
from utils.logger import setup_logger
from utils.numeric_utils import clean_numeric  # Centralized numeric cleaning

logger = setup_logger('base_fetcher')


class BaseFetcher(ABC):
    """
    Abstract base class for all data fetchers.
    Provides common utilities and enforces consistent interface.
    """
    
    def __init__(self, symbol: str, source: DataSource):
        self.symbol = symbol
        self.source = source
    
    def _create_field(self, value: Any) -> Optional[FieldWithSource]:
        """
        Create a FieldWithSource from a raw value.
        Automatically sets the source based on the fetcher's source.
        
        Args:
            value: Raw value (can be float, int, string number, or None/NaN)
            
        Returns:
            FieldWithSource with value and source, or None if value is missing
        """
        # Handle missing values
        if value is None:
            return None
        
        # Handle pandas NA
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        
        if pd.isna(value):
            return None
        
        # Convert to float
        try:
            float_value = float(value)
            if math.isnan(float_value) or math.isinf(float_value):
                return None
            return FieldWithSource(value=float_value, source=self.source.value)
        except (ValueError, TypeError):
            return None
    
    def _create_text_field(self, value: Any) -> Optional[TextFieldWithSource]:
        """
        Create a TextFieldWithSource from a raw value.
        
        Args:
            value: Raw value (string or convertible to string)
            
        Returns:
            TextFieldWithSource with value and source, or None if value is missing
        """
        if value is None:
            return None
        
        if pd.isna(value):
            return None
        
        str_value = str(value).strip()
        if not str_value:
            return None
        
        return TextFieldWithSource(value=str_value, source=self.source.value)
    
    def _safe_get(self, data: Dict, key: str, default: Any = None) -> Any:
        """
        Safely get a value from a dictionary.
        
        Args:
            data: Source dictionary
            key: Key to look up
            default: Default value if key not found
            
        Returns:
            Value from dictionary or default
        """
        if not data:
            return default
        return data.get(key, default)
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """
        Safely convert a value to float.
        Delegates to centralized clean_numeric utility.
        
        Args:
            value: Value to convert
            
        Returns:
            Float value or None if conversion fails
        """
        return clean_numeric(value)

    @abstractmethod
    def fetch_income_statements(self, limit: int = None) -> list:
        """Fetch income statements."""
        pass

    @abstractmethod
    def fetch_balance_sheets(self, limit: int = None) -> list:
        """Fetch balance sheets."""
        pass

    @abstractmethod
    def fetch_cash_flow_statements(self, limit: int = None) -> list:
        """Fetch cash flow statements."""
        pass
        
    def fetch_cash_flows(self, limit: int = None) -> list:
        """Alias for fetch_cash_flow_statements (Backward Compatibility)."""
        return self.fetch_cash_flow_statements(limit=limit)

# Fetcher registry for dynamic source selection
class FetcherRegistry:
    """Registry of available fetchers by data source."""
    
    _fetchers: Dict[DataSource, type] = {}
    
    @classmethod
    def register(cls, source: DataSource, fetcher_class: type):
        """Register a fetcher class for a data source."""
        cls._fetchers[source] = fetcher_class
        logger.info(f"Registered fetcher: {fetcher_class.__name__} for {source.value}")
    
    @classmethod
    def get(cls, source: DataSource) -> Optional[type]:
        """Get the fetcher class for a data source."""
        return cls._fetchers.get(source)
    
    @classmethod
    def available_sources(cls) -> List[DataSource]:
        """Get list of available data sources."""
        return list(cls._fetchers.keys())

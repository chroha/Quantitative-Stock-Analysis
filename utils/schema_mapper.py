
"""
Schema Mapper - Helper to map raw data to unified schema using field_registry.

This module acts as the bridge between raw data (dicts/DataFrames) and the Unified Schema,
using the centralized definitions in utils.field_registry.
"""

import pandas as pd
from typing import Dict, Any, Optional, Union
from utils.unified_schema import FieldWithSource, DataSource
from utils.field_registry import get_all_fields, get_source_field_name, BALANCE_FIELDS, INCOME_FIELDS, CASHFLOW_FIELDS
from utils.logger import setup_logger

logger = setup_logger('schema_mapper')

class SchemaMapper:
    """Helper to map raw data to unified schema fields."""
    
    @staticmethod
    def _extract_value(data: Any, keys: list, source: DataSource) -> Optional[Any]:
        """
        Extract value from data using a list of potential keys.
        Supports dictionary or pandas Series/DataFrame access.
        """
        if data is None:
            return None
            
        # Try each key in order
        for key in keys:
            # Pandas Series/DataFrame
            if hasattr(data, 'index') or hasattr(data, 'loc'):
                if key in data.index:
                    return data.loc[key]
                # Handle case-insensitive match for Pandas? (Optional, but strict is safer)
                
            # Dictionary
            elif isinstance(data, dict):
                if key in data:
                    return data[key]
                
        return None

    @staticmethod
    def map_statement(
        data: Any, 
        statement_type: str, 
        source: DataSource
    ) -> Dict[str, FieldWithSource]:
        """
        Map a raw data object (dict or Series) to a dictionary of {field_name: FieldWithSource}.
        
        Args:
            data: Raw data object (dict for API json, or pd.Series for Yahoo row)
            statement_type: 'income', 'balance', 'cashflow'
            source: DataSource enum
            
        Returns:
            Dictionary mapping unified field names to FieldWithSource objects
        """
        # Determine which fields to look for
        if statement_type == 'income':
            target_fields = INCOME_FIELDS
        elif statement_type == 'balance':
            target_fields = BALANCE_FIELDS
        elif statement_type == 'cashflow':
            target_fields = CASHFLOW_FIELDS
        else:
            logger.error(f"Unknown statement type: {statement_type}")
            return {}
            
        mapped_data = {}
        
        for unified_name in target_fields.keys():
            # Get potential source names from Registry
            source_names = get_source_field_name(unified_name, source)
            
            if not source_names:
                continue
                
            # Extract raw value
            raw_value = SchemaMapper._extract_value(data, source_names, source)
            
            # Create field object if value exists
            if raw_value is not None and not pd.isna(raw_value):
                try:
                    # Generic cleanup for numbers
                    if isinstance(raw_value, str):
                        # Simple cleanup (handled differently per source usually, but baseline safety)
                        raw_value = raw_value.replace(',', '')
                    
                    val_float = float(raw_value)
                    mapped_data[unified_name] = FieldWithSource(
                        value=val_float, 
                        source=source.value
                    )
                except (ValueError, TypeError):
                    continue
                    
        return mapped_data

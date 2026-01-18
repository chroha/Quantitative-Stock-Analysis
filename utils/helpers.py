"""
Common helper utilities for the application.
"""

from datetime import datetime
from typing import Any, Optional
import pandas as pd


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Safely convert value to float.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Float value or default
    """
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """
    Safely convert value to integer.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Integer value or default
    """
    try:
        if pd.isna(value):
            return default
        return int(value)
    except (ValueError, TypeError):
        return default


def format_large_number(value: float, decimals: int = 2) -> str:
    """
    Format large numbers with appropriate suffix (K, M, B, T).
    
    Args:
        value: Number to format
        decimals: Number of decimal places
        
    Returns:
        Formatted string (e.g., '1.23B')
    """
    if abs(value) >= 1e12:
        return f"{value / 1e12:.{decimals}f}T"
    elif abs(value) >= 1e9:
        return f"{value / 1e9:.{decimals}f}B"
    elif abs(value) >= 1e6:
        return f"{value / 1e6:.{decimals}f}M"
    elif abs(value) >= 1e3:
        return f"{value / 1e3:.{decimals}f}K"
    else:
        return f"{value:.{decimals}f}"


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parse date string to datetime object.
    
    Args:
        date_str: Date string to parse
        
    Returns:
        Datetime object or None if parsing fails
    """
    if not date_str:
        return None
    
    try:
        return pd.to_datetime(date_str)
    except Exception:
        return None


def get_fiscal_year_quarter(date: datetime) -> tuple[int, int]:
    """
    Get fiscal year and quarter from date.
    
    Args:
        date: Date to analyze
        
    Returns:
        Tuple of (fiscal_year, quarter)
    """
    year = date.year
    month = date.month
    
    # Standard fiscal quarters (can be customized per company)
    if month <= 3:
        quarter = 1
    elif month <= 6:
        quarter = 2
    elif month <= 9:
        quarter = 3
    else:
        quarter = 4
    
    return year, quarter

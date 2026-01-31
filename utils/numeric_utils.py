"""
Numeric Utilities - Centralized numeric value handling.

Provides standardized functions for:
1. Cleaning numeric values (handling NaN/Inf/None)
2. Safe formatting for display/reporting
3. Validation of numeric values

This module ensures consistent behavior across all modules when dealing with
potentially invalid numeric values from financial data sources.
"""

import math
from typing import Any, Optional, Union


def is_valid_number(value: Any) -> bool:
    """
    Check if a value is a valid, finite number.
    
    Args:
        value: Any value to check
        
    Returns:
        True if value is a valid finite number, False otherwise
        
    Examples:
        >>> is_valid_number(3.14)
        True
        >>> is_valid_number(float('nan'))
        False
        >>> is_valid_number(None)
        False
    """
    if value is None:
        return False
    
    try:
        float_val = float(value)
        return not (math.isnan(float_val) or math.isinf(float_val))
    except (ValueError, TypeError):
        return False


def clean_numeric(value: Any) -> Optional[float]:
    """
    Clean a numeric value, returning None for invalid values.
    
    This is the core sanitization function. Use before any calculations
    to ensure NaN/Inf/None values are handled consistently.
    
    Args:
        value: Raw value (can be float, int, string number, or None/NaN)
        
    Returns:
        Float value if valid, None if value is missing/invalid
        
    Examples:
        >>> clean_numeric(3.14)
        3.14
        >>> clean_numeric("42.5")
        42.5
        >>> clean_numeric(float('nan'))
        None
        >>> clean_numeric(None)
        None
    """
    if value is None:
        return None
    
    try:
        float_value = float(value)
        if math.isnan(float_value) or math.isinf(float_value):
            return None
        return float_value
    except (ValueError, TypeError):
        return None


def safe_format(
    value: Any, 
    format_spec: str = ".2f", 
    default: str = "N/A",
    as_percent: bool = False
) -> str:
    """
    Safely format a numeric value for display/reporting.
    
    Returns a default string if the value is None/NaN/invalid.
    
    Args:
        value: Value to format
        format_spec: Python format specification (e.g., ".2f", ".0f", ".2%")
        default: String to return if value is invalid
        as_percent: If True, multiply by 100 and append "%" (for decimal ratios)
        
    Returns:
        Formatted string or default if value is invalid
        
    Examples:
        >>> safe_format(0.1234, ".2%")
        '12.34%'
        >>> safe_format(1234.5, ",.0f")
        '1,235'
        >>> safe_format(None)
        'N/A'
        >>> safe_format(0.15, ".1f", as_percent=True)
        '15.0%'
    """
    cleaned = clean_numeric(value)
    if cleaned is None:
        return default
    
    try:
        if as_percent:
            return f"{cleaned * 100:{format_spec}}%"
        return format(cleaned, format_spec)
    except (ValueError, TypeError):
        return str(cleaned) if cleaned is not None else default


def safe_divide(
    numerator: Any, 
    denominator: Any, 
    default: Optional[float] = None
) -> Optional[float]:
    """
    Safely perform division, handling None/NaN/zero denominators.
    
    Args:
        numerator: Dividend value
        denominator: Divisor value
        default: Value to return if division fails
        
    Returns:
        Division result or default if invalid
        
    Examples:
        >>> safe_divide(10, 2)
        5.0
        >>> safe_divide(10, 0)
        None
        >>> safe_divide(None, 5)
        None
    """
    clean_num = clean_numeric(numerator)
    clean_den = clean_numeric(denominator)
    
    if clean_num is None or clean_den is None or clean_den == 0:
        return default
    
    return clean_num / clean_den

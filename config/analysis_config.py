"""
Analysis Configuration
Centralized configuration for analysis thresholds, limits, and scoring parameters.
"""

from typing import Dict, Any

# --- Data Sufficiency Thresholds ---
# Used in run_analysis.py to determine if we should proceed
DATA_THRESHOLDS = {
    "REQUIRE_PROFILE_NAME": True,
    "REQUIRE_HISTORY": True,
    "REQUIRE_FINANCIALS": True,
    # Minimum years of history to be considered "good" (used in status logs)
    "MIN_HISTORY_YEARS_GOOD": 4, 
}

# --- Gap Analysis Thresholds (Data Acquisition) ---
# Used in initial_data_loader.py to trigger fallback fetches (FMP/AlphaVantage)
GAP_THRESHOLDS = {
    "PHASE3_FMP_ENABLED": True,
    "PHASE4_AV_ENABLED": True,
    # If set to True, will fetch paid data if these specific fields are missing
    "FETCH_ON_MISSING_VALUATION": True,  # PE, PB, PS
    "FETCH_ON_MISSING_GROWTH": True,     # Earnings Growth
    "FETCH_ON_MISSING_ESTIMATES": True,  # Analyst Targets
}

# --- Valuation Assessment Thresholds ---
# Used in valuation_output.py to generate text assessments
# defined as (lower_bound, assessment_text)
# The logic will check: value > threshold
VALUATION_THRESHOLDS = {
    "SIGNIFICANTLY_UNDERVALUED": 20.0,   # > +20%
    "UNDERVALUED": 10.0,                 # > +10%
    "FAIRLY_VALUED_LOWER": -10.0,        # > -10% (and <= 10%)
    "OVERVALUED_LOWER": -20.0,           # > -20% (and <= -10%)
    # Anything <= -20% is "Significantly Overvalued"
}

# --- Metric Validation Bounds ---
# Used in calculators (profitability.py, etc.) to flag outliers
# Format: 'METRIC_NAME': {'min': float, 'max': float}
METRIC_BOUNDS = {
    'effective_tax_rate': {'min': 0.0, 'max': 1.0},
    'ROIC': {'min': -0.5, 'max': 1.0},
    'ROE': {'min': -0.5, 'max': 2.0},
    'gross_margin': {'min': -1.0, 'max': 1.0},
    'net_margin': {'min': -1.0, 'max': 0.5},
}

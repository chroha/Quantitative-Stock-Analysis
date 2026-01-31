"""
Macro Data Configuration
Parameters for macro economic data fetching and analysis.
"""

# Lookback periods for different data series
LOOKBACK_PERIODS = {
    'GS2_days': 60,          # 2-year Treasury yield
    'VIX_days': 10,          # VIX volatility index
    'USDJPY_days': 10,       # USD/JPY exchange rate
    'cpi_months': 13,        # CPI history for YoY calculation
}

# Cache TTL (time-to-live) in seconds
CACHE_TTL = {
    'fred_data': 3600,           # 1 hour for FRED data
    'fred_cpi': 86400,           # 24 hours for CPI (monthly data)
    'yahoo_market_hours': 300,   # 5 minutes during market hours
    'yahoo_after_hours': 3600,   # 1 hour after market close
}

# Trend analysis thresholds
TREND_THRESHOLDS = {
    'slope_rising': 0.1,         # Slope > 0.1 = rising trend
    'slope_declining': -0.1,     # Slope < -0.1 = declining trend
}

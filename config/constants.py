"""
Centralized constants for the application.
Stores API base URLs, timeouts, and other magic numbers.
"""

from typing import Dict

# --- API Configuration ---

# Financial Modeling Prep (FMP)
FMP_BASE_URL = "https://financialmodelingprep.com/stable"
FMP_TIMEOUT_SECONDS = 10
FMP_RETRIES = 3

# Alpha Vantage
ALPHAVANTAGE_BASE_URL = "https://www.alphavantage.co/query"
ALPHAVANTAGE_TIMEOUT_SECONDS = 30
ALPHAVANTAGE_MIN_REQUEST_INTERVAL = 1.5  # seconds
ALPHAVANTAGE_RETRIES = 3

# Finnhub
FINNHUB_BASE_URL = "https://finnhub.io/api/v1"
FINNHUB_TIMEOUT_SECONDS = 15
FINNHUB_RETRIES = 3

# Yahoo Finance (yfinance)
YAHOO_TIMEOUT_SECONDS = 20

# EDGAR (SEC)
EDGAR_USER_AGENT = "QuantitativeStockAnalysis/3.0 (contact@example.com)"

# --- Data Processing ---

# Default years of data to fetch
DEFAULT_YEARS_HISTORY = 5
DEFAULT_QUARTERS_HISTORY = 4

# --- Data Directory Paths (relative to project root) ---
# Unified data storage structure
DATA_CACHE_STOCK = "data/cache/stock"         # Per-stock analysis outputs
DATA_CACHE_MACRO = "data/cache/macro"         # Macro economic snapshots
DATA_CACHE_BENCHMARK = "data/cache/benchmark" # Industry benchmark data
DATA_REPORTS = "generated_reports"            # Human-readable reports

# --- API Endpoints ---
FMP_ENDPOINTS: Dict[str, str] = {
    'profile': 'profile',
    'price_target': 'price-target-consensus',
    'income_statement': 'income-statement',
    'balance_sheet': 'balance-sheet-statement',
    'cash_flow': 'cash-flow-statement',
    'ratios': 'ratios',
    'key_metrics': 'key-metrics',
    'financial_growth': 'financial-growth',
    'analyst_estimates': 'analyst-estimates',
}

ALPHAVANTAGE_FUNCTIONS: Dict[str, str] = {
    'overview': 'OVERVIEW',
    'income_statement': 'INCOME_STATEMENT',
    'balance_sheet': 'BALANCE_SHEET',
    'cash_flow': 'CASH_FLOW',
}

FINNHUB_ENDPOINTS: Dict[str, str] = {
    'profile': 'stock/profile2',
    'earnings_calendar': 'calendar/earnings',
    'earnings_estimates': 'stock/earnings',
    'revenue_estimates': 'stock/revenue-estimates',
    'eps_estimates': 'stock/eps-estimates',
    'ebitda_estimates': 'stock/ebitda-estimates',
}

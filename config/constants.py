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

# Yahoo Finance (yfinance)
YAHOO_TIMEOUT_SECONDS = 20

# EDGAR (SEC)
EDGAR_USER_AGENT = "QuantitativeStockAnalysis/3.0 (contact@example.com)"

# --- Data Processing ---

# Default years of data to fetch
DEFAULT_YEARS_HISTORY = 5
DEFAULT_QUARTERS_HISTORY = 4

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

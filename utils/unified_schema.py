"""
Unified Data Schema - The System's "Constitution"
=================================================

This module defines the standardized field names, data models, and source mappings
used throughout the entire Quantitative Stock Analysis system.

Field Naming Convention
-----------------------
All standardized fields start with "std_" prefix to distinguish from raw source fields.

Unit Conventions (CRITICAL for Accuracy)
----------------------------------------
- **Monetary Values** (revenue, net_income, debt, etc.):
  - Unit: Raw USD value (NOT in millions/billions)
  - Example: $1.5 billion = 1_500_000_000.0
  
- **Ratio Values** (margins, ROE, ROA, growth rates, yields):
  - Unit: Decimal (NOT percentage)
  - Example: 15% = 0.15, not 15.0
  
- **Per-Share Values** (EPS, book value per share):
  - Unit: Raw USD per share
  - Example: $5.50 per share = 5.50

- **Multiplier Ratios** (PE, PB, PS, EV/EBITDA):
  - Unit: Pure ratio (no conversion needed)
  - Example: PE of 25x = 25.0

Data Source Priority (4-Tier Cascade)
-------------------------------------
1. Yahoo Finance (primary, real-time)
2. SEC EDGAR (official filings)
3. FMP (supplementary)
4. Alpha Vantage (fallback)

Each FieldWithSource tracks both value and source for provenance.

Define standardized field names and data models using Pydantic to ensure type safety.
"""

from datetime import datetime
from typing import Optional, Literal, Dict, Any, List
from pydantic import BaseModel, Field

# Data source types for provenance tracking
# Extended to support 4-tier cascade: Yahoo > FMP > Alpha Vantage > SEC EDGAR
DataSource = Literal['yahoo', 'fmp', 'alphavantage', 'sec_edgar', 'finnhub', 'manual', 'normalized']


class FieldWithSource(BaseModel):
    """Numeric field with source tracking."""
    value: Optional[float] = None
    source: Optional[DataSource] = None


class TextFieldWithSource(BaseModel):
    """Text field with source tracking."""
    value: Optional[str] = None
    source: Optional[DataSource] = None


class PriceData(BaseModel):
    """
    Price data model with unified field names.
    Use standardized field names.
    """
    std_date: Optional[datetime] = Field(None, description="Date of price data")
    std_open: Optional[FieldWithSource] = Field(None, description="Opening price")
    std_high: Optional[FieldWithSource] = Field(None, description="High price")
    std_low: Optional[FieldWithSource] = Field(None, description="Low price")
    std_close: Optional[FieldWithSource] = Field(None, description="Closing price")
    std_adjusted_close: Optional[FieldWithSource] = Field(None, description="Adjusted closing price")
    std_volume: Optional[FieldWithSource] = Field(None, description="Trading volume")


class IncomeStatement(BaseModel):
    """
    Income statement model with unified field names.
    Use standardized field names.
    """
    std_period: Optional[str] = Field(None, description="Period (e.g., '2024-Q4', '2024-FY')")
    std_period_type: Literal['FY', 'Q', 'TTM'] = Field('FY', description="Period type: Fiscal Year, Quarter, or TTM")
    std_revenue: Optional[FieldWithSource] = Field(None, description="Total revenue")
    std_cost_of_revenue: Optional[FieldWithSource] = Field(None, description="Cost of revenue")
    std_gross_profit: Optional[FieldWithSource] = Field(None, description="Gross profit")
    std_operating_expenses: Optional[FieldWithSource] = Field(None, description="Operating expenses")
    std_operating_income: Optional[FieldWithSource] = Field(None, description="Operating income")
    std_pretax_income: Optional[FieldWithSource] = Field(None, description="Income before tax")
    std_interest_expense: Optional[FieldWithSource] = Field(None, description="Interest expense")
    std_income_tax_expense: Optional[FieldWithSource] = Field(None, description="Income tax expense")
    std_net_income: Optional[FieldWithSource] = Field(None, description="Net income")
    std_eps: Optional[FieldWithSource] = Field(None, description="Earnings per share (basic)")
    std_eps_diluted: Optional[FieldWithSource] = Field(None, description="Diluted EPS")
    std_shares_outstanding: Optional[FieldWithSource] = Field(None, description="Shares outstanding")
    std_ebitda: Optional[FieldWithSource] = Field(None, description="EBITDA")


class BalanceSheet(BaseModel):
    """
    Balance sheet model with unified field names.
    Use standardized field names.
    """
    std_period: Optional[str] = Field(None, description="Period (e.g., '2024-Q4', '2024-FY')")
    std_period_type: Literal['FY', 'Q', 'TTM'] = Field('FY', description="Period type: Fiscal Year, Quarter, or TTM")
    std_total_assets: Optional[FieldWithSource] = Field(None, description="Total assets")
    std_current_assets: Optional[FieldWithSource] = Field(None, description="Current assets")
    std_cash: Optional[FieldWithSource] = Field(None, description="Cash and equivalents")
    std_accounts_receivable: Optional[FieldWithSource] = Field(None, description="Accounts receivable")
    std_inventory: Optional[FieldWithSource] = Field(None, description="Inventory")
    std_total_liabilities: Optional[FieldWithSource] = Field(None, description="Total liabilities")
    std_current_liabilities: Optional[FieldWithSource] = Field(None, description="Current liabilities")
    std_total_debt: Optional[FieldWithSource] = Field(None, description="Total debt")
    std_shareholder_equity: Optional[FieldWithSource] = Field(None, description="Total shareholder equity")


class CashFlow(BaseModel):
    """
    Cash flow statement model with unified field names.
    Use standardized field names.
    """
    std_period: Optional[str] = Field(None, description="Period (e.g., '2024-Q4', '2024-FY')")
    std_period_type: Literal['FY', 'Q', 'TTM'] = Field('FY', description="Period type: Fiscal Year, Quarter, or TTM")
    std_operating_cash_flow: Optional[FieldWithSource] = Field(None, description="Operating cash flow")
    std_investing_cash_flow: Optional[FieldWithSource] = Field(None, description="Investing cash flow")
    std_financing_cash_flow: Optional[FieldWithSource] = Field(None, description="Financing cash flow")
    std_capex: Optional[FieldWithSource] = Field(None, description="Capital expenditure")
    std_free_cash_flow: Optional[FieldWithSource] = Field(None, description="Free cash flow")
    std_stock_based_compensation: Optional[FieldWithSource] = Field(None, description="Stock-based compensation expense")
    std_dividends_paid: Optional[FieldWithSource] = Field(None, description="Dividends paid (cash)")
    std_repurchase_of_stock: Optional[FieldWithSource] = Field(None, description="Stock repurchase (buyback) amount")


class AnalystTargets(BaseModel):
    """Analyst price targets and estimates."""
    std_price_target_low: Optional[FieldWithSource] = Field(None, description="Analyst price target (low)")
    std_price_target_high: Optional[FieldWithSource] = Field(None, description="Analyst price target (high)")
    std_price_target_avg: Optional[FieldWithSource] = Field(None, description="Analyst price target (average)")
    std_price_target_consensus: Optional[FieldWithSource] = Field(None, description="Consensus price target")
    std_number_of_analysts: Optional[FieldWithSource] = Field(None, description="Number of analysts")


class ForecastData(BaseModel):
    """
    Forecast and Analyst Estimates Data Model
    
    Integrates forward-looking metrics from multiple sources:
    - Yahoo Finance: forward_eps, forward_pe, earnings_growth
    - FMP: analyst estimates, price targets, ratings
    - Finnhub: earnings surprises, historical actuals vs estimates
    
    Data Source Priority:
    - Forward EPS: Yahoo > FMP > Finnhub
    - Price Targets: FMP > Yahoo
    - Earnings Surprises: Finnhub (exclusive)
    """
    
    # === Forward Metrics (Next Fiscal Year) ===
    std_forward_eps: Optional[FieldWithSource] = Field(
        None, 
        description="Forward EPS - Next fiscal year analyst consensus (USD per share)"
    )
    std_forward_pe: Optional[FieldWithSource] = Field(
        None,
        description="Forward P/E ratio based on forward EPS"
    )
    std_forward_revenue: Optional[FieldWithSource] = Field(
        None,
        description="Forward revenue estimate - Next fiscal year (USD)"
    )
    
    # === Analyst Price Targets ===
    std_price_target_low: Optional[FieldWithSource] = Field(
        None,
        description="Analyst price target - Low (USD per share)"
    )
    std_price_target_high: Optional[FieldWithSource] = Field(
        None,
        description="Analyst price target - High (USD per share)"
    )
    std_price_target_avg: Optional[FieldWithSource] = Field(
        None,
        description="Analyst price target - Average (USD per share)"
    )
    std_price_target_consensus: Optional[FieldWithSource] = Field(
        None,
        description="Consensus price target (USD per share)"
    )
    std_number_of_analysts: Optional[FieldWithSource] = Field(
        None,
        description="Number of analysts covering the stock"
    )
    
    # === Analyst Ratings Distribution ===
    std_analyst_rating_strong_buy: Optional[FieldWithSource] = Field(
        None,
        description="Number of Strong Buy ratings"
    )
    std_analyst_rating_buy: Optional[FieldWithSource] = Field(
        None,
        description="Number of Buy ratings"
    )
    std_analyst_rating_hold: Optional[FieldWithSource] = Field(
        None,
        description="Number of Hold ratings"
    )
    std_analyst_rating_sell: Optional[FieldWithSource] = Field(
        None,
        description="Number of Sell ratings"
    )
    std_analyst_rating_strong_sell: Optional[FieldWithSource] = Field(
        None,
        description="Number of Strong Sell ratings"
    )
    
    # === Earnings Estimates (Fiscal Years) ===
    std_eps_estimate_current_year: Optional[FieldWithSource] = Field(
        None,
        description="EPS estimate for current fiscal year (USD per share)"
    )
    std_eps_estimate_next_year: Optional[FieldWithSource] = Field(
        None,
        description="EPS estimate for next fiscal year (USD per share)"
    )
    std_revenue_estimate_current_year: Optional[FieldWithSource] = Field(
        None,
        description="Revenue estimate for current fiscal year (USD)"
    )
    std_revenue_estimate_next_year: Optional[FieldWithSource] = Field(
        None,
        description="Revenue estimate for next fiscal year (USD)"
    )
    std_ebitda_estimate_next_year: Optional[FieldWithSource] = Field(
        None,
        description="EBITDA estimate for next fiscal year (USD)"
    )
    
    # === Earnings Surprises (Historical Actuals vs Estimates) ===
    # Finnhub-exclusive: Track how company performed vs analyst expectations
    std_earnings_surprise_history: Optional[list[Dict[str, Any]]] = Field(
        default_factory=list,
        description="Historical earnings surprises - Actual vs Estimate comparison"
    )
    # Each dict contains:
    # {
    #   "period": "2025-12-31",
    #   "quarter": 1,
    #   "year": 2026,
    #   "actual": 2.84,
    #   "estimate": 2.7257,
    #   "surprise": 0.1143,
    #   "surprise_percent": 4.1934,
    #   "symbol": "AAPL"
    # }
    
    # === Growth Estimates ===
    std_earnings_growth_current_year: Optional[FieldWithSource] = Field(
        None,
        description="Estimated earnings growth rate for current year (decimal, e.g., 0.15 = 15%)"
    )
    std_earnings_growth_next_year: Optional[FieldWithSource] = Field(
        None,
        description="Estimated earnings growth rate for next year (decimal)"
    )
    std_revenue_growth_next_year: Optional[FieldWithSource] = Field(
        None,
        description="Estimated revenue growth rate for next year (decimal)"
    )
    
    # Metadata
    last_updated: datetime = Field(
        default_factory=datetime.now,
        description="Last forecast data update timestamp"
    )



class ETFData(BaseModel):
    """ETF data model for sector benchmarks."""
    symbol: str = Field(..., description="ETF ticker symbol")
    name: Optional[TextFieldWithSource] = Field(None, description="ETF name")
    sector: Optional[str] = Field(None, description="Sector this ETF represents")
    
    # Valuation Ratios
    pe_ratio: Optional[FieldWithSource] = Field(None, description="ETF PE ratio")
    pb_ratio: Optional[FieldWithSource] = Field(None, description="ETF PB ratio")
    ps_ratio: Optional[FieldWithSource] = Field(None, description="ETF PS (Price-to-Sales) ratio")
    forward_pe: Optional[FieldWithSource] = Field(None, description="ETF Forward PE ratio")
    
    # Dividend Metrics
    dividend_yield: Optional[FieldWithSource] = Field(None, description="Dividend yield (%)")
    dividend_rate: Optional[FieldWithSource] = Field(None, description="Annual dividend amount")
    
    # Profitability Metrics
    roe: Optional[FieldWithSource] = Field(None, description="Return on Equity (%)")
    roa: Optional[FieldWithSource] = Field(None, description="Return on Assets (%)")
    profit_margin: Optional[FieldWithSource] = Field(None, description="Profit margin (%)")
    
    # Financial Health
    debt_to_equity: Optional[FieldWithSource] = Field(None, description="Debt-to-Equity ratio")
    
    # Risk Metrics
    beta: Optional[FieldWithSource] = Field(None, description="Beta coefficient")
    
    # Market Data
    market_cap: Optional[FieldWithSource] = Field(None, description="ETF total market cap")
    price: Optional[FieldWithSource] = Field(None, description="Current ETF price")
    expense_ratio: Optional[FieldWithSource] = Field(None, description="ETF expense ratio")
    
    data_date: datetime = Field(default_factory=datetime.now, description="Data fetch timestamp")


class SectorBenchmark(BaseModel):
    """Sector benchmark data aggregated from ETF."""
    sector: str = Field(..., description="GICS sector name")
    etf_symbol: str = Field(..., description="Representative ETF symbol")
    
    # Valuation Ratios
    sector_avg_pe: Optional[float] = Field(None, description="Sector average PE ratio")
    sector_avg_pb: Optional[float] = Field(None, description="Sector average PB ratio")
    sector_avg_ps: Optional[float] = Field(None, description="Sector average PS ratio")
    sector_avg_forward_pe: Optional[float] = Field(None, description="Sector average Forward PE")
    
    # Dividend Metrics
    sector_avg_dividend_yield: Optional[float] = Field(None, description="Sector average dividend yield (%)")
    sector_avg_dividend_rate: Optional[float] = Field(None, description="Sector average dividend amount")
    
    # Profitability Metrics  
    sector_avg_roe: Optional[float] = Field(None, description="Sector average ROE (%)")
    sector_avg_roa: Optional[float] = Field(None, description="Sector average ROA (%)")
    sector_avg_profit_margin: Optional[float] = Field(None, description="Sector average profit margin (%)")
    
    # Financial Health
    sector_avg_debt_to_equity: Optional[float] = Field(None, description="Sector average Debt-to-Equity")
    
    # Risk Metrics
    sector_avg_beta: Optional[float] = Field(None, description="Sector average Beta")
    
    # Market Data
    sector_market_cap: Optional[float] = Field(None, description="Sector total market capitalization")
    etf_price: Optional[float] = Field(None, description="ETF current price")
    
    data_date: datetime = Field(default_factory=datetime.now, description="Benchmark data timestamp")


class CompanyProfile(BaseModel):
    """
    Company profile information.
    
    CRITICAL: This schema defines the allowed fields for company profile data.
    If you add new fields to YahooFetcher (or other fetchers), you MUST add them here.
    Otherwise, Pydantic will silently drop the extra fields during validation.

    """
    std_symbol: Optional[str] = Field(None, description="Stock ticker symbol")
    std_company_name: Optional[TextFieldWithSource] = Field(None, description="Company name")
    std_industry: Optional[TextFieldWithSource] = Field(None, description="Industry")
    std_sector: Optional[TextFieldWithSource] = Field(None, description="Sector")
    std_market_cap: Optional[FieldWithSource] = Field(None, description="Market capitalization")
    std_description: Optional[TextFieldWithSource] = Field(None, description="Company description")
    std_website: Optional[TextFieldWithSource] = Field(None, description="Company website")
    std_ceo: Optional[TextFieldWithSource] = Field(None, description="CEO name")
    std_beta: Optional[FieldWithSource] = Field(None, description="Stock Beta (risk coefficient)")
    std_shares_outstanding: Optional[FieldWithSource] = Field(None, description="Total shares outstanding")
    
    # Forward EPS and Valuation Fields
    std_forward_eps: Optional[FieldWithSource] = Field(None, description="Forward EPS (analyst estimate)")
    std_trailing_eps: Optional[FieldWithSource] = Field(None, description="Trailing Twelve Month EPS")
    std_forward_pe: Optional[FieldWithSource] = Field(None, description="Forward P/E ratio")
    std_peg_ratio: Optional[FieldWithSource] = Field(None, description="PEG Ratio (PE / EPS Growth)")
    std_earnings_growth: Optional[FieldWithSource] = Field(None, description="Earnings growth rate (decimal)")
    
    # Missing Valuation Fields Added 2026-01-20
    std_pe_ratio: Optional[FieldWithSource] = Field(None, description="Trailing P/E Ratio")
    std_pb_ratio: Optional[FieldWithSource] = Field(None, description="Price to Book Ratio")
    std_ps_ratio: Optional[FieldWithSource] = Field(None, description="Price to Sales Ratio")
    std_eps: Optional[FieldWithSource] = Field(None, description="Earnings Per Share (Basis)")
    std_book_value_per_share: Optional[FieldWithSource] = Field(None, description="Book Value Per Share")
    std_dividend_yield: Optional[FieldWithSource] = Field(None, description="Dividend Yield")
    
    # Currency Fields (for ADR/International Stock Normalization)
    std_financial_currency: Optional[TextFieldWithSource] = Field(None, description="Currency used in financial statements (e.g., 'TWD')")
    std_listing_currency: Optional[TextFieldWithSource] = Field(None, description="Currency stock is listed in (e.g., 'USD')")

    # New Fields Added 2026-02-01 (Ownership, Short Interest, Advanced Valuation)
    std_held_percent_insiders: Optional[FieldWithSource] = Field(None, description="Percentage of shares held by insiders")
    std_held_percent_institutions: Optional[FieldWithSource] = Field(None, description="Percentage of shares held by institutions")
    std_short_ratio: Optional[FieldWithSource] = Field(None, description="Short ratio (days to cover)")
    std_short_percent_of_float: Optional[FieldWithSource] = Field(None, description="Short percentage of float")
    std_enterprise_value: Optional[FieldWithSource] = Field(None, description="Enterprise Value")
    std_enterprise_to_ebitda: Optional[FieldWithSource] = Field(None, description="Enterprise Value to EBITDA")

    # New Fields Added 2026-02-01 (Round 2: Analyst, Risk, Per Share)
    std_recommendation_key: Optional[TextFieldWithSource] = Field(None, description="Analyst recommendation key (buy, hold, etc)")
    std_52_week_change: Optional[FieldWithSource] = Field(None, description="52 Week Price Change (%)")
    std_sandp_52_week_change: Optional[FieldWithSource] = Field(None, description="S&P 500 52 Week Change (%)")
    std_current_ratio: Optional[FieldWithSource] = Field(None, description="Current Ratio (MRQ)")
    std_quick_ratio: Optional[FieldWithSource] = Field(None, description="Quick Ratio (MRQ)")
    std_audit_risk: Optional[FieldWithSource] = Field(None, description="Audit Risk Score")
    std_board_risk: Optional[FieldWithSource] = Field(None, description="Board Risk Score")
    std_total_cash_per_share: Optional[FieldWithSource] = Field(None, description="Total Cash Per Share")
    std_revenue_per_share: Optional[FieldWithSource] = Field(None, description="Revenue Per Share")


class StockData(BaseModel):
    """
    Complete stock data model combining all categories.
    This is the primary data structure used throughout the system.
    """
    symbol: str = Field(..., description="Stock ticker symbol")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last data update timestamp")
    
    # Data categories
    profile: Optional[CompanyProfile] = None
    price_history: list[PriceData] = Field(default_factory=list, description="Historical price data")
    income_statements: list[IncomeStatement] = Field(default_factory=list, description="Income statements")
    balance_sheets: list[BalanceSheet] = Field(default_factory=list, description="Balance sheets")
    cash_flows: list[CashFlow] = Field(default_factory=list, description="Cash flow statements")
    
    # Analyst & Forecast Data
    analyst_targets: Optional[AnalystTargets] = None  # DEPRECATED: Use forecast_data instead (kept for compatibility)
    forecast_data: Optional[ForecastData] = Field(
        None,
        description="Forward-looking metrics and analyst estimates (Yahoo/FMP/Finnhub)"
    )
    
    sector_benchmark: Optional[SectorBenchmark] = Field(None, description="Sector benchmark data for comparison")
    
    # Metadata for processing flags (e.g. source tracking)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Auxiliary processing metadata")


# =============================================================================
# YAHOO FINANCE FIELD MAPPING
# =============================================================================
# Maps Yahoo Finance raw field names -> Unified schema field names
#
# Unit Reference:
# - Price fields: USD per share
# - Volume: Number of shares traded
# - Revenue/Income/Expense fields: Raw USD (not millions)
# - EPS fields: USD per share
# - Cash flow fields: Raw USD
# =============================================================================
YAHOO_FIELD_MAPPING = {
    # Price data (Unit: USD per share, except Volume which is count)
    'Open': 'std_open',
    'High': 'std_high',
    'Low': 'std_low',
    'Close': 'std_close',
    'Adj Close': 'std_adjusted_close',
    'Volume': 'std_volume',
    
    # Income statement (Unit: Raw USD)
    'Total Revenue': 'std_revenue',
    'Cost Of Revenue': 'std_cost_of_revenue',
    'Gross Profit': 'std_gross_profit',
    'Operating Expense': 'std_operating_expenses',
    'Operating Income': 'std_operating_income',
    'Pretax Income': 'std_pretax_income',
    'Interest Expense': 'std_interest_expense',
    'Tax Provision': 'std_income_tax_expense',
    'Net Income': 'std_net_income',
    'Basic EPS': 'std_eps',           # Unit: USD per share
    'Diluted EPS': 'std_eps_diluted', # Unit: USD per share
    'Basic Average Shares': 'std_shares_outstanding',  # Unit: Count
    'EBITDA': 'std_ebitda',
    
    # Balance sheet (Unit: Raw USD)
    'Total Assets': 'std_total_assets',
    'Current Assets': 'std_current_assets',
    'Cash And Cash Equivalents': 'std_cash',
    'Accounts Receivable': 'std_accounts_receivable',
    'Inventory': 'std_inventory',
    'Total Liabilities Net Minority Interest': 'std_total_liabilities',
    'Current Liabilities': 'std_current_liabilities',
    'Total Debt': 'std_total_debt',
    'Stockholders Equity': 'std_shareholder_equity',
    
    # Cash flow (Unit: Raw USD, negative = outflow)
    'Operating Cash Flow': 'std_operating_cash_flow',
    'Investing Cash Flow': 'std_investing_cash_flow',
    'Financing Cash Flow': 'std_financing_cash_flow',
    'Capital Expenditure': 'std_capex',
    'Free Cash Flow': 'std_free_cash_flow',
    'Stock Based Compensation': 'std_stock_based_compensation',
    'Repurchase Of Capital Stock': 'std_repurchase_of_stock',
    'Common Stock Repurchased': 'std_repurchase_of_stock',  # Alternative name
    'Cash Dividends Paid': 'std_dividends_paid',
    'Dividends Paid': 'std_dividends_paid',
}

# FMP field names -> Unified schema names
FMP_FIELD_MAPPING = {
    # Price data
    'open': 'std_open',
    'high': 'std_high',
    'low': 'std_low',
    'close': 'std_close',
    'adjClose': 'std_adjusted_close',
    'volume': 'std_volume',
    
    # Analyst targets
    'targetLow': 'std_price_target_low',
    'targetHigh': 'std_price_target_high',
    'targetMean': 'std_price_target_avg',
    'targetConsensus': 'std_price_target_consensus',
    'numberOfAnalysts': 'std_number_of_analysts',
    
    # Company profile
    'companyName': 'std_company_name',
    'industry': 'std_industry',
    'sector': 'std_sector',
    'mktCap': 'std_market_cap',
    'description': 'std_description',
    'website': 'std_website',
    'ceo': 'std_ceo',
    
    # Cash flow (FMP has this field)
    # Cash flow (FMP has this field)
    'stockBasedCompensation': 'std_stock_based_compensation',
    'commonStockRepurchased': 'std_repurchase_of_stock',
    'dividendsPaid': 'std_dividends_paid',
}

# =============================================================================
# NEW DATA MODELS (2026-02-16) - Finnhub Expansion
# =============================================================================

class NewsItem(BaseModel):
    """News item from Finnhub or other sources."""
    id: str = Field(..., description="Unique news ID")
    category: str = Field(..., description="News category (company, top news, etc)")
    datetime: int = Field(..., description="Unix timestamp")
    headline: str = Field(..., description="News headline")
    source: str = Field(..., description="News source")
    url: str = Field(..., description="Link to original article")
    summary: Optional[str] = Field(None, description="Short summary/abstract")
    related: Optional[str] = Field(None, description="Related tickers")
    image: Optional[str] = Field(None, description="Image URL")

class InsiderTransaction(BaseModel):
    """Insider transaction record."""
    name: str = Field(..., description="Insider name")
    share: int = Field(..., description="Number of shares held after transaction")
    change: int = Field(..., description="Number of shares changed")
    filing_date: str = Field(..., description="Filing date")
    transaction_date: str = Field(..., description="Transaction date")
    transaction_price: float = Field(..., description="Transaction price")
    transaction_code: Optional[str] = Field(None, description="Transaction code")
    
class InsiderSentiment(BaseModel):
    """Insider sentiment metrics (Finnhub specific)."""
    year: int
    month: int
    change: float = Field(..., description="Net buying/selling share count")
    mspr: float = Field(..., description="Monthly Share Purchase Ratio")

class SentimentData(BaseModel):
    """Container for sentiment and insider data."""
    insider_sentiment: List[InsiderSentiment] = Field(default_factory=list)
    insider_transactions: List[InsiderTransaction] = Field(default_factory=list)

# Update StockData to include new fields
# Note: We cannot easily modify the existing StockData class in-place without re-declaring it.
# Users should use this updated definition.

# Re-declare StockData with new fields (News, Sentiment)
class StockData(BaseModel):
    """
    Complete stock data model combining all categories.
    This is the primary data structure used throughout the system.
    """
    symbol: str = Field(..., description="Stock ticker symbol")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last data update timestamp")
    
    # Data categories
    profile: Optional[CompanyProfile] = None
    price_history: list[PriceData] = Field(default_factory=list, description="Historical price data")
    income_statements: list[IncomeStatement] = Field(default_factory=list, description="Income statements")
    balance_sheets: list[BalanceSheet] = Field(default_factory=list, description="Balance sheets")
    cash_flows: list[CashFlow] = Field(default_factory=list, description="Cash flow statements")
    
    # Analyst & Forecast Data
    analyst_targets: Optional[AnalystTargets] = None  # DEPRECATED: Use forecast_data instead
    forecast_data: Optional[ForecastData] = Field(
        None,
        description="Forward-looking metrics and analyst estimates (Yahoo/FMP/Finnhub)"
    )
    
    sector_benchmark: Optional[SectorBenchmark] = Field(None, description="Sector benchmark data for comparison")
    
    # NEW: News & Sentiment
    news: List[NewsItem] = Field(default_factory=list, description="Recent news items")
    sentiment: Optional[SentimentData] = Field(None, description="Insider sentiment and transaction data")
    
    # NEW: Peers (Simple list)
    peers: List[str] = Field(default_factory=list, description="List of peer ticker symbols")
    
    # Metadata for processing flags (e.g. source tracking)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Auxiliary processing metadata")



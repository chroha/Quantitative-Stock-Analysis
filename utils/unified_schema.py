"""
Unified data schema - The system's "constitution".
Defines standardized field names and data models using Pydantic for type safety.

统一数据架构 - 系统的"宪法"。
使用 Pydantic 定义标准化的字段名称和数据模型，以确保类型安全。
"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


# Data source types for provenance tracking
# Extended to support 4-tier cascade: Yahoo > FMP > Alpha Vantage > SEC EDGAR
DataSource = Literal['yahoo', 'fmp', 'alphavantage', 'sec_edgar', 'manual']


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
    价格数据模型，使用统一字段名。
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
    利润表模型，使用统一字段名。
    """
    std_period: Optional[str] = Field(None, description="Period (e.g., '2024-Q4', '2024-FY')")
    std_revenue: Optional[FieldWithSource] = Field(None, description="Total revenue")
    std_cost_of_revenue: Optional[FieldWithSource] = Field(None, description="Cost of revenue")
    std_gross_profit: Optional[FieldWithSource] = Field(None, description="Gross profit")
    std_operating_expenses: Optional[FieldWithSource] = Field(None, description="Operating expenses")
    std_operating_income: Optional[FieldWithSource] = Field(None, description="Operating income")
    std_pretax_income: Optional[FieldWithSource] = Field(None, description="Income before tax")
    std_income_tax_expense: Optional[FieldWithSource] = Field(None, description="Income tax expense")
    std_net_income: Optional[FieldWithSource] = Field(None, description="Net income")
    std_eps: Optional[FieldWithSource] = Field(None, description="Earnings per share (basic)")
    std_eps_diluted: Optional[FieldWithSource] = Field(None, description="Diluted EPS")
    std_shares_outstanding: Optional[FieldWithSource] = Field(None, description="Shares outstanding")
    std_ebitda: Optional[FieldWithSource] = Field(None, description="EBITDA")


class BalanceSheet(BaseModel):
    """
    Balance sheet model with unified field names.
    资产负债表模型，使用统一字段名。
    """
    std_period: Optional[str] = Field(None, description="Period (e.g., '2024-Q4', '2024-FY')")
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
    现金流量表模型，使用统一字段名。
    """
    std_period: Optional[str] = Field(None, description="Period (e.g., '2024-Q4', '2024-FY')")
    std_operating_cash_flow: Optional[FieldWithSource] = Field(None, description="Operating cash flow")
    std_investing_cash_flow: Optional[FieldWithSource] = Field(None, description="Investing cash flow")
    std_financing_cash_flow: Optional[FieldWithSource] = Field(None, description="Financing cash flow")
    std_capex: Optional[FieldWithSource] = Field(None, description="Capital expenditure")
    std_free_cash_flow: Optional[FieldWithSource] = Field(None, description="Free cash flow")
    std_stock_based_compensation: Optional[FieldWithSource] = Field(None, description="Stock-based compensation expense")
    std_dividends_paid: Optional[FieldWithSource] = Field(None, description="Dividends paid (cash)")


class AnalystTargets(BaseModel):
    """Analyst price targets and estimates."""
    std_price_target_low: Optional[FieldWithSource] = Field(None, description="Analyst price target (low)")
    std_price_target_high: Optional[FieldWithSource] = Field(None, description="Analyst price target (high)")
    std_price_target_avg: Optional[FieldWithSource] = Field(None, description="Analyst price target (average)")
    std_price_target_consensus: Optional[FieldWithSource] = Field(None, description="Consensus price target")
    std_number_of_analysts: Optional[FieldWithSource] = Field(None, description="Number of analysts")


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
    """Company profile information."""
    std_symbol: Optional[str] = Field(None, description="Stock ticker symbol")
    std_company_name: Optional[TextFieldWithSource] = Field(None, description="Company name")
    std_industry: Optional[TextFieldWithSource] = Field(None, description="Industry")
    std_sector: Optional[TextFieldWithSource] = Field(None, description="Sector")
    std_market_cap: Optional[FieldWithSource] = Field(None, description="Market capitalization")
    std_description: Optional[TextFieldWithSource] = Field(None, description="Company description")
    std_website: Optional[TextFieldWithSource] = Field(None, description="Company website")
    std_ceo: Optional[TextFieldWithSource] = Field(None, description="CEO name")
    std_beta: Optional[FieldWithSource] = Field(None, description="Stock Beta (risk coefficient)")


class StockData(BaseModel):
    """
    Complete stock data model combining all categories.
    This is the primary data structure used throughout the system.

    股票完整数据模型，包含所有类别的数据。
    这是整个系统中使用的主要数据结构。
    """
    symbol: str = Field(..., description="Stock ticker symbol")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last data update timestamp")
    
    # Data categories
    profile: Optional[CompanyProfile] = None
    price_history: list[PriceData] = Field(default_factory=list, description="Historical price data")
    income_statements: list[IncomeStatement] = Field(default_factory=list, description="Income statements")
    balance_sheets: list[BalanceSheet] = Field(default_factory=list, description="Balance sheets")
    cash_flows: list[CashFlow] = Field(default_factory=list, description="Cash flow statements")
    analyst_targets: Optional[AnalystTargets] = None
    sector_benchmark: Optional[SectorBenchmark] = Field(None, description="Sector benchmark data for comparison")


# Field mapping dictionaries
# Yahoo Finance field names -> Unified schema names
YAHOO_FIELD_MAPPING = {
    # Price data
    'Open': 'std_open',
    'High': 'std_high',
    'Low': 'std_low',
    'Close': 'std_close',
    'Adj Close': 'std_adjusted_close',
    'Volume': 'std_volume',
    
    # Income statement
    'Total Revenue': 'std_revenue',
    'Cost Of Revenue': 'std_cost_of_revenue',
    'Gross Profit': 'std_gross_profit',
    'Operating Expense': 'std_operating_expenses',
    'Operating Income': 'std_operating_income',
    'Pretax Income': 'std_pretax_income',
    'Tax Provision': 'std_income_tax_expense',
    'Net Income': 'std_net_income',
    'Basic EPS': 'std_eps',
    'Diluted EPS': 'std_eps_diluted',
    'Basic Average Shares': 'std_shares_outstanding',
    'EBITDA': 'std_ebitda',
    
    # Balance sheet
    'Total Assets': 'std_total_assets',
    'Current Assets': 'std_current_assets',
    'Cash And Cash Equivalents': 'std_cash',
    'Accounts Receivable': 'std_accounts_receivable',
    'Inventory': 'std_inventory',
    'Total Liabilities Net Minority Interest': 'std_total_liabilities',
    'Current Liabilities': 'std_current_liabilities',
    'Total Debt': 'std_total_debt',
    'Stockholders Equity': 'std_shareholder_equity',
    
    # Cash flow
    'Operating Cash Flow': 'std_operating_cash_flow',
    'Investing Cash Flow': 'std_investing_cash_flow',
    'Financing Cash Flow': 'std_financing_cash_flow',
    'Capital Expenditure': 'std_capex',
    'Free Cash Flow': 'std_free_cash_flow',
    'Stock Based Compensation': 'std_stock_based_compensation',
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
    'stockBasedCompensation': 'std_stock_based_compensation',
}

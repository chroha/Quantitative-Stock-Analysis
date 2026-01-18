"""
Yahoo Finance data fetcher.
Primary data source for financial statements and price data.
[INTERNAL PROCESS MODULE] - This module is used by StockDataLoader, do not call directly.

[INTERNAL PROCESS MODULE] - This module is used by StockDataLoader, do not call directly.
"""

import yfinance as yf
import pandas as pd
from typing import Optional
from datetime import datetime
from utils.logger import setup_logger
from utils.unified_schema import (
    StockData, PriceData, IncomeStatement, BalanceSheet, CashFlow,
    CompanyProfile, AnalystTargets, FieldWithSource, TextFieldWithSource, YAHOO_FIELD_MAPPING
)

logger = setup_logger('yahoo_fetcher')


class YahooFetcher:
    """Fetches data from Yahoo Finance and maps to unified schema."""
    
    def __init__(self, symbol: str):
        """
        Initialize Yahoo fetcher for a specific symbol.
        
        Args:
            symbol: Stock ticker symbol
        """
        self.symbol = symbol.upper()
        self.ticker = None
        logger.info(f"Initializing Yahoo fetcher for {self.symbol}")
    
    def _create_field_with_source(self, value) -> Optional[FieldWithSource]:
        """
        Create FieldWithSource object from value.
        
        Args:
            value: Raw value from Yahoo Finance
            
        Returns:
            FieldWithSource object or None if value is missing
        """
        if pd.isna(value):
            return None
        
        try:
            return FieldWithSource(value=float(value), source='yahoo')
        except (ValueError, TypeError):
            return None
    
    def fetch_profile(self) -> Optional[CompanyProfile]:
        """
        Fetch company profile information.
        
        Returns:
            CompanyProfile object or None if fetch fails
        """
        try:
            self.ticker = yf.Ticker(self.symbol)
            info = self.ticker.info
            
            logger.info(f"Fetched company profile for {self.symbol}")
            
            return CompanyProfile(
                std_symbol=self.symbol,
                std_company_name=TextFieldWithSource(value=info.get('longName', ''), source='yahoo') if info.get('longName') else None,
                std_industry=TextFieldWithSource(value=info.get('industry', ''), source='yahoo') if info.get('industry') else None,
                std_sector=TextFieldWithSource(value=info.get('sector', ''), source='yahoo') if info.get('sector') else None,
                std_market_cap=self._create_field_with_source(info.get('marketCap')),
                std_description=TextFieldWithSource(value=info.get('longBusinessSummary', ''), source='yahoo') if info.get('longBusinessSummary') else None,
                std_website=TextFieldWithSource(value=info.get('website', ''), source='yahoo') if info.get('website') else None,
                std_beta=self._create_field_with_source(info.get('beta')),  # Stock-specific Beta
            )
        
        except Exception as e:
            logger.error(f"Failed to fetch profile from Yahoo: {e}")
            return None
    
    def fetch_analyst_targets(self) -> Optional[AnalystTargets]:
        """
        Fetch analyst price targets from Yahoo Finance.
        
        Returns:
            AnalystTargets object or None if fetch fails
        """
        try:
            if not self.ticker:
                self.ticker = yf.Ticker(self.symbol)
            
            info = self.ticker.info
            
            # Extract analyst targets from info dict
            targets = AnalystTargets(
                std_price_target_low=self._create_field_with_source(info.get('targetLowPrice')),
                std_price_target_high=self._create_field_with_source(info.get('targetHighPrice')),
                std_price_target_avg=self._create_field_with_source(info.get('targetMeanPrice')),
                std_price_target_consensus=self._create_field_with_source(info.get('targetMedianPrice')),
                std_number_of_analysts=self._create_field_with_source(info.get('numberOfAnalystOpinions')),
            )
            
            # Check if any data was actually fetched
            if any([targets.std_price_target_low, targets.std_price_target_high, targets.std_price_target_avg]):
                logger.info(f"Fetched analyst targets for {self.symbol} from Yahoo")
                return targets
            else:
                logger.warning(f"No analyst target data available for {self.symbol} from Yahoo")
                return None
        
        except Exception as e:
            logger.error(f"Failed to fetch analyst targets from Yahoo: {e}")
            return None
    
    def fetch_price_history(self, period: str = "1y") -> list[PriceData]:
        """
        Fetch historical price data.
        
        Args:
            period: Time period (e.g., '1mo', '3mo', '1y', '5y')
            
        Returns:
            List of PriceData objects
        """
        try:
            if not self.ticker:
                self.ticker = yf.Ticker(self.symbol)
            
            hist = self.ticker.history(period=period)
            logger.info(f"Fetched {len(hist)} days of price history for {self.symbol}")
            
            price_data_list = []
            for date, row in hist.iterrows():
                price_data = PriceData(
                    std_date=date.to_pydatetime(),
                    std_open=self._create_field_with_source(row.get('Open')),
                    std_high=self._create_field_with_source(row.get('High')),
                    std_low=self._create_field_with_source(row.get('Low')),
                    std_close=self._create_field_with_source(row.get('Close')),
                    std_adjusted_close=self._create_field_with_source(row.get('Close')),  # Yahoo returns adjusted by default
                    std_volume=self._create_field_with_source(row.get('Volume')),
                )
                price_data_list.append(price_data)
            
            return price_data_list
        
        except Exception as e:
            logger.error(f"Failed to fetch price history from Yahoo: {e}")
            return []
    
    def _parse_financial_statement(self, df: pd.DataFrame, statement_type: str) -> list:
        """
        Parse financial statement DataFrame to unified schema.
        
        Args:
            df: DataFrame from yfinance
            statement_type: 'income', 'balance', or 'cashflow'
            
        Returns:
            List of statement objects
        """
        if df is None or df.empty:
            logger.warning(f"No {statement_type} statement data available")
            return []
        
        statements = []
        
        # Iterate through each column (period)
        for col in df.columns:
            period_str = col.strftime('%Y-%m-%d') if isinstance(col, pd.Timestamp) else str(col)
            
            if statement_type == 'income':
                stmt = IncomeStatement(
                    std_period=period_str,
                    std_revenue=self._create_field_with_source(df.loc['Total Revenue', col]) if 'Total Revenue' in df.index else None,
                    std_cost_of_revenue=self._create_field_with_source(df.loc['Cost Of Revenue', col]) if 'Cost Of Revenue' in df.index else None,
                    std_gross_profit=self._create_field_with_source(df.loc['Gross Profit', col]) if 'Gross Profit' in df.index else None,
                    std_operating_expenses=self._create_field_with_source(df.loc['Operating Expense', col]) if 'Operating Expense' in df.index else None,
                    std_operating_income=self._create_field_with_source(df.loc['Operating Income', col]) if 'Operating Income' in df.index else None,
                    std_pretax_income=self._create_field_with_source(df.loc['Pretax Income', col]) if 'Pretax Income' in df.index else None,
                    std_income_tax_expense=self._create_field_with_source(df.loc['Tax Provision', col]) if 'Tax Provision' in df.index else None,
                    std_net_income=self._create_field_with_source(df.loc['Net Income', col]) if 'Net Income' in df.index else None,
                    std_eps=self._create_field_with_source(df.loc['Basic EPS', col]) if 'Basic EPS' in df.index else None,
                    std_eps_diluted=self._create_field_with_source(df.loc['Diluted EPS', col]) if 'Diluted EPS' in df.index else None,
                    std_shares_outstanding=self._create_field_with_source(df.loc['Basic Average Shares', col]) if 'Basic Average Shares' in df.index else None,
                    std_ebitda=self._create_field_with_source(df.loc['EBITDA', col]) if 'EBITDA' in df.index else None,
                )
                statements.append(stmt)
            
            elif statement_type == 'balance':
                stmt = BalanceSheet(
                    std_period=period_str,
                    std_total_assets=self._create_field_with_source(df.loc['Total Assets', col]) if 'Total Assets' in df.index else None,
                    std_current_assets=self._create_field_with_source(df.loc['Current Assets', col]) if 'Current Assets' in df.index else None,
                    std_cash=self._create_field_with_source(df.loc['Cash And Cash Equivalents', col]) if 'Cash And Cash Equivalents' in df.index else None,
                    std_total_liabilities=self._create_field_with_source(df.loc['Total Liabilities Net Minority Interest', col]) if 'Total Liabilities Net Minority Interest' in df.index else None,
                    std_current_liabilities=self._create_field_with_source(df.loc['Current Liabilities', col]) if 'Current Liabilities' in df.index else None,
                    std_total_debt=self._create_field_with_source(df.loc['Total Debt', col]) if 'Total Debt' in df.index else None,
                    std_shareholder_equity=self._create_field_with_source(df.loc['Stockholders Equity', col]) if 'Stockholders Equity' in df.index else None,
                )
                statements.append(stmt)
            
            elif statement_type == 'cashflow':
                stmt = CashFlow(
                    std_period=period_str,
                    std_operating_cash_flow=self._create_field_with_source(df.loc['Operating Cash Flow', col]) if 'Operating Cash Flow' in df.index else None,
                    std_investing_cash_flow=self._create_field_with_source(df.loc['Investing Cash Flow', col]) if 'Investing Cash Flow' in df.index else None,
                    std_financing_cash_flow=self._create_field_with_source(df.loc['Financing Cash Flow', col]) if 'Financing Cash Flow' in df.index else None,
                    std_capex=self._create_field_with_source(df.loc['Capital Expenditure', col]) if 'Capital Expenditure' in df.index else None,
                    std_free_cash_flow=self._create_field_with_source(df.loc['Free Cash Flow', col]) if 'Free Cash Flow' in df.index else None,
                    std_stock_based_compensation=self._create_field_with_source(df.loc['Stock Based Compensation', col]) if 'Stock Based Compensation' in df.index else None,
                    std_dividends_paid=self._create_field_with_source(df.loc['Cash Dividends Paid', col]) if 'Cash Dividends Paid' in df.index else (self._create_field_with_source(df.loc['Dividends Paid', col]) if 'Dividends Paid' in df.index else None),
                )
                statements.append(stmt)
        
        logger.info(f"Parsed {len(statements)} {statement_type} statements")
        return statements
    
    def fetch_income_statements(self) -> list[IncomeStatement]:
        """Fetch income statements."""
        try:
            if not self.ticker:
                self.ticker = yf.Ticker(self.symbol)
            
            income_stmt = self.ticker.financials
            return self._parse_financial_statement(income_stmt, 'income')
        
        except Exception as e:
            logger.error(f"Failed to fetch income statements from Yahoo: {e}")
            return []
    
    def fetch_balance_sheets(self) -> list[BalanceSheet]:
        """Fetch balance sheets."""
        try:
            if not self.ticker:
                self.ticker = yf.Ticker(self.symbol)
            
            balance_sheet = self.ticker.balance_sheet
            return self._parse_financial_statement(balance_sheet, 'balance')
        
        except Exception as e:
            logger.error(f"Failed to fetch balance sheets from Yahoo: {e}")
            return []
    
    def fetch_cash_flows(self) -> list[CashFlow]:
        """Fetch cash flow statements."""
        try:
            if not self.ticker:
                self.ticker = yf.Ticker(self.symbol)
            
            cash_flow = self.ticker.cashflow
            return self._parse_financial_statement(cash_flow, 'cashflow')
        
        except Exception as e:
            logger.error(f"Failed to fetch cash flows from Yahoo: {e}")
            return []
    
    def fetch_all(self) -> StockData:
        """
        Fetch all available data from Yahoo Finance.
        
        Returns:
            StockData object populated with Yahoo data
        """
        logger.info(f"Starting complete data fetch for {self.symbol} from Yahoo Finance")
        
        stock_data = StockData(
            symbol=self.symbol,
            profile=self.fetch_profile(),
            price_history=self.fetch_price_history(period="1y"),
            income_statements=self.fetch_income_statements(),
            balance_sheets=self.fetch_balance_sheets(),
            cash_flows=self.fetch_cash_flows(),
            analyst_targets=self.fetch_analyst_targets(),  # NEW: Fetch analyst targets
        )
        
        logger.info(f"Completed Yahoo fetch for {self.symbol}")
        return stock_data
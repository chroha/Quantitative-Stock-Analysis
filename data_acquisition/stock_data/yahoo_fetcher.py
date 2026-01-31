"""
Yahoo Finance data fetcher.
Primary data source for financial statements and price data.
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
from utils.field_registry import DataSource
from data_acquisition.stock_data.base_fetcher import BaseFetcher

logger = setup_logger('yahoo_fetcher')


class YahooFetcher(BaseFetcher):
    """Fetches data from Yahoo Finance and maps to unified schema."""
    
    def __init__(self, symbol: str):
        """
        Initialize Yahoo fetcher for a specific symbol.
        
        Args:
            symbol: Stock ticker symbol
        """
        super().__init__(symbol, DataSource.YAHOO)
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
            
        NOTE: If you add new fields here, you MUST update CompanyProfile in utils/unified_schema.py.
        Otherwise, the data will be dropped during the save process.
        注意: 如果在此处添加新字段，必须同步更新 utils/unified_schema.py 中的 CompanyProfile 定义。
        否则，数据将在保存过程中被丢弃。
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
                # Valuation Ratios
                std_pe_ratio=self._create_field_with_source(info.get('trailingPE')),
                std_pb_ratio=self._create_field_with_source(info.get('priceToBook')),
                std_ps_ratio=self._create_field_with_source(info.get('priceToSalesTrailing12Months')),
                # EPS and Book Value
                std_eps=self._create_field_with_source(info.get('trailingEps')),
                std_book_value_per_share=self._create_field_with_source(info.get('bookValue')),
                # Dividend
                std_dividend_yield=self._create_field_with_source(info.get('dividendYield')),
                # Forward EPS and Growth Fields
                std_forward_eps=self._create_field_with_source(info.get('forwardEps')),
                std_trailing_eps=self._create_field_with_source(info.get('trailingEps')),
                std_forward_pe=self._create_field_with_source(info.get('forwardPE')),
                std_peg_ratio=self._create_field_with_source(info.get('trailingPegRatio')),
                std_earnings_growth=self._create_field_with_source(info.get('earningsGrowth')),
                # Currency Fields (CRITICAL for ADR/International Stock Currency Normalization)
                std_financial_currency=TextFieldWithSource(value=info.get('financialCurrency', 'USD'), source='yahoo') if info.get('financialCurrency') else None,
                std_listing_currency=TextFieldWithSource(value=info.get('currency', 'USD'), source='yahoo') if info.get('currency') else None,
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
    
    def _parse_financial_statement(self, df: pd.DataFrame, statement_type: str, period_type: str = 'FY') -> list:
        """
        Parse financial statement DataFrame to unified schema.
        
        Args:
            df: DataFrame from yfinance
            statement_type: 'income', 'balance', or 'cashflow'
            period_type: 'FY' (Annual) or 'Q' (Quarterly)
            
        Returns:
            List of statement objects
        """
        if df is None or df.empty:
            logger.warning(f"No {statement_type} statement data available")
            return []
        
        statements = []
        from utils.schema_mapper import SchemaMapper
        from utils.field_registry import DataSource as RegistryDataSource
        
        # Iterate through each column (period)
        for col in df.columns:
            period_str = col.strftime('%Y-%m-%d') if isinstance(col, pd.Timestamp) else str(col)
            
            # Map raw series using SchemaMapper
            mapped_fields = SchemaMapper.map_statement(
                df[col], 
                statement_type, 
                RegistryDataSource.YAHOO
            )
            
            # Create statement object
            if statement_type == 'income':
                stmt = IncomeStatement(std_period=period_str, std_period_type=period_type, **mapped_fields)
            elif statement_type == 'balance':
                stmt = BalanceSheet(std_period=period_str, std_period_type=period_type, **mapped_fields)
            elif statement_type == 'cashflow':
                stmt = CashFlow(std_period=period_str, std_period_type=period_type, **mapped_fields)
            else:
                continue
                
            statements.append(stmt)
        
        logger.info(f"Parsed {len(statements)} {statement_type} statements")
        return statements
    
    def fetch_income_statements(self) -> list[IncomeStatement]:
        """Fetch income statements (Annual + latest Quarterly)."""
        try:
            if not self.ticker:
                self.ticker = yf.Ticker(self.symbol)
            
            # Fetch Annual
            annual_df = self.ticker.financials
            # yfinance sometimes returns duplicates or TTM, filter?
            # For now, trust parser.
            annual_stmts = self._parse_financial_statement(annual_df, 'income', 'FY')
            
            # Fetch Quarterly
            quarterly_df = self.ticker.quarterly_financials
            quarterly_stmts = self._parse_financial_statement(quarterly_df, 'income', 'Q')
            
            # Merge and deduplicate by date (prefer latest fetch or quarterly for recent)
            merged = {s.std_period: s for s in annual_stmts}
            for s in quarterly_stmts:
                if s.std_period not in merged:
                    merged[s.std_period] = s
            
            final_list = list(merged.values())
            final_list.sort(key=lambda x: x.std_period, reverse=True)
            return final_list
        
        except Exception as e:
            logger.error(f"Failed to fetch income statements from Yahoo: {e}")
            return []
    
    def fetch_balance_sheets(self) -> list[BalanceSheet]:
        """Fetch balance sheets (Annual + latest Quarterly)."""
        try:
            if not self.ticker:
                self.ticker = yf.Ticker(self.symbol)
            
            # Fetch Annual
            annual_df = self.ticker.balance_sheet
            annual_stmts = self._parse_financial_statement(annual_df, 'balance', 'FY')
            
            # Fetch Quarterly
            quarterly_df = self.ticker.quarterly_balance_sheet
            quarterly_stmts = self._parse_financial_statement(quarterly_df, 'balance', 'Q')
            
            # Merge and deduplicate by date
            # Key: date string. Value: Statement object
            merged = {s.std_period: s for s in annual_stmts}
            # Update with quarterly (prefer quarterly if duplicate date exists, or vice versa? 
            # Usually annual is more audited, but for same date they should be identical.
            # We want to capture the NEWER dates from quarterly.)
            for s in quarterly_stmts:
                if s.std_period not in merged:
                    merged[s.std_period] = s
            
            # Convert back to list and sort descending
            final_list = list(merged.values())
            final_list.sort(key=lambda x: x.std_period, reverse=True)
            
            return final_list
        
        except Exception as e:
            logger.error(f"Failed to fetch balance sheets from Yahoo: {e}")
            return []
    
    def fetch_cash_flow_statements(self) -> list[CashFlow]:
        """Fetch cash flow statements (Annual + latest Quarterly)."""
        try:
            if not self.ticker:
                self.ticker = yf.Ticker(self.symbol)
            
            # Fetch Annual
            annual_df = self.ticker.cashflow
            annual_stmts = self._parse_financial_statement(annual_df, 'cashflow', 'FY')
            
            # Fetch Quarterly
            quarterly_df = self.ticker.quarterly_cashflow
            quarterly_stmts = self._parse_financial_statement(quarterly_df, 'cashflow', 'Q')
            
            # Merge
            merged = {s.std_period: s for s in annual_stmts}
            for s in quarterly_stmts:
                if s.std_period not in merged:
                    merged[s.std_period] = s
            
            final_list = list(merged.values())
            final_list.sort(key=lambda x: x.std_period, reverse=True)
            return final_list
        
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
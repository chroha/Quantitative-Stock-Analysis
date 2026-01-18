"""
Base Fetcher - Abstract base class for data fetchers.
Provides common interface for all data sources (Yahoo, FMP, Alpha Vantage, SEC EDGAR).
Designed for easy extension to add new data sources.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Any
from enum import Enum

from utils.unified_schema import (
    StockData, IncomeStatement, BalanceSheet, CashFlow,
    CompanyProfile, AnalystTargets, PriceData
)


class DataSource(Enum):
    """Enumeration of available data sources with priority order."""
    YAHOO = "yahoo"
    FMP = "fmp"
    ALPHAVANTAGE = "alphavantage"
    SEC_EDGAR = "sec_edgar"  # Reserved for future implementation


class BaseFetcher(ABC):
    """
    Abstract base class for all data fetchers.
    Implementations must provide the following methods.
    """
    
    def __init__(self, symbol: str):
        """
        Initialize fetcher for a specific stock symbol.
        
        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL')
        """
        self.symbol = symbol.upper()
    
    @property
    @abstractmethod
    def source(self) -> DataSource:
        """Return the data source identifier."""
        pass
    
    @abstractmethod
    def fetch_profile(self) -> Optional[CompanyProfile]:
        """
        Fetch company profile information.
        
        Returns:
            CompanyProfile object or None if fetch fails
        """
        pass
    
    @abstractmethod
    def fetch_income_statements(self) -> List[IncomeStatement]:
        """
        Fetch income statements (typically 5 years annual).
        
        Returns:
            List of IncomeStatement objects
        """
        pass
    
    @abstractmethod  
    def fetch_balance_sheets(self) -> List[BalanceSheet]:
        """
        Fetch balance sheets (typically 5 years annual).
        
        Returns:
            List of BalanceSheet objects
        """
        pass
    
    @abstractmethod
    def fetch_cash_flows(self) -> List[CashFlow]:
        """
        Fetch cash flow statements (typically 5 years annual).
        
        Returns:
            List of CashFlow objects
        """
        pass
    
    def fetch_price_history(self, period: str = "1y") -> List[PriceData]:
        """
        Fetch historical price data.
        Optional - not all sources provide this.
        
        Args:
            period: Time period (e.g., '1y', '5y')
            
        Returns:
            List of PriceData objects
        """
        return []
    
    def fetch_analyst_targets(self) -> Optional[AnalystTargets]:
        """
        Fetch analyst price targets.
        Optional - not all sources provide this.
        
        Returns:
            AnalystTargets object or None
        """
        return None
    
    def fetch_all(self) -> StockData:
        """
        Fetch all available data from this source.
        
        Returns:
            StockData object populated with available data
        """
        return StockData(
            symbol=self.symbol,
            profile=self.fetch_profile(),
            income_statements=self.fetch_income_statements(),
            balance_sheets=self.fetch_balance_sheets(),
            cash_flows=self.fetch_cash_flows(),
            price_history=self.fetch_price_history(),
            analyst_targets=self.fetch_analyst_targets(),
        )


class FetcherRegistry:
    """
    Registry for managing available data fetchers.
    Allows dynamic registration of new data sources.
    """
    
    _fetchers = {}
    
    @classmethod
    def register(cls, source: DataSource, fetcher_class: type):
        """Register a fetcher class for a data source."""
        cls._fetchers[source] = fetcher_class
    
    @classmethod
    def get_fetcher(cls, source: DataSource, symbol: str) -> Optional[BaseFetcher]:
        """Get an instance of fetcher for the specified source."""
        fetcher_class = cls._fetchers.get(source)
        if fetcher_class:
            return fetcher_class(symbol)
        return None
    
    @classmethod
    def get_available_sources(cls) -> List[DataSource]:
        """Get list of registered data sources."""
        return list(cls._fetchers.keys())

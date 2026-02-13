"""
Base Data Source Strategy
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from utils.unified_schema import StockData
from utils.logger import setup_logger

logger = setup_logger('data_strategy')

class DataSourceStrategy(ABC):
    """
    Abstract base class for data fetching strategies.
    Each strategy represents a specific data source (Yahoo, FMP, etc.)
    """
    
    def __init__(self, symbol: str):
        self.symbol = symbol.upper()
        
    @abstractmethod
    def fetch_data(self, current_data: StockData) -> StockData:
        """
        Fetch data from the source and merge/update the current_data object.
        
        Args:
            current_data: The StockData object accumulating results from previous phases.
            
        Returns:
            Updated StockData object.
        """
        pass

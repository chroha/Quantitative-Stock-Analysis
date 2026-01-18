"""
Base Valuation Model
Abstract base class for all valuation methods.
"""

from abc import ABC, abstractmethod
from typing import Optional
from utils.unified_schema import StockData


class BaseValuationModel(ABC):
    """
    Abstract base class for valuation models.
    
    All valuation methods must inherit from this class and implement
    the calculate_fair_value method.
    """
    
    @abstractmethod
    def calculate_fair_value(
        self,
        stock_data: StockData,
        benchmark_data: dict,
        sector: str
    ) -> Optional[float]:
        """
        Calculate fair value per share using this valuation method.
        
        Args:
            stock_data: Complete stock data object
            benchmark_data: Industry benchmark data from Damodaran
            sector: GICS sector name
            
        Returns:
            Fair value per share, or None if calculation not possible
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """
        Return the identifier for this model.
        
        Returns:
            Model name (e.g., 'pe', 'pb', 'dcf')
        """
        pass
    
    def get_model_display_name(self) -> str:
        """
        Return human-readable name for this model.
        
        Returns:
            Display name (e.g., 'PE Valuation', 'DCF Model')
        """
        return self.get_model_name().upper()

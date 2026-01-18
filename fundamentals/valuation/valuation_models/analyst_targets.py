"""
Analyst Targets Model
Uses median analyst price target.
"""

from typing import Optional
from .base_model import BaseValuationModel
from utils.unified_schema import StockData
from utils.logger import setup_logger

logger = setup_logger('analyst_targets')


class AnalystTargetsModel(BaseValuationModel):
    """
    Analyst Price Targets.
    Uses MEDIAN analyst target price (not average).
    """
    
    def get_model_name(self) -> str:
        return "analyst"
    
    def get_model_display_name(self) -> str:
        return "Analyst Median"
    
    def calculate_fair_value(
        self,
        stock_data: StockData,
        benchmark_data: dict,
        sector: str
    ) -> Optional[float]:
        """Use median analyst price target as fair value."""
        try:
            if not stock_data.analyst_targets:
                logger.warning(f"{stock_data.symbol}: No analyst targets available")
                return None
            
            # Use consensus price target (closest to median)
            consensus_target = stock_data.analyst_targets.std_price_target_consensus
            
            if consensus_target is None or consensus_target.value is None or consensus_target.value <= 0:
                logger.warning(f"{stock_data.symbol}: Invalid analyst consensus target")
                return None
            
            target_price = consensus_target.value
            logger.info(f"{stock_data.symbol}: Analyst Consensus Target=${target_price:.2f}")
            
            return target_price
            
        except Exception as e:
            logger.error(f"Analyst targets failed for {stock_data.symbol}: {e}")
            return None

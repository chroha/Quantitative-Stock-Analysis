"""
PEG Valuation Model.

Calculates fair value based on Price/Earnings to Growth ratio.
PEG = PE / Annual EPS Growth Rate

A PEG of 1 suggests fair value, <1 undervalued, >1 overvalued.
Fair Value = Current Price / PEG (normalized to PEG=1)
"""

from typing import Optional, Any
from utils.unified_schema import StockData
from .base_model import BaseValuationModel


class PEGValuationModel(BaseValuationModel):
    """
    PEG Valuation Model.
    
    Uses direct PEG ratio from Yahoo Finance if available,
    or calculates from Forward PE and Earnings Growth.
    
    Fair Value = Current Price * (1 / PEG)
    This implies: if PEG = 2, stock is 2x overvalued, fair value = price / 2
    """
    
    def get_model_name(self) -> str:
        return "peg"

    def get_model_display_name(self) -> str:
        return "PEG Valuation"

    def calculate_fair_value(self, stock_data: StockData, benchmark_data: Any, sector: str) -> Optional[float]:
        try:
            # Get current price
            if not stock_data.price_history:
                return None
            current_price = stock_data.price_history[-1].std_close.value
            if current_price is None or current_price <= 0:
                return None
            
            # Try to get PEG ratio directly from profile (Yahoo provides this)
            peg_ratio = None
            if stock_data.profile and stock_data.profile.std_peg_ratio:
                peg_field = stock_data.profile.std_peg_ratio
                if peg_field.value is not None and peg_field.value > 0:
                    peg_ratio = peg_field.value
            
            # Fallback: Calculate PEG from Forward PE and Earnings Growth
            if peg_ratio is None and stock_data.profile:
                forward_pe = None
                earnings_growth = None
                
                if stock_data.profile.std_forward_pe:
                    forward_pe = stock_data.profile.std_forward_pe.value
                if stock_data.profile.std_earnings_growth:
                    earnings_growth = stock_data.profile.std_earnings_growth.value
                
                if forward_pe and earnings_growth:
                    # Earnings growth is decimal (e.g., 0.15 = 15%)
                    # PEG = PE / (Growth * 100)
                    growth_pct = earnings_growth * 100
                    if growth_pct > 0:
                        peg_ratio = forward_pe / growth_pct
            
            if peg_ratio is None or peg_ratio <= 0:
                return None
            
            # Fair value calculation
            # If PEG = 1, fair value = current price
            # If PEG > 1, overvalued, fair value < current price
            # If PEG < 1, undervalued, fair value > current price
            
            # Cap extreme PEG values to avoid unrealistic results
            if peg_ratio > 5:
                peg_ratio = 5  # Extremely overvalued cap
            if peg_ratio < 0.2:
                peg_ratio = 0.2  # Extremely undervalued cap
                
            fair_value = current_price / peg_ratio
            
            return fair_value
            
        except Exception as e:
            import logging
            logging.getLogger('peg_model').warning(f"PEG calculation failed: {e}")
            return None

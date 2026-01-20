from typing import Optional, Any
from utils.unified_schema import StockData
from .base_model import BaseValuationModel

class PeterLynchModel(BaseValuationModel):
    """
    Peter Lynch Fair Value Model.
    
    Fair Value = PEG * Earnings Growth Rate * EPS
    Simplified: Fair P/E should equal Growth Rate.
    So Fair Value = Growth Rate * EPS.
    
    Typically uses Expected Earnings Growth. We will use 5Y CAGR or consensus if available.
    """
    
    def get_model_name(self) -> str:
        return "peter_lynch"

    def get_model_display_name(self) -> str:
        return "Peter Lynch Fair Value"

    def calculate_fair_value(self, stock_data: StockData, benchmark_data: Any, sector: str) -> Optional[float]:
        try:
            # Need EPS and Growth Rate
            if not stock_data.income_statements:
                return None
            
            # Pydantic safety: check if field exists and has value
            eps_field = stock_data.income_statements[0].std_eps_diluted
            if eps_field is None:
                return None
            eps = eps_field.value
            
            if eps is None or eps <= 0:
                return None
                
            # Growth Rate - prioritization:
            # 1. Analyst Growth Estimates (not currently in StockData schema fully formatted, usually in analysis)
            # 2. Net Income CAGR 5Y (Historical)
            
            # Retrieve calculated Historical CAGR from processed Financial Data if possible?
            # But the Valuation Model only receives StockData. 
            # We must recalculate or look for it.
            # Let's calculate simple NI CAGR from history.
            
            growth_rate = self._calculate_ni_cagr(stock_data)
            
            if growth_rate is None:
                return None
                
            # Convert decimal to percentage for multiplier (e.g. 0.15 -> 15)
            growth_multiplier = growth_rate * 100
            
            # Lynch Cap: Growth > 25% is unsustainable -> Cap multiplier at 25
            # Also Min: Growth < 5% -> maybe not a Lynch stock, but let's calculate anyway.
            if growth_multiplier > 25:
                growth_multiplier = 25
            if growth_multiplier < 0:
                return None
                
            # Basic Lynch: Fair P/E = Growth Rate
            fair_value = eps * growth_multiplier
            
            # Adjust for Dividend Yield? Lynch often added Div Yield to Growth Rate.
            # Lynch Fair PE = Growth + Dividend Yield
            div_yield = 0
            if stock_data.profile and stock_data.profile.std_market_cap and stock_data.profile.std_market_cap.value and stock_data.profile.std_market_cap.value > 0:
                # We don't have stored Div Yield in profile easily, calculate from last dividend if possible
                # or skip. Let's keep it simple for now.
                pass
                
            return fair_value
            
        except Exception as e:
            # Log the exception for debugging
            import logging
            logging.getLogger('peter_lynch_model').warning(f"Peter Lynch calculation failed: {e}")
            return None

    def _calculate_ni_cagr(self, stock_data: StockData) -> Optional[float]:
        # Needs at least 4-5 years
        stmts = stock_data.income_statements
        if not stmts or len(stmts) < 2:
            return None
            
        # Try to use standard NI, if None, skip
        try:
            current = stmts[0].std_net_income.value
            oldest = stmts[-1].std_net_income.value
            years = len(stmts) - 1
            
            if current is None or oldest is None or oldest <= 0:
                 # Check if we have positive NI in oldest
                 # Attempt a shorter range if full range is invalid?
                 # For now, strict.
                 return None
                 
            # Simple CAGR
            if current <= 0:
                # Negative current earnings -> undefined growth for Lynch
                return None
                
            cagr = (current / oldest) ** (1/years) - 1
            return cagr
        except Exception:
            return None

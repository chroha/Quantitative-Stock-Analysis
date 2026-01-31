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
                raise ValueError(f"EPS is non-positive ({eps}), model inapplicable")
                
            # Growth Rate - prioritization:
            # 1. Analyst Growth Estimates (not currently in StockData schema fully formatted, usually in analysis)
            # 2. Net Income CAGR 5Y (Historical)
            
            # Retrieve calculated Historical CAGR from processed Financial Data if possible?
            # But the Valuation Model only receives StockData. 
            # We must recalculate or look for it.
            # Let's calculate simple NI CAGR from history.
            
            growth_rate = self._calculate_ni_cagr(stock_data)
            
            if growth_rate is None:
                raise ValueError("Insufficient historical data to calculate growth rate")
                
            # Convert decimal to percentage for multiplier (e.g. 0.15 -> 15)
            growth_multiplier = growth_rate * 100
            
            # Lynch Cap: Growth > 25% is unsustainable -> Cap multiplier at 25
            # Also Min: Growth < 5% -> maybe not a Lynch stock, but let's calculate anyway.
            if growth_multiplier > 25:
                growth_multiplier = 25
            if growth_multiplier <= 0:
                raise ValueError(f"Growth rate is non-positive ({growth_multiplier:.1f}%), model inapplicable")
                
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
        # Needs at least 3 years of data
        stmts = stock_data.income_statements
        if not stmts or len(stmts) < 3:
            return None
            
        # Filter for Annual reports only to be precise, or just use indices if sorted
        # Assuming sorted desc (Latest -> Oldest)
        
        # We want approx 5 years lookback. 
        # If we have annuals mixed with quarters, it's tricky. 
        # Let's try to find the statement closest to 5 years ago.
        
        import datetime
        latest_date = stmts[0].std_period
        # Handle TTM prefix
        if latest_date.startswith("TTM-"):
             latest_date = latest_date[4:]
             
        try:
            latest_dt = datetime.datetime.strptime(latest_date, "%Y-%m-%d")
        except:
            return None
            
        target_date = latest_dt - datetime.timedelta(days=5*365)
        
        base_stmt = None
        years_diff = 0
        
        # Find statement closest to 5y ago, but not older than 6y
        for stmt in stmts:
            try:
                s_date = stmt.std_period
                if s_date.startswith("TTM-"):
                    s_date = s_date[4:]
                    
                s_dt = datetime.datetime.strptime(s_date, "%Y-%m-%d")
                age_days = (latest_dt - s_dt).days
                age_years = age_days / 365.0
                
                if 4.5 <= age_years <= 6.5:
                    base_stmt = stmt
                    years_diff = age_years
                    break
            except:
                continue
                
        # Fallback: if no 5y data, try 3y
        if not base_stmt:
             target_date_3y = latest_dt - datetime.timedelta(days=3*365)
             for stmt in stmts:
                try:
                    s_date = stmt.std_period
                    if s_date.startswith("TTM-"):
                        s_date = s_date[4:]
                    s_dt = datetime.datetime.strptime(s_date, "%Y-%m-%d")
                    age_days = (latest_dt - s_dt).days
                    age_years = age_days / 365.0
                    
                    if 2.5 <= age_years <= 3.5:
                        base_stmt = stmt
                        years_diff = age_years
                        break
                except:
                    continue

        if not base_stmt:
            # Last resort: use oldest available if profitable
            base_stmt = stmts[-1]
            try:
                s_date = base_stmt.std_period
                if s_date.startswith("TTM-"):
                    s_date = s_date[4:]
                s_dt = datetime.datetime.strptime(s_date, "%Y-%m-%d")
                years_diff = (latest_dt - s_dt).days / 365.0
            except:
                years_diff = len(stmts) / 4 # Rough estimate
            
        try:
            current = stmts[0].std_net_income.value
            oldest = base_stmt.std_net_income.value
            
            if current is None or oldest is None:
                return None
            
            # If base year is negative, we can't calculate a meaningful CAGR directly.
            # Lynch would look for a "normal" year.
            # Strategy: if oldest < 0, move forward in time until positive (up to 3y lookback)
            if oldest <= 0:
                # Try to find a profitable year between base and current
                idx = stmts.index(base_stmt)
                while idx > 0:
                    idx -= 1
                    s = stmts[idx]
                    val = s.std_net_income.value
                    if val and val > 0:
                        # Found a closer positive year
                        oldest = val
                        # Recalculate years
                        try:
                           s_date = s.std_period
                           if s_date.startswith("TTM-"):
                               s_date = s_date[4:]
                           s_dt = datetime.datetime.strptime(s_date, "%Y-%m-%d")
                           years_diff = (latest_dt - s_dt).days / 365.0
                        except:
                           pass # Keep old estimate or fail
                        break
                
                if oldest <= 0:
                    return None # Still negative, give up
            
            if current <= 0:
                return None # Current loss = no P/E based valuation
                
            if years_diff < 1:
                return None
                
            cagr = (current / oldest) ** (1/years_diff) - 1
            return cagr
        except Exception:
            return None

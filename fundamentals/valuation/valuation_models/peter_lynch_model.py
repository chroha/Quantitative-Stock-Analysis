from typing import Optional, Any
from utils.unified_schema import StockData
from .base_model import BaseValuationModel
import datetime

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
        """
        Calculate Net Income CAGR.
        Priority:
        1. Historical 5Y Net Income CAGR (calculated)
        2. Historical 3-4Y Net Income CAGR (calculated)
        3. Profile's Earnings Growth (last resort)
        """
        # Strategy 1 & 2: Calculate from historical data
        # Filter for Annual reports only to be precise
        all_stmts = stock_data.income_statements
        stmts = [s for s in all_stmts if s.std_period_type == 'FY']
        
        # If insufficient annual data, fall back to whatever we have (but risky) or try TTM
        # For now, let's rely on FY.
        if stmts and len(stmts) >= 3:
            # Assuming sorted desc (Latest -> Oldest)
            # Re-sort to be safe because we just filtered
            stmts.sort(key=lambda x: x.std_period or "", reverse=True)
            
            latest_date_str = stmts[0].std_period
            
            # Helper to parse date
            def parse_date(d_str):
                try:
                    if d_str.startswith("Synthetic_TTM"): return None
                    if d_str.startswith("TTM-"): d_str = d_str[4:]
                    return datetime.datetime.strptime(d_str, "%Y-%m-%d")
                except: return None

            latest_dt = parse_date(latest_date_str)
            if not latest_dt:
                # If latest is synthetic, try next
                if len(stmts) > 1:
                     latest_date_str = stmts[1].std_period
                     latest_dt = parse_date(latest_date_str)
            
            if latest_dt:
                # Find best base statement (Priorities: ~5y -> ~4y -> ~3y)
                best_candidate = None
                best_diff = 0
                
                for stmt in stmts:
                    s_dt = parse_date(stmt.std_period)
                    if not s_dt: continue
                    
                    age_days = (latest_dt - s_dt).days
                    age_years = age_days / 365.0
                    
                    # Ideal: 4.5 - 5.5 years
                    if 4.5 <= age_years <= 5.5:
                        best_candidate = stmt
                        best_diff = age_years
                        break # Found ideal
                    
                    # Acceptable: 2.5 - 6.5 years
                    if 2.5 <= age_years <= 6.5:
                         # Keep looking for better, or store as fallback
                         if best_candidate is None or abs(age_years - 5) < abs(best_diff - 5):
                             best_candidate = stmt
                             best_diff = age_years
                
                if best_candidate:
                    try:
                        current = stmts[0].std_net_income.value
                        oldest = best_candidate.std_net_income.value
                        
                        if current is not None and oldest is not None and current > 0 and oldest > 0:
                            cagr = (current / oldest) ** (1/best_diff) - 1
                            return cagr
                    except Exception:
                        pass # Calculation failed, fall through to strategy 3

        # Strategy 3: Profile Earnings Growth (Yahoo/FMP provided)
        if stock_data.profile and stock_data.profile.std_earnings_growth:
             return stock_data.profile.std_earnings_growth.value
             
        return None

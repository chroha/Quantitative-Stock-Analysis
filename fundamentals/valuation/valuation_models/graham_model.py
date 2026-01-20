from typing import Optional, Any
from utils.unified_schema import StockData
from .base_model import BaseValuationModel

class GrahamNumberModel(BaseValuationModel):
    """
    Graham Number Valuation Model.
    
    Formula: sqrt(22.5 * EPS * BVPS)
    Where:
        22.5 = 15 (max P/E) * 1.5 (max P/B)
    """
    
    def get_model_name(self) -> str:
        return "graham"

    def get_model_display_name(self) -> str:
        return "Graham Number"

    def calculate_fair_value(self, stock_data: StockData, benchmark_data: Any, sector: str) -> Optional[float]:
        try:
            # Need EPS and BVPS
            # EPS (Diluted)
            if not stock_data.income_statements:
                return None
            eps = stock_data.income_statements[0].std_eps_diluted.value
            
            # BVPS (Book Value Per Share)
            if not stock_data.balance_sheets:
                return None
            equity = stock_data.balance_sheets[0].std_shareholder_equity.value
            shares = stock_data.income_statements[0].std_shares_outstanding.value
            
            if shares is None or shares == 0:
                shares = self._get_shares_from_profile(stock_data) # Helper if exists or fallback
                
            if shares is None or shares == 0:
                return None
                
            bvps = equity / shares
            
            if eps is None or eps <= 0 or bvps <= 0:
                return None
                
            graham_number = (22.5 * eps * bvps) ** 0.5
            return graham_number
            
        except Exception:
            return None

    def _get_shares_from_profile(self, stock_data) -> Optional[float]:
        if stock_data.profile and stock_data.profile.mkt_cap and stock_data.profile.price:
             return stock_data.profile.mkt_cap.value / stock_data.profile.price.value
        return None

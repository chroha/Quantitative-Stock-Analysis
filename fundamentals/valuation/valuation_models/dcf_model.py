"""
DCF (Discounted Cash Flow) Model
Simplified DCF valuation using free cash flow projections.
"""

from typing import Optional
from .base_model import BaseValuationModel
from utils.unified_schema import StockData
from utils.logger import setup_logger

logger = setup_logger('dcf_model')


class DCFModel(BaseValuationModel):
    """
    Simplified DCF Model.
    
    Uses:
    - Latest FCF as base
    - Industry growth rate (simplified: use GDP growth ~3%)
    - WACC calculated from Beta
    - 5-year projection + terminal value
    """
    
    # Constants
    RISK_FREE_RATE = 0.04  # 4% (10-year Treasury)
    MARKET_RETURN = 0.10   # 10% historical market return
    GROWTH_RATE = 0.03     # 3% perpetual growth rate
    PROJECTION_YEARS = 5
    
    def get_model_name(self) -> str:
        return "dcf"
    
    def get_model_display_name(self) -> str:
        return "DCF Model"
    
    def calculate_fair_value(
        self,
        stock_data: StockData,
        benchmark_data: dict,
        sector: str
    ) -> Optional[float]:
        """Calculate fair value using simplified DCF."""
        try:
            # 1. Get latest Free Cash Flow
            if not stock_data.cash_flows:
                logger.warning(f"{stock_data.symbol}: No cash flow statements")
                return None
            
            latest_cf = stock_data.cash_flows[0]
            if not latest_cf.std_free_cash_flow or latest_cf.std_free_cash_flow.value is None:
                logger.warning(f"{stock_data.symbol}: No FCF data")
                return None
            
            fcf = latest_cf.std_free_cash_flow.value
            
            if fcf <= 0:
                logger.warning(f"{stock_data.symbol}: Negative or zero FCF ({fcf})")
                return None
            
            # 2. Calculate WACC using Beta
            # Priority: Stock-specific Beta > Industry Beta > Default 1.0
            beta = None
            
            # Try to get stock-specific Beta from profile first
            if stock_data.profile and stock_data.profile.std_beta:
                beta = stock_data.profile.std_beta.value
                logger.info(f"{stock_data.symbol}: Using stock-specific Beta={beta:.3f}")
            
            # Fallback to industry Beta
            if beta is None or beta <= 0:
                sector_benchmarks = benchmark_data.get('sectors', {}).get(sector, {})
                metrics = sector_benchmarks.get('metrics', {})
                beta_data = metrics.get('beta', {})
                industry_beta = beta_data.get('mean') if isinstance(beta_data, dict) else None
                
                if industry_beta and industry_beta > 0:
                    beta = industry_beta
                    logger.info(f"{stock_data.symbol}: Using industry Beta={beta:.3f} (stock Beta not available)")
            
            # Final fallback to market beta
            if beta is None or beta <= 0:
                logger.warning(f"{stock_data.symbol}: No valid beta found, using market default 1.0")
                beta = 1.0
            
            # WACC = Risk-free + Beta * (Market Return - Risk-free)
            wacc = self.RISK_FREE_RATE + beta * (self.MARKET_RETURN - self.RISK_FREE_RATE)
            
            # 3. Project FCF for 5 years
            projected_fcfs = []
            for year in range(1, self.PROJECTION_YEARS + 1):
                projected_fcf = fcf * ((1 + self.GROWTH_RATE) ** year)
                discount_factor = (1 + wacc) ** year
                pv = projected_fcf / discount_factor
                projected_fcfs.append(pv)
            
            # 4. Calculate Terminal Value
            terminal_fcf = fcf * ((1 + self.GROWTH_RATE) ** (self.PROJECTION_YEARS + 1))
            terminal_value = terminal_fcf / (wacc - self.GROWTH_RATE)
            pv_terminal = terminal_value / ((1 + wacc) ** self.PROJECTION_YEARS)
            
            # 5. Enterprise Value = Sum of PV(FCFs) + PV(Terminal Value)
            enterprise_value = sum(projected_fcfs) + pv_terminal
            
            # 6. Convert to Equity Value
            if not stock_data.balance_sheets:
                logger.warning(f"{stock_data.symbol}: No balance sheet for debt adjustment")
                return None
            
            latest_bs = stock_data.balance_sheets[0]
            
            # Net Debt = Total Debt - Cash
            total_debt = 0
            if latest_bs.std_total_debt and latest_bs.std_total_debt.value:
                total_debt = latest_bs.std_total_debt.value
            
            cash = 0
            if latest_bs.std_cash and latest_bs.std_cash.value:
                cash = latest_bs.std_cash.value
            
            net_debt = total_debt - cash
            equity_value = enterprise_value - net_debt
            
            # 7. Get shares outstanding
            if not stock_data.income_statements:
                logger.warning(f"{stock_data.symbol}: No income statements for shares")
                return None
            
            latest_income = stock_data.income_statements[0]
            if not latest_income.std_shares_outstanding or latest_income.std_shares_outstanding.value is None:
                logger.warning(f"{stock_data.symbol}: No shares outstanding")
                return None
            
            shares = latest_income.std_shares_outstanding.value
            
            if shares <= 0:
                logger.warning(f"{stock_data.symbol}: Invalid shares ({shares})")
                return None
            
            fair_value_per_share = equity_value / shares
            
            logger.info(f"{stock_data.symbol}: FCF={fcf/1e9:.2f}B, WACC={wacc*100:.1f}%, Beta={beta:.2f}, Fair Value=${fair_value_per_share:.2f}")
            
            return fair_value_per_share if fair_value_per_share > 0 else None
            
        except Exception as e:
            logger.error(f"DCF valuation failed for {stock_data.symbol}: {e}")
            return None

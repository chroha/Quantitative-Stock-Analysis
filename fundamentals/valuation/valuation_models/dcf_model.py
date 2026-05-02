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
            # 1. Get latest Free Cash Flow from the latest FY/TTM cash flow statement.
            # cash_flows[0] may be a quarterly snapshot (e.g., Q1) with negative or partial FCF,
            # which would cause DCF to return N/A. Prefer annual data for a stable base.
            annual_cf_for_fcf = next((cf for cf in stock_data.cash_flows
                                      if getattr(cf, 'std_period_type', 'FY') in ['FY', 'TTM']), None)
            latest_cf = annual_cf_for_fcf if annual_cf_for_fcf is not None else stock_data.cash_flows[0]
            
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

            # Safety check: if WACC is too close to GROWTH_RATE, the Terminal Value
            # formula denominator (wacc - growth_rate) approaches zero, causing the
            # fair value to explode. This typically affects low-Beta defensive stocks
            # (e.g., utilities, defense) where WACC can fall near 4-5%.
            # Enforce a minimum spread of 2% to keep Terminal Value realistic.
            MIN_SPREAD = 0.02
            if wacc - self.GROWTH_RATE < MIN_SPREAD:
                wacc_clamped = self.GROWTH_RATE + MIN_SPREAD
                logger.warning(
                    f"{stock_data.symbol}: WACC ({wacc*100:.1f}%) - GROWTH_RATE ({self.GROWTH_RATE*100:.1f}%) "
                    f"spread < {MIN_SPREAD*100:.0f}%. Clamping WACC to {wacc_clamped*100:.1f}% "
                    f"to prevent Terminal Value explosion (Beta={beta:.2f})."
                )
                wacc = wacc_clamped

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
            
            # Select FY/TTM balance sheet aligned with the latest annual cash flow to avoid
            # incomplete quarterly snapshots (e.g. FMP Q1 data mis-labeled as FY) that
            # have near-zero total_debt, which produces a large negative net_debt and
            # pushes the DCF fair value far above realistic levels.
            annual_cf_period = None
            if stock_data.cash_flows:
                annual_cf = next((cf for cf in stock_data.cash_flows
                                  if getattr(cf, 'std_period_type', 'FY') in ['FY', 'TTM']), None)
                annual_cf_period = getattr(annual_cf, 'std_period', None) if annual_cf else None
            
            latest_bs = None
            if annual_cf_period:
                for bs in stock_data.balance_sheets:
                    if getattr(bs, 'std_period_type', '') not in ['FY', 'TTM']:
                        continue
                    if getattr(bs, 'std_period', '') <= annual_cf_period:
                        latest_bs = bs
                        break
            if latest_bs is None:
                latest_bs = next((bs for bs in stock_data.balance_sheets
                                  if getattr(bs, 'std_period_type', '') in ['FY', 'TTM']),
                                 stock_data.balance_sheets[0])
            
            # Sanity check: debt drop > 95% in one period is almost certainly corrupt data.
            # 5% threshold avoids false positives on companies that legitimately reduced debt.
            # prev_debt > 1e8 guard prevents issues on tiny absolute values.
            debt_field = getattr(latest_bs, 'std_total_debt', None)
            selected_debt = debt_field.value if debt_field and hasattr(debt_field, 'value') else None
            selected_period = getattr(latest_bs, 'std_period', '')
            if selected_debt is not None:
                for bs in stock_data.balance_sheets:
                    if getattr(bs, 'std_period_type', '') not in ['FY', 'TTM']:
                        continue
                    bs_period = getattr(bs, 'std_period', '')
                    if bs_period < selected_period:
                        prev_debt_f = getattr(bs, 'std_total_debt', None)
                        prev_debt = prev_debt_f.value if prev_debt_f and hasattr(prev_debt_f, 'value') else None
                        if (prev_debt and prev_debt > 1e8
                                and selected_debt < prev_debt * 0.05):
                            logger.warning(
                                f"{stock_data.symbol}: DCF BS {selected_period} total_debt={selected_debt/1e9:.2f}B "
                                f"is <5% of prior {bs_period} debt={prev_debt/1e9:.2f}B. "
                                f"Likely incomplete data — falling back to {bs_period}."
                            )
                            latest_bs = bs
                        break
            
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

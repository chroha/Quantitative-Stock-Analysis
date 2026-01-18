"""
EV/EBITDA Valuation Model
Enterprise Value to EBITDA multiple valuation.
"""

from typing import Optional
from .base_model import BaseValuationModel
from utils.unified_schema import StockData
from utils.logger import setup_logger

logger = setup_logger('ev_valuation')


class EVValuationModel(BaseValuationModel):
    """
    EV/EBITDA Multiple Valuation.
    Fair Enterprise Value = EBITDA × Industry EV/EBITDA
    Fair Equity Value = EV - Net Debt
    Fair Value Per Share = Fair Equity Value / Shares Outstanding
    """
    
    def get_model_name(self) -> str:
        return "ev_ebitda"
    
    def get_model_display_name(self) -> str:
        return "EV/EBITDA Valuation"
    
    def calculate_fair_value(
        self,
        stock_data: StockData,
        benchmark_data: dict,
        sector: str
    ) -> Optional[float]:
        """Calculate fair value using EV/EBITDA multiple."""
        try:
            # Get latest EBITDA
            if not stock_data.income_statements:
                logger.warning(f"{stock_data.symbol}: No income statements available")
                return None
            
            latest_income = stock_data.income_statements[0]  # Most recent
            
            if not latest_income.std_ebitda or latest_income.std_ebitda.value is None:
                logger.warning(f"{stock_data.symbol}: No EBITDA data")
                return None
            
            ebitda = latest_income.std_ebitda.value
            
            if ebitda <= 0:
                logger.warning(f"{stock_data.symbol}: Negative or zero EBITDA ({ebitda})")
                return None
            
            # Get industry EV/EBITDA
            sector_benchmarks = benchmark_data.get('sectors', {}).get(sector, {})
            valuation_multiples = sector_benchmarks.get('metrics', {}).get('valuation_multiples', {})
            
            industry_ev_ebitda = valuation_multiples.get('ev_ebitda')
            
            if industry_ev_ebitda is None or industry_ev_ebitda <= 0:
                logger.warning(f"{sector}: No valid industry EV/EBITDA ratio")
                return None
            
            # Calculate fair enterprise value
            fair_ev = ebitda * industry_ev_ebitda
            
            # Get net debt from balance sheet
            if not stock_data.balance_sheets:
                logger.warning(f"{stock_data.symbol}: No balance sheets available")
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
            
            # Fair Equity Value = EV - Net Debt
            fair_equity_value = fair_ev - net_debt
            
            # Get shares outstanding from income statement
            if not latest_income.std_shares_outstanding or latest_income.std_shares_outstanding.value is None:
                logger.warning(f"{stock_data.symbol}: No shares outstanding data")
                return None
            
            shares = latest_income.std_shares_outstanding.value
            
            if shares <= 0:
                logger.warning(f"{stock_data.symbol}: Invalid shares outstanding ({shares})")
                return None
            
            fair_value_per_share = fair_equity_value / shares
            
            logger.info(f"{stock_data.symbol}: EBITDA={ebitda/1e9:.2f}B, Industry EV/EBITDA={industry_ev_ebitda:.2f}, Fair Value=${fair_value_per_share:.2f}")
            
            return fair_value_per_share if fair_value_per_share > 0 else None
            
        except Exception as e:
            logger.error(f"EV/EBITDA valuation failed for {stock_data.symbol}: {e}")
            return None

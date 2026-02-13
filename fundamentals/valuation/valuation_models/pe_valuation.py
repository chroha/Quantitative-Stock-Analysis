"""
PE Valuation Model
Price-to-Earnings multiple valuation.
"""

from typing import Optional
from .base_model import BaseValuationModel
from utils.unified_schema import StockData
from utils.logger import setup_logger

logger = setup_logger('pe_valuation')


class PEValuationModel(BaseValuationModel):
    """
    PE Multiple Valuation.
    Fair Value = EPS × Industry PE
    
    Uses forward PE if available, otherwise current PE.
    """
    
    def get_model_name(self) -> str:
        return "pe"
    
    def get_model_display_name(self) -> str:
        return "PE Valuation"
    
    def calculate_fair_value(
        self,
        stock_data: StockData,
        benchmark_data: dict,
        sector: str
    ) -> Optional[float]:
        """Calculate fair value using PE multiple."""
        try:
            # Get latest EPS (diluted)
            if not stock_data.income_statements:
                logger.warning(f"{stock_data.symbol}: No income statements available")
                return None
            
            latest_income = stock_data.income_statements[0]  # Most recent
            eps = None
            if latest_income.std_eps_diluted and latest_income.std_eps_diluted.value is not None:
                eps = latest_income.std_eps_diluted.value
            elif latest_income.std_eps and latest_income.std_eps.value is not None:
                eps = latest_income.std_eps.value
            
            if eps is None:
                logger.warning(f"{stock_data.symbol}: No EPS data (Basic or Diluted)")
                return None
            
            if eps <= 0:
                logger.warning(f"{stock_data.symbol}: Negative or zero EPS ({eps})")
                return None
            
            # Get industry PE (prefer forward PE, fallback to current)
            sector_benchmarks = benchmark_data.get('sectors', {}).get(sector, {})
            valuation_multiples = sector_benchmarks.get('metrics', {}).get('valuation_multiples', {})
            
            industry_pe = valuation_multiples.get('pe_forward')  # Forward PE preferred
            if industry_pe is None or industry_pe <= 0:
                industry_pe = valuation_multiples.get('pe_current')  # Fallback to current
            
            if industry_pe is None or industry_pe <= 0:
                logger.warning(f"{sector}: No valid industry P/E ratio")
                return None
            
            fair_value = eps * industry_pe
            logger.info(f"{stock_data.symbol}: EPS={eps:.2f}, Industry PE={industry_pe:.2f}, Fair Value=${fair_value:.2f}")
            
            return fair_value
            
        except Exception as e:
            logger.error(f"PE valuation failed for {stock_data.symbol}: {e}")
            return None

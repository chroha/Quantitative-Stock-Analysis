"""
PS Valuation Model
Price-to-Sales multiple valuation.
"""

from typing import Optional
from .base_model import BaseValuationModel
from utils.unified_schema import StockData
from utils.logger import setup_logger

logger = setup_logger('ps_valuation')


class PSValuationModel(BaseValuationModel):
    """
    PS Multiple Valuation.
    Fair Value = Sales Per Share × Industry PS
    """
    
    def get_model_name(self) -> str:
        return "ps"
    
    def get_model_display_name(self) -> str:
        return "PS Valuation"
    
    def calculate_fair_value(
        self,
        stock_data: StockData,
        benchmark_data: dict,
        sector: str
    ) -> Optional[float]:
        """Calculate fair value using PS multiple."""
        try:
            # Get latest revenue
            if not stock_data.income_statements:
                logger.warning(f"{stock_data.symbol}: No income statements available")
                return None
            
            latest_income = stock_data.income_statements[0]  # Most recent
            
            if not latest_income.std_revenue or latest_income.std_revenue.value is None:
                logger.warning(f"{stock_data.symbol}: No revenue data")
                return None
            
            revenue = latest_income.std_revenue.value
            
            # Get shares outstanding from same income statement
            if not latest_income.std_shares_outstanding or latest_income.std_shares_outstanding.value is None:
                logger.warning(f"{stock_data.symbol}: No shares outstanding data")
                return None
            
            shares = latest_income.std_shares_outstanding.value
            
            if shares <= 0 or revenue <= 0:
                logger.warning(f"{stock_data.symbol}: Invalid revenue ({revenue}) or shares ({shares})")
                return None
            
            sales_per_share = revenue / shares
            
            # Get industry PS ratio
            sector_benchmarks = benchmark_data.get('sectors', {}).get(sector, {})
            valuation_multiples = sector_benchmarks.get('metrics', {}).get('valuation_multiples', {})
            
            industry_ps = valuation_multiples.get('ps_ratio')
            
            if industry_ps is None or industry_ps <= 0:
                logger.warning(f"{sector}: No valid industry P/S ratio")
                return None
            
            fair_value = sales_per_share * industry_ps
            logger.info(f"{stock_data.symbol}: SPS=${sales_per_share:.2f}, Industry PS={industry_ps:.2f}, Fair Value=${fair_value:.2f}")
            
            return fair_value
            
        except Exception as e:
            logger.error(f"PS valuation failed for {stock_data.symbol}: {e}")
            return None

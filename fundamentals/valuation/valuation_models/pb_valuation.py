"""
PB Valuation Model
Price-to-Book multiple valuation.
"""

from typing import Optional
from .base_model import BaseValuationModel
from utils.unified_schema import StockData
from utils.logger import setup_logger

logger = setup_logger('pb_valuation')


class PBValuationModel(BaseValuationModel):
    """
    PB Multiple Valuation.
    Fair Value = Book Value Per Share × Industry PB
    """
    
    def get_model_name(self) -> str:
        return "pb"
    
    def get_model_display_name(self) -> str:
        return "PB Valuation"
    
    def calculate_fair_value(
        self,
        stock_data: StockData,
        benchmark_data: dict,
        sector: str
    ) -> Optional[float]:
        """Calculate fair value using PB multiple."""
        try:
            # Get latest balance sheet for book value
            if not stock_data.balance_sheets:
                logger.warning(f"{stock_data.symbol}: No balance sheets available")
                return None
            
            latest_bs = stock_data.balance_sheets[0]  # Most recent
            
            # Calculate Book Value Per Share = Shareholders' Equity / Shares Outstanding
            if not latest_bs.std_shareholder_equity or latest_bs.std_shareholder_equity.value is None:
                logger.warning(f"{stock_data.symbol}: No shareholders' equity data")
                return None
            
            # Get shares from income statement (balance sheet doesn't have it)
            if not stock_data.income_statements:
                logger.warning(f"{stock_data.symbol}: No income statements for shares count")
                return None
            
            latest_income = stock_data.income_statements[0]
            if not latest_income.std_shares_outstanding or latest_income.std_shares_outstanding.value is None:
                logger.warning(f"{stock_data.symbol}: No shares outstanding data")
                return None
            
            equity = latest_bs.std_shareholder_equity.value
            shares = latest_income.std_shares_outstanding.value
            
            if shares <= 0 or equity <= 0:
                logger.warning(f"{stock_data.symbol}: Invalid equity ({equity}) or shares ({shares})")
                return None
            
            book_value_per_share = equity / shares
            
            # Get industry PB ratio
            sector_benchmarks = benchmark_data.get('sectors', {}).get(sector, {})
            valuation_multiples = sector_benchmarks.get('metrics', {}).get('valuation_multiples', {})
            
            industry_pb = valuation_multiples.get('pb_ratio')
            
            if industry_pb is None or industry_pb <= 0:
                logger.warning(f"{sector}: No valid industry P/B ratio")
                return None
            
            fair_value = book_value_per_share * industry_pb
            logger.info(f"{stock_data.symbol}: BVPS=${book_value_per_share:.2f}, Industry PB={industry_pb:.2f}, Fair Value=${fair_value:.2f}")
            
            return fair_value
            
        except Exception as e:
            logger.error(f"PB valuation failed for {stock_data.symbol}: {e}")
            return None

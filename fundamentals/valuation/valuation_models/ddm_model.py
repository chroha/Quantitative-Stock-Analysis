"""
DDM (Dividend Discount Model)
Gordon Growth Model for dividend-paying stocks.
"""

from typing import Optional
from .base_model import BaseValuationModel
from utils.unified_schema import StockData
from utils.logger import setup_logger

logger = setup_logger('ddm_model')


class DDMModel(BaseValuationModel):
    """
    Dividend Discount Model (Gordon Growth Model).
    
    Fair Value = D1 / (r - g)
    Where:
    - D1 = Expected dividend next year
    - r = Required rate of return (using CAPM)
    - g = Dividend growth rate
    """
    
    # Constants
    RISK_FREE_RATE = 0.04  # 4% (10-year Treasury)
    MARKET_RETURN = 0.10   # 10% historical market return
    DEFAULT_GROWTH_RATE = 0.03  # 3% if can't calculate from history
    
    def get_model_name(self) -> str:
        return "ddm"
    
    def get_model_display_name(self) -> str:
        return "DDM (Dividend)"
    
    def calculate_fair_value(
        self,
        stock_data: StockData,
        benchmark_data: dict,
        sector: str
    ) -> Optional[float]:
        """Calculate fair value using Gordon Growth Model."""
        try:
            # 1. Get Dividend Data
            if not stock_data.cash_flows:
                logger.warning(f"{stock_data.symbol}: No cash flow statements for dividend data")
                return None
            
            # Sort cash flows by date descending to ensure we check latest first
            sorted_cfs = sorted(
                [cf for cf in stock_data.cash_flows if cf.std_period], 
                key=lambda x: x.std_period, 
                reverse=True
            )
            
            if not sorted_cfs:
                return None

            # Find most recent valid dividend payment (look back up to 2 years)
            dividends_paid = 0
            latest_cf = None
            
            for cf in sorted_cfs[:2]:  # Check latest 2 periods
                if hasattr(cf, 'std_dividends_paid') and cf.std_dividends_paid and cf.std_dividends_paid.value:
                    if cf.std_dividends_paid.value != 0:
                        dividends_paid = abs(cf.std_dividends_paid.value)
                        latest_cf = cf
                        logger.info(f"{stock_data.symbol}: Found dividend data in period {cf.std_period}")
                        break
            
            if dividends_paid == 0:
                logger.warning(f"{stock_data.symbol}: No dividend data available or zero dividends (Non-dividend payer?)")
                return None
            
            # Get shares outstanding to calculate DPS
            if not stock_data.income_statements:
                logger.warning(f"{stock_data.symbol}: No income statements")
                return None
            
            latest_income = stock_data.income_statements[0]
            if not latest_income.std_shares_outstanding or latest_income.std_shares_outstanding.value is None:
                logger.warning(f"{stock_data.symbol}: No shares outstanding")
                return None
            
            shares = latest_income.std_shares_outstanding.value
            if shares <= 0:
                return None
            
            current_dps = dividends_paid / shares  # Dividend per share
            
            # 2. Estimate dividend growth rate
            # Try to use historical data if available
            growth_rate = self._estimate_dividend_growth(stock_data)
            if growth_rate is None:
                growth_rate = self.DEFAULT_GROWTH_RATE
                logger.info(f"{stock_data.symbol}: Using default growth rate {growth_rate*100:.1f}%")
            
            # 3. Calculate required return using CAPM
            # Priority: Stock Beta (Yahoo/FMP) > Industry Beta > Default 1.0
            beta = 1.0
            
            # Try stock-specific beta first
            if stock_data.profile and stock_data.profile.std_beta and stock_data.profile.std_beta.value:
                beta = stock_data.profile.std_beta.value
                logger.info(f"{stock_data.symbol}: Using stock-specific Beta={beta:.3f}")
            else:
                # Fallback to industry beta
                sector_benchmarks = benchmark_data.get('sectors', {}).get(sector, {})
                metrics = sector_benchmarks.get('metrics', {})
                benchmark_beta = metrics.get('beta', {}).get('mean')
                
                if benchmark_beta and benchmark_beta > 0:
                    beta = benchmark_beta
                    logger.info(f"{stock_data.symbol}: Using industry Beta={beta:.2f} (Stock-specific unavailable)")
                else:
                    logger.warning(f"{sector}: No valid beta available, using market beta 1.0")
                    beta = 1.0
            
            # Required return calculation
            # Required return = Risk-free + Beta * (Market - Risk-free)
            required_return = self.RISK_FREE_RATE + beta * (self.MARKET_RETURN - self.RISK_FREE_RATE)
            
            # 4. Check Gordon Growth Model validity
            # If historical growth is higher than required return, it's unsustainable for a perpetual model.
            # In this case, we cap the growth rate to the default rate (3%) or slightly below required return.
            if growth_rate >= required_return:
                logger.warning(f"{stock_data.symbol}: Historical growth ({growth_rate:.1%}) >= Required Return ({required_return:.1%}). Capping growth at {self.DEFAULT_GROWTH_RATE:.1%}")
                growth_rate = self.DEFAULT_GROWTH_RATE
                
                # Double check
                if growth_rate >= required_return:
                    # If it's still too high (e.g. erratic risk free rate), fail gracefully
                    logger.warning(f"{stock_data.symbol}: Adjusted growth still too high, model invalid")
                    return None
            
            # 5. Calculate fair value
            # D1 = D0 * (1 + g)
            next_year_dps = current_dps * (1 + growth_rate)
            fair_value = next_year_dps / (required_return - growth_rate)
            
            logger.info(f"{stock_data.symbol}: DPS=${current_dps:.2f}, Growth={growth_rate*100:.1f}%, Required Return={required_return*100:.1f}%, Fair Value=${fair_value:.2f}")
            
            return fair_value if fair_value > 0 else None
            
        except Exception as e:
            logger.error(f"DDM valuation failed for {stock_data.symbol}: {e}")
            return None
    
    def _estimate_dividend_growth(self, stock_data: StockData) -> Optional[float]:
        """
        Estimate dividend growth rate from historical data.
        
        Returns growth rate or None if insufficient data.
        """
        try:
            if len(stock_data.cash_flows) < 2:
                return None
            
            # Get dividends from last 2 years
            dividends = []
            for cf in stock_data.cash_flows[:2]:
                if cf.std_dividends_paid and cf.std_dividends_paid.value:
                    dividends.append(abs(cf.std_dividends_paid.value))
            
            if len(dividends) < 2:
                return None
            
            # Calculate growth rate: (D1 / D0) - 1
            growth = (dividends[0] / dividends[1]) - 1
            
            # Sanity check: growth should be between -20% and +20%
            if -0.20 <= growth <= 0.20:
                return growth
            else:
                logger.warning(f"Dividend growth {growth*100:.1f}% seems unrealistic, using default")
                return None
                
        except Exception as e:
            logger.debug(f"Could not estimate dividend growth: {e}")
            return None

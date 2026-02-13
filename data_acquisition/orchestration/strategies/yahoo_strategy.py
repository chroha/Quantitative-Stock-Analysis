"""

Yahoo Finance Strategy (Phase 1)

"""

from utils.unified_schema import StockData

from data_acquisition.stock_data.yahoo_fetcher import YahooFetcher

from utils.logger import setup_logger

from .base_strategy import DataSourceStrategy



logger = setup_logger('yahoo_strategy')



"""
Yahoo Finance Strategy (Phase 1)
"""
from utils.unified_schema import StockData
from data_acquisition.stock_data.yahoo_fetcher import YahooFetcher
from utils.logger import setup_logger
from .base_strategy import DataSourceStrategy

logger = setup_logger('yahoo_strategy')

class YahooStrategy(DataSourceStrategy):
    """
    Phase 1: Fetch Base Data from Yahoo Finance.
    Provides: Price History, Profile, Basic Financials.
    """
    
    def fetch_data(self, current_data: StockData) -> StockData:
        logger.info(f"-> [Phase 1] Fetching Base Data (Yahoo Finance) for {self.symbol}...")
        try:
            fetcher = YahooFetcher(self.symbol)
            # YahooFetcher.fetch_all() returns a NEW StockData object
            fetched_data = fetcher.fetch_all()
            
            if fetched_data:
                # Copy forward metrics from profile to forecast_data for consistency
                # Yahoo stores forward EPS/PE in profile, but AI report reads from forecast_data
                if fetched_data.profile:
                    from utils.unified_schema import ForecastData
                    
                    # Initialize forecast_data if not exists
                    if not fetched_data.forecast_data:
                        fetched_data.forecast_data = ForecastData()
                    
                    # Copy forward EPS if available in profile
                    if fetched_data.profile.std_forward_eps and not fetched_data.forecast_data.std_forward_eps:
                        fetched_data.forecast_data.std_forward_eps = fetched_data.profile.std_forward_eps
                        logger.info(f"Copied Forward EPS from profile to forecast_data: {fetched_data.profile.std_forward_eps.value}")
                    
                    # Copy forward PE if available in profile
                    if fetched_data.profile.std_forward_pe and not fetched_data.forecast_data.std_forward_pe:
                        fetched_data.forecast_data.std_forward_pe = fetched_data.profile.std_forward_pe
                        logger.info(f"Copied Forward PE from profile to forecast_data: {fetched_data.profile.std_forward_pe.value}")
                
                # Since this is Phase 1, we can just return what we fetched
                # (or merge if current_data already had something, but usually it's empty)
                return fetched_data
            else:
                logger.warning(f"Yahoo fetch failed for {self.symbol}")
                return current_data
                
        except Exception as e:
            logger.error(f"Yahoo Strategy failed: {e}")
            return current_data

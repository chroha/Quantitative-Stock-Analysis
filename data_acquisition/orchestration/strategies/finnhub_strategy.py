"""
Finnhub Strategy (Phase 3 - Forecasts & Sentiment)
"""
from utils.unified_schema import StockData, AnalystTargets
from data_acquisition.stock_data.finnhub_fetcher import FinnhubFetcher
from data_acquisition.stock_data.intelligent_merger import IntelligentMerger
from utils.logger import setup_logger
from .base_strategy import DataSourceStrategy

logger = setup_logger('finnhub_strategy')

class FinnhubStrategy(DataSourceStrategy):
    """
    Phase 3: Fetch Forecasts, Sentiment, and Basic Info from Finnhub.
    Provides: Analyst Targets, Basic Estimates, Company Profile (Sector/Industry).
    """
    
    def fetch_data(self, current_data: StockData) -> StockData:
        logger.info(f"-> [Phase 3] Fetching Forecasts & Profile (Finnhub) for {self.symbol}...")
        try:
            fetcher = FinnhubFetcher(self.symbol)
            merger = IntelligentMerger(self.symbol)
            
            # 1. Fetch Forecasts (Primary)
            # Returns ForecastData object (not dict)
            forecast_data = fetcher.fetch_forecast_data()
            
            if forecast_data:
                # Merge forecast object if present
                if not current_data.forecast_data:
                    current_data.forecast_data = forecast_data
                    logger.info("Initialized forecast_data from Finnhub")
                else:
                    # Merge specific fields if missing (intelligent field-by-field merge)
                    
                    # Earnings Surprise History
                    if not current_data.forecast_data.std_earnings_surprise_history:
                        current_data.forecast_data.std_earnings_surprise_history = forecast_data.std_earnings_surprise_history
                        if forecast_data.std_earnings_surprise_history:
                            logger.info("Merged earnings surprise history from Finnhub")
                    
                    # Price Targets
                    if not current_data.forecast_data.std_price_target_consensus:
                        current_data.forecast_data.std_price_target_consensus = forecast_data.std_price_target_consensus
                        if forecast_data.std_price_target_consensus:
                            logger.info("Merged price target consensus from Finnhub")
                    
                    if not current_data.forecast_data.std_price_target_low:
                        current_data.forecast_data.std_price_target_low = forecast_data.std_price_target_low
                    
                    if not current_data.forecast_data.std_price_target_high:
                        current_data.forecast_data.std_price_target_high = forecast_data.std_price_target_high
                    
                    if not current_data.forecast_data.std_price_target_avg:
                        current_data.forecast_data.std_price_target_avg = forecast_data.std_price_target_avg
                    
                    if not current_data.forecast_data.std_number_of_analysts:
                        current_data.forecast_data.std_number_of_analysts = forecast_data.std_number_of_analysts
                    
                    # Forward Metrics (PE)
                    if not current_data.forecast_data.std_forward_pe:
                        current_data.forecast_data.std_forward_pe = forecast_data.std_forward_pe
                        if forecast_data.std_forward_pe:
                            logger.info(f"Merged Forward PE from Finnhub: {forecast_data.std_forward_pe.value}")
                    
                    # EPS Estimates (Current Year / Next Year)
                    if not current_data.forecast_data.std_eps_estimate_current_year:
                        current_data.forecast_data.std_eps_estimate_current_year = forecast_data.std_eps_estimate_current_year
                        if forecast_data.std_eps_estimate_current_year:
                            logger.info(f"Merged EPS estimate (CY) from Finnhub: {forecast_data.std_eps_estimate_current_year.value}")
                    
                    if not current_data.forecast_data.std_eps_estimate_next_year:
                        current_data.forecast_data.std_eps_estimate_next_year = forecast_data.std_eps_estimate_next_year
                        if forecast_data.std_eps_estimate_next_year:
                            logger.info(f"Merged EPS estimate (NY) from Finnhub: {forecast_data.std_eps_estimate_next_year.value}")
                    
                    # Revenue Estimates (Current Year / Next Year)
                    if not current_data.forecast_data.std_revenue_estimate_current_year:
                        current_data.forecast_data.std_revenue_estimate_current_year = forecast_data.std_revenue_estimate_current_year
                        if forecast_data.std_revenue_estimate_current_year:
                            logger.info(f"Merged Revenue estimate (CY) from Finnhub: {forecast_data.std_revenue_estimate_current_year.value}")
                    
                    if not current_data.forecast_data.std_revenue_estimate_next_year:
                        current_data.forecast_data.std_revenue_estimate_next_year = forecast_data.std_revenue_estimate_next_year
                        if forecast_data.std_revenue_estimate_next_year:
                            logger.info(f"Merged Revenue estimate (NY) from Finnhub: {forecast_data.std_revenue_estimate_next_year.value}")
                        
                # Update base Analyst Targets if missing (for backward compat)
                if not current_data.analyst_targets:
                     # Construct AnalystTargets from forecast data
                     current_data.analyst_targets = AnalystTargets(
                         std_price_target_low=forecast_data.std_price_target_low,
                         std_price_target_high=forecast_data.std_price_target_high,
                         std_price_target_avg=forecast_data.std_price_target_avg,
                         std_price_target_consensus=forecast_data.std_price_target_consensus,
                         std_number_of_analysts=forecast_data.std_number_of_analysts
                     )

            # 2. Fetch Profile (Secondary - for Gap Filling)
            # Finnhub has good Sector/Industry data if Yahoo is missing it
            finnhub_profile = fetcher.fetch_profile()
            if finnhub_profile:
                current_data.profile = merger.merge_profiles(current_data.profile, finnhub_profile)
                
        except Exception as e:
            logger.warning(f"Finnhub Strategy failed: {e}")
            
        return current_data

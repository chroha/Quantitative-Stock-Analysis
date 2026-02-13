"""
Financial Modeling Prep (FMP) Strategy (Phase 4 - Deep Data)
"""
from typing import Dict, Any
from utils.unified_schema import StockData, IncomeStatement, BalanceSheet, CashFlow
from data_acquisition.stock_data.fmp_fetcher import FMPFetcher
from data_acquisition.stock_data.intelligent_merger import IntelligentMerger
from utils.logger import setup_logger
from .base_strategy import DataSourceStrategy

logger = setup_logger('fmp_strategy')

class FMPStrategy(DataSourceStrategy):
    """
    Phase 4: Fetch Deep Financials and Long History from FMP.
    Provides: Granular Financial Statements, Ratios, Growth Metrics.
    
    Strategy: 
    - Always fetch financial statements to ensure historical depth.
    - Fetch Profile/Ratios to supplement Yahoo.
    - Fetch Estimates if missing from Finnhub.
    """
    
    def fetch_data(self, current_data: StockData) -> StockData:
        logger.info(f"-> [Phase 4] Fetching Deep Data (FMP) for {self.symbol}...")
        try:
            fetcher = FMPFetcher(self.symbol)
            merger = IntelligentMerger(self.symbol)
            
            # 1. Financial Statements (Always Fetch for History)
            # We want to merge FMP data into existing data (Yahoo/EDGAR)
            # FMP is Tier 4 priority, so it won't overwrite existing higher-priority data
            inc = fetcher.fetch_income_statements()
            bal = fetcher.fetch_balance_sheets()
            cf = fetcher.fetch_cash_flow_statements()
            
            # Using empty lists for Yahoo/Edgar args as they are already in current_data
            # The merger handles merging NEW list into OLD list
            if inc: 
                current_data.income_statements = merger.merge_statements(
                    current_data.income_statements, [], inc, [], IncomeStatement
                )
            if bal: 
                current_data.balance_sheets = merger.merge_statements(
                    current_data.balance_sheets, [], bal, [], BalanceSheet
                )
            if cf: 
                current_data.cash_flows = merger.merge_statements(
                    current_data.cash_flows, [], cf, [], CashFlow
                )

            # 2. Profile & Ratios (Supplement Yahoo)
            # Always try to fetch these to fill gaps like 'sector', 'industry', 'website' etc if missing
            ratios = fetcher.fetch_ratios()
            if ratios: 
                current_data.profile = merger.merge_profiles(current_data.profile, ratios)
        
            base_profile = fetcher.fetch_profile()
            if base_profile:
                current_data.profile = merger.merge_profiles(current_data.profile, base_profile)
                
            growth = fetcher.fetch_financial_growth()
            if growth: 
                current_data.profile = merger.merge_profiles(current_data.profile, growth)

            # 3. Forecast Data (Estimates, Price Targets, Growth)
            # Use the new comprehensive fetcher
            forecast = fetcher.fetch_forecast_data()
            if forecast:
                # Merge into existing forecast data or assign if None
                if current_data.forecast_data:
                    # Simple merge: prefer non-null new values
                    fd = current_data.forecast_data
                    if forecast.std_eps_estimate_current_year: fd.std_eps_estimate_current_year = forecast.std_eps_estimate_current_year
                    if forecast.std_revenue_estimate_current_year: fd.std_revenue_estimate_current_year = forecast.std_revenue_estimate_current_year
                    if forecast.std_number_of_analysts: fd.std_number_of_analysts = forecast.std_number_of_analysts
                    
                    if forecast.std_price_target_low: fd.std_price_target_low = forecast.std_price_target_low
                    if forecast.std_price_target_high: fd.std_price_target_high = forecast.std_price_target_high
                    if forecast.std_price_target_avg: fd.std_price_target_avg = forecast.std_price_target_avg
                    if forecast.std_price_target_consensus: fd.std_price_target_consensus = forecast.std_price_target_consensus
                    
                    if forecast.std_earnings_growth_current_year: fd.std_earnings_growth_current_year = forecast.std_earnings_growth_current_year
                    if forecast.std_revenue_growth_next_year: fd.std_revenue_growth_next_year = forecast.std_revenue_growth_next_year
                else:
                    current_data.forecast_data = forecast

            # 4. Analyst Targets (Legacy support/Normalization)
            # Populate analyst_targets from forecast data if missing
            if not current_data.analyst_targets and current_data.forecast_data:
                 from utils.unified_schema import AnalystTargets
                 fd = current_data.forecast_data
                 current_data.analyst_targets = AnalystTargets(
                     std_price_target_low=fd.std_price_target_low,
                     std_price_target_high=fd.std_price_target_high,
                     std_price_target_avg=fd.std_price_target_avg,
                     std_price_target_consensus=fd.std_price_target_consensus,
                     std_number_of_analysts=fd.std_number_of_analysts
                 )

        except Exception as e:
            logger.error(f"FMP Strategy failed: {e}")
            
        return current_data

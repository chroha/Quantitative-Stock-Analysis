"""
Alpha Vantage Strategy (Phase 5 - Fallback)
"""
from typing import Dict, Any
from utils.unified_schema import StockData, IncomeStatement, BalanceSheet, CashFlow
from data_acquisition.stock_data.alphavantage_fetcher import AlphaVantageFetcher
from data_acquisition.stock_data.intelligent_merger import IntelligentMerger
from utils.logger import setup_logger
from .base_strategy import DataSourceStrategy

logger = setup_logger('av_strategy')

class AlphaVantageStrategy(DataSourceStrategy):
    """
    Phase 5: Fetch Fallback Data from Alpha Vantage.
    Provides: Financial Statements (if missing elsewhere), Profile.
    
    Strategy:
    - Only called if critical gaps remain (Enforced by Orchestrator).
    - Fetches full financials to fill gaps.
    """
    
    def fetch_data(self, current_data: StockData) -> StockData:
        logger.info(f"-> [Phase 5] Fetching Fallback Data (Alpha Vantage) for {self.symbol}...")
        try:
            fetcher = AlphaVantageFetcher(self.symbol)
            merger = IntelligentMerger(self.symbol)
            
            # Fetch Financials
            # AV is Tier 5, so merging logic is: merge AV into existing
            inc = fetcher.fetch_income_statements()
            bal = fetcher.fetch_balance_sheets()
            cf = fetcher.fetch_cash_flow_statements()
            
            if inc: 
                current_data.income_statements = merger.merge_statements(
                    current_data.income_statements, [], [], inc, IncomeStatement
                )
            if bal: 
                current_data.balance_sheets = merger.merge_statements(
                    current_data.balance_sheets, [], [], bal, BalanceSheet
                )
            if cf: 
                current_data.cash_flows = merger.merge_statements(
                    current_data.cash_flows, [], [], cf, CashFlow
                )
                
            # Fetch Profile (if needed)
            if not current_data.profile or not current_data.profile.std_market_cap:
                av_profile = fetcher.fetch_profile()
                if av_profile:
                    current_data.profile = merger.merge_profiles(current_data.profile, av_profile)

        except Exception as e:
            logger.error(f"Alpha Vantage Strategy failed: {e}")
            
        return current_data

"""
SEC Edgar Strategy (Phase 2)
"""
from utils.unified_schema import StockData, IncomeStatement, BalanceSheet, CashFlow
from data_acquisition.stock_data.edgar_fetcher import EdgarFetcher
from data_acquisition.stock_data.intelligent_merger import IntelligentMerger
from utils.logger import setup_logger
from .base_strategy import DataSourceStrategy

logger = setup_logger('edgar_strategy')

class EdgarStrategy(DataSourceStrategy):
    """
    Phase 2: Fetch Official Filings from SEC EDGAR.
    Provides: Audited Financial Statements (10-K, 10-Q).
    """
    
    def fetch_data(self, current_data: StockData) -> StockData:
        logger.info(f"-> [Phase 2] Fetching Official Filings (SEC EDGAR) for {self.symbol}...")
        try:
            fetcher = EdgarFetcher()
            # EdgarFetcher returns a dictionary of lists
            edgar_data = fetcher.fetch_all_financials(self.symbol)
            
            merger = IntelligentMerger(self.symbol)
            
            # Merge logic: Integrate EDGAR data into existing data
            if edgar_data.get('income_statements'):
                current_data.income_statements = merger.merge_statements(
                    current_data.income_statements, edgar_data['income_statements'], [], [], IncomeStatement
                )
            if edgar_data.get('balance_sheets'):
                current_data.balance_sheets = merger.merge_statements(
                    current_data.balance_sheets, edgar_data['balance_sheets'], [], [], BalanceSheet
                )
            if edgar_data.get('cash_flows'):
                current_data.cash_flows = merger.merge_statements(
                    current_data.cash_flows, edgar_data['cash_flows'], [], [], CashFlow
                )
                
        except Exception as e:
            logger.error(f"Edgar Strategy failed: {e}")
            
        return current_data

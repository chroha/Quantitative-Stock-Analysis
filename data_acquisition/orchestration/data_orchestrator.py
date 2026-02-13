"""
Data Orchestrator - Central Coordinator for Stock Data Acquisition
"""
from typing import Optional, Dict

from utils.unified_schema import StockData
from utils.logger import setup_logger
from data_acquisition.orchestration.gap_analyzer import GapAnalyzer
from data_acquisition.orchestration.data_processor import DataProcessor
from config.analysis_config import GAP_THRESHOLDS

# Import Strategies
from data_acquisition.orchestration.strategies.yahoo_strategy import YahooStrategy
from data_acquisition.orchestration.strategies.edgar_strategy import EdgarStrategy
from data_acquisition.orchestration.strategies.finnhub_strategy import FinnhubStrategy
from data_acquisition.orchestration.strategies.fmp_strategy import FMPStrategy
from data_acquisition.orchestration.strategies.alphavantage_strategy import AlphaVantageStrategy

logger = setup_logger('data_orchestrator')

class DataOrchestrator:
    """
    Coordinates the multi-stage data acquisition process using the Strategy Pattern.
    
    Phases:
    1. Yahoo Finance (Base) - Always
    2. SEC EDGAR (Official) - Always (if possible)
    3. Finnhub (Forecasts) - Always
    4. FMP (Deep Data) - Always (Default) or Gap Fill (Configurable)
    5. Alpha Vantage (Fallback) - Gap Fill Only
    """
    
    def __init__(self):
        self.gap_analyzer = GapAnalyzer()
        self.processor = DataProcessor()
        # Configuration flags
        self.use_fmp = True 
        self.use_alphavantage = True
        self.efficiency_mode = False # If True, FMP becomes "Gap Fill Only"

    def fetch_stock_data(self, symbol: str) -> StockData:
        """
        Execute the Hybrid Ensemble data fetching strategy.
        """
        logger.info(f"Starting Data Acquisition for {symbol}")
        
        # Initialize empty container
        data = StockData(symbol=symbol)
        
        # Phase 1: Yahoo Finance (Base)
        # Strategy: Always Fetch
        data = YahooStrategy(symbol).fetch_data(data)
        
        # Phase 2: SEC EDGAR (Official)
        # Strategy: Always Fetch
        data = EdgarStrategy(symbol).fetch_data(data)
        
        # Phase 3: Finnhub (Forecasts)
        # Strategy: Always Fetch
        data = FinnhubStrategy(symbol).fetch_data(data)
        
        # Analyze current state
        gaps = self.gap_analyzer.analyze(data)
        self._log_gaps("Phase 3 (Mid-Point)", gaps)

        # Phase 4: FMP (Deep Data)
        # Strategy: Always Fetch (unless efficiency_mode is ON and no gaps)
        # Even if no critical gaps, FMP is valuable for history depth.
        should_run_fmp = self.use_fmp
        if self.efficiency_mode:
             # In efficiency mode, only run if we have gaps
             should_run_fmp = self.use_fmp and (gaps['needs_phase3_fmp'] or gaps['history_gaps']['is_shallow'])
             
        if should_run_fmp:
            data = FMPStrategy(symbol).fetch_data(data)
            gaps = self.gap_analyzer.analyze(data)
            self._log_gaps("Phase 4 (FMP)", gaps)
            
        # Phase 5: Alpha Vantage (Fallback)
        # Strategy: Gap Fill Only
        if gaps['needs_phase4_av'] and self.use_alphavantage:
            data = AlphaVantageStrategy(symbol).fetch_data(data)
            gaps = self.gap_analyzer.analyze(data)
            self._log_gaps("Phase 5 (AV)", gaps)
            
        # Final Processing
        data = self.processor.sanitize_data(data)
        data = self.processor.construct_synthetic_ttm(data)
        
        logger.info(f"Data Acquisition Completed for {symbol}")
        return data

    def _log_gaps(self, phase: str, gaps: Dict):
        """Log the current state of data gaps."""
        status = []
        if gaps.get('critical_error'):
            status.append(f"CRITICAL: {gaps['critical_error']}")
        else:
            if gaps['missing_valuation']: status.append("Valuation")
            if gaps['missing_basic']: status.append("Basic Info")
            if gaps['missing_estimates']: status.append("Estimates")
            if gaps['missing_ebitda']: status.append("EBITDA")
            if gaps['financial_gaps']['is_incomplete']: 
                details = gaps['financial_gaps'].get('details', {})
                missing_fin = [k for k,v in details.items() if not v]
                status.append(f"Financials({','.join(missing_fin)})")
            if gaps['history_gaps']['is_shallow']:
                status.append(f"History(<4y)")
        
        logger.info(f"   [{phase}] Gaps Remaining: {', '.join(status) if status else 'None'}")

"""
Data Loader Module - Unified External Entry Point for Data Acquisition
"""
import json
import os
from datetime import datetime
from typing import Optional
from utils.unified_schema import StockData
from utils.logger import setup_logger

logger = setup_logger('data_loader')

class StockDataLoader:
    """
    Stock Data Loader - Main entry point class for the Data Acquisition Layer.
    Facade for DataOrchestrator.
    """
    
    def __init__(self, use_alphavantage: bool = True):
        try:
            from data_acquisition.orchestration.data_orchestrator import DataOrchestrator
            self.orchestrator = DataOrchestrator()
            self.orchestrator.use_alphavantage = use_alphavantage
            self.orchestrator.use_fmp = True
        except Exception as e:
            logger.error(f"DEBUG: Import Failed: {e}")
            raise e
    
    def fetch_stock_data(self, symbol: str) -> StockData:
        return self.orchestrator.fetch_stock_data(symbol)

    def get_stock_data(self, symbol: str, force_refresh: bool = False) -> StockData:
        """
        Smart fetch: Check local cache first, if missing/old, then fetch from APIs.
        """
        from config.constants import DATA_CACHE_STOCK
        from datetime import datetime
        import glob
        
        # 1. Try to load from cache if not forced
        if not force_refresh:
            try:
                # Find latest file: initial_data_SYMBOL_YYYY-MM-DD.json
                search_pattern = os.path.join(DATA_CACHE_STOCK, f"initial_data_{symbol}_*.json")
                files = sorted(glob.glob(search_pattern))
                
                if files:
                    latest_file = files[-1]
                    # Check age (e.g., 24 hours) - For now just check if it's from today? 
                    # Actually user said "validation might fetch to get fresh price", so maybe strict age?
                    # Let's say if file date is TODAY, we use it. 
                    # Or maybe just return it if it exists and let caller decide?
                    # User complaint was about "run_valuation" running AGAIN after "run_scoring".
                    # Those happen in same session, so file should definitely be used.
                    
                    # Logic: If file date == today, use it.
                    file_date_str = os.path.basename(latest_file).split('_')[-1].replace('.json', '')
                    today_str = datetime.now().strftime('%Y-%m-%d')
                    
                    if file_date_str == today_str:
                        logger.info(f"Loading cached data for {symbol}: {os.path.basename(latest_file)}")
                        return self.load_stock_data(latest_file)
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")

        # 2. Fetch from APIs
        return self.fetch_stock_data(symbol)

    def save_stock_data(self, data: StockData, output_dir: str) -> str:
        """
        Save StockData object to JSON file.
        Matches legacy behavior for run_analysis.py.
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            
        filename = f"initial_data_{data.symbol}_{datetime.now().strftime('%Y-%m-%d')}.json"
        filepath = os.path.join(output_dir, filename)
        
        try:
            # Helper to serialize datetime/enum
            def default_serializer(obj):
                if isinstance(obj, (datetime)):
                    return obj.isoformat()
                return str(obj)

            with open(filepath, 'w', encoding='utf-8') as f:
                # Use model_dump if Pydantic v2, dict() if v1
                # unified_schema uses Pydantic BaseModel
                json_data = data.model_dump() if hasattr(data, 'model_dump') else data.dict()
                json.dump(json_data, f, indent=4, default=default_serializer)
                
            logger.info(f"Saved stock data to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save stock data: {e}")
            raise e

    def load_stock_data(self, file_path: str) -> StockData:
        """
        Load StockData from JSON file.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data_dict = json.load(f)
                return StockData(**data_dict)
        except Exception as e:
            logger.error(f"Failed to load stock data from {file_path}: {e}")
            # Identify if it's a validation error or file error
            raise e

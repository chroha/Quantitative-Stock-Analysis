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

    def get_stock_data(self, symbol: str) -> StockData:
        """Alias for fetch_stock_data to maintain backward compatibility."""
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

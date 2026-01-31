"""
Financial Data Output Generator.
Reads raw stock data, runs fundamental calculators,
and outputs calculated financial metrics.
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path
from dataclasses import asdict
from typing import Dict, Any, Optional



from utils.logger import setup_logger
from data_acquisition import StockDataLoader
from fundamentals.financial_data.profitability import ProfitabilityCalculator
from fundamentals.financial_data.growth import GrowthCalculator
from fundamentals.financial_data.capital_allocation import CapitalAllocationCalculator

logger = setup_logger('financial_data_output')


class FinancialDataGenerator:
    """
    Orchestrates the calculation of fundamental metrics and saving of results.
    """
    
    def __init__(self, data_dir: str):
        """
        Initialize generator.
        
        Args:
            data_dir: Directory for reading/writing data files (required)
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Initialize calculators (they are stateless per symbol usually, or cheap to init)
        # Actually calculators take symbol in __init__, so we instantiate per symbol
        self.loader = StockDataLoader()
        
    def _find_latest_file(self, symbol: str) -> Optional[Path]:
        """Find the most recent initial_data file for a symbol."""
        pattern = f"initial_data_{symbol}_*.json"
        files = list(self.data_dir.glob(pattern))
        
        if not files:
            return None
            
        # Sort by modification time (or filename date)
        # Filename format: initial_data_AAPL_2026-01-16.json
        # We can just sort by name as ISO date sorts correctly string-wise
        files.sort(reverse=True)
        return files[0]

    def _get_input_path(self, symbol: str, date_str: Optional[str] = None) -> Path:
        """Get the path to the input JSON file."""
        if date_str:
            filename = f"initial_data_{symbol}_{date_str}.json"
            return self.data_dir / filename
        else:
            found = self._find_latest_file(symbol)
            if found:
                return found
            # Fallback to today's date if no file found (will likely fail later)
            today = datetime.now().strftime("%Y-%m-%d")
            return self.data_dir / f"initial_data_{symbol}_{today}.json"

    def generate(self, symbol: str, date_str: Optional[str] = None, quiet: bool = False) -> Optional[str]:
        """
        Generate financial data for a stock.
        
        Args:
            symbol: Stock ticker
            date_str: Date string YYYY-MM-DD. If None, uses latest available or today.
            quiet: If True, suppress console output (for use by run_analysis.py)
            
        Returns:
            Path to generated file or None if failed
        """
        symbol = symbol.upper()
        input_path = self._get_input_path(symbol, date_str)
        
        if not input_path.exists():
            logger.error(f"Input file not found: {input_path}")
            print(f"[ERROR] No data file found for {symbol} at {input_path}")
            return None
            
        logger.info(f"Loading data from {input_path}")
        try:
            # Load stock data
            stock_data = self.loader.load_stock_data(str(input_path))
            if not stock_data:
                logger.error("Failed to load stock data object")
                return None
                
            # Initialize calculators
            prof_calc = ProfitabilityCalculator(symbol)
            growth_calc = GrowthCalculator(symbol)
            cap_alloc_calc = CapitalAllocationCalculator(symbol)
            
            # Run calculations
            logger.info("Running fundamental calculations...")
            prof_metrics = prof_calc.calculate_all(stock_data)
            growth_metrics = growth_calc.calculate_all(stock_data)
            cap_alloc_metrics = cap_alloc_calc.calculate_all(stock_data)
            
            # Extract sector from profile
            sector = "Unknown"
            if stock_data.profile and stock_data.profile.std_sector:
                sector = stock_data.profile.std_sector.value

            # Construct output
            output_data = {
                "metadata": {
                    "symbol": symbol,
                    "sector": sector,
                    "generated_at": datetime.now().isoformat(),
                    "source_file": input_path.name,
                    "version": "3.0"
                },
                "metrics": {
                    "profitability": asdict(prof_metrics),
                    "growth": asdict(growth_metrics),
                    "capital_allocation": asdict(cap_alloc_metrics)
                }
            }
            
            # Clean up dataclass dicts (convert datetime to str if needed)
            # asdict handles basics, but datetime objects need serialization helper if json dump fails
            # But ProfitabilityMetrics has default_factory=datetime.now
            
            # Generate output filename
            # Use the date from the INPUT file to match versions
            # Extract date from input filename: initial_data_SYMBOL_YYYY-MM-DD.json
            try:
                # initial_data_SYMBOL_YYYY-MM-DD.json
                # Split by underscore
                parts = input_path.stem.split('_')
                # Date is the last part
                data_date = parts[-1] 
            except:
                data_date = datetime.now().strftime("%Y-%m-%d")
            
            output_filename = f"financial_data_{symbol}_{data_date}.json"
            output_path = self.data_dir / output_filename
            
            # Save JSON
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, default=str, ensure_ascii=False)
                
            logger.info(f"Saved financial data to {output_path}")
            if not quiet:
                print(f"[OK] Financial data generated: {output_path}")
            
            return str(output_path)
            
        except Exception as e:
            logger.exception(f"Failed to generate financial data for {symbol}")
            print(f"[ERROR] Generation failed: {e}")
            return None



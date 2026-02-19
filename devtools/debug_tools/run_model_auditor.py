"""
Model Auditor Tool
==================
Consolidated tool for verifying logic, scoring models, and valuation calculations.
Replaces:
- run_debug_financial_scoring.py
- run_debug_technical_scoring.py
- run_debug_valuation.py
- run_debug_analysis.py
"""

import sys
import os
import argparse
from typing import Optional
from pathlib import Path

# Ensure project root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.constants import DATA_CACHE_STOCK, DATA_CACHE_BENCHMARK
from utils.logger import setup_logger
from utils.console_utils import print_header, symbol as console_symbol

# Import Generators/Calculators
from fundamentals.financial_scorers.financial_scorers_output import FinancialScorerGenerator
from fundamentals.technical_scorers.technical_scorers_output import TechnicalScorerGenerator
from fundamentals.financial_data.financial_data_output import FinancialDataGenerator
from fundamentals.valuation import ValuationCalculator
from fundamentals.valuation.valuation_output import ValuationOutput
from data_acquisition import StockDataLoader
from data_acquisition.benchmark_data.benchmark_data_loader import BenchmarkDataLoader

# Import Full Pipeline Components for Option 4
# (Assuming run_debug_analysis.py logic is mainly orchestrating these)

logger = setup_logger("model_auditor")

class ModelAuditor:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.benchmark_dir = os.path.join(project_root, DATA_CACHE_BENCHMARK)
        
    def ensure_data_available(self, symbol: str) -> bool:
        """Check if data exists, if not auto-fetch and save to standard cache."""
        try:
             # Helper to check if data exists recently
            from datetime import datetime
            
            # 1. Check/Fetch Initial Data
            data_file_pattern = f"initial_data_{symbol}_*.json"
            files = sorted(list(Path(self.output_dir).glob(data_file_pattern)))
            
            should_fetch = True
            if files:
                latest_file = files[-1]
                file_date_str = latest_file.stem.split('_')[-1] # Extract YYYY-MM-DD
                try:
                    file_date = datetime.strptime(file_date_str, "%Y-%m-%d")
                    if (datetime.now() - file_date).days < 2:
                        should_fetch = False
                except:
                    pass

            if should_fetch:
                print(f"  {console_symbol.INFO} Data missing or old. Auto-fetching {symbol}...")
                loader = StockDataLoader()
                stock_data = loader.get_stock_data(symbol)
                saved_path = loader.save_stock_data(stock_data, self.output_dir)
                print(f"  {console_symbol.OK} Data Saved to: {os.path.basename(saved_path)}")
                
            return True
        except Exception as e:
            logger.error(f"Data Assurance Error: {e}")
            print(f"{console_symbol.FAIL} Failed to ensure data: {e}")
            return False

    def run_financial_scoring(self, symbol: str):
        """Run Financial Scoring Logic."""
        print(f"\n--- Running Financial Scoring ({symbol}) ---")
        
        # 1. Ensure Raw Data
        if not self.ensure_data_available(symbol): return
        
        try:
            # 2. Generate Financial Metrics (Intermediate Step)
            print(f"  {console_symbol.ARROW} Generating Financial Metrics...")
            # Silence output from generator unless error
            metrics_gen = FinancialDataGenerator(data_dir=self.output_dir)
            metrics_path = metrics_gen.generate(symbol, quiet=True)
            
            if not metrics_path:
                print(f"{console_symbol.FAIL} Failed to generate metrics (required for scoring).")
                return
                
            # 3. Score
            generator = FinancialScorerGenerator(data_dir=self.output_dir, benchmark_dir=self.benchmark_dir)
            result = generator.generate(symbol)
            if result:
                print(f"{console_symbol.OK} Financial Scoring Complete.")
            else:
                print(f"{console_symbol.FAIL} Financial Scoring Failed.")
        except Exception as e:
            logger.error(f"Financial Scoring Error: {e}")
            print(f"{console_symbol.FAIL} Error: {e}")

    def run_technical_scoring(self, symbol: str):
        """Run Technical Scoring Logic."""
        print(f"\n--- Running Technical Scoring ({symbol}) ---")
        if not self.ensure_data_available(symbol): return
        
        try:
            generator = TechnicalScorerGenerator(data_dir=self.output_dir)
            result = generator.generate(symbol)
            if result:
                print(f"{console_symbol.OK} Technical Scoring Complete.")
            else:
                print(f"{console_symbol.FAIL} Technical Scoring Failed.")
        except Exception as e:
            logger.error(f"Technical Scoring Error: {e}")
            print(f"{console_symbol.FAIL} Error: {e}")

    def run_valuation(self, symbol: str):
        """Run Valuation Models (DCF, etc)."""
        print(f"\n--- Running Valuation Models ({symbol}) ---")
        # Ensure data, but ValuationCalculator usually loads via StockDataLoader internally ?? 
        # Actually ValuationCalculator.calculate_valuation takes stock_data object.
        # So we need to load it here or let the calculator handle it?
        # looking at previous code: 
        # loader = StockDataLoader()
        # stock_data = loader.get_stock_data(symbol)
        # So we should ensure data is ready, then load it.
        
        if not self.ensure_data_available(symbol): return

        try:
            loader = StockDataLoader()
            stock_data = loader.get_stock_data(symbol)
            
            calculator = ValuationCalculator(benchmark_data_path=self.benchmark_dir)
            result = calculator.calculate_valuation(stock_data)
            
            ValuationOutput.print_console(result)
            json_path = ValuationOutput.save_json(result, self.output_dir)
            print(f"{console_symbol.OK} Valuation Saved: {os.path.basename(json_path)}")
            
        except Exception as e:
            logger.error(f"Valuation Error: {e}")
            print(f"{console_symbol.FAIL} Error: {e}")

    def run_full_pipeline(self, symbol: str):
        """Run Full Analysis Pipeline (Data -> Score -> Value)."""
        print(f"\n--- Running Full Analysis Pipeline ({symbol}) ---")
        try:
            # 1. Check & Fetch Data
            print(f"\n[1/3] Data Acquisition...")
            if not self.ensure_data_available(symbol): return
            print(f"{console_symbol.OK} Data Ready.")
            
            # 2. Benchmarks & Scoring
            print(f"\n[2/3] Scoring Models...")
            self.run_financial_scoring(symbol)
            self.run_technical_scoring(symbol)
            
            # 3. Valuation
            print(f"\n[3/3] Valuation...")
            self.run_valuation(symbol)
            
            print(f"\n{console_symbol.OK} Full Pipeline Analysis Complete.")
            
        except Exception as e:
            logger.error(f"Pipeline Error: {e}")
            print(f"{console_symbol.FAIL} Error: {e}")


def interactive_menu():
    output_dir = os.path.join(project_root, DATA_CACHE_STOCK)
    auditor = ModelAuditor(output_dir)
    
    while True:
        print_header("MODEL AUDITOR TOOL (Logic Verification)")
        print("1. Audit Financial Scoring")
        print("2. Audit Technical Scoring")
        print("3. Audit Valuation Models (DCF)")
        print("4. Run Full Pipeline Analysis")
        print("5. Exit")
        
        choice = input("\nSelect Option [1-5]: ").strip()
        
        if choice == '5':
            break
            
        symbol = input("Enter Stock Symbol (e.g. AAPL): ").strip().upper()
        if not symbol: continue
        
        if choice == '1':
            auditor.run_financial_scoring(symbol)
        elif choice == '2':
            auditor.run_technical_scoring(symbol)
        elif choice == '3':
            auditor.run_valuation(symbol)
        elif choice == '4':
            auditor.run_full_pipeline(symbol)
        else:
            print("Invalid selection.")
        
        # input("\nPress Enter to continue...") # Removed for better UX

def main():
    parser = argparse.ArgumentParser(description='Run Model Auditor')
    parser.add_argument('symbol', nargs='?', help='Stock symbol')
    parser.add_argument('--mode', choices=['financial', 'technical', 'valuation', 'full'], default='full')
    args = parser.parse_args()
    
    if args.symbol:
        output_dir = os.path.join(project_root, DATA_CACHE_STOCK)
        auditor = ModelAuditor(output_dir)
        sym = args.symbol.upper()
        
        if args.mode == 'financial':
            auditor.run_financial_scoring(sym)
        elif args.mode == 'technical':
            auditor.run_technical_scoring(sym)
        elif args.mode == 'valuation':
            auditor.run_valuation(sym)
        elif args.mode == 'full':
            auditor.run_full_pipeline(sym)
    else:
        interactive_menu()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")

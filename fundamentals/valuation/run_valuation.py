"""
Valuation Analysis Runner
Run this script to interactively perform stock valuation.
"""

import sys
import os
from pathlib import Path

# Setup project root path
current_dir = os.path.dirname(os.path.abspath(__file__))
# .../fundamentals/valuation
# We need to go up 2 levels?
# No wait:
# script: .../fundamentals/valuation/run_valuation.py
# dir: .../fundamentals/valuation
# parent: .../fundamentals
# gran: .../Quantitative Stock Analysis V3.0
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir))) 
# Wait, let's verify again.
# standard: os.path.dirname(os.path.abspath(__file__)) gives "X:\...\valuation"
# dirname 1: "X:\...\fundamentals"
# dirname 2: "X:\...\Quantitative Stock Analysis V3.0"
# So 2 levels of os.path.dirname calls on the current_dir.
project_root = os.path.dirname(os.path.dirname(current_dir))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.constants import DATA_CACHE_STOCK, DATA_CACHE_BENCHMARK
from fundamentals.valuation import ValuationCalculator
from fundamentals.valuation.valuation_output import ValuationOutput
from data_acquisition import StockDataLoader
from datetime import datetime

def main():
    print("\n" + "="*60)
    print("Valuation Analysis Runner")
    print("="*60)
    
    try:
        # Get ticker from user
        ticker = input("Enter stock symbol (e.g., AAPL): ").strip().upper()
        if not ticker:
            print("Operation cancelled.")
            return
            
        # Step 1: Load/Fetch stock data
        print(f"\nStep 1: Checking data for {ticker}...")
        loader = StockDataLoader()
        
        # Try to load existing data first to save time
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # Use unified data cache paths
        output_dir = os.path.join(project_root, DATA_CACHE_STOCK)
        benchmark_dir = os.path.join(project_root, DATA_CACHE_BENCHMARK)
        data_path = os.path.join(output_dir, f"initial_data_{ticker}_{current_date}.json")
        
        if os.path.exists(data_path):
            print(f"  Found existing data: {os.path.basename(data_path)}")
            stock_data = loader.load_stock_data(data_path)
        else:
            print(f"  Fetching fresh data for {ticker}...")
            # Interactive fetch might print its own logs, that's fine.
            stock_data = loader.get_stock_data(ticker)
            loader.save_stock_data(stock_data, output_dir)
        
        print(f"  [OK] Stock data ready")
        
        # Step 2: Initialize valuation calculator
        print(f"\nStep 2: Initializing valuation calculator...")
        # Calculator expects benchmark data in benchmark_dir
        calculator = ValuationCalculator(benchmark_data_path=benchmark_dir)
        
        # Step 3: Calculate valuation
        print(f"\nStep 3: Calculating valuation...")
        valuation_result = calculator.calculate_valuation(stock_data)
        
        # Step 4: Display results
        print(f"\nStep 4: Report")
        ValuationOutput.print_console(valuation_result)
        
        # Step 5: Save to JSON
        json_path = ValuationOutput.save_json(valuation_result, output_dir)
        print(f"[OK] Results saved to: {json_path}")
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"\n[ERROR] An error occurred: {e}")
        # import traceback
        # traceback.print_exc()

if __name__ == "__main__":
    main()

"""
Financial Data Generation Runner.
Interact with this script to generate financial metrics from fetched stock data.
"""

import sys
import os
from pathlib import Path

# Setup project root path
# We are in fundamentals/financial_data/run_financial_data.py
# Root is ../../..
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
# Wait, let's count carefully.
# .../Quantitative Stock Analysis V3.0/fundamentals/financial_data/run_financial_data.py
# current_dir = .../financial_data
# parent 1 = .../fundamentals
# parent 2 = .../Quantitative Stock Analysis V3.0
project_root = os.path.dirname(os.path.dirname(current_dir))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.constants import DATA_CACHE_STOCK
from fundamentals.financial_data.financial_data_output import FinancialDataGenerator

def main():
    """Interactive mode for generating financial data."""
    print("\n" + "="*80)
    print("  FINANCIAL DATA GENERATOR")
    print("="*80)
    
    # Interactive input
    try:
        symbol = input("\nEnter stock symbol (e.g. AAPL): ").strip().upper()
        
        if not symbol:
            print("[ERROR] Stock symbol cannot be empty.")
            sys.exit(1)
        
        # Use unified data cache path
        data_dir = os.path.join(project_root, DATA_CACHE_STOCK)
        generator = FinancialDataGenerator(data_dir=data_dir)
        
        # Try to find the latest file for this symbol
        latest_file = generator._find_latest_file(symbol)
        
        if not latest_file:
            print(f"\n[ERROR] No data found for {symbol}")
            print(f"Looking for: {data_dir}/initial_data_{symbol}_*.json")
            print(f"\nPlease run data acquisition first:")
            print(f"  python data_acquisition/stock_data/run_stock_fetch.py")
            sys.exit(1)
        
        print(f"\n[INFO] Using data file: {latest_file.name}")
        
        # Generate financial data
        result = generator.generate(symbol)
        
        if result:
            print(f"\n{'='*80}")
            print("SUCCESS")
            print(f"{'='*80}")
            sys.exit(0)
        else:
            print(f"\n{'='*80}")
            print("FAILED")
            print(f"{'='*80}")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] An error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

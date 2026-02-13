"""
Stock Data Fetch Runner
Run this script to interactively fetch and save stock data using the new Hybrid Ensemble Strategy.

Usage:
  python data_acquisition/stock_data/run_stock_fetch.py
"""

import sys
import os

# Setup project root path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from data_acquisition.stock_data.initial_data_loader import StockDataLoader
from config.constants import DATA_CACHE_STOCK

def main():
    print("\n" + "="*60)
    print("Stock Data Fetcher (Hybrid Ensemble)")
    print("="*60)
    print("\nData Sources: Yahoo, EDGAR, Finnhub, FMP, Alpha Vantage")
    
    try:
        symbol = input("\nEnter stock symbol (e.g., AAPL): ").strip().upper()
        if not symbol:
            print("Operation cancelled (empty symbol).")
            return
        
        print(f"\n[1/3] Initializing data loader...")
        loader = StockDataLoader(use_alphavantage=True)
        
        print(f"[2/3] Fetching data for {symbol}...")
        data = loader.get_stock_data(symbol)
        
        print(f"[3/3] Saving data...")
        # Add output_dir argument
        output_dir = os.path.join(project_root, DATA_CACHE_STOCK)
        saved_path = loader.save_stock_data(data, output_dir)
        
        print(f"\n{'='*60}")
        print(f"[SUCCESS] Data acquired and saved!")
        print(f"{'='*60}")
        print(f"\n  Output File: {saved_path}")
        
        # Summary
        print(f"\n  DATA SUMMARY:")
        print(f"  {'─'*40}")
        print(f"  Price History:    {len(data.price_history)} days")
        print(f"  Income Statements: {len(data.income_statements)} periods")
        print(f"  Balance Sheets:    {len(data.balance_sheets)} periods")
        print(f"  Cash Flow Stmts:   {len(data.cash_flows)} periods")
        
        if data.profile:
            sector = data.profile.std_sector.value if data.profile.std_sector else "N/A"
            industry = data.profile.std_industry.value if data.profile.std_industry else "N/A"
            print(f"\n  Company: {data.profile.std_company_name.value if data.profile.std_company_name else symbol}")
            print(f"  Sector:  {sector}")
            print(f"  Industry: {industry}")
            
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\n[ERROR] An error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

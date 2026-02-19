
import sys
import os
import logging

# Add project root to path
sys.path.insert(0, os.getcwd())

from data_acquisition.stock_data.initial_data_loader import StockDataLoader
from fundamentals.financial_data.growth import GrowthCalculator
from config.constants import DATA_CACHE_STOCK

# Setup logging to console
logging.basicConfig(level=logging.INFO)

def debug_growth(symbol):
    print(f"Loading data for {symbol}...")
    loader = StockDataLoader()
    # Assuming file exists from previous run
    data_path = os.path.join(DATA_CACHE_STOCK, f"initial_data_{symbol}_2026-02-16.json")
    
    if not os.path.exists(data_path):
        # Try finding any file
        import glob
        files = glob.glob(os.path.join(DATA_CACHE_STOCK, f"initial_data_{symbol}_*.json"))
        if files:
            data_path = files[-1]
            print(f"Using {data_path}")
        else:
            print("No data file found")
            return

    stock_data = loader.load_stock_data(data_path)
    print(f"Stock Data Loaded. Income Stmts: {len(stock_data.income_statements)}")
    
    # Check periods
    fy_stmts = [s for s in stock_data.income_statements 
                if getattr(s, 'std_period_type', 'FY') in ['FY', 'TTM']]
    print(f"FY/TTM Stmts: {len(fy_stmts)}")
    for i, s in enumerate(fy_stmts):
        print(f"  [{i}] {s.std_period} ({s.std_period_type}) Rev: {s.std_revenue.value if s.std_revenue else 'None'}")

    calc = GrowthCalculator(symbol)
    metrics = calc.calculate_all(stock_data)
    
    print("\nMetrics:")
    print(f"Rev CAGR: {metrics.revenue_cagr_5y}")
    print(f"NI CAGR: {metrics.net_income_cagr_5y}")
    print(f"FCF CAGR: {metrics.fcf_cagr_5y}")
    print(f"Warnings: {metrics.warnings}")

if __name__ == "__main__":
    debug_growth("AAPL")

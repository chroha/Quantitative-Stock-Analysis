"""
Stock Data Fetch Runner
Run this script to interactively fetch and save stock data with 3-tier cascade:
  1. Yahoo Finance (primary)
  2. FMP (supplementary)
  3. Alpha Vantage (fallback)

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


from utils.console_utils import symbol

def print_validation_report(loader: StockDataLoader, symbol_str: str):
    """Print detailed validation report."""
    result = loader.get_validation_report()
    if not result:
        print("  [No validation data available]")
        return
    
    print(f"\n{'='*60}")
    print(f"VALIDATION REPORT: {symbol_str}")
    print(f"{'='*60}")
    
    status_overall = f"{symbol.OK} COMPLETE" if result.is_complete else f"{symbol.WARN} INCOMPLETE"
    print(f"\n  Overall Status: {status_overall}")
    print(f"  Completeness:   {result.average_completeness:.1%}")
    print(f"  Periods Validated: {result.total_periods_validated}")
    print(f"  Incomplete Periods: {result.incomplete_periods}")
    
    if result.period_results:
        print(f"\n  {'Period':<15} {'Type':<12} {'Status':<10} {'Score':<8}")
        print(f"  {'-'*15} {'-'*12} {'-'*10} {'-'*8}")
        
        for pr in result.period_results:
            status = f"{symbol.OK} OK" if pr.is_complete else f"{symbol.WARN} MISSING"
            print(f"  {pr.period:<15} {pr.statement_type:<12} {status:<10} {pr.completeness_score:.0%}")
            
            if pr.missing_required:
                print(f"    └─ Required missing: {', '.join(pr.missing_required)}")
            if pr.missing_important and not pr.is_complete:
                print(f"    └─ Important missing: {', '.join(pr.missing_important[:3])}...")
    
    print(f"{'='*60}\n")


def main():
    print("\n" + "="*60)
    print("Stock Data Fetcher (3-Tier Cascade)")
    print("="*60)
    print("\nData Sources: Yahoo Finance → FMP → Alpha Vantage")
    print("With field-level validation for each period")
    
    try:
        symbol = input("\nEnter stock symbol (e.g., AAPL): ").strip().upper()
        if not symbol:
            print("Operation cancelled (empty symbol).")
            return
        
        print(f"\n[1/3] Initializing data loader...")
        loader = StockDataLoader(use_alphavantage=True)
        
        print(f"[2/3] Fetching data for {symbol} (may take 20-30 seconds)...")
        data = loader.get_stock_data(symbol)
        
        print(f"[3/3] Saving data...")
        saved_path = loader.save_stock_data(data)
        
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
        
        # Print detailed validation report
        print_validation_report(loader, symbol)
        
        print("\n[TIP] Review the validation report above for data completeness.")
        print("      If there are missing required fields, check the log files for details.")
            
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\n[ERROR] An error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

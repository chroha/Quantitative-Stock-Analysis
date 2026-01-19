"""
Test script for verifying the new V2 data pipeline with IntelligentMerger.
"""
import sys
sys.path.insert(0, '.')

from data_acquisition.stock_data.initial_data_loader import StockDataLoader

def test_v2_pipeline(symbol: str = "AAPL"):
    """Test the new get_stock_data_v2 method."""
    print(f"\n{'='*60}")
    print(f"Testing V2 Pipeline for: {symbol}")
    print(f"{'='*60}\n")
    
    loader = StockDataLoader(use_alphavantage=False)  # Skip AV for faster test
    
    try:
        data = loader.get_stock_data_v2(symbol)
        
        print(f"\n--- Results ---")
        print(f"Symbol: {data.symbol}")
        print(f"Income Statements: {len(data.income_statements)}")
        print(f"Balance Sheets: {len(data.balance_sheets)}")
        print(f"Cash Flows: {len(data.cash_flows)}")
        
        if loader.validation_result:
            print(f"\nCompleteness: {loader.validation_result.average_completeness:.1%}")
            print(f"Is Complete: {loader.validation_result.is_complete}")
        
        # Check a sample field to verify merge
        if data.income_statements:
            stmt = data.income_statements[0]
            print(f"\nSample Period: {stmt.std_period}")
            if stmt.std_revenue:
                print(f"  Revenue: {stmt.std_revenue.value:,.0f} (source: {stmt.std_revenue.source})")
            if stmt.std_net_income:
                print(f"  Net Income: {stmt.std_net_income.value:,.0f} (source: {stmt.std_net_income.source})")
        
        print(f"\n{'='*60}")
        print("V2 Pipeline Test: SUCCESS")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    test_v2_pipeline(symbol)

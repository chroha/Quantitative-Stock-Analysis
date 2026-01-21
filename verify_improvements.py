import os
import dotenv
from pathlib import Path

# Load environment variables (User Config)
env_path = Path('user_config') / '.env'
dotenv.load_dotenv(dotenv_path=env_path)

from data_acquisition.stock_data.initial_data_loader import StockDataLoader

def main():
    symbol = "NVDA" 
    print(f"Testing Data Acquisition with OpenBB v4.4.4 (Tier 0) for {symbol}...")
    
    # Initialize loader with OpenBB enabled
    loader = StockDataLoader(use_alphavantage=False, use_openbb=True)
    
    try:
        # Fetch data
        data = loader.get_stock_data(symbol)
        
        print("\nFETCH SUCCESSFUL!")
        print(f"Symbol: {data.symbol}")
        
        # Check Source Metadata
        if data.profile and data.profile.std_company_name:
             print(f"Profile Source: {data.profile.std_company_name.source}")
        
        # Check if any field came from OpenBB
        sources = set()
        for stmt in data.income_statements:
            # Fix Pydantic deprecation check
            fields = getattr(stmt, 'model_fields', None)
            if not fields:
                 # Fallback for older pydantic
                 fields = stmt.__fields__
                 
            for field in fields:
                val = getattr(stmt, field)
                if hasattr(val, 'source') and val.source:
                    sources.add(val.source)
        
        print(f"Sources utilized in Income Statements: {sources}")
        
    except Exception as e:
        print(f"\nFETCH FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

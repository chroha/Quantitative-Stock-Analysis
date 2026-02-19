
import json
import os
import sys

# Path to the cache directory
CACHE_DIR = "c:/Users/chr0h/OneDrive/美股/Quantitative Stock Analysis/data/cache/stock"
SYMBOL = "AAPL"
DATE = "2026-02-16"

initial_file = os.path.join(CACHE_DIR, f"initial_data_{SYMBOL}_{DATE}.json")
financial_file = os.path.join(CACHE_DIR, f"financial_data_{SYMBOL}_{DATE}.json")

def inspect_json(filepath, name):
    print(f"Inspecting {name} ({filepath})...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if name == "Initial":
            cfs = data.get('cash_flows', [])
            print(f"  Total Cash Flows: {len(cfs)}")
            for i, cf in enumerate(cfs[:3]): # Show first 3
                print(f"    CF[{i}]: Period={cf.get('std_period')}, OCF={cf.get('std_operating_cash_flow')}")
                
        elif name == "Financial":
            # Financial data structure might be different
            # It usually has 'metrics' or similar
            # Let's check keys
            print(f"  Keys: {list(data.keys())}")
            # It likely has 'cash_flow' or similar key
            if 'cash_flow_statement' in data:
                 print(f"  CF Statement: {data['cash_flow_statement']}")
            # Or maybe just metrics flattened?
            
    except Exception as e:
        print(f"  Error reading {name}: {e}")

if __name__ == "__main__":
    inspect_json(initial_file, "Initial")
    print("-" * 50)
    inspect_json(financial_file, "Financial")

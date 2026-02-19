
import json
import sys
from pathlib import Path

path = r"c:\Users\chr0h\OneDrive\美股\Quantitative Stock Analysis\data\cache\stock\initial_data_AAPL_2026-02-16.json"

try:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    stmts = data.get('income_statements', [])
    print(f"Total Income Statements: {len(stmts)}")
    
    fy_count = 0
    ttm_count = 0
    other_count = 0
    
    print("-" * 40)
    for i, s in enumerate(stmts[:10]):
        ptype = s.get('std_period_type', 'Unknown')
        period = s.get('std_period', 'Unknown')
        rev = s.get('std_revenue', {})
        rev_val = rev.get('value') if isinstance(rev, dict) else rev
        
        print(f"[{i}] Period: {period} Type: {ptype} Revenue: {rev_val}")
        
        if ptype == 'FY': fy_count += 1
        elif ptype == 'TTM': ttm_count += 1
        else: other_count += 1
            
    print("-" * 40)
    print(f"FY: {fy_count}, TTM: {ttm_count}, Other: {other_count}")
    
except Exception as e:
    print(f"Error: {e}")

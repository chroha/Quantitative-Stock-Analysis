"""
Financial Scoring Runner
Run this script to interactively generate financial scores for a company.
"""

import sys
import os
from pathlib import Path

# Setup project root path
current_dir = os.path.dirname(os.path.abspath(__file__))
# .../fundamentals/financial_scorers
# We need to go up 2 levels
project_root = os.path.dirname(os.path.dirname(current_dir)) 

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fundamentals.financial_scorers.financial_scorers_output import FinancialScorerGenerator

def main():
    print("\n" + "="*80)
    print("  FINANCIAL SCORER GENERATOR")
    print("="*80)
    
    try:
        symbol = input("\nEnter stock symbol (e.g. AAPL): ").strip().upper()
        if not symbol:
            print("[ERROR] Symbol cannot be empty")
            return
            
        # By default FinancialScorerGenerator uses "generated_data" in CWD.
        # We might want to ensure it uses project's generated_data if run from anywhere.
        output_dir = os.path.join(project_root, "generated_data")
        
        generator = FinancialScorerGenerator(data_dir=output_dir)
        result = generator.generate(symbol)
        
        if result:
            print(f"[SUCCESS] Scoring complete: {result}")
        else:
            print("[FAILURE] Scoring failed. Check logs.")
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"\n[ERROR] An error occurred: {e}")

if __name__ == "__main__":
    main()

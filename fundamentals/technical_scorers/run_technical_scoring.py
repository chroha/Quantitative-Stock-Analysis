"""
Technical Scoring Runner
Run this script to interactively generate technical scores for a company.
"""

import sys
import os
from pathlib import Path

# Setup project root path
current_dir = os.path.dirname(os.path.abspath(__file__))
# .../fundamentals/technical_scorers
# We need to go up 2 levels
project_root = os.path.dirname(os.path.dirname(current_dir)) 

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fundamentals.technical_scorers.technical_scorers_output import TechnicalScorerGenerator

def main():
    print("\n" + "="*80)
    print("                               Technical Scorer Generator")
    print("="*80)
    
    try:
        symbol = input("\nEnter stock symbol (e.g. AAPL): ").strip().upper()
        if not symbol:
            print("[ERROR] Symbol cannot be empty")
            return
            
        # By default uses "generated_data" in CWD.
        output_dir = os.path.join(project_root, "generated_data")
        
        generator = TechnicalScorerGenerator(data_dir=output_dir)
        result = generator.generate(symbol)
        
        if result:
            # Success message already printed by generator
            pass
        else:
            print("[FAILURE] Scoring failed. Check logs.")
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"\n[ERROR] An error occurred: {e}")

if __name__ == "__main__":
    main()

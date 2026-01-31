"""
Data Audit Tool CLI
===================

Usage:
    python run_data_audit.py <SYMBOL>

Example:
    python run_data_audit.py TSM
    python run_data_audit.py AAPL
"""

import sys
import os
import argparse
from data_acquisition.audit.data_auditor import DataAuditor

def main():
    parser = argparse.ArgumentParser(description="Run Data Audit for a specific stock.")
    parser.add_argument("symbol", type=str, help="Stock ticker symbol (e.g. TSM)")
    parser.add_argument("--dir", type=str, default="debug_data", help="Output directory for debug data")
    
    args = parser.parse_args()
    
    symbol = args.symbol.upper()
    output_dir = args.dir
    
    print(f"Initializing Data Audit for {symbol}...")
    
    auditor = DataAuditor(symbol, output_dir)
    auditor.run_full_audit()

if __name__ == "__main__":
    main()

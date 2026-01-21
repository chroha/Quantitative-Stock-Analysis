"""
Quantitative Stock Analysis System - Stock Scanner
Batch analyzes stocks to find candidates with healthy Financial and Technical scores.
Skips Valuation and AI modules for speed.
Generated consolidated report sorted by Financial Score.
"""

import sys
import os
import argparse
import json
import logging
from datetime import datetime
import pandas as pd
from typing import Optional, Dict, Any, List

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# IMPORTANT: Set logging mode BEFORE importing modules that create loggers
from utils import LoggingContext, set_logging_mode
set_logging_mode(LoggingContext.SILENT)

# Now import modules (their loggers will respect SILENT mode)
from data_acquisition import StockDataLoader, BenchmarkDataLoader
from fundamentals.financial_scorers.financial_scorers_output import FinancialScorerGenerator
from fundamentals.technical_scorers.technical_scorers_output import TechnicalScorerGenerator
from fundamentals.financial_data.financial_data_output import FinancialDataGenerator
from utils import setup_logger
from utils.report_utils import (
    format_financial_score_report,
    format_technical_score_report
)

# Setup scanner logger
logger = setup_logger('run_scanner')




# ==============================================================================
# SCANNER LOGIC
# ==============================================================================

def analyze_stock(symbol, output_dir, force_update=True):
    """Run analysis for a single stock and return report data."""
    report_data = {
        'symbol': symbol,
        'fin_score': 0,
        'tech_score': 0,
        'report_text': ""
    }
    
    full_report_lines = []
    
    try:
        # STEP 1: Data Acquisition
        print(f"\nFetching data for {symbol}...")
        
        # NOTE: StockDataLoader has its own 'print' statements that we added earlier.
        # However, its logger output will be suppressed by our monkey patch.
        # This is exactly what we want: Keep explicit 'prints' but hide 'logs'.
        loader = StockDataLoader()
        
        # Check cache logic could be here, but usually scanning warrants fresh data
        # especially for technicals.
        stock_data = loader.get_stock_data(symbol)
        loader.save_stock_data(stock_data, output_dir)
            
        if not stock_data:
            print(f"[ERROR] Failed to load data for {symbol}")
            return None

        # Check API usage for rate limiting logic
        paid_api_used = stock_data.metadata.get('paid_api_used', False) if stock_data.metadata else False
        report_data['paid_api_used'] = paid_api_used

        print(f"  [OK] Data acquisition complete")

        # STEP 2: Financial Metric Calculation
        print(f"\n[2/4] Calculating Fundamental Metrics...")
        fin_data_gen = FinancialDataGenerator(data_dir=output_dir)
        fin_data_path = fin_data_gen.generate(symbol, quiet=True)
        
        if not fin_data_path:
            print("[ERROR] Failed metrics calculation (returns None)")
            return None

        # Print detailed metrics summary like run_analysis.py
        try:
            with open(fin_data_path, 'r', encoding='utf-8') as f:
                fd = json.load(f)
                pm = fd.get('metrics', {}).get('profitability', {})
                gm = fd.get('metrics', {}).get('growth', {})
                cm = fd.get('metrics', {}).get('capital_allocation', {})
                
                def fmt(val, is_pct=True):
                    if val is None: return "N/A"
                    return f"{val*100:.1f}%" if is_pct else f"{val:.2f}"
                
                # Special handling for buyback (negative dilution)
                dilution = cm.get('share_dilution_cagr_5y')
                
                print(f"  - ROIC: {fmt(pm.get('roic'))}")
                print(f"  - Rev Growth: {fmt(gm.get('revenue_cagr_5y'))}")
                print(f"  - FCF Growth: {fmt(gm.get('fcf_cagr_5y'))}")
                print(f"  - Dilution: {fmt(dilution)}")
                
        except Exception:
            pass

        # STEP 3: Financial Scoring
        print(f"\n[3/4] Calculating Financial Score...")
        # Silence logger for scorer
        scorer = FinancialScorerGenerator(data_dir=output_dir)
        fin_score_path = scorer.generate(symbol, quiet=True)
        
        fin_score_val = 0
        if fin_score_path:
             with open(fin_score_path, 'r', encoding='utf-8') as f:
                 sd_file = json.load(f)
                 sd = sd_file.get('score', {})
                 fin_score_val = sd.get('total_score', 0)
                 print(f"  [OK] Score: {fin_score_val} / 100")
        else:
             print("  [WARN] Financial scoring failed")
             sd = {}
             
        # STEP 4: Technical Scoring
        print(f"\n[4/4] Calculating Technical Score...")
        tech_scorer = TechnicalScorerGenerator(data_dir=output_dir)
        tech_score_path = tech_scorer.generate(symbol, quiet=True)
        
        tech_score_val = 0
        if tech_score_path:
             with open(tech_score_path, 'r', encoding='utf-8') as f:
                 td = json.load(f)
                 tech_score_val = td.get('score', {}).get('total_score', 0)
                 
                 # Append summary reports to consolidate text
                 fin_report = format_financial_score_report(sd)
                 tech_report = format_technical_score_report(td.get('score', {}))
                 
                 # Strip ANSI codes for file output
                 # ... existing logic ok ...
                 # Actually format_x_report returns strings with ANSI codes? 
                 # Let's assume report_utils handles separate raw text or strip it.
                 # For now, just append what we get.
                 
                 # Simple helpers to strip ANSI if needed, or assume report_utils returns clean text?
                 # Inspecting report_utils previously showed it returns colored text.
                 # The file might contain ANSI codes which is annoying but readable in `cat`.
                 # Ideally we strip them.
                 import re
                 ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                 
                 fin_report_text = ansi_escape.sub('', fin_report)
                 tech_report_text = ansi_escape.sub('', tech_report)
                 
                 full_report_lines.append(fin_report_text)
                 full_report_lines.append("-" * 40)
                 full_report_lines.append(tech_report_text)
             print(f"  [OK] Score: {tech_score_val} / 100")
        else:
             print("  [WARN] Technical scoring failed")

        report_data['fin_score'] = fin_score_val
        report_data['tech_score'] = tech_score_val
        
        # Prepare final consolidated text for this stock
        header = f"\n{'='*70}\nREPORT: {symbol}\n{'='*70}\n"
        report_data['report_text'] = header + "\n".join(full_report_lines)
        
        return report_data
            
    except Exception as e:
        import traceback
        print(f"[ERROR] Exception scanning {symbol}: {e}")
        # traceback.print_exc() # detailed trace if needed
        return None

def main():
    parser = argparse.ArgumentParser(description='Stock Scanner')
    parser.add_argument('symbols', nargs='*', help='Stock symbols to scan (space separated)')
    parser.add_argument('--list', '-l', help='Path to file containing symbols')
    args = parser.parse_args()
    
    symbols = []
    if args.symbols:
        symbols.extend([s.upper() for s in args.symbols])
    
    if args.list:
        if os.path.exists(args.list):
            with open(args.list, 'r') as f:
                symbols.extend([line.strip().upper() for line in f if line.strip()])
        else:
            print(f"List file not found: {args.list}")
            
    if not symbols:
        inp = input("Enter symbols to scan (e.g. AAPL NVDA MSFT): ").strip()
        if inp:
            # Support both comma and space separation
            # Replace commas with spaces, then split by whitespace
            symbols = [s.strip().upper() for s in inp.replace(',', ' ').split() if s.strip()]
    
    if not symbols:
        print("No symbols provided.")
        return
    
    # Remove duplicates
    symbols = list(set(symbols))

    print(f"\nScanning {len(symbols)} stocks...")
    print("-" * 60)
    
    output_dir = os.path.join(current_dir, "generated_data")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 0. Benchmark Data Check (Prevent crash)
    bench_loader = BenchmarkDataLoader()
    bench_path = bench_loader.get_output_path()
    if not bench_path.exists():
        print("[INFO] Missing Industry Benchmarks. Downloading...")
        bench_loader.run_update()
    else:
        # Prompt for update if benchmarks exist but user might want to refresh
        # Ask if running interactively (approximated by not being a list file run? or just always ask?)
        # User requested to be asked.
        if True: 
             choice = input("  Update industry benchmarks? (y/N): ").strip().lower()
             if choice == 'y':
                 print("  Downloading industry data files...")
                 bench_loader.run_update(force_refresh=True)
        
    # Rate limiting delay for batch scanning (to avoid API rate limits)
    # Alpha Vantage free tier: 5 requests/minute, so we need ~12s between stocks
    INTER_STOCK_DELAY = 12  # seconds between stocks
    
    results = []
    
    for i, symbol in enumerate(symbols):
        print(f"\n>>> Analyzing {symbol} ({i+1}/{len(symbols)}) <<<")
        res = analyze_stock(symbol, output_dir)
        if res:
            results.append(res)
        
        # Add delay between stocks to avoid API rate limits (skip for last stock)
        if len(symbols) > 1 and i < len(symbols) - 1:
            paid_api_used = False # Default to False (Optimistic)
            if res and 'paid_api_used' in res:
                paid_api_used = res['paid_api_used']
            
            if paid_api_used:
                import time
                print(f"\n  [WAIT] Waiting {INTER_STOCK_DELAY}s to avoid API rate limits...")
                time.sleep(INTER_STOCK_DELAY)
            else:
                print("\n  [FAST] Free data sources used, skipping delay.")
            
    print("\n" + "="*70)
    print("SCAN COMPLETE")
    print("="*70)
    
    if not results:
        print("No results generated.")
        return

    # Sort results by Financial Score Descending
    results.sort(key=lambda x: x['fin_score'], reverse=True)
    
    # 1. Print Summary List to Console
    print("\nSummary (Sorted by Financial Score):")
    print("-" * 60)
    for res in results:
        print(f"{res['symbol']:<6} : Financial Score - {res['fin_score']:>5.1f} / 100   Technical Score - {res['tech_score']:>3} / 100")
    print("-" * 60)
    
    # 2. Generate Consolidated Report File
    # Use timestamp to avoid overwriting files if multiple scans run per day
    timestamp_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    report_filename = f"stock_scan_{timestamp_str}.txt"
    
    # Save report to generated_reports/
    report_dir = os.path.join(current_dir, "generated_reports")
    if not os.path.exists(report_dir):
        os.makedirs(report_dir)
        
    report_path = os.path.join(report_dir, report_filename)
    
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"STOCK SCAN REPORT - {timestamp_str}\n")
            f.write(f"Generated at: {datetime.now().strftime('%H:%M:%S')}\n")
            f.write("="*70 + "\n\n")
            
            # Write Summary Table
            f.write("SUMMARY (Sorted by Financial Score)\n")
            f.write("-" * 60 + "\n")
            for res in results:
                f.write(f"{res['symbol']:<6} : Financial Score - {res['fin_score']:>5.1f} / 100   Technical Score - {res['tech_score']:>3} / 100\n")
            f.write("-" * 60 + "\n\n")
            
            # Write Detailed Reports
            for res in results:
                f.write(res['report_text'])
                f.write("\n\n")
                
        print(f"\nFull report saved to: {report_path}")
        
    except Exception as e:
        print(f"[ERROR] Failed to write report file: {e}")

if __name__ == "__main__":
    main()

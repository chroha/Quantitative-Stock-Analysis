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

# ==============================================================================
# LOGGING MONKEY PATCH
# Must be applied BEFORE importing modules that setup loggers
# ==============================================================================
import utils.logger

# Save original function
_original_setup_logger = utils.logger.setup_logger

def _silent_setup_logger(name: str, level: int = logging.INFO, log_file: Optional[str] = None) -> logging.Logger:
    """
    Monkey-patched logger setup to silence noisy modules during scanning.
    Intercepts logger creation and forces CRITICAL level for sub-modules.
    """
    # Whitelist: Loggers we WANT to see (or handle manually)
    whitelist = ['run_scanner']
    
    # Check if this logger is in whitelist
    if name not in whitelist:
        # Force silence for everything else (Fetchers, Calculators, Validators, etc.)
        level = logging.CRITICAL
        
    return _original_setup_logger(name, level, log_file)

# Apply patch
utils.logger.setup_logger = _silent_setup_logger

from data_acquisition import StockDataLoader
from fundamentals.financial_scorers.financial_scorers_output import FinancialScorerGenerator
from fundamentals.technical_scorers.technical_scorers_output import TechnicalScorerGenerator
from fundamentals.financial_data.financial_data_output import FinancialDataGenerator

# Setup scanner logger (this will pass the filter as it's whitelisted)
logger = utils.logger.setup_logger('run_scanner')


# ==============================================================================
# REPORT FORMATTERS (Copied from run_analysis.py for consistency)
# ==============================================================================

def format_financial_score_report(score_data):
    """Format financial score as a clean report string."""
    if not score_data:
        return None
    
    lines = []
    lines.append("-" * 70)
    lines.append("FINANCIAL SCORE REPORT")
    lines.append("-" * 70)
    
    # Check for data warnings
    if 'data_warnings' in score_data:
        for w in score_data['data_warnings']:
             lines.append(f"[NOTE] {w} - Score reliability reduced.")
        lines.append("-" * 70)

    lines.append(f"Total Score: {score_data.get('total_score', 0):.1f} / 100")
    lines.append("")
    
    cats = score_data.get('category_scores', {})
    for cat_name, cat_data in cats.items():
        name = cat_name.replace('_', ' ').title()
        score = cat_data.get('score', 0)
        
        # Calculate actual max score based on active weights
        actual_max = 0
        if 'metrics' in cat_data:
            for metric, details in cat_data['metrics'].items():
                if not details.get('disabled', False):
                    actual_max += details.get('weight', 0)
        
        # Use actual max if calculated, otherwise use the stored max
        display_max = actual_max if actual_max > 0 else cat_data.get('max', 0)
        
        # Cap displayed score to max (handle sector weight overrides)
        display_score = min(score, display_max) if display_max > 0 else score
        
        lines.append(f"  {name:<20} : {display_score:>5.1f} / {display_max}")
        
        # Metrics detail
        if 'metrics' in cat_data:
            for metric, details in cat_data['metrics'].items():
                val = details.get('value')
                
                # Format value
                if isinstance(val, float):
                    if abs(val) < 1:
                        val_str = f"{val:.2%}"
                    else:
                        val_str = f"{val:.2f}"
                else:
                    val_str = str(val) if val is not None else "N/A"
                
                # Check if disabled
                if details.get('disabled', False):
                    note = details.get('note', 'Not used for this sector')
                    lines.append(f"      - {metric:<24}: {val_str:>10} ({note})")
                    continue
                
                weighted = details.get('weighted_score', 0)
                weight = details.get('weight', 0)
                lines.append(f"      - {metric:<24}: {val_str:>10} (Score: {weighted} / {weight})")
    
    lines.append("-" * 70)
    return "\n".join(lines)


def format_technical_score_report(score_data):
    """Format technical score as a clean report string."""
    if not score_data:
        return None
    
    lines = []
    lines.append("-" * 70)
    lines.append("TECHNICAL SCORE REPORT")
    lines.append("-" * 70)
    total = score_data.get('total_score', 0)
    max_score = score_data.get('max_score', 100)
    lines.append(f"Total Score: {total} / {max_score}")
    lines.append("")
    
    cats = score_data.get('categories', {})
    for cat_name, cat_data in cats.items():
        name = cat_name.replace('_', ' ').title()
        earned = cat_data.get('earned_points', 0)
        max_pts = cat_data.get('max_points', 0)
        lines.append(f"  {name:<20} : {earned:>5} / {max_pts}")
        
        # Indicators detail
        if 'indicators' in cat_data:
            for ind, details in cat_data['indicators'].items():
                score = details.get('score', 0)
                max_ind = details.get('max_score', 0)
                signal = details.get('explanation', details.get('signal', ''))
                
                # Find the primary value - try common key patterns
                val = None
                for key in [ind, 'value', 'rsi', 'macd', 'adx', 'atr', 'roc', 'obv', 
                           'current_price', 'position', 'bandwidth', 'volume_ratio']:
                    if key in details and key != 'score' and key != 'max_score':
                        candidate = details.get(key)
                        if isinstance(candidate, (int, float)) and val is None:
                            val = candidate
                            break
                
                if isinstance(val, float):
                    val_str = f"{val:.2f}"
                elif val is not None:
                    val_str = str(val)
                else:
                    val_str = f"{score}/{max_ind}"
                
                # Truncate long signals
                if len(signal) > 50:
                    signal = signal[:47] + "..."
                lines.append(f"      - {ind:<20}: {val_str:>10} ({signal})")
    
    lines.append("-" * 70)
    return "\n".join(lines)

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

        print(f"  ✓ Data acquisition complete")

        # STEP 2: Financial Metric Calculation
        print(f"\n[2/4] Calculating Fundamental Metrics...")
        fin_data_gen = FinancialDataGenerator(data_dir=output_dir)
        fin_data_path = fin_data_gen.generate(symbol, quiet=True)
        
        if not fin_data_path:
            print("[ERROR] Failed metrics calculation")
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
                if dilution is not None and dilution < 0:
                    buyback_str = f"Buyback {abs(dilution)*100:.1f}%"
                else:
                    buyback_str = f"Dilution {fmt(dilution)}"

                print(f"  ✓ Profitability: ROIC {fmt(pm.get('roic'))} | ROE {fmt(pm.get('roe'))} | Net Margin {fmt(pm.get('net_margin'))}")
                print(f"  ✓ Growth: Revenue {fmt(gm.get('revenue_cagr_5y'))} | Net Income {fmt(gm.get('net_income_cagr_5y'))} | FCF {fmt(gm.get('fcf_cagr_5y'))}")
                print(f"  ✓ Capital: {buyback_str} | Capex {fmt(cm.get('capex_intensity_3y'))} | D/E {fmt(cm.get('debt_to_equity'), False)}")
        except Exception:
            print("  ✓ Financial metrics generated")

        # STEP 3: Financial Scoring
        print(f"\n[3/4] Financial Scoring...")
        fin_gen = FinancialScorerGenerator(data_dir=output_dir)
        fin_score_path = fin_gen.generate(symbol, quiet=True)
        
        fin_score_val = 0
        if fin_score_path:
             with open(fin_score_path, 'r', encoding='utf-8') as f:
                 data = json.load(f)
                 fin_score_val = data.get('score', {}).get('total_score', 0)
                 # Buffer detailed report
                 fin_report_text = format_financial_score_report(data.get('score', {}))
                 if fin_report_text:
                     full_report_lines.append(fin_report_text)
                 
                 # Print warning if exists
                 warnings = data.get('score', {}).get('data_warnings', [])
                 if warnings:
                     print(f"  [!] {warnings[0]}")
             print(f"  ✓ Score: {fin_score_val:.1f} / 100")
        else:
             print("  [WARN] Financial scoring failed")

        # STEP 4: Technical Scoring
        print(f"\n[4/4] Technical Scoring...")
        tech_gen = TechnicalScorerGenerator(data_dir=output_dir)
        tech_score_path = tech_gen.generate(symbol, quiet=True)
        
        tech_score_val = 0
        if tech_score_path:
             with open(tech_score_path, 'r', encoding='utf-8') as f:
                 data = json.load(f)
                 tech_score_val = data.get('score', {}).get('total_score', 0)
                 max_s = data.get('score', {}).get('max_score', 100)
                 # Buffer detailed report
                 full_report_lines.append("")
                 tech_report_text = format_technical_score_report(data.get('score', {}))
                 if tech_report_text:
                     full_report_lines.append(tech_report_text)
             print(f"  ✓ Score: {tech_score_val} / {max_s}")
        else:
             print("  [WARN] Technical scoring failed")

        report_data['fin_score'] = fin_score_val
        report_data['tech_score'] = tech_score_val
        
        # Prepare final consolidated text for this stock
        header = f"\n{'='*70}\nREPORT: {symbol}\n{'='*70}\n"
        report_data['report_text'] = header + "\n".join(full_report_lines)
        
        return report_data
            
    except Exception as e:
        logger.error(f"Error scanning {symbol}: {e}")
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
            import time
            print(f"\n  ⏳ Waiting {INTER_STOCK_DELAY}s to avoid API rate limits...")
            time.sleep(INTER_STOCK_DELAY)
            
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

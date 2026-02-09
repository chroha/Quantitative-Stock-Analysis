
"""
Pipeline Orchestrator for Quantitative Stock Analysis.
Executes the full analysis workflow:
1. Clean Cache
2. Update Benchmarks
3. Analyze Stocks (Batch)
4. Generate Summary Report
5. Run Macro Analysis
"""

import os
import sys
import shutil
import subprocess
import logging
from pathlib import Path
from typing import List

# Setup project root
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from datetime import datetime
from config.constants import DATA_CACHE_STOCK, DATA_CACHE_MACRO, DATA_CACHE_BENCHMARK, DATA_REPORTS
from data_acquisition.benchmark_data.benchmark_data_loader import BenchmarkDataLoader
from utils.console_utils import symbol as ICON, print_step, print_separator

# Configure simple logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger('pipeline')

def print_header(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def clean_cache():
    """Cleans data/cache directories, preserving benchmark CSVs."""
    print_step(1, 5, "Cleaning Data Cache")
    
    # Paths
    cache_dirs = [
        os.path.join(current_dir, DATA_CACHE_STOCK),
        os.path.join(current_dir, DATA_CACHE_MACRO)
    ]
    
    # Clean Stock and Macro entirely
    for d in cache_dirs:
        display_name = os.path.basename(d)
        if os.path.exists(d):
            print(f"  Cleaning {display_name}...")
            for filename in os.listdir(d):
                file_path = os.path.join(d, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f"    [WARN] Failed to delete {filename}: {e}")
            print(f"  {ICON.OK} Cleaned {display_name}")
    
    # Clean Benchmark (preserve CSVs)
    bench_dir = os.path.join(current_dir, DATA_CACHE_BENCHMARK)
    if os.path.exists(bench_dir):
        deleted_count = 0
        for filename in os.listdir(bench_dir):
            file_path = os.path.join(bench_dir, filename)
            # Delete if it's NOT a CSV and is a file (e.g. JSON)
            if os.path.isfile(file_path) and not filename.lower().endswith('.csv'):
                try:
                    os.unlink(file_path)
                    deleted_count += 1
                except Exception as e:
                    print(f"  {ICON.WARN} Failed to delete {filename}: {e}")
        
        if deleted_count > 0:
            print(f"  {ICON.OK} Cleaned benchmark cache (preserved CSVs)")
        else:
             print(f"  {ICON.OK} Benchmark cache already clean")

def update_benchmarks():
    """Updates industry benchmarks."""
    print_step(2, 5, "Industry Benchmarks")
    
    loader = BenchmarkDataLoader()
    json_path = loader.get_output_path()
    
    # Interaction
    choice = input("  Update industry benchmarks? (y/N): ").strip().lower()
    force_refresh = (choice == 'y')
    
    print("  Processing benchmarks...")
    result = loader.run_update(force_refresh=force_refresh)
    
    if result:
        print(f"  {ICON.OK} Benchmarks ready")
    else:
        print(f"  {ICON.FAIL} Benchmark update failed")
        sys.exit(1)

def run_stock_analysis(symbols: List[str]):
    """Runs run_analysis.py for each symbol."""
    print_step(3, 5, "Stock Analysis Batch")
    
    for i, symbol in enumerate(symbols):
        print(f"\n  --- Analyzing {symbol} ({i+1}/{len(symbols)}) ---")
        try:
            # We call run_analysis.py as a subprocess.
            # Passing the symbol ensures it runs in non-interactive mode where appropriate (or we rely on its args)
            # Note: The user said "run_analysis.py logic defaults to generating AI reports when arguments are provided"
            cmd = [sys.executable, "run_analysis.py", symbol]
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"  {ICON.FAIL} Analysis failed for {symbol}")
        except Exception as e:
            print(f"  {ICON.FAIL} Error executing analysis for {symbol}: {e}")

def run_summary(symbols: List[str]):
    """Runs run_getform.py to generate summary CSV."""
    print_step(4, 5, "Generating Summary Report")
    
    try:
        cmd = [sys.executable, "run_getform.py"] + symbols
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        print(f"  {ICON.FAIL} Summary generation failed")

def run_macro():
    """Runs run_macro_report.py."""
    print_step(5, 5, "Macro Analysis")
    
    # Check if report for today already exists
    today_str = datetime.now().strftime("%Y-%m-%d")
    report_filename = f"macro_report_{today_str}.md"
    report_path = os.path.join(current_dir, DATA_REPORTS, report_filename)
    
    if os.path.exists(report_path):
        print(f"  {ICON.INFO} Macro report for today found: {report_filename}")
        # Default Y means "Skip"
        choice = input(f"  Skip macro analysis? (Y/n): ").strip().lower()
        if choice != 'n':
            print(f"  {ICON.OK} Skipped macro analysis.")
            return

    try:
        # This will be interactive for Forward PE input
        cmd = [sys.executable, "run_macro_report.py"]
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        print(f"  {ICON.FAIL} Macro analysis failed")

def main():
    print_header("AUTOMATED STOCK ANALYSIS PIPELINE")
    
    # 1. Get Inputs
    if len(sys.argv) > 1:
        symbols = [s.strip().upper() for s in sys.argv[1:]]
    else:
        inp = input("Enter stock symbols (e.g. AAPL GOOGL NVDA): ").strip()
        if not inp:
            print("No symbols provided.")
            return
        symbols = [s.strip().upper() for s in inp.replace(',', ' ').split() if s.strip()]
    
    print(f"\n  Pipeline targets: {', '.join(symbols)}")
    print("  Starting execution...")
    
    # 2. Pipeline Execution
    try:
        clean_cache()
        update_benchmarks()
        run_stock_analysis(symbols)
        run_summary(symbols)
        run_macro()
        
        print_separator()
        print(f"  {ICON.OK} PIPELINE EXECUTION COMPLETE")
        print_separator()
        
    except KeyboardInterrupt:
        print("\n[!] Pipeline cancelled by user.")
    except Exception as e:
        print(f"\n[ERROR] Pipeline failed: {e}")

if __name__ == "__main__":
    main()

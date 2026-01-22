"""
Macro Strategy Report Orchestrator (System V3.0)
宏观策略报告生成主程序
"""

import sys
import os
import json
import shutil
import argparse
from datetime import datetime
from pathlib import Path

# IMPORTANT: Set logging mode BEFORE importing modules
from utils import LoggingContext, set_logging_mode
set_logging_mode(LoggingContext.ORCHESTRATED)

from data_acquisition.macro_data.macro_aggregator import MacroAggregator
from fundamentals.macro_indicator.macro_report import MacroReportGenerator
from fundamentals.macro_indicator.macro_markdown_report import MacroMarkdownGenerator
from utils.logger import setup_logger
from utils.console_utils import symbol as ICON, print_step, print_separator

logger = setup_logger('run_macro_report')

def print_header(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        import re
        print(re.sub(r'[^\x00-\x7F]+', '', text))

def main():
    print_header("MACRO STRATEGY ANALYSIS SYSTEM")
    
    # Paths
    current_dir = Path(__file__).parent.absolute()
    data_dir = current_dir / 'data_acquisition' / 'macro_data' / 'data'
    json_path = data_dir / 'macro_latest.json'
    cache_dir = data_dir / '.cache'
    reports_dir = current_dir / 'generated_reports'
    
    # Check existing data
    existing_data = None
    if json_path.exists():
        try:
            with open(json_path, 'r') as f:
                existing_data = json.load(f)
        except Exception:
            pass
            
    # Interactive Flow
    should_fetch = True
    force_refresh = False
    
    if existing_data:
        ts = existing_data.get('snapshot_date', 'Unknown')
        try:
            # Parse ISO timestamp for cleaner display
            dt = datetime.fromisoformat(ts)
            ts_display = dt.strftime("%Y-%m-%d %H:%M")
        except:
            ts_display = ts
            
        print(f"\n  {ICON.OK} Found existing macro data (Snapshot: {ts_display})")
        print("  [1] Use existing data (Generate Report Only)")
        print("  [2] Refresh data (Smart Update - use cache if valid)")
        print("  [3] Force Refresh (Clear cache + Fresh Fetch)")
        
        choice = input("\n  Select option [1]: ").strip() or "1"
        
        if choice == "1":
            should_fetch = False
        elif choice == "3":
            force_refresh = True
            print(f"\n  {ICON.WARN} Clearing cache for fresh fetch...")
            if cache_dir.exists():
                shutil.rmtree(cache_dir, ignore_errors=True)
                cache_dir.mkdir(exist_ok=True)
    
    # Step 1: Data Acquisition
    if should_fetch:
        print_step(1, 2, "Fetching Macro Data")
        try:
            # Pass 'input' function to enable interactive prompting for missing data
            aggregator = MacroAggregator(interactive_input_func=input) 
            snapshot = aggregator.run()
            
            # Check status
            status = snapshot['data_quality']['overall_status']
            if status == 'ok':
                print(f"  {ICON.OK} Data fetch successful")
            elif status == 'degraded':
                 print(f"  {ICON.WARN} Data fetch completed with warnings")
            else:
                 print(f"  {ICON.FAIL} Data fetch failed")
                 return
                 
            existing_data = snapshot # Update current data
            
        except Exception as e:
            logger.error(f"Fetch failed: {e}")
            print(f"  {ICON.FAIL} Critical error during data fetch: {e}")
            return
    else:
        print_step(1, 2, "Loading Data")
        print(f"  {ICON.OK} Loaded local snapshot")

    # Step 2: Report Generation
    print_step(2, 2, "Generating Analysis Report")
    
    if not existing_data:
        print(f"  {ICON.FAIL} No data available to generate report.")
        return

    try:
        # 1. Console Report (Concise / English)
        console_gen = MacroReportGenerator()
        console_text = console_gen.generate_report(existing_data)
        
        print("\n" + "="*60)
        safe_print(console_text)
        print("="*60)
        
        # 2. Markdown Report (Bilingual / Detailed)
        md_gen = MacroMarkdownGenerator()
        md_text = md_gen.generate_markdown(existing_data)
        
        # Determine filename
        ts = existing_data.get('snapshot_date', datetime.now().isoformat())
        try:
            dt = datetime.fromisoformat(ts)
            date_str = dt.strftime("%Y-%m-%d")
        except:
            date_str = "unknown_date"
            
        if not reports_dir.exists():
            reports_dir.mkdir(parents=True)
            
        report_file = reports_dir / f"macro_report_{date_str}.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(md_text)
            
        print(f"\n  {ICON.OK} Detailed report saved: {report_file}")
        
    except Exception as e:
        logger.error(f"Report generation failed: {e}", exc_info=True)
        print(f"  {ICON.FAIL} Report output failed: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Operation cancelled.")
    except Exception as e:
        print(f"\n[ERROR] Unexpected system error: {e}")

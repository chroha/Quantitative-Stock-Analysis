"""
Macro Strategy Report Orchestrator (System V3.0)
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
# Analyzers
from fundamentals.reporting.report_assembler import ReportAssembler
from fundamentals.macro_indicator.cycle_analyzer import CycleAnalyzer
from fundamentals.macro_indicator.risk_assessor import RiskAssessor
from fundamentals.macro_indicator.valuation_allocator import ValuationAllocator
# Reporters
from fundamentals.macro_indicator.macro_report import MacroReportGenerator
from fundamentals.macro_indicator.macro_markdown_report import MacroMarkdownReport
from fundamentals.macro_indicator.macro_ai_analyst import MacroAIAnalyst
from data_acquisition.stock_data.finnhub_fetcher import FinnhubFetcher
from config.constants import DATA_CACHE_MACRO, DATA_REPORTS
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
    
    # Paths (using unified constants)
    current_dir = Path(__file__).parent.absolute()
    data_dir = current_dir / DATA_CACHE_MACRO
    json_path = data_dir / 'macro_latest.json'
    cache_dir = data_dir / '.cache'
    reports_dir = current_dir / DATA_REPORTS
    
    # Check existing data
    existing_data = None
    if json_path.exists():
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        except Exception:
            pass
            
    # Interactive Flow
    should_fetch = True
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    if existing_data:
        ts = existing_data.get('snapshot_date', 'Unknown')
        data_date = ts[:10]  # First 10 chars for YYYY-MM-DD
        
        try:
            dt = datetime.fromisoformat(ts)
            ts_display = dt.strftime("%H:%M")
        except:
            ts_display = ts

        if data_date == today_str:
            print(f"\n  {ICON.OK} Found macro data for TODAY ({ts_display})")
            user_input = input(f"  Refresh data? [y/N]: ").strip().lower()
            if user_input != 'y':
                should_fetch = False
                print(f"  > Using existing data.")
            else:
                print(f"  > Refreshing data...")
        else:
            print(f"\n  {ICON.INFO} Existing data is from {data_date}. Fetching new data for today...")
    else:
        print(f"\n  {ICON.INFO} No local data found. Starting fresh fetch...")
    
    # Step 1: Data Acquisition
    macro_data = existing_data
    
    if should_fetch:
        print_step(1, 4, "Fetching Macro Data")
        try:
            # Pass 'input' function to enable interactive prompting for missing data
            aggregator = MacroAggregator(interactive_input_func=input) 
            macro_data = aggregator.run()
            
            # Check status
            status = macro_data['data_quality']['overall_status']
            if status == 'ok':
                print(f"  {ICON.OK} Data fetch successful")
                # Show summary
                summary = aggregator.get_summary(macro_data)
                print("\n" + "\n".join(["  " + line for line in summary.split('\n')]))
                
            elif status == 'degraded':
                 print(f"  {ICON.WARN} Data fetch completed with warnings")
            else:
                 print(f"  {ICON.FAIL} Data fetch failed")
                 return
                 
        except Exception as e:
            logger.error(f"Fetch failed: {e}")
            print(f"  {ICON.FAIL} Critical error during data fetch: {e}")
            return
    else:
        print_step(1, 4, "Loading Data")
        print(f"  {ICON.OK} Loaded local snapshot")

    if not macro_data:
        print(f"  {ICON.FAIL} No data available to generate report.")
        return

    # Step 2: Analysis Algorithms
    print_step(2, 4, "Running Analysis Models")
    try:
        # Initialize Analyzers
        cycle_analyzer = CycleAnalyzer()
        risk_assessor = RiskAssessor()
        valuation_allocator = ValuationAllocator()
        
        # Run Analysis
        analysis_results = {
            'cycle': cycle_analyzer.analyze(macro_data),
            'risk': risk_assessor.analyze(macro_data),
            'valuation': valuation_allocator.analyze(macro_data)
        }
        
        # Use 'phase' for cycle, and 'equity_bond_allocation' for valuation
        print(f"  {ICON.OK} Business Cycle Analyzed: {analysis_results['cycle'].get('phase', 'Unknown')}")
        print(f"  {ICON.OK} Risk Environment Assessed: {analysis_results['risk'].get('environment', 'Unknown')}")
        print(f"  {ICON.OK} Valuation Model Run: {analysis_results['valuation'].get('equity_bond_allocation', 'Unknown')}")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        print(f"  {ICON.FAIL} Analysis modules failed: {e}")
        return

    print_step(3, 4, "Fetching Market News")
    market_news = {}
    try:
        fh = FinnhubFetcher("MARKET")
        print("  > Fetching General Market News...")
        market_news['general'] = fh.fetch_market_news('general')
        
        print("  > Fetching Forex News...")
        market_news['forex'] = fh.fetch_market_news('forex')
        
        print("  > Fetching Crypto News...")
        market_news['crypto'] = fh.fetch_market_news('crypto')
        
        print(f"  {ICON.OK} Market News fetched ({len(market_news['general'])} general, {len(market_news['forex'])} forex, {len(market_news['crypto'])} crypto)")
        
        # Attach to macro_data for report generation
        macro_data['market_news'] = market_news
        
    except Exception as e:
        logger.warning(f"Market News Fetch Failed: {e}")
        print(f"  {ICON.WARN} Market News Fetch Failed: {e}")


    print_step(4, 4, "Generating Reports")
    
    # AI Commentary Generation
    ai_commentary = None
    ai_analyst = None
    try:
        print(f"  > Generating AI Strategic Commentary (Bilingual)...")
        ai_analyst = MacroAIAnalyst()
        ai_commentary = ai_analyst.generate_commentary(macro_data, analysis_results)
        print(f"  {ICON.OK} AI Commentary generated.")
    except Exception as e:
        logger.error(f"AI Generation failed: {e}")
        print(f"  {ICON.WARN} AI Commentary failed: {e}")
    
    try:
        # Markdown Dashboard (Bilingual / Detailed)
        md_gen = MacroMarkdownReport(output_dir=reports_dir)
        md_text = md_gen.generate_report(macro_data, analysis_results, ai_commentary)
        
        # Assemble with Disclaimer
        md_text = ReportAssembler.assemble_macro_report(md_text)
        
        # Determine filename
        ts = macro_data.get('snapshot_date', datetime.now().isoformat())
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
            
        print(f"\n  {ICON.OK} Dashboard generated: {report_file}")
        
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

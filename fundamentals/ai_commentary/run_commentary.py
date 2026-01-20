"""
AI Commentary Runner
Run this script to generate an AI-powered investment commentary.
"""

import sys
import os
import argparse
from pathlib import Path
from datetime import datetime

# Setup project root path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fundamentals.ai_commentary.data_aggregator import DataAggregator
from fundamentals.ai_commentary.commentary_generator import CommentaryGenerator
from utils.logger import setup_logger

logger = setup_logger('run_commentary')

def main():
    # Ensure UTF-8 output for Windows console
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass

    print("\n" + "="*60)
    print("🤖 AI Investment Commentary Generator")
    print("="*60)
    
    try:
        # Get ticker from user
        if len(sys.argv) > 1:
            symbol = sys.argv[1]
        else:
            symbol = input("Enter stock symbol (e.g., AAPL): ").strip().upper()
            
        if not symbol:
            print("Operation cancelled.")
            return

        output_dir = os.path.join(project_root, "generated_data")
        
        # Step 1: Aggregate Data
        print(f"\nStep 1: Aggregating data for {symbol}...")
        aggregator = DataAggregator(data_dir=output_dir)
        aggregated_data = aggregator.aggregate(symbol)
        
        if not aggregated_data:
            print(f"[ERROR] Missing scoring data for {symbol}.")
            print("Please run financial_scoring, technical_scoring, and valuation first.")
            return
            
        print(f"  [OK] Data aggregated successfully.")
        
        # Step 2: Generate Commentary
        print(f"\nStep 2: Generating analysis with Google AI...")
        generator = CommentaryGenerator()
        report = generator.generate_report(aggregated_data)
        
        if not report:
            print(f"[ERROR] Failed to generate report. Check API key and logs.")
            return
        
        # Step 2.5: Generate raw data appendix
        print(f"   Generating data appendix...")
        appendix = aggregator.get_raw_data_appendix(symbol)
        if appendix:
            report = report + appendix
            
        # Step 3: Save Report
        date_str = aggregated_data['stock_info']['date']
        report_filename = f"ai_analysis_{symbol}_{date_str}.md"
        
        # Save to generated_reports
        report_dir = os.path.join(project_root, "generated_reports")
        if not os.path.exists(report_dir):
            os.makedirs(report_dir)
            
        report_path = os.path.join(report_dir, report_filename)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
            
        print(f"\n[SUCCESS] Report generated ({len(report)} chars):")
        print(f"  {report_path}")
        print("="*60)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        logger.exception("Runtime error")
        print(f"\n[ERROR] An error occurred: {e}")

if __name__ == "__main__":
    main()

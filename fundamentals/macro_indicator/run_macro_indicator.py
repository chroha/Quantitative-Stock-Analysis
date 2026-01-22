"""
Run Macro Indicator Analysis - CLI entry point for generating macro reports
运行宏观指标分析 - 生成分析报告
"""

import sys
import json
import argparse
from pathlib import Path

# Add project root to path to import utils and modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fundamentals.macro_indicator.macro_report import MacroReportGenerator
from utils.logger import setup_logger
from utils.console_utils import symbol

logger = setup_logger('run_macro_indicator')

def safe_print(text: str):
    """Safely print text handling unicode/emoji."""
    try:
        print(text)
    except UnicodeEncodeError:
        import re
        ascii_text = re.sub(r'[^\x00-\x7F]+', '', text)
        print(ascii_text)

def main():
    """Main entry for macro indicator reporting."""
    parser = argparse.ArgumentParser(description="Generate macro analysis report from fetched data.")
    parser.add_argument("--data", type=str, help="Path to macro_latest.json (optional)")
    args = parser.parse_args()
    
    logger.info("Starting macro indicator analysis...")
    
    try:
        # Determine data path
        if args.data:
            data_path = Path(args.data)
        else:
            # Default location: data_acquisition/macro_data/data/macro_latest.json
            project_root = Path(__file__).parent.parent.parent
            data_path = project_root / 'data_acquisition' / 'macro_data' / 'data' / 'macro_latest.json'
            
        logger.info(f"Loading data from: {data_path}")
        
        if not data_path.exists():
            logger.error(f"{symbol.FAIL} Data file not found: {data_path}")
            print(f"\nError: Data file not found. Please run data fetcher first:")
            print(f"python data_acquisition/macro_data/run_macro_fetch.py")
            return 1
            
        # Load Data
        with open(data_path, 'r') as f:
            snapshot = json.load(f)
            
        # Generate Report
        report_gen = MacroReportGenerator()
        report_text = report_gen.generate_report(snapshot)
        
        safe_print("\n" + report_text + "\n")
        logger.info(f"{symbol.OK} Report generation complete")
        return 0
        
    except Exception as e:
        logger.error(f"Fatal error during report generation: {e}", exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(main())

"""
Report Auditor Tool
===================
Consolidated tool for verifying output generation.
Replaces:
- run_debug_commentary.py
- run_debug_summary.py
"""

import sys
import os
import argparse
from pathlib import Path

# Ensure project root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.constants import DATA_CACHE_STOCK, DATA_REPORTS
from utils.logger import setup_logger
from utils.console_utils import print_header, symbol as console_symbol

# Import Generators
from fundamentals.ai_commentary.data_aggregator import DataAggregator
from fundamentals.ai_commentary.report_generator import ReportGenerator
# Assume Logic for Summary (if different) is inside ReportGenerator or similar

logger = setup_logger("report_auditor")

class ReportAuditor:
    def __init__(self):
        self.stock_dir = os.path.join(project_root, DATA_CACHE_STOCK)
        self.report_dir = os.path.join(project_root, DATA_REPORTS)
        
    def run_commentary_audit(self, symbol: str):
        """Run AI Commentary Generation."""
        print(f"\n--- Running AI Commentary Audit ({symbol}) ---")
        try:
            # 1. Aggregate Data
            print(f"  Aggregating data...")
            # Note: This assumes data already exists (run Model Auditor first if not)
            aggregator = DataAggregator(self.stock_dir)
            context = aggregator.aggregate(symbol)
            
            if not context:
                print(f"{console_symbol.FAIL} Failed to aggregate data. Run Model Auditor first?")
                return

            print(f"  {console_symbol.OK} Data Context Built.")
            

            
            # 2. Generate Commentary (Mock or Real)
            print(f"  Generating commentary...")
            generator = ReportGenerator()
            report_content = generator.generate_stock_report(context)
            
            # 3. Append Data Appendix
            print(f"  Generating data appendix...")
            appendix = aggregator.get_raw_data_appendix(symbol)
            if appendix:
                report_content += "\n\n" + appendix

            if report_content:
                # Save report manually
                from datetime import datetime
                today = datetime.now().strftime("%Y-%m-%d")
                filename = f"AUDIT_ai_analysis_{symbol}_{today}.md"
                report_path = os.path.join(self.report_dir, filename)
                
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(report_content)
                    
                print(f"{console_symbol.OK} Commentary Saved: {os.path.basename(report_path)}")
            else:
                 print(f"{console_symbol.FAIL} Commentary Generation Failed.")
                 
        except Exception as e:
            logger.error(f"Commentary Audit Error: {e}")
            print(f"{console_symbol.FAIL} Error: {e}")
            import traceback
            traceback.print_exc()

    def run_data_audit(self, symbol: str):
        """Run Data & Prompt Audit (No AI)."""
        print(f"\n--- Running Data & Prompt Audit (No AI) ({symbol}) ---")
        try:
            # 1. Aggregate Data
            print(f"  Aggregating data...")
            aggregator = DataAggregator(self.stock_dir)
            context = aggregator.aggregate(symbol)
            
            if not context:
                print(f"{console_symbol.FAIL} Failed to aggregate data.")
                return

            print(f"  {console_symbol.OK} Data Context Built.")

            # 2. Build Prompt (The "Input" to AI)
            print(f"  Building Prompt Template...")
            from fundamentals.ai_commentary.prompts import build_analysis_prompt
            prompt_content = build_analysis_prompt(context)
            
            # 3. Append Data Appendix (The "Raw Data")
            print(f"  Generating data appendix...")
            appendix = aggregator.get_raw_data_appendix(symbol)
            
            # Combine
            from datetime import datetime
            today_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            full_content = "# AUDIT REPORT: PROMPT + RAW DATA (NO AI GENERATION)\n"
            full_content += f"# Symbol: {symbol}\n"
            full_content += f"# Generated: {today_ts}\n\n"
            full_content += "--- START OF PROMPT SENT TO AI ---\n"
            full_content += prompt_content
            full_content += "\n--- END OF PROMPT ---\n\n"
            
            if appendix:
                 full_content += "--- RAW DATA APPENDIX (PYTHON GENERATED) ---\n"
                 full_content += appendix

            # Save
            from datetime import datetime
            today = datetime.now().strftime("%Y-%m-%d")
            filename = f"AUDIT_PROMPT_DATA_{symbol}_{today}.md"
            report_path = os.path.join(self.report_dir, filename)
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(full_content)
                
            print(f"{console_symbol.OK} Data Audit Saved: {os.path.basename(report_path)}")
                
        except Exception as e:
            logger.error(f"Data Audit Error: {e}")
            print(f"{console_symbol.FAIL} Error: {e}")
            import traceback
            traceback.print_exc()


    def run_macro_report_audit(self):
        """Run Macro Strategy Report Generation."""
        print(f"\n--- Running Macro Strategy Report Audit ---")
        try:
            from data_acquisition.macro_data.macro_aggregator import MacroAggregator
            from fundamentals.macro_indicator.cycle_analyzer import CycleAnalyzer
            from fundamentals.macro_indicator.risk_assessor import RiskAssessor
            from fundamentals.macro_indicator.valuation_allocator import ValuationAllocator
            from fundamentals.macro_indicator.macro_report import MacroReportGenerator
            from fundamentals.macro_indicator.macro_markdown_report import MacroMarkdownReport
            from fundamentals.macro_indicator.macro_ai_analyst import MacroAIAnalyst
            
            # 1. Fetch/Load Data
            print("  [1/4] Loading Macro Data...")
            # Interactive fetch allowed
            aggregator = MacroAggregator(interactive_input_func=input)
            # Try to just load existing if possible, or fetch if missing
            # For audit purposes, let's just trigger a run which handles loading/fetching
            macro_data = aggregator.run()
            
            if not macro_data:
                print(f"{console_symbol.FAIL} No macro data available.")
                return

            # 2. Run Analysis
            print("  [2/4] Running Analysis Models (Cycle, Risk, Valuation)...")
            analysis_results = {
                'cycle': CycleAnalyzer().analyze(macro_data),
                'risk': RiskAssessor().analyze(macro_data),
                'valuation': ValuationAllocator().analyze(macro_data)
            }
            print(f"  {console_symbol.OK} Analysis Complete.")

            # 3. Generate AI Commentary
            print("  [3/4] Generating AI Commentary...")
            ai_commentary = MacroAIAnalyst().generate_commentary(macro_data, analysis_results)
            print(f"  {console_symbol.OK} AI Commentary Generated.")

            # 4. Generate Markdown Report
            print("  [4/4] Generating Markdown Dashboard...")
            md_gen = MacroMarkdownReport(output_dir=self.report_dir)
            md_text = md_gen.generate_report(macro_data, analysis_results, ai_commentary)
            
            # Save
            from datetime import datetime
            ts = macro_data.get('snapshot_date', datetime.now().isoformat())
            try:
                 date_str = datetime.fromisoformat(ts).strftime("%Y-%m-%d")
            except:
                 date_str = "unknown_date"
                 
            report_file = os.path.join(self.report_dir, f"macro_report_{date_str}.md")
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(md_text)
                
            print(f"{console_symbol.OK} Macro Report Saved: {os.path.basename(report_file)}")

        except Exception as e:
            logger.error(f"Macro Report Audit Error: {e}")
            print(f"{console_symbol.FAIL} Error: {e}")

def interactive_menu():
    auditor = ReportAuditor()
    
    while True:
        print_header("REPORT AUDITOR TOOL (Output Verification)")
        print("1. Audit Stock AI Commentary (Full AI Gen)")
        print("2. Audit Stock Data & Prompt (No AI)")
        print("3. Audit Macro Strategy Report")
        print("4. Exit")
        
        choice = input("\nSelect Option [1-4]: ").strip()
        
        if choice == '4':
            break
            
        if choice == '3':
            auditor.run_macro_report_audit()
            continue
            
        symbol = input("Enter Stock Symbol (e.g. AAPL): ").strip().upper()
        if not symbol: continue
        
        if choice == '1':
            auditor.run_commentary_audit(symbol)
        elif choice == '2':
            auditor.run_data_audit(symbol)
        else:
            print("Invalid selection.")

def main():
    interactive_menu()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")

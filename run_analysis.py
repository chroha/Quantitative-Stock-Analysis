"""
Quantitative Stock Analysis System - Single Stock Analyzer
Orchestrates the full analysis pipeline:
1. Data Acquisition (Stock & Benchmark)
2. Financial Scoring
3. Technical Scoring
4. Valuation Analysis
5. AI Commentary Generation
"""

import sys
import os
import json
import logging
from datetime import datetime
from pathlib import Path

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# IMPORTANT: Set logging mode BEFORE importing modules that create loggers
from utils import LoggingContext, set_logging_mode
set_logging_mode(LoggingContext.ORCHESTRATED)

# Now import modules (their loggers will respect ORCHESTRATED mode)
from config.constants import DATA_CACHE_STOCK, DATA_CACHE_BENCHMARK, DATA_REPORTS
from data_acquisition import StockDataLoader, BenchmarkDataLoader
from fundamentals.financial_data.financial_data_output import FinancialDataGenerator
from fundamentals.financial_scorers.financial_scorers_output import FinancialScorerGenerator
from fundamentals.technical_scorers.technical_scorers_output import TechnicalScorerGenerator
from fundamentals.valuation import ValuationCalculator
from fundamentals.valuation.valuation_output import ValuationOutput
from fundamentals.stock.data_aggregator import DataAggregator
from fundamentals.stock.stock_ai_analyst import StockAIAnalyst
from utils.logger import setup_logger
from utils.console_utils import symbol as ICON, print_step, print_separator
from utils.report_utils import (
    format_financial_score_report,
    format_technical_score_report,
    format_valuation_report
)
from fundamentals.reporting.report_assembler import ReportAssembler

logger = setup_logger('run_analysis')


def print_header(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)









def main():
    print_header("QUANTITATIVE STOCK ANALYSIS SYSTEM")
    
    # --- Input ---
    force_fetch = "--force-fetch" in sys.argv
    
    if len(sys.argv) > 1:
        # Filter out flags to get the symbol
        args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
        if args:
            symbol = args[0].strip().upper()
        else:
            symbol = input("Enter stock symbol (e.g., AAPL): ").strip().upper()
    else:
        symbol = input("Enter stock symbol (e.g., AAPL): ").strip().upper()
    
    if not symbol:
        print("[ERROR] Symbol is required.")
        return

    output_dir = os.path.join(current_dir, DATA_CACHE_STOCK)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # Report buffer - collect all reports here
    reports = []
    
    try:
        # ==============================================================================
        # STEP 1: Data Acquisition
        # ==============================================================================
        print_step(1, 6, "Data Acquisition")
        
        # 1.1 Benchmark Data
        bench_loader = BenchmarkDataLoader()
        bench_path = bench_loader.get_output_path()
        
        if bench_path.exists() and not force_fetch:
            print(f"  {ICON.OK} Industry Benchmark data available")
            if len(sys.argv) <= 1:
                choice = input("  Update industry benchmarks? (y/N): ").strip().lower()
                if choice == 'y':
                    print("  Downloading industry data files...")
                    bench_loader.run_update(force_refresh=True)
        else:
            print("  Fetching Industry Benchmarks...")
            print("  Downloading industry data files...")
            bench_loader.run_update(force_refresh=force_fetch)

        # 1.2 Stock Data
        stock_loader = StockDataLoader()
        stock_file = f"initial_data_{symbol}_{current_date}.json"
        stock_path = os.path.join(output_dir, stock_file)
        
        stock_data = None
        if os.path.exists(stock_path) and not force_fetch:
            print(f"  {ICON.OK} Found existing data for {symbol}")
            if len(sys.argv) <= 1:
                choice = input("  Update stock data? (y/N): ").strip().lower()
                if choice == 'y':
                     # Fix: Force refresh when user explicitly asks for update
                     stock_data = stock_loader.get_stock_data(symbol, force_refresh=True)
                     stock_loader.save_stock_data(stock_data, output_dir)
                else:
                    stock_data = stock_loader.load_stock_data(stock_path)
            else:
                stock_data = stock_loader.load_stock_data(stock_path)
        else:
            print(f"  Fetching data for {symbol}...")
            stock_data = stock_loader.get_stock_data(symbol)
            stock_loader.save_stock_data(stock_data, output_dir)
            
        # Validate sufficiency of data
        try:
            from config.analysis_config import DATA_THRESHOLDS
        except ImportError:
            # Fallback defaults if config is missing during refactor
            DATA_THRESHOLDS = {
                "REQUIRE_PROFILE_NAME": True,
                "REQUIRE_HISTORY": True,
                "REQUIRE_FINANCIALS": True
            }

        # Check for meaningful data (not just empty objects)
        has_profile = False
        if stock_data and stock_data.profile and stock_data.profile.std_company_name:
             has_profile = bool(stock_data.profile.std_company_name.value)
             
        has_history = False
        if stock_data and stock_data.price_history:
             has_history = len(stock_data.price_history) > 0
             
        has_financials = False
        if stock_data and stock_data.income_statements:
             has_financials = len(stock_data.income_statements) > 0
        
        # Check against config
        critical_missing = []
        if DATA_THRESHOLDS.get("REQUIRE_PROFILE_NAME", True) and not has_profile:
            critical_missing.append("Company Profile")
        if DATA_THRESHOLDS.get("REQUIRE_HISTORY", True) and not has_history:
            critical_missing.append("Price History")
        if DATA_THRESHOLDS.get("REQUIRE_FINANCIALS", True) and not has_financials:
             critical_missing.append("Financial Statements")
             
        has_critical_data = len(critical_missing) == 0

        if not has_critical_data:
            print(f"  {ICON.FAIL} No meaningful data found for {symbol}.")
            print("  (Missing Company Name, Price History, and Financial Statements)")
            print("  Stopping analysis to prevent errors.")
            return
        
        print(f"  {ICON.OK} Data acquisition complete")

        # ==============================================================================
        # STEP 2: Financial Data Calculation
        # ==============================================================================
        print_step(2, 6, "Calculating Fundamental Metrics")
        fin_data_gen = FinancialDataGenerator(data_dir=output_dir)
        fin_data_path = fin_data_gen.generate(symbol, quiet=True)
        
        if not fin_data_path:
            print(f"  {ICON.FAIL} Financial metric calculation failed.")
            return

        # Print summary of calculated metrics
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

                print(f"  {ICON.OK} Profitability: ROIC {fmt(pm.get('roic'))} | ROE {fmt(pm.get('roe'))} | Net Margin {fmt(pm.get('net_margin'))}")
                print(f"  {ICON.OK} Growth: Revenue {fmt(gm.get('revenue_cagr_5y'))} | Net Income {fmt(gm.get('net_income_cagr_5y'))} | FCF {fmt(gm.get('fcf_cagr_5y'))}")
                print(f"  {ICON.OK} Capital: {buyback_str} | Capex {fmt(cm.get('capex_intensity_3y'))} | D/E {fmt(cm.get('debt_to_equity'), False)}")
        except Exception as e:
            # Fallback if any error reading metrics
            print(f"  {ICON.OK} Financial data generated")

        # ==============================================================================
        # STEP 3: Financial Scoring
        # ==============================================================================
        print_step(3, 6, "Financial Scoring")
        benchmark_dir = os.path.join(current_dir, DATA_CACHE_BENCHMARK)
        fin_gen = FinancialScorerGenerator(data_dir=output_dir, benchmark_dir=benchmark_dir)
        fin_score_path = fin_gen.generate(symbol, quiet=True)
        
        fin_score = None
        try:
            if fin_score_path:
                with open(fin_score_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    fin_score = data.get('score', {})
                print(f"  {ICON.OK} Score: {fin_score.get('total_score', 0):.1f} / 100")
                
                # Warnings
                if fin_score.get('warnings'):
                    print(f"  {ICON.WARN} {len(fin_score['warnings'])} warnings generated")
                
                # Buffer the detailed report
                fin_report = format_financial_score_report(fin_score)
                if fin_report:
                    reports.append(fin_report)
            else:
                print(f"  {ICON.WARN} Financial scoring failed or skipped.")
        except Exception as e:
            print(f"  {ICON.FAIL} Scoring failed: {e}")
            print(f"  {ICON.WARN} Financial scoring failed or skipped.")

        # ==============================================================================
        # STEP 4: Technical Scoring
        # ==============================================================================
        print_step(4, 6, "Technical Scoring")
        tech_gen = TechnicalScorerGenerator(data_dir=output_dir)
        tech_score_path = tech_gen.generate(symbol, quiet=True)
        
        tech_score = None
        try:
            if tech_score_path:
                with open(tech_score_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    tech_score = data.get('score', {})
                print(f"  {ICON.OK} Score: {tech_score.get('total_score', 0):.1f} / 100")
                
                # Extract details safely
                try:
                    cats = tech_score.get('categories', {})
                    rsi_val = cats.get('momentum', {}).get('indicators', {}).get('rsi', {}).get('rsi')
                    
                    adx_data = cats.get('trend_strength', {}).get('indicators', {}).get('adx', {})
                    adx_val = adx_data.get('adx', 0)
                    p_di = adx_data.get('plus_di', 0)
                    m_di = adx_data.get('minus_di', 0)
                    trend_dir = "Up" if p_di > m_di else "Down"
                    trend_str = f"{trend_dir} ({adx_val:.1f})"
                    
                    print(f"  {ICON.OK} Trend: {trend_str} | RSI: {rsi_val}")
                except Exception:
                    print(f"  {ICON.OK} Trend: N/A | RSI: N/A")

                # Buffer the detailed report
                tech_report = format_technical_score_report(tech_score)
                if tech_report:
                    reports.append(tech_report)
            else:
                print(f"  {ICON.WARN} Technical scoring failed or skipped.")
                
        except Exception as e:
            print(f"  {ICON.FAIL} Technical scoring failed: {e}")
            print(f"  {ICON.WARN} Technical scoring failed or skipped.")

        # ==============================================================================
        # STEP 5: Valuation
        # ==============================================================================
        print_step(5, 6, "Valuation Analysis")
        val_calc = ValuationCalculator(benchmark_data_path=benchmark_dir)
        val_result = val_calc.calculate_valuation(stock_data)
        
        if val_result:
            fv = val_result.get('weighted_fair_value')
            diff = val_result.get('price_difference_pct')
            if fv and diff is not None:
                print(f"  {ICON.OK} Fair Value: ${fv:.2f} ({'+' if diff >= 0 else ''}{diff:.1f}%)")
            else:
                print(f"  {ICON.OK} Valuation complete")
            
            ValuationOutput.save_json(val_result, output_dir)
            
            # Buffer the detailed report
            val_report = format_valuation_report(val_result)
            if val_report:
                reports.append(val_report)
        else:
            print(f"  {ICON.WARN} Valuation failed.")

        # ==============================================================================
        # DISPLAY BUFFERED REPORTS (before AI call)
        # ==============================================================================
        if reports:
            print("\n" + "="*80)
            print("  DETAILED ANALYSIS REPORTS")
            print("  (Review while waiting for AI commentary)")
            print("="*80)
            for report in reports:
                print("\n" + report)

        # ==============================================================================
        # STEP 6: AI Commentary
        # ==============================================================================
        print_step(6, 6, "AI Commentary Generation")
        
        # Ask user whether to generate AI commentary
        if len(sys.argv) <= 1:  # Only prompt in interactive mode
            ai_choice = input("  Generate AI commentary? (Y/n): ").strip().lower()
            if ai_choice == 'n':
                print(f"  {ICON.OK} Skipped AI commentary generation.")
                print("\n" + "="*80)
                print("  ANALYSIS COMPLETE")
                print("="*80)
                return
        
        # Check prerequisites
        if not (fin_score and tech_score and val_result):
            print(f"  {ICON.WARN} Missing prerequisite scores. AI report might be incomplete.")

        aggregator = DataAggregator(data_dir=output_dir)
        aggregated_data = aggregator.aggregate(symbol)
        
        if aggregated_data:
            # Use StockAIAnalyst for generation
            analyst = StockAIAnalyst()
            report = analyst.generate_report(aggregated_data)
            
            # Append raw data appendix
            print(f"   Generating data appendix...")
            appendix = aggregator.get_raw_data_appendix(symbol)
            
            # Use Assembler to build final report
            report = ReportAssembler.assemble_stock_report(report, appendix)
            
            # Save to generated_reports
            report_file = f"ai_analysis_{symbol}_{current_date}.md"
            report_dir = os.path.join(current_dir, DATA_REPORTS)
            if not os.path.exists(report_dir):
                os.makedirs(report_dir, exist_ok=True)
                
            report_path = os.path.join(report_dir, report_file)
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
                
            print(f"\n[OK] AI Report Generated Successfully!")
            print(f"   Path: {report_path}")
        else:
            print("  [ERROR] Data aggregation failed.")

    except KeyboardInterrupt:
        print("\n[!] Analysis cancelled by user.")
    except Exception as e:
        logger.exception("Analysis pipeline failed")
        print(f"\n[ERROR] Pipeline failed: {e}")

if __name__ == "__main__":
    main()

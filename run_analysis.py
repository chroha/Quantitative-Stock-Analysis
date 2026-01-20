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

from data_acquisition import StockDataLoader, BenchmarkDataLoader
from fundamentals.financial_data.financial_data_output import FinancialDataGenerator
from fundamentals.financial_scorers.financial_scorers_output import FinancialScorerGenerator
from fundamentals.technical_scorers.technical_scorers_output import TechnicalScorerGenerator
from fundamentals.valuation import ValuationCalculator
from fundamentals.valuation.valuation_output import ValuationOutput
from fundamentals.ai_commentary.data_aggregator import DataAggregator
from fundamentals.ai_commentary.commentary_generator import CommentaryGenerator
from utils.logger import setup_logger

logger = setup_logger('run_analysis')


def suppress_sub_module_logs():
    """
    Suppress all logs from sub-modules during run_analysis.py execution.
    Only show ERROR and above for cleaner console output.
    Sub-modules will still log to file if configured.
    """
    noisy_loggers = [
        # Data acquisition
        'data_loader', 'yahoo_fetcher', 'fmp_fetcher', 'data_merger',
        'alphavantage_fetcher', 'field_validator',
        # Benchmark
        'benchmark_loader', 'benchmark_calculator',
        # Financial data & scoring  
        'financial_data_output', 'financial_scorers_output', 
        'technical_scorers_output', 'valuation_calculator', 'valuation_output',
        'calculator_base', 'company_scorer', 'metric_scorer',
        # Valuation modules
        'pe_valuation', 'pb_valuation', 'ps_valuation', 'ev_valuation',
        'analyst_targets', 'dcf_model', 'ddm_model', 'damodaran_fetcher',
        # Calculator modules
        'profitability', 'growth', 'capital_allocation',
    ]
    for name in noisy_loggers:
        logging.getLogger(name).setLevel(logging.ERROR)
    
    # Also suppress dynamic loggers like ProfitabilityCalculator_AAPL
    suppress_dynamic_calculators()


def suppress_dynamic_calculators():
    """Suppress dynamically created calculator loggers (e.g., ProfitabilityCalculator_V)."""
    for logger_name in list(logging.Logger.manager.loggerDict.keys()):
        if 'Calculator_' in logger_name or 'Scorer_' in logger_name:
            logging.getLogger(logger_name).setLevel(logging.ERROR)


def print_header(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)


def print_step(step_num, total, title):
    print(f"\n[{step_num}/{total}] {title}...")


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


def format_valuation_report(val_result):
    """Format valuation result as a clean report string."""
    if not val_result:
        return None
    
    ticker = val_result.get('ticker', '?')
    sector = val_result.get('sector', 'Unknown')
    current_price = val_result.get('current_price')
    weighted_fv = val_result.get('weighted_fair_value')
    price_diff = val_result.get('price_difference_pct')
    methods = val_result.get('method_results', {})
    confidence = val_result.get('confidence', {})
    
    lines = []
    lines.append("-" * 70)
    lines.append(f"VALUATION REPORT - {ticker} ({sector})")
    lines.append("-" * 70)
    
    if current_price:
        lines.append(f"Current Price: ${current_price:.2f}")
    
    if methods:
        lines.append("")
        lines.append("Valuation Methods:")
        sorted_methods = sorted(methods.items(), key=lambda x: x[1].get('weight', 0), reverse=True)
        for method_name, result in sorted_methods:
            model_name = result['model_name']
            fair_value = result.get('fair_value')
            weight = result.get('weight', 0)
            upside = result.get('upside_pct')
            status = result.get('status', 'success')
            
            # Handle failed models
            if status == 'failed' or fair_value is None:
                reason = result.get('reason', 'Unable to calculate')
                lines.append(f"  {model_name:20s}      N/A   (Weight: {weight*100:>3.0f}%)  [{reason}]")
                continue
            
            upside_str = f"{'+'if upside >= 0 else ''}{upside:.1f}%"
            if weight > 0:
                lines.append(f"  {model_name:20s} ${fair_value:>8.2f}  (Weight: {weight*100:>3.0f}%)  [{upside_str:>7s}]")
            else:
                lines.append(f"  {model_name:20s} ${fair_value:>8.2f}  (Weight:   0%)  [Not used]")
    
    if weighted_fv:
        lines.append("")
        lines.append(f"Weighted Fair Value: ${weighted_fv:.2f}")
    
    if price_diff is not None:
        diff_str = f"{'+'if price_diff >= 0 else ''}{price_diff:.1f}%"
        if price_diff > 20:
            assessment = "Significantly Undervalued"
        elif price_diff > 10:
            assessment = "Undervalued"
        elif price_diff > -10:
            assessment = "Fairly Valued"
        elif price_diff > -20:
            assessment = "Overvalued"
        else:
            assessment = "Significantly Overvalued"
        lines.append(f"Price Difference: {diff_str} ({assessment})")
    
    if confidence:
        methods_used = confidence.get('methods_used', 0)
        methods_total = confidence.get('methods_available', 0)
        lines.append(f"Confidence: {methods_used}/{methods_total} methods available")
    
    lines.append("-" * 70)
    return "\n".join(lines)


def main():
    print_header("QUANTITATIVE STOCK ANALYSIS SYSTEM V3.0")
    
    # Suppress sub-module logs for clean output
    suppress_sub_module_logs()
    
    # --- Input ---
    if len(sys.argv) > 1:
        symbol = sys.argv[1].strip().upper()
    else:
        symbol = input("Enter stock symbol (e.g., AAPL): ").strip().upper()
    
    if not symbol:
        print("[ERROR] Symbol is required.")
        return

    output_dir = os.path.join(current_dir, "generated_data")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
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
        
        if bench_path.exists():
            print(f"  ✓ Industry Benchmark data available")
            if len(sys.argv) <= 1:
                choice = input("  Update industry benchmarks? (y/N): ").strip().lower()
                if choice == 'y':
                    print("  Downloading industry data files...")
                    bench_loader.run_update(force_refresh=True)
        else:
            print("  Fetching Industry Benchmarks...")
            print("  Downloading industry data files...")
            bench_loader.run_update()

        # 1.2 Stock Data
        stock_loader = StockDataLoader()
        stock_file = f"initial_data_{symbol}_{current_date}.json"
        stock_path = os.path.join(output_dir, stock_file)
        
        stock_data = None
        if os.path.exists(stock_path):
            print(f"  ✓ Found existing data for {symbol}")
            if len(sys.argv) <= 1:
                choice = input("  Update stock data? (y/N): ").strip().lower()
                if choice == 'y':
                     stock_data = stock_loader.get_stock_data(symbol)
                     stock_loader.save_stock_data(stock_data, output_dir)
                else:
                    stock_data = stock_loader.load_stock_data(stock_path)
            else:
                stock_data = stock_loader.load_stock_data(stock_path)
        else:
            print(f"  Fetching data for {symbol}...")
            stock_data = stock_loader.get_stock_data(symbol)
            stock_loader.save_stock_data(stock_data, output_dir)
            
        if not stock_data:
            print("[ERROR] Failed to load stock data.")
            return
        
        print(f"  ✓ Data acquisition complete")

        # ==============================================================================
        # STEP 2: Financial Data Calculation
        # ==============================================================================
        print_step(2, 6, "Calculating Fundamental Metrics")
        fin_data_gen = FinancialDataGenerator(data_dir=output_dir)
        fin_data_path = fin_data_gen.generate(symbol, quiet=True)
        
        if not fin_data_path:
            print("[ERROR] Financial metric calculation failed.")
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

                print(f"  ✓ Profitability: ROIC {fmt(pm.get('roic'))} | ROE {fmt(pm.get('roe'))} | Net Margin {fmt(pm.get('net_margin'))}")
                print(f"  ✓ Growth: Revenue {fmt(gm.get('revenue_cagr_5y'))} | Net Income {fmt(gm.get('net_income_cagr_5y'))} | FCF {fmt(gm.get('fcf_cagr_5y'))}")
                print(f"  ✓ Capital: {buyback_str} | Capex {fmt(cm.get('capex_intensity_3y'))} | D/E {fmt(cm.get('debt_to_equity'), False)}")
        except Exception as e:
            # Fallback if any error reading metrics
            print(f"  ✓ Financial data generated")
        
        # Suppress any dynamically created calculator loggers
        suppress_dynamic_calculators()

        # ==============================================================================
        # STEP 3: Financial Scoring
        # ==============================================================================
        print_step(3, 6, "Financial Scoring")
        fin_gen = FinancialScorerGenerator(data_dir=output_dir)
        fin_score_path = fin_gen.generate(symbol, quiet=True)
        
        fin_score = None
        if fin_score_path:
            with open(fin_score_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                fin_score = data.get('score', {})
            print(f"  ✓ Score: {fin_score.get('total_score', 0):.1f} / 100")
            
            # Buffer the detailed report
            fin_report = format_financial_score_report(fin_score)
            if fin_report:
                reports.append(fin_report)
        else:
            print("  [WARN] Financial scoring failed or skipped.")

        # ==============================================================================
        # STEP 4: Technical Scoring
        # ==============================================================================
        print_step(4, 6, "Technical Scoring")
        tech_gen = TechnicalScorerGenerator(data_dir=output_dir)
        tech_score_path = tech_gen.generate(symbol, quiet=True)
        
        tech_score = None
        if tech_score_path:
            with open(tech_score_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                tech_score = data.get('score', {})
            print(f"  ✓ Score: {tech_score.get('total_score', 0)} / {tech_score.get('max_score', 100)}")
            
            # Buffer the detailed report
            tech_report = format_technical_score_report(tech_score)
            if tech_report:
                reports.append(tech_report)
        else:
            print("  [WARN] Technical scoring failed or skipped.")

        # ==============================================================================
        # STEP 5: Valuation
        # ==============================================================================
        print_step(5, 6, "Valuation Analysis")
        val_calc = ValuationCalculator(benchmark_data_path=output_dir)
        val_result = val_calc.calculate_valuation(stock_data)
        
        if val_result:
            fv = val_result.get('weighted_fair_value')
            diff = val_result.get('price_difference_pct')
            if fv and diff is not None:
                print(f"  ✓ Fair Value: ${fv:.2f} ({'+' if diff >= 0 else ''}{diff:.1f}%)")
            else:
                print(f"  ✓ Valuation complete")
            
            ValuationOutput.save_json(val_result, output_dir)
            
            # Buffer the detailed report
            val_report = format_valuation_report(val_result)
            if val_report:
                reports.append(val_report)
        else:
            print("  [WARN] Valuation failed.")

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
                print("  ✓ Skipped AI commentary generation.")
                print("\n" + "="*80)
                print("  ANALYSIS COMPLETE")
                print("="*80)
                return
        
        # Check prerequisites
        if not (fin_score and tech_score and val_result):
            print("  [WARN] Missing prerequisite scores. AI report might be incomplete.")

        aggregator = DataAggregator(data_dir=output_dir)
        aggregated_data = aggregator.aggregate(symbol)
        
        if aggregated_data:
            generator = CommentaryGenerator()
            report = generator.generate_report(aggregated_data)
            
            # Append raw data appendix (Same logic as run_commentary.py)
            print(f"   Generating data appendix...")
            appendix = aggregator.get_raw_data_appendix(symbol)
            if appendix:
                report = report + appendix
            
            if report:
                report_file = f"ai_analysis_{symbol}_{current_date}.md"
                # Save to generated_reports
                report_dir = os.path.join(current_dir, "generated_reports")
                if not os.path.exists(report_dir):
                    os.makedirs(report_dir)
                    
                report_path = os.path.join(report_dir, report_file)
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(report)
                print(f"\n✅ AI Report Generated Successfully!")
                print(f"   Path: {report_path}")
            else:
                print("  [ERROR] AI generation failed (API error or empty response).")
        else:
            print("  [ERROR] Data aggregation failed.")

    except KeyboardInterrupt:
        print("\n[!] Analysis cancelled by user.")
    except Exception as e:
        logger.exception("Analysis pipeline failed")
        print(f"\n[ERROR] Pipeline failed: {e}")

if __name__ == "__main__":
    main()

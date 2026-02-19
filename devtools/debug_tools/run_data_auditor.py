"""
Data Auditor Module
===================

Core logic for the Data Audit System.
Responsible for:
1. Capturing raw API responses ("The Source of Truth").
2. Running fetchers in isolation to verify parsing logic.
3. Comparing raw fields vs. mapped fields to identify gaps.
4. Tracing data provenance through the pipeline.
5. [NEW] Interactive Menu & Full Cross-Source Scan.
6. [NEW] Benchmark & Macro Data Validation.
"""

import os
import json
import sys
import argparse
import pandas as pd
import yfinance as yf
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

# Ensure project root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import Fetchers
from data_acquisition.stock_data.yahoo_fetcher import YahooFetcher
from data_acquisition.stock_data.edgar_fetcher import EdgarFetcher
from data_acquisition.stock_data.fmp_fetcher import FMPFetcher
from data_acquisition.stock_data.alphavantage_fetcher import AlphaVantageFetcher
from data_acquisition.stock_data.finnhub_fetcher import FinnhubFetcher
from data_acquisition.stock_data.initial_data_loader import StockDataLoader

# Import Mappings and Constants
from utils.unified_schema import YAHOO_FIELD_MAPPING, StockData
from utils.console_utils import symbol as console_symbol, print_header, print_step
from config.constants import DATA_CACHE_BENCHMARK, DATA_CACHE_MACRO
from utils.logger import setup_logger
from data_acquisition.benchmark_data.benchmark_data_loader import BenchmarkDataLoader
from data_acquisition.macro_data.macro_aggregator import MacroAggregator

# Setup logger using unified utility
logger = setup_logger("data_auditor")

class DataAuditor:
    def __init__(self, symbol: str, output_base_dir: str):
        self.symbol = symbol.upper() if symbol else "GENERAL"
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Structure: output_base_dir / Symbol_Timestamp
        self.session_dir = os.path.join(output_base_dir, f"{self.symbol}_{self.timestamp}")
        
        # Sub-directories
        self.dirs = {
            'raw': os.path.join(self.session_dir, "1_raw_source"),
            'parsed': os.path.join(self.session_dir, "2_parsed_isolated"),
            'merged': os.path.join(self.session_dir, "3_pipeline_states"),
            'reports': os.path.join(self.session_dir, "4_audit_reports")
        }
        
    def _prepare_dirs(self):
        """Create directories only when needed to avoid empty folders for skipped modes."""
        for d in self.dirs.values():
            os.makedirs(d, exist_ok=True)
            
    def _save_json(self, data: Dict, filename: str, sub_dir: str):
        self._prepare_dirs()
        path = os.path.join(self.dirs[sub_dir], filename)
        
        def default_serializer(obj):
            if isinstance(obj, (datetime, pd.Timestamp)):
                return obj.isoformat()
            if hasattr(obj, 'to_dict'): # Pydantic models
                return obj.to_dict() 
            return str(obj)

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, default=default_serializer)
        logger.info(f"Saved: {path}")

    def _save_txt(self, lines: List[str], filename: str, sub_dir: str, header: str = None):
        self._prepare_dirs()
        path = os.path.join(self.dirs[sub_dir], filename)
        with open(path, 'w', encoding='utf-8') as f:
            if header:
                f.write(header + "\n" + "="*len(header) + "\n\n")
            f.write("\n".join(lines))
        logger.info(f"Report: {path}")

    # --- Stock Audit Methods ---

    def audit_yahoo(self, full_scan: bool = False):
        """Audit Yahoo Finance Data."""
        logger.info(f"\n--- Auditing Yahoo Finance ({self.symbol}) [Full={full_scan}] ---")
        try:
            # 1. Raw
            ticker = yf.Ticker(self.symbol)
            raw_info = ticker.info
            self._save_json(raw_info, "yahoo_raw_info.json", 'raw')
            
            # 2. Unmapped Analysis
            mapped_keys = set(YAHOO_FIELD_MAPPING.keys())
            raw_keys = set(raw_info.keys())
            unmapped = sorted(list(raw_keys - mapped_keys))
            
            ignored_prefixes = ['underlying', 'sandbox', 'gmt', 'uuid', 'messageBoard', 'companyOfficers']
             # Fields that are manually extracted or known
            KNOWN_MANUAL_FIELDS = {
                'longName', 'shortName', 'industry', 'sector', 'website', 'longBusinessSummary',
                'marketCap', 'beta', 'symbol', 'bookValue', 'dividendYield', 
                'trailingPE', 'forwardPE', 'pegRatio', 'priceToBook', 
                'trailingEps', 'forwardEps', 'currency', 'financialCurrency', 'exchange',
                'regularMarketOpen', 'regularMarketDayHigh', 'regularMarketDayLow', 
                'regularMarketPreviousClose', 'regularMarketVolume',
                'heldPercentInsiders', 'heldPercentInstitutions', 'shortRatio', 
                'shortPercentOfFloat', 'enterpriseValue', 'enterpriseToEbitda',
                'recommendationKey', '52WeekChange', 'SandP52WeekChange',
                'currentRatio', 'quickRatio', 'auditRisk', 'boardRisk',
                'totalCashPerShare', 'revenuePerShare',
                'targetLowPrice', 'targetHighPrice', 'targetMeanPrice', 'targetMedianPrice', 'numberOfAnalystOpinions'
            }
            possible_unmapped = set(unmapped) - KNOWN_MANUAL_FIELDS
            interesting_unmapped = [k for k in sorted(list(possible_unmapped)) if not any(k.startswith(p) for p in ignored_prefixes)]
            
            self._save_txt(interesting_unmapped, "yahoo_unmapped_fields.txt", 'reports', 
                          header=f"Yahoo Fields NOT Mapped ({len(interesting_unmapped)} found)")

            # 3. Parsed
            fetcher = YahooFetcher(self.symbol)
            # Yahoo fetch_all always fetches max available based on its implementation, 
            # but we can explicitly pass limit=None to income/balance/cashflow if we exposed it in fetch_all.
            # Currently fetch_all doesn't take args, but the underlying methods do. 
            # For Yahoo, default is ALL.
            data = fetcher.fetch_all()
            self._save_json(data.model_dump(), "yahoo_parsed.json", 'parsed')
            
        except Exception as e:
            logger.error(f"Yahoo Audit Failed: {e}")

    def audit_edgar(self):
        """Audit SEC EDGAR Data."""
        logger.info(f"\n--- Auditing SEC EDGAR ({self.symbol}) ---")
        try:
            fetcher = EdgarFetcher()
            # Edgar fetcher is complex, assumes full fetch by default usually
            data_dict = fetcher.fetch_all_financials(self.symbol)
            serialized = {k: [stmt.model_dump() for stmt in v] for k, v in data_dict.items()}
            self._save_json(serialized, "edgar_parsed.json", 'parsed')
            logger.info(f"Edgar: Retrieved {len(serialized.get('income_statements', []))} income statements")
        except Exception as e:
            logger.error(f"Edgar Audit Failed: {e}")

    def audit_fmp(self, full_scan: bool = False):
        """Audit FMP Data (Profile + Financials)."""
        logger.info(f"\n--- Auditing FMP ({self.symbol}) [Full={full_scan}] ---")
        try:
            limit = None if full_scan else 6
            fetcher = FMPFetcher(self.symbol)
            profile = fetcher.fetch_profile()
            income = fetcher.fetch_income_statements(limit=limit)
            audit_data = {
                'profile': profile.model_dump() if profile else None,
                'income_statements': [s.model_dump() for s in income] if income else []
            }
            self._save_json(audit_data, "fmp_parsed.json", 'parsed')
        except Exception as e:
            logger.warning(f"FMP Audit Failed: {e}")

    def audit_alphavantage(self, full_scan: bool = False):
        """Audit Alpha Vantage Data."""
        logger.info(f"\n--- Auditing Alpha Vantage ({self.symbol}) [Full={full_scan}] ---")
        try:
            limit = None if full_scan else 5
            fetcher = AlphaVantageFetcher(self.symbol)
            profile = fetcher.fetch_profile()
            income = fetcher.fetch_income_statements(limit=limit) # Added check effectively
            audit_data = {
                'profile': profile.model_dump() if profile else None,
                'income_statements': [s.model_dump() for s in income] if income else []
            }
            self._save_json(audit_data, "alphavantage_parsed.json", 'parsed')
        except Exception as e:
            logger.warning(f"AlphaVantage Audit Failed: {e}")
            
    # ... (Forecast methods unchanged) ...

    def audit_fmp_forecast(self):
        """Audit FMP Forecast Data."""
        logger.info(f"\n--- Auditing FMP Forecast ({self.symbol}) ---")
        try:
            fetcher = FMPFetcher(self.symbol)
            forecast = fetcher.fetch_forecast_data()
            if forecast:
                self._save_json(forecast.model_dump(), "fmp_forecast.json", 'parsed')
                
                # Summary
                lines = [f"FMP Forecast: {self.symbol}", "="*30]
                lines.append(f"Analysts: {forecast.std_number_of_analysts.value if forecast.std_number_of_analysts else 'N/A'}")
                lines.append(f"Avg Target: {forecast.std_price_target_avg.value if forecast.std_price_target_avg else 'N/A'}")
                self._save_txt(lines, "fmp_forecast_summary.txt", 'reports')
        except Exception as e:
            logger.warning(f"FMP Forecast Audit Failed: {e}")

    def audit_finnhub(self):
        """Audit Finnhub Forecast & New Data (Phase 2)."""
        logger.info(f"\n--- Auditing Finnhub (Forecast, News, Sentiment, Peers) ---")
        try:
            fetcher = FinnhubFetcher(self.symbol)
            
            # 1. Forecast
            forecast = fetcher.fetch_forecast_data()
            if forecast:
                self._save_json(forecast.model_dump(), "finnhub_forecast.json", 'parsed')
            
            # 2. Company News (Last 30 days)
            import datetime
            end = datetime.date.today().strftime('%Y-%m-%d')
            start = (datetime.date.today() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
            news = fetcher.fetch_company_news(start, end)
            if news:
                self._save_json([n.model_dump() for n in news], "finnhub_news.json", 'parsed')
                
            # 3. Peers
            peers = fetcher.fetch_peers()
            if peers:
                self._save_json(peers, "finnhub_peers.json", 'parsed')
                
            # 4. Sentiment
            sentiment = fetcher.fetch_sentiment()
            if sentiment:
                self._save_json(sentiment.model_dump(), "finnhub_sentiment.json", 'parsed')

            # Summary Report
            lines = [f"Finnhub Audit: {self.symbol}", "="*30]
            lines.append(f"EPS Estimate: {forecast.std_eps_estimate_current_year.value if forecast and forecast.std_eps_estimate_current_year else 'N/A'}")
            lines.append(f"News Count (30d): {len(news)}")
            lines.append(f"Peers: {', '.join(peers[:5])}...")
            lines.append(f"Sentiment Data: {'Yes' if sentiment else 'No'}")
            self._save_txt(lines, "finnhub_summary.txt", 'reports')
            
        except Exception as e:
            logger.warning(f"Finnhub Audit Failed: {e}")

    def run_pipeline_integration(self):
        """Run Full Integrity Pipeline."""
        logger.info(f"\n--- Running Pipeline Integration ({self.symbol}) ---")
        try:
            loader = StockDataLoader()
            final_data = loader.get_stock_data(self.symbol)
            self._save_json(final_data.model_dump(), "final_merged_pipeline.json", 'merged')
            
            # Simple provenance report
            lines = [f"Pipeline Result: {self.symbol}", "="*30]
            lines.append(f"Income Stmts: {len(final_data.income_statements)}")
            lines.append(f"Balance Sheets: {len(final_data.balance_sheets)}")
            if final_data.profile:
                lines.append(f"Profile Source: {final_data.profile.std_description.source if final_data.profile.std_description else 'N/A'}")
            self._save_txt(lines, "final_provenance_report.txt", 'reports')
            
        except Exception as e:
            logger.error(f"Pipeline Integration Failed: {e}")

    def audit_full_scan(self):
        """Execute Full Cross-Source Fetch."""
        logger.info(f"\n--- ⚡ RUNNING FULL CROSS-SOURCE SCAN FOR {self.symbol} ---")
        
        results = {}
        
        # 1. Yahoo
        try:
            yf_data = YahooFetcher(self.symbol).fetch_all()
            if yf_data:
                self._save_json(yf_data.model_dump(), "yahoo_full_scan.json", 'raw')
            results['Yahoo'] = {
                'Profile': bool(yf_data and yf_data.profile),
                'Financials': bool(yf_data and yf_data.income_statements),
                'Price': bool(yf_data and yf_data.price_history)
            }
        except Exception as e: results['Yahoo'] = {'Error': str(e)}

        # 2. FMP
        try:
            fmp = FMPFetcher(self.symbol)
            profile = fmp.fetch_profile()
            income = fmp.fetch_income_statements(limit=6) # Breadth check only
            forecast = fmp.fetch_forecast_data()
            
            # Save Raw Data
            fmp_raw = {
                'profile': profile.model_dump() if profile else None,
                'income_statements': [x.model_dump() for x in income] if income else [],
                'forecast': forecast.model_dump() if forecast else None
            }
            self._save_json(fmp_raw, "fmp_full_scan.json", 'raw')

            results['FMP'] = {
                'Profile': bool(profile),
                'Financials': bool(income),
                'Forecast': bool(forecast)
            }
        except Exception as e: results['FMP'] = {'Error': str(e)}

        # 3. AlphaVantage
        try:
            av = AlphaVantageFetcher(self.symbol)
            profile = av.fetch_profile()
            inc = av.fetch_income_statements(limit=6)
            bal = av.fetch_balance_sheets(limit=6)
            cf = av.fetch_cash_flow_statements(limit=6)
            
            av_raw = {
                'profile': profile.model_dump() if profile else None,
                'income_statements': [x.model_dump() for x in inc] if inc else [],
                'balance_sheets': [x.model_dump() for x in bal] if bal else [],
                'cash_flow_statements': [x.model_dump() for x in cf] if cf else []
            }
            self._save_json(av_raw, "alphavantage_full_scan.json", 'raw')
            
            has_financials = bool(inc or bal or cf)
            results['AlphaVantage'] = {
                'Profile': bool(profile),
                'Financials': has_financials
            }
        except Exception as e: results['AlphaVantage'] = {'Error': str(e)}

        # 4. Finnhub
        try:
            fh = FinnhubFetcher(self.symbol)
            profile = fh.fetch_profile()
            forecast = fh.fetch_forecast_data()
            import datetime
            start_news = (datetime.date.today() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
            news = fh.fetch_company_news(start_news, datetime.date.today().strftime('%Y-%m-%d'))
            sentiment = fh.fetch_sentiment()
            peers = fh.fetch_peers()
            
            fh_raw = {
                'profile': profile.model_dump() if profile else None,
                'forecast': forecast.model_dump() if forecast else None,
                'news_count': len(news),
                'sentiment': sentiment.model_dump() if sentiment else None,
                'peers': peers
            }
            self._save_json(fh_raw, "finnhub_full_scan.json", 'raw')

            results['Finnhub'] = {
                'Profile': bool(profile),
                'Forecast': bool(forecast),
                'News': bool(news),
                'Sentiment': bool(sentiment),
                'Peers': bool(peers)
            }
        except Exception as e: results['Finnhub'] = {'Error': str(e)}

        # 5. Edgar
        try:
            edgar = EdgarFetcher()
            edgar_data = edgar.fetch_all_financials(self.symbol)
            
            # Serialize individually
            edgar_serialized = {k: [stmt.model_dump() for stmt in v] for k, v in edgar_data.items()}
            self._save_json(edgar_serialized, "edgar_full_scan.json", 'raw')
            
            results['Edgar'] = {'Financials': bool(edgar_data.get('income_statements'))}
        except Exception as e: results['Edgar'] = {'Error': str(e)}

        self._save_json(results, "full_scan_coverage.json", 'reports')
        
        print(f"\n[Full Scan Summary for {self.symbol}]")
        print(f"{'Source':<15} | {'Profile':<8} | {'Finance':<8} | {'Forecast':<8} | {'Price':<8} | {'News/Sent':<10}")
        print("-" * 80)
        for source, data in results.items():
            if 'Error' in data:
                print(f"{source:<15} | ERROR: {data['Error']}")
                continue
            p = "YES" if data.get('Profile') else "NO"
            f = "YES" if data.get('Financials') else "NO"
            fo = "YES" if data.get('Forecast') else "NO"
            pr = "YES" if data.get('Price') else "NO"
            
            # New fields logic
            ns = []
            if data.get('News'): ns.append("News")
            if data.get('Sentiment'): ns.append("Sent")
            if data.get('Peers'): ns.append("Peer")
            ns_str = ",".join(ns) if ns else "NO"

            # Mask implicitly unsupported types
            if source == 'Edgar': p, fo, pr, ns_str = '-', '-', '-', '-'
            if source == 'AlphaVantage': fo, pr, ns_str = '-', '-', '-'
            if source == 'Finnhub': f, pr = '-', '-'
            if source == 'FMP': pr = '-'
            if source == 'Yahoo': ns_str = '-' # Though Yahoo has news, we rely on Finnhub for now
            
            print(f"{source:<15} | {p:<8} | {f:<8} | {fo:<8} | {pr:<8} | {ns_str:<10}")

    # --- System Audits ---

    def audit_benchmarks(self):
        """Validate Benchmark Data Files."""
        logger.info("\n--- Auditing Industry Benchmarks ---")
        bench_dir = Path(project_root) / DATA_CACHE_BENCHMARK
        
        # Expected CSV files
        EXPECTED_FILES = [
            'betas_data.csv', 'div_yield_data.csv', 'ev_ebitda_data.csv', 
            'margins_data.csv', 'pbv_data.csv', 'pe_data.csv', 
            'ps_data.csv', 'roc_data.csv', 'roe_data.csv', 'wacc_data.csv'
        ]

        # Check for missing directory or empty directory
        missing_data = False
        if not bench_dir.exists():
            print(f"{console_symbol.WARN} Benchmark Directory Missing: {bench_dir}")
            missing_data = True
        else:
            files = list(bench_dir.glob("*.csv"))
            if not files:
                print(f"{console_symbol.WARN} No benchmark CSV files found.")
                missing_data = True
        
        # Interactive Prompt to Fix
        if missing_data:
            print("\nbenchmark data is required for calculating industry scores.")
            choice = input(f"  ? Download latest benchmarks from Damodaran now? (Y/n): ").strip().lower()
            if choice in ['', 'y', 'yes']:
                print(f"\n  {console_symbol.ARROW} Downloading benchmark data...")
                loader = BenchmarkDataLoader()
                result = loader.run_update(force_refresh=True)
                if result:
                    print(f"  {console_symbol.OK} Benchmarks updated successfully.")
                else:
                    print(f"  {console_symbol.FAIL} Failed to update benchmarks.")
                    return
            else:
                print("  Skipping benchmark update.")
                return

        # Re-check files
        if not bench_dir.exists(): return
        found_files = {f.name: f for f in bench_dir.glob("*.csv")}
        
        # Check JSON Cache
        json_files = sorted(list(bench_dir.glob("benchmark_data_*.json")))
        latest_json = json_files[-1] if json_files else None
        
        print(f"\n[Benchmark Data Status]")
        print(f"{'File Name':<30} | {'Status':<10} | {'Age (Days)':<10}")
        print("-" * 55)
        
        # 1. Check CSVs
        for expected in EXPECTED_FILES:
            if expected in found_files:
                f_path = found_files[expected]
                delta = (datetime.now() - datetime.fromtimestamp(f_path.stat().st_mtime)).days
                status = "OK" if delta < 30 else "OLD"
                print(f"{expected:<30} | {status:<10} | {delta:<10}")
            else:
                print(f"{expected:<30} | MISSING    | -")
        
        print("-" * 55)
        
        # 2. Check JSON
        if latest_json:
            delta = (datetime.now() - datetime.fromtimestamp(latest_json.stat().st_mtime)).days
            print(f"{latest_json.name:<30} | GENERATED  | {delta:<10}")
        else:
            print(f"{'benchmark_data_*.json':<30} | MISSING    | -")
            print(f"\n{console_symbol.WARN} JSON cache missing. Run update to generate.")
            
    def audit_macro(self):
        """Validate Macro Data Cache."""
        logger.info("\n--- Auditing Macro Data ---")
        macro_dir = Path(project_root) / DATA_CACHE_MACRO
        latest_file = macro_dir / "macro_latest.json"
        
        # Check for missing file
        if not latest_file.exists():
            print(f"{console_symbol.WARN} Macro Snapshot Missing: {latest_file}")
            
            # Interactive Fix
            print("\nMacro data is required for market risk analysis.")
            choice = input(f"  ? Download latest macro data (FRED/Yahoo) now? (Y/n): ").strip().lower()
            if choice in ['', 'y', 'yes']:
                print(f"\n  {console_symbol.ARROW} Fetching macro data...")
                try:
                    # Pass input function to allow Forward PE prompt if needed
                    agg = MacroAggregator(interactive_input_func=input)
                    agg.run()
                    print(f"  {console_symbol.OK} Macro data updated successfully.")
                except Exception as e:
                    print(f"  {console_symbol.FAIL} Failed to update macro data: {e}")
                    return
            else:
                 print("  Skipping macro update.")
                 return

        # Re-check
        if not latest_file.exists(): return

        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            ts = data.get('snapshot_date', 'Unknown')
            qual = data.get('data_quality', {}).get('overall_status', 'Unknown')
            
            # Calculate Age
            try:
                file_ts = datetime.fromtimestamp(latest_file.stat().st_mtime)
                age = (datetime.now() - file_ts).days
                age_str = f"{age} days old"
            except:
                age_str = "Unknown age"

            print(f"\n[Macro Data Status]")
            print(f"{'Metric':<20} | {'Value':<30}")
            print("-" * 55)
            print(f"{'Snapshot Date':<20} | {ts}")
            print(f"{'File Age':<20} | {age_str}")
            print(f"{'Quality Status':<20} | {qual}")
            
            # Check Keys
            keys = list(data.get('dashboard_data', {}).keys())
            print(f"{'Sections':<20} | {', '.join(keys)}")
            
        except Exception as e:
            print(f"{console_symbol.FAIL} Corrupt Macro File: {e}")


def interactive_menu(output_dir: str):
    while True:
        print_header("DATA AUDITOR TOOL (Data Verification)")
        print("1. Audit Single Stock (Standard)")
        print("2. Audit Single Stock (Full Cross-Source Scan)")
        print("3. Audit Industry Benchmarks")
        print("4. Audit Macro Data")
        print("5. Exit")
        
        choice = input("\nSelect Option [1-5]: ").strip()
        
        if choice == '5':
            print("Exiting.")
            break
            
        if choice in ['1', '2']:
            symbol = input("Enter Stock Symbol (e.g. AAPL): ").strip().upper()
            if not symbol: continue
            
            auditor = DataAuditor(symbol, output_dir)
            if choice == '1':
                auditor.run_pipeline_integration() # Standard Flow
                # Optionally run specific standard audits
                auditor.audit_yahoo()
                auditor.audit_edgar()
            elif choice == '2':
                auditor.audit_full_scan()
                
        elif choice == '3':
            auditor = DataAuditor("SYS", output_dir)
            auditor.audit_benchmarks()
            
        elif choice == '4':
            auditor = DataAuditor("SYS", output_dir)
            auditor.audit_macro()
        else:
            print("Invalid selection.")

def main():
    parser = argparse.ArgumentParser(description='Run Data Audit')
    parser.add_argument('symbol', nargs='?', help='Stock symbol to audit')
    parser.add_argument('--full-scan', action='store_true', help='Force full cross-source fetch')
    args = parser.parse_args()
    
    # Define Audit Output Directory
    OUTPUT_DIR = os.path.join(project_root, "devtools", "audit_output")
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
    print(f"Audit Output Directory: {OUTPUT_DIR}")

    # If args provided, run headless
    if args.symbol:
        auditor = DataAuditor(args.symbol, OUTPUT_DIR)
        if args.full_scan:
            auditor.audit_full_scan()
        else:
            # Run Standard Audit Suite
            auditor.audit_yahoo()
            auditor.audit_edgar()
            auditor.audit_fmp()
            auditor.audit_alphavantage()
            auditor.audit_fmp_forecast()
            auditor.audit_finnhub()
            auditor.run_pipeline_integration()
    else:
        # Interactive Mode
        interactive_menu(OUTPUT_DIR)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")

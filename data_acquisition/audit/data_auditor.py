"""
Data Auditor Module
===================

Core logic for the Data Audit System.
Responsible for:
1. Capturing raw API responses ("The Source of Truth").
2. Running fetchers in isolation to verify parsing logic.
3. Comparing raw fields vs. mapped fields to identify gaps.
4. Tracing data provenance through the pipeline.
"""

import os
import json
import pandas as pd
import yfinance as yf
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

import sys

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
from data_acquisition.stock_data.finnhub_fetcher import FinnhubFetcher  # NEW
from data_acquisition.stock_data.initial_data_loader import StockDataLoader

# Import Mappings
from utils.unified_schema import YAHOO_FIELD_MAPPING, FMP_FIELD_MAPPING, StockData
from utils.console_utils import symbol as console_symbol

# Setup basic logging to console
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("data_auditor")

class DataAuditor:
    def __init__(self, symbol: str, output_dir: str):
        self.symbol = symbol.upper()

        self.output_dir = output_dir
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = os.path.join(self.output_dir, f"{self.symbol}_{self.timestamp}")
        
        # Sub-directories
        self.dirs = {
            'raw': os.path.join(self.session_dir, "1_raw_source"),
            'parsed': os.path.join(self.session_dir, "2_parsed_isolated"),
            'merged': os.path.join(self.session_dir, "3_pipeline_states"),
            'reports': os.path.join(self.session_dir, "4_audit_reports")
        }
        
        for d in self.dirs.values():
            os.makedirs(d, exist_ok=True)
            
    def _save_json(self, data: Dict, filename: str, sub_dir: str):
        path = os.path.join(self.dirs[sub_dir], filename)
        
        # Helper to serialize non-serializable objects (like datetime)
        def default_serializer(obj):
            if isinstance(obj, (datetime, pd.Timestamp)):
                return obj.isoformat()
            if hasattr(obj, 'to_dict'): # Pydantic models
                return obj.to_dict() 
            return str(obj)

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, default=default_serializer)
        logger.info(f"Saved: {path}")

    def audit_yahoo(self):
        """Audit Yahoo Finance Data."""
        logger.info(f"\n--- Auditing Yahoo Finance ({self.symbol}) ---")
        
        # 1. Raw Data Capture
        try:
            ticker = yf.Ticker(self.symbol)
            raw_info = ticker.info
            self._save_json(raw_info, "yahoo_raw_info.json", 'raw')
            
            # 2. Unmapped Field Detection
            mapped_keys = set(YAHOO_FIELD_MAPPING.keys())
            raw_keys = set(raw_info.keys())
            
            unmapped = list(raw_keys - mapped_keys)
            unmapped.sort()
            
            # Filter out boring/irrelevant keys to make report useful
            # Filter out boring/irrelevant keys to make report useful
            ignored_prefixes = ['underlying', 'sandbox', 'gmt', 'uuid', 'messageBoard', 'companyOfficers']
            
            # Fields that are manually extracted in YahooFetcher (not in generic mapping)
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
                          header=f"Yahoo Fields NOT Mapped in unified_schema.py ({len(interesting_unmapped)} found)")
                          
        except Exception as e:
            logger.error(f"Failed to capture raw Yahoo data: {e}")

        # 3. Parsed Data Isolation
        try:
            fetcher = YahooFetcher(self.symbol)
            data = fetcher.fetch_all()
            self._save_json(data.model_dump(), "yahoo_parsed.json", 'parsed')
        except Exception as e:
            logger.error(f"Failed to fetch parsed Yahoo data: {e}")

    def audit_edgar(self):
        """Audit SEC EDGAR Data."""
        logger.info(f"\n--- Auditing SEC EDGAR ({self.symbol}) ---")
        # Edgar is complex (CIK lookup etc), just run the fetcher
        try:
            fetcher = EdgarFetcher()
            # This returns a dict of statement lists
            data_dict = fetcher.fetch_all_financials(self.symbol)
            
            # Serialize
            serialized = {}
            for k, v in data_dict.items(): # income_statements, etc.
                serialized[k] = [stmt.model_dump() for stmt in v]
                
            self._save_json(serialized, "edgar_parsed.json", 'parsed')
            logger.info(f"Edgar: Retrieved {len(serialized.get('income_statements', []))} income statements")
        except Exception as e:
            logger.error(f"Failed to audit Edgar: {e}")

    def audit_fmp(self):
        """Audit FMP Data."""
        logger.info(f"\n--- Auditing FMP ({self.symbol}) ---")
        try:
            fetcher = FMPFetcher(self.symbol)
            # FMP fetcher methods return objects or lists of objects
            # We'll fetch profile and one statement type as sample
            profile = fetcher.fetch_profile()
            income = fetcher.fetch_income_statements()
            
            audit_data = {
                'profile': profile.model_dump() if profile else None,
                'income_statements': [s.model_dump() for s in income] if income else []
            }
            self._save_json(audit_data, "fmp_parsed.json", 'parsed')
        except Exception as e:
            logger.warning(f"Failed to audit FMP (Check API Key/Quota): {e}")

    def audit_alphavantage(self):
        """Audit Alpha Vantage Data."""
        logger.info(f"\n--- Auditing Alpha Vantage ({self.symbol}) ---")
        try:
            fetcher = AlphaVantageFetcher(self.symbol)
            profile = fetcher.fetch_profile()
            audit_data = {
                'profile': profile.model_dump() if profile else None
            }
            self._save_json(audit_data, "alphavantage_parsed.json", 'parsed')
        except Exception as e:
            logger.warning(f"Failed to audit AV (Check API Key): {e}")

    def run_pipeline_integration(self):
        """Run the full StockDataLoader pipeline and capture final result."""
        logger.info(f"\n--- Running Full Integrity Pipeline ({self.symbol}) ---")
        try:
            loader = StockDataLoader()
            # This runs the cascade: Yahoo -> Edgar -> FMP -> AV -> Normalize -> TTM
            final_data = loader.get_stock_data(self.symbol)
            
            self._save_json(final_data.model_dump(), "final_merged_pipeline.json", 'merged')
            
            # Generate Completeness Report
            self._generate_completeness_report(final_data)
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")

    def _generate_completeness_report(self, data: StockData):
        """Analyze final data to see where fields came from."""
        report = []
        report.append(f"DATA COMPLETENESS REPORT: {self.symbol}")
        report.append("=" * 50)
        
        # 1. Profile Source
        if data.profile:
            report.append("\n[Company Profile Source Map]")
            for field, val in data.profile.model_dump().items():
                if field.startswith('std_') and val and isinstance(val, dict):
                    src = val.get('source', 'Unknown')
                    v = val.get('value')
                    report.append(f"  {field:<30} : {str(v)[:20]:<20} ({src})")
                    
        # 2. Financial Statements Depth
        report.append(f"\n[Financials Depth]")
        report.append(f"  Income Statements: {len(data.income_statements)}")
        report.append(f"  Balance Sheets   : {len(data.balance_sheets)}")
        report.append(f"  Cash Flows       : {len(data.cash_flows)}")
        
        if data.income_statements:
            latest = data.income_statements[0]
            report.append(f"\n[Latest Income Statement Sample - {latest.std_period}]")
            for field, val in latest.model_dump().items():
                if field.startswith('std_') and val and isinstance(val, dict):
                     src = val.get('source', 'Unknown')
                     v = val.get('value')
                     report.append(f"  {field:<30} : {str(v)[:20]:<20} ({src})")

        # 3. Forecast Data
        if data.forecast_data:
            report.append(f"\n[Forecast Data Source Map]")
            for field, val in data.forecast_data.model_dump().items():
                if field.startswith('std_') and val:
                    if isinstance(val, dict): # FieldWithSource
                        src = val.get('source', 'Unknown')
                        v = val.get('value')
                        report.append(f"  {field:<35} : {str(v)[:20]:<20} ({src})")
                    elif isinstance(val, list): # Special handling for history lists
                        report.append(f"  {field:<35} : {len(val)} records (See parsed/finnhub_forecast.json)")

        self._save_txt(report, "final_provenance_report.txt", 'reports')

    def _save_txt(self, lines: List[str], filename: str, sub_dir: str, header: str = None):
        path = os.path.join(self.dirs[sub_dir], filename)
        with open(path, 'w', encoding='utf-8') as f:
            if header:
                f.write(header + "\n" + "="*len(header) + "\n\n")
            f.write("\n".join(lines))
        logger.info(f"Report: {path}")

    def audit_finnhub(self):
        """Audit Finnhub forecast data using new fetch_forecast_data method."""
        logger.info(f"\n--- Auditing Finnhub Forecast Data ({self.symbol}) ---")
        try:
            fetcher = FinnhubFetcher(self.symbol)
            
            # 1. Fetch using new unified method
            forecast_data = fetcher.fetch_forecast_data()
            
            # 2. Save parsed forecast data
            if forecast_data:
                self._save_json(forecast_data.model_dump(), "finnhub_forecast.json", 'parsed')
            
            # 3. Generate summary report
            summary = []
            summary.append(f"FINNHUB FORECAST DATA: {self.symbol}")
            summary.append("=" * 50)
            
            if forecast_data:
                # Earnings Surprises (Finnhub's unique feature)
                surprises = forecast_data.std_earnings_surprise_history
                if surprises and len(surprises) > 0:
                    summary.append(f"\n{console_symbol.OK} Earnings Surprise History: {len(surprises)} records")
                    # Show latest 3
                    for s in surprises[:3]:
                        summary.append(f"  {s['period']}: Actual={s.get('actual', 0):.2f} vs Est={s.get('estimate', 0):.2f} (Surprise: {s.get('surprisePercent', 0):.1f}%)")
                else:
                    summary.append(f"\n{console_symbol.FAIL} No earnings surprise data")
                
                # EPS/Revenue Estimates
                summary.append("\nEstimates:")
                if forecast_data.std_eps_estimate_current_year:
                    summary.append(f"  {console_symbol.OK} EPS Estimate: {forecast_data.std_eps_estimate_current_year.value:.2f}")
                else:
                    summary.append(f"  {console_symbol.FAIL} EPS Estimate")
                    
                if forecast_data.std_revenue_estimate_current_year:
                    summary.append(f"  {console_symbol.OK} Revenue Estimate: ${forecast_data.std_revenue_estimate_current_year.value:,.0f}")
                else:
                    summary.append(f"  {console_symbol.FAIL} Revenue Estimate")
                    
                if forecast_data.std_ebitda_estimate_next_year:
                    summary.append(f"  {console_symbol.OK} EBITDA Estimate: ${forecast_data.std_ebitda_estimate_next_year.value:,.0f}")
                else:
                    summary.append(f"  {console_symbol.FAIL} EBITDA Estimate")
            else:
                summary.append(f"\n{console_symbol.FAIL} No forecast data available from Finnhub")
            
            self._save_txt(summary, "finnhub_summary.txt", 'reports')
            
        except Exception as e:
            logger.warning(f"Failed to audit Finnhub: {e}")
    
    def audit_fmp_forecast(self):
        """Audit FMP forecast data using new fetch_forecast_data method."""
        logger.info(f"\n--- Auditing FMP Forecast Data ({self.symbol}) ---")
        try:
            fetcher = FMPFetcher(self.symbol)
            
            # Fetch forecast data
            forecast_data = fetcher.fetch_forecast_data()
            
            if forecast_data:
                self._save_json(forecast_data.model_dump(), "fmp_forecast.json", 'parsed')
            
            # Generate summary
            summary = []
            summary.append(f"FMP FORECAST DATA: {self.symbol}")
            summary.append("=" * 50)
            
            if forecast_data:
                # Price Targets
                summary.append("\nPrice Targets:")
                if forecast_data.std_price_target_low:
                    summary.append(f"  Low:  ${forecast_data.std_price_target_low.value:.2f}")
                if forecast_data.std_price_target_high:
                    summary.append(f"  High: ${forecast_data.std_price_target_high.value:.2f}")
                if forecast_data.std_price_target_avg:
                    summary.append(f"  Avg:  ${forecast_data.std_price_target_avg.value:.2f}")
                if forecast_data.std_number_of_analysts:
                    summary.append(f"  Analysts: {forecast_data.std_number_of_analysts.value:.0f}")
                
                # Estimates
                summary.append("\nEstimates:")
                if forecast_data.std_eps_estimate_current_year:
                    summary.append(f"  {console_symbol.OK} EPS: {forecast_data.std_eps_estimate_current_year.value:.2f}")
                if forecast_data.std_revenue_estimate_current_year:
                    summary.append(f"  {console_symbol.OK} Revenue: ${forecast_data.std_revenue_estimate_current_year.value:,.0f}")
                
                # Growth
                summary.append("\nGrowth Estimates:")
                if forecast_data.std_earnings_growth_current_year:
                    summary.append(f"  {console_symbol.OK} Earnings Growth: {forecast_data.std_earnings_growth_current_year.value*100:.1f}%")
                if forecast_data.std_revenue_growth_next_year:
                    summary.append(f"  {console_symbol.OK} Revenue Growth: {forecast_data.std_revenue_growth_next_year.value*100:.1f}%")
            else:
                summary.append(f"\n{console_symbol.FAIL} No forecast data available from FMP")
            
            self._save_txt(summary, "fmp_forecast_summary.txt", 'reports')
            
        except Exception as e:
            logger.warning(f"Failed to audit FMP forecast: {e}")


    def run_full_audit(self):
        """Run all audit steps."""
        logger.info(f"Starting Data Audit for {self.symbol}...")
        logger.info(f"Output Directory: {self.session_dir}")
        
        # Phase 1: Isolation
        self.audit_yahoo()
        self.audit_edgar()
        self.audit_fmp()
        self.audit_alphavantage()
        
        # Phase 1.5: Forecast Data (New - Phase 3)
        logger.info("\n=== FORECAST DATA AUDIT ===")
        self.audit_fmp_forecast()   # FMP forecast data
        self.audit_finnhub()         # Finnhub forecast data
        
        # Phase 2: Integration
        self.run_pipeline_integration()
        
        logger.info(f"\nAudit Complete! Please inspect the 'reports' folder in: \n{self.session_dir}")

if __name__ == "__main__":
    import argparse
    
    # 允许命令行参数，如果没有则交互式输入
    parser = argparse.ArgumentParser(description='Run Data Audit for a Stock Symbol')
    parser.add_argument('symbol', nargs='?', help='Stock symbol to audit')
    args = parser.parse_args()
    
    symbol = args.symbol
    if not symbol:
        symbol = input("Enter stock symbol (e.g., AAPL): ").strip().upper()
    
    if not symbol:
        symbol = "AAPL"
        print("Defaulting to AAPL")
    
    # Run from project root usually
    output_dir = "debug_data"
    
    print(f"\nInitializing Data Auditor for {symbol}...")
    auditor = DataAuditor(symbol, output_dir)
    auditor.run_full_audit()

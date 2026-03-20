import os
import glob
import json
import re
from datetime import datetime
from typing import List

from config.constants import DATA_CACHE_STOCK, DATA_REPORTS
from utils.report_utils import format_financial_score_report, format_technical_score_report

class FastScanReporter:
    """Generates the Fast Scan compiled plaintext report from cached score JSONs."""
    
    @staticmethod
    def _strip_ansi(text: str) -> str:
        if not text:
            return ""
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)

    @staticmethod
    def get_latest_json(cache_dir: str, prefix: str, symbol: str) -> dict:
        pattern = os.path.join(cache_dir, f"{prefix}_{symbol}_*.json")
        files = glob.glob(pattern)
        if not files:
            return {}
        # Sort by modification time to get the latest
        latest_file = max(files, key=os.path.getmtime)
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    @staticmethod
    def generate_report(symbols: List[str], project_root: str):
        cache_dir = os.path.join(project_root, DATA_CACHE_STOCK)
        reports_dir = os.path.join(project_root, DATA_REPORTS)
        os.makedirs(reports_dir, exist_ok=True)
        
        results = []
        
        for symbol in symbols:
            # 1. Load Financial Score
            fin_data = FastScanReporter.get_latest_json(cache_dir, "financial_score", symbol)
            fin_score_dict = fin_data.get('score', {})
            fin_score_val = fin_score_dict.get('total_score', 0)
            
            # 2. Load Technical Score
            tech_data = FastScanReporter.get_latest_json(cache_dir, "technical_score", symbol)
            tech_score_dict = tech_data.get('score', {})
            tech_score_val = tech_score_dict.get('total_score', 0)
            
            if not fin_data and not tech_data:
                continue
                
            # 3. Format detailed sub-reports
            fin_text = FastScanReporter._strip_ansi(format_financial_score_report(fin_score_dict) or "")
            tech_text = FastScanReporter._strip_ansi(format_technical_score_report(tech_score_dict) or "")
            
            full_report_lines = []
            header = f"\n{'='*70}\nREPORT: {symbol}\n{'='*70}\n"
            full_report_lines.append(header)
            
            if fin_text:
                full_report_lines.append(fin_text)
            if fin_text and tech_text:
                full_report_lines.append("-" * 40)
            if tech_text:
                full_report_lines.append(tech_text)
                
            results.append({
                'symbol': symbol,
                'fin_score': fin_score_val,
                'tech_score': tech_score_val,
                'report_text': "\n".join(full_report_lines)
            })

        if not results:
            print("  [WARN] No scoring data found. Cannot generate fast scan report.")
            return

        # Sort by Financial Score Descending
        results.sort(key=lambda x: x['fin_score'], reverse=True)
        
        timestamp_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        report_filename = f"stock_scan_{timestamp_str}.txt"
        report_path = os.path.join(reports_dir, report_filename)
        
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(f"STOCK SCAN REPORT - {timestamp_str}\n")
                f.write(f"Generated at: {datetime.now().strftime('%H:%M:%S')}\n")
                f.write("="*70 + "\n\n")
                
                # Write Summary Table
                f.write("SUMMARY (Sorted by Financial Score)\n")
                f.write("-" * 60 + "\n")
                for res in results:
                    f.write(f"{res['symbol']:<6} : Financial Score - {res['fin_score']:>5.1f} / 100   Technical Score - {res['tech_score']:>3} / 100\n")
                f.write("-" * 60 + "\n\n")
                
                # Write Detailed Reports
                for res in results:
                    f.write(res['report_text'])
                    f.write("\n\n")
                    
            print(f"  [OK] Fast Scan Report saved to: {report_path}")
        except Exception as e:
            print(f"  [ERROR] Failed to write fast scan report file: {e}")

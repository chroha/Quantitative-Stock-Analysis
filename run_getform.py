"""
Organize Data Tool
Aggregates financial, technical, and valuation data for multiple stocks into a single CSV report.
Compatible with AI Commentary data structure.
"""

import sys
import os
import csv
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional

# Setup project root path to import internal modules
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = current_dir if os.path.basename(current_dir) != "Quantitative Stock Analysis V3.0" else current_dir
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fundamentals.ai_commentary.data_aggregator import DataAggregator
from config.constants import DATA_CACHE_STOCK, DATA_REPORTS
from utils.logger import setup_logger

logger = setup_logger('organize_data')

# Define the structure of the report
# Format: (Display Label, Data Path)
# Data Path is dot-separated, e.g. "financial_score.profitability.score"
# If Data Path is None, it's a section header.

REPORT_STRUCTURE = [
    # --- Financial Fundamentals ---
    # Profitability
    ("ROIC Score", "financial_score.profitability.roic.score"),
    ("ROE Score", "financial_score.profitability.roe.score"),
    ("Operating Margin Score", "financial_score.profitability.op_margin.score"),
    ("Gross Margin Score", "financial_score.profitability.gross_margin.score"),
    ("Net Margin Score", "financial_score.profitability.net_margin.score"),

    # Growth
    ("FCF CAGR Score", "financial_score.growth.fcf_cagr.score"),
    ("Net Income CAGR Score", "financial_score.growth.ni_cagr.score"),
    ("Revenue CAGR Score", "financial_score.growth.rev_cagr.score"),
    ("Earnings Quality Score", "financial_score.growth.quality.score"),
    ("FCF/Debt Ratio Score", "financial_score.growth.debt.score"),

    # Capital Allocation
    ("Buyback Yield Score", "financial_score.capital.buyback.score"),
    ("Capex Intensity Score", "financial_score.capital.capex.score"),
    ("SBC Impact Score", "financial_score.capital.sbc.score"),

    # Total Financial
    ("TOTAL FINANCIAL SCORE", "financial_score.total.score"),

    # --- Technical Analysis ---
    # --- Technical Analysis ---
    # Trend
    ("ADX Score", "technical_score.trend.adx.score"),
    ("Multi MA Score", "technical_score.trend.multi_ma.score"),
    ("52W Position Score", "technical_score.trend.52w_pos.score"),

    # Momentum
    ("RSI Score", "technical_score.momentum.rsi.score"),
    ("MACD Score", "technical_score.momentum.macd.score"),
    ("ROC Score", "technical_score.momentum.roc.score"),

    # Volatility
    ("ATR Score", "technical_score.volatility.atr.score"),
    ("Bollinger Score", "technical_score.volatility.bollinger.score"),
    
    # Structure
    ("Resistance Dist Score", "technical_score.structure.resistance.score"),
    ("High/Low Score", "technical_score.structure.high_low.score"),

    # Volume
    ("OBV Score", "technical_score.volume.obv.score"),
    ("Vol Strength Score", "technical_score.volume.vol_strength.score"),

    # Total Technical
    ("TOTAL TECHNICAL SCORE", "technical_score.total.score"),

    # --- Valuation ---
    ("PE Model", "valuation.pe.fair"),
    ("PS Model", "valuation.ps.fair"),
    ("PB Model", "valuation.pb.fair"),
    ("EV/EBITDA Model", "valuation.ev_ebitda.fair"),
    ("PEG Model", "valuation.peg.fair"),
    ("DDM Model", "valuation.ddm.fair"),
    ("DCF Model", "valuation.dcf.fair"),
    ("Graham Model", "valuation.graham.fair"),
    ("Peter Lynch Model", "valuation.lynch.fair"),
    ("Analyst Target", "valuation.analyst.fair"),
    
    # Summary Valuation
    ("Weighted Fair Value", "valuation.fair"),
]

def get_nested_value(data: Dict[str, Any], path: str) -> Any:
    """
    Retrieve value from nested dictionary using dot-notation path.
    Returns '-' if path not found.
    """
    keys = path.split('.')
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return '-'
    
    # Formatting
    if isinstance(current, (int, float)):
        # Heuristic formatting
        if 'margin' in path or 'roic' in path or 'roe' in path or 'cagr' in path or 'yield' in path or 'upside' in path or 'pos' in path or 'atr' in path:
             # Likely percentage (except if value is > 5, likely whole number score, but metrics here are mixed)
             # Our simplified data has 'val' as raw numbers.
             # e.g. ROIC 0.41 -> 41.93%
             # Scores are 0-100 integers.
             # Prices are floats.
             
             # If it looks like a score (path ends in .score or .total.score), format as int
             if path.endswith('.score'):
                 return f"{current:.1f}"
             
             # If it looks like a price or raw value
             return current
             
    return current

def main():
    parser = argparse.ArgumentParser(description="Organize stock data into CSV report.")
    parser.add_argument('symbols', nargs='*', help='Stock symbols (e.g. AAPL MSFT)')
    args = parser.parse_args()
    
    symbols = [s.upper() for s in args.symbols]
    
    if not symbols:
        inp = input("Enter stock symbols to organize (e.g. AAPL MSFT): ").strip()
        if inp:
             symbols = [s.strip().upper() for s in inp.replace(',', ' ').split() if s.strip()]

    if not symbols:
        print("No symbols provided. Exiting.")
        return

    print(f"Organizing data for {len(symbols)} stocks: {', '.join(symbols)}")
    
    # Initialize Aggregator
    aggregator = DataAggregator(data_dir=os.path.join(project_root, DATA_CACHE_STOCK))
    
    # Prepare Data Matrix
    # Columns: Metric Name, Symbol1, Symbol2, ...
    header = ["Metric"] + symbols
    
    # Store data for each symbol
    symbol_data = {}
    
    for symbol in symbols:
        print(f"Loading data for {symbol}...")
        data = aggregator.aggregate(symbol)
        if not data:
            print(f"  [WARN] No data found for {symbol}. Skipping.")
        symbol_data[symbol] = data

    # Build Rows
    rows = []
    
    for label, path in REPORT_STRUCTURE:
        row = [label]
        
        # If section header
        if path is None:
            # Fill rest with empty or dashed
            row.extend([""] * len(symbols))
            rows.append(row)
            continue
            
        for symbol in symbols:
            data = symbol_data.get(symbol)
            if data:
                val = get_nested_value(data, path)
                
                # Format specific values
                if isinstance(val, (int, float)):
                    # Price fields
                    if 'price' in path or 'fair' in path:
                         val = f"${val:.2f}"
                    # Percentage fields (heuristic: val < 5 and not a score)
                    elif ('cagr' in path or 'margin' in path or 'roe' in path or 'roic' in path or 'yield' in path or 'upside' in path or 'pos' in path or 'atr' in path):
                        # Some values in simplified data might already be percentage? 
                        # Looking at data_aggregator, it returns raw values.
                        # Usually < 1.0 for %
                        if abs(val) <= 10.0:  # Assuming not > 1000%
                             val = f"{val*100:.2f}%"
                        else:
                             val = f"{val:.2f}" # Maybe it's a score or large percent
                    elif 'score' in path:
                        val = f"{val:.1f}"
                    else:
                        val = str(val)
                
                row.append(val)
            else:
                row.append("N/A")
        
        rows.append(row)

    # Save CSV
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    report_dir = os.path.join(project_root, DATA_REPORTS)
    if not os.path.exists(report_dir):
        os.makedirs(report_dir, exist_ok=True)
        
    filename = f"collated_scores_{timestamp}.csv"
    filepath = os.path.join(report_dir, filename)
    
    try:
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
            
        print(f"\n[SUCCESS] Report saved to:")
        print(f"  {filepath}")
        
    except Exception as e:
        print(f"\n[ERROR] Failed to save CSV: {e}")

if __name__ == "__main__":
    main()

"""
Valuation Output
Format and display valuation results.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict

from utils.logger import setup_logger

logger = setup_logger('valuation_output')


class ValuationOutput:
    """Handle valuation result formatting and output."""
    
    @staticmethod
    def print_console(valuation_result: dict) -> None:
        """
        Print valuation results to console in formatted style.
        
        Args:
            valuation_result: Dictionary from ValuationCalculator.calculate_valuation()
        """
        ticker = valuation_result['ticker']
        sector = valuation_result.get('sector', 'Unknown')
        current_price = valuation_result.get('current_price')
        weighted_fv = valuation_result.get('weighted_fair_value')
        price_diff = valuation_result.get('price_difference_pct')
        methods = valuation_result.get('method_results', {})
        confidence = valuation_result.get('confidence', {})
        error = valuation_result.get('error')
        
        print("\n" + "="*80)
        print(f"{'VALUATION ANALYSIS':^80}")
        print(f"{ticker} - {sector}".center(80))
        print("="*80)
        
        if error:
            print(f"\n[ERROR]: {error}\n")
            print("="*80 + "\n")
            return
        
        if current_price:
            print(f"\nCurrent Price: ${current_price:.2f}")
        
        if not methods:
            print("\n[WARNING] No valuation methods available")
            print("="*80 + "\n")
            return
        
        print(f"\nValuation Methods (Sorted by Weight):")
        print("-" * 80)
        
        # Sort methods by weight descending
        sorted_methods = sorted(methods.items(), key=lambda item: item[1].get('weight', 0), reverse=True)
        
        for method_name, result in sorted_methods:
            model_name = result['model_name']
            fair_value = result.get('fair_value')
            weight = result.get('weight', 0)
            upside = result.get('upside_pct')
            
            # Handle failed models or missing data
            if fair_value is None or upside is None:
                reason = result.get('reason', 'Unable to calculate')
                if weight > 0:
                    print(f"  {model_name:20s}      N/A   (Weight: {weight*100:>4.0f}%)  [{reason}]")
                else:
                    # If weight is 0 and value is None, likely not applicable (e.g. EV/EBITDA for Banks)
                    status = result.get('status', 'excluded')
                    if status == 'failed':
                         print(f"  {model_name:20s}      N/A   (Weight:   0%)  [{reason}]")
                    else:
                         print(f"  {model_name:20s}      N/A   (Weight:   0%)  [Not used]")
                continue

            # Format upside with color indicators
            upside_str = f"{'+'if upside >= 0 else ''}{upside:.1f}%"
            
            if weight > 0:
                print(f"  {model_name:20s} ${fair_value:>8.2f}  (Weight: {weight*100:>4.0f}%)  [{upside_str:>7s}]")
            else:
                print(f"  {model_name:20s} ${fair_value:>8.2f}  (Weight:   0%)  [Not used]")
        
        print("-" * 80)
        
        if weighted_fv:
            print(f"\nWeighted Fair Value: ${weighted_fv:.2f}")
        
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
            
            print(f"Price Difference: {diff_str} ({assessment})")
        
        if confidence:
            methods_used = confidence.get('methods_used', 0)
            methods_total = confidence.get('methods_available', 0)
            print(f"\nConfidence: {methods_used}/{methods_total} methods available")
        
        print("\n" + "="*80 + "\n")
    
    @staticmethod
    def save_json(valuation_result: dict, output_dir: str = "generated_data") -> Path:
        """
        Save valuation results to JSON file.
        
        Args:
            valuation_result: Dictionary from ValuationCalculator.calculate_valuation()
            output_dir: Directory to save JSON file
            
        Returns:
            Path to saved file
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        ticker = valuation_result['ticker']
        date = datetime.now().strftime("%Y-%m-%d")
        filename = f"valuation_{ticker}_{date}.json"
        filepath = output_path / filename
        
        with open(filepath, 'w') as f:
            json.dump(valuation_result, f, indent=2)
        
        logger.info(f"Valuation results saved to {filepath}")
        return filepath

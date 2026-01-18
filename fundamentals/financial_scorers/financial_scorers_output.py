
"""
Financial Scorers Output Generator.
Orchestrates the scoring process by reading generated financial data and benchmark data,
running the scoring engine, and outputting the final score.
"""

import os
import sys
import json
import glob
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, Any



from utils.logger import setup_logger
from fundamentals.financial_scorers.company_scorer import CompanyScorer
from fundamentals.financial_data import (
    ProfitabilityMetrics,
    GrowthMetrics,
    CapitalAllocationMetrics
)

logger = setup_logger('financial_scorers_output')

class FinancialScorerGenerator:
    """
    Generates financial scores from pre-calculated financial data.
    """
    
    def __init__(self, data_dir: str = "generated_data"):
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            logger.warning(f"Data directory does not exist: {self.data_dir}")
        
    def _find_latest_file(self, pattern: str) -> Optional[Path]:
        """Find the most recent file matching a pattern."""
        files = list(self.data_dir.glob(pattern))
        if not files:
            return None
        # Sort by name (which includes date) usually works for YYYY-MM-DD
        # But let's rely on string sort of the filename which puts dates in order
        files.sort(reverse=True)
        return files[0]

    def _load_json(self, path: Path) -> Dict[str, Any]:
        """Load JSON file."""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def generate(self, symbol: str, quiet: bool = False) -> Optional[str]:
        """
        Generate financial score for a stock.
        
        Args:
            symbol: Stock ticker
            quiet: If True, suppress console output (for use by run_analysis.py)
            
        Returns:
            Path to generated score file or None if failed
        """
        symbol = symbol.upper()
        
        # 1. Find latest financial data for the stock
        # Pattern: financial_data_{SYMBOL}_{DATE}.json
        fin_data_pattern = f"financial_data_{symbol}_*.json"
        fin_data_path = self._find_latest_file(fin_data_pattern)
        
        if not fin_data_path:
            logger.error(f"No financial data found for {symbol}")
            print(f"[ERROR] No financial data file found for {symbol}")
            return None
            
        # 2. Find latest benchmark data
        # Pattern: benchmark_data_{DATE}.json
        # User mentioned: @benchmark_data_2026-01-16.json
        # So pattern is benchmark_data_*.json
        bench_pattern = "benchmark_data_*.json"
        bench_path = self._find_latest_file(bench_pattern)
        
        if not bench_path:
            logger.error("No benchmark data found")
            print("[ERROR] No benchmark data file found")
            return None
            
        logger.info(f"Using financial data: {fin_data_path.name}")
        logger.info(f"Using benchmark data: {bench_path.name}")
        
        try:
            # Load data
            fin_data = self._load_json(fin_data_path)
            bench_data = self._load_json(bench_path)
            
            # 3. Initialize Scorer with loaded benchmarks
            # CompanyScorer takes path to benchmarks, but here we might want to pass data directly?
            # Existing CompanyScorer loads from json path in __init__.
            # We should probably modify CompanyScorer to accept loaded dict OR 
            # we can just pass the path to bench_path!
            
            scorer = CompanyScorer(benchmarks_path=str(bench_path))
            
            # 4. Reconstruct Metric Objects
            # The JSON output from financial_data_output contains dicts, we need to convert back to objects
            # or ensure CompanyScorer handles dicts.
            # Looking at CompanyScorer code:
            # def score_company(self, profitability: ProfitabilityMetrics...
            # It expects specific attributes like profitability.roic.
            # So we must reconstruct the objects.
            
            metrics = fin_data.get('metrics', {})
            meta = fin_data.get('metadata', {})
            sector = meta.get('sector', 'Unknown')
            company_name = meta.get('company_name', symbol) # Assuming name might be there or just use Symbol
            
            # Reconstruct ProfitabilityMetrics
            prof_dict = metrics.get('profitability', {})
            # Filter valid keys (in case JSON has extras)
            # Actually dataclass constructor might handle it if we unpack? 
            # But ProfitabilityMetrics has fields like calculation_date which might be string in JSON.
            # We need to be careful.
            
            prof_metrics = ProfitabilityMetrics()
            for k, v in prof_dict.items():
                if hasattr(prof_metrics, k):
                    setattr(prof_metrics, k, v)
                    
            # Reconstruct GrowthMetrics
            growth_dict = metrics.get('growth', {})
            growth_metrics = GrowthMetrics()
            for k, v in growth_dict.items():
                if hasattr(growth_metrics, k):
                    setattr(growth_metrics, k, v)
                    
            # Reconstruct CapitalAllocationMetrics
            cap_dict = metrics.get('capital_allocation', {})
            cap_metrics = CapitalAllocationMetrics()
            for k, v in cap_dict.items():
                if hasattr(cap_metrics, k):
                    setattr(cap_metrics, k, v)
            
            # 5. Score
            logger.info(f"Scoring {symbol} in sector {sector}...")
            score_result = scorer.score_company(
                profitability=prof_metrics,
                growth=growth_metrics,
                capital_allocation=cap_metrics,
                sector=sector,
                company_name=company_name
            )
            
            # Check for data warnings in metrics (e.g. insufficient history) and attach to score result
            data_warnings = []
            
            # Helper to extract warnings
            def _extract_warnings(metrics_dict):
                warnings = metrics_dict.get('warnings', [])
                for w in warnings:
                    # w is dict here because loaded from JSON
                    if w.get('warning_type') == 'data_insufficient':
                        data_warnings.append(w.get('message'))

            _extract_warnings(metrics.get('growth', {}))
            
            if data_warnings:
                score_result['data_warnings'] = data_warnings
            
            # 6. Save Output
            # financial_score_{stock_code}_{date}.json
            # Use date from fin_data_path to align
            # fin_data_path name format: financial_data_AAPL_2026-01-16.json
            try:
                data_date = fin_data_path.stem.split('_')[-1]
            except:
                data_date = datetime.now().strftime("%Y-%m-%d")
                
            output_filename = f"financial_score_{symbol}_{data_date}.json"
            output_path = self.data_dir / output_filename
            
            # Add metadata about sources
            final_output = {
                "metadata": {
                    "symbol": symbol,
                    "generated_at": datetime.now().isoformat(),
                    "source_financial_data": fin_data_path.name,
                    "source_benchmark_data": bench_path.name,
                    "scoring_version": "3.0"
                },
                "score": score_result
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(final_output, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Saved score to {output_path}")
            if not quiet:
                print(f"[OK] Score generated: {output_path}")
                
                # Print concise summary
                print("-" * 60)
                print("FINANCIAL SCORE SUMMARY")
                print("-" * 60)
                print(f"Total Score: {score_result['total_score']} / 100")
                print("")
                print("Category Breakdown:")
                
                cats = score_result.get('category_scores', {})
                for cat_name, cat_data in cats.items():
                    name = cat_name.replace('_', ' ').title()
                    score = cat_data.get('score', 0)
                    max_pts = cat_data.get('max', 0)
                    print(f"  {name:<20} : {score:>5.1f} / {max_pts}")
                print("-" * 60)
            
            return str(output_path)
            
        except Exception as e:
            logger.exception(f"Failed to score {symbol}")
            print(f"[ERROR] Scoring failed: {e}")
            return None



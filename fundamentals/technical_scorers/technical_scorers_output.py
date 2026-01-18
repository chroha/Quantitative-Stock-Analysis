"""
Technical Scorer Output - Runs the technical analysis scoring and saves results.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from utils.logger import setup_logger
from fundamentals.technical_scorers.technical_scorer import TechnicalScorer

logger = setup_logger('technical_scorers_output')


class TechnicalScorerGenerator:
    """
    Generates technical scores from initial stock data.
    """
    
    def __init__(self, data_dir: str = "generated_data"):
        """
        Initialize generator.
        
        Args:
            data_dir: Directory containing initial_data files
        """
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            logger.warning(f"Data directory does not exist: {self.data_dir}")
    
    def _find_latest_file(self, pattern: str) -> Optional[Path]:
        """
        Find the most recent file matching a pattern.
        
        Args:
            pattern: Glob pattern to match files
            
        Returns:
            Path to latest file or None
        """
        files = list(self.data_dir.glob(pattern))
        if not files:
            return None
        # Sort by filename (includes date) in reverse order
        files.sort(reverse=True)
        return files[0]
    
    def _load_json(self, path: Path) -> Dict[str, Any]:
        """
        Load JSON file.
        
        Args:
            path: Path to JSON file
            
        Returns:
            Loaded JSON data
        """
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def generate(self, symbol: str, quiet: bool = False) -> Optional[str]:
        """
        Generate technical score for a stock symbol.
        
        Args:
            symbol: Stock ticker symbol
            quiet: If True, suppress console output (for use by run_analysis.py)
            
        Returns:
            Path to generated score file or None if failed
        """
        symbol = symbol.upper()
        
        logger.info(f"Starting technical scoring for {symbol}")
        if not quiet:
            print(f"\n{'='*80}")
            print(f"  Generating Technical Analysis Score for {symbol}...")
            print(f"{'='*80}\n")
        
        # Find latest initial_data file for the symbol
        # Pattern: initial_data_{SYMBOL}_{DATE}.json
        data_pattern = f"initial_data_{symbol}_*.json"
        data_path = self._find_latest_file(data_pattern)
        
        if not data_path:
            logger.error(f"No initial data found for {symbol}")
            print(f"[ERROR] Initial data not found for {symbol}")
            print(f"       Please run the data acquisition module first to generate initial_data_{symbol}_*.json")
            return None
        
        logger.info(f"Using data file: {data_path.name}")
        if not quiet:
            print(f"[INFO] Using data file: {data_path.name}")
        
        try:
            # Load initial data
            initial_data = self._load_json(data_path)
            
            # Extract price history
            price_history = initial_data.get('price_history', [])
            
            if not price_history:
                logger.error("No price history found in data file")
                print(f"[ERROR] No price history found in data file")
                return None
            
            logger.info(f"Loaded {len(price_history)} days of price data")
            if not quiet:
                print(f"[INFO] Loaded {len(price_history)} days of price data")
            
            # Initialize scorer
            scorer = TechnicalScorer(price_history)
            
            # Calculate scores
            logger.info("Calculating technical indicators...")
            if not quiet:
                print(f"\n[CALCULATING] Analyzing technical indicators...")
            
            score_result = scorer.calculate_score()
            
            # Check for errors
            if score_result.get('error'):
                logger.error(f"Scoring failed: {score_result.get('message')}")
                print(f"\n[ERROR] {score_result.get('message')}")
                return None
            
            # Print summary
            if not quiet:
                summary = scorer.get_summary(score_result)
                print(f"\n{summary}")
            
            # Prepare output
            # Extract date from data file name
            try:
                # initial_data_AAPL_2026-01-17.json -> 2026-01-17
                data_date = data_path.stem.split('_')[-1]
            except:
                data_date = datetime.now().strftime("%Y-%m-%d")
            
            output_filename = f"technical_score_{symbol}_{data_date}.json"
            output_path = self.data_dir / output_filename
            
            # Build final output
            final_output = {
                "metadata": {
                    "symbol": symbol,
                    "generated_at": datetime.now().isoformat(),
                    "source_data_file": data_path.name,
                    "scoring_version": "1.0"
                },
                "score": score_result
            }
            
            # Save to file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(final_output, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved technical score to {output_path}")
            if not quiet:
                print(f"\n[SUCCESS] Technical score saved: {output_path}")
            
            return str(output_path)
            
        except Exception as e:
            logger.exception(f"Failed to generate technical score for {symbol}")
            print(f"\n[ERROR] Failed to generate technical score: {e}")
            import traceback
            traceback.print_exc()
            return None




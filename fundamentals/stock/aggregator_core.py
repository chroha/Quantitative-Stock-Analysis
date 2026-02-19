"""
Aggregator Core Module
======================

Responsible for locating and loading raw data files for AI commentary generation.
Focuses purely on File I/O and JSON parsing, without formatting logic.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

class AggregatorCore:
    """Core logic for data aggregation (File Finding & Loading)."""
    
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        
    def _load_json(self, file_path: Path) -> Dict[str, Any]:
        """Load JSON data from file."""
        if not file_path.exists():
            return {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
            
    def _find_latest_file(self, pattern: str) -> Optional[Path]:
        """Find the most recent file matching a pattern."""
        files = list(self.data_dir.glob(pattern))
        if not files:
            return None
        files.sort(reverse=True)
        return files[0]

    def load_data_bundle(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Locate and load all relevant data files for a symbol.
        Returns a dictionary containing raw data from all sources.
        """
        symbol = symbol.upper()
        
        # 1. Find Files
        fin_path = self._find_latest_file(f"financial_score_{symbol}_*.json")
        tech_path = self._find_latest_file(f"technical_score_{symbol}_*.json")
        val_path = self._find_latest_file(f"valuation_{symbol}_*.json")
        raw_path = self._find_latest_file(f"initial_data_{symbol}_*.json")
        fin_data_path = self._find_latest_file(f"financial_data_{symbol}_*.json")

        # Check critical files
        if not fin_path or not tech_path or not val_path:
            return None
            
        # 2. Load Data
        bundle = {
            "symbol": symbol,
            "paths": {
                "financial_score": fin_path,
                "technical_score": tech_path,
                "valuation": val_path,
                "initial_data": raw_path,
                "financial_data": fin_data_path
            },
            "data": {
                "financial_score": self._load_json(fin_path),
                "technical_score": self._load_json(tech_path),
                "valuation": self._load_json(val_path),
                "initial_data": self._load_json(raw_path) if raw_path else {},
                "financial_data": self._load_json(fin_data_path) if fin_data_path else {}
            },
            "metadata": {
                "date": fin_path.stem.split('_')[-1]
            }
        }
        
        return bundle

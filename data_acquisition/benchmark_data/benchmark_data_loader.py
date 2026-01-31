"""
Benchmark Data Loader.

Orchestrates the fetching, calculation, and saving of sector benchmark data.
Replaces the old run_benchmark_update.py script.
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# Add project root to sys.path if running independently

from utils.logger import setup_logger
from config.constants import DATA_CACHE_BENCHMARK
from data_acquisition.benchmark_data.damodaran_fetcher import DamodaranFetcher
from data_acquisition.benchmark_data.industry_mapper import SECTOR_MAPPING, get_unmapped_industries
from data_acquisition.benchmark_data.benchmark_calculator import BenchmarkCalculator

logger = setup_logger('benchmark_loader')

class BenchmarkDataLoader:
    """
    Orchestrates the process of fetching raw data, calculating benchmarks,
    and saving them to a JSON file.
    """
    
    def __init__(self):
        self.generated_at = datetime.now().strftime('%Y-%m-%d')
        self.output_dir = Path(DATA_CACHE_BENCHMARK)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def get_output_path(self) -> Path:
        """Get the expected output file path for today."""
        filename = f"benchmark_data_{self.generated_at}.json"
        return self.output_dir / filename
    
    def run_update(self, force_refresh: bool = False) -> Optional[str]:
        """
        Run the full update process.
        
        Args:
            force_refresh: If True, re-download data from web even if cached.
            
        Returns:
            Path to generated JSON file as string, or None if failed.
        """
        logger.info("Starting Benchmark Update Process")
        
        # 1. Fetch Data
        fetcher = DamodaranFetcher()  # Uses DATA_CACHE_BENCHMARK by default
        
        try:
            # Check cache logic if not forced
            if not force_refresh:
                cache_status = fetcher.check_cache_exists()
                if all(cache_status.values()):
                    logger.info("Using cached Damodaran data")
                else:
                    logger.info("Cache incomplete, fetching from web")
                    force_refresh = True
            
            dataframes = fetcher.fetch_all(force_refresh=force_refresh)
            logger.info(f"Fetched {len(dataframes)} datasets")
            print(f"  ✓ Raw files downloaded/verified ({len(dataframes)} datasets)")
            
        except Exception as e:
            logger.error(f"Failed to fetch data: {e}")
            return None
            
        # 2. Key Checks
        if not dataframes:
            logger.error("No dataframes returned")
            return None

        # 3. Initialize Calculator with all DataFrames
        try:
            calculator = BenchmarkCalculator(
                # Existing data sources (for scoring)
                dataframes['roc'],
                dataframes['wacc'],
                dataframes['betas'],
                roe_df=dataframes.get('roe'),
                
                # New valuation multiples data sources
                pbv_df=dataframes.get('pbv'),
                pe_df=dataframes.get('pe'),
                ps_df=dataframes.get('ps'),
                ev_ebitda_df=dataframes.get('ev_ebitda'),
                margins_df=dataframes.get('margins'),
                div_yield_df=dataframes.get('div_yield'),
            )
        except Exception as e:
            logger.error(f"Failed to initialize calculator: {e}")
            return None
            
        # 4. Check Unmapped (Log warning but continue)
        available_industries = set(calculator.roc_df[calculator.ROC_COLUMNS['industry']].unique())
        unmapped = get_unmapped_industries(available_industries)
        if unmapped:
            logger.warning(f"{len(unmapped)} industries not mapped to any sector")
            
        # 5. Aggregate Sectors
        sector_data = {}
        for sector_name, industries in SECTOR_MAPPING.items():
            try:
                data = calculator.aggregate_sector(sector_name, industries)
                if data:
                    sector_data[sector_name] = data
            except Exception as e:
                logger.error(f"Failed to process sector {sector_name}: {e}")
        
        if not sector_data:
            logger.error("No sectors successfully processed")
            return None
            
        logger.info(f"Successfully processed {len(sector_data)}/11 sectors")
        
        # 6. Generate JSON
        output_path = self.get_output_path()
        result = self._save_json(sector_data, output_path)
        if result:
            print(f"  ✓ Benchmark JSON generated: {os.path.basename(result)}")
        return result

    def _save_json(self, sector_data: Dict[str, Dict], output_path: Path) -> str:
        """Generate and save the JSON file."""
        output = {
            'metadata': {
                'version': '3.0-hybrid',
                'generated_at': self.generated_at,
                'source': f'Damodaran_{datetime.now().year}_Jan',
                'description': 'Hybrid scoring: Tier 1 (Synthetic Z-Score), Tier 2 (Mean Multiplier), Tier 3 (Absolute)',
            },
            'defaults': {
                'tier2_multipliers': {
                    'p75_proxy': 1.25,
                    'p25_proxy': 0.75,
                    'p90_proxy': 1.50,
                    'description': 'For metrics without CV data, use mean × multiplier'
                },
                'z_score_params': {
                    'p75': 0.675,
                    'p25': -0.675,
                    'p90': 1.282,
                    'p10': -1.282,
                    'description': 'Standard normal distribution Z-scores for percentiles'
                },
                'tier3_growth_thresholds': {
                    'cagr_excellent': 0.20,
                    'cagr_good': 0.15,
                    'cagr_ok': 0.10,
                    'cagr_weak': 0.05,
                    'cagr_poor': 0.00,
                    'description': 'Absolute thresholds for growth metrics'
                }
            },
            'sectors': sector_data
        }
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved benchmark data to {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"Failed to save JSON: {e}")
            return None

    def validate_structure(self, json_path: str) -> bool:
        """Validate generated JSON structure."""
        try:
            with open(json_path, encoding='utf-8') as f:
                data = json.load(f)
            
            # Simple check for key components
            if 'sectors' not in data or len(data['sectors']) == 0:
                logger.error("Validation Failed: No sectors found")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Validation Error: {e}")
            return False



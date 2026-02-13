"""
Valuation Calculator
Main engine for coordinating multiple valuation methods with sector-specific weights.
"""

import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

from utils.unified_schema import StockData
from utils.logger import setup_logger
from .valuation_config import get_sector_weights
from .valuation_models.base_model import BaseValuationModel
from .valuation_models.pe_valuation import PEValuationModel
from .valuation_models.pb_valuation import PBValuationModel
from .valuation_models.ps_valuation import PSValuationModel
from .valuation_models.ev_valuation import EVValuationModel
from .valuation_models.analyst_targets import AnalystTargetsModel
from .valuation_models.dcf_model import DCFModel
from .valuation_models.dcf_model import DCFModel
from .valuation_models.ddm_model import DDMModel
from .valuation_models.graham_model import GrahamNumberModel
from .valuation_models.peter_lynch_model import PeterLynchModel

logger = setup_logger('valuation_calculator')

# Sector name normalization (same as company_scorer)
# Different data sources use different sector naming conventions
SECTOR_ALIASES = {
    'Consumer Cyclical': 'Consumer Discretionary',  # Yahoo Finance convention
    'Consumer Defensive': 'Consumer Staples',        # Yahoo Finance convention
}

def normalize_sector(sector: str) -> str:
    """Normalize sector name to GICS standard classification."""
    return SECTOR_ALIASES.get(sector, sector)



class ValuationCalculator:
    """
    Main valuation engine.
    
    Coordinates multiple valuation models and applies sector-specific weights
    to produce a weighted fair value estimate.
    """
    
    def __init__(self, benchmark_data_path: str):
        """
        Initialize valuation calculator.
        
        Args:
            benchmark_data_path: Directory containing benchmark_data.json (required)
        """
        self.benchmark_data = self._load_benchmark_data(benchmark_data_path)
        self.models = self._initialize_models()
        logger.info("Valuation calculator initialized")
    
    def _load_benchmark_data(self, data_dir: str) -> dict:
        """Load industry benchmark data from Damodaran."""
        data_path = Path(data_dir)
        
        # Find most recent benchmark file
        benchmark_files = list(data_path.glob("benchmark_data_*.json"))
        if not benchmark_files:
            raise FileNotFoundError(f"No benchmark data found in {data_dir}")
        
        # Use most recent file
        latest_file = max(benchmark_files, key=lambda p: p.stat().st_mtime)
        logger.info(f"Loading benchmark data from {latest_file}")
        
        with open(latest_file, 'r') as f:
            return json.load(f)
    
    def _initialize_models(self) -> Dict[str, BaseValuationModel]:
        """Initialize all valuation models."""
        from .valuation_models.peg_model import PEGValuationModel
        
        return {
            'pe': PEValuationModel(),
            'pb': PBValuationModel(),
            'ps': PSValuationModel(),
            'ev_ebitda': EVValuationModel(),
            'analyst': AnalystTargetsModel(),
            'dcf': DCFModel(),
            'ddm': DDMModel(),
            'graham': GrahamNumberModel(),
            'peter_lynch': PeterLynchModel(),
            'peg': PEGValuationModel(),
        }
    
    def calculate_valuation(self, stock_data: StockData) -> dict:
        """
        Calculate comprehensive valuation for a stock.
        
        Args:
            stock_data: Complete stock data object
            
        Returns:
            Valuation results dictionary with:
            - ticker
            - sector
            - current_price
            - method_results: dict of {method: {fair_value, weight, upside_pct}}
            - weighted_fair_value
            - price_difference_pct (negative if overvalued)
            - valuation_date
        """
        try:
            # Get sector and current price
            if not stock_data.profile or not stock_data.profile.std_sector:
                logger.error(f"{stock_data.symbol}: No sector information")
                return self._error_result(stock_data.symbol, "No sector information")
            
            sector = stock_data.profile.std_sector.value
            
            # Normalize sector name (e.g., "Consumer Cyclical" -> "Consumer Discretionary")
            normalized_sector = normalize_sector(sector)
            
            if not stock_data.price_history:
                logger.error(f"{stock_data.symbol}: No price history")
                return self._error_result(stock_data.symbol, "No price history", sector=sector)
            
            current_price = stock_data.price_history[-1].std_close.value
            
            logger.info(f"\n{'='*80}")
            logger.info(f"Calculating valuation for {stock_data.symbol} ({sector} -> {normalized_sector})")
            logger.info(f"Current Price: ${current_price:.2f}")
            logger.info(f"{'='*80}")
            
            # Get sector-specific weights (use normalized sector)
            weights = get_sector_weights(normalized_sector)
            if not weights:
                logger.error(f"No valuation weights defined for sector: {sector} (normalized: {normalized_sector})")
                return self._error_result(stock_data.symbol, f"Unsupported sector: {sector}", 
                                         sector=sector, current_price=current_price)
            
            # Calculate each applicable method
            method_results = {}
            total_weight = 0
            weighted_sum = 0
            weighted_methods_count = 0
            
            # Iterate through ALL available models, not just configured weights
            for method_name, model in self.models.items():
                # Get weight from config, default to 0.0 if not defined
                weight = weights.get(method_name, 0.0)
                
                # Calculate fair value for this method
                fair_value = None
                failure_reason = 'Unable to calculate'
                
                try:
                    # Pass normalized sector to valuation models for benchmark lookup
                    fair_value = model.calculate_fair_value(
                        stock_data, 
                        self.benchmark_data, 
                        normalized_sector  # Use normalized sector for benchmark queries
                    )
                except ValueError as e:
                    failure_reason = str(e)
                    logger.warning(f"  {model.get_model_display_name()}: {failure_reason}")
                except Exception as e:
                    failure_reason = f"Error: {str(e)}"
                    logger.error(f"  {model.get_model_display_name()} failed with error: {e}")
                
                if fair_value is not None and fair_value > 0:
                    upside_pct = ((fair_value - current_price) / current_price) * 100
                    
                    method_results[method_name] = {
                        'model_name': model.get_model_display_name(),
                        'fair_value': round(fair_value, 2),
                        'weight': weight,
                        'upside_pct': round(upside_pct, 2),
                        'status': 'success'
                    }
                    
                    # Special handling for EV/EBITDA to include industry multiple
                    if method_name == 'ev_ebitda':
                        try:
                            sector_benchmarks = self.benchmark_data.get('sectors', {}).get(sector, {})
                            industry_multiple = sector_benchmarks.get('metrics', {}).get('valuation_multiples', {}).get('ev_ebitda')
                            if industry_multiple:
                                method_results[method_name]['industry_multiple'] = industry_multiple
                        except Exception:
                            pass # Fail silently if structure differs, not critical
                    
                    if weight > 0:
                        weighted_sum += fair_value * weight
                        total_weight += weight
                        weighted_methods_count += 1
                        logger.info(f"  {model.get_model_display_name()}: ${fair_value:.2f} (Weight: {weight*100:.0f}%) [{'+'if upside_pct>=0 else ''}{upside_pct:.1f}%]")
                    else:
                        logger.info(f"  {model.get_model_display_name()}: ${fair_value:.2f} (Weight: 0%) [Excluded from Weighted Avg]")
                else:
                    # Still include failed models in results so they appear in report
                    method_results[method_name] = {
                        'model_name': model.get_model_display_name(),
                        'fair_value': None,
                        'weight': weight,
                        'upside_pct': None,
                        'status': 'failed',
                        'reason': failure_reason
                    }
                    if not fair_value: # Don't log again if we already logged exception
                         logger.warning(f"  {model.get_model_display_name()}: {failure_reason}")
            
            # Check if we have enough methods
            if total_weight == 0 or len(method_results) < 2:
                logger.error(f"Insufficient valuation methods available ({len(method_results)} methods)")
                return {
                    'ticker': stock_data.symbol,
                    'sector': sector,
                    'current_price': current_price,
                    'method_results': method_results,
                    'weighted_fair_value': None,
                    'price_difference_pct': None,
                    'error': 'Insufficient data for valuation',
                    'valuation_date': datetime.now().strftime('%Y-%m-%d')
                }
            
            # Calculate normalized weighted fair value
            weighted_fair_value = weighted_sum / total_weight
            
            # Price difference (negative if overvalued)
            price_diff_pct = ((weighted_fair_value - current_price) / current_price) * 100
            
            logger.info(f"\n{'-'*80}")
            logger.info(f"Weighted Fair Value: ${weighted_fair_value:.2f}")
            logger.info(f"Price Difference: {'+'if price_diff_pct>=0 else ''}{price_diff_pct:.1f}%")
            logger.info(f"Confidence: {weighted_methods_count}/{len(weights)} methods available")
            logger.info(f"{'='*80}\n")
            
            return {
                'ticker': stock_data.symbol,
                'sector': sector,
                'current_price': round(current_price, 2),
                'method_results': method_results,
                'weighted_fair_value': round(weighted_fair_value, 2),
                'price_difference_pct': round(price_diff_pct, 2),
                'confidence': {
                    'methods_used': weighted_methods_count,
                    'methods_available': len(weights),
                    'total_weight_used': round(total_weight, 2)
                },
                'valuation_date': datetime.now().strftime('%Y-%m-%d')
            }
            
        except Exception as e:
            logger.exception(f"Valuation calculation failed for {stock_data.symbol}")
            return self._error_result(stock_data.symbol, str(e))
    
    def _error_result(self, ticker: str, error_msg: str, sector: str = None, current_price: float = None) -> dict:
        """Create error result dictionary."""
        return {
            'ticker': ticker,
            'sector': sector,
            'current_price': current_price,
            'method_results': {},
            'weighted_fair_value': None,
            'price_difference_pct': None,
            'error': error_msg,
            'valuation_date': datetime.now().strftime('%Y-%m-%d')
        }

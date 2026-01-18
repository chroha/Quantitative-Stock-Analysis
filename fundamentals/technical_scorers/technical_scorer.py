"""
Main Technical Scorer.
Orchestrates all technical indicator calculations and generates comprehensive scores.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime

from .trend_indicators import TrendIndicators
from .momentum_indicators import MomentumIndicators
from .volatility_indicators import VolatilityIndicators
from .price_structure_indicators import PriceStructureIndicators
from .volume_indicators import VolumeIndicators
from .scoring_config import CATEGORY_WEIGHTS, MIN_DATA_POINTS


class TechnicalScorer:
    """
    Main technical analysis scorer.
    Coordinates all indicator calculations and generates final score.
    """
    
    def __init__(self, price_data: list):
        """
        Initialize with price history data.
        
        Args:
            price_data: List of price records from initial_data JSON
        """
        self.price_data = price_data
        self.df = self._prepare_dataframe()
    
    def _prepare_dataframe(self) -> pd.DataFrame:
        """
        Convert price data from JSON format to pandas DataFrame.
        
        Returns:
            DataFrame with columns: date, open, high, low, close, volume
        """
        records = []
        
        for entry in self.price_data:
            try:
                record = {
                    'date': entry.get('std_date', ''),
                    'open': entry.get('std_open', {}).get('value', np.nan),
                    'high': entry.get('std_high', {}).get('value', np.nan),
                    'low': entry.get('std_low', {}).get('value', np.nan),
                    'close': entry.get('std_close', {}).get('value', np.nan),
                    'volume': entry.get('std_volume', {}).get('value', np.nan)
                }
                records.append(record)
            except Exception:
                continue
        
        df = pd.DataFrame(records)
        
        # Remove rows with missing critical data
        df = df.dropna(subset=['date', 'close'])
        
        # Convert date to datetime (handle timezone-aware dates)
        df['date'] = pd.to_datetime(df['date'], utc=True)
        # Convert to timezone-naive for calculations
        df['date'] = df['date'].dt.tz_localize(None)
        
        # Sort by date
        df = df.sort_values('date').reset_index(drop=True)
        
        return df
    
    def calculate_score(self) -> Dict[str, Any]:
        """
        Calculate comprehensive technical score.
        
        Returns:
            Dict with category scores, total score, and detailed breakdown
        """
        # Check data sufficiency
        if len(self.df) < MIN_DATA_POINTS:
            return {
                'error': True,
                'message': f'Insufficient data for technical analysis. Need at least {MIN_DATA_POINTS} days, got {len(self.df)}',
                'total_score': 0,
                'categories': {}
            }
        
        # Calculate all indicator categories
        trend_calc = TrendIndicators(self.df)
        trend_results = trend_calc.calculate_all()
        
        momentum_calc = MomentumIndicators(self.df)
        momentum_results = momentum_calc.calculate_all()
        
        volatility_calc = VolatilityIndicators(self.df)
        volatility_results = volatility_calc.calculate_all()
        
        structure_calc = PriceStructureIndicators(self.df)
        structure_results = structure_calc.calculate_all()
        
        volume_calc = VolumeIndicators(self.df)
        volume_results = volume_calc.calculate_all()
        
        # Aggregate results
        categories = {
            'trend_strength': trend_results,
            'momentum': momentum_results,
            'volatility': volatility_results,
            'price_structure': structure_results,
            'volume_price': volume_results
        }
        
        # Calculate total score
        total_score = sum(cat['earned_points'] for cat in categories.values())
        max_total = sum(cat['max_points'] for cat in categories.values())
        

        
        # Get latest price info
        latest_price = self.df['close'].iloc[-1]
        latest_date = self.df['date'].iloc[-1]
        
        return {
            'error': False,
            'total_score': round(total_score, 2),
            'max_score': max_total,
            'score_percentage': round((total_score / max_total) * 100, 1),
            'categories': categories,
            'data_info': {
                'total_days': len(self.df),
                'date_range': {
                    'start': self.df['date'].iloc[0].isoformat(),
                    'end': latest_date.isoformat()
                },
                'latest_price': round(latest_price, 2)
            }
        }
    

    
    def get_summary(self, score_result: Dict[str, Any]) -> str:
        """
        Generate a concise summary of the scoring results.
        
        Args:
            score_result: Result from calculate_score()
            
        Returns:
            Formatted summary string
        """
        if score_result.get('error'):
            return f"ERROR: {score_result.get('message')}"
        
        lines = []
        lines.append("-" * 60)
        lines.append("TECHNICAL SCORE SUMMARY")
        lines.append("-" * 60)
        lines.append(f"Total Score: {score_result['total_score']:.1f} / {score_result['max_score']}")
        lines.append(f"Data Points: {score_result['data_info']['total_days']} days")
        lines.append("")
        
        lines.append("Category Breakdown:")
        
        for cat_name, cat_data in score_result['categories'].items():
            name = cat_data['category'].replace('_', ' ').title()
            score = cat_data['earned_points']
            max_pts = cat_data['max_points']
            lines.append(f"  {name:<20} : {score:>5.1f} / {max_pts}")
            
        lines.append("-" * 60)
        
        return "\n".join(lines)

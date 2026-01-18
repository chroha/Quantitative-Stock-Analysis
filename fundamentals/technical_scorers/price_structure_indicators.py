"""
Price Structure Indicators.
Implements Support/Resistance and High/Low Structure pattern analysis.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple
from .scoring_config import (
    STRUCTURE_WEIGHTS, SUPPORT_RESISTANCE_CONFIG, HIGH_LOW_CONFIG
)


class PriceStructureIndicators:
    """Calculator for price structure indicators."""
    
    def __init__(self, df: pd.DataFrame):
        """
        Initialize with price data.
        
        Args:
            df: DataFrame with columns: date, open, high, low, close, volume
        """
        self.df = df.copy()
        self.df['date'] = pd.to_datetime(self.df['date'], utc=True).dt.tz_localize(None)
        self.df = self.df.sort_values('date').reset_index(drop=True)
    
    def calculate_all(self) -> Dict[str, Any]:
        """Calculate all price structure indicators and return scores."""
        results = {
            'category': 'price_structure',
            'max_points': sum(STRUCTURE_WEIGHTS.values()),
            'earned_points': 0,
            'indicators': {}
        }
        
        sr_result = self.calculate_support_resistance()
        hl_result = self.calculate_high_low_structure()
        
        results['indicators']['support_resistance'] = sr_result
        results['indicators']['high_low_structure'] = hl_result
        
        results['earned_points'] = (
            sr_result['score'] +
            hl_result['score']
        )
        
        return results
    
    def _find_pivot_points(self, window: int = 5) -> Tuple[List[int], List[int]]:
        """
        Find local highs and lows (pivot points).
        
        Args:
            window: Window size for pivot detection
            
        Returns:
            Tuple of (high_indices, low_indices)
        """
        df = self.df
        highs = []
        lows = []
        
        for i in range(window, len(df) - window):
            # Check if this is a local high
            if df['high'].iloc[i] == df['high'].iloc[i-window:i+window+1].max():
                highs.append(i)
            
            # Check if this is a local low
            if df['low'].iloc[i] == df['low'].iloc[i-window:i+window+1].min():
                lows.append(i)
        
        return highs, lows
    
    def calculate_support_resistance(self) -> Dict[str, Any]:
        """
        Calculate Support/Resistance strength score.
        
        Returns:
            Dict with score and key levels
        """
        lookback = SUPPORT_RESISTANCE_CONFIG['lookback_period']
        
        if len(self.df) < lookback:
            return {
                'score': 0,
                'max_score': STRUCTURE_WEIGHTS['support_resistance'],
                'nearest_support': None,
                'nearest_resistance': None,
                'explanation': 'Insufficient data for S/R analysis'
            }
        
        recent_df = self.df.tail(lookback).reset_index(drop=True)
        current_price = recent_df['close'].iloc[-1]
        
        # Find pivot points
        high_indices, low_indices = self._find_pivot_points(window=3)
        
        # Collect resistance levels (highs above current price)
        resistance_levels = []
        for idx in high_indices:
            if idx < len(recent_df):
                high_price = recent_df['high'].iloc[idx]
                if high_price > current_price:
                    resistance_levels.append(high_price)
        
        # Collect support levels (lows below current price)
        support_levels = []
        for idx in low_indices:
            if idx < len(recent_df):
                low_price = recent_df['low'].iloc[idx]
                if low_price < current_price:
                    support_levels.append(low_price)
        
        # Find nearest levels
        nearest_resistance = min(resistance_levels) if resistance_levels else None
        nearest_support = max(support_levels) if support_levels else None
        
        # Calculate distances as percentage
        if nearest_resistance:
            resistance_dist = ((nearest_resistance - current_price) / current_price) * 100
        else:
            resistance_dist = None
        
        if nearest_support:
            support_dist = ((current_price - nearest_support) / current_price) * 100
        else:
            support_dist = None
        
        # Score based on distances
        score = 0
        explanation = ""
        
        # Handle cases where support/resistance not found
        # Handle cases where support/resistance not found
        if support_dist is None and resistance_dist is None:
            score = 4
            explanation = "Neutral Position (No Clear S/R)"
        elif support_dist is None:
            # No support found (price at/near lows)
            if resistance_dist and resistance_dist < 2:
                score = 2
                explanation = f"Near Resistance ({resistance_dist:.1f}%), No Support"
            else:
                score = 3
                explanation = "At Lows, No Support"
        elif resistance_dist is None:
            # No resistance found (price at/near highs)
            if support_dist and support_dist > 5:
                score = 8
                explanation = f"Breakout (Support {support_dist:.1f}%), No Resistance"
            elif support_dist and support_dist > 3:
                score = 6
                explanation = f"Strong Support ({support_dist:.1f}%), No Resistance"
            else:
                score = 4
                explanation = "At Highs, No Resistance"
        else:
            # Both support and resistance found
            if support_dist > 5 and resistance_dist > 5:
                score = 8
                explanation = f"Safe Zone (Supp>{support_dist:.1f}%, Res>{resistance_dist:.1f}%)"
            elif support_dist > 3:
                score = 6
                explanation = f"Strong Support (Supp {support_dist:.1f}%, Res {resistance_dist:.1f}%)"
            elif resistance_dist < 2:
                score = 2
                explanation = f"Near Resistance (Res {resistance_dist:.1f}%, Supp {support_dist:.1f}%)"
            elif support_dist < 0:  # Broken below support
                score = 0
                explanation = f"Support Broken ({abs(support_dist):.1f}%)"
            else:
                score = 4
                explanation = f"Neutral Position (Supp {support_dist:.1f}%, Res {resistance_dist:.1f}%)"
        
        return {
            'score': score,
            'max_score': STRUCTURE_WEIGHTS['support_resistance'],
            'current_price': round(current_price, 2),
            'nearest_support': round(nearest_support, 2) if nearest_support else None,
            'nearest_resistance': round(nearest_resistance, 2) if nearest_resistance else None,
            'support_distance_pct': round(support_dist, 2) if nearest_support else None,
            'resistance_distance_pct': round(resistance_dist, 2) if nearest_resistance else None,
            'explanation': explanation
        }
    
    def calculate_high_low_structure(self) -> Dict[str, Any]:
        """
        Calculate High/Low structure (Dow Theory) score.
        
        Returns:
            Dict with score and pattern description
        """
        short_period = HIGH_LOW_CONFIG['short_period']
        long_period = HIGH_LOW_CONFIG['long_period']
        
        if len(self.df) < long_period:
            return {
                'score': 0,
                'max_score': STRUCTURE_WEIGHTS['high_low_structure'],
                'pattern': None,
                'explanation': 'Insufficient data for structure analysis'
            }
        
        df = self.df.copy()
        
        # Find recent highs and lows
        short_df = df.tail(short_period)
        long_df = df.tail(long_period)
        
        # Identify swing highs and lows
        def find_swings(data: pd.DataFrame, window: int = 5):
            """Find swing highs and lows."""
            highs = []
            lows = []
            
            for i in range(window, len(data) - window):
                if data['high'].iloc[i] == data['high'].iloc[i-window:i+window+1].max():
                    highs.append((i, data['high'].iloc[i]))
                if data['low'].iloc[i] == data['low'].iloc[i-window:i+window+1].min():
                    lows.append((i, data['low'].iloc[i]))
            
            return highs, lows
        
        swing_highs, swing_lows = find_swings(long_df, window=3)
        
        # Analyze pattern
        score = 0
        pattern = ""
        
        if len(swing_highs) >= 2 and len(swing_lows) >= 2:
            # Check for higher highs
            recent_highs = sorted(swing_highs, key=lambda x: x[0])[-2:]
            higher_high = recent_highs[-1][1] > recent_highs[-2][1]
            
            # Check for higher lows
            recent_lows = sorted(swing_lows, key=lambda x: x[0])[-2:]
            higher_low = recent_lows[-1][1] > recent_lows[-2][1]
            
            # Check for lower lows
            lower_low = recent_lows[-1][1] < recent_lows[-2][1]
            
            if higher_high and higher_low:
                # Perfect uptrend - check if pullbacks are shallow
                max_pullback = 0
                for i in range(len(df)):
                    if i > 0:
                        pullback_pct = ((df['high'].iloc[:i+1].max() - df['low'].iloc[i]) / 
                                       df['high'].iloc[:i+1].max()) * 100
                        max_pullback = max(max_pullback, pullback_pct)
                
                if max_pullback < 15:  # Shallow pullbacks
                    score = HIGH_LOW_CONFIG['scores']['perfect_uptrend']
                    pattern = "Higher Highs + Shallow Pullbacks (Perfect Uptrend)"
                else:
                    score = HIGH_LOW_CONFIG['scores']['uptrend_unstable']
                    pattern = "Higher Highs + Deep Pullbacks (Volatile Uptrend)"
            
            elif lower_low:
                score = HIGH_LOW_CONFIG['scores']['downtrend']
                pattern = "Lower Lows (Downtrend)"
            
            else:
                score = HIGH_LOW_CONFIG['scores']['consolidation']
                pattern = "Consolidation (No Clear Trend)"
        
        else:
            # Not enough swing points
            # Check simple trend
            recent_high = df['high'].tail(short_period).max()
            overall_high = df['high'].tail(long_period).max()
            
            if recent_high >= overall_high * 0.99:  # Near highs
                score = HIGH_LOW_CONFIG['scores']['uptrend_unstable']
                pattern = "Near Highs"
            else:
                score = HIGH_LOW_CONFIG['scores']['consolidation']
                pattern = "Consolidating"
        
        return {
            'score': score,
            'max_score': STRUCTURE_WEIGHTS['high_low_structure'],
            'pattern': pattern,
            'swing_highs_count': len(swing_highs),
            'swing_lows_count': len(swing_lows),
            'explanation': pattern
        }

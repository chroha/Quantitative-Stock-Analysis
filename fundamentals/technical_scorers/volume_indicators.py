"""
Volume-Price Relationship Indicators.
Implements OBV and Volume Strength scoring.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
from .scoring_config import (
    VOLUME_WEIGHTS, OBV_CONFIG, VOLUME_STRENGTH_CONFIG
)


class VolumeIndicators:
    """Calculator for volume-price relationship indicators."""
    
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
        """Calculate all volume indicators and return scores."""
        results = {
            'category': 'volume_price',
            'max_points': sum(VOLUME_WEIGHTS.values()),
            'earned_points': 0,
            'indicators': {}
        }
        
        obv_result = self.calculate_obv()
        volume_result = self.calculate_volume_strength()
        
        results['indicators']['obv'] = obv_result
        results['indicators']['volume_strength'] = volume_result
        
        results['earned_points'] = (
            obv_result['score'] +
            volume_result['score']
        )
        
        return results
    
    def calculate_obv(self) -> Dict[str, Any]:
        """
        Calculate OBV (On-Balance Volume) score.
        
        Returns:
            Dict with score and OBV details
        """
        period = OBV_CONFIG['trend_period']
        
        if len(self.df) < period + 5:
            return {
                'score': 0,
                'max_score': VOLUME_WEIGHTS['obv'],
                'obv': None,
                'explanation': 'Insufficient data for OBV'
            }
        
        df = self.df.copy()
        
        # Calculate OBV
        df['price_change'] = df['close'].diff()
        df['obv'] = 0.0
        
        # Initialize OBV
        obv_values = [0]
        for i in range(1, len(df)):
            if df['price_change'].iloc[i] > 0:
                obv_values.append(obv_values[-1] + df['volume'].iloc[i])
            elif df['price_change'].iloc[i] < 0:
                obv_values.append(obv_values[-1] - df['volume'].iloc[i])
            else:
                obv_values.append(obv_values[-1])
        
        df['obv'] = obv_values
        
        # Calculate OBV trend
        recent_obv = df['obv'].tail(period)
        obv_slope = (recent_obv.iloc[-1] - recent_obv.iloc[0]) / period
        
        # Normalize slope
        avg_obv = recent_obv.mean()
        if avg_obv != 0:
            obv_slope_normalized = obv_slope / abs(avg_obv)
        else:
            obv_slope_normalized = 0
        
        # Check price trend
        recent_prices = df['close'].tail(period)
        price_rising = recent_prices.iloc[-1] > recent_prices.iloc[0]
        obv_rising = recent_obv.iloc[-1] > recent_obv.iloc[0]
        
        # Alignment score
        alignment_score = 0
        alignment_status = ""
        
        if obv_rising and price_rising:
            alignment_score = OBV_CONFIG['alignment_scores']['both_rising']
            alignment_status = "Price & Vol Rising (Best)"
        elif price_rising and not obv_rising:
            # Check if OBV is flat
            obv_change_pct = abs(recent_obv.iloc[-1] - recent_obv.iloc[0]) / abs(recent_obv.iloc[0]) if recent_obv.iloc[0] != 0 else 0
            if obv_change_pct < 0.05:
                alignment_score = OBV_CONFIG['alignment_scores']['price_up_obv_flat']
                alignment_status = "Price Up/Vol Flat (Caution)"
            else:
                alignment_score = OBV_CONFIG['alignment_scores']['divergence']
                alignment_status = "Divergence (Risk)"
        else:
            alignment_score = 0
            alignment_status = "Price Falling"
        
        # Trend strength bonus
        trend_score = 0
        if obv_slope_normalized > OBV_CONFIG['trend_threshold']:
            trend_score = OBV_CONFIG['trend_bonus']
            trend_status = "OBV Strong Uptrend"
        else:
            trend_status = "OBV Neutral/Weak"
        
        total_score = alignment_score + trend_score
        
        return {
            'score': total_score,
            'max_score': VOLUME_WEIGHTS['obv'],
            'obv': int(df['obv'].iloc[-1]),
            'obv_slope': round(obv_slope_normalized, 6),
            'alignment_score': alignment_score,
            'trend_score': trend_score,
            'explanation': f"{alignment_status}, {trend_status}"
        }
    
    def calculate_volume_strength(self) -> Dict[str, Any]:
        """
        Calculate Volume Strength score.
        
        Returns:
            Dict with score and volume ratio
        """
        period = VOLUME_STRENGTH_CONFIG['period']
        
        if len(self.df) < period + 1:
            return {
                'score': 0,
                'max_score': VOLUME_WEIGHTS['volume_strength'],
                'volume_ratio': None,
                'explanation': 'Insufficient data for volume analysis'
            }
        
        df = self.df.copy()
        
        # Calculate average volume
        df['avg_volume'] = df['volume'].rolling(window=period).mean()
        
        latest = df.iloc[-1]
        current_volume = latest['volume']
        avg_volume = latest['avg_volume']
        
        if avg_volume == 0:
            volume_ratio = 1.0
        else:
            volume_ratio = current_volume / avg_volume
        
        # Ratio score
        ratio_score = 0
        for threshold, score in sorted(VOLUME_STRENGTH_CONFIG['ratio_scores'].items(), reverse=True):
            if volume_ratio >= threshold:
                ratio_score = score
                break
        
        if volume_ratio >= 2.0:
            ratio_status = "High Volume"
        elif volume_ratio >= 1.5:
            ratio_status = "Moderate High Volume"
        elif volume_ratio >= 1.0:
            ratio_status = "Normal"
        elif volume_ratio >= 0.5:
            ratio_status = "Low Volume"
        else:
            ratio_status = "Extremely Low Volume"
        
        # Alignment score (volume vs price)
        alignment_score = 0
        alignment_status = ""
        
        # Check price change
        if len(df) >= 2:
            price_change = df['close'].iloc[-1] - df['close'].iloc[-2]
            price_up = price_change > 0
            
            if volume_ratio >= 1.5 and price_up:
                alignment_score = VOLUME_STRENGTH_CONFIG['alignment_scores']['high_vol_price_up']
                alignment_status = "High Vol Uptrend (Best)"
            elif volume_ratio < 1.5 and price_up:
                alignment_score = VOLUME_STRENGTH_CONFIG['alignment_scores']['low_vol_price_up']
                alignment_status = "Low Vol Uptrend (Normal)"
            elif volume_ratio >= 1.5 and not price_up:
                alignment_score = VOLUME_STRENGTH_CONFIG['alignment_scores']['high_vol_price_down']
                alignment_status = "High Vol Downtrend (Panic)"
            else:
                alignment_score = 0
                alignment_status = "Low Vol Downtrend"
        
        total_score = ratio_score + alignment_score
        
        return {
            'score': total_score,
            'max_score': VOLUME_WEIGHTS['volume_strength'],
            'volume_ratio': round(volume_ratio, 2),
            'current_volume': int(current_volume),
            'avg_volume': int(avg_volume),
            'ratio_score': ratio_score,
            'alignment_score': alignment_score,
            'explanation': f"Vol Ratio={volume_ratio:.2f} ({ratio_status}), {alignment_status}"
        }

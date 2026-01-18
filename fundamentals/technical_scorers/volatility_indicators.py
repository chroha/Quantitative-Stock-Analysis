"""
Volatility Indicators.
Implements ATR and Bollinger Bands scoring.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
from .scoring_config import (
    VOLATILITY_WEIGHTS, ATR_CONFIG, BOLLINGER_CONFIG
)


class VolatilityIndicators:
    """Calculator for volatility indicators."""
    
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
        """Calculate all volatility indicators and return scores."""
        results = {
            'category': 'volatility',
            'max_points': sum(VOLATILITY_WEIGHTS.values()),
            'earned_points': 0,
            'indicators': {}
        }
        
        atr_result = self.calculate_atr()
        bollinger_result = self.calculate_bollinger()
        
        results['indicators']['atr'] = atr_result
        results['indicators']['bollinger'] = bollinger_result
        
        results['earned_points'] = (
            atr_result['score'] +
            bollinger_result['score']
        )
        
        return results
    
    def calculate_atr(self) -> Dict[str, Any]:
        """
        Calculate ATR (Average True Range) score.
        
        Returns:
            Dict with score, ATR, and ATR%
        """
        period = ATR_CONFIG['period']
        
        if len(self.df) < period + 10:
            return {
                'score': 0,
                'max_score': VOLATILITY_WEIGHTS['atr'],
                'atr': None,
                'atr_pct': None,
                'explanation': 'Insufficient data for ATR'
            }
        
        df = self.df.copy()
        
        # Calculate True Range
        df['h-l'] = df['high'] - df['low']
        df['h-pc'] = abs(df['high'] - df['close'].shift(1))
        df['l-pc'] = abs(df['low'] - df['close'].shift(1))
        df['tr'] = df[['h-l', 'h-pc', 'l-pc']].max(axis=1)
        
        # Calculate ATR
        df['atr'] = df['tr'].ewm(alpha=1/period, adjust=False).mean()
        
        # Calculate ATR%
        df['atr_pct'] = (df['atr'] / df['close']) * 100
        
        latest = df.iloc[-1]
        atr_value = latest['atr']
        atr_pct = latest['atr_pct']
        
        # Level score
        level_score = 0
        for (low, high), score in ATR_CONFIG['level_scores'].items():
            if low <= atr_pct < high:
                level_score = score
                break
        
        if 1.5 <= atr_pct <= 3.0:
            level_status = "Ideal Volatility"
        elif 3.0 < atr_pct <= 4.0:
            level_status = "High Volatility"
        elif 1.0 <= atr_pct < 1.5:
            level_status = "Low Volatility"
        elif 4.0 < atr_pct <= 6.0:
            level_status = "Very High Volatility"
        else:
            level_status = "Extreme Volatility"
        
        # Trend score (ATR trend vs price trend)
        trend_score = 0
        trend_status = "稳定"
        
        if len(df) >= 10:
            lookback = 10
            atr_change = df['atr'].iloc[-1] - df['atr'].iloc[-lookback]
            price_change = df['close'].iloc[-1] - df['close'].iloc[-lookback]
            
            if atr_change < 0 and price_change > 0:
                trend_score = ATR_CONFIG['trend_scores']['falling_price_rising']
                trend_status = "Vol Contracting + Price Rising (Healthy)"
            elif abs(atr_change / df['atr'].iloc[-lookback]) < 0.1:
                trend_score = ATR_CONFIG['trend_scores']['stable']
                trend_status = "Volatility Stable"
            elif atr_change > 0 and price_change < 0:
                trend_score = ATR_CONFIG['trend_scores']['rising_price_falling']
                trend_status = "Panic Selling"
            else:
                trend_score = ATR_CONFIG['trend_scores']['stable']
                trend_status = "Volatility Normal"
        
        total_score = level_score + trend_score
        
        return {
            'score': total_score,
            'max_score': VOLATILITY_WEIGHTS['atr'],
            'atr': round(atr_value, 4),
            'atr_pct': round(atr_pct, 2),
            'level_score': level_score,
            'trend_score': trend_score,
            'explanation': f"ATR%={atr_pct:.2f}% ({level_status}), {trend_status}"
        }
    
    def calculate_bollinger(self) -> Dict[str, Any]:
        """
        Calculate Bollinger Bands score.
        
        Returns:
            Dict with score and band details
        """
        period = BOLLINGER_CONFIG['period']
        std_dev = BOLLINGER_CONFIG['std_dev']
        
        if len(self.df) < period:
            return {
                'score': 0,
                'max_score': VOLATILITY_WEIGHTS['bollinger'],
                'upper': None,
                'middle': None,
                'lower': None,
                'explanation': 'Insufficient data for Bollinger Bands'
            }
        
        df = self.df.copy()
        
        # Calculate Bollinger Bands
        df['middle'] = df['close'].rolling(window=period).mean()
        df['std'] = df['close'].rolling(window=period).std()
        df['upper'] = df['middle'] + (df['std'] * std_dev)
        df['lower'] = df['middle'] - (df['std'] * std_dev)
        df['bandwidth'] = (df['upper'] - df['lower']) / df['middle']
        
        latest = df.iloc[-1]
        price = latest['close']
        upper = latest['upper']
        middle = latest['middle']
        lower = latest['lower']
        bandwidth = latest['bandwidth']
        
        # Position score
        position_score = 0
        position_status = ""
        
        # Check if expanding (compare to previous)
        is_expanding = False
        if len(df) >= 2:
            prev_bandwidth = df['bandwidth'].iloc[-2]
            is_expanding = bandwidth > prev_bandwidth
        
        if price > upper:
            if is_expanding:
                position_score = BOLLINGER_CONFIG['position_scores']['break_upper_expanding']
                position_status = "Break Upper + Band Expanding (Strong)"
            else:
                position_score = BOLLINGER_CONFIG['position_scores']['near_upper']
                position_status = "Break Upper"
        elif price >= middle + (upper - middle) * 0.5:
            position_score = BOLLINGER_CONFIG['position_scores']['near_upper']
            position_status = "Near Upper (Strong)"
        elif price >= middle - (middle - lower) * 0.5:
            position_score = BOLLINGER_CONFIG['position_scores']['mid']
            position_status = "Near Middle (Neutral)"
        elif price >= lower:
            position_score = BOLLINGER_CONFIG['position_scores']['near_lower']
            position_status = "Near Lower (Weak)"
        else:
            position_score = BOLLINGER_CONFIG['position_scores']['break_lower']
            position_status = "Break Lower (Oversold)"
        
        # Bandwidth score (check percentile)
        bandwidth_score = 0
        bandwidth_status = ""
        
        percentile_window = min(BOLLINGER_CONFIG['percentile_window'], len(df))
        if percentile_window >= 50:
            recent_bandwidths = df['bandwidth'].tail(percentile_window)
            percentile = (recent_bandwidths < bandwidth).sum() / len(recent_bandwidths)
            
            if 0.2 <= percentile <= 0.8:
                bandwidth_score = BOLLINGER_CONFIG['bandwidth_scores']['normal']
                bandwidth_status = "Bandwidth Normal"
            elif percentile > 0.8:
                bandwidth_score = BOLLINGER_CONFIG['bandwidth_scores']['expanding']
                bandwidth_status = "Bandwidth Expanding (Volatile)"
            else:
                bandwidth_score = BOLLINGER_CONFIG['bandwidth_scores']['squeeze']
                bandwidth_status = "Bandwidth Squeeze (Breakout Pending)"
        else:
            bandwidth_score = BOLLINGER_CONFIG['bandwidth_scores']['normal']
            bandwidth_status = "数据不足"
        
        total_score = position_score + bandwidth_score
        
        return {
            'score': total_score,
            'max_score': VOLATILITY_WEIGHTS['bollinger'],
            'upper': round(upper, 2),
            'middle': round(middle, 2),
            'lower': round(lower, 2),
            'current_price': round(price, 2),
            'bandwidth': round(bandwidth, 4),
            'position_score': position_score,
            'bandwidth_score': bandwidth_score,
            'explanation': f"{position_status}, {bandwidth_status}"
        }

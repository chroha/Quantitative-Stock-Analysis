"""
Trend Strength Indicators.
Implements ADX, Multi-period Moving Averages, and 52-week Price Position scoring.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from .scoring_config import (
    TREND_WEIGHTS, ADX_CONFIG, MA_CONFIG, PRICE_POSITION_CONFIG
)


class TrendIndicators:
    """Calculator for trend strength indicators."""
    
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
        """Calculate all trend indicators and return scores."""
        results = {
            'category': 'trend_strength',
            'max_points': TREND_WEIGHTS['adx'] + TREND_WEIGHTS['multi_ma'] + TREND_WEIGHTS['price_position'],
            'earned_points': 0,
            'indicators': {}
        }
        
        # Calculate each indicator
        adx_result = self.calculate_adx()
        ma_result = self.calculate_multi_ma()
        position_result = self.calculate_price_position()
        
        results['indicators']['adx'] = adx_result
        results['indicators']['multi_ma'] = ma_result
        results['indicators']['price_position'] = position_result
        
        # Sum earned points
        results['earned_points'] = (
            adx_result['score'] + 
            ma_result['score'] + 
            position_result['score']
        )
        
        return results
    
    def calculate_adx(self) -> Dict[str, Any]:
        """
        Calculate ADX (Average Directional Index) score.
        
        Returns:
            Dict with score, adx_value, plus_di, minus_di, and explanation
        """
        period = ADX_CONFIG['period']
        
        if len(self.df) < period * 2:
            return {
                'score': 0,
                'max_score': TREND_WEIGHTS['adx'],
                'adx': None,
                'plus_di': None,
                'minus_di': None,
                'explanation': 'Insufficient data for ADX calculation'
            }
        
        df = self.df.copy()
        
        # Calculate True Range
        df['h-l'] = df['high'] - df['low']
        df['h-pc'] = abs(df['high'] - df['close'].shift(1))
        df['l-pc'] = abs(df['low'] - df['close'].shift(1))
        df['tr'] = df[['h-l', 'h-pc', 'l-pc']].max(axis=1)
        
        # Calculate Directional Movement
        df['h-ph'] = df['high'] - df['high'].shift(1)
        df['pl-l'] = df['low'].shift(1) - df['low']
        
        df['plus_dm'] = np.where(
            (df['h-ph'] > df['pl-l']) & (df['h-ph'] > 0),
            df['h-ph'],
            0
        )
        df['minus_dm'] = np.where(
            (df['pl-l'] > df['h-ph']) & (df['pl-l'] > 0),
            df['pl-l'],
            0
        )
        
        # Smooth with Wilder's smoothing (exponential moving average)
        alpha = 1.0 / period
        df['atr'] = df['tr'].ewm(alpha=alpha, adjust=False).mean()
        df['plus_dm_smooth'] = df['plus_dm'].ewm(alpha=alpha, adjust=False).mean()
        df['minus_dm_smooth'] = df['minus_dm'].ewm(alpha=alpha, adjust=False).mean()
        
        # Calculate Directional Indicators
        df['plus_di'] = 100 * df['plus_dm_smooth'] / df['atr']
        df['minus_di'] = 100 * df['minus_dm_smooth'] / df['atr']
        
        # Calculate DX and ADX
        df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
        df['adx'] = df['dx'].ewm(alpha=alpha, adjust=False).mean()
        
        # Get latest values
        latest = df.iloc[-1]
        adx_value = latest['adx']
        plus_di = latest['plus_di']
        minus_di = latest['minus_di']
        
        # Calculate base score
        base_score = 0
        if adx_value >= 40:
            base_score = 10
            strength = "Very Strong Trend"
        elif adx_value >= 30:
            base_score = 8
            strength = "Strong Trend"
        elif adx_value >= 25:
            base_score = 6
            strength = "Trend Present"
        elif adx_value >= 20:
            base_score = 4
            strength = "Weak Trend"
        else:
            base_score = max(0, min(2, int(adx_value / 10)))
            strength = "No Trend/Sideways"
        
        # Calculate direction bonus
        direction_score = ADX_CONFIG['direction_bonus'] if plus_di > minus_di else 0
        direction = "Uptrend" if plus_di > minus_di else "Downtrend"
        
        total_score = base_score + direction_score
        
        return {
            'score': total_score,
            'max_score': TREND_WEIGHTS['adx'],
            'adx': round(adx_value, 2),
            'plus_di': round(plus_di, 2),
            'minus_di': round(minus_di, 2),
            'base_score': base_score,
            'direction_score': direction_score,
            'explanation': f"ADX={adx_value:.1f} ({strength}), +DI={plus_di:.1f}, -DI={minus_di:.1f} ({direction})"
        }
    
    def calculate_multi_ma(self) -> Dict[str, Any]:
        """
        Calculate Multi-period Moving Average system score.
        
        Returns:
            Dict with score and detailed breakdown
        """
        periods = MA_CONFIG['periods']
        max_period = max(periods)
        
        if len(self.df) < max_period:
            return {
                'score': 0,
                'max_score': TREND_WEIGHTS['multi_ma'],
                'ma20': None,
                'ma50': None,
                'ma200': None,
                'explanation': 'Insufficient data for MA calculation'
            }
        
        df = self.df.copy()
        
        # Calculate MAs
        df['ma20'] = df['close'].rolling(window=20).mean()
        df['ma50'] = df['close'].rolling(window=50).mean()
        df['ma200'] = df['close'].rolling(window=200).mean()
        
        latest = df.iloc[-1]
        price = latest['close']
        ma20 = latest['ma20']
        ma50 = latest['ma50']
        ma200 = latest['ma200']
        
        # Arrangement scoring
        arrangement_score = 0
        if price > ma20 > ma50 > ma200:
            arrangement_score = MA_CONFIG['arrangement_scores']['perfect_bullish']
            arrangement = "Perfect Bullish Alignment"
        elif price > ma20 > ma50:
            arrangement_score = MA_CONFIG['arrangement_scores']['mid_bullish']
            arrangement = "Mid-term Bullish"
        elif price > ma20:
            arrangement_score = MA_CONFIG['arrangement_scores']['short_bullish']
            arrangement = "Short-term Bullish"
        elif price < min(ma20, ma50, ma200):
            arrangement_score = MA_CONFIG['arrangement_scores']['complete_bearish']
            arrangement = "Complete Bearish"
        else:
            arrangement_score = MA_CONFIG['arrangement_scores']['mixed']
            arrangement = "Mixed Alignment"
        
        # Slope scoring (check if MAs are rising)
        lookback = 5
        if len(df) >= lookback + max_period:
            ma20_slope = (df['ma20'].iloc[-1] - df['ma20'].iloc[-lookback]) / lookback
            ma50_slope = (df['ma50'].iloc[-1] - df['ma50'].iloc[-lookback]) / lookback
            
            if ma20_slope > 0 and ma50_slope > 0:
                slope_score = MA_CONFIG['slope_scores']['both_rising']
                slope_status = "Both MAs Rising"
            elif ma20_slope > 0:
                slope_score = MA_CONFIG['slope_scores']['ma20_rising']
                slope_status = "MA20 Rising"
            else:
                slope_score = MA_CONFIG['slope_scores']['none']
                slope_status = "MAs Flat/Falling"
        else:
            slope_score = 0
            slope_status = "Insufficient Data"
        
        # Golden cross detection (MA20 crossed above MA50 in last N days)
        golden_cross_score = 0
        golden_cross_status = "No Golden Cross"
        lookback_days = MA_CONFIG['golden_cross_lookback']
        
        if len(df) >= max_period + lookback_days:
            recent_df = df.tail(lookback_days)
            for i in range(1, len(recent_df)):
                if (recent_df['ma20'].iloc[i] > recent_df['ma50'].iloc[i] and
                    recent_df['ma20'].iloc[i-1] <= recent_df['ma50'].iloc[i-1]):
                    golden_cross_score = MA_CONFIG['golden_cross_bonus']
                    golden_cross_status = f"Recent Golden Cross (within {lookback_days}d)"
                    break
        
        total_score = arrangement_score + slope_score + golden_cross_score
        
        return {
            'score': total_score,
            'max_score': TREND_WEIGHTS['multi_ma'],
            'ma20': round(ma20, 2),
            'ma50': round(ma50, 2),
            'ma200': round(ma200, 2),
            'current_price': round(price, 2),
            'arrangement_score': arrangement_score,
            'slope_score': slope_score,
            'golden_cross_score': golden_cross_score,
            'explanation': f"{arrangement}, {slope_status}, {golden_cross_status}"
        }
    
    def calculate_price_position(self) -> Dict[str, Any]:
        """
        Calculate 52-week price position score.
        
        Returns:
            Dict with score and position details
        """
        # Use 252 trading days as approximate 52 weeks
        lookback = min(252, len(self.df))
        
        if lookback < 50:  # Need reasonable amount of data
            return {
                'score': 0,
                'max_score': TREND_WEIGHTS['price_position'],
                'position': None,
                'explanation': 'Insufficient data for price position'
            }
        
        recent_df = self.df.tail(lookback)
        current_price = recent_df['close'].iloc[-1]
        high_52w = recent_df['high'].max()
        low_52w = recent_df['low'].min()
        
        # Calculate relative position
        if high_52w == low_52w:
            relative_position = 0.5  # Edge case
        else:
            relative_position = (current_price - low_52w) / (high_52w - low_52w)
        
        # Score based on position
        score = 0
        for threshold, points in sorted(PRICE_POSITION_CONFIG['thresholds'].items(), reverse=True):
            if relative_position >= threshold:
                score = points
                break
        
        position_pct = relative_position * 100
        
        if relative_position >= 0.90:
            zone = "Near Highs"
        elif relative_position >= 0.75:
            zone = "Upper Zone"
        elif relative_position >= 0.50:
            zone = "Middle Zone"
        elif relative_position >= 0.25:
            zone = "Lower Zone"
        else:
            zone = "Bottom Zone"
        
        return {
            'score': score,
            'max_score': TREND_WEIGHTS['price_position'],
            'position': round(position_pct, 1),
            'current_price': round(current_price, 2),
            'high_52w': round(high_52w, 2),
            'low_52w': round(low_52w, 2),
            'explanation': f"52-Week Position: {position_pct:.1f}% ({zone})"
        }

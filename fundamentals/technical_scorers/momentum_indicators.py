"""
Momentum Indicators.
Implements RSI, MACD, and ROC scoring.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
from .scoring_config import (
    MOMENTUM_WEIGHTS, RSI_CONFIG, MACD_CONFIG, ROC_CONFIG
)


class MomentumIndicators:
    """Calculator for momentum indicators."""
    
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
        """Calculate all momentum indicators and return scores."""
        results = {
            'category': 'momentum',
            'max_points': sum(MOMENTUM_WEIGHTS.values()),
            'earned_points': 0,
            'indicators': {}
        }
        
        rsi_result = self.calculate_rsi()
        macd_result = self.calculate_macd()
        roc_result = self.calculate_roc()
        
        results['indicators']['rsi'] = rsi_result
        results['indicators']['macd'] = macd_result
        results['indicators']['roc'] = roc_result
        
        results['earned_points'] = (
            rsi_result['score'] +
            macd_result['score'] +
            roc_result['score']
        )
        
        return results
    
    def calculate_rsi(self) -> Dict[str, Any]:
        """
        Calculate RSI (Relative Strength Index) score.
        
        Returns:
            Dict with score, rsi_value, and details
        """
        period = RSI_CONFIG['period']
        
        if len(self.df) < period + 1:
            return {
                'score': 0,
                'max_score': MOMENTUM_WEIGHTS['rsi'],
                'rsi': None,
                'explanation': 'Insufficient data for RSI'
            }
        
        df = self.df.copy()
        
        # Calculate price changes
        df['change'] = df['close'].diff()
        df['gain'] = np.where(df['change'] > 0, df['change'], 0)
        df['loss'] = np.where(df['change'] < 0, -df['change'], 0)
        
        # Calculate average gain and loss using Wilder's smoothing
        df['avg_gain'] = df['gain'].ewm(alpha=1/period, adjust=False).mean()
        df['avg_loss'] = df['loss'].ewm(alpha=1/period, adjust=False).mean()
        
        # Calculate RS and RSI
        df['rs'] = df['avg_gain'] / df['avg_loss']
        df['rsi'] = 100 - (100 / (1 + df['rs']))
        
        latest_rsi = df['rsi'].iloc[-1]
        
        # Base score calculation
        base_score = 0
        for (low, high), score in RSI_CONFIG['base_scores'].items():
            if low <= latest_rsi < high:
                base_score = score
                break
        
        # Determine zone
        # Determine zone
        if 55 <= latest_rsi <= 70:
            zone = "Strong (Not Overbought)"
        elif 70 < latest_rsi <= 80:
            zone = "Overbought (Strong)"
        elif 50 <= latest_rsi < 55:
            zone = "Neutral-Bullish"
        elif 40 <= latest_rsi < 50:
            zone = "Neutral-Bearish"
        elif 30 <= latest_rsi < 40:
            zone = "Weak"
        elif latest_rsi < 30:
            zone = "Oversold"
        else:
            zone = "Extremely Overbought"
        
        # Simple divergence check (price new high but RSI lower high)
        divergence_score = RSI_CONFIG['divergence_bonus']
        divergence_status = "No Divergence"
        
        if len(df) >= 20:
            recent_df = df.tail(20)
            price_peak_idx = recent_df['close'].idxmax()
            rsi_peak_idx = recent_df['rsi'].idxmax()
            
            # Check for bearish divergence (price making higher high, RSI making lower high)
            if price_peak_idx > rsi_peak_idx:
                price_at_rsi_peak = recent_df.loc[rsi_peak_idx, 'close']
                current_price = recent_df['close'].iloc[-1]
                if current_price > price_at_rsi_peak and latest_rsi < recent_df.loc[rsi_peak_idx, 'rsi']:
                    divergence_score = RSI_CONFIG['divergence_penalty']
                    divergence_status = "Bearish Divergence (Risk)"
        
        total_score = base_score + divergence_score
        
        return {
            'score': total_score,
            'max_score': MOMENTUM_WEIGHTS['rsi'],
            'rsi': round(latest_rsi, 2),
            'base_score': base_score,
            'divergence_score': divergence_score,
            'explanation': f"RSI={latest_rsi:.1f} ({zone}), {divergence_status}"
        }
    
    def calculate_macd(self) -> Dict[str, Any]:
        """
        Calculate MACD score.
        
        Returns:
            Dict with score and MACD components
        """
        fast = MACD_CONFIG['fast']
        slow = MACD_CONFIG['slow']
        signal = MACD_CONFIG['signal']
        
        if len(self.df) < slow + signal:
            return {
                'score': 0,
                'max_score': MOMENTUM_WEIGHTS['macd'],
                'macd': None,
                'signal_line': None,
                'histogram': None,
                'explanation': 'Insufficient data for MACD'
            }
        
        df = self.df.copy()
        
        # Calculate MACD
        ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
        df['macd'] = ema_fast - ema_slow
        df['signal'] = df['macd'].ewm(span=signal, adjust=False).mean()
        df['histogram'] = df['macd'] - df['signal']
        
        latest = df.iloc[-1]
        macd_value = latest['macd']
        signal_value = latest['signal']
        histogram = latest['histogram']
        
        # Check signal state
        signal_score = 0
        signal_state = ""
        
        # Check for golden/death cross
        if len(df) >= 2:
            prev = df.iloc[-2]
            is_golden_cross = macd_value > signal_value and prev['macd'] <= prev['signal']
            is_death_cross = macd_value < signal_value and prev['macd'] >= prev['signal']
            
            # Check histogram expansion/contraction
            is_expanding = abs(histogram) > abs(prev['histogram'])
            
            if is_golden_cross and is_expanding and macd_value > 0:
                signal_score = MACD_CONFIG['signal_scores']['golden_expanding_positive']
                signal_state = "Golden Cross + Expanding Hist + MACD>0"
            elif is_golden_cross and is_expanding:
                signal_score = MACD_CONFIG['signal_scores']['golden_expanding']
                signal_state = "Golden Cross + Expanding Hist"
            elif is_golden_cross:
                signal_score = MACD_CONFIG['signal_scores']['golden_expanding']
                signal_state = "Golden Cross + Converging Hist"
            elif is_death_cross and not is_expanding:
                signal_score = MACD_CONFIG['signal_scores']['death_converging']
                signal_state = "Death Cross + Converging Hist"
            else:
                # Check current state (not necessarily recent cross)
                if macd_value > signal_value and macd_value > 0:
                    signal_score = MACD_CONFIG['signal_scores']['golden_expanding']
                    signal_state = "MACD > Signal & > 0"
                elif macd_value > signal_value:
                    signal_score = MACD_CONFIG['signal_scores']['golden_converging']
                    signal_state = "MACD > Signal"
                else:
                    signal_score = MACD_CONFIG['signal_scores']['other']
                    signal_state = "MACD < Signal"
        
        # Position score
        position_score = 0
        if macd_value > 0 and signal_value > 0:
            position_score = MACD_CONFIG['position_scores']['both_positive']
            position_state = "Both > 0"
        elif macd_value > 0:
            position_score = MACD_CONFIG['position_scores']['fast_positive']
            position_state = "MACD > 0"
        else:
            position_score = MACD_CONFIG['position_scores']['negative']
            position_state = "Both < 0"
        
        total_score = signal_score + position_score
        
        return {
            'score': total_score,
            'max_score': MOMENTUM_WEIGHTS['macd'],
            'macd': round(macd_value, 4),
            'signal_line': round(signal_value, 4),
            'histogram': round(histogram, 4),
            'signal_score': signal_score,
            'position_score': position_score,
            'explanation': f"{signal_state}, {position_state}"
        }
    
    def calculate_roc(self) -> Dict[str, Any]:
        """
        Calculate ROC (Rate of Change) score.
        
        Returns:
            Dict with score and ROC value
        """
        period = ROC_CONFIG['period']
        
        if len(self.df) < period + 1:
            return {
                'score': 0,
                'max_score': MOMENTUM_WEIGHTS['roc'],
                'roc': None,
                'explanation': 'Insufficient data for ROC'
            }
        
        df = self.df.copy()
        
        # Calculate ROC as percentage change
        df['roc'] = ((df['close'] - df['close'].shift(period)) / df['close'].shift(period)) * 100
        
        latest_roc = df['roc'].iloc[-1]
        
        # Score based on thresholds
        score = 0
        for threshold, points in sorted(ROC_CONFIG['thresholds'].items(), reverse=True):
            if latest_roc >= threshold:
                score = points
                break
        
        if latest_roc >= 10:
            status = "Strong Surge"
        elif latest_roc >= 5:
            status = "Solid Gain"
        elif latest_roc >= 2:
            status = "Moderate Gain"
        elif latest_roc >= 0:
            status = "Slight Gain"
        elif latest_roc >= -5:
            status = "Slight Loss"
        else:
            status = "Significant Loss"
        
        return {
            'score': score,
            'max_score': MOMENTUM_WEIGHTS['roc'],
            'roc': round(latest_roc, 2),
            'period': period,
            'explanation': f"{period}日ROC={latest_roc:.2f}% ({status})"
        }

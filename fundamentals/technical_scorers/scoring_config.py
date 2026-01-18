"""
Technical Scoring Configuration.
Defines all weights, thresholds, and parameters for technical indicator scoring.
"""

# ==================== CATEGORY WEIGHTS ====================
# Total: 100 points
CATEGORY_WEIGHTS = {
    'trend_strength': 35,      # Trend Strength
    'momentum': 25,            # Momentum Indicators
    'volatility': 15,          # Volatility
    'price_structure': 15,     # Price Structure (Support/Resistance)
    'volume_price': 10         # Volume-Price Relationship
}

# ==================== TREND STRENGTH (35 points) ====================
TREND_WEIGHTS = {
    'adx': 12,                 # Average Directional Index
    'multi_ma': 13,            # Multi-period Moving Average System
    'price_position': 10       # 52-week Price Position
}

# ADX Scoring Thresholds
ADX_CONFIG = {
    'period': 14,
    'thresholds': {
        'extreme_strong': (40, 10),    # ADX >= 40: 10 points
        'strong': (30, 8),              # ADX >= 30: 8 points
        'moderate': (25, 6),            # ADX >= 25: 6 points
        'weak': (20, 4),                # ADX >= 20: 4 points
        'very_weak': (0, 2)             # ADX < 20: 0-2 points
    },
    'direction_bonus': 2                # +DI > -DI: +2 points
}

# Moving Average Configuration
MA_CONFIG = {
    'periods': [20, 50, 200],
    'golden_cross_lookback': 10,        # Days to check for recent golden cross
    'arrangement_scores': {
        'perfect_bullish': 10,          # Price > MA20 > MA50 > MA200
        'mid_bullish': 7,               # Price > MA20 > MA50
        'short_bullish': 4,             # Price > MA20
        'complete_bearish': 0,          # Price < all MAs
        'mixed': 2                      # Other arrangements
    },
    'slope_scores': {
        'both_rising': 2,               # MA20 & MA50 rising
        'ma20_rising': 1,               # Only MA20 rising
        'none': 0
    },
    'golden_cross_bonus': 1             # Recent golden cross
}

# 52-Week Position Configuration
PRICE_POSITION_CONFIG = {
    'thresholds': {
        0.90: 10,                       # >= 90% of range
        0.75: 8,                        # >= 75% of range
        0.50: 6,                        # >= 50% of range
        0.25: 3,                        # >= 25% of range
        0.00: 0                         # Bottom area
    }
}

# ==================== MOMENTUM (25 points) ====================
MOMENTUM_WEIGHTS = {
    'rsi': 10,                 # Relative Strength Index
    'macd': 10,                # MACD
    'roc': 5                   # Rate of Change
}

# RSI Configuration
RSI_CONFIG = {
    'period': 14,
    'base_scores': {
        (55, 70): 8,                    # Optimal range: strong but not overbought
        (70, 80): 6,                    # Overbought but strong
        (50, 55): 5,                    # Neutral-bullish
        (40, 50): 3,                    # Neutral-bearish
        (30, 40): 2,                    # Weak
        (0, 30): 0,                     # Oversold
        (80, 100): 0                    # Extreme overbought
    },
    'divergence_bonus': 2,              # No divergence
    'divergence_penalty': 0             # Top divergence detected
}

# MACD Configuration
MACD_CONFIG = {
    'fast': 12,
    'slow': 26,
    'signal': 9,
    'signal_scores': {
        'golden_expanding_positive': 7,  # Golden cross + expanding histogram + MACD > 0
        'golden_expanding': 5,           # Golden cross + expanding histogram
        'golden_converging': 3,          # Golden cross + converging histogram
        'death_converging': 2,           # Death cross but converging
        'other': 0
    },
    'position_scores': {
        'both_positive': 3,              # Fast & slow > 0
        'fast_positive': 2,              # Only fast > 0
        'negative': 0
    }
}

# ROC Configuration
ROC_CONFIG = {
    'period': 20,
    'thresholds': {
        10.0: 5,
        5.0: 4,
        2.0: 3,
        0.0: 2,
        -5.0: 1,
        -100.0: 0
    }
}

# ==================== VOLATILITY (15 points) ====================
VOLATILITY_WEIGHTS = {
    'atr': 8,                  # Average True Range
    'bollinger': 7             # Bollinger Bands
}

# ATR Configuration
ATR_CONFIG = {
    'period': 14,
    'level_scores': {
        (1.5, 3.0): 6,                  # Ideal volatility
        (3.0, 4.0): 4,                  # High volatility
        (1.0, 1.5): 3,                  # Low volatility
        (4.0, 6.0): 2,                  # Very high volatility
        (0.0, 1.0): 0,                  # Extremely low
        (6.0, 100.0): 0                 # Extremely high
    },
    'trend_scores': {
        'falling_price_rising': 2,      # ATR falling + price rising (healthy)
        'stable': 1,                    # ATR stable
        'rising_price_falling': 0       # ATR rising + price falling (panic)
    }
}

# Bollinger Bands Configuration
BOLLINGER_CONFIG = {
    'period': 20,
    'std_dev': 2,
    'position_scores': {
        'break_upper_expanding': 5,     # Price > upper band + expanding
        'near_upper': 4,                # Price near upper band
        'mid': 2,                       # Price near middle
        'near_lower': 1,                # Price near lower band
        'break_lower': 0                # Price < lower band
    },
    'bandwidth_scores': {
        'normal': 2,                    # 20-80 percentile
        'expanding': 1,                 # > 80 percentile
        'squeeze': 0                    # < 20 percentile
    },
    'percentile_window': 100            # Days to calculate bandwidth percentile
}

# ==================== PRICE STRUCTURE (15 points) ====================
STRUCTURE_WEIGHTS = {
    'support_resistance': 8,   # Support/Resistance Strength
    'high_low_structure': 7    # High/Low Pattern
}

# Support/Resistance Configuration
SUPPORT_RESISTANCE_CONFIG = {
    'lookback_period': 50,              # Days to identify pivot points
    'min_touches': 2,                   # Minimum touches for valid level
    'distance_scores': {
        'safe_zone': (5.0, 5.0, 8),     # Support > 5% AND Resistance > 5%
        'strong_support': (3.0, 0, 6),  # Support > 3%
        'near_resistance': (0, 2.0, 2), # Resistance < 2%
        'broken_support': (-100, -2.0, 0) # Broken support
    }
}

# High/Low Structure Configuration
HIGH_LOW_CONFIG = {
    'short_period': 20,                 # Short-term structure
    'long_period': 50,                  # Long-term structure
    'scores': {
        'perfect_uptrend': 7,           # Higher highs + higher lows
        'uptrend_unstable': 5,          # Higher highs but deep pullbacks
        'consolidation': 3,             # No new highs/lows
        'downtrend': 0                  # Lower lows
    }
}

# ==================== VOLUME-PRICE (10 points) ====================
VOLUME_WEIGHTS = {
    'obv': 5,                  # On-Balance Volume
    'volume_strength': 5       # Relative Volume
}

# OBV Configuration
OBV_CONFIG = {
    'alignment_scores': {
        'both_rising': 4,               # OBV up + Price up
        'price_up_obv_flat': 2,         # Price up + OBV flat
        'divergence': 0                 # Price up + OBV down
    },
    'trend_period': 20,
    'trend_threshold': 0.01,
    'trend_bonus': 1                    # Strong OBV trend
}

# Volume Strength Configuration
VOLUME_STRENGTH_CONFIG = {
    'period': 20,                       # Average volume period
    'ratio_scores': {
        2.0: 3,                         # Heavy volume
        1.5: 2,                         # Moderate volume increase
        1.0: 2,                         # Normal volume
        0.5: 1,                         # Low volume
        0.0: 0                          # Extremely low
    },
    'alignment_scores': {
        'high_vol_price_up': 2,         # Volume > 1.5 + Price up
        'low_vol_price_up': 1,          # Volume < 1.5 + Price up
        'high_vol_price_down': 0        # Volume > 1.5 + Price down
    }
}

# ==================== GENERAL SETTINGS ====================
MIN_DATA_POINTS = 250                   # Minimum days of data required for all calculations
INSUFFICIENT_DATA_SCORE = 0             # Score when data is insufficient

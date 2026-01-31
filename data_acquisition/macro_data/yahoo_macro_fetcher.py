"""
Yahoo Finance Macro Data Fetcher - 从Yahoo Finance获取宏观市场数据

Fetches market indicators from Yahoo Finance using Batch Download.
Assets:
- Equity Indices: SPY (S&P 500), IWM (Russell 2000)
- Market Style: VUG (Growth), VTV (Value)
- Volatility: ^VIX, ^VIX3M
- Commodities: CL=F (Oil), GC=F (Gold), HG=F (Copper)
- Crypto: BTC-USD
- Currencies: AUDUSD=X, AUDCNY=X, DX-Y.NYB (DXY), JPY=X (USD/JPY)

Provides calculated metrics: 1D%, 1W%, 1M%, YTD%, 52W Position.
"""

import os
import json
import time
import requests
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import pytz
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from config.settings import settings
from utils.logger import setup_logger

logger = setup_logger('yahoo_macro_fetcher')


class YahooMacroFetcher:
    """Fetcher for Yahoo Finance macro market data with batch processing and trend calculation."""
    
    # Define Ticker Mapping
    TICKERS = {
        'SPY': 'SP500_ETF',
        'IWM': 'Russell2000_ETF',
        'VUG': 'Growth_ETF',
        'VTV': 'Value_ETF',
        '^VIX': 'VIX',
        '^VIX3M': 'VIX3M',
        'CL=F': 'Crude_Oil',
        'GC=F': 'Gold',
        'HG=F': 'Copper',
        'BTC-USD': 'Bitcoin',
        'DX-Y.NYB': 'DXY',
        'JPY=X': 'USDJPY',
        'AUDUSD=X': 'AUDUSD',
        'AUDCNY=X': 'AUDCNY',
        # GICS Sectors
        'XLK': 'XLK', 'XLC': 'XLC', 'XLY': 'XLY',
        'XLE': 'XLE', 'XLF': 'XLF', 'XLI': 'XLI', 'XLB': 'XLB', 'XLRE': 'XLRE',
        'XLP': 'XLP', 'XLV': 'XLV', 'XLU': 'XLU'
    }

    # Reverse mapping for internal lookup
    REVERSE_TICKERS = {v: k for k, v in TICKERS.items()}

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize Yahoo macro fetcher.
        
        Args:
            config: Configuration dict
        """
        self.config = config or {}
        self.nyse_tz = pytz.timezone('US/Eastern')
        
    def _calculate_returns(self, history_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate extensive return metrics for an asset.
        
        Args:
            history_df: Historical DataFrame (must possess 'Close' column)
            
        Returns:
            Dict with price, returns (1D/1W/1M/YTD), and 52W position
        """
        if history_df is None or len(history_df) < 2:
            return {}

        df = history_df.sort_index()
        current_price = float(df['Close'].iloc[-1])
        current_date = df.index[-1]
        
        # Helper to get Pct Change
        def get_pct_change(days_lookback):
            try:
                # Find date closest to lookback
                target_date = current_date - timedelta(days=days_lookback)
                # Get index location of closest date <= target_date
                # Since df is sorted, we can search sorted
                # But simple way: filter
                
                # Check if we have enough history
                if df.index[0] > target_date: 
                    # Not enough data for full period
                   return None

                # Approximate using iloc if trading days match roughly
                # 1W = ~5 trading days, 1M = ~21, 1Y = ~252
                # More robust: find latest date <= target_date
                past_slice = df[df.index <= target_date]
                if past_slice.empty:
                    return None
                    
                start_price = float(past_slice['Close'].iloc[-1])
                return (current_price - start_price) / start_price
            except Exception:
                return None

        # YTD
        try:
            year_start = datetime(current_date.year, 1, 1)
            # Ensure current_date timezone info is compatible with year_start if needed
            # yfinance index usually tz-aware, datetime(..., 1, 1) is naive
            if current_date.tzinfo and not year_start.tzinfo:
                 # Check if we can make year_start aware, or make current_date naive
                 # Using tz_convert or naive comparison
                 # Safest: compare date components
                 pass

            # Simpler approach: Filter by year
            this_year_df = df[df.index.year == current_date.year]
            if len(this_year_df) > 1:
                start_price = float(this_year_df['Close'].iloc[0])
                ytd_change = (current_price - start_price) / start_price
            else:
                 # If only 1 data point this year (e.g. Jan 2), try to get last year close
                 # This logic is slightly complex, fallback to simple
                 ytd_change = None
        except:
            ytd_change = None

        # 52-Week Position
        try:
            # Last 252 trading days (approx 1 year) or full df if shorter, max 1 year by calendar
            one_year_ago = current_date - timedelta(days=365)
            last_year_df = df[df.index >= one_year_ago]
            
            high_52w = float(last_year_df['Close'].max())
            low_52w = float(last_year_df['Close'].min())
            
            if high_52w > low_52w:
                pos_52w = (current_price - low_52w) / (high_52w - low_52w) * 100
            else:
                pos_52w = 50.0 # Flat range
        except Exception:
            high_52w, low_52w, pos_52w = None, None, None

        return {
            'price': current_price,
            'change_1d': get_pct_change(1), # This might be logically 1 day ago? No, 1 calendar day is risky.
            # Use simpler iloc based approach for short term to be safe against weekends
            # Actually yfinance gives daily data. iloc[-2] is the previous close.
            'change_1d_safe': (current_price / float(df['Close'].iloc[-2]) - 1) if len(df) >= 2 else 0.0,
            'change_1w': get_pct_change(7),
            'change_1m': get_pct_change(30),
            'change_ytd': ytd_change,
            'high_52w': high_52w,
            'low_52w': low_52w,
            'position_52w': pos_52w,
            'last_updated': current_date.strftime('%Y-%m-%d')
        }

    def fetch_all(self) -> Dict[str, Any]:
        """
        Fetch all Yahoo Finance macro data using Batch Download.
        
        Returns:
            Dict structured by categories (Equity, Commodities, Currencies, Market Internals)
        """
        logger.info("=" * 50)
        logger.info("Fetching Yahoo Finance market data (Batch)...")
        logger.info("=" * 50)
        
        result = {
            'data': {},
            'status': 'ok',
            'warnings': []
        }
        
        ticker_list = list(self.TICKERS.keys())
        
        try:
            # Download batch data
            # period="2y" to ensure enough data for 52W high/low calculation even directly after new year
            data = yf.download(ticker_list, period="2y", group_by='ticker', auto_adjust=True, progress=False, threads=True)
            
            if data.empty:
                result['status'] = 'failed'
                result['warnings'].append("Batch download returned no data")
                return result

            # Process each ticker
            for ticker_symbol, internal_name in self.TICKERS.items():
                try:
                    # Handle MultiIndex column structure from yfinance
                    # If len(tickers) > 1, columns are (Ticker, Price Type)
                    # Use xs to extract dataframe for specific ticker
                    try:
                        ticker_df = data.xs(ticker_symbol, axis=1, level=0) if len(ticker_list) > 1 else data
                    except KeyError:
                        logger.warning(f"Ticker {ticker_symbol} not found in batch data")
                        continue

                    # If 'Close' is missing (failed download for this one), skip
                    if 'Close' not in ticker_df.columns or ticker_df['Close'].isnull().all():
                        logger.warning(f"No Close data for {ticker_symbol}")
                        continue
                        
                    # Drop NaNs
                    ticker_df = ticker_df.dropna(subset=['Close'])
                    
                    if len(ticker_df) < 2:
                        logger.warning(f"Insufficient history for {ticker_symbol}")
                        continue

                    metrics = self._calculate_returns(ticker_df)
                    
                    # Store by Internal Name for cleaner aggregation
                    result['data'][internal_name] = metrics
                    result['data'][internal_name]['ticker'] = ticker_symbol # Store original ticker
                    
                    logger.info(f"Processed {internal_name}: ${metrics['price']:.2f} (1D: {metrics['change_1d_safe']:.2%})")
                    
                except Exception as e:
                    logger.error(f"Error processing {ticker_symbol}: {e}")
                    result['warnings'].append(f"Error processing {ticker_symbol}")

            # ------------------------------------------------------------------
            # Calculate Derived Ratios (Market Internals)
            # ------------------------------------------------------------------
            d = result['data']
            
            # 1. Growth vs Value Ratio (VUG / VTV)
            if 'Growth_ETF' in d and 'Value_ETF' in d:
                ratio_val = d['Growth_ETF']['price'] / d['Value_ETF']['price']
                
                # We can't easily get historical ratio returns without full dataframe alignment
                # For now, just current ratio is fine, or simple comparison of 1D chg
                growth_mom = d['Growth_ETF']['change_1m'] or 0
                value_mom = d['Value_ETF']['change_1m'] or 0
                
                result['data']['Style_Ratio'] = {
                    'current': ratio_val,
                    'momentum_signal': "Growth" if growth_mom > value_mom else "Value",
                    'spread_1m': growth_mom - value_mom
                }
            
            # 2. Size Ratio (IWM / SPY) - Small vs Large
            if 'Russell2000_ETF' in d and 'SP500_ETF' in d:
                 ratio_val = d['Russell2000_ETF']['price'] / d['SP500_ETF']['price']
                 
                 small_mom = d['Russell2000_ETF']['change_1m'] or 0
                 large_mom = d['SP500_ETF']['change_1m'] or 0
                 
                 result['data']['Size_Ratio'] = {
                    'current': ratio_val,
                    'momentum_signal': "Small Caps" if small_mom > large_mom else "Large Caps",
                     'spread_1m': small_mom - large_mom
                }
            
            # 3. VIX Trend Structure (VIX vs SMA20)
            # Replaces unreliable VIX3M term structure
            if '^VIX' in ticker_list:
                try:
                    vix_df = data.xs('^VIX', axis=1, level=0) if len(ticker_list) > 1 else data
                    
                    # Drop NaNs to match main loop processing (critical for accurate SMA)
                    if 'Close' in vix_df.columns:
                        vix_df = vix_df.dropna(subset=['Close'])
                    
                    # Ensure we have enough data
                    if len(vix_df) > 20:
                        current_vix = vix_df['Close'].iloc[-1]
                        sma20 = vix_df['Close'].rolling(window=20).mean().iloc[-1]
                        
                        ratio = current_vix / sma20
                        
                        # Interpretation
                        if ratio > 1.1:
                            signal = "Rising Fear (Risk-Off)"
                        elif ratio < 0.9:
                            signal = "Calming (Risk-On)"
                        else:
                            signal = "Neutral"
                            
                        result['data']['VIX_Structure'] = {
                            'ratio': ratio,
                            'signal': signal,
                            'current': current_vix,
                            'sma20': sma20
                        }
                except Exception as e:
                    pass # VIX structure failed

        except Exception as e:
            logger.error(f"Batch fetch failed: {e}")
            result['status'] = 'failed'
            result['warnings'].append(f"Batch fetch critical error: {e}")

        return result

"""
FRED Data Fetcher

Fetches economic indicators from FRED (Federal Reserve Economic Data):
- Yields: GS10, GS2
- Inflation: CPIAUCSL
- Employment: UNRATE, ICSA (Claims), CCSA (Continued Claims)
- Sentiment: UMCSENT
- Risk/Liquidity: STLFSI3, BAMLH0A0HYM2

Provides caching mechanism and error handling.
"""

import os
import json
import time
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path
from utils.logger import setup_logger
from config.constants import DATA_CACHE_MACRO

logger = setup_logger('fred_fetcher')

try:
    from fredapi import Fred
    FREDAPI_AVAILABLE = True
except ImportError:
    FREDAPI_AVAILABLE = False
    logger.warning("fredapi not installed. Run: pip install fredapi")


class FREDFetcher:
    """Fetcher for FRED economic data with caching and error handling."""
    
    def __init__(self, api_key: Optional[str] = None, config: Optional[Dict] = None):
        """
        Initialize FRED fetcher.
        
        Args:
            api_key: FRED API key (or set FRED_API_KEY env var)
            config: Configuration dict with lookback periods and cache settings
        """
        if not FREDAPI_AVAILABLE:
            raise ImportError(
                "fredapi library is required. Install it with: pip install fredapi"
            )
        
        # Get API key
        self.api_key = api_key or os.getenv('FRED_API_KEY')
        if not self.api_key:
            raise ValueError(
                "FRED API key is required. Set FRED_API_KEY environment variable "
                "or pass api_key parameter. Get a free key at: "
                "https://fred.stlouisfed.org/"
            )
        
        # Initialize FRED client
        try:
            self.fred = Fred(api_key=self.api_key)
        except Exception as e:
            logger.error(f"Failed to initialize FRED client: {e}")
            raise ValueError(
                f"Invalid FRED API key or connection failed: {e}\n"
                "Get a valid key at: https://fred.stlouisfed.org/"
            )
        
        # Load configuration
        self.config = config or self._load_default_config()
        self.lookback_days = self.config.get('lookback_periods', {})
        self.cache_ttl = self.config.get('cache_ttl_seconds', {}).get('fred_data', 3600)
        self.cpi_ttl = self.config.get('cache_ttl_seconds', {}).get('fred_cpi', 86400)
        
        # Setup cache directory (use unified cache path)
        project_root = Path(__file__).parent.parent.parent
        self.cache_dir = project_root / DATA_CACHE_MACRO / '.cache'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Reset daily request counter if needed
        self._check_daily_reset()

    def _check_daily_reset(self):
        """Check and reset daily request counter."""
        counter_path = self.cache_dir / 'request_counter.json'
        today = datetime.now().strftime('%Y-%m-%d')
        
        reset = True
        if counter_path.exists():
            try:
                with open(counter_path, 'r') as f:
                    data = json.load(f)
                    if data.get('date') == today:
                        reset = False
            except:
                pass
        
        if reset:
            try:
                with open(counter_path, 'w') as f:
                    json.dump({'date': today, 'count': 0}, f)
            except:
                pass
    
    def _load_default_config(self) -> Dict:
        """Load default configuration from Python module."""
        try:
            from data_acquisition.macro_data.macro_config import (
                LOOKBACK_PERIODS, CACHE_TTL
            )
            return {
                'lookback_periods': LOOKBACK_PERIODS,
                'cache_ttl_seconds': CACHE_TTL
            }
        except ImportError:
            return {
                'lookback_periods': {'GS2_days': 60},
                'cache_ttl_seconds': {'fred_data': 3600}
            }
    
    def _get_cache_path(self, series_id: str) -> Path:
        """Get cache file path for a series."""
        return self.cache_dir / f"fred_{series_id}.json"
    
    def _load_from_cache(self, series_id: str) -> Optional[Dict]:
        """Load data from cache if valid."""
        cache_path = self._get_cache_path(series_id)
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r') as f:
                cached = json.load(f)
            
            # Check if cache is still valid
            cache_time = datetime.fromisoformat(cached['timestamp'])
            age_seconds = (datetime.now() - cache_time).total_seconds()
            
            # Use specific TTL for CPI if series is CPIAUCSL
            ttl = self.cpi_ttl if series_id == 'CPIAUCSL' else self.cache_ttl
            
            if age_seconds < ttl:
                logger.info(f"Using cached data for {series_id} (age: {age_seconds:.0f}s)")
                return cached['data']
            else:
                logger.debug(f"Cache expired for {series_id} (age: {age_seconds:.0f}s)")
                return None
        except Exception as e:
            logger.warning(f"Failed to load cache for {series_id}: {e}")
            return None
    
    def _save_to_cache(self, series_id: str, data: Dict):
        """Save data to cache."""
        cache_path = self._get_cache_path(series_id)
        try:
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
            with open(cache_path, 'w') as f:
                json.dump(cache_data, f, indent=2)
            logger.debug(f"Cached data for {series_id}")
        except Exception as e:
            logger.warning(f"Failed to save cache for {series_id}: {e}")
    
    def _fetch_series(self, series_id: str, days: Optional[int] = None) -> Optional[pd.Series]:
        """
        Fetch a FRED series with caching and retry logic.
        
        Args:
            series_id: FRED series identifier (e.g., 'GS10')
            days: Number of days to look back (None = latest only)
            
        Returns:
            pandas Series with date index, or None if fetch fails
        """
        # Try cache first
        cached = self._load_from_cache(series_id)
        if cached:
            df = pd.DataFrame(cached)
            df['date'] = pd.to_datetime(df['date'])
            return df.set_index('date')['value']
        
        # Fetch from API
        try:
            if days:
                start_date = datetime.now() - timedelta(days=days)
                data = self.fred.get_series(series_id, observation_start=start_date)
            else:
                # Get recent data and take latest (default 60 days to be safe for monthly)
                start_date = datetime.now() - timedelta(days=60)
                data = self.fred.get_series(series_id, observation_start=start_date)
            
            # Update request counter
            self._increment_request_counter()
            
            if data is None or len(data) == 0:
                logger.warning(f"No data returned for {series_id}")
                return None
            
            # Save to cache
            cache_data = {
                'date': data.index.strftime('%Y-%m-%d').tolist(),
                'value': data.values.tolist()
            }
            self._save_to_cache(series_id, cache_data)
            
            logger.info(f"Fetched {series_id}: {len(data)} observations")
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch {series_id}: {e}")
            
            # Retry once after delay
            try:
                logger.info(f"Retrying {series_id} after 2 seconds...")
                time.sleep(2)
                if days:
                    start_date = datetime.now() - timedelta(days=days)
                    data = self.fred.get_series(series_id, observation_start=start_date)
                else:
                    data = self.fred.get_series(series_id, observation_start=datetime.now() - timedelta(days=60))
                
                if data is not None and len(data) > 0:
                    logger.info(f"Retry successful for {series_id}")
                    return data
            except Exception as retry_error:
                logger.error(f"Retry failed for {series_id}: {retry_error}")
            
    def _increment_request_counter(self):
        """Increment daily request counter."""
        counter_path = self.cache_dir / 'request_counter.json'
        try:
            if counter_path.exists():
                with open(counter_path, 'r') as f:
                    data = json.load(f)
                data['count'] = data.get('count', 0) + 1
                with open(counter_path, 'w') as f:
                    json.dump(data, f)
        except:
            pass

    def _get_latest_point(self, series_id: str, days_lookback: int = 60) -> Dict[str, Any]:
        """Helper to get latest value and date for a series."""
        s = self._fetch_series(series_id, days=days_lookback)
        if s is not None and len(s) > 0:
            val = float(s.iloc[-1])
            date_str = s.index[-1].strftime('%Y-%m-%d')
            
            # Trend (Previous value comparison)
            prev_val = float(s.iloc[-2]) if len(s) > 1 else val
            trend = "stable"
            if val > prev_val: trend = "up"
            elif val < prev_val: trend = "down"
            
            return {
                'value': val,
                'date': date_str,
                'prev_value': prev_val,
                'trend': trend
            }
        return None

    def fetch_treasury_yields(self) -> Dict[str, Any]:
        """Fetch Treasury yield data (DGS10, DGS2 - Daily)."""
        result = {
            'GS10_current': None,
            'GS10_prev': None,
            'GS2_current': None,
            'GS2_prev': None,
            'GS2_historical': None,
            'yield_curve_10y_2y': None,
            'yield_curve_10y_2y_prev': None,
            'yield_date': None,
            'status': 'ok',
            'warnings': []
        }
        
        # Fetch DGS10 (Daily 10-Year Treasury Constant Maturity Rate)
        # Short lookback (14 days) to get latest daily print
        gs10_data = self._fetch_series('DGS10', days=14)
        if gs10_data is not None and len(gs10_data) > 0:
            result['GS10_current'] = float(gs10_data.iloc[-1])
            if len(gs10_data) > 1:
                result['GS10_prev'] = float(gs10_data.iloc[-2])
            result['yield_date'] = gs10_data.index[-1].strftime('%Y-%m-%d')
            logger.info(f"DGS10 (10Y Daily): {result['GS10_current']:.2f}% ({result['yield_date']})")
        else:
            result['warnings'].append("Failed to fetch DGS10")
            result['status'] = 'degraded'
        
        # Fetch DGS2 (Daily 2-Year Treasury Constant Maturity Rate)
        gs2_data = self._fetch_series('DGS2', days=14)
        if gs2_data is not None and len(gs2_data) > 0:
            result['GS2_current'] = float(gs2_data.iloc[-1])
            if len(gs2_data) > 1:
                result['GS2_prev'] = float(gs2_data.iloc[-2])
             # Store historical for trend if needed, but mainly we need current
            result['GS2_historical'] = [
                {'date': date.strftime('%Y-%m-%d'), 'value': float(value)}
                for date, value in gs2_data.items()
            ]
            # Use date from DGS2 if DGS10 failed, or just confirm consistency
            if not result['yield_date']:
                result['yield_date'] = gs2_data.index[-1].strftime('%Y-%m-%d')
                
            logger.info(f"DGS2 (2Y Daily): {result['GS2_current']:.2f}%")
        else:
            result['warnings'].append("Failed to fetch DGS2")
            result['status'] = 'degraded'
        
        # Calculate yield curve spread
        if result['GS10_current'] is not None and result['GS2_current'] is not None:
            result['yield_curve_10y_2y'] = result['GS10_current'] - result['GS2_current']
            logger.info(f"Yield curve (10Y-2Y): {result['yield_curve_10y_2y']:.2f}%")
            
        if result['GS10_prev'] is not None and result['GS2_prev'] is not None:
            result['yield_curve_10y_2y_prev'] = result['GS10_prev'] - result['GS2_prev']
        
        return result
    
    def fetch_cpi(self) -> Dict[str, Any]:
        """Fetch Consumer Price Index (CPI)."""
        result = {
            'CPI_latest': None,
            'CPI_YOY': None,
            'CPI_date': None,
            'CPI_history': None,
            'data_age_days': None,
            'status': 'ok',
            'warnings': []
        }
        
        # Fetch 14 months history for YoY (12 month window + margin)
        days_lookback = 450 
        
        cpi_data = self._fetch_series('CPIAUCSL', days=days_lookback)
        
        if cpi_data is not None and len(cpi_data) > 0:
            latest_val = float(cpi_data.iloc[-1])
            latest_date = cpi_data.index[-1]
            
            result['CPI_latest'] = latest_val
            if len(cpi_data) > 1:
                result['CPI_prev'] = float(cpi_data.iloc[-2])
            result['CPI_date'] = latest_date.strftime('%Y-%m-%d')
            result['CPI_history'] = [
                {'date': date.strftime('%Y-%m-%d'), 'value': float(value)}
                for date, value in cpi_data.items()
            ]
            
            # Calculate YoY
            # Find closest date 12 months ago
            target_date = latest_date - timedelta(days=365)
            # Find closest index
            try:
                # Find index with nearest date
                idx = cpi_data.index.get_indexer([target_date], method='nearest')[0]
                val_year_ago = float(cpi_data.iloc[idx])
                # Check if date is reasonable (within 15 days of target)
                date_year_ago = cpi_data.index[idx]
                if abs((date_year_ago - target_date).days) < 20:
                    yoy = (latest_val / val_year_ago) - 1
                    result['CPI_YOY'] = yoy * 100 # stored as percentage e.g. 3.2
                    logger.info(f"CPI YoY: {result['CPI_YOY']:.2f}%")
                else:
                    logger.warning(f"Could not find exact 1-year ago match for CPI. Closest: {date_year_ago}")

                # Calculate Trend (Previous Month YoY)
                if len(cpi_data) >= 2:
                    prev_val = float(cpi_data.iloc[-2])
                    prev_date = cpi_data.index[-2]
                    target_prev = prev_date - timedelta(days=365)
                    try:
                        idx_prev = cpi_data.index.get_indexer([target_prev], method='nearest')[0]
                        val_year_ago_prev = float(cpi_data.iloc[idx_prev])
                        date_year_ago_prev = cpi_data.index[idx_prev]
                        if abs((date_year_ago_prev - target_prev).days) < 20:
                            yoy_prev = (prev_val / val_year_ago_prev) - 1
                            result['CPI_YOY_prev'] = yoy_prev * 100
                    except:
                        pass
            except Exception as e:
                logger.warning(f"Error calc CPI YoY: {e}")
            
            data_age = (datetime.now() - latest_date).days
            result['data_age_days'] = data_age
            
            if data_age > 45:
                warning = f"CPI data is {data_age} days old (last: {result['CPI_date']})"
                result['warnings'].append(warning)
                logger.warning(warning)
            
            logger.info(f"CPI Index: {result['CPI_latest']:.1f} (as of {result['CPI_date']})")
        else:
            result['warnings'].append("Failed to fetch CPI")
            result['status'] = 'degraded'
        
        return result
        
    def fetch_employment_data(self) -> Dict[str, Any]:
        """Fetch Employment Data (Unemployment Rate, Initial Claims)."""
        result = {
            'UNRATE': None,
            'ICSA': None, # Initial Claims
            'CCSA': None, # Continued Claims
            'status': 'ok', 
            'warnings': []
        }
        
        # 1. Unemployment Rate (Monthly)
        unrate = self._get_latest_point('UNRATE', days_lookback=90)
        if unrate:
            result['UNRATE'] = unrate
            logger.info(f"Unemployment Rate: {unrate['value']:.1f}% ({unrate['date']})")
        else:
            result['warnings'].append("Failed to fetch UNRATE")
            
        # 2. Initial Jobless Claims (Weekly)
        icsa = self._get_latest_point('ICSA', days_lookback=30)
        if icsa:
            result['ICSA'] = icsa
            logger.info(f"Initial Claims: {icsa['value']:,.0f} ({icsa['date']})")
        else:
            result['warnings'].append("Failed to fetch ICSA")

        # 3. Continued Claims (Weekly)
        ccsa = self._get_latest_point('CCSA', days_lookback=30)
        if ccsa:
            result['CCSA'] = ccsa
        else:
            # Not critical, suppress warning
            pass
            
        if not result['UNRATE'] and not result['ICSA']:
            result['status'] = 'degraded'

        return result

    def fetch_sentiment_and_risk(self) -> Dict[str, Any]:
        """Fetch Sentiment and Risk Indicators."""
        result = {
            'UMCSENT': None,    # Consumer Sentiment
            'STLFSI3': None,    # Financial Stress
            'HY_SPREAD': None,  # High Yield Spread
            'status': 'ok',
            'warnings': []
        }
        
        # 1. Consumer Sentiment (Monthly)
        umcsent = self._get_latest_point('UMCSENT', days_lookback=90)
        if umcsent:
            result['UMCSENT'] = umcsent
            logger.info(f"Consumer Sentiment: {umcsent['value']:.1f}")
        else:
             result['warnings'].append("Failed to fetch UMCSENT")

        # 2. Financial Stress Index (Weekly)
        # STLFSI3 discontinued, replaced by STLFSI4
        stress = self._get_latest_point('STLFSI4', days_lookback=60)
        if stress:
            result['STLFSI3'] = stress # Keep key same for Aggregator compatibility or update it? 
            # Aggregator uses f_rsk.get('STLFSI3')
            # Let's keep the internal key 'STLFSI3' in the result dict to avoid breaking Aggregator mapping
            # satisfying "Fin Stress Idx': f_rsk.get('STLFSI3')" in aggregator.
        else:
             result['warnings'].append("Failed to fetch STLFSI4 (Fin Stress)")
        
        # 3. High Yield Option-Adjusted Spread (Daily)
        hy_spread = self._get_latest_point('BAMLH0A0HYM2', days_lookback=10)
        if hy_spread:
            result['HY_SPREAD'] = hy_spread
            logger.info(f"HY Spread: {hy_spread['value']:.2f}%")
        else:
             result['warnings'].append("Failed to fetch High Yield Spread")
             
        return result

    def fetch_all(self) -> Dict[str, Any]:
        """
        Fetch all FRED data.
        
        Returns:
            Combined dict with all indicators
        """
        logger.info("=" * 50)
        logger.info("Fetching FRED economic data...")
        logger.info("=" * 50)
        
        treasury = self.fetch_treasury_yields()
        inflation = self.fetch_cpi()
        employment = self.fetch_employment_data()
        risk_sentiment = self.fetch_sentiment_and_risk()
        
        # Combine results
        result = {
            'treasury_yields': {k: v for k, v in treasury.items() if k not in ['status', 'warnings']},
            'inflation': {k: v for k, v in inflation.items() if k not in ['status', 'warnings']},
            'employment': {k: v for k, v in employment.items() if k not in ['status', 'warnings']},
            'risk_sentiment': {k: v for k, v in risk_sentiment.items() if k not in ['status', 'warnings']},
            
            'status': 'ok' if all(x['status'] == 'ok' for x in [treasury, inflation, employment]) else 'degraded',
            'warnings': treasury['warnings'] + inflation['warnings'] + employment['warnings'] + risk_sentiment['warnings']
        }
        
        logger.info(f"FRED fetch complete. Status: {result['status']}")
        if result['warnings']:
            logger.warning(f"Warnings: {', '.join(result['warnings'])}")
        
        return result

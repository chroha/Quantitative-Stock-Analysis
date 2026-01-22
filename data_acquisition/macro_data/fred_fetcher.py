"""
FRED Data Fetcher - 从FRED获取宏观经济数据

Fetches economic indicators from FRED (Federal Reserve Economic Data):
- GS10: 10-Year Treasury Yield
- GS2: 2-Year Treasury Yield  
- CPIAUCSL: Consumer Price Index

提供缓存机制和错误处理
"""

import os
import json
import time
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path
from utils.logger import setup_logger

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
        self.lookback_days = self.config.get('lookback_periods', {})
        self.cache_ttl = self.config.get('cache_ttl_seconds', {}).get('fred_data', 3600)
        self.cpi_ttl = self.config.get('cache_ttl_seconds', {}).get('fred_cpi', 86400)
        
        # Setup cache directory
        self.cache_dir = Path(__file__).parent / 'data' / '.cache'
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
        """Load default configuration."""
        config_path = Path(__file__).parent / 'macro_config.json'
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
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
                # Get recent data and take latest (default 30 days)
                start_date = datetime.now() - timedelta(days=30)
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
                    data = self.fred.get_series(series_id, observation_start=datetime.now() - timedelta(days=30))
                
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
            
    def fetch_treasury_yields(self) -> Dict[str, Any]:
        """
        Fetch Treasury yield data (GS10, GS2).
        
        Returns:
            Dict with current yields and historical GS2 data
        """
        result = {
            'GS10_current': None,
            'GS2_current': None,
            'GS2_historical': None,
            'yield_curve_10y_2y': None,
            'status': 'ok',
            'warnings': []
        }
        
        # Fetch GS10 (current value)
        gs10_data = self._fetch_series('GS10')
        if gs10_data is not None and len(gs10_data) > 0:
            result['GS10_current'] = float(gs10_data.iloc[-1])
            logger.info(f"GS10 (10Y Treasury): {result['GS10_current']:.2f}%")
        else:
            result['warnings'].append("Failed to fetch GS10")
            result['status'] = 'degraded'
        
        # Fetch GS2 (current + historical)
        gs2_days = self.lookback_days.get('GS2_days', 60)
        gs2_data = self._fetch_series('GS2', days=gs2_days)
        if gs2_data is not None and len(gs2_data) > 0:
            result['GS2_current'] = float(gs2_data.iloc[-1])
            result['GS2_historical'] = [
                {'date': date.strftime('%Y-%m-%d'), 'value': float(value)}
                for date, value in gs2_data.items()
            ]
            logger.info(f"GS2 (2Y Treasury): {result['GS2_current']:.2f}% ({len(gs2_data)} days)")
        else:
            result['warnings'].append("Failed to fetch GS2")
            result['status'] = 'degraded'
        
        # Calculate yield curve spread
        if result['GS10_current'] and result['GS2_current']:
            result['yield_curve_10y_2y'] = result['GS10_current'] - result['GS2_current']
            logger.info(f"Yield curve (10Y-2Y): {result['yield_curve_10y_2y']:.2f}%")
        
        return result
    
    def fetch_cpi(self) -> Dict[str, Any]:
        """
        Fetch Consumer Price Index (CPI) data including history for YoY calc.
        
        Returns:
            Dict with latest CPI value, history, and metadata
        """
        result = {
            'CPI_latest': None,
            'CPI_date': None,
            'CPI_history': None,
            'data_age_days': None,
            'status': 'ok',
            'warnings': []
        }
        
        # Fetch 13 months history for YoY calculation
        months = self.config.get('lookback_periods', {}).get('cpi_months', 13)
        days_lookback = months * 31  # Approx days
        
        cpi_data = self._fetch_series('CPIAUCSL', days=days_lookback)
        
        if cpi_data is not None and len(cpi_data) > 0:
            result['CPI_latest'] = float(cpi_data.iloc[-1])
            result['CPI_date'] = cpi_data.index[-1].strftime('%Y-%m-%d')
            
            # Store history list for aggregator to calculate YoY
            result['CPI_history'] = [
                {'date': date.strftime('%Y-%m-%d'), 'value': float(value)}
                for date, value in cpi_data.items()
            ]
            
            # Check data staleness
            data_age = (datetime.now() - cpi_data.index[-1]).days
            result['data_age_days'] = data_age
            
            if data_age > 45:
                warning = f"CPI data is {data_age} days old (last: {result['CPI_date']})"
                result['warnings'].append(warning)
                logger.warning(warning)
            
            # Check if we have enough history for YoY (needs at least 13 months roughly)
            if len(cpi_data) < 12:
                result['warnings'].append("CPI history less than 12 months, YoY may be unreliable")
            
            logger.info(f"CPI: {result['CPI_latest']:.1f} (as of {result['CPI_date']}, {data_age} days ago)")
        else:
            result['warnings'].append("Failed to fetch CPI")
            result['status'] = 'degraded'
        
        return result
        
    def fetch_unemployment(self) -> Dict[str, Any]:
        """
        Fetch Unemployment Rate (UNRATE).
        
        Returns:
            Dict with latest UNRATE value
        """
        result = {
            'UNRATE_current': None,
            'UNRATE_date': None,
            'status': 'ok',
            'warnings': []
        }
        
        unrate_data = self._fetch_series('UNRATE', days=60) # Last 2 months is enough for latest
        
        if unrate_data is not None and len(unrate_data) > 0:
            result['UNRATE_current'] = float(unrate_data.iloc[-1])
            result['UNRATE_date'] = unrate_data.index[-1].strftime('%Y-%m-%d')
            logger.info(f"Unemployment Rate: {result['UNRATE_current']:.1f}% ({result['UNRATE_date']})")
        else:
            result['warnings'].append("Failed to fetch Unemployment Rate")
            result['status'] = 'degraded'
            
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
        unemployment = self.fetch_unemployment()
        
        # Combine results
        result = {
            'treasury_yields': {k: v for k, v in treasury.items() if k not in ['status', 'warnings']},
            'inflation': {k: v for k, v in inflation.items() if k not in ['status', 'warnings']},
            'employment': {k: v for k, v in unemployment.items() if k not in ['status', 'warnings']},
            'status': 'ok' if all(x['status'] == 'ok' for x in [treasury, inflation, unemployment]) else 'degraded',
            'warnings': treasury['warnings'] + inflation['warnings'] + unemployment['warnings']
        }
        
        logger.info(f"FRED fetch complete. Status: {result['status']}")
        if result['warnings']:
            logger.warning(f"Warnings: {', '.join(result['warnings'])}")
        
        return result

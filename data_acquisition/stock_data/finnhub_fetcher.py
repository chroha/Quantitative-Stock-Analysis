"""
Finnhub Data Fetcher - Fifth-tier data source for forecast/estimates data.
Used to supplement FMP forecast data and provide broader coverage.

API Documentation: https://finnhub.io/docs/api

Key Endpoints:
- /stock/earnings: Earnings surprises and estimates
- /stock/revenue-estimates: Revenue forecasts
- /stock/eps-estimates: EPS forecasts  
- /stock/ebitda-estimates: EBITDA forecasts
"""

import os
import requests
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from config import constants
from utils.logger import setup_logger
from utils.unified_schema import (
    CompanyProfile, FieldWithSource, TextFieldWithSource
)
from data_acquisition.stock_data.base_fetcher import BaseFetcher, DataSource, FetcherRegistry

logger = setup_logger('finnhub_fetcher')


class FinnhubFetcher(BaseFetcher):
    """
    Fetches forecast/estimates data from Finnhub API.
    Used as fifth-tier data source primarily for forward-looking estimates.
    """
    
    BASE_URL = constants.FINNHUB_BASE_URL
    _last_request_time = 0
    _min_request_interval = 1.0  # Rate limit: 60 calls/minute (free tier)
    
    def __init__(self, symbol: str):
        self.symbol = symbol.upper()
        self.api_key = os.getenv('FINNHUB_API_KEY')
        
        if not self.api_key:
            logger.warning("FINNHUB_API_KEY not found in environment variables")
    
    def _rate_limit(self):
        """Enforce rate limiting between API calls (60 calls/minute for free tier)."""
        elapsed = time.time() - FinnhubFetcher._last_request_time
        if elapsed < self._min_request_interval:
            sleep_time = self._min_request_interval - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        FinnhubFetcher._last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict]:
        """
        Make API request with rate limiting and error handling.
        
        Args:
            endpoint: Finnhub endpoint path (e.g., 'stock/profile2')
            params: Additional query parameters
            
        Returns:
            JSON response dict or None on failure
        """
        if not self.api_key:
            logger.error("Cannot make Finnhub request: API key not configured")
            return None
        
        self._rate_limit()
        
        url = f"{self.BASE_URL}/{endpoint}"
        request_params = {'token': self.api_key}
        
        if params:
            request_params.update(params)
        
        try:
            logger.debug(f"Finnhub request: {endpoint} with params {params}")
            response = requests.get(
                url,
                params=request_params,
                timeout=constants.FINNHUB_TIMEOUT_SECONDS
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Finnhub returns empty dict {} or list [] when no data available
                if not data or (isinstance(data, dict) and not data) or (isinstance(data, list) and not data):
                    logger.warning(f"Finnhub returned empty data for {endpoint}")
                    return None
                
                logger.info(f"Successfully fetched {endpoint} from Finnhub")
                return data
                
            elif response.status_code == 401:
                logger.error("Finnhub API authentication failed - check API key")
                return None
            elif response.status_code == 429:
                logger.warning("Finnhub rate limit exceeded")
                return None
            else:
                logger.error(f"Finnhub API error {response.status_code}: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"Finnhub request timeout for {endpoint}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Finnhub request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in Finnhub request: {e}")
            return None
    
    def _create_field_with_source(self, value: Any) -> Optional[FieldWithSource]:
        """Create FieldWithSource from raw value."""
        if value is None or value == '':
            return None
        try:
            return FieldWithSource(value=value, source='finnhub')
        except:
            return None
    
    def fetch_profile(self) -> Optional[CompanyProfile]:
        """
        Fetch company profile/overview.
        Endpoint: /stock/profile2
        """
        data = self._make_request(constants.FINNHUB_ENDPOINTS['profile'], {'symbol': self.symbol})
        
        if not data:
            return None
        
        try:
            return CompanyProfile(
                std_company_name=TextFieldWithSource(value=data.get('name'), source='finnhub'),
                std_industry=TextFieldWithSource(value=data.get('finnhubIndustry'), source='finnhub'),
                std_sector=TextFieldWithSource(value=data.get('ggroup'), source='finnhub'),  # GICS group
                std_country=TextFieldWithSource(value=data.get('country'), source='finnhub'),
                std_currency=TextFieldWithSource(value=data.get('currency'), source='finnhub'),
                std_exchange=TextFieldWithSource(value=data.get('exchange'), source='finnhub'),
                std_market_cap=self._create_field_with_source(data.get('marketCapitalization')),
            )
        except Exception as e:
            logger.error(f"Failed to parse Finnhub profile: {e}")
            return None
    
    def fetch_earnings_estimates(self) -> Optional[List[Dict]]:
        """
        Fetch earnings estimates and surprises.
        Endpoint: /stock/earnings
        
        Returns:
            List of earnings data with actual vs estimates
        """
        data = self._make_request(constants.FINNHUB_ENDPOINTS['earnings_estimates'], {'symbol': self.symbol})
        
        if not data or not isinstance(data, list):
            return None
        
        logger.info(f"Fetched {len(data)} earnings records from Finnhub")
        return data
    
    def fetch_revenue_estimates(self) -> Optional[List[Dict]]:
        """
        Fetch revenue estimates.
        Endpoint: /stock/revenue-estimates
        
        Returns:
            List of revenue estimate data
        """
        data = self._make_request(constants.FINNHUB_ENDPOINTS['revenue_estimates'], {'symbol': self.symbol})
        
        if not data or not isinstance(data, dict):
            return None
        
        # Finnhub revenue estimates format: {"data": [...], "symbol": "AAPL"}
        estimates = data.get('data', [])
        logger.info(f"Fetched {len(estimates)} revenue estimates from Finnhub")
        return estimates
    
    def fetch_eps_estimates(self) -> Optional[List[Dict]]:
        """
        Fetch EPS estimates.
        Endpoint: /stock/eps-estimates
        
        Returns:
            List of EPS estimate data
        """
        data = self._make_request(constants.FINNHUB_ENDPOINTS['eps_estimates'], {'symbol': self.symbol})
        
        if not data or not isinstance(data, dict):
            return None
        
        # Format: {"data": [...], "symbol": "AAPL"}
        estimates = data.get('data', [])
        logger.info(f"Fetched {len(estimates)} EPS estimates from Finnhub")
        return estimates
    
    def fetch_ebitda_estimates(self) -> Optional[List[Dict]]:
        """
        Fetch EBITDA estimates.
        Endpoint: /stock/ebitda-estimates
        
        Returns:
            List of EBITDA estimate data
        """
        data = self._make_request(constants.FINNHUB_ENDPOINTS['ebitda_estimates'], {'symbol': self.symbol})
        
        if not data or not isinstance(data, dict):
            return None
        
        estimates = data.get('data', [])
        logger.info(f"Fetched {len(estimates)} EBITDA estimates from Finnhub")
        return estimates


# Register this fetcher
FetcherRegistry.register(DataSource.FINNHUB, FinnhubFetcher)

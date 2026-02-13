"""
HTTP Utility module for standardized API requests.
Handles retries, timeouts, and common error logging.
"""

import time
import requests
from typing import Optional, Dict, Any, Union
from utils.logger import setup_logger

logger = setup_logger('http_utils')

def make_request(
    url: str, 
    params: Optional[Dict[str, Any]] = None, 
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 10,
    retries: int = 3,
    retry_delay: float = 1.0,
    source_name: str = "API"
) -> Optional[Union[Dict, list]]:
    """
    Make an HTTP GET request with retries and error handling.

    Args:
        url: The full URL to request.
        params: Query parameters dictionary.
        headers: Request headers dictionary.
        timeout: Request timeout in seconds.
        retries: Number of retry attempts for transient errors.
        retry_delay: Delay in seconds between retries (exponential backoff applied).
        source_name: Name of the data source for logging.

    Returns:
        Parses JSON response if successful, None otherwise.
    """
    attempt = 0
    while attempt <= retries:
        try:
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in (429, 500, 502, 503, 504):
                # Transient errors - retry
                logger.warning(f"{source_name} HTTP {e.response.status_code}: {e}. Retrying ({attempt+1}/{retries})...")
            
            elif e.response.status_code == 403:
                logger.warning(f"{source_name} 403 Forbidden. Feature not available on current plan or key invalid.")
                return None
            
            elif e.response.status_code == 402:
                 logger.warning(f"{source_name} 402 Payment/Plan Required. Feature not available on current plan.")
                 return None

            elif e.response.status_code == 404:
                logger.warning(f"{source_name} 404 Not Found: {url}")
                return None
            else:
                 # Non-transient error
                logger.error(f"{source_name} HTTP error: {e}")
                return None

        except requests.exceptions.RequestException as e:
            logger.warning(f"{source_name} connection error: {e}. Retrying ({attempt+1}/{retries})...")
        
        except ValueError as e:
            logger.error(f"{source_name} JSON parsing error: {e}")
            return None

        # Logic for retry loop
        attempt += 1
        if attempt <= retries:
            sleep_time = retry_delay * (2 ** (attempt - 1)) # Exponential backoff
            time.sleep(sleep_time)
            
    logger.error(f"{source_name} request failed after {retries} retries: {url}")
    return None

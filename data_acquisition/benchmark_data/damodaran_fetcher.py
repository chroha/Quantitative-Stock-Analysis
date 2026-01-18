"""
Damodaran data fetcher.
Fetches industry data from NYU Stern HTML pages (easier than Excel parsing).
"""

import pandas as pd
from pathlib import Path
from typing import Dict
from utils.logger import setup_logger

logger = setup_logger('damodaran_fetcher')


class DamodaranFetcher:
    """
    Fetch industry data from Damodaran's HTML pages.
    Source: https://pages.stern.nyu.edu/~adamodar/
    """
    
    BASE_URL = "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile"
    
    HTML_FILES = {
        # Existing data sources (for financial scoring)
        'roc': 'roc.htm',      # Return on Capital, Operating Margin
        'wacc': 'wacc.htm',    # ROE, Cost of Equity
        'betas': 'betas.htm',  # Beta, CV of Operating Income
        'roe': 'roe.htm',      # Return on Equity
        
        # New data sources for valuation multiples
        'pbv': 'pbvdata.htm',        # Price/Book Ratio
        'pe': 'pedata.htm',          # PE Ratio (Current, Trailing, Forward)
        'ps': 'psdata.htm',          # Price/Sales Ratio
        'ev_ebitda': 'vebitda.htm',  # EV/EBITDA, EV/Sales
        'margins': 'margin.htm',     # Operating, Pre-tax, Net Margin
        'div_yield': 'divfund.htm',  # Dividend Yield, Payout Ratio (was divyield.htm)
    }
    
    def __init__(self, cache_dir: str = 'user_config'):
        """
        Initialize fetcher.
        
        Args:
            cache_dir: Directory to cache downloaded data (CSV format)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Damodaran fetcher initialized (cache: {cache_dir})")
    
    def fetch_html_table(self, file_key: str, force_refresh: bool = False) -> pd.DataFrame:
        """
        Fetch data from HTML page and parse table.
        
        Args:
            file_key: File key ('roc', 'wacc', or 'betas')
            force_refresh: If True, bypass cache and re-fetch
            
        Returns:
            DataFrame with industry data
        """
        if file_key not in self.HTML_FILES:
            raise ValueError(f"Unknown file key: {file_key}")
        
        # Check cache first
        cache_file = self.cache_dir / f"{file_key}_data.csv"
        if cache_file.exists() and not force_refresh:
            logger.info(f"Loading cached {file_key} data from {cache_file}")
            return pd.read_csv(cache_file)
        
        # Fetch from web
        html_file = self.HTML_FILES[file_key]
        url = f"{self.BASE_URL}/{html_file}"
        
        logger.info(f"Fetching {file_key} data from {url}...")
        
        try:
            # Special case: EV/EBITDA has multi-row header (row 0 is categories, row 1 is actual columns)
            if file_key == 'ev_ebitda':
                tables = pd.read_html(url, header=1)  # Skip first row, use second as header
            else:
                tables = pd.read_html(url, header=0)
            
            if not tables:
                raise ValueError(f"No tables found in {url}")
            
            # Take the first (and usually only) table
            df = tables[0]
            
            # Clean up column names (strip whitespace)
            df.columns = df.columns.str.strip()
            
            logger.info(f"Fetched {file_key} data: {len(df)} rows, {len(df.columns)} columns")
            logger.debug(f"Columns: {list(df.columns)}")
            
            # Cache to CSV for faster subsequent loads
            df.to_csv(cache_file, index=False)
            logger.info(f"Cached data to {cache_file}")
            
            return df
        
        except Exception as e:
            logger.error(f"Failed to fetch {file_key} from {url}: {e}")
            raise
    
    def fetch_all(self, force_refresh: bool = False) -> Dict[str, pd.DataFrame]:
        """
        Fetch all required datasets.
        
        Args:
            force_refresh: If True, bypass cache and re-fetch all data
            
        Returns:
            Dictionary mapping file keys to DataFrames
        """
        logger.info("Fetching all Damodaran datasets...")
        
        data = {}
        for file_key in self.HTML_FILES.keys():
            try:
                data[file_key] = self.fetch_html_table(file_key, force_refresh)
            except Exception as e:
                # Make div_yield optional - don't fail if it's not available
                if file_key == 'div_yield':
                    logger.warning(f"Dividend yield data not available (404), continuing without it")
                    data[file_key] = None
                else:
                    logger.error(f"Failed to fetch {file_key}: {e}")
                    raise
        
        logger.info(f"Successfully fetched {len([v for v in data.values() if v is not None])} datasets")
        return data
    
    def check_cache_exists(self) -> Dict[str, bool]:
        """
        Check which datasets are cached locally.
        
        Returns:
            Dictionary mapping file keys to cache existence status
        """
        status = {}
        for file_key in self.HTML_FILES.keys():
            cache_file = self.cache_dir / f"{file_key}_data.csv"
            status[file_key] = cache_file.exists()
        
        return status
    
    def clear_cache(self):
        """Clear all cached CSV files."""
        for file_key in self.HTML_FILES.keys():
            cache_file = self.cache_dir / f"{file_key}_data.csv"
            if cache_file.exists():
                cache_file.unlink()
                logger.info(f"Cleared cache: {cache_file}")


"""
Configuration settings loader with secure API key management.
Loads environment variables from .env file and provides masked logging.
Now supports multiple API keys via APIKeyManager for rotation.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from .api_key_manager import APIKeyManager

# Load environment variables from .env
project_root = Path(__file__).parent.parent
env_path = project_root / '.env'
load_dotenv(dotenv_path=env_path)


class Settings:
    """Application settings with secure API key handling and rotation support."""
    
    def __init__(self):
        self.manager = APIKeyManager()
        
        # Register keys from environment variables
        # The manager handles parsing comma-separated strings
        self.manager.register('FMP', os.getenv('FMP_API_KEY'))
        self.manager.register('GOOGLE', os.getenv('GOOGLE_AI_KEY'))
        self.manager.register('ALPHAVANTAGE', os.getenv('ALPHAVANTAGE_API_KEY'))
        self.manager.register('FRED', os.getenv('FRED_API_KEY'))
        self.manager.register('FINNHUB', os.getenv('FINNHUB_API_KEY'))
        
        # Validate required environment variables
        if not self.manager.validate_has_key('FMP'):
            raise ValueError(
                "FMP_API_KEY not found in environment variables. "
                "Please create a .env file with FMP_API_KEY=your_key"
            )
            
        # Other keys are optional/fallback, so we don't strictly raise error
        # but the manager will return None if they are missing.
    
    # --- Dynamic Properties for Key Rotation ---
    
    @property
    def FMP_API_KEY(self) -> str | None:
        return self.manager.get('FMP')

    @property
    def GOOGLE_AI_KEY(self) -> str | None:
        return self.manager.get('GOOGLE')

    @property
    def ALPHAVANTAGE_API_KEY(self) -> str | None:
        return self.manager.get('ALPHAVANTAGE')

    @property
    def FRED_API_KEY(self) -> str | None:
        return self.manager.get('FRED')

    @property
    def FINNHUB_API_KEY(self) -> str | None:
        return self.manager.get('FINNHUB')

    # --- Rotation Control ---

    def rotate_keys(self):
        """
        Manually rotate to the next set of keys.
        Useful for long-running batch processes like run_scanner.py.
        """
        return self.manager.rotate()

    def get_key_count(self, provider: str) -> int:
        """Get number of keys configured for a specific provider."""
        return self.manager.get_key_count(provider)

    # --- Helpers ---

    @staticmethod
    def mask_api_key(api_key: str) -> str:
        """
        Mask API key for secure logging.
        Shows only first 4 and last 4 characters.
        
        Args:
            api_key: The API key to mask
            
        Returns:
            Masked API key (e.g., 'ltwM...I4ha')
        """
        if not api_key or len(api_key) < 8:
            return "****"
        return f"{api_key[:4]}...{api_key[-4:]}"
    
    def get_masked_fmp_key(self) -> str:
        """Get masked FMP API key for logging."""
        # Note: calling self.FMP_API_KEY triggers the property getter
        # so this always logs the CURRENT active key
        return self.mask_api_key(self.FMP_API_KEY)


# Global settings instance
settings = Settings()

"""
Configuration settings loader with secure API key management.
Loads environment variables from .env file and provides masked logging.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from user_config/.env
project_root = Path(__file__).parent.parent
env_path = project_root / 'user_config' / '.env'
load_dotenv(dotenv_path=env_path)


class Settings:
    """Application settings with secure API key handling."""
    
    def __init__(self):
        self.FMP_API_KEY = os.getenv('FMP_API_KEY')
        
        # Validate required environment variables
        if not self.FMP_API_KEY:
            raise ValueError(
                "FMP_API_KEY not found in environment variables. "
                "Please create a .env file with FMP_API_KEY=your_key"
            )
            
        self.GOOGLE_AI_KEY = os.getenv('GOOGLE_AI_KEY')
        # Google AI Key is optional for core functionality, but needed for commentary module
        # We won't raise error here to avoid breaking other modules if user doesn't have it
        
        self.ALPHAVANTAGE_API_KEY = os.getenv('ALPHAVANTAGE_API_KEY')
        # Alpha Vantage is optional - used as fallback data source
    
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
        return self.mask_api_key(self.FMP_API_KEY)


# Global settings instance
settings = Settings()

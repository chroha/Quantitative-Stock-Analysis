"""
Logging utilities with automatic API key masking for security.
"""

import logging
import re
from typing import Optional
from config.settings import settings


class SecureFormatter(logging.Formatter):
    """Custom formatter that masks API keys in log messages."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pattern to detect potential API keys (long alphanumeric strings)
        self.api_key_pattern = re.compile(r'\b[A-Za-z0-9]{20,}\b')
    
    def format(self, record):
        # Get the original formatted message
        message = super().format(record)
        
        # Mask any long alphanumeric strings that look like API keys
        def mask_match(match):
            key = match.group(0)
            return settings.mask_api_key(key)
        
        # Replace potential API keys with masked versions
        masked_message = self.api_key_pattern.sub(mask_match, message)
        return masked_message


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Setup a logger with secure formatting.
    
    Args:
        name: Logger name
        level: Logging level (default: INFO)
        log_file: Optional file path for file logging
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Console handler with secure formatting
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # Format with timestamp, level, and message
    formatter = SecureFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Optional file handler
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# Default logger for the application
default_logger = setup_logger('stock_analysis', level=logging.INFO)

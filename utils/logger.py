"""
Logging utilities with automatic API key masking for security.
Supports context-aware logging for orchestration vs standalone execution.
"""

import logging
import re
import os
from typing import Optional
from enum import Enum
from config.settings import settings


class LoggingContext(Enum):
    """Logging context modes for different execution scenarios."""
    STANDALONE = "standalone"      # Module run independently (full logging)
    ORCHESTRATED = "orchestrated"  # Called by run_analysis.py (quiet sub-modules)
    SILENT = "silent"              # Batch scanning (minimal output)
    PIPELINE_QUIET = "pipeline_quiet" # User-facing pipeline (clean output)


# Global logging mode (default: check env var, else standalone)
_env_mode = os.getenv('LOG_MODE', 'standalone').lower()
try:
    _CURRENT_MODE = LoggingContext(_env_mode)
except ValueError:
    _CURRENT_MODE = LoggingContext.STANDALONE

# Console loggers that should always show INFO level (orchestration scripts)
CONSOLE_LOGGERS = {
    'run_analysis', 'run_scanner', 'run_commentary',
    'run_financial_scoring', 'run_technical_scoring',
    'run_valuation', 'run_financial_data', 'run_benchmarks',
    'run_stock_fetch'
}


def set_logging_mode(mode: LoggingContext):
    """
    Set the global logging mode.
    
    Args:
        mode: LoggingContext enum value
    """
    global _CURRENT_MODE
    _CURRENT_MODE = mode


def get_logging_mode() -> LoggingContext:
    """Get the current logging mode."""
    return _CURRENT_MODE


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
    Setup a logger with secure formatting and context-aware levels.
    
    Args:
        name: Logger name
        level: Logging level (default: INFO, may be overridden by mode)
        log_file: Optional file path for file logging
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Determine effective level based on current mode
    effective_level = level
    current_mode = get_logging_mode()
    
    if current_mode == LoggingContext.ORCHESTRATED:
        # In orchestrated mode, only console loggers get INFO, others get ERROR
        if name not in CONSOLE_LOGGERS:
            effective_level = logging.ERROR
    elif current_mode == LoggingContext.SILENT:
        # In silent mode, everything is CRITICAL
        effective_level = logging.CRITICAL
    elif current_mode == LoggingContext.PIPELINE_QUIET:
         # In pipeline quiet mode, suppress almost everything except explicit errors
         # We rely on print() in run_pipeline.py for user progress
         effective_level = logging.ERROR

    # STANDALONE mode uses the provided level (default INFO)
    
    logger.setLevel(effective_level)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Console handler with secure formatting
    console_handler = logging.StreamHandler()
    console_handler.setLevel(effective_level)
    
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
        file_handler.setLevel(effective_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# Default logger for the application
default_logger = setup_logger('stock_analysis', level=logging.INFO)


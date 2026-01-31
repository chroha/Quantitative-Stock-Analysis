"""
Run Macro Data Fetch - CLI entry point for macro data acquisition
"""

import sys
import shutil
import argparse
import json
from pathlib import Path

# Add parent directory to path to import utils
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from data_acquisition.macro_data.macro_aggregator import MacroAggregator
from config.constants import DATA_CACHE_MACRO
from utils.logger import setup_logger

logger = setup_logger('run_macro_fetch')


def safe_print(text: str):
    """
    Safely print text that may contain emoji/unicode on Windows.
    Falls back to ASCII-only output if encoding fails.
    """
    try:
        print(text)
    except UnicodeEncodeError:
        # Remove emoji and non-ASCII characters for Windows console
        import re
        ascii_text = re.sub(r'[^\x00-\x7F]+', '', text)
        print(ascii_text)


def main():
    """Main entry point for macro data fetch."""
    from utils.console_utils import symbol
    
    # Parse Arguments
    parser = argparse.ArgumentParser(description="Fetch and analyze macro economic data.")
    parser.add_argument("--config", type=str, help="Path to config file (overrides default)")
    parser.add_argument("--force-fetch", action="store_true", help="Clear cache and force fetch")
    args = parser.parse_args()
    
    logger.info("Starting macro data fetch...")
    
    try:
        # Load config override if provided
        config = None
        if args.config:
            try:
                with open(args.config, 'r') as f:
                    config = json.load(f)
                logger.info(f"Loaded config from {args.config}")
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                return 1
        
        # Force Fetch: Clear cache directory
        if args.force_fetch:
            project_root = Path(__file__).parent.parent.parent
            cache_dir = project_root / DATA_CACHE_MACRO / '.cache'
            if cache_dir.exists():
                logger.info("Clearing cache for force fetch...")
                shutil.rmtree(cache_dir, ignore_errors=True)
                cache_dir.mkdir(exist_ok=True)
        
        # Initialize aggregator (FRED API key from environment)
        aggregator = MacroAggregator(config=config)
        
        # Fetch and save data
        snapshot = aggregator.run()
        
        # Display summary (use safe_print to handle emoji on Windows)
        summary = aggregator.get_summary(snapshot)
        safe_print("\n" + summary + "\n")
        
        # Check status
        status = snapshot['data_quality']['overall_status']
        if status == 'ok':
            logger.info(f"{symbol.OK} Macro data fetch completed successfully")
            return 0
        elif status == 'degraded':
            logger.warning(f"{symbol.WARN} Macro data fetch completed with warnings")
            return 1
        else:
            logger.error(f"{symbol.FAIL} Macro data fetch failed")
            return 2
    
    except Exception as e:
        logger.error(f"Fatal error during macro data fetch: {e}", exc_info=True)
        return 3


if __name__ == '__main__':
    sys.exit(main())

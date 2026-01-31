"""
Macro Data Acquisition Module

Fetches macroeconomic indicators from FRED and Yahoo Finance.
"""

from .fred_fetcher import FREDFetcher
from .yahoo_macro_fetcher import YahooMacroFetcher
from .macro_aggregator import MacroAggregator

__all__ = ['FREDFetcher', 'YahooMacroFetcher', 'MacroAggregator']

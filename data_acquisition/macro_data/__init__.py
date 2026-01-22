"""
Macro Data Acquisition Module - 宏观数据获取模块

Fetches macroeconomic indicators from FRED and Yahoo Finance.

从FRED和Yahoo Finance获取宏观经济指标
"""

from .fred_fetcher import FREDFetcher
from .yahoo_macro_fetcher import YahooMacroFetcher
from .macro_aggregator import MacroAggregator

__all__ = ['FREDFetcher', 'YahooMacroFetcher', 'MacroAggregator']

"""
Data Acquisition Module / 数据获取模块

该模块负责从外部API（Yahoo Finance, FMP）获取股票数据，并将其标准化为统一格式。
This module is responsible for fetching stock data from external APIs (Yahoo Finance, FMP) and normalizing it into a unified format.

主要入口点 / Main Entry Point:
    - StockDataLoader: 统一的数据加载器类 / Unified data loader class

主要数据模型 / Main Data Models:
    - StockData: 完整的股票数据对象 / Complete stock data object
    - DataSource: 数据源枚举 / Data source enumeration
"""

from .stock_data.initial_data_loader import StockDataLoader
from .benchmark_data.benchmark_data_loader import BenchmarkDataLoader
from utils.unified_schema import StockData, DataSource

__all__ = [
    'StockDataLoader',
    'BenchmarkDataLoader',
    'StockData',
    'DataSource',
]

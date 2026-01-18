"""
Fundamentals module - Financial metrics calculation and scoring.
Consumes StockData (Runtime) and Benchmark JSON (Reference) to produce scores.

基本面模块 - 财务指标计算与评分。
消耗 StockData（运行时数据）和基准 JSON（参考数据）以生成评分。
"""

from .financial_data import (
    ProfitabilityCalculator,
    GrowthCalculator,
    CapitalAllocationCalculator,
    ProfitabilityMetrics,
    GrowthMetrics,
    CapitalAllocationMetrics
)
from .financial_scorers import (
    CompanyScorer,
    MetricScorer
)
from .financial_data.financial_data_output import FinancialDataGenerator

__all__ = [
    'ProfitabilityCalculator',
    'GrowthCalculator',
    'CapitalAllocationCalculator',
    'ProfitabilityMetrics',
    'GrowthMetrics',
    'CapitalAllocationMetrics',
    'CompanyScorer',
    'MetricScorer',
    'FinancialDataGenerator',
]

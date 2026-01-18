"""
Fundamentals calculators package.

Process stock data into financial metrics (Profitability, Growth, Capital Allocation).
Basic Principle: Raw Data -> Calculation -> Logic/Formulas -> Metrics

基本面计算器包。
将股票数据处理为财务指标（盈利能力、增长、资本配置）。
基本原则：原始数据 -> 计算 -> 逻辑/公式 -> 指标
"""

from .calculator_base import CalculatorBase, CalculationResult, MetricWarning
from .profitability import ProfitabilityCalculator, ProfitabilityMetrics
from .growth import GrowthCalculator, GrowthMetrics
from .capital_allocation import CapitalAllocationCalculator, CapitalAllocationMetrics

__all__ = [
    'CalculatorBase',
    'CalculationResult',
    'MetricWarning',
    'ProfitabilityCalculator',
    'ProfitabilityMetrics',
    'GrowthCalculator',
    'GrowthMetrics',
    'CapitalAllocationCalculator',
    'CapitalAllocationMetrics',
]

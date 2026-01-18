"""
Scorers module - Converts calculated fundamentals into scores using industry benchmarks.

Takes output from calculators/ and score against sector_benchmarks.json.

评分模块 - 使用行业基准将计算出的基本面转换为评分。
获取 calculators/ 的输出，并对照 sector_benchmarks.json 进行评分。
"""

from fundamentals.financial_scorers.company_scorer import CompanyScorer
from fundamentals.financial_scorers.metric_scorer import MetricScorer
from fundamentals.financial_scorers.scoring_config import (
    CATEGORY_WEIGHTS,
    SECTOR_WEIGHT_OVERRIDES
)

__all__ = [
    'MetricScorer',
    'CompanyScorer',
    'CATEGORY_WEIGHTS',
]

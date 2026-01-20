"""
Metric Registry - Single source of truth for output metrics and indicators.

This registry defines the display names (English/Chinese) and formatting rules
for all metrics used in reports and analysis.
"""

from typing import Dict, NamedTuple, Optional
from enum import Enum

class MetricFormat(Enum):
    DECIMAL = 'decimal'
    PERCENT = 'percent'
    CURRENCY = 'currency'
    CURRENCY_LARGE = 'currency_large'
    STRING = 'string'

class MetricDefinition(NamedTuple):
    unified_key: str
    en_name: str
    cn_name: str
    format: MetricFormat
    description: str = ""

# =============================================================================
# FINANCIAL METRICS (Profitability, Growth, Capital)
# =============================================================================
FINANCIAL_METRICS: Dict[str, MetricDefinition] = {
    # Profitability
    'roic': MetricDefinition('roic', 'ROIC', '投资资本回报率', MetricFormat.PERCENT, 'Return on Invested Capital'),
    'roe': MetricDefinition('roe', 'ROE', '股本回报率', MetricFormat.PERCENT, 'Return on Equity'),
    'net_margin': MetricDefinition('net_margin', 'Net Profit Margin', '净利率', MetricFormat.PERCENT, ''),
    'operating_margin': MetricDefinition('operating_margin', 'Operating Margin', '营业利润率', MetricFormat.PERCENT, ''),
    'gross_margin': MetricDefinition('gross_margin', 'Gross Margin', '毛利率', MetricFormat.PERCENT, ''),
    
    # Growth
    'revenue_cagr_5y': MetricDefinition('revenue_cagr_5y', 'Revenue CAGR (5Y)', '5年营收复合增长', MetricFormat.PERCENT, ''),
    'net_income_cagr_5y': MetricDefinition('net_income_cagr_5y', 'Net Income CAGR (5Y)', '5年净利复合增长', MetricFormat.PERCENT, ''),
    'fcf_cagr_5y': MetricDefinition('fcf_cagr_5y', 'FCF CAGR (5Y)', '5年自由现金流增长', MetricFormat.PERCENT, ''),
    
    # Capital Allocation / Health
    'earnings_quality_3y': MetricDefinition('earnings_quality_3y', 'Quality of Earnings', '盈利质量(OCF/NI)', MetricFormat.DECIMAL, 'Ratio of Operating Cash Flow to Net Income'),
    'fcf_to_debt_ratio': MetricDefinition('fcf_to_debt_ratio', 'FCF to Debt', '自由现金流/债务', MetricFormat.DECIMAL, ''),
    'debt_coverage': MetricDefinition('debt_coverage', 'Debt Coverage', '债务覆盖率', MetricFormat.DECIMAL, ''),
    'share_dilution_cagr_5y': MetricDefinition('share_dilution_cagr_5y', 'Share Dilution CAGR', '股份稀释率(负为回购)', MetricFormat.PERCENT, ''),
    'capex_intensity_3y': MetricDefinition('capex_intensity_3y', 'Capex Intensity', '资本支出强度', MetricFormat.DECIMAL, 'Capex as % of Revenue (Decimal)'),
    'debt_to_equity': MetricDefinition('debt_to_equity', 'Debt to Equity', '债务股本比', MetricFormat.DECIMAL, ''),
}

# =============================================================================
# TECHNICAL INDICATORS
# =============================================================================
TECHNICAL_INDICATORS: Dict[str, MetricDefinition] = {
    'rsi': MetricDefinition('rsi', 'RSI', '相对强弱指数', MetricFormat.DECIMAL, ''),
    'macd': MetricDefinition('macd', 'MACD', '指数平滑异同移动平均', MetricFormat.DECIMAL, ''),
    'adx': MetricDefinition('adx', 'ADX', '平均趋向指数', MetricFormat.DECIMAL, ''),
    'atr': MetricDefinition('atr', 'ATR', '平均真实波幅', MetricFormat.DECIMAL, ''), 
    'obv': MetricDefinition('obv', 'OBV', '能量潮', MetricFormat.DECIMAL, ''),
    'roc': MetricDefinition('roc', 'ROC', '变动率(%)', MetricFormat.DECIMAL, ''),
    
    'current_price': MetricDefinition('current_price', 'Current Price', '当前价格', MetricFormat.CURRENCY, ''),
    'price_position': MetricDefinition('price_position', '52W Position', '52周位置(%)', MetricFormat.DECIMAL, 'Position within 52 week range'),
    'bollinger': MetricDefinition('bollinger', 'Bollinger/Bandwidth', '布林带/带宽', MetricFormat.DECIMAL, ''),
    'volume_ratio': MetricDefinition('volume_ratio', 'Volume Ratio', '量比', MetricFormat.DECIMAL, ''),
    'trend_strength': MetricDefinition('trend_strength', 'Trend Strength', '趋势强度', MetricFormat.DECIMAL, ''),
}

# =============================================================================
# VALUATION MODELS
# =============================================================================
VALUATION_MODELS: Dict[str, MetricDefinition] = {
    'pe': MetricDefinition('pe', 'PE Valuation', '市盈率估值', MetricFormat.CURRENCY, ''),
    'pb': MetricDefinition('pb', 'PB Valuation', '市净率估值', MetricFormat.CURRENCY, ''),
    'ps': MetricDefinition('ps', 'PS Valuation', '市销率估值', MetricFormat.CURRENCY, ''),
    'ev_ebitda': MetricDefinition('ev_ebitda', 'EV/EBITDA', '企业价值倍数', MetricFormat.CURRENCY, ''),
    'peg': MetricDefinition('peg', 'PEG Valuation', 'PEG估值', MetricFormat.CURRENCY, ''),
    'ddm': MetricDefinition('ddm', 'DDM Model', '股息折现模型', MetricFormat.CURRENCY, ''),
    'dcf': MetricDefinition('dcf', 'DCF Model', '自由现金流折现', MetricFormat.CURRENCY, ''),
    'graham': MetricDefinition('graham', 'Graham Number', '格雷厄姆估值', MetricFormat.CURRENCY, ''),
    'peter_lynch': MetricDefinition('peter_lynch', 'Peter Lynch Fair Value', '彼得林奇估值', MetricFormat.CURRENCY, ''),
    'analyst': MetricDefinition('analyst', 'Analyst Target', '分析师目标价', MetricFormat.CURRENCY, ''),
}

def get_metric_definition(key: str) -> Optional[MetricDefinition]:
    """Find definition for any metric key."""
    if key in FINANCIAL_METRICS: return FINANCIAL_METRICS[key]
    if key in TECHNICAL_INDICATORS: return TECHNICAL_INDICATORS[key]
    if key in VALUATION_MODELS: return VALUATION_MODELS[key]
    return None

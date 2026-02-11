"""
Utilities module for Quantitative Stock Analysis System.

=== 开发者必读 / DEVELOPER GUIDE ===

本目录包含项目的核心基础设施和通用工具。
开发前请先阅读参考文档:
  - 中文: utils/UTILS_REFERENCE_CN.md
  - English: utils/UTILS_REFERENCE.md

--- 常用工具速查 (Quick Reference) ---

1. 数值处理 (numeric_utils.py) ★ 最常用
   from utils.numeric_utils import clean_numeric, safe_divide, safe_format, is_valid_number
   - clean_numeric(value)        清洗数值(NaN/Inf/None → None)
   - safe_divide(a, b)           安全除法(除零保护)
   - safe_format(val, ".2f")     安全格式化(无效值→"N/A")
   - is_valid_number(value)      检查是否为有效有限数

2. 类型转换 (helpers.py)
   from utils.helpers import safe_float, safe_int, format_large_number, parse_date
   - safe_float(value, default)  安全转float
   - safe_int(value, default)    安全转int
   - format_large_number(val)    大数格式化(1234567 → "1.23M")
   - parse_date(date_str)        日期解析

3. 日志 (logger.py)
   from utils.logger import setup_logger
   - logger = setup_logger('module_name')
   - LoggingContext: 临时切换日志级别的上下文管理器

4. HTTP请求 (http_utils.py)
   from utils.http_utils import make_request
   - make_request(url, params, retries=3, source_name="API")
   - 内置重试、超时、指数退避
   - 自动处理429/5xx等瞬态错误

5. 控制台输出 (console_utils.py)
   from utils.console_utils import symbol, print_step, print_separator
   - symbol.OK / symbol.FAIL / symbol.WARN  (跨平台安全符号)
   - print_step(1, 5, "Processing...")

6. 报告格式化 (report_utils.py)
   from utils.report_utils import format_financial_score_report, format_valuation_report
   - 统一的报告格式化工具

--- 数据架构 (不直接import,了解即可) ---

7. unified_schema.py    数据模型定义(StockData, ForecastData等)
8. field_registry.py    字段映射(Yahoo/EDGAR/FMP/AV字段名对照)
9. schema_mapper.py     JSON→Schema转换逻辑
10. currency_normalizer.py  货币转换与ADR标准化
11. metric_registry.py  指标定义(中英文名称、格式化规则)
12. macro_translations.py   宏观指标翻译字典

=== 注意事项 ===
- 做数值计算时,务必使用 clean_numeric() 或 safe_divide(),不要裸用 Python 除法
- 做HTTP请求时,务必使用 make_request(),不要直接用 requests.get()
- 新增数据字段时,必须同步更新 unified_schema.py 和 field_registry.py
- 日志统一用 setup_logger(),不要用 print() 做调试输出
"""

from .logger import setup_logger, default_logger, LoggingContext, set_logging_mode, get_logging_mode
from .helpers import (
    safe_float,
    safe_int,
    format_large_number,
    parse_date,
    get_fiscal_year_quarter
)

__all__ = [
    'setup_logger',
    'default_logger',
    'safe_float',
    'safe_int',
    'format_large_number',
    'parse_date',
    'get_fiscal_year_quarter'
]

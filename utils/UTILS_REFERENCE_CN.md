# 工具与基础设施参考文档

本文档旨在帮助开发者了解 `utils/` 目录下的核心基础设施、数据架构和通用工具函数。

> **⚠️ 开发者须知**
>
> 在编写新模块或修改现有代码前，请确保：
>
> 1. **数值计算** → 使用 `numeric_utils.py` 中的 `clean_numeric()` / `safe_divide()`，禁止裸用 Python 除法
> 2. **HTTP 请求** → 使用 `http_utils.py` 中的 `make_request()`，禁止直接用 `requests.get()`（内置重试和错误处理）
> 3. **日志输出** → 使用 `logger.py` 中的 `setup_logger()`，避免用 `print()` 做调试
> 4. **新增数据字段** → 必须同步更新 `unified_schema.py` + `field_registry.py`
> 5. **格式化输出** → 使用 `safe_format()` 和 `format_large_number()` 确保 None/NaN 不会崩溃
>
> 快速入口: `utils/__init__.py` 中有完整的工具速查表

## 1. 核心数据架构

### `unified_schema.py`

- **用途**: 系统的“宪法”，使用 Pydantic 定义统一的数据模型。
- **核心模型**:
  - `StockData`: 包含单个股票所有数据的主对象。
  - `IncomeStatement`, `BalanceSheet`, `CashFlow`: 标准化三大财务报表。
  - `CompanyProfile`: 公司元数据（行业、板块、简介）。
  - `ForecastData`: **[NEW]** 前瞻预测数据模型,包含：
    - Forward EPS/PE (`std_forward_eps`, `std_forward_pe`)
    - 增长预期 (`std_earnings_growth_current_year`, `std_revenue_growth_next_year`)
    - 分析师目标价 (`std_price_target_low/high/consensus`)
    - Earnings Surprise History (`std_earnings_surprise_history`) - 最近4季度盈利意外记录
  - `FieldWithSource`: 带有来源追踪的值对象（例如：来源='yahoo'）。
- **规则**: 所有数据获取模块的输出必须符合此 schema 定义。

### `field_registry.py`

- **用途**: 中央字段注册表，负责将原始 API 字段映射到统一 Schema 字段名。
- **核心功能**:
  - **多源映射**: 例如将标准字段 `std_revenue` 映射到：
    - Yahoo: `Total Revenue`
    - EDGAR: `Revenues`, `SalesRevenueNet`
    - FMP: `revenue`
    - Alpha Vantage: `totalRevenue`
  - **优先级逻辑**: 定义数据合并时的来源优先级 (默认: Yahoo > FMP > EDGAR > AV)。
- **扩展指南**: 如果发现某些字段抓取失败，可以在此处添加新的 XBRL Tag 或 API 字段名。

### `schema_mapper.py`

- **用途**: 将原始 JSON 数据转换为 `unified_schema` 对象的转换逻辑。

### `currency_normalizer.py`

- **用途**: **国际股票的自动货币转换和ADR股份标准化**。
- **核心功能**:
  - **全局货币转换**: 自动检测并转换外币（如新台币、港币）财报数据为美元，使用实时汇率。
  - **ADR股份标准化**: 通过市值计算隐含ADR股数，并据此调整EPS。
  - **多层防护机制**:  
    - 转换255+个货币字段，覆盖所有数据源（Yahoo、FMP、EDGAR、Alpha Vantage）。
    - 重新计算EPS: `EPS_USD = 美元净利润 / ADR股数`。
    - 防止重复转换已处理数据（source='manual'）。
- **适用股票**: 主要针对ADR（台积电TSM、阿里BABA、京东JD），但可应用于任何非美元报告的公司。
- **技术细节**: 当公司档案中检测到 `FinancialCurrency != ListingCurrency` 时自动触发。

---

## 2. 指标与定义

### `metric_registry.py`

- **用途**: 所有财务和技术指标的“字典”。
- **内容**:
  - 定义指标 Key (如 `roic`, `rsi`)。
  - 存储中英文显示名称。
  - 定义格式化规则（百分比、货币、小数）。
- **用途**: 此文件决定了报告中指标的显示名称和单位。

### `macro_translations.py`

- **用途**: 宏观分析模块的翻译字典。
- **内容**: 包含宏观指标 KEY (如 `gdp`, `cpi`) 和报告 UI 元素的双语对照。

---

## 3. 辅助函数库

### `numeric_utils.py`

- **用途**: 提供安全的数值运算。
- **函数**:
  - `safe_float()`: 健壮的字符串转浮点数（自动处理 "N/A", "--"）。
  - `calculate_cagr()`: 复合年增长率计算。
  - `calculate_growth_rate()`: 简单的环比/同比计算。
  - `safe_divide()`: 带除零保护的除法运算。

### `http_utils.py`

- **用途**: 网络请求封装。
- **功能**:
  - `fetch_url()`: 封装了 User-Agent 轮换和错误处理的请求函数。
  - `RateLimiter`: API 请求限流器，防止触发 Alpha Vantage/FMP 的频率限制。
  - **智能错误处理**: 自动识别 403 Forbidden (如 Finnhub 权限不足) 并触发优雅降级，防止程序崩溃。

### `helpers.py`

- **用途**: 通用辅助工具。
- **功能**:
  - 日期解析与格式化。
  - 文件读写辅助。
  - 字符串处理。

---

## 4. 日志与输出

### `logger.py`

- **用途**: 中央日志配置。
- **功能**:
  - 多级别日志控制 (INFO, DEBUG, ERROR)。
  - 全局日志文件轮转策略。

### `console_utils.py`

- **用途**: 控制台富文本输出工具。
- **功能**:
  - 进度条显示。
  - 彩色状态信息 (成功绿色, 警告黄色, 错误红色)。

---

## 5. 报告生成

### `report_utils.py`

- **用途**: 生成文本和 Markdown 报告的辅助工具。
- **功能**:
  - Markdown 表格生成器。
  - 报告模板渲染辅助函数。

---

## 快速索引图

| 文件 | 用途 |
| :--- | :--- |
| `unified_schema.py` | **数据模型** (是什么) |
| `field_registry.py` | **字段映射** (在哪里) |
| `currency_normalizer.py` | **货币转换 & ADR标准化** |
| `metric_registry.py` | **指标定义** (怎么叫) |
| `numeric_utils.py` | **数学运算** (CAGR, Growth) |
| `http_utils.py` | **网络请求** (Fetch, Limit) |
| `logger.py` | **日志记录** |

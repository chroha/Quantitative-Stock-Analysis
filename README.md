# Quantitative Stock Analysis System V3.0 (量化股票分析系统)

## 简介
这是一个高阶的量化股票分析与筛选工具，旨在通过自动化的方式，对美股进行基本面、技术面和估值的全方位评估。它能够自动获取数据、计算复杂的财务指标、进行打分，并生成投资报告。

## 核心功能

### 1. 深度个股分析 (`run_analysis.py`)
针对单个股票进行全流程分析：
- **数据获取**: 采用 4 层级联数据源策略：
    - **T1 Yahoo Finance**: 主要数据源，提供实时行情和历史财报。
    - **T2 SEC EDGAR**: 官方 XBRL 数据源，直接从美国证监会获取原始财务报表。
    - **T3 FMP**: 补充分析师预期和其他结构化数据。
    - **T4 Alpha Vantage**: 最终后备源，填补冷门股票的数据空缺。
- **财务评分**: 基于 ROIC, ROE, 利润率, 增长率, 资本配置等 20+ 个指标进行加权打分 (0-100)。评分考虑了行业基准（Damodaran 数据）。
- **技术评分**: 结合 RSI, MACD, 均线系统 (SMA/EMA) 评估当前趋势与动能。
- **估值模型**: 
    - 现金流折现 (DCF)
    - 股利折现 (DDM)
    - 均值回归 (Graham Number, Peter Lynch)
    - 相对估值 (PE/PS Multiples)
- **AI 投资点评**: 调用 Google Gemini 模型，基于上述所有数据生成专业的投资见解与风险提示。

### 2. 批量选股扫描 (`run_scanner.py`)
- **批量处理**: 支持一次性扫描多个自选股。
- **快速评分**: 略过耗时的估值和AI步骤，专注于财务与技术面打分。
- **自动排名**: 结果按财务健康度 (Financial Score) 自动排序。
- **降级处理**: 智能识别并标记数据不足（如上市不足5年）的股票，并在报告中提供“可靠性降低”的提示。
- **输出**: 在控制台打印摘要，并生成包含详细指标的汇总文本报告。

## 目录结构
```
.
├── data_acquisition/       # 数据获取模块 (Yahoo, EDGAR, FMP, Alpha Vantage)
│   ├── benchmark_data/     # 行业基准数据获取
│   └── stock_data/         # 个股财务数据获取
├── fundamentals/           # 核心分析逻辑
│   ├── financial_data/     # 财务指标计算 (Growth, Profitability, Capital)
│   ├── financial_scorers/  # 财务评分引擎 (配置与权重)
│   ├── technical_scorers/  # 技术指标评分
│   ├── valuation/          # 估值模型集合
│   └── ai_commentary/      # AI 报告生成
├── generated_data/         # 输出目录 (JSON 数据, PDF/TXT 报告)
├── config/                 # 配置文件 (阈值与API设置)
└── utils/                  # 通用工具 (日志管理, 安全遮罩)
```

## 数据存放与产物 (Data Storage & Artifacts)

### 1. 用户配置与原始数据 (`user_config/`)
- **`.env`**: 存放 API Key 的私密文件。
- **`.csv` (xls)**: 从 Damodaran 下载的原始行业数据文件 (如 `wacc.csv`, `betas.csv`)。
- **`sector_benchmarks.json`**: 静态行业基准数据文件 (由 Damodaran 的原始 CSV 数据处理生成，作为系统的默认基准)。

### 2. 生成数据 (`generated_data/`)
系统运行过程中的中间数据存放于此：
- **原始数据**: `initial_data_{SYMBOL}_{DATE}.json`
- **行业基准**: `benchmark_data_{DATE}.json`
- **计算结果**: `financial_data_{SYMBOL}_{DATE}.json`
- **评分明细**: `financial_score_{SYMBOL}_{DATE}.json`

### 3. 分析报告 (`generated_reports/`)
最终生成的供用户阅读的报告存放于此：
- **扫描报告**: `stock_scan_{DATE}.txt` (批量扫描结果汇总)
- **AI 报告**: `ai_analysis_{SYMBOL}_{DATE}.md` (AI 深度分析报告)

## 安装与配置

### 1. 环境依赖
请确保安装 Python 3.8+，然后安装所需库：
```bash
pip install -r requirements.txt
```
(主要依赖包括: `pandas`, `yfinance`, `requests`, `google-generativeai`)

### 2. API Key 配置
本系统依赖外部 API 服务以保证数据的完整性。请在项目根目录下创建 `.env` 文件，并填入您的 Key：

**文件: `.env`**
```env
# [必填] Alpha Vantage: 用于补充 Yahoo Finance 缺失的冷门财务数据
ALPHAVANTAGE_API_KEY=your_key_here

# [必填] Financial Modeling Prep (FMP): 用于获取分析师一致预期、WACC 和补充财务数据
FMP_API_KEY=your_key_here

# [必填] Google Gemini: 用于生成 AI 分析报告
GEMINI_API_KEY=your_key_here
```

### 3. 获取 API Key
- **Alpha Vantage**: [获取 Key (免费)](https://www.alphavantage.co/support/#api-key) - 每日 25 次调用限制。
- **FMP**: [注册 (免费版)](https://site.financialmodelingprep.com/) - 免费版有部分端点限制，系统会自动处理。
- **Google Gemini**: [AI Studio](https://aistudio.google.com/app/apikey) - 免费使用。

## 使用说明

### 运行个股分析 (深度模式)
```bash
python run_analysis.py AAPL
# 或者直接运行 python run_analysis.py 按提示输入
```

### 运行批量扫描 (筛选模式)
```bash
python run_scanner.py AAPL MSFT NVDA TSLA
# 或者
python run_scanner.py
# (根据提示输入 CSV 列表或手动输入代码)
```

## 核心算法与逻辑 (Core Algorithms & Logic)

本系统不仅仅是数据的展示，而是内置了一套完整的量化评估引擎。

### 1. 合成统计学基准 (Synthetic Benchmarking Algorithm)
当行业数据缺乏详细分布（即只有平均值而无 P90/P10 分位点）时，系统采用核心算法重构分布：
*   **输入**: 从 Damodaran 获取的行业均值 ($\mu$) 和由波动率推导出的变异系数 (CV)。
*   **计算**:
    *   引入 **阻尼系数 (Damping Factor)** (通常 0.8~0.95) 以修正现实数据的厚尾效应。
    *   基于合成 Z-Score 公式反推关键分位点：$P_{xx} = \mu \pm Z \times (\mu \times CV \times Damping)$。
*   **意义**: 实现了**“行业相对公平”**。在公用事业等低波动行业，稍高于平均即可能被评为优秀；而在生物科技等高波动行业，需大幅超越平均值才能获得高分。

### 2. 动态权重评分 (Dynamic Sector Scoring)
系统不采用“一刀切”的评分标准，而是针对 GICS 11 个一级行业定制了权重配置 (`scoring_config.py`)：
*   **科技股**: 高度重视 **Growth** (营收/净利 CAGR) 和研发投入。
*   **金融/REITs**: 核心参考 **Capital Allocation** (股息/回购) 和 **PB** (市净率)。
*   **能源/公用事业**: 侧重 **Cash Flow** (FCF) 和债务健康度。
*   *自适应机制*: 如果某指标因数据缺失无法计算，其权重会自动按比例分配给同类别的其他指标，确保最终得分为 0-100 的有效值。

### 3. 综合估值模型 (Valuation Blender)
为了避免单一视角的偏见，系统融合了 **7 种主流估值方法**，并根据行业特性进行加权求和 (`valuation_config.py`)：
*   **绝对估值**:
    1.  **DCF (现金流折现)**: 适用于现金流预测相对准确的成熟企业。
    2.  **DDM (股息折现)**: 专用于高分红行业（如银行、公用事业）。
*   **相对估值**:
    3.  **PE (市盈率)**: 盈利稳定型企业的标尺。
    4.  **PS (市销率)**: 高增长但暂未盈利（SaaS/Biotech）企业的核心指标。
    5.  **PB (市净率)**: 重资产或金融企业的底线逻辑。
    6.  **EV/EBITDA**: 剔除资本结构和折旧影响，适用于制造业。
*   **市场预期**:
    7.  **Analyst Targets**: 纳入华尔街的一致预期目标价作为市场情绪参考。

### 4. 数据完整性与兜底
系统采用级联获取策略：Yahoo (首选) -> FMP (次选) -> Alpha Vantage (兜底)。确保即便某个源挂了，也能自动切换并在报告中标记“数据来源可靠性降低”。（注：V3.0 已完全自动化，移除了旧版的手动数据录入模式）。

## 后续开发计划 (Future Roadmap)

### 接入 SEC EDGAR (Tier 4 数据源)
目前系统已实现了 Yahoo, FMP, Alpha Vantage 三级数据兜底。为进一步提升数据权威性和兜底能力，计划在未来接入美国证监会 (SEC) 的官方 EDGAR 数据作为第 4 级数据源。

**开发指南:**
1.  **架构扩展**: 
    - 系统已预留扩展接口，请参考 `data_acquisition/stock_data/base_fetcher.py`。
    - 需创建一个继承自 `BaseFetcher` 的 `EdgarFetcher` 类，并实现 `fetch_income_statements` 等标准接口。
2.  **技术难点**:
    - **XBRL 解析**: SEC 数据通常以 XBRL 格式提供，结构复杂。需要将成百上千个 XBRL 标签映射到本项目标准化的 70+ 个核心字段 (定义于 `utils.unified_schema`)。
    - **API 交互**: 需要处理 SEC 的 REST API 请求头 (User-Agent 需符合 SEC 规范)。
3.  **参考资料**:
    - [SEC EDGAR API 文档](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
    - [Alpha Vantage 字段参考](https://documentation.alphavantage.co/FundamentalDataDocs/index.html)

---
Generated by Antigravity Agent

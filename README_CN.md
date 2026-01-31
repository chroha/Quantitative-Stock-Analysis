# Quantitative Stock Analysis System (量化股票分析系统)

[English Version](README.md)

## 简介

这是一个量化股票分析与筛选工具，平时自用，用于帮我快速对美股进行基本面、技术面和估值的全方位评估。它能够自动获取数据、计算复杂的财务指标、并按设计的量化方式进行打分，最终生成投资报告辅助决策。

## 核心功能

### 1. 个股分析 (`run_analysis.py`)

针对单个股票进行全流程分析：

- **数据获取**: 采用 4 层级联数据源策略：
  - **T1 Yahoo Finance**: 主要数据源，提供实时行情和历史财报。
  - **T2 SEC EDGAR**: 官方 XBRL 数据源，直接从美国证监会获取原始财务报表。
  - **T3 FMP**: 补充分析师预期和其他结构化数据。
  - **T4 Alpha Vantage**: 最终后备源，填补冷门股票的数据空缺。
  - **数据完整性评分卡 (Scorecard)**: 实时可视化数据健康度、历史深度（逐年矩阵）及缺失字段。
- **财务评分**: 基于 ROIC, ROE, 利润率, 增长率, 资本配置等 20+ 个指标进行加权打分 (0-100)。评分考虑了行业基准。
- **技术评分**: 结合 RSI, MACD, 均线系统 (SMA/EMA) 评估当前趋势与动能。
- **估值模型**:
  - 现金流折现 (DCF)
  - 股利折现 (DDM)
  - 相对估值 (PE/PB/PS/EV-EBITDA 倍数)
  - 价值投资模型 (Graham Number, Peter Lynch, PEG Ratio)
  - 分析师一致预期
- **AI 投资点评**: 调用 Google Gemini 模型，基于上述所有数据生成解读报告。

### 3. 宏观策略分析 (`run_macro_report.py`)

全新的宏观经济分析模块，用于生成自上而下的市场策略报告：

- **AI 宏观策略解读**: 模拟“机构级 CIO”视角，自动识别市场异常与背离信号，生成包含深度诊断与行动建议的双语研报。
- **全量数据整合**: 聚合 FRED (利率/通胀) 与 Yahoo Finance (全球市场/板块) 数据，构建完整宏观拼图。
- **量化风险模型**: 包含经济周期定位、ERP 估值极值预警及澳洲市场贸易条件分析。

### 2. 批量选股扫描 (`run_scanner.py`)

- **批量处理**: 支持一次性扫描多个自选股。
- **快速评分**: 略过耗时的估值和AI步骤，专注于财务与技术面打分。
- **自动排名**: 结果按财务健康度 (Financial Score) 自动排序。
- **降级处理**: 智能识别并标记数据不足（如上市不足5年）的股票，并在报告中提供“可靠性降低”的提示。
- **输出**: 在控制台打印摘要，并生成包含详细指标的汇总文本报告。

## 目录结构

```text
.
├── data_acquisition/       # 数据获取模块 (Yahoo, EDGAR, FMP, Alpha Vantage)
│   ├── benchmark_data/     # 行业基准数据获取
│   ├── stock_data/         # 个股财务数据获取
│   └── macro_data/         # 宏观经济数据 (FRED, Yahoo)
├── fundamentals/           # 核心分析逻辑
│   ├── financial_data/     # 财务指标计算 (Growth, Profitability, Capital)
│   ├── financial_scorers/  # 财务评分引擎 (配置与权重)
│   ├── technical_scorers/  # 技术指标评分
│   ├── valuation/          # 估值模型集合
│   ├── ai_commentary/      # AI 报告生成
│   └── macro_indicator/    # 宏观策略分析 (周期, 风险, 资产配置)
├── data/                   # [统一数据目录]
│   └── cache/              # 缓存数据 (gitignore)
│       ├── stock/          # 个股分析数据 (JSON)
│       ├── macro/          # 宏观经济快照
│       └── benchmark/      # 行业基准数据 (JSON + CSV)
├── generated_reports/      # 最终报告 (AI 分析, 扫描汇总)
├── report_example/         # 报告样例 (Markdown Report Examples)
├── config/                 # 配置文件 (阈值与API设置)
├── user_config/            # 用户私密配置 (.env)
├── utils/                  # 通用工具 (日志管理, 安全遮罩)
├── run_analysis.py         # 个股深度分析入口
├── run_scanner.py          # 批量扫描入口
├── run_getform.py          # 数据表单生成工具
└── run_macro_report.py     # 宏观策略报告入口
```

## 数据存放与产物 (Data Storage & Artifacts)

### 1. 用户配置 (`user_config/`)

仅存放用户私密配置，由 `.gitignore` 排除：

- **`.env`**: 存放 API Key 的私密文件。
- **`.env.example`**: 配置模板，帮助新用户快速设置。

### 2. 数据缓存 (`data/cache/`)

系统运行过程中的所有数据存放于此，由 `.gitignore` 排除：

- **`stock/`**: 个股分析数据
  - `initial_data_{SYMBOL}_{DATE}.json` - 原始获取数据
  - `financial_data_{SYMBOL}_{DATE}.json` - 计算后的财务指标
  - `financial_score_{SYMBOL}_{DATE}.json` - 评分明细
- **`macro/`**: 宏观经济数据
  - `macro_latest.json` - 最新宏观数据快照
- **`benchmark/`**: 行业基准数据
  - `benchmark_data_{DATE}.json` - 行业评分基准
  - `*_data.csv` - Damodaran 原始数据缓存

### 3. 分析报告 (`generated_reports/`)

最终生成的供用户阅读的报告存放于此：

- **扫描报告**: `stock_scan_{DATE}.txt` (批量扫描结果汇总)
- **AI 报告**: `ai_analysis_{SYMBOL}_{DATE}.md` (AI 深度分析报告)
- **宏观报告**: `macro_report_{DATE}.md` (宏观策略分析报告)
- **数据表格**: `collated_scores_{DATE}.csv` (run_getform生成的汇总表)

### 4. 报告样例 (Report Examples)

如果您想查看生成的 AI 分析报告长什么样，可以参考以下样例：

- **[美股 AI 分析报告样例](report_example/ai_analysis_AAPL_example.md)**
- **[宏观策略分析报告样例](report_example/macro_report_example.md)**

## 安装与配置

### 1. 环境依赖

请确保安装 Python 3.8+，然后直接安装所需库：

```bash
pip install yfinance requests pydantic python-dotenv pandas numpy python-dateutil fredapi scipy pytz
```

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

# [必填] FRED API Key: 用于获取宏观经济数据
FRED_API_KEY=your_key_here
```

### 3. 获取 API Key

- **Alpha Vantage**: [获取 Key (免费)](https://www.alphavantage.co/support/#api-key) - 免费版有部分端点限制。
- **FMP**: [注册 (免费版)](https://site.financialmodelingprep.com/) - 免费层级有部分限制，每日最大请求250次，每股根据数据需补充情况消耗0-5次。
- **Google Gemini**: [AI Studio](https://aistudio.google.com/app/apikey) - 免费使用。
- **FRED**: [获取 Key (免费)](https://fred.stlouisfed.org/) - 免费使用。

### 4. 高级配置 (Advanced Configuration)

系统行为高度可定制，所有关键阈值均在 `config/analysis_config.py` 中定义。

- **数据完整性 (Data Sufficiency)**: 定义分析所需的最少数据量 (如 `MIN_HISTORY_YEARS_GOOD`)。
- **缺口分析 (Gap Analysis)**: 开关备用数据源的抓取逻辑 (如 `FETCH_ON_MISSING_VALUATION`)。
- **估值阈值 (Valuation Limits)**: 设定低估/高估的文本评判标准。
- **指标边界 (Metric Bounds)**: 定义财务指标的有效范围 (如 ROIC, ROE) 以过滤异常值。

## 使用说明

### 运行个股分析 (分析模式)

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

### 运行数据汇总 (报表模式)

```bash
python run_getform.py AAPL MSFT
# 将多个股票的评分和估值数据汇总为 CSV
```

### 运行宏观策略报告 (Macro Mode)

```bash
python run_macro_report.py
# 启动交互式菜单，选择生成报告或刷新数据
```

## 开发与调试 (Development & Debugging)

### 数据审计系统 (Data Audit System)

本项目内置了强大的数据审计工具，用于排查数据异常、字段缺失或 DDM 估值失败等问题：

```bash
python run_data_audit.py --symbol TSM
```

**功能说明:**

1. **原始经过抓取 (Raw Capture)**: 将 Yahoo/FMP/EDGAR 的 API 原始响应保存至 `debug_data/`。
2. **隔离测试 (Isolation)**: 独立运行每个数据源的解析器，验证解析逻辑是否正确。
3. **链路追踪 (Pipeline Trace)**: 对数据合并、货币标准化等中间状态进行快照保存。
4. **诊断报告 (Reports)**:
    - `yahoo_unmapped_fields.txt`: 识别 API 返回了但我们 schema 未使用的字段。
    - `final_provenance_report.txt`: 精确追踪每个数据点（如营收）的具体来源（Yahoo 还是 FMP）。

## 核心算法与逻辑 (Core Algorithms & Logic)

本系统除了数据展示外，也包含了一套量化评估逻辑。

### 1. 合成统计学基准 (Synthetic Benchmarking Algorithm)

当行业数据缺乏详细分布（即只有平均值而无 P90/P10 分位点）时，系统采用核心算法重构分布：

- **输入**: 从 Damodaran 获取的行业均值 ($\mu$) 和由波动率推导出的变异系数 (CV)。
- **计算**:
  - 引入 **阻尼系数 (Damping Factor)** (通常 0.8~0.95) 以修正现实数据的厚尾效应。
  - 基于合成 Z-Score 公式反推关键分位点：$P_{xx} = \mu \pm Z \times (\mu \times CV \times Damping)$。
- **意义**: 实现了**“行业相对公平”**。在公用事业等低波动行业，稍高于平均即可能被评为优秀；而在生物科技等高波动行业，需大幅超越平均值才能获得高分。

### 2. 动态权重评分 (Dynamic Sector Scoring)

系统不采用“一刀切”的评分标准，而是针对 GICS 11 个一级行业定制了权重配置 (`scoring_config.py`)：

- **科技股**: 高度重视 **Growth** (营收/净利 CAGR) 和研发投入。
- **金融/REITs**: 核心参考 **Capital Allocation** (股息/回购) 和 **PB** (市净率)。
- **能源/公用事业**: 侧重 **Cash Flow** (FCF) 和债务健康度。
- *自适应机制*: 如果某指标因数据缺失无法计算，其权重会自动按比例分配给同类别的其他指标，确保最终得分为 0-100 的有效值。

#### 财务数据权重分配可视化

![scoring_weights_overview](scoring_weights_overview.png)
*估值权重概览*

![scoring_weights_detailed](scoring_weights_detailed.png)
*估值权重具体情况*

### 3. 综合估值模型 (Valuation Blender)

为了避免单一视角的偏见，系统融合了 **10 种主流估值方法**，并根据行业特性进行加权求和 (`valuation_config.py`)：

- **绝对估值**:
    1. **DCF (现金流折现)**: 适用于现金流预测相对准确的成熟企业。
    2. **DDM (股息折现)**: 专用于高分红行业（如银行、公用事业）。
- **相对估值**:
    3.  **PE (市盈率)**: 盈利稳定型企业的标尺。
    4.  **PS (市销率)**: 高增长但暂未盈利（SaaS/Biotech）企业的核心指标。
    5.  **PB (市净率)**: 重资产或金融企业的底线逻辑。
    6.  **EV/EBITDA**: 剔除资本结构和折旧影响，适用于制造业。
- **价值投资模型**:
    7.  **Graham Number (格雷厄姆估值)**: 基于 EPS 和账面价值的保守内在价值。
    8.  **Peter Lynch (彼得林奇估值)**: 使用净利 CAGR 进行增长调整估值。
    9.  **PEG Ratio (PEG 估值)**: 市盈增长比，成长股核心指标。
- **市场预期**:
    10. **Analyst Targets**: 纳入华尔街的一致预期目标价作为市场情绪参考。

#### 估值逻辑可视化

![Valuation Weights Detailed](valuation_weights_detailed_en.png)
*详细估值权重与逻辑图*

![Valuation Weights Final](valuation_weights_final_en.png)
*最终估值合成逻辑*

---

## 问题反馈 (Feedback & Issues)

本系统涉及与多个数据源（Yahoo/EDGAR/FMP/Alpha Vantage）的交互及复杂的财务计算。

如果您在使用过程中发现 **Bug**、**计算错误**、**数据抓取失败** 或 **字段映射错误**，欢迎提交 Issue 进行反馈。您的反馈对于提升系统的准确性和健壮性非常重要，谢谢！

## 风险提示及免责声明

市场有风险，投资需谨慎。本报告中所述观点、分析及评分仅代表模型在特定参数下的逻辑推演，不构成对任何金融产品的买入、持有或卖出建议。投资者应根据个人风险承受能力独立决策。作者对因使用本报告内容而导致的任何直接或间接投资损失不承担法律责任。

---
Generated by Antigravity Agent

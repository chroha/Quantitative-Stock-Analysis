# 配置文件参考

本文档列出了项目中所有可供用户自定义的配置文件。

## 1. 核心配置 (`config/`)

### `config/settings.py`

- **用途**: API 密钥和环境设置
- **数据来源**: `user_config/.env`
- **主要变量**:
  - `GOOGLE_AI_KEY`: Gemini API 密钥（用于 AI 评论）
  - `FMP_API_KEY`: Financial Modeling Prep API 密钥
  - `FRED_API_KEY`: FRED API 密钥（用于宏观数据）
  - `ALPHA_VANTAGE_KEY`: Alpha Vantage API 密钥

### `config/constants.py`

- **用途**: 路径常量和目录结构
- **主要变量**:
  - `DATA_CACHE_STOCK`: 股票数据缓存目录
  - `DATA_CACHE_MACRO`: 宏观数据缓存目录
  - `DATA_CACHE_BENCHMARK`: 基准数据缓存目录
  - `DATA_REPORTS`: 生成报告目录

### `config/analysis_config.py`

- **用途**: 分析阈值和验证参数
- **可自定义项**:
  - `DATA_SUFFICIENCY_CONFIG`: 历史数据完整性阈值
  - `DATA_FETCH_GAP_THRESHOLDS`: 可接受的数据缺口百分比
  - `VALUATION_THRESHOLDS`: 估值评估边界
  - `METRIC_BOUNDS`: 指标验证边界

---

## 2. 财务评分 (`fundamentals/financial_scorers/`)

### `scoring_config.py` (财务)

- **用途**: 财务指标评分权重和阈值
- **可自定义项**:
  - `CATEGORY_WEIGHTS`: 盈利能力/成长性/资本配置权重
  - `SECTOR_WEIGHT_OVERRIDES`: 行业特定调整
  - `TIER3_THRESHOLDS`: 各指标的绝对评分阈值
  - 特殊指标评分函数（股权稀释、股权激励等）

---

## 3. 技术评分 (`fundamentals/technical_scorers/`)

### `scoring_config.py` (技术)

- **用途**: 技术指标评分参数
- **可自定义项**:
  - `CATEGORY_WEIGHTS`: 趋势/动量/波动/结构/成交量权重
  - `MA_CONFIG`: 移动平均线周期
  - `RSI_CONFIG`: RSI 阈值和评分
  - `ADX_CONFIG`: 趋势强度阈值
  - `BOLLINGER_CONFIG`: 布林带参数
  - `ATR_CONFIG`: 波动率评分
  - `VOLUME_CONFIG`: 成交量分析参数

---

## 4. 估值模型 (`fundamentals/valuation/`)

### `valuation_config.py`

- **用途**: 行业特定估值方法权重
- **可自定义项**:
  - `SECTOR_WEIGHTS`: 11 个 GICS 行业，每个行业 10 种估值方法权重
  - 估值方法: PE、PB、PS、EV/EBITDA、DCF、DDM、格雷厄姆、彼得林奇、PEG、分析师目标价

---

## 5. 宏观分析 (`data_acquisition/macro_data/`)

### `macro_config.py`

- **用途**: 宏观数据获取和分析参数
- **可自定义项**:
  - `LOOKBACK_WEEKS`: 历史数据回溯周期
  - `CACHE_TTL_HOURS`: 缓存过期时间
  - `TREND_THRESHOLD`: 趋势显著性阈值
  - `MA_PERIOD`: 趋势计算移动平均周期

---

## 6. 用户配置 (`user_config/`)

### `.env`

- **用途**: API 密钥（敏感数据，已被 git 忽略）
- **必需的密钥**:

  ```env
  FMP_API_KEY=你的_fmp_密钥
  FRED_API_KEY=你的_fred_密钥
  GOOGLE_AI_KEY=你的_gemini_密钥
  ALPHA_VANTAGE_KEY=你的_av_密钥
  ```

### `.env.example`

- **用途**: `.env` 文件模板

---

## 快速参考表

| 配置文件 | 位置 | 用途 |
| :--- | :--- | :--- |
| `settings.py` | `config/` | API 密钥、环境设置 |
| `constants.py` | `config/` | 路径、目录 |
| `analysis_config.py` | `config/` | 数据质量阈值 |
| `scoring_config.py` | `fundamentals/financial_scorers/` | 财务评分权重 |
| `scoring_config.py` | `fundamentals/technical_scorers/` | 技术评分参数 |
| `valuation_config.py` | `fundamentals/valuation/` | 行业估值权重 |
| `macro_config.py` | `data_acquisition/macro_data/` | 宏观数据设置 |
| `.env` | `user_config/` | API 密钥（从 .env.example 创建）|

---

## 注意事项

1. **不要提交 `.env`** - 它包含敏感的 API 密钥
2. **行业权重总和为 1.0** - 修改估值权重时，确保各方法权重之和为 100%
3. **修改后测试** - 运行 `python run_analysis.py AAPL` 验证配置更改

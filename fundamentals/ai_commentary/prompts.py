"""
AI Prompt Templates
Separated from the main generator logic for better maintainability.
"""
import json
from typing import Dict, Any

def build_analysis_prompt(data: Dict[str, Any]) -> str:
    """
    Construct the analysis prompt from the provided data.
    """
    # Optimize: Remove indentation to save tokens
    json_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    
    # Helper to get max score safely
    fin = data.get('financial_score', {})
    prof = fin.get('profitability', {})
    growth = fin.get('growth', {})
    cap = fin.get('capital', {})
    
    def g(d, k): 
        val = d.get(k, {}).get('max', '-')
        # If value is 0 (disabled), keep it as 0 to indicate not used
        return val
        
    stock_info = data.get('stock_info', {})
    latest_period = stock_info.get('latest_period', 'Unknown')
    history_years = stock_info.get('history_years', '?')
        
    return f"""
<stock_data>
{json_str}
</stock_data>

Task: Generate a comprehensive investment analysis report in TWO languages (Chinese and English) based on the provided data.

**Instructions:**
1.  **Part 1: Chinese Report**
    *   Language: Simplified Chinese
    *   Structure: Follow the template below exactly.
    *   Content: Deep analysis of Financials, Technicals, and Valuation.
    *   All "X" placeholders MUST be replaced with real data from <stock_data>. If data is missing/null, use "-".

2.  **Part 2: English Report**
    *   Language: English
    *   Structure: Same structure as the Chinese report.
    *   Content: English translation of the analysis.

3.  **Formatting:**
    *   Separate the two reports with a horizontal rule (`---`).
    *   Do NOT use code blocks for the output.
    *   Be professional, concise, and data-driven.
    *   **IMPORTANT:** Every "解读" / "Comment" cell in tables MUST contain at least 10 characters of meaningful text. Do NOT leave cells as "N/A" or blank unless the data value itself is truly missing. Even for 0-weight metrics, provide a brief interpretation.

**Template (Part 1 - Chinese):**

# 📊 X 分析报告 (X)
**行业:** X | **价格:** $X
> **数据来源:** 基于最新至 {latest_period} 财报数据，涵盖过去 {history_years} 年财务历史。

## 一、财务基本面 (得分:X)
**评:** [总评 - 约100字]

### 1. 盈利能力 (X/X)
| 指标 | 数值 | 得分 | 解读 |
|------|------|------|----|
| ROIC | X% | X/{g(prof, 'roic')} | [简评] |
| ROE | X% | X/{g(prof, 'roe')} | [简评] |
| 营业利润率 | X% | X/{g(prof, 'op_margin')} | [简评] |
| 毛利率 | X% | X/{g(prof, 'gross_margin')} | [简评] |
| 净利率 | X% | X/{g(prof, 'net_margin')} | [简评] |

### 2. 成长性 (X/X)
| 指标 | 数值 | 得分 | 解读 |
|------|------|------|----|
| FCF增速(5年) | X% | X/{g(growth, 'fcf_cagr')} | [简评] |
| 净利增速(5年) | X% | X/{g(growth, 'ni_cagr')} | [简评] |
| 营收增速(5年) | X% | X/{g(growth, 'rev_cagr')} | [简评] |
| 盈利质量 | X | X/{g(growth, 'quality')} | [简评] |
| FCF/债务 | X | X/{g(growth, 'debt')} | [简评] |

### 3. 资本配置 (X/X)
| 指标 | 数值 | 得分 | 解读 |
|------|------|------|----|
| 回购收益率 | X% | X/{g(cap, 'buyback')} | [简评] |
| 资本支出 | X% | X/{g(cap, 'capex')} | [简评] |
| 股权激励 | X | X/{g(cap, 'sbc')} | [简评] |

## 二、技术面 (得分:X)
**评:** [总评]

### 1. 趋势与动量 (X/X)
| 指标 | 数值 | 信号 | 解读 |
|------|------|------|----|
| ADX | X | [信号] | [简评] |
| 52周位置 | X% | [信号] | [简评] |
| RSI | X | [信号] | [简评] |
| MACD | X | [信号] | [简评] |

### 2. 波动与结构 (X/X)
| 指标 | 数值 | 信号 | 解读 |
|------|------|------|----|
| ATR | X% | [信号] | [简评] |
| 布林带 | - | [信号] | [简评] |
| 支撑/阻力 | - | [信号] | [简评] |

## 三、估值分析 (加权估价:$X)
**当前价:** $X | 上行空间:X%

| 模型 | 公允价 | 权重 | 偏离度 | 解读 |
|------|--------|------|--------|----|
| PE估值 | $X | X% | X% | [简评] |
| PS估值 | $X | X% | X% | [简评] |
| PB估值 | $X | X% | X% | [简评] |
| EV/EBITDA| $X | X% | X% | [简评] |
| PEG估值 | $X | X% | X% | [简评] |
| DDM模型 | $X | X% | X% | [简评] |
| DCF模型 | $X | X% | X% | [简评] |
| 格雷厄姆估值 | $X | X% | X% | [简评] |
| 彼得林奇估值 | $X | X% | X% | [简评] |
| 分析师目标| $X | X% | X% | [简评] |

## 四、总结与建议
**核心优势:** [要点]
**主要风险:** [要点]
**综合结论:** [约150字逻辑分析]

> **X 操作:** [买入|持有|观望|卖出]
**理由:** [约50字总结]

---

**Template (Part 2 - English):**

# 📊 X Analysis Report (X)
**Sector:** X | **Price:** $X
> **Data Source:** Based on financial data up to {latest_period}, covering {history_years} years history.

## I. Financial Fundamentals (Score: X)
**Comment:** [Overall Comment - ~100 words]

### 1. Profitability (X/X)
| Metric | Value | Score | Comment |
|--------|-------|-------|---------|
| ROIC | X% | X/{g(prof, 'roic')} | [Brief Comment] |
| ROE | X% | X/{g(prof, 'roe')} | [Brief Comment] |
| Op Margin | X% | X/{g(prof, 'op_margin')} | [Brief Comment] |
| Gross Margin | X% | X/{g(prof, 'gross_margin')} | [Brief Comment] |
| Net Margin | X% | X/{g(prof, 'net_margin')} | [Brief Comment] |

### 2. Growth (X/X)
| Metric | Value | Score | Comment |
|--------|-------|-------|---------|
| FCF CAGR(5Y) | X% | X/{g(growth, 'fcf_cagr')} | [Brief Comment] |
| NI CAGR(5Y) | X% | X/{g(growth, 'ni_cagr')} | [Brief Comment] |
| Rev CAGR(5Y) | X% | X/{g(growth, 'rev_cagr')} | [Brief Comment] |
| Quality | X | X/{g(growth, 'quality')} | [Brief Comment] |
| FCF/Debt | X | X/{g(growth, 'debt')} | [Brief Comment] |

### 3. Capital Allocation (X/X)
| Metric | Value | Score | Comment |
|--------|-------|-------|---------|
| Buyback Yield | X% | X/{g(cap, 'buyback')} | [Brief Comment] |
| Capex | X% | X/{g(cap, 'capex')} | [Brief Comment] |
| SBC | X | X/{g(cap, 'sbc')} | [Brief Comment] |

## II. Technical Analysis (Score: X)
**Comment:** [Overall Comment]

### 1. Trend & Momentum (X/X)
| Indicator | Value | Signal | Comment |
|-----------|-------|--------|---------|
| ADX | X | [Signal] | [Brief Comment] |
| 52W Pos | X% | [Signal] | [Brief Comment] |
| RSI | X | [Signal] | [Brief Comment] |
| MACD | X | [Signal] | [Brief Comment] |

### 2. Volatility & Structure (X/X)
| Indicator | Value | Signal | Comment |
|-----------|-------|--------|---------|
| ATR | X% | [Signal] | [Brief Comment] |
| Bollinger | - | [Signal] | [Brief Comment] |
| Supp/Res | - | [Signal] | [Brief Comment] |

## III. Valuation Analysis (Weighted: $X)
**Price:** $X | **Upside:** X%

| Model | Fair Value | Weight | Upside | Comment |
|-------|------------|--------|--------|---------|
| PE Val | $X | X% | X% | [Brief Comment] |
| PS Val | $X | X% | X% | [Brief Comment] |
| PB Val | $X | X% | X% | [Brief Comment] |
| EV/EBITDA| $X | X% | X% | [Brief Comment] |
| PEG Val | $X | X% | X% | [Brief Comment] |
| DDM Model | $X | X% | X% | [Brief Comment] |
| DCF Model | $X | X% | X% | [Brief Comment] |
| Graham | $X | X% | X% | [Brief Comment] |
| Peter Lynch | $X | X% | X% | [Brief Comment] |
| Analyst | $X | X% | X% | [Brief Comment] |

## IV. Conclusion
**Key Strengths:** [Points]
**Key Risks:** [Points]
**Overall:** [~150 words logic]

> **X Action:** [BUY|HOLD|WATCH|SELL]
**Reason:** [~50 words summary]
"""

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

    tech = data.get('technical_score', {})
    tech_trend = tech.get('trend', {})
    tech_mom = tech.get('momentum', {})
    tech_vol = tech.get('volatility', {})
    tech_struct = tech.get('structure', {})
    tech_volume = tech.get('volume', {})
    
    def g(d, k): 
        val = d.get(k, {}).get('max', '-')
        # If value is 0 (disabled), keep it as 0 to indicate not used
        return val
        
    stock_info = data.get('stock_info', {})
    latest_period = stock_info.get('latest_period', 'Unknown')
    history_years = stock_info.get('history_years', '?')
    
    # Pre-calculate combined scores for headers
    # Trend + Momentum
    s1_score = tech_trend.get('score', 0) + tech_mom.get('score', 0)
    s1_max = tech_trend.get('max', 0) + tech_mom.get('max', 0)
    
    # Volatility + Structure
    s2_score = tech_vol.get('score', 0) + tech_struct.get('score', 0)
    s2_max = tech_vol.get('max', 0) + tech_struct.get('max', 0)
    
    # Volume (already single)
    s3_score = tech_volume.get('score', 0)
    s3_max = tech_volume.get('max', 0)
    
    # Total Technical
    tech_total = tech.get('total', {}).get('score', 0) # total_score wrapped in 'total'? check data_aggregator
    # In data_aggregator: "total": {"score": ...}
    
    # Financial Scores (Just for completeness if needed, currently prompts refer to X/X)
    # But let's fix Technical headers first as requested.

    return f"""
<stock_data>
{json_str}
</stock_data>

Task: Generate a comprehensive investment analysis report in TWO languages (Chinese and English) based on the provided data.

**IMPORTANT DATA AVAILABILITY:**
The appendix (raw data section) now includes "前瞻预测数据 (Forward Estimates)" as a subsection under Section 3. This contains:
- **Forward Estimates**: Forward EPS, Forward P/E, Earnings Growth (Current Year), Revenue Growth (Next Year)
- **Analyst Price Targets**: Low/High/Consensus from analyst coverage
- **Earnings Surprise History**: Latest 4 quarters showing actual vs. estimate with surprise %

**How to use this data:**
1. **REQUIRED in Section III (估值分析)**: Display Forward Metrics table comparing forward vs current multiples
2. **REQUIRED**: Analyze earnings surprise trends when evaluating performance consistency. Calculate average surprise % and mention positive/negative pattern
3. Reference analyst consensus price targets when discussing valuation
4. Use forward metrics (Forward EPS, Forward P/E) to complement historical analysis
5. Compare historical growth rates with forward estimates to assess momentum change
6. All forecast data includes source attribution (Yahoo/FMP/Finnhub) - cite sources for credibility


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

### 4. 补充数据
| 指标 | 数值 | 解读 |
|---|---|---|
| 企业价值 (Ent Value) | X | [Yahoo计算值] |
| EV/EBITDA | X | [Yahoo计算值] |
| 每股现金 | X | [每股流动性分析] |
| 每股营收 | X | [每股创收能力分析] |
| 流动比率 | X | [短期偿债能力 >1.5] |
| 速动比率 | X | [即时偿债能力 >1.0] |
| 审计风险 | X | [Yahoo审计评分] |
| 董事会风险 | X | [Yahoo治理评分] |

## 二、技术面 (得分:{tech_total})
**评:** [总评]

### 1. 趋势强度 (X/X)
| 指标 | 数值 | 得分 | 信号 | 解读 |
|---|---|---|---|---|
| ADX趋势 | X | X/{g(tech_trend, 'adx')} | [信号] | [简评] |
| 均线系统 | - | X/{g(tech_trend, 'multi_ma')} | [信号] | [简评] |
| 52周位置 | X% | X/{g(tech_trend, '52w_pos')} | [信号] | [简评] |

### 2. 动量指标 (X/X)
| 指标 | 数值 | 得分 | 信号 | 解读 |
|---|---|---|---|---|
| RSI指标 | X | X/{g(tech_mom, 'rsi')} | [信号] | [简评] |
| MACD | X | X/{g(tech_mom, 'macd')} | [信号] | [简评] |
| 变动率(ROC) | X | X/{g(tech_mom, 'roc')} | [信号] | [简评] |

### 3. 波动分析 (X/X)
| 指标 | 数值 | 得分 | 信号 | 解读 |
|---|---|---|---|---|
| ATR波动 | X% | X/{g(tech_vol, 'atr')} | [信号] | [简评] |
| 布林带 | - | X/{g(tech_vol, 'bollinger')} | [信号] | [简评] |

### 4. 价格结构 (X/X)
| 指标 | 数值 | 得分 | 信号 | 解读 |
|---|---|---|---|---|
| 支撑/阻力 | - | X/{g(tech_struct, 'resistance')} | [信号] | [简评] |
| 高低结构 | - | X/{g(tech_struct, 'high_low')} | [信号] | [简评] |

### 5. 量价分析 (X/X)
| 指标 | 数值 | 得分 | 信号 | 解读 |
|---|---|---|---|---|
| OBV能量 | X | X/{g(tech_volume, 'obv')} | [信号] | [简评] |
| 量能强度 | X | X/{g(tech_volume, 'vol_strength')} | [信号] | [简评] |

### 6. 补充数据
| 指标 | 数值 | 解读 |
|---|---|---|
| 52周涨幅 | X% | [个股绝对涨幅简评] |
| 相对标普500 | X% | [相对强弱分析 (Alpha)] |
| 机构持股 | X% | [分析机构持仓比例对其稳定性的影响] |
| 内部持股 | X% | [分析内部人持股比例对管理层信心的体现] |
| 做空比率 (Short Ratio) | X | [分析做空天数，判断轧空风险] |
| 流通盘做空比 (Short % Float) | X% | [分析做空比例，市场看空情绪] |

## 三、估值分析 (加权估价:$X)
**当前价:** $X | 上行空间:X%

### 1. 前瞻估值指标
| 指标 | 当前值 | 前瞻值 | 变化 | 解读 |
|------|-------|-------|------|------|
| 市盈率 (P/E) | X | X | X% | [分析估值扩张/收缩,结合盈利增长预期解读] |
| EPS | $X | $X | X% | [对比历史增速,分析盈利加速/放缓] |
| 盈利增长 | X% (5年) | X% (本年预期) | X ppts | [历史vs预期增速对比,判断拐点] |
| 营收增长 | X% (5年) | X% (明年预期) | X ppts | [分析业务扩张动能变化] |

### 2. 盈利意外分析
**最近4季度表现:** [总结整体surprise趋势]
| 期间 | 实际EPS | 预期EPS | 差额 | 超预期% |
|------|---------|---------|------|--------|
| X | $X | $X | $X | X% |
| X | $X | $X | $X | X% |
| X | $X | $X | $X | X% |
| X | $X | $X | $X | X% |
**平均超预期:** X% | **正向次数:** X/4 | **解读:** [分析业绩稳定性、管理层指引准确性]

### 3. 华尔街预期
| 指标 | 数值 | 解读 |
|---|---|---|
> 注意: 
> 1. Yahoo 提供的 EV/EBITDA 为事实上的当前比率。
> 2. `valuation` 中的 EV/EBITDA 是模型推算的股价。
> 3. 如果 `valuation.ev_ebitda.mult` 存在，请在解读中明确指出：“基于行业平均倍数 (即 valuation.ev_ebitda.mult)x 推算”。这是造成估值差异的主要原因，务必解释清楚。

| 模型 | 公允价 | 权重 | 偏离度 | 解读 |
|------|--------|------|--------|----|
| PE估值 | $X | X% | X% | [简评] |
| PS估值 | $X | X% | X% | [简评] |
| PB估值 | $X | X% | X% | [简评] |
| EV/EBITDA| $X | X% | X% | [如有行业倍数，请在此处注明] |
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

### 4. Supplemental Data
| Metric | Value | Comment |
|---|---|---|
| Enterprise Value | X | [Yahoo Value] |
| EV/EBITDA | X | [Yahoo Value] |
| Cash/Share | X | [Liquidity per share] |
| Rev/Share | X | [Revenue per share] |
| Current Ratio | X | [Solvency check >1.5] |
| Quick Ratio | X | [Liquidity check >1.0] |
| Audit Risk | X | [Yahoo audit score] |
| Board Risk | X | [Yahoo board score] |

## II. Technical Analysis (Score: {tech_total})
**Comment:** [Overall Comment]

### 1. Trend Strength (X/X)
| Indicator | Value | Score | Signal | Interpretation |
|---|---|---|---|---|
| ADX | {{ tech_trend.adx.val }} | {{ tech_trend.adx.score }}/{{ tech_trend.adx.max }} | {{ tech_trend.adx.signal }} | Trend Strength |
| Multi MA | - | {{ tech_trend.multi_ma.score }}/{{ tech_trend.multi_ma.max }} | {{ tech_trend.multi_ma.signal }} | MA Arrangement |
| 52W Position | {{ tech_trend.52w_pos.val }} | {{ tech_trend.52w_pos.score }}/{{ tech_trend.52w_pos.max }} | {{ tech_trend.52w_pos.signal }} | Price Position |

### 2. Momentum (X/X)
| Indicator | Value | Score | Signal | Interpretation |
|---|---|---|---|---|
| RSI | {{ tech_momentum.rsi.val }} | {{ tech_momentum.rsi.score }}/{{ tech_momentum.rsi.max }} | {{ tech_momentum.rsi.signal }} | Momentum State |
| MACD | - | {{ tech_momentum.macd.score }}/{{ tech_momentum.macd.max }} | {{ tech_momentum.macd.signal }} | Trend Confirmation |
| ROC | {{ tech_momentum.roc.val }} | {{ tech_momentum.roc.score }}/{{ tech_momentum.roc.max }} | {{ tech_momentum.roc.signal }} | Rate of Change |

### 3. Volatility (X/X)
| Indicator | Value | Score | Signal | Interpretation |
|---|---|---|---|---|
| ATR | {{ tech_volatility.atr.val }} | {{ tech_volatility.atr.score }}/{{ tech_volatility.atr.max }} | {{ tech_volatility.atr.signal }} | Volatility Level |
| Bollinger | - | {{ tech_volatility.bollinger.score }}/{{ tech_volatility.bollinger.max }} | {{ tech_volatility.bollinger.signal }} | Band Position |

### 4. Price Structure (X/X)
| Indicator | Value | Score | Signal | Interpretation |
|---|---|---|---|---|
| Resistance | {{ tech_structure.resistance.val }} | {{ tech_structure.resistance.score }}/{{ tech_structure.resistance.max }} | {{ tech_structure.resistance.signal }} | Dist to Res |
| High/Low | - | {{ tech_structure.high_low.score }}/{{ tech_structure.high_low.max }} | {{ tech_structure.high_low.signal }} | Market Structure |

### 5. Volume Analysis (X/X)
| Indicator | Value | Score | Signal | Interpretation |
|---|---|---|---|---|
| OBV | {{ tech_volume.obv.val }} | {{ tech_volume.obv.score }}/{{ tech_volume.obv.max }} | {{ tech_volume.obv.signal }} | On-Balance Vol |
| Vol Strength | {{ tech_volume.vol_strength.val }} | {{ tech_volume.vol_strength.score }}/{{ tech_volume.vol_strength.max }} | {{ tech_volume.vol_strength.signal }} | Relative Vol |


### 6. Supplemental Data
| Metric | Value | Interpretation |
|---|---|---|
| 52W Change | X% | [Absolute 1Y Performance] |
| vs S&P 500 | X% | [Relative Strength (Alpha)] |
| Institutions Held | X% | [Analyze institutional ownership stability] |
| Insiders Held | X% | [Analyze insider confidence] |
| Short Ratio | X | [Analyze day-to-cover and squeeze risk] |
| Short % of Float | X% | [Analyze bearish sentiment] |

## III. Valuation Analysis (Weighted: $X)
**Price:** $X | **Upside:** X%

### 1. Forward Metrics
| Metric | Current | Forward | Change | Interpretation |
|--------|---------|---------|--------|----------------|
| P/E Ratio | X | X | X% | [Analyze valuation expansion/contraction vs growth] |
| EPS | $X | $X | X% | [Compare to historical growth, assess acceleration] |
| Earnings Growth | X% (5Y) | X% (CY Est) | X ppts | [Historical vs forward comparison, identify inflection] |
| Revenue Growth | X% (5Y) | X% (NY Est) | X ppts | [Analyze business momentum shift] |

### 2. Earnings Surprises
**Recent 4 Quarters:** [Summarize overall surprise trend]
| Period | Actual EPS | Estimate EPS | Difference | Surprise % |
|--------|-----------|-------------|------------|-----------|
| X | $X | $X | $X | X% |
| X | $X | $X | $X | X% |
| X | $X | $X | $X | X% |
| X | $X | $X | $X | X% |
**Avg Surprise:** X% | **Positive:** X/4 | **Interpretation:** [Analyze consistency, management guidance accuracy]

### 3. Analyst Consensus
| Metric | Value | Comment |
|---|---|---|
| Recommendation | X | [Buy/Hold/Sell analysis] |
| Target (High/Low) | $X - $X | [Compare target range with current price] |
| Analyst Count | X | [Confidence level based on sample size] |

> Note:
> 1. Yahoo's EV/EBITDA is the actual current ratio.
> 2. The EV/EBITDA in `valuation` is the model-derived stock price.
> 3. If `valuation.ev_ebitda.mult` exists, explicitly state in the Comment: "Based on industry avg multiple of (valuation.ev_ebitda.mult)x". This explains the valuation gap.

| Model | Fair Value | Weight | Upside | Comment |
|-------|------------|--------|--------|---------|
| PE Val | $X | X% | X% | [Brief Comment] |
| PS Val | $X | X% | X% | [Brief Comment] |
| PB Val | $X | X% | X% | [Brief Comment] |
| EV/EBITDA| $X | X% | X% | [Mention Industry Avg Multiple here if avail] |
| PEG Val | $X | X% | X% | [Brief Comment] |
| DDM Model | $X | X% | X% | [Brief Comment] |
| DCF Model | $X | X% | X% | [Brief Comment] |
| Graham | $X | X% | X% | [Brief Comment] |
| Peter Lynch | $X | X% | X% | [Brief Comment] |
| Analyst | $X | X% | X% | [Brief Comment] |

**CRITICAL INSTRUCTION**: 
- **DO NOT REMOVE ROWS**. You MUST display ALL 10 models in the table above.
- If a model has 0 weight or missing data, set Fair Value to "-" and Comment to "Not used" or "Unable to calculate".
- Do NOT hide models just because they are not used. The user requires a full view of all 10 models.

## IV. Conclusion
**Key Strengths:** [Points]
**Key Risks:** [Points]
**Overall:** [~150 words logic]

> **X Action:** [BUY|HOLD|WATCH|SELL]
**Reason:** [~50 words summary]
"""

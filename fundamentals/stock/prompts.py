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

Task: Generate a comprehensive investment analysis report in Chinese based on the provided data.
**IMPORTANT DATA AVAILABILITY:**
The appendix (raw data section) now includes "前瞻预测数据 (Forward Estimates)" as a subsection under Section 3. This contains:
- **Forward Estimates**: Forward EPS, Forward P/E, Earnings Growth (Current Year), Revenue Growth (Next Year)
- **Analyst Price Targets**: Low/High/Consensus from analyst coverage
- **Earnings Surprise History**: Latest 4 quarters showing actual vs. estimate with surprise %
- **Market Intelligence**:
    - **News**: Top 5 recent headlines with source and summary (dates are formatted as YYYY-MM-DD strings)
    - **Insider Sentiment**: Monthly Share Purchase Ratio (MSPR) and Net Buy/Sell change
    - **Competitors**: List of key peer companies

**SPECIAL METRIC RULES:**
- **FCF/债务 (FCF/Debt)**: When `interpretation` is "Debt-Free (Max Score)", the company has NO debt.
  Display value as "0" (no debt), and write comment as "公司无债务，财务风险极低" / "Company is debt-free; zero financial leverage risk."
  This metric receives FULL marks, NOT 0.
- **News dates**: All news dates in `market_intelligence.news[].date` are pre-formatted as YYYY-MM-DD strings. Use them directly — do NOT convert or reformat them.

**How to use this data:**
1. **REQUIRED in Section III (估值分析)**: Display Forward Metrics table comparing forward vs current multiples
2. **REQUIRED**: Analyze earnings surprise trends when evaluating performance consistency. Calculate average surprise % and mention positive/negative pattern
3. Reference analyst consensus price targets when discussing valuation
4. Use forward metrics (Forward EPS, Forward P/E) to complement historical analysis
5. Compare historical growth rates with forward estimates to assess momentum change
6. All forecast data includes source attribution (Yahoo/FMP/Finnhub) - cite sources for credibility


**Instructions:**
1.  **Language:** Simplified Chinese
2.  **Structure:** Follow the template below exactly.
3.  **Content:** Deep analysis of Financials, Technicals, and Valuation.
    *   All "X" placeholders MUST be replaced with real data from <stock_data>. If data is missing/null, use "-".
4.  **Formatting:**
    *   Do NOT use code blocks for the output.
    *   Be professional, concise, and data-driven.
    *   **IMPORTANT:** Every "解读" / "Comment" cell in tables MUST contain at least 10 characters of meaningful text. Do NOT leave cells as "N/A" or blank unless the data value itself is truly missing. Even for 0-weight metrics, provide a brief interpretation.

**Template:**

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
| 营业利润率(GAAP) | X% | X/{g(prof, 'op_margin')} | [简评] |
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
| 企业价值 | X | [Yahoo计算值] |
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
| 均线系统 | X | X/{g(tech_trend, 'multi_ma')} | [信号] | [简评] |
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
| 布林带 | X | X/{g(tech_vol, 'bollinger')} | [信号] | [简评] |

### 4. 价格结构 (X/X)
| 指标 | 数值 | 得分 | 信号 | 解读 |
|---|---|---|---|---|
| 支撑/阻力 | X | X/{g(tech_struct, 'resistance')} | [信号] | [简评] |
| 高低结构 | X | X/{g(tech_struct, 'high_low')} | [信号] | [简评] |

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
| 做空比率 | X | [分析做空天数，判断轧空风险] |
| 流通盘做空比 | X% | [分析做空比例，市场看空情绪] |

## 三、市场情绪与情报 (Market Sentiment)
### 1. 内部交易情绪
**MSPR (月度购买比率):** X | **净买入/卖出:** X
**解读:** [分析内部人近期交易行为，MSPR>0通常由买入驱动，<0由卖出驱动。结合净变化判断内部信心]

### 2. 同业竞争
**主要竞争对手:** [列出Peers]
**对比简述:** [基于行业地位，简述其相对于同业的竞争优势或劣势]

### 3. 关键新闻情报 (AI精选)
1. **[新闻标题]** ([日期]) - [情感: 正面/负面/中性]
   > [一句话摘要及对股价的潜在影响分析]
2. **[新闻标题]** ([日期]) - [情感: 正面/负面/中性]
   > [一句话摘要及对股价的潜在影响分析]
3. **[新闻标题]** ([日期]) - [情感: 正面/负面/中性]
   > [一句话摘要及对股价的潜在影响分析]

## 四、估值分析 (加权估价:$X)
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

### 3. 华尔街预期
| 指标 | 数值 | 解读 |
|---|---|---|
| 评级建议 | X | [买入/持有/卖出 分析] |
| 目标价范围 | $X - $X | [对比当前价格与目标价范围] |
| 分析师数量 | X | [基于样本量的置信度分析] |

## 五、总结与建议
**核心优势:** [要点]
**主要风险:** [要点]
**综合结论:** [约150字逻辑分析]

> **X 操作:** [买入|持有|观望|卖出]
**理由:** [约50字总结]
"""

def build_executive_summary_prompt(data: Dict[str, Any]) -> str:
    """
    Construct the executive summary prompt from the provided data.
    """
    json_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    
    return f"""
<stock_data>
{json_str}
</stock_data>

Task: Generate a concise Executive Summary (approx 200 words) for this stock in English.

Structure:
1. **Investment Verdict**: Buy/Hold/Sell with short rationale.
2. **Key Highlights**: 3 bullet points on most critical Financial/Technical factors.
3. **Risk Warning**: 1 key risk.

Keep it professional, direct, and data-backed.
"""


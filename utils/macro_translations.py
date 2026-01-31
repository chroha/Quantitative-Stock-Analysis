"""
Macro Report Translations - Bilingual support for Macro Dashboard.
"""

MACRO_LABELS = {
    # Report Meta
    'title': {
        'cn': '全球宏观市场仪表盘',
        'en': 'Global Macro Dashboard'
    },
    'generated_at': {
        'cn': '生成时间',
        'en': 'Generated at'
    },
    'data_status': {
        'cn': '数据状态',
        'en': 'Data Status'
    },
    
    # Section Headers (Clean Chinese)
    'exec_summary': {
        'cn': '核心摘要', 
        'en': 'Executive Summary'
    },
    'asset_perf': {
        'cn': '跨资产表现',
        'en': 'Cross-Asset Performance'
    },
    'sector_rotation': {
        'cn': '板块轮动',
        'en': 'Sector Rotation'
    },
    'econ_indicators': {
        'cn': '经济指标',
        'en': 'Economic Indicators'
    },
    'market_internals': {
        'cn': '市场内部结构',
        'en': 'Market Internals'
    },
    'deep_dive': {
        'cn': '模型逻辑诊断',
        'en': 'Algo Logic & Diagnostics'
    },
    
    # Executive Summary Table
    'dimension': {'cn': '维度', 'en': 'Dimension'},
    'status': {'cn': '状态', 'en': 'Status'},
    'key_insight': {'cn': '核心观点', 'en': 'Key Insight'},
    'biz_cycle': {'cn': '商业周期', 'en': 'Business Cycle'},
    'risk_env': {'cn': '风险环境', 'en': 'Risk Environment'},
    'valuation': {'cn': '估值模型', 'en': 'Valuation'},
    'target': {'cn': '目标', 'en': 'Target'},
    
    # Cycle Phase Mappings
    'Recovery': {'cn': '复苏期', 'en': 'Recovery'},
    'Expansion': {'cn': '扩张期', 'en': 'Expansion'},
    'Neutral Expansion': {'cn': '温和扩张', 'en': 'Neutral Expansion'},
    'Overheating': {'cn': '过热期', 'en': 'Overheating'},
    'Slowdown': {'cn': '放缓期', 'en': 'Slowdown'},
    'Recession Watch': {'cn': '衰退预警', 'en': 'Recession Watch'},
    
    # Risk Environment Mappings
    'Risk On (Low Risk)': {'cn': '逐险模式 (低风险)', 'en': 'Risk On (Low Risk)'},
    'Neutral (Medium Risk)': {'cn': '中性观望 (中风险)', 'en': 'Neutral (Medium Risk)'},
    'Cautious (High Risk)': {'cn': '谨慎模式 (高风险)', 'en': 'Cautious (High Risk)'},
    'Risk Off (Extreme Risk)': {'cn': '避险模式 (极度风险)', 'en': 'Risk Off (Extreme Risk)'},
    'Risk On': {'cn': '逐险模式', 'en': 'Risk On'},
    'Neutral': {'cn': '中性', 'en': 'Neutral'},
    'Risk Off': {'cn': '避险模式', 'en': 'Risk Off'},
    'Unknown': {'cn': '未知', 'en': 'Unknown'},
    
    # Valuation Mappings
    'Underweight Stocks (Defensive)': {'cn': '低配股票 (防御)', 'en': 'Underweight Stocks (Defensive)'},
    'Overweight Stocks (Aggressive)': {'cn': '超配股票 (进取)', 'en': 'Overweight Stocks (Aggressive)'},
    'Neutral (60/40)': {'cn': '中性配置 (60/40)', 'en': 'Neutral (60/40)'},
    
    # Asset Table
    'asset_class': {'cn': '资产类别', 'en': 'Asset Class'},
    'instrument': {'cn': '标的', 'en': 'Instrument'},
    'price': {'cn': '价格', 'en': 'Price'},
    'pos_52w': {'cn': '52周位置', 'en': '52W Pos'},
    'no_data': {'cn': '_暂无数据_', 'en': '_No data available._'},
    
    # Asset Groups
    'Indices': {'cn': '指数', 'en': 'Indices'},
    'Commodities': {'cn': '大宗商品', 'en': 'Commodities'},
    'Crypto': {'cn': '加密货币', 'en': 'Crypto'},
    'Currencies': {'cn': '外汇', 'en': 'Currencies'},

    # Sector Rotation Labels
    'group': {'cn': '分组', 'en': 'Group'},
    'sector': {'cn': '行业', 'en': 'Sector'},
    
    'defensive': {'cn': '🛡️ 防御型', 'en': '🛡️ Defensive'},
    'cyclical': {'cn': '⚙️ 周期型', 'en': '⚙️ Cyclical'},
    'sensitive': {'cn': '🚀 进攻/敏感型', 'en': '🚀 Sensitive'},
    
    'XLK': {'cn': '💻 科技 (XLK)', 'en': '💻 Tech (XLK)'},
    'XLC': {'cn': '📱 通讯 (XLC)', 'en': '📱 Comm (XLC)'},
    'XLY': {'cn': '🛍️ 非必选 (XLY)', 'en': '🛍️ Discret (XLY)'},
    'XLE': {'cn': '🛢️ 能源 (XLE)', 'en': '🛢️ Energy (XLE)'},
    'XLF': {'cn': '🏦 金融 (XLF)', 'en': '🏦 Financials (XLF)'},
    'XLI': {'cn': '🏗️ 工业 (XLI)', 'en': '🏗️ Industrials (XLI)'},
    'XLB': {'cn': '🧱 材料 (XLB)', 'en': '🧱 Materials (XLB)'},
    'XLRE': {'cn': '🏠 地产 (XLRE)', 'en': '🏠 Real Estate (XLRE)'},
    'XLP': {'cn': '🛒 必选 (XLP)', 'en': '🛒 Staples (XLP)'},
    'XLV': {'cn': '💊 医疗 (XLV)', 'en': '💊 Health (XLV)'},
    'XLU': {'cn': '⚡ 公用 (XLU)', 'en': '⚡ Utilities (XLU)'},

    # Sector Status Labels
    'sec_surge': {'cn': '🔥 暴涨', 'en': '🔥 Surge'},
    'sec_dump': {'cn': '🩸 崩盘', 'en': '🩸 Dump'},
    'sec_safety': {'cn': '🛡️ 避险', 'en': '🛡️ Safety Bid'},
    'sec_inflation': {'cn': '🛢️ 通胀', 'en': '🛢️ Inflation'},
    'sec_profit': {'cn': '📉 获利了结', 'en': '📉 Profit Taking'},
    'sec_rate_fear': {'cn': '💸 利率承压', 'en': '💸 Rate Fear'},
    'sec_rotation': {'cn': '🔄 风格轮动', 'en': '🔄 Rotation'},
    'sec_trend': {'cn': '🚀 趋势延续', 'en': '🚀 Trend Cont.'},
    'sec_rebound': {'cn': '🐈 超跌反弹', 'en': '🐈 Rebound'},
    'sec_pullback': {'cn': '🔻 良性回调', 'en': '🔻 Pullback'},
    'sec_inflow': {'cn': '🟢 资金流入', 'en': '🟢 Inflow'},
    'sec_outflow': {'cn': '🔴 资金流出', 'en': '🔴 Outflow'},
    'sec_choppy': {'cn': '⚪ 震荡', 'en': '⚪ Choppy'},
    
    # Economic Table
    'category': {'cn': '类别', 'en': 'Category'},
    'indicator': {'cn': '指标', 'en': 'Indicator'},
    'latest_val': {'cn': '最新值', 'en': 'Latest Value'},
    'trend': {'cn': '趋势', 'en': 'Trend'},
    'prev_val': {'cn': '前值', 'en': 'Previous'},
    'data_date': {'cn': '数据日期', 'en': 'Data Date'},
    
    # Economic Categories
    'Growth & Labor': {'cn': '增长与就业', 'en': 'Growth & Labor'},
    'Inflation': {'cn': '通胀', 'en': 'Inflation'},
    'Rates & liquidity': {'cn': '利率与流动性', 'en': 'Rates & Liquidity'},
    'Sentiment': {'cn': '情绪', 'en': 'Sentiment'},
    
    # Internals
    'style_size': {'cn': '风格与规模轮动', 'en': 'Style & Size Rotation'},
    'metric': {'cn': '指标', 'en': 'Metric'},
    'current_ratio': {'cn': '当前比率', 'en': 'Current Ratio'},
    'mom_signal': {'cn': '动量信号', 'en': 'Momentum Signal'},
    'spread_1m': {'cn': '1月价差', 'en': '1M Spread'},
    'growth_val': {'cn': '成长 vs 价值', 'en': 'Growth vs Value'},
    'small_large': {'cn': '小盘 vs 大盘', 'en': 'Small vs Large'},
    
    'risk_struct': {'cn': '风险结构 (VIX)', 'en': 'Risk Structure (VIX)'},
    'vix_level': {'cn': 'VIX 水平', 'en': 'VIX Level'},
    'vix_mom': {'cn': 'VIX 动量', 'en': 'VIX Momentum'},
    'risk_note': {
        'cn': '比率 > 1.1: 恐慌上升 (避险); 比率 < 0.9: 情绪平稳 (逐险)', 
        'en': 'Ratio > 1.1: Rising Fear (Risk-Off); Ratio < 0.9: Calming (Risk-On)'
    },
    
    # Deep Dive / Algo Logic Keys
    'val_header': {'cn': '估值模型: 联邦模型', 'en': 'Valuation Model: Fed Model'},
    'val_algorithm': {'cn': '**算法:** `ERP` = `标普500盈利率 (1/PE)` - `无风险利率 (10Y)`', 'en': '**Algorithm:** `ERP` = `S&P500 Yield (1/PE)` - `Risk Free (10Y)`'},
    
    'component': {'cn': '组件', 'en': 'Component'},
    'input': {'cn': '输入数据', 'en': 'Input'},
    'logic': {'cn': '计算公式', 'en': 'Logic'},
    'result': {'cn': '结果', 'en': 'Result'},
    
    'equity_yield': {'cn': '美股收益率', 'en': 'Equity Yield'},
    'risk_free': {'cn': '无风险利率', 'en': 'Risk Free'},
    'erp_label': {'cn': '风险溢价 (ERP)', 'en': 'Risk Premium (ERP)'},
    
    'signal_logic': {'cn': '🛡️ 阈值判定', 'en': '🛡️ Signal Logic Thresholds'},
    'triggered': {'cn': '<-- **[触发]**', 'en': '<-- **[TRIGGERED]**'},
    
    'cycle_header': {'cn': '周期判定: 三因子模型', 'en': 'Cycle Judgement: Three-Factor Model'},
    'cycle_algorithm': {'cn': '**算法:** `总分` = `利差得分` + `通胀得分` + `就业得分`', 'en': '**Algorithm:** `Total Score` = `Spread Score` + `Inflation Score` + `Employment Score`'},
    
    'factor': {'cn': '因子', 'en': 'Factor'},
    'condition': {'cn': '判定条件', 'en': 'Condition'},
    'score': {'cn': '得分', 'en': 'Score'},
    
    'spread_factor': {'cn': '收益率曲线', 'en': 'Yield Curve'},
    'inflation_factor': {'cn': '通胀状况', 'en': 'Inflation Status'},
    'employ_factor': {'cn': '就业状况', 'en': 'Employment Status'},
    'final_verdict': {'cn': '最终裁决', 'en': 'Final Verdict'},
    
    # Trends
    'Rising': {'cn': '上升', 'en': 'Rising'},
    'Falling': {'cn': '下降', 'en': 'Falling'},
    'Stable': {'cn': '平稳', 'en': 'Stable'}
}

def get_label(key: str, lang: str = 'cn') -> str:
    """Get translated label. Fallback to key if not found."""
    if key in MACRO_LABELS:
        return MACRO_LABELS[key].get(lang, key)
    return key

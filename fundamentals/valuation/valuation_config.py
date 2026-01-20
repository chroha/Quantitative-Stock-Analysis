"""
Valuation Configuration
Sector-specific weights for different valuation methods.
"""

# Sector-specific method weights
# Each sector uses different valuation approaches based on industry characteristics
# 10 Models: pe, pb, ps, ev_ebitda, dcf, ddm, graham, peter_lynch, peg, analyst
SECTOR_WEIGHTS = {
    "Technology": {
        # 核心逻辑：成长定价 > 营收定价 > 盈利定价
        "peg": 0.15,           # 成长性估值核心，修正单纯PE误导
        "ps": 0.20,            # 营收增长对科技股至关重要(SaaS/云计算)
        "dcf": 0.15,           # 长期现金流是真理，但不过度依赖
        "peter_lynch": 0.15,   # 适合评估成熟科技股(FAANG类)
        "pe": 0.15,            # 传统盈利估值，权重适中
        "ev_ebitda": 0.10,     # 参考指标
        "analyst": 0.10,       # 创新驱动，市场预期重要
        "ddm": 0.00,           # 科技股分红极少
        "pb": 0.00,            # 轻资产，账面价值无意义
        "graham": 0.00         # 对高成长股过于保守
    },
    
    "Healthcare": {
        # 核心逻辑：增长潜力 + 现金流稳定性并重
        "peg": 0.15,           # 生物科技/创新药必看增长率
        "dcf": 0.15,           # 现金流相对稳定
        "pe": 0.15,            # 主流估值指标
        "ev_ebitda": 0.15,     # 医药制造业重要指标
        "analyst": 0.10,       # 临床试验结果影响大
        "peter_lynch": 0.10,   # 适合稳健医疗股
        "ps": 0.10,            # 营收规模参考
        "graham": 0.05,        # 成熟医药企业可用
        "ddm": 0.05,           # 部分大药企有分红
        "pb": 0.00             # 非资产密集型
    },
    
    "Financials": {
        # 核心逻辑：账面价值 + 分红 + 价值投资为主
        "pb": 0.30,            # 绝对核心(银行/保险账面价值)
        "ddm": 0.20,           # 金融股是分红大户
        "graham": 0.15,        # 格雷厄姆非常适合评估资产安全性
        "pe": 0.15,            # 需要调整的PE(周期性)
        "analyst": 0.15,       # 监管政策影响巨大
        "dcf": 0.00,           # 金融股现金流极难预测
        "peter_lynch": 0.05,   # 可用于寻找被低估银行股
        "peg": 0.00,           # 金融股不看成长率
        "ps": 0.00,            # 营收对金融业意义不大
        "ev_ebitda": 0.00      # 金融业无效指标
    },
    
    "Consumer Discretionary": {
        # 核心逻辑：盈利质量 + 成长性 + 林奇偏好
        "pe": 0.20,            # 主要估值指标
        "peter_lynch": 0.15,   # 林奇最爱板块("买你所懂的")
        "ps": 0.15,            # 营收增长重要
        "ev_ebitda": 0.15,     # 企业价值评估
        "peg": 0.10,           # 成长性参考
        "dcf": 0.10,           # 现金流受经济周期影响
        "graham": 0.05,        # 部分传统零售可用
        "analyst": 0.05,       # 消费趋势预测
        "ddm": 0.05,           # 部分成熟企业分红
        "pb": 0.00             # 轻资产为主
    },
    
    "Consumer Staples": {
        # 核心逻辑：稳定分红 + 价值投资 + 防御性
        "pe": 0.20,            # 主要指标
        "ddm": 0.20,           # 稳定高分红
        "graham": 0.15,        # 防御型价值股，资产稳定
        "dcf": 0.15,           # 现金流极其稳定
        "ev_ebitda": 0.10,     # 企业价值参考
        "analyst": 0.10,       # 市场份额预测
        "ps": 0.05,            # 营收增长有限
        "peter_lynch": 0.05,   # 低增长不太适合
        "pb": 0.00,            # 参考意义有限
        "peg": 0.00            # 增长缓慢
    },
    
    "Energy": {
        # 核心逻辑：企业价值 + 周期预判为主
        "ev_ebitda": 0.35,     # 核心指标(资本密集+高折旧)
        "analyst": 0.20,       # 周期性极强，油价预期权重高
        "graham": 0.10,        # 传统能源资产价值兜底
        "dcf": 0.10,           # 现金流波动大但需考虑
        "ddm": 0.10,           # 传统能源公司高分红
        "pe": 0.05,            # 周期性导致PE波动剧烈
        "pb": 0.05,            # 资产参考
        "ps": 0.05,            # 营收受油价影响大
        "peter_lynch": 0.00,   # 不适合周期股
        "peg": 0.00            # 增长不稳定
    },
    
    "Industrials": {
        # 核心逻辑：企业价值 + 资产质量 + 订单预期
        "ev_ebitda": 0.25,     # 重资产行业核心指标
        "pe": 0.20,            # 主要盈利指标
        "graham": 0.15,        # 大量厂房设备，适合格雷厄姆
        "analyst": 0.10,       # 订单预期和经济周期
        "dcf": 0.10,           # 现金流相对稳定
        "ps": 0.05,            # 营收规模参考
        "pb": 0.05,            # 资产价值参考
        "peter_lynch": 0.05,   # 可捕捉周期底部机会
        "ddm": 0.05,           # 部分工业股分红
        "peg": 0.00            # 增长不稳定
    },
    
    "Materials": {
        # 核心逻辑：企业价值 + 资产安全性
        "ev_ebitda": 0.30,     # 核心指标(重资产+高负债)
        "graham": 0.20,        # 强周期+重资产，格雷厄姆权重高
        "pe": 0.15,            # 周期性PE
        "pb": 0.15,            # 有形资产重要
        "analyst": 0.10,       # 大宗商品价格预期
        "dcf": 0.10,           # 现金流波动
        "ddm": 0.00,           # 分红不稳定
        "ps": 0.00,            # 营收波动大
        "peter_lynch": 0.00,   # 不适合
        "peg": 0.00            # 增长不稳定
    },
    
    "Real Estate": {
        # 核心逻辑：分红收益 + 资产价值(NAV)
        "ddm": 0.30,           # REITs核心就是分红(法定要求)
        "pb": 0.20,            # NAV(净资产价值)关键指标
        "analyst": 0.15,       # 利率预期影响极大
        "graham": 0.15,        # 大量有形资产，适合价值投资
        "dcf": 0.10,           # 租金现金流预测
        "pe": 0.10,            # 注意：应使用P/FFO而非P/E
        "ev_ebitda": 0.00,     # 房地产不适用
        "peter_lynch": 0.00,   # 增长有限
        "peg": 0.00,           # 不适用
        "ps": 0.00             # 不看营收
    },
    
    "Utilities": {
        # 核心逻辑：分红为王 + 防御性价值
        "ddm": 0.35,           # 最高权重(稳定高分红)
        "graham": 0.20,        # 公用事业资产极重，格雷厄姆有效
        "pe": 0.15,            # 稳定盈利
        "dcf": 0.15,           # 现金流极其可预测
        "analyst": 0.10,       # 监管政策影响
        "pb": 0.05,            # 资产参考
        "ev_ebitda": 0.00,     # 参考意义有限
        "peter_lynch": 0.00,   # 低增长
        "peg": 0.00,           # 增长极有限
        "ps": 0.00             # 不看营收
    },
    
    "Communication Services": {
        # 核心逻辑：分化行业(电信运营商 vs 互联网媒体)
        "pe": 0.20,            # 主要指标
        "ev_ebitda": 0.15,     # 电信运营商核心指标
        "ps": 0.15,            # 互联网公司看营收
        "peg": 0.15,           # 媒体/游戏公司成长性
        "dcf": 0.15,           # 现金流评估
        "analyst": 0.10,       # 用户增长预期
        "ddm": 0.05,           # 电信运营商分红
        "peter_lynch": 0.05,   # 部分适用
        "graham": 0.00,        # 不太适用
        "pb": 0.00             # 轻资产为主
    }
}


def get_sector_weights(sector: str) -> dict:
    """
    Get valuation method weights for a given sector.
    
    Args:
        sector: GICS sector name
        
    Returns:
        Dictionary of method weights, or empty dict if sector not found
    """
    return SECTOR_WEIGHTS.get(sector, {})


def get_all_sectors() -> list:
    """Get list of all supported sectors."""
    return list(SECTOR_WEIGHTS.keys())

from typing import Dict, Any
from datetime import datetime
from .cycle_analyzer import CycleAnalyzer
from .risk_assessor import RiskAssessor
from .valuation_allocator import ValuationAllocator

class MacroMarkdownGenerator:
    """Generates bilingual (CN/EN) Markdown reports."""
    
    def __init__(self):
        self.cycle_analyzer = CycleAnalyzer()
        self.risk_assessor = RiskAssessor()
        self.valuation_allocator = ValuationAllocator()
        
    def generate_markdown(self, data: Dict[str, Any]) -> str:
        """Generate full markdown report."""
        
        # Run analyses
        cycle = self.cycle_analyzer.analyze(data)
        risk = self.risk_assessor.analyze(data)
        valuation = self.valuation_allocator.analyze(data)
        
        timestamp = data.get('snapshot_date', datetime.now().isoformat())
        try:
            dt = datetime.fromisoformat(timestamp)
            date_str = dt.strftime("%Y-%m-%d")
        except:
            date_str = timestamp

        # Content Generation
        md = []
        
        # ==========================================
        # CHINESE SECTION
        # ==========================================
        md.append(f"# 📊 宏观策略分析报告")
        md.append(f"**日期:** {date_str} | **数据源:** FRED, Yahoo Finance")
        
        # 1. Economic Cycle
        c_phase = cycle['phase']
        c_phase_cn = self._translate_phase(c_phase)
        c_score = cycle['score']
        
        md.append(f"\n## 一、经济周期")
        md.append(f"**当前阶段:** {c_phase_cn} ({c_phase}) | **得分:** {c_score}/4")
        md.append(f"> 基于收益率曲线、CPI通胀率和失业率的综合评估。")
        
        md.append(f"\n| 指标 |数 值  | 解读  |")
        md.append(f"|---|---|---|")
        # Spread
        spread = cycle['metrics'].get('spread')
        spread_str = f"{spread:.2f}%" if spread is not None else "N/A"
        md.append(f"| 10Y-2Y 利差 | {spread_str} | {self._interp_spread(spread)} |")
        # Inflation
        cpi = cycle['metrics'].get('cpi_yoy')
        cpi_str = f"{cpi*100:.1f}%" if cpi is not None else "N/A"
        md.append(f"| CPI 通胀 (YoY) | {cpi_str} | {self._interp_cpi(cpi)} |")
        # Unemployment
        unrate = cycle['metrics'].get('unrate')
        unrate_str = f"{unrate:.1f}%" if unrate is not None else "N/A"
        md.append(f"| 失业率 | {unrate_str} | {self._interp_unrate(unrate)} |")

        # 2. Risk Environment
        r_env = risk['environment']
        r_env_cn = self._translate_risk_env(r_env)
        r_score = risk['risk_score']
        r_pos = risk['position_sizing']
        
        md.append(f"\n## 二、风险环境")
        md.append(f"**风险状态:** {r_env_cn}")
        md.append(f"**建议仓位:** {r_pos}")
        
        md.append(f"\n| 指标 (Metric) |数 值 (Value) | 解读 (Interpretation) |")
        md.append(f"|---|---|---|")
        # VIX
        vix = risk['metrics'].get('vix')
        md.append(f"| VIX 恐慌指数 | {vix:.2f} | {self._interp_vix(vix)} |")
        # DXY
        dxy = risk['metrics'].get('dxy')
        md.append(f"| 美元指数 (DXY) | {dxy:.2f} | {self._interp_dxy(dxy)} |")
        # USDJPY
        usdjpy = risk['metrics'].get('usdjpy')
        md.append(f"| Carry Trade (USDJPY) | {usdjpy:.2f} | {self._interp_usdjpy(usdjpy)} |")

        # 3. Valuation & Allocation
        v_alloc = valuation['equity_bond_allocation']
        v_geo = valuation['geographic_bias']
        
        v_alloc_cn = self._translate_alloc(v_alloc)
        v_geo_cn = self._translate_geo(v_geo)
        
        v_erp = valuation['erp']
        v_erp_str = f"{v_erp*100:.2f}%" if v_erp is not None else "N/A"
        
        # Extract raw valuation inputs
        try:
            em = data.get('equity_market', {})
            ty = data.get('treasury_yields', {})
            cur = data.get('currencies', {})
            
            fwd_pe = em.get('SPX_forward_pe')
            pe_source = em.get('SPX_forward_pe_source', 'Unknown')
            yield_10y = ty.get('GS10_current')
            aud_usd = cur.get('AUDUSD_current')
        except:
            fwd_pe, yield_10y, aud_usd = None, None, None

        md.append(f"\n## 三、估值与配置")
        md.append(f"**股债配置:** {v_alloc_cn}")
        md.append(f"**ERP (股权风险溢价):** {v_erp_str}")
        
        if 'trailing_proxy' in str(valuation.get('pe_source', '')):
             md.append("> ⚠️ **注意:** 由于缺乏 Forward PE，使用了 Trailing PE 作为替代，估值可能偏保守。")
             
        md.append(f"\n| 维度 (Dimension) | 建议 (Suggestion) | 原始数据 (Raw Data) |")
        md.append(f"|---|---|---|")
        
        pe_str = f"{fwd_pe:.2f}" if fwd_pe else "N/A"
        y10_str = f"{yield_10y:.2f}%" if yield_10y else "N/A"
        aud_str = f"{aud_usd:.4f}" if aud_usd else "N/A"
        
        md.append(f"| 资产配置 | {v_alloc_cn} | Forward PE: {pe_str} vs 10Y: {y10_str} |")
        md.append(f"| 地域偏好 | {v_geo_cn} | AUD/USD: {aud_str} |")

        md.append(f"\n### 免责声明")
        md.append(f"本报告仅供信息参考及教育用途，不构成任何金融产品建议。本报告内容在编制时未考虑您的个人投资目标、财务状况或特定需求。历史表现并非未来表现的可靠指标。在做出任何投资决策之前，您应考虑寻求独立的专业咨询。")

        md.append("\n---\n")

        # ==========================================
        # ENGLISH SECTION
        # ==========================================
        md.append(f"# 📊 Macro Strategy Report")
        md.append(f"**Date:** {date_str}")
        
        # I. Economic Cycle
        md.append(f"\n## I. Economic Cycle")
        md.append(f"**Phase:** {c_phase} | **Score:** {c_score}/4")
        
        md.append(f"\n| Metric | Value | Status |")
        md.append(f"|---|---|---|")
        # Spread
        md.append(f"| Yield Spread (10Y-2Y) | {spread_str} | {self._interp_spread_en(spread)} |")
        # Inflation
        md.append(f"| CPI Inflation (YoY) | {cpi_str} | {self._interp_cpi_en(cpi)} |")
        # Unemployment
        md.append(f"| Unemployment (UNRATE) | {unrate_str} | {self._interp_unrate_en(unrate)} |")
        
        # II. Risk Environment
        md.append(f"\n## II. Risk Environment")
        md.append(f"**Environment:** {r_env} | **Risk Score:** {r_score}/3")
        md.append(f"**Position Sizing:** {r_pos}")
        
        md.append(f"\n| Metric | Value | Signal |")
        md.append(f"|---|---|---|")
        md.append(f"| VIX Volatility | {vix:.2f} | {self._interp_vix_en(vix)} |")
        md.append(f"| Dollar Index (DXY) | {dxy:.2f} | {self._interp_dxy_en(dxy)} |")
        md.append(f"| USD/JPY (Carry) | {usdjpy:.2f} | {self._interp_usdjpy_en(usdjpy)} |")
            
        # III. Valuation & Allocation (Tables)
        md.append(f"\n## III. Valuation & Allocation")
        md.append(f"**Allocation:** {v_alloc}")
        md.append(f"**Geo Bias:** {v_geo}")
        md.append(f"**Equity Risk Premium:** {v_erp_str}")

        md.append(f"\n| Dimension | Suggestion | Raw Data |")
        md.append(f"|---|---|---|")
        md.append(f"| Asset Allocation | {v_alloc} | Forward PE: {pe_str} vs 10Y: {y10_str} |")
        md.append(f"| Geographic Bias | {v_geo} | AUD/USD: {aud_str} |")
        
        md.append(f"\n### Disclaimer")
        md.append(f"This report is for informational and educational purposes only and does not constitute financial product advice. It has been prepared without taking into account your personal objectives, financial situation, or needs. Past performance is not a reliable indicator of future performance. You should consider seeking independent professional advice before making any investment decisions.")
        
        return "\n".join(md)
        
    # --- Translation Helpers ---
    def _translate_phase(self, phase):
        map = {
            "Recovery": "复苏期", "Expansion": "扩张期", 
            "Neutral Expansion": "中性扩张", "Overheating": "过热期",
            "Slowdown": "放缓期", "Recession Watch": "衰退预警"
        }
        return map.get(phase, phase)
        
    def _translate_risk_env(self, env):
        map = {
            "Risk On (Low Risk)": "低风险 (Risk On)",
            "Neutral (Medium Risk)": "中性风险",
            "Cautious (High Risk)": "高风险 (谨慎)",
            "Risk Off (Extreme Risk)": "极端风险 (Risk Off)"
        }
        return map.get(env, env)
        
    def _translate_alloc(self, alloc):
        if "Underweight Stocks" in alloc: return "低配股票 / 超配债券"
        if "Overweight Stocks" in alloc: return "超配股票 (积极)"
        if "Neutral" in alloc: return "中性配置 (60/40)"
        return alloc
        
    def _translate_geo(self, geo):
        if "Local Bias" in geo: return "偏好本地资产 (澳洲/新兴)"
        if "US Bias" in geo: return "偏好美元资产 (美股)"
        if "Neutral" in geo: return "全球均衡配置"
        return geo

    # --- Interpretation Helpers (Chinese) ---
    def _interp_spread(self, val):
        if val is None: return "N/A"
        if val > 0.5: return "健康 (>0.5%)"
        if val < 0: return "倒挂 (衰退信号)"
        return "扁平 (警惕)"
        
    def _interp_cpi(self, val):
        if val is None: return "N/A"
        pct = val * 100
        if pct < 2: return "低通胀"
        if pct > 4: return "高通胀"
        return "温和通胀"

    def _interp_unrate(self, val):
        if val is None: return "N/A"
        if val < 4: return "充分就业 (过热风险)"
        if val > 6: return "就业恶化"
        return "就业稳定"
        
    def _interp_vix(self, val):
        if val < 15: return "低波动 (乐观)"
        if val > 25: return "极度恐慌"
        return "正常波动"
        
    def _interp_dxy(self, val):
        if val > 100: return "美元强势 (避险/紧缩)"
        return "美元弱势 (流动性充裕)"
        
    def _interp_usdjpy(self, val):
        if val > 150: return "套息交易活跃 (Risk-On)"
        return "中性"

    # --- Interpretation Helpers (English) ---
    def _interp_spread_en(self, val):
        if val is None: return "N/A"
        if val > 0.5: return "Healthy (>0.5%)"
        if val < 0: return "Inverted (Recession)"
        return "Flat (Caution)"
        
    def _interp_cpi_en(self, val):
        if val is None: return "N/A"
        pct = val * 100
        if pct < 2: return "Low Inflation"
        if pct > 4: return "High Inflation"
        return "Moderate"

    def _interp_unrate_en(self, val):
        if val is None: return "N/A"
        if val < 4: return "Full Employment"
        if val > 6: return "Worsening"
        return "Stable"
        
    def _interp_vix_en(self, val):
        if val < 15: return "Low Vol (Optimistic)"
        if val > 25: return "Extreme Fear"
        return "Normal"
        
    def _interp_dxy_en(self, val):
        if val > 100: return "Strong USD"
        return "Weak USD"
        
    def _interp_usdjpy_en(self, val):
        if val > 150: return "Carry Trade Active"
        return "Neutral"

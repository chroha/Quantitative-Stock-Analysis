"""
Macro Analysis Markdown Report Generator

Generates a Markdown report with a "Macro Dashboard" layout, including:
1. Cross-Asset Performance Table (1D, 1W, 1M, YTD, 52W Position)
2. Economic Indicators Traffic Light System
3. Sector Rotation (11 GICS Sectors) with Contextual Status
4. Market Internals & Risk Analysis
5. Algo Logic & Diagnostics (Deep Dive)
6. AI Strategic Commentary (Bilingual)
"""

import pandas as pd
from datetime import datetime
from typing import Dict, Any, List
from utils.macro_translations import get_label

class MacroMarkdownReport:
    """Generates bilingual Markdown reports for macro analysis."""
    
    def __init__(self, output_dir='./reports'):
        self.output_dir = output_dir

    def generate_report(self, data: Dict[str, Any], analysis_results: Dict[str, Any], ai_commentary: Dict[str, str] = None) -> str:
        """
        Generate the full Bilingual Markdown report (Chinese first, then English).
        """
        md = []
        
        # 1. Chinese Version
        md.append(self._generate_single_language_report(data, analysis_results, lang='cn', commentary=ai_commentary))
        
        md.append("\n\n---\n")
        
        # 2. English Version
        md.append(self._generate_single_language_report(data, analysis_results, lang='en', commentary=ai_commentary))
        
        return "\n".join(md)

    def _generate_single_language_report(self, data: Dict[str, Any], analysis_results: Dict[str, Any], lang: str, commentary: Dict[str, str] = None) -> str:
        """Generate report for a specific language."""
        dashboard = data.get('dashboard_data', {})
        snapshot_date = data.get('snapshot_date', datetime.now().strftime('%Y-%m-%d'))[:10]
        
        md = []
        title = get_label('title', lang)
        gen_at = get_label('generated_at', lang)
        data_status = get_label('data_status', lang)
        
        status_val = data.get('data_quality', {}).get('overall_status', 'Unknown')
        
        md.append(f"# 🌍 {title} - {snapshot_date}")
        md.append(f"> **{gen_at}:** {datetime.now().strftime('%Y-%m-%d %H:%M')} | **{data_status}:** {status_val}")
        md.append("\n---")
        
        # 1. Executive Summary
        md.append(self._render_executive_summary(analysis_results, lang))
        
        # 2. Cross-Asset Performance
        header = get_label('asset_perf', lang)
        md.append(f"## 1. 📈 {header}")
        md.append(self._render_asset_performance_table(dashboard.get('assets', {}), lang))
        
        # 3. Economic Indicators
        header = get_label('econ_indicators', lang)
        md.append(f"## 2. 🚦 {header}")
        md.append(self._render_economic_indicators(dashboard.get('economic', {}), lang))
        
        # 4. Sector Rotation
        # Extract SPY Change for contextual logic
        spy_data = dashboard.get('assets', {}).get('Indices', {}).get('S&P 500', {})
        spy_chg = spy_data.get('change_1d_safe', 0) if spy_data else 0
        
        header = get_label('sector_rotation', lang)
        md.append(f"## 3. 🧩 {header}")
        md.append(self._render_sector_rotation(dashboard.get('sectors', {}), spy_chg, lang))
        
        # 5. Market Internals
        header = get_label('market_internals', lang)
        md.append(f"## 4. 🔬 {header}")
        md.append(self._render_market_internals(dashboard.get('internals', {}), lang))
        
        # 6. Algo Logic & Diagnostics (Deep Dive)
        header = get_label('deep_dive', lang)
        md.append(f"## 5. ⚙️ {header}")
        md.append(self._render_deep_dive(analysis_results, data, lang))
        
        # 7. AI Commentary
        md.append(self._render_ai_commentary(commentary, lang))
        
        return "\n".join(md)

    def _render_executive_summary(self, analysis: Dict, lang: str) -> str:
        """Render the top-level summary of Cycle, Risk, and Valuation."""
        cycle = analysis.get('cycle', {})
        risk = analysis.get('risk', {})
        val = analysis.get('valuation', {})
        
        # Translate dynamic values
        phase = get_label(cycle.get('phase', 'Unknown'), lang)
        
        risk_env_raw = risk.get('environment', 'Unknown')
        risk_env = get_label(risk_env_raw, lang)
        
        val_alloc_raw = val.get('equity_bond_allocation', 'Unknown')
        val_alloc = get_label(val_alloc_raw, lang)
        
        cycle_details = ", ".join(cycle.get('details', []))
        
        risk_score = risk.get('risk_score', 0)
        risk_details = ", ".join(risk.get('details', []))
        
        risk_emoji = "🟢" if "Risk On" in risk_env_raw or "Low" in risk_env_raw else "🟡" if "Neutral" in risk_env_raw else "🔴"
        
        header = get_label('exec_summary', lang)
        col_dim = get_label('dimension', lang)
        col_status = get_label('status', lang)
        col_insight = get_label('key_insight', lang)
        
        lbl_cycle = get_label('biz_cycle', lang)
        lbl_risk = get_label('risk_env', lang)
        lbl_val = get_label('valuation', lang)
        lbl_target = get_label('target', lang)
        
        erp_val = val.get('erp')
        erp_str = f"{erp_val:.2%}" if erp_val is not None else "N/A"
        
        summary = f"""
### 📊 {header}

| {col_dim} | {col_status} | {col_insight} |
| :--- | :--- | :--- |
| **{lbl_cycle}** | **{phase}** | {cycle_details if cycle_details else 'N/A'} |
| **{lbl_risk}** | {risk_emoji} **{risk_env}** | Score: {risk_score}/3. {risk_details} |
| **{lbl_val}** | **{val_alloc}** | ERP: {erp_str} ({lbl_target} > 3%) |
"""
        return summary

    def _render_asset_performance_table(self, assets: Dict, lang: str) -> str:
        """Render a unified table for asset performance."""
        if not assets:
            return get_label('no_data', lang)
            
        col_asset = get_label('asset_class', lang)
        col_instr = get_label('instrument', lang)
        col_price = get_label('price', lang)
        col_pos = get_label('pos_52w', lang)
        
        md = [f"| {col_asset} | {col_instr} | {col_price} | 1D% | 1W% | 1M% | YTD% | {col_pos} |",
              "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |"]
        
        def format_pct(val):
            if val is None: return "-"
            color = "🔴" if val < 0 else "🟢"
            return f"{color} {val*100:+.2f}%"

        def format_pos(val):
            if val is None: return "-"
            return f"{val:.1f}%"

        groups = ['Indices', 'Commodities', 'Crypto', 'Currencies']
        
        for group in groups:
            items = assets.get(group, {})
            group_label = get_label(group, lang)
            for name, metrics in items.items():
                if not metrics: continue
                
                name_display = f"**{name}**"
                ticker = metrics.get('ticker', '')
                price = f"{metrics.get('price', 0):,.2f}"
                
                c1d = format_pct(metrics.get('change_1d_safe'))
                c1w = format_pct(metrics.get('change_1w'))
                c1m = format_pct(metrics.get('change_1m'))
                cytd = format_pct(metrics.get('change_ytd'))
                pos = format_pos(metrics.get('position_52w'))
                
                md.append(f"| {group_label} | {name_display} <br> *({ticker})* | {price} | {c1d} | {c1w} | {c1m} | {cytd} | {pos} |")
                
        return "\n".join(md)

    def _render_sector_rotation(self, sectors: Dict, spy_chg: float, lang: str) -> str:
        """Render Sector Rotation table (11 GICS Sectors) with Smart Status."""
        if not sectors:
            return get_label('no_data', lang)

        col_group = get_label('group', lang)
        col_sector = get_label('sector', lang)
        col_price = get_label('price', lang)
        col_status = get_label('status', lang)

        md = [f"| {col_group} | {col_sector} | {col_price} | 1D% | 1W% | {col_status} |",
              "| :--- | :--- | :---: | :---: | :---: | :--- |"]
        
        def format_pct(val):
            if val is None: return "-"
            color = "🔴" if val < 0 else "🟢"
            return f"{color} {val*100:+.2f}%"

        def get_status(ticker, chg_1d, chg_1w):
            if chg_1d is None: return ""
            c1d = chg_1d
            c1w = chg_1w if chg_1w is not None else 0
            
            # 0. Config
            DEFENSIVE = ['XLP', 'XLV', 'XLU']
            CYCLICAL  = ['XLE', 'XLF', 'XLI', 'XLB']
            GROWTH    = ['XLK', 'XLC', 'XLY']
            
            # 1. Extreme
            if c1d > 0.02: return get_label('sec_surge', lang)
            if c1d < -0.02: return get_label('sec_dump', lang)
            
            # 2. Contextual
            # Safety Bid
            if spy_chg < 0.002 and ticker in DEFENSIVE and c1d > 0.006:
                return get_label('sec_safety', lang)
            # Inflation
            if ticker in ['XLE', 'XLB'] and c1d > 0.008:
                return get_label('sec_inflation', lang)
            # Profit Taking
            if ticker in GROWTH and c1d < -0.012:
                return get_label('sec_profit', lang)
            # Rate Fear
            if ticker in ['XLRE', 'XLU'] and c1d < -0.01:
                return get_label('sec_rate_fear', lang)
            # Rotation (Simplified Check)
            if ticker in CYCLICAL and c1d > 0.008 and abs(spy_chg) < 0.003:
                return get_label('sec_rotation', lang)
            
            # 3. Technical
            if c1w > 0.03 and c1d > 0.002: return get_label('sec_trend', lang)
            if c1w < -0.03 and c1d > 0.005: return get_label('sec_rebound', lang)
            if c1w > 0.03 and -0.01 < c1d < -0.002: return get_label('sec_pullback', lang)
            
            # 4. Flow
            if c1d > 0.005: return get_label('sec_inflow', lang)
            if c1d < -0.005: return get_label('sec_outflow', lang)
            
            return get_label('sec_choppy', lang)

        # Group Definitions
        groups = {
            'defensive': ['XLV', 'XLP', 'XLU'],
            'cyclical': ['XLE', 'XLF', 'XLI', 'XLB', 'XLRE'],
            'sensitive': ['XLK', 'XLC', 'XLY']
        }

        for grp_key, tickers in groups.items():
            grp_label = get_label(grp_key, lang)
            first_row = True
            
            for ticker in tickers:
                sec_data = sectors.get(ticker)
                
                # Check labels
                sec_label = get_label(ticker, lang)
                
                if not sec_data:
                    md.append(f"| {f'**{grp_label}**' if first_row else ''} | {sec_label} | - | - | - | |")
                    first_row = False
                    continue
                
                price = f"{sec_data.get('price', 0):,.2f}"
                c1d_val = sec_data.get('change_1d_safe')
                c1w_val = sec_data.get('change_1w')
                
                c1d_str = format_pct(c1d_val)
                c1w_str = format_pct(c1w_val)
                
                status = get_status(ticker, c1d_val, c1w_val)
                
                g_col = f"**{grp_label}**" if first_row else ""
                md.append(f"| {g_col} | {sec_label} | {price} | {c1d_str} | {c1w_str} | {status} |")
                first_row = False
        
        return "\n".join(md)

    def _render_economic_indicators(self, economics: Dict, lang: str) -> str:
        """Render economic indicators with trend arrows."""
        if not economics:
            return get_label('no_data', lang)
            
        col_cat = get_label('category', lang)
        col_ind = get_label('indicator', lang)
        col_val = get_label('latest_val', lang)
        col_trend = get_label('trend', lang)
        col_prev = get_label('prev_val', lang)
        col_date = get_label('data_date', lang)
        
        md = [f"| {col_cat} | {col_ind} | {col_val} | {col_trend} | {col_prev} | {col_date} |",
              "| :--- | :--- | :---: | :---: | :---: | :---: |"]
        
        rising = get_label('Rising', lang)
        falling = get_label('Falling', lang)
        stable = get_label('Stable', lang)
        
        trend_map = {
            'up': f"↗️ {rising}", 
            'down': f"↘️ {falling}", 
            'stable': f"➡️ {stable}",
            '-': "-"
        }
        
        for category, indicators in economics.items():
            cat_label = get_label(category, lang)
            for name, data in indicators.items():
                if name == 'CPI Context': continue 
                
                if not data or not isinstance(data, dict):
                    val_display = f"{data:.2f}" if isinstance(data, float) else str(data)
                    md.append(f"| {cat_label} | {name} | {val_display} | - | - | - |")
                    continue
                    
                val = data.get('value')
                date = data.get('date', '-')
                prev = data.get('prev_value')
                trend = data.get('trend', '-')
                
                if 'Rate' in name or 'Yield' in name or 'Spread' in name or 'CPI (YoY)' in name or 'Treasury' in name:
                    val_str = f"{val:.2f}%" if val is not None else "-"
                    prev_str = f"{prev:.2f}%" if prev is not None else ""
                else:
                    val_str = f"{val:,.1f}" if val is not None else "-"
                    prev_str = f"{prev:,.1f}" if prev is not None else ""
                
                trend_display = trend_map.get(trend, trend)
                
                md.append(f"| {cat_label} | **{name}** | **{val_str}** | {trend_display} | {prev_str} | {date} |")

        return "\n".join(md)

    def _render_market_internals(self, internals: Dict, lang: str) -> str:
        """Render market internal ratios and VIX structure."""
        if not internals:
            return get_label('no_data', lang)
            
        md = []
        
        # 1. Style & Size
        style = internals.get('Style_Ratio', {})
        size = internals.get('Size_Ratio', {})
        
        header = get_label('style_size', lang)
        col_metric = get_label('metric', lang)
        col_curr = get_label('current_ratio', lang)
        col_mom = get_label('mom_signal', lang)
        col_spread = get_label('spread_1m', lang)
        
        md.append(f"### {header}")
        md.append(f"| {col_metric} | {col_curr} | {col_mom} | {col_spread} |")
        md.append("| :--- | :---: | :---: | :---: |")
        
        lbl_growth = get_label('growth_val', lang)
        lbl_small = get_label('small_large', lang)
        
        if style:
            md.append(f"| **{lbl_growth}** | {style.get('current', 0):.4f} | **{style.get('momentum_signal')}** | {style.get('spread_1m', 0)*100:+.2f}% |")
        if size:
            md.append(f"| **{lbl_small}** | {size.get('current', 0):.4f} | **{size.get('momentum_signal')}** | {size.get('spread_1m', 0)*100:+.2f}% |")
            
        # 2. VIX Structure
        vix_term = internals.get('VIX_Structure', {})
        vix_lvl = internals.get('VIX_Level', {})
        
        if vix_term:
            ratio = vix_term.get('ratio')
            signal = vix_term.get('signal')
            sma20 = vix_term.get('sma20')
            ratio_str = f"{ratio:.2f}" if ratio else "-"
            sma_str = f"{sma20:.2f}" if sma20 else "-"
            
            header_risk = get_label('risk_struct', lang)
            lbl_vix = get_label('vix_level', lang)
            lbl_mom = get_label('vix_mom', lang)
            lbl_note = get_label('risk_note', lang)
            
            md.append(f"\n### {header_risk}")
            md.append(f"- **{lbl_vix}:** {vix_lvl.get('price', 0):.2f} (SMA20: {sma_str})")
            md.append(f"- **{lbl_mom} (VIX/SMA20):** {ratio_str} ({signal})")
            md.append(f"> *{lbl_note}*")
            
        return "\n".join(md)

    def _render_deep_dive(self, analysis: Dict, data: Dict, lang: str) -> str:
        """Render detailed algo logic diagnostics."""
        cycle = analysis.get('cycle', {})
        val = analysis.get('valuation', {})
        
        # Data Extraction
        equity = data.get('equity_market', {})
        treasury = data.get('treasury_yields', {})
        inflation = data.get('inflation', {})
        employment = data.get('employment', {})
        
        pe = equity.get('SPX_forward_pe')
        yield_10y = treasury.get('GS10_current')
        erp = val.get('erp')
        
        spread = treasury.get('yield_curve_10y_2y')
        cpi_yoy = inflation.get('CPI_YOY')
        
        # Safe extraction of UNRATE using fix from previous debugging
        unrate_raw = employment.get('UNRATE')
        unrate = unrate_raw.get('value') if isinstance(unrate_raw, dict) else unrate_raw
        
        phase_raw = cycle.get('phase', 'Unknown')
        phase = get_label(phase_raw, lang)
        
        md = []
        
        # --- Valuation Model ---
        md.append(f"### 🏛️ {get_label('val_header', lang)}")
        md.append(f"> {get_label('val_algorithm', lang)}")
        
        # Table Headers
        c_comp = get_label('component', lang)
        c_input = get_label('input', lang)
        c_logic = get_label('logic', lang)
        c_res = get_label('result', lang)
        
        if pe and yield_10y and erp is not None:
            yield_eq = (1/pe) * 100
            md.append("")
            md.append(f"| {c_comp} | {c_input} | {c_logic} | {c_res} |")
            md.append(f"| :--- | :--- | :--- | :--- |")
            
            l_ey = get_label('equity_yield', lang)
            l_rf = get_label('risk_free', lang)
            l_erp = get_label('erp_label', lang)
            
            md.append(f"| **{l_ey}** | PE: **{pe:.2f}** | $1 / PE$ | **{yield_eq:.2f}%** |")
            md.append(f"| **{l_rf}** | 10Y: **{yield_10y:.2f}%** | Market Rate | **{yield_10y:.2f}%** |")
            md.append(f"| **{l_erp}** | - | $Yield - RiskFree$ | **{erp*100:.2f}%** |")
            
            # Signal Logic
            md.append("")
            md.append(f"**{get_label('signal_logic', lang)}:**")
            
            erp_pct = erp * 100
            trig_ovr = get_label('triggered', lang) if erp_pct > 3.0 else ""
            trig_und = get_label('triggered', lang) if erp_pct < 1.0 else ""
            trig_neu = get_label('triggered', lang) if 1.0 <= erp_pct <= 3.0 else ""
            
            l_over = get_label('Overweight Stocks (Aggressive)', lang)
            l_under = get_label('Underweight Stocks (Defensive)', lang)
            l_neu = get_label('Neutral (60/40)', lang)
            
            md.append(f"* `IF ERP > 3.00%`: 🟢 {l_over} {trig_ovr}")
            md.append(f"* `IF ERP < 1.00%`: 🔴 {l_under} {trig_und}")
            md.append(f"* `ELSE`: 🟡 {l_neu} {trig_neu}")
            
        else:
            md.append(f"_{get_label('no_data', lang)}_")

        md.append("\n---")

        # --- Cycle Model ---
        md.append(f"\n### 🔄 {get_label('cycle_header', lang)}")
        md.append(f"> {get_label('cycle_algorithm', lang)}")
        
        c_fact = get_label('factor', lang)
        c_met = get_label('indicator', lang)
        c_cond = get_label('condition', lang)
        c_score = get_label('score', lang)
        
        md.append("")
        md.append(f"| {c_fact} | {c_met} | {c_cond} | {c_score} |")
        md.append(f"| :--- | :--- | :--- | :---: |")
        
        # Factor 1: Spread
        l_spread = get_label('spread_factor', lang)
        s_val = spread if spread is not None else 0
        s_score_num = 2 if s_val > 0.5 else 1 if s_val > 0 else -2
        s_score_display = f"✅ +{s_score_num}" if s_score_num > 0 else f"❌ {s_score_num}"
        md.append(f"| **{l_spread}** | Spread: **{s_val:.2f}%** | `Spread > 0` | {s_score_display} |")
        
        # Factor 2: Inflation
        l_inf = get_label('inflation_factor', lang)
        i_val = cpi_yoy if cpi_yoy is not None else 0
        # Simulating analyzer logic for display
        i_score_num = 1 if (i_val <= 3.0 and i_val >= 1.0) else -1 if i_val > 4.0 else 0
        i_score_display = f"{'✅' if i_score_num > 0 else '⚠️'} {i_score_num:+}"
        md.append(f"| **{l_inf}** | CPI YoY: **{i_val:.2f}%** | `1.5% < CPI < 3.5%` | {i_score_display} |")
        
        # Factor 3: Employment
        l_emp = get_label('employ_factor', lang)
        u_val = unrate if unrate is not None else 0
        u_score_num = 1 if u_val < 5.0 else -2 if u_val > 6.0 else 0
        u_score_display = f"{'✅' if u_score_num > 0 else '❌'} {u_score_num:+}"
        md.append(f"| **{l_emp}** | U-Rate: **{u_val:.2f}%** | `Rate < 5%` | {u_score_display} |")
        
        # Verdict
        l_verdict = get_label('final_verdict', lang)
        total_score = s_score_num + i_score_num + u_score_num
        md.append(f"| **{l_verdict}** | **{total_score}** | `MAX: 4` | **{phase}** |")
        
        return "\n".join(md)

    def _render_ai_commentary(self, commentary: Dict[str, str], lang: str) -> str:
        """Render AI Commentary Section."""
        if not commentary: return ""
        text = commentary.get(lang, "")
        if not text: return ""
        
        header = "AI 深度解读" if lang == 'cn' else "AI Strategic Analysis"
        return f"\n## 6. 🧠 {header}\n\n{text}"

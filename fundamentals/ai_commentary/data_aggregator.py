"""
Data Aggregator for AI Commentary.
Aggregates financial, technical, and valuation data into a simplified format for AI analysis.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

class DataAggregator:
    """Aggregates data from various scoring and valuation outputs."""
    
    def __init__(self, data_dir: str):
        """
        Initialize aggregator.
        
        Args:
            data_dir: Directory containing data files (required)
        """
        self.data_dir = Path(data_dir)
        
    def _load_json(self, file_path: Path) -> Dict[str, Any]:
        """Load JSON data from file."""
        if not file_path.exists():
            return {}
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    def _find_latest_file(self, pattern: str) -> Optional[Path]:
        """Find the most recent file matching a pattern."""
        files = list(self.data_dir.glob(pattern))
        if not files:
            return None
        files.sort(reverse=True)
        return files[0]

    def aggregate(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Aggregate data for a specific symbol.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Simplified dictionary of aggregated data or None if critical data missing
        """
        symbol = symbol.upper()
        
        # Find latest files
        fin_path = self._find_latest_file(f"financial_score_{symbol}_*.json")
        tech_path = self._find_latest_file(f"technical_score_{symbol}_*.json")
        val_path = self._find_latest_file(f"valuation_{symbol}_*.json")
        raw_path = self._find_latest_file(f"initial_data_{symbol}_*.json")
        
        if not fin_path or not tech_path or not val_path:
            return None
            
        fin_data = self._load_json(fin_path)
        tech_data = self._load_json(tech_path)
        val_data = self._load_json(val_path)
        
        # Extract date from one of the files
        date_str = fin_path.stem.split('_')[-1]
        
        # Extract period info from raw data
        latest_period = "Unknown"
        history_years = 0
        latest_period = "Unknown"
        history_years = 0
        if raw_path:
            raw_data = self._load_json(raw_path)
            stmts = raw_data.get('income_statements', [])
            bs_stmts = raw_data.get('balance_sheets', [])
            
            p1 = ""
            p2 = ""
            
            if stmts and len(stmts) > 0:
                p1 = stmts[0].get('std_period', '')
                # Only count Annual/TTM for history depth display
                # Need to handle dict access since raw data is dict here, not object? 
                # Yes, _load_json returns dict. 
                # Check period_type field availability.
                hist_count = 0
                for s in stmts:
                    ptype = s.get('std_period_type', 'FY') # Default to FY if missing
                    if ptype in ['FY', 'TTM']:
                        hist_count += 1
                history_years = hist_count
                
            if bs_stmts and len(bs_stmts) > 0:
                p2 = bs_stmts[0].get('std_period', '')
                
            # Take the latest date string (YYYY-MM-DD comparison works alphabetically)
            if p1 and p2:
                latest_period = max(p1, p2)
            elif p1:
                latest_period = p1
            elif p2:
                latest_period = p2

        # Build simplified structure
        aggregated = {
            "stock_info": {
                "symbol": symbol,
                "sector": fin_data.get('metadata', {}).get('sector', 'Unknown'), # Sector moved to meta in fin data? Check structure
                "price": tech_data.get('score', {}).get('data_info', {}).get('current_price', 0),
                "date": date_str,
                "latest_period": latest_period,
                "history_years": history_years
            },
            
            "financial_score": self._simplify_financial(fin_data.get('score', {})),
            "technical_score": self._simplify_technical(tech_data.get('score', {})),
            "valuation": self._simplify_valuation(val_data)
        }
        
        # Cross-fill price/sector if missing
        if aggregated['stock_info']['sector'] == 'Unknown':
             aggregated['stock_info']['sector'] = val_data.get('sector', 'Unknown')
             
        if aggregated['stock_info']['price'] == 0:
            aggregated['stock_info']['price'] = val_data.get('current_price', 0)
            
        return aggregated

    def _simplify_financial(self, score_data: Dict) -> Dict:
        """Simplify financial score data."""
        cats = score_data.get('category_scores', {})
        
        # Helper to extract metric details from nested category structure
        def get_metric(metric_name):
            # Search for metric in all categories
            for cat_key, cat_val in cats.items():
                metrics = cat_val.get('metrics', {})
                if metric_name in metrics:
                    m = metrics[metric_name]
                    return {
                        "val": m.get('value', 0),
                        "score": m.get('weighted_score', 0), # Use weighted score
                        "max": m.get('weight', 0),
                        "rank": m.get('interpretation', 'N/A').split('(')[-1].strip(')') # Try extract 'Top 10%'
                    }
            return {"val": 0, "score": 0, "max": 0, "rank": "N/A"}

        return {
            "total": {"score": score_data.get('total_score', 0)},
            "profitability": {
                "score": cats.get('profitability', {}).get('score', 0),
                "max": cats.get('profitability', {}).get('max', 0),
                "pct": cats.get('profitability', {}).get('percentage', 0),
                "roic": get_metric('roic'),
                "roe": get_metric('roe'),
                "op_margin": get_metric('operating_margin'),
                "gross_margin": get_metric('gross_margin'),
                "net_margin": get_metric('net_margin')
            },
            "growth": {
                "score": cats.get('growth', {}).get('score', 0),
                "max": cats.get('growth', {}).get('max', 0),
                "pct": cats.get('growth', {}).get('percentage', 0),
                "fcf_cagr": get_metric('fcf_cagr_5y'),
                "ni_cagr": get_metric('net_income_cagr_5y'),
                "rev_cagr": get_metric('revenue_cagr_5y'),
                "quality": get_metric('earnings_quality_3y'),
                "debt": get_metric('fcf_to_debt_ratio')
            },
            "capital": {
                "score": cats.get('capital_allocation', {}).get('score', 0),
                "max": cats.get('capital_allocation', {}).get('max', 0),
                "pct": cats.get('capital_allocation', {}).get('percentage', 0),
                "buyback": get_metric('share_dilution_cagr_5y'),
                "capex": get_metric('capex_intensity_3y'),
                "sbc": get_metric('sbc_impact_3y')
            }
        }

    def _simplify_technical(self, score_data: Dict) -> Dict:
        """Simplify technical score data."""
        cats = score_data.get('categories', {})
        
        # Helper to get indicator data
        # Note: Category keys in JSON might differ from what we initially thought
        # JSON keys: 'trend_strength', 'momentum', 'volatility', 'price_structure', 'volume_price'
        
        def fmt(cat_key, ind_key):
            # Check if category exists
            if cat_key not in cats:
                return {"val": 0, "score": 0, "max": 0, "signal": "N/A"}
                
            d = cats[cat_key].get('indicators', {}).get(ind_key, {})
            explanation = d.get('explanation', '')
            
            # Signal extraction
            signal = explanation
            if '(' in explanation and ')' in explanation:
                pass
            
            if not signal: signal = "N/A"
            
            # Value extraction
            val = 0
            # Common keys for primary value
            d_keys = d.keys()
            for key in [ind_key, cat_key, 'value', 'current_price', 'adx', 'rsi', 'atr_pct', 'roc', 'position', 'bandwidth', 'nearest_resistance']:
                if key in d_keys:
                     if isinstance(d[key], (int, float)):
                         val = d[key]
                         break
            
            return {
                "val": val, 
                "score": d.get('score', 0), 
                "max": d.get('max_score', 0), 
                "signal": signal
            }

        return {
            "total": {"score": score_data.get('total_score', 0)},
            "trend": {
                "score": cats.get('trend_strength', {}).get('earned_points', 0), 
                "max": cats.get('trend_strength', {}).get('max_points', 0),
                "adx": fmt('trend_strength', 'adx'),
                "multi_ma": fmt('trend_strength', 'multi_ma'),
                "52w_pos": fmt('trend_strength', 'price_position')
            },
            "momentum": {
                "score": cats.get('momentum', {}).get('earned_points', 0),
                "max": cats.get('momentum', {}).get('max_points', 0),
                "rsi": fmt('momentum', 'rsi'),
                "macd": fmt('momentum', 'macd'),
                "roc": fmt('momentum', 'roc')
            },
            "volatility": {
                "score": cats.get('volatility', {}).get('earned_points', 0),
                "max": cats.get('volatility', {}).get('max_points', 0),
                "atr": fmt('volatility', 'atr'),
                "bollinger": fmt('volatility', 'bollinger')
            },
            "structure": {
                "score": cats.get('price_structure', {}).get('earned_points', 0),
                "max": cats.get('price_structure', {}).get('max_points', 0),
                "resistance": fmt('price_structure', 'support_resistance'),
                "high_low": fmt('price_structure', 'high_low_structure')
            },
            "volume": {
                "score": cats.get('volume_price', {}).get('earned_points', 0),
                "max": cats.get('volume_price', {}).get('max_points', 0),
                "obv": fmt('volume_price', 'obv'),
                "vol_strength": fmt('volume_price', 'volume_strength')
            }
        }

    def _simplify_valuation(self, val_data: Dict) -> Dict:
        """Simplify valuation data."""
        methods = val_data.get('method_results', {})
        
        def fmt(key):
            m = methods.get(key, {})
            return {
                "fair": m.get('fair_value', 0),
                "wt": int(m.get('weight', 0) * 100),
                "up": m.get('upside_pct', 0)
            }
            
        return {
            "fair": val_data.get('weighted_fair_value', 0),
            "current": val_data.get('current_price', 0),
            "upside": val_data.get('price_difference_pct', 0),
            "pe": fmt('pe'),
            "ps": fmt('ps'),
            "pb": fmt('pb'),
            "ev_ebitda": fmt('ev_ebitda'),
            "ev_sales": fmt('ev_sales'),  # Just in case
            "peg": fmt('peg'),            # Just in case
            "ddm": fmt('ddm'),
            "analyst": fmt('analyst'),
            "dcf": fmt('dcf'),
            "graham": fmt('graham'),
            "lynch": fmt('peter_lynch')
        }
    
    def get_raw_data_appendix(self, symbol: str) -> str:
        """
        Generate a markdown appendix with all raw data for reference.
        Format: English Name | Chinese Name | Value | Field ID
        Uses utils.metric_registry for standardized naming.
        """
        from utils.metric_registry import (
            FINANCIAL_METRICS, TECHNICAL_INDICATORS, VALUATION_MODELS, MetricFormat
        )
        
        symbol = symbol.upper()
        lines = []
        
        # Find data files
        fin_score_path = self._find_latest_file(f"financial_score_{symbol}_*.json")
        tech_score_path = self._find_latest_file(f"technical_score_{symbol}_*.json")
        val_path = self._find_latest_file(f"valuation_{symbol}_*.json")
        # Add these to top scope
        raw_path = self._find_latest_file(f"initial_data_{symbol}_*.json")
        fin_data_path = self._find_latest_file(f"financial_data_{symbol}_*.json")
        
        lines.append("\n---\n")
        lines.append("## 📊 原始数据附表 (Raw Data Appendix)\n")
        lines.append("> 方便查阅每个指标的原始值和程序字段名。\n")
        
        # Helper for formatting values based on Registry Definition
        def format_val(val, fmt_type):
            if val is None: return "N/A (Missing)"
            if isinstance(val, (int, float)):
                if fmt_type == MetricFormat.PERCENT:
                    # Heuristic: if value is small decimal (e.g. 0.15), it's likely 15%
                    return f"{val*100:.2f}%"
                elif fmt_type in (MetricFormat.CURRENCY, MetricFormat.CURRENCY_LARGE):
                    # Human readable large numbers
                    abs_val = abs(val)
                    if abs_val >= 1e9:
                        return f"${val/1e9:.2f}B"
                    elif abs_val >= 1e6:
                        return f"${val/1e6:.2f}M"
                    return f"${val:.2f}"
                elif fmt_type == MetricFormat.DECIMAL:
                    return f"{val:.4f}" if abs(val) < 10 else f"{val:.2f}"
            return str(val)

        # Helper for extracting value from potentially source-wrapped dicts
        def get_field_val(obj, field_name):
            if not obj: return None
            val = obj.get(field_name)
            if isinstance(val, dict) and 'value' in val:
                return val['value']
            return val

        # === Financial Data Components (Source: Financial Data) ===
        if fin_data_path:
            fd = self._load_json(fin_data_path)
            if fd:
                metrics = fd.get('metrics', {})
                prof = metrics.get('profitability', {})
                growth = metrics.get('growth', {})
                cap = metrics.get('capital_allocation', {})
                
                lines.append("### 1. 财务计算组件 (Financial Calculation Components)\n")
                lines.append("| Component | 中文名称 | Value (数值) | Logic (逻辑) |")
                lines.append("|---|---|---|---|")
                
                # ROIC Components
                lines.append(f"| NOPAT | 税后营业利润 | {format_val(prof.get('roic_nopat'), MetricFormat.CURRENCY)} | `Operating Income * (1 - Tax Rate)` |")
                lines.append(f"| Invested Capital | 投入资本 | {format_val(prof.get('roic_invested_capital'), MetricFormat.CURRENCY)} | `Total Equity + Total Debt - Cash` |")
                lines.append(f"| Tax Rate | 有效税率 | {format_val(prof.get('roic_effective_tax_rate'), MetricFormat.PERCENT)} | `Income Tax / Pretax Income` |")
                
                # Margin Components (Revenue is already in Valuation section, but repeated here for completeness context)
                # We need raw income statement values which are in initial_data, but financial_data has computed margins.
                # Let's use the raw data loaded earlier if available.
                if raw_path:
                    raw_d = self._load_json(raw_path)
                    stmts = raw_d.get('income_statements', [])
                    if stmts:
                        curr = stmts[0]
                        gp = get_field_val(curr, 'std_gross_profit')
                        op_inc = get_field_val(curr, 'std_operating_income')
                        lines.append(f"| Gross Profit | 毛利润 | {format_val(gp, MetricFormat.CURRENCY)} | `Revenue - Cost of Revenue` |")
                        lines.append(f"| Operating Income | 营业利润 | {format_val(op_inc, MetricFormat.CURRENCY)} | `Gross Profit - OpEx` |")
                
                # Cash Flow Components
                fcf = growth.get('fcf_latest') if 'fcf_latest' in growth else 'N/A'
                lines.append(f"| FCF (Latest) | 自由现金流 | {format_val(fcf, MetricFormat.CURRENCY)} | `OCF - CapEx` |")
                
                # Check for OCF and CapEx in raw data
                if raw_path:
                    raw_d = self._load_json(raw_path)
                    cf_stmts = raw_d.get('cash_flow_statements', [])
                    if cf_stmts:
                        curr_cf = cf_stmts[0]
                        ocf = get_field_val(curr_cf, 'std_cash_flow_operating')
                        capex = get_field_val(curr_cf, 'std_capex')
                        lines.append(f"| Operating Cash Flow | 经营现金流 | {format_val(ocf, MetricFormat.CURRENCY)} | `From Cash Flow Stmt` |")
                        lines.append(f"| Capital Expenditure | 资本支出 | {format_val(capex, MetricFormat.CURRENCY)} | `From Cash Flow Stmt` |")
                
                # Capital Allocation
                lines.append(f"| SBC Impact | 股权激励 | {format_val(cap.get('sbc_impact_3y'), MetricFormat.PERCENT)} | `SBC / Revenue (3Y Avg)` |")
                lines.append(f"| Dilution Rate | 稀释率 | {format_val(cap.get('share_dilution_cagr_5y'), MetricFormat.PERCENT)} | `Share Count CAGR` |")
                
                lines.append("")
        
        # === Technical Data Components (Source: Technical Score) ===
        if tech_score_path:
            td = self._load_json(tech_score_path)
            if td:
                score_data = td.get('score', {})
                cats = score_data.get('categories', {})
                data_info = score_data.get('data_info', {})
                
                # Helper to find specific indicator values in categories
                def find_ind_val(ind_name, key='value'):
                    for cat in cats.values():
                        inds = cat.get('indicators', {})
                        if ind_name in inds:
                            return inds[ind_name].get(key)
                    return None
                
                lines.append("### 2. 技术指标组件 (Technical Indicator Components)\n")
                lines.append("| Component | 中文名称 | Value (数值) | Context (参考) |")
                lines.append("|---|---|---|---|")
                
                # Market Data (Raw inputs for Position, Volume Ratio)
                latest_price = data_info.get('latest_price')
                high_52w = data_info.get('high_52w')
                low_52w = data_info.get('low_52w')
                
                lines.append(f"| Latest Price | 最新价格 | {format_val(latest_price, MetricFormat.CURRENCY)} | `Close Price` |")
                lines.append(f"| 52-Week High | 52周最高 | {format_val(high_52w, MetricFormat.CURRENCY)} | `Highest Price (1Y)` |")
                lines.append(f"| 52-Week Low | 52周最低 | {format_val(low_52w, MetricFormat.CURRENCY)} | `Lowest Price (1Y)` |")
                
                latest_vol = data_info.get('latest_volume')
                avg_vol = data_info.get('avg_volume')
                lines.append(f"| Latest Volume | 最新成交量 | {format_val(latest_vol, MetricFormat.DECIMAL)} | `Daily Volume` |")
                lines.append(f"| Avg Volume | 平均成交量 | {format_val(avg_vol, MetricFormat.DECIMAL)} | `20-Day Average` |")
                
                # Moving Averages (Trend inputs)
                sma_20 = find_ind_val('multi_ma', 'ma20')
                if sma_20:
                    lines.append(f"| SMA 20 | 20日均线 | {format_val(sma_20, MetricFormat.CURRENCY)} | `Short Trend` |")
                
                sma_50 = find_ind_val('multi_ma', 'ma50')
                if sma_50:
                    lines.append(f"| SMA 50 | 50日均线 | {format_val(sma_50, MetricFormat.CURRENCY)} | `Medium Trend` |")
                
                sma_200 = find_ind_val('multi_ma', 'ma200')
                if sma_200:
                    lines.append(f"| SMA 200 | 200日均线 | {format_val(sma_200, MetricFormat.CURRENCY)} | `Long Trend` |")
                
                # Volatility Components (Raw Bollinger Bands instead of Bandwidth)
                bb_upper = find_ind_val('bollinger', 'upper')
                bb_lower = find_ind_val('bollinger', 'lower')
                bb_middle = find_ind_val('bollinger', 'middle')
                
                if bb_upper:
                    lines.append(f"| BB Upper | 布林上轨 | {format_val(bb_upper, MetricFormat.CURRENCY)} | `20D SMA + 2*StdDev` |")
                if bb_middle:
                     lines.append(f"| BB Middle | 布林中轨 | {format_val(bb_middle, MetricFormat.CURRENCY)} | `20D SMA` |")
                if bb_lower:
                    lines.append(f"| BB Lower | 布林下轨 | {format_val(bb_lower, MetricFormat.CURRENCY)} | `20D SMA - 2*StdDev` |")
                
                # Momentum Raw Values
                rsi = find_ind_val('rsi', 'rsi')
                lines.append(f"| RSI (14) | 相对强弱指数 | {format_val(rsi, MetricFormat.DECIMAL)} | `Momentum (0-100)` |")
                
                roc = find_ind_val('roc', 'roc')
                if roc is not None:
                    lines.append(f"| ROC (20) | 变动率 | {format_val(roc, MetricFormat.PERCENT)} | `Price Rate of Change` |")
                
                macd_line = find_ind_val('macd', 'macd')
                signal_line = find_ind_val('macd', 'signal_line')
                macd_hist = find_ind_val('macd', 'histogram')
                
                if macd_line:
                    lines.append(f"| MACD Line | MACD线 | {format_val(macd_line, MetricFormat.DECIMAL)} | `12EMA - 26EMA` |")
                if signal_line:
                    lines.append(f"| Signal Line | 信号线 | {format_val(signal_line, MetricFormat.DECIMAL)} | `9EMA of MACD` |")
                if macd_hist:
                    lines.append(f"| MACD Hist | MACD柱 | {format_val(macd_hist, MetricFormat.DECIMAL)} | `MACD - Signal` |")
                
                # Trend Strength (ADX)
                adx = find_ind_val('adx', 'adx')
                if adx:
                    lines.append(f"| ADX | 趋势强度 | {format_val(adx, MetricFormat.DECIMAL)} | `>25=Strong Trend` |")
                
                # Structure
                supp = find_ind_val('support_resistance', 'nearest_support')
                res = find_ind_val('support_resistance', 'nearest_resistance')
                if supp:
                    lines.append(f"| Support | 最近支撑 | {format_val(supp, MetricFormat.CURRENCY)} | `Nearest Support Level` |")
                if res:
                    lines.append(f"| Resistance | 最近阻力 | {format_val(res, MetricFormat.CURRENCY)} | `Nearest Resistance Level` |")
                    
                hl_pattern = find_ind_val('high_low_structure', 'pattern')
                if hl_pattern:
                    lines.append(f"| Structure | 市场结构 | {format_val(hl_pattern, MetricFormat.STRING)} | `High/Low Pattern` |")

                # Volume Analysis
                obv = find_ind_val('obv', 'obv')
                if obv:
                    # OBV is cumulative, formatting as large currency just to get B/M suffix but no currency sign logic?
                    # format_val uses currency logic if fmt=CURRENCY. We can use DECIMAL or just force string.
                    # Let's use DECIMAL for now, or add a CUSTOM handling if easy.
                    lines.append(f"| OBV | 能量潮 | {format_val(obv, MetricFormat.DECIMAL)} | `On-Balance Volume` |")
                    
                vol_ratio = find_ind_val('volume_strength', 'volume_ratio')
                if vol_ratio:
                    lines.append(f"| Vol Ratio | 量比 | {format_val(vol_ratio, MetricFormat.DECIMAL)} | `Vol / AvgVol` |")

                # Volatility (ATR)
                atr = find_ind_val('atr', 'atr') # Raw value
                atr_pct = find_ind_val('atr', 'atr_pct') # Percentage
                if atr_pct:
                    lines.append(f"| ATR % | 波动率百分比 | {format_val(atr_pct, MetricFormat.PERCENT)} | `ATR / Price` |")
                
                lines.append("")

        # === Valuation Input Data (Source: Initial Data + Financial Data) ===
        # Path finding moved to top of function
        
        if raw_path or fin_data_path:
            lines.append("### 3. 估值基础数据 (Valuation Input Data)\n")
            lines.append("| English Name | 中文名称 | Value (数值) | Field Name (字段) |")
            lines.append("|---|---|---|---|")
            
            # Load data sources
            raw_data = self._load_json(raw_path) if raw_path else {}
            fin_metrics_data = self._load_json(fin_data_path) if fin_data_path else {}
            fin_metrics = fin_metrics_data.get('metrics', {})
            
            # Extract profile and latest statement data
            profile = raw_data.get('profile', {})
            income_stmts = raw_data.get('income_statements', [])
            balance_stmts = raw_data.get('balance_sheets', [])
            cf_stmts = raw_data.get('cash_flows', [])
            
            # Helper to get field value safely
            def get_field_val(obj, field):
                if not obj: return None
                f = obj.get(field)
                # Handle both dict with 'value' (FieldWithSource) and direct value
                if isinstance(f, dict) and 'value' in f:
                     return f.get('value')
                return f
            
            # 1. Growth Metrics (CAGR)
            lines.append(f"| Revenue CAGR (5Y) | 营收增速 | {format_val(fin_metrics.get('growth', {}).get('revenue_cagr_5y'), MetricFormat.PERCENT)} | `revenue_cagr_5y` |")
            lines.append(f"| Net Income CAGR (5Y) | 净利增速 | {format_val(fin_metrics.get('growth', {}).get('net_income_cagr_5y'), MetricFormat.PERCENT)} | `net_income_cagr_5y` |")
            lines.append(f"| FCF CAGR (5Y) | FCF增速 | {format_val(fin_metrics.get('growth', {}).get('fcf_cagr_5y'), MetricFormat.PERCENT)} | `fcf_cagr_5y` |")
            
            # 2. Latest Financials (Verification Data)
            if income_stmts:
                latest_is = income_stmts[0]
                lines.append(f"| Net Income (Latest) | 最新净利润 | {format_val(get_field_val(latest_is, 'std_net_income'), MetricFormat.CURRENCY_LARGE)} | `std_net_income` |")
                lines.append(f"| Revenue (Latest) | 最新营收 | {format_val(get_field_val(latest_is, 'std_revenue'), MetricFormat.CURRENCY_LARGE)} | `std_revenue` |")
                lines.append(f"| EBITDA | EBITDA | {format_val(get_field_val(latest_is, 'std_ebitda'), MetricFormat.CURRENCY_LARGE)} | `std_ebitda` |")

            if cf_stmts:
                latest_cf = cf_stmts[0]
                # FCF Calculation Components
                ocf = get_field_val(latest_cf, 'std_operating_cash_flow')
                capex = get_field_val(latest_cf, 'std_capex')
                fcf = get_field_val(latest_cf, 'std_free_cash_flow')
                sbc = get_field_val(latest_cf, 'std_stock_based_compensation')
                stock_repurchase = get_field_val(latest_cf, 'std_repurchase_of_stock')
                
                # If FCF missing, calculate
                if fcf is None and ocf is not None and capex is not None:
                    fcf = ocf + capex # Capex is usually negative
                    
                lines.append(f"| Operating Cash Flow | 经营现金流 | {format_val(ocf, MetricFormat.CURRENCY_LARGE)} | `std_operating_cash_flow` |")
                lines.append(f"| Capital Expenditure | 资本支出 | {format_val(capex, MetricFormat.CURRENCY_LARGE)} | `std_capex` |")
                lines.append(f"| Free Cash Flow | 自由现金流 | {format_val(fcf, MetricFormat.CURRENCY_LARGE)} | `OCF - CapEx` |")
                
                lines.append(f"| Stock Based Comp | 股权激励金额 | {format_val(sbc, MetricFormat.CURRENCY_LARGE)} | `std_stock_based_compensation` |")
                lines.append(f"| Stock Repurchase | 股票回购金额 | {format_val(stock_repurchase, MetricFormat.CURRENCY_LARGE)} | `std_repurchase_of_stock` |")
            
            if balance_stmts:
                latest_bs = balance_stmts[0]
                total_debt = get_field_val(latest_bs, 'std_total_debt')
                cash = get_field_val(latest_bs, 'std_cash') or get_field_val(latest_bs, 'std_cash_and_equivalents')
                shareholder_equity = get_field_val(latest_bs, 'std_shareholder_equity')
                
                lines.append(f"| Total Debt | 总债务 | {format_val(total_debt, MetricFormat.CURRENCY_LARGE)} | `std_total_debt` |")
                lines.append(f"| Cash & Equiv | 现金及等价物 | {format_val(cash, MetricFormat.CURRENCY_LARGE)} | `std_cash` |")
                lines.append(f"| Shareholder Equity | 股东权益 | {format_val(shareholder_equity, MetricFormat.CURRENCY_LARGE)} | `std_shareholder_equity` |")
            
            # 3. Quality & Allocation Ratios (Calculated)
            # Access nested metrics correctly
            metrics_growth = fin_metrics.get('growth', {})
            metrics_cap = fin_metrics.get('capital_allocation', {})
            metrics_prof = fin_metrics.get('profitability', {})
            
            lines.append(f"| Earnings Quality | 盈利质量 | {format_val(metrics_growth.get('earnings_quality_3y') or metrics_prof.get('earnings_quality'), MetricFormat.DECIMAL)} | `OCF / Net Income` |")
            lines.append(f"| CapEx Intensity | 资本开支占比 | {format_val(metrics_cap.get('capex_intensity_3y'), MetricFormat.PERCENT)} | `CapEx / OCF (Avg 3Y)` |")
            lines.append(f"| SBC Impact | SBC营收占比 | {format_val(metrics_cap.get('sbc_impact_3y'), MetricFormat.PERCENT)} | `SBC / Revenue (Avg 3Y)` |")

            # Market data from profile
            market_cap = get_field_val(profile, 'std_market_cap')
            lines.append(f"| Market Cap | 市值 | {format_val(market_cap, MetricFormat.CURRENCY_LARGE)} | `profile.std_market_cap` |")
            
            # Price ratios
            pe_ratio = get_field_val(profile, 'std_pe_ratio')
            pb_ratio = get_field_val(profile, 'std_pb_ratio')
            ps_ratio = get_field_val(profile, 'std_ps_ratio')
            peg_ratio = get_field_val(profile, 'std_peg_ratio')
            div_yield = get_field_val(profile, 'std_dividend_yield')
            
            lines.append(f"| P/E Ratio | 市盈率 | {format_val(pe_ratio, MetricFormat.DECIMAL)} | `profile.std_pe_ratio` |")
            lines.append(f"| P/B Ratio | 市净率 | {format_val(pb_ratio, MetricFormat.DECIMAL)} | `profile.std_pb_ratio` |")
            lines.append(f"| P/S Ratio | 市销率 | {format_val(ps_ratio, MetricFormat.DECIMAL)} | `profile.std_ps_ratio` |")
            lines.append(f"| PEG Ratio | PEG比率 | {format_val(peg_ratio, MetricFormat.DECIMAL)} | `profile.std_peg_ratio` |")
            lines.append(f"| Dividend Yield | 股息率 | {format_val(div_yield, MetricFormat.PERCENT)} | `profile.std_dividend_yield` |")

            # EPS
            eps = get_field_val(profile, 'std_eps')
            forward_eps = get_field_val(profile, 'std_forward_eps')
            book_value = get_field_val(profile, 'std_book_value_per_share')
            earnings_growth = get_field_val(profile, 'std_earnings_growth')
            
            lines.append(f"| EPS (TTM) | 每股收益 | {format_val(eps, MetricFormat.CURRENCY)} | `profile.std_eps` |")
            lines.append(f"| Forward EPS | 前瞻每股收益 | {format_val(forward_eps, MetricFormat.CURRENCY)} | `profile.std_forward_eps` |")
            lines.append(f"| Book Value/Share | 每股账面价值 | {format_val(book_value, MetricFormat.CURRENCY)} | `std_book_value_per_share` |")
            lines.append(f"| Earnings Growth | 盈利增长率 | {format_val(earnings_growth, MetricFormat.PERCENT)} | `profile.std_earnings_growth` |")

        lines.append("")
        return "\n".join(lines)


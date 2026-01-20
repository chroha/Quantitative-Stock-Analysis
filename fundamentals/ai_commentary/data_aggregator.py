"""
Data Aggregator for AI Commentary.
Aggregates financial, technical, and valuation data into a simplified format for AI analysis.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

class DataAggregator:
    """Aggregates data from various scoring and valuation outputs."""
    
    def __init__(self, data_dir: str = "generated_data"):
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
                history_years = len(stmts)
                
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
                "52w_pos": fmt('trend_strength', 'price_position')
            },
            "momentum": {
                "score": cats.get('momentum', {}).get('earned_points', 0),
                "max": cats.get('momentum', {}).get('max_points', 0),
                "rsi": fmt('momentum', 'rsi'),
                "macd": fmt('momentum', 'macd')
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
                "resistance": fmt('price_structure', 'support_resistance')
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
        """
        symbol = symbol.upper()
        lines = []
        
        # Find data files
        fin_path = self._find_latest_file(f"financial_score_{symbol}_*.json")
        fin_data_path = self._find_latest_file(f"financial_data_{symbol}_*.json")
        tech_path = self._find_latest_file(f"technical_score_{symbol}_*.json")
        val_path = self._find_latest_file(f"valuation_{symbol}_*.json")
        
        lines.append("\n---\n")
        lines.append("## 📊 原始数据附表 (Raw Data Appendix)\n")
        lines.append("> 方便查阅每个指标的原始值和程序字段名。\n")
        
        # Definitions for mapping
        # key: (English Name, Chinese Name)
        fin_map = {
            # Profitability
            'roic': ('ROIC', '投资资本回报率'),
            'roe': ('ROE', '股本回报率'),
            'net_margin': ('Net Profit Margin', '净利率'),
            'operating_margin': ('Operating Margin', '营业利润率'),
            'gross_margin': ('Gross Margin', '毛利率'),
            # Growth
            'revenue_cagr_5y': ('Revenue CAGR (5Y)', '5年营收复合增长'),
            'net_income_cagr_5y': ('Net Income CAGR (5Y)', '5年净利复合增长'),
            'fcf_cagr_5y': ('FCF CAGR (5Y)', '5年自由现金流增长'),
            # Capital
            'quality_of_earnings': ('Quality of Earnings', '盈利质量(OCF/NI)'),
            'fcf_to_debt': ('FCF to Debt', '自由现金流/债务'),
            'dept_coverage': ('Debt Coverage', '债务覆盖率'),
            'share_dilution_cagr_5y': ('Share Dilution CAGR', '股份稀释率(负为回购)'),
            'capex_intensity_3y': ('Capex Intensity', '资本支出强度'),
            'debt_to_equity': ('Debt to Equity', '债务股本比')
        }
        
        # === Financial Metrics ===
        if fin_data_path:
            fd = self._load_json(fin_data_path)
            if fd:
                metrics = fd.get('metrics', {})
                lines.append("### 1. 财务指标 (Financial Metrics)\n")
                lines.append("| English Name | 中文名称 | Value (数值) | Field Name (字段) |")
                lines.append("|---|---|---|---|")
                
                # We flatten the categories to list them all
                for category in ['profitability', 'growth', 'capital_allocation']:
                    cat_data = metrics.get(category, {})
                    keys = sorted(cat_data.keys())
                    for k in keys:
                        v = cat_data[k]
                        if v is None: continue
                        
                        # Get names
                        en_name, cn_name = fin_map.get(k, (k.replace('_', ' ').title(), '未知指标'))
                        
                        # Format value
                        if isinstance(v, float):
                            if 'margin' in k or 'roic' in k or 'roe' in k or 'cagr' in k:
                                val_str = f"{v*100:.2f}%"
                            elif abs(v) < 100:
                                val_str = f"{v:.4f}"
                            else:
                                val_str = f"{v:.2f}"
                        else:
                            val_str = str(v)
                            
                        lines.append(f"| {en_name} | {cn_name} | {val_str} | `{k}` |")
                lines.append("")
        
        # === Technical Indicators ===
        if tech_path:
            td = self._load_json(tech_path)
            if td:
                score = td.get('score', {})
                cats = score.get('categories', {})
                
                lines.append("### 2. 技术指标 (Technical Indicators)\n")
                lines.append("| English Name | 中文名称 | Value (数值) | Field Name (字段) |")
                lines.append("|---|---|---|---|")
                
                tech_map = {
                    'rsi': ('RSI', '相对强弱指数'),
                    'macd': ('MACD', '指数平滑异同移动平均'),
                    'adx': ('ADX', '平均趋向指数'),
                    'atr': ('ATR', '平均真实波幅'),
                    'obv': ('OBV', '能量潮'),
                    'roc': ('ROC', '变动率'),
                    'williams_r': ('Williams %R', '威廉指标'),
                    'stoch_k': ('Stoch K', '随机指标K'),
                    'current_price': ('Current Price', '当前价格'),
                    'position_52w': ('52W Position', '52周位置(%)'),
                    'bollinger_bandwidth': ('BB Bandwidth', '布林带带宽'),
                    'bollinger_b_percent': ('BB %B', '布林带%B'),
                    'volume_ratio': ('Volume Ratio', '量比'),
                    'trend_strength': ('Trend Strength', '趋势强度'),
                }
                
                # Extract all indicators across categories
                for cat_name, cat_data in cats.items():
                    indicators = cat_data.get('indicators', {})
                    for ind_name, ind_data in indicators.items():
                        # Find the primary value
                        value = None
                        field_key = ind_name # Default field name
                        
                        # Try to find specific value keys
                        for key in ['value', 'rsi', 'macd', 'adx', 'atr', 'roc', 'obv', 
                                    'current_price', 'position', 'bandwidth', 'volume_ratio', ind_name]:
                            if key in ind_data and key not in ['score', 'max_score', 'explanation']:
                                value = ind_data.get(key)
                                if value is not None:
                                    field_key = key # Found the specific data key
                                    break
                        
                        # Get names
                        en_name, cn_name = tech_map.get(ind_name, (ind_name.replace('_', ' ').title(), '-'))
                        if en_name == ind_name.replace('_', ' ').title():
                             # Try mapping the found key if the indicator name didn't match
                             en_name, cn_name = tech_map.get(field_key, (en_name, cn_name))

                        val_str = f"{value:.2f}" if isinstance(value, float) else str(value) if value else "N/A"
                        
                        lines.append(f"| {en_name} | {cn_name} | {val_str} | `{field_key}` |")
                lines.append("")

        # === Valuation Models ===
        if val_path:
            vd = self._load_json(val_path)
            if vd:
                lines.append("### 3. 估值模型 (Valuation Models)\n")
                lines.append("| English Name | 中文名称 | Fair Value (公允价) | Field ID (字段) |")
                lines.append("|---|---|---|---|")
                
                models = [
                    ('pe_valuation', 'PE Valuation', '市盈率估值'),
                    ('pb_valuation', 'PB Valuation', '市净率估值'),
                    ('ps_valuation', 'PS Valuation', '市销率估值'),
                    ('ev_ebitda', 'EV/EBITDA', '企业价值倍数'),
                    ('ddm', 'DDM Model', '股息折现模型'),
                    ('dcf', 'DCF Model', '自由现金流折现'),
                    ('graham', 'Graham Number', '格雷厄姆估值'),
                    ('peter_lynch', 'Peter Lynch Fair Value', '彼得林奇估值'),
                    ('analyst', 'Analyst Target', '分析师目标价'),
                ]
                
                for key, en_name, cn_name in models:
                    model = vd.get('models', {}).get(key, {})
                    fv = model.get('fair_value')
                    if fv is not None:
                        lines.append(f"| {en_name} | {cn_name} | ${fv:.2f} | `{key}` |")
                lines.append("")
        
        return "\n".join(lines)

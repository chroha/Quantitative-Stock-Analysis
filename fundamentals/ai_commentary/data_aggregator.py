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
        advanced_metrics = {}
        if raw_path:
            raw_data = self._load_json(raw_path)
            profile = raw_data.get('profile', {})
            
            # Helper to safely get value from field dict
            def get_val(key):
                obj = profile.get(key)
                if isinstance(obj, dict): return obj.get('value')
                return obj
            
            # Add advanced metrics
            analyst_targets = raw_data.get('analyst_targets', {})
            def get_target(key):
                obj = analyst_targets.get(key)
                if isinstance(obj, dict): return obj.get('value')
                return obj

            advanced_metrics = {
                "ownership": {
                    "insiders_pct": get_val('std_held_percent_insiders'),
                    "institutions_pct": get_val('std_held_percent_institutions')
                },
                "short_interest": {
                    "ratio": get_val('std_short_ratio'),
                    "float_pct": get_val('std_short_percent_of_float')
                },
                "valuation_extended": {
                    "enterprise_value": get_val('std_enterprise_value'),
                    "ev_to_ebitda": get_val('std_enterprise_to_ebitda')
                },
                "analyst_details": {
                    "rec_key": get_val('std_recommendation_key'),
                    "target_high": get_target('std_price_target_high'),
                    "target_low": get_target('std_price_target_low'),
                    "num_analysts": get_target('std_number_of_analysts')
                },
                "relative_strength": {
                    "stock_52w_change": get_val('std_52_week_change'),
                    "sp500_52w_change": get_val('std_sandp_52_week_change')
                },
                "liquidity_risk": {
                    "current_ratio": get_val('std_current_ratio'),
                    "quick_ratio": get_val('std_quick_ratio'),
                    "audit_risk": get_val('std_audit_risk'),
                    "board_risk": get_val('std_board_risk')
                },
                "per_share_extended": {
                    "cash_ps": get_val('std_total_cash_per_share'),
                    "rev_ps": get_val('std_revenue_per_share')
                }
            }

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
        aggregated_base = {
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
        
        # Add forecast_data if available
        if raw_path:
            raw_data_for_forecast = self._load_json(raw_path)
            forecast_data = raw_data_for_forecast.get('forecast_data', {})
            if forecast_data:
                aggregated_base["forecast"] = self._simplify_forecast(forecast_data, aggregated_base, raw_data_for_forecast)
        
        # Merge advanced metrics if they exist
        if advanced_metrics:
            aggregated_base["advanced_metrics"] = advanced_metrics
            
        aggregated = aggregated_base
        
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
                "up": m.get('upside_pct', 0),
                "mult": m.get('industry_multiple') # Extract industry multiple if available
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
    
    def _simplify_forecast(self, forecast_data: Dict, aggregated_base: Dict, raw_data: Dict) -> Dict:
        """Simplify forecast data for AI consumption."""
        def get_val(field):
            obj = forecast_data.get(field)
            if isinstance(obj, dict):
                return obj.get('value')
            return obj
        
        # Extract current values for comparison
        profile = raw_data.get('profile', {})
        
        def get_profile_val(field):
            obj = profile.get(field)
            if isinstance(obj, dict):
                return obj.get('value')
            return obj
        
        # Current P/E, EPS from profile
        current_pe = get_profile_val('std_pe_ratio')
        current_eps = get_profile_val('std_eps')
        
        # Historical growth rates from aggregated financial_score
        fin_score = aggregated_base.get('financial_score', {})
        growth = fin_score.get('growth', {})
        current_earnings_growth_5y = growth.get('ni_cagr', {}).get('val', 0) if growth.get('ni_cagr') else 0
        current_revenue_growth_5y = growth.get('rev_cagr', {}).get('val', 0) if growth.get('rev_cagr') else 0
        
        # Extract forward metrics
        fwd_eps = get_val('std_forward_eps')
        fwd_pe = get_val('std_forward_pe')
        earnings_growth_cy = get_val('std_earnings_growth_current_year')
        revenue_growth_ny = get_val('std_revenue_growth_next_year')
        
        # Extract price targets
        pt_low = get_val('std_price_target_low')
        pt_high = get_val('std_price_target_high')
        pt_consensus = get_val('std_price_target_consensus')
        
        # Process earnings surprises
        surprises = forecast_data.get('std_earnings_surprise_history', [])
        surprise_summary = None
        if surprises and isinstance(surprises, list):
            avg_surprise = sum(s.get('surprise_percent', 0) for s in surprises) / len(surprises) if surprises else 0
            positive_count = sum(1 for s in surprises if s.get('surprise_percent', 0) > 0)
            
            surprise_summary = {
                "avg_surprise_pct": avg_surprise,
                "positive_count": positive_count,
                "total_count": len(surprises),
                "latest_4": [
                    {
                        "period": s.get('period', 'N/A'),
                        "actual": s.get('actual', 0),
                        "estimate": s.get('estimate', 0),
                        "surprise_pct": s.get('surprise_percent', 0)
                    }
                    for s in surprises[:4]
                ]
            }
        
        return {
            # Current values
            "current_pe": current_pe,
            "current_eps": current_eps,
            "current_earnings_growth_5y": current_earnings_growth_5y,
            "current_revenue_growth_5y": current_revenue_growth_5y,
            # Forward values
            "forward_eps": fwd_eps,
            "forward_pe": fwd_pe,
            "earnings_growth_current_year": earnings_growth_cy,
            "revenue_growth_next_year": revenue_growth_ny,
            # Price targets
            "price_target_low": pt_low,
            "price_target_high": pt_high,
            "price_target_consensus": pt_consensus,
            # Surprises
            "surprises": surprise_summary
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
            # Unwrap dict if present (from new source tracking)
            if isinstance(val, dict) and 'value' in val:
                val = val['value']

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
        
        def merge_sources(sources):
            """Merge a list of sources into a unique, joined string."""
            if not sources: return "N/A"
            unique = sorted(list(set(s for s in sources if s and s != 'N/A')))
            if not unique: return "N/A"
            return "/".join(unique)

        def get_field_with_source(obj, field):
            """Extract both value and source."""
            if not obj: return None, 'N/A'
            f = obj.get(field)
            if isinstance(f, dict):
                val = f.get('value')
                src = f.get('source', 'N/A')
                # Capitalize source for consistency
                if src and src != 'N/A':
                    src = src.title()
                return val, src
            # If not a dict with source, return value and N/A
            return f, 'N/A'
            
        def extract_metric_source(metric_data, default_source="Calculated"):
            """Extract value and source from a metric (which might be a dict or float)."""
            if isinstance(metric_data, dict) and 'source' in metric_data:
                src = metric_data.get('source', default_source)
                if src and src != 'N/A':
                    src = src.title()
                return metric_data.get('value'), src
            return metric_data, default_source

        # === Financial Data Components (Source: Financial Data) ===
        if fin_data_path:
            fd = self._load_json(fin_data_path)
            if fd:
                metrics = fd.get('metrics', {})
                prof = metrics.get('profitability', {})
                growth = metrics.get('growth', {})
                cap = metrics.get('capital_allocation', {})
                
                lines.append("### 1. 财务计算组件 (Financial Calculation Components)\n")
                lines.append("| Component | 中文名称 | Value (数值) | Source | Logic (逻辑) |")
                lines.append("|---|---|---|---|---|")
                
                
                
                # Determine source (fallback)
                fin_source_fallback = "Calculated"
                if raw_path:
                    raw_d = self._load_json(raw_path)
                    stmts = raw_d.get('income_statements', [])
                    if stmts and len(stmts) > 0:
                        sample_field = stmts[0].get('std_revenue')
                        if isinstance(sample_field, dict) and 'source' in sample_field:
                            # Use this as base, but we prefer specific sources
                            pass 
                
                # ROIC Components
                nopat_val, nopat_src = extract_metric_source(prof.get('roic_nopat'), fin_source_fallback)
                ic_val, ic_src = extract_metric_source(prof.get('roic_invested_capital'), fin_source_fallback)
                tax_val, tax_src = extract_metric_source(prof.get('roic_effective_tax_rate'), fin_source_fallback)
                
                lines.append(f"| NOPAT | 税后营业利润 | {format_val(nopat_val, MetricFormat.CURRENCY_LARGE)} | {nopat_src} | `Operating Income * (1 - Tax Rate)` |")
                lines.append(f"| Invested Capital | 投入资本 | {format_val(ic_val, MetricFormat.CURRENCY_LARGE)} | {ic_src} | `Total Equity + Total Debt - Cash` |")
                lines.append(f"| Tax Rate | 有效税率 | {format_val(tax_val, MetricFormat.PERCENT)} | {tax_src} | `Income Tax / Pretax Income` |")

                # Margin Components (Revenue is already in Valuation section, but repeated here for completeness context)
                # We need raw income statement values which are in initial_data, but financial_data has computed margins.
                # Let's use the raw data loaded earlier if available.
                if raw_path:
                    raw_d = self._load_json(raw_path)
                    stmts = raw_d.get('income_statements', [])
                    if stmts:
                        curr = stmts[0]
                        gp_val, gp_src = get_field_with_source(curr, 'std_gross_profit')
                        op_inc_val, op_src = get_field_with_source(curr, 'std_operating_income')
                        lines.append(f"| Gross Profit | 毛利润 | {format_val(gp_val, MetricFormat.CURRENCY_LARGE)} | {gp_src} | `Revenue - Cost of Revenue` |")
                        lines.append(f"| Operating Income | 营业利润 | {format_val(op_inc_val, MetricFormat.CURRENCY_LARGE)} | {op_src} | `Gross Profit - OpEx` |")

                # Cash Flow Components
                fcf_data = growth.get('fcf_latest')
                # Try to construct better source for FCF if it says "Calculated"
                fcf_val, fcf_src = extract_metric_source(fcf_data, "Calculated")
                
                # Check for OCF and CapEx in raw data first to get their sources
                ocf_src_raw = "N/A"
                capex_src_raw = "N/A"
                
                if raw_path:
                    raw_d = self._load_json(raw_path)
                    cf_stmts = raw_d.get('cash_flow_statements', [])
                    if cf_stmts:
                        curr_cf = cf_stmts[0]
                        ocf_val, ocf_src_raw = get_field_with_source(curr_cf, 'std_cash_flow_operating')
                        capex_val, capex_src_raw = get_field_with_source(curr_cf, 'std_capex')
                        
                        # If FCF source is generic, improve it
                        if fcf_src == "Calculated":
                             fcf_src = merge_sources([ocf_src_raw, capex_src_raw])

                        lines.append(f"| FCF (Latest) | 自由现金流 | {format_val(fcf_val, MetricFormat.CURRENCY_LARGE)} | {fcf_src} | `OCF - CapEx` |")
                        lines.append(f"| Operating Cash Flow | 经营现金流 | {format_val(ocf_val, MetricFormat.CURRENCY_LARGE)} | {ocf_src_raw} | `From Cash Flow Statement` |")
                        lines.append(f"| Capital Expenditure | 资本支出 | {format_val(capex_val, MetricFormat.CURRENCY_LARGE)} | {capex_src_raw} | `From Cash Flow Statement` |")
                
                # SBC Impact & Dilution from capital allocation metrics (also calculated from CF/statement data)
                sbc_val, sbc_src = extract_metric_source(cap.get('sbc_impact_3y'), "Calculated")
                dilution_val, dilution_src = extract_metric_source(cap.get('share_dilution_cagr_5y'), "Calculated")
                
                lines.append(f"| SBC Impact | 股权激励 | {format_val(sbc_val, MetricFormat.PERCENT)} | {sbc_src} | `SBC / Revenue (3Y Avg)` |")
                lines.append(f"| Dilution Rate | 稀释率 | {format_val(dilution_val, MetricFormat.PERCENT)} | {dilution_src} | `Share Count CAGR` |")
                
                lines.append("")
        
        # === Technical Data Components (Source: Technical Score) ===
        if tech_score_path:
            td = self._load_json(tech_score_path)
            if td:
                score_data = td.get('score', {})
                cats = score_data.get('categories', {})
                data_info = score_data.get('data_info', {})
                
                # Determine source from price_history metadata
                price_data_source = "Calculated"  # Default fallback
                if raw_path:
                    raw_d = self._load_json(raw_path)
                    # Check if price_history has source info
                    ph = raw_d.get('price_history', [])
                    if ph and len(ph) > 0:
                        # Price history entries might have source field
                        first_entry = ph[0]
                        if isinstance(first_entry, dict) and 'source' in first_entry:
                            price_data_source = first_entry['source'].title()
                    # Also check root metadata
                    if price_data_source == "Calculated":
                        meta = raw_d.get('metadata', {})
                        if 'price_source' in meta:
                            price_data_source = meta['price_source'].title()
                        elif 'source' in meta and 'price' in str(meta.get('data_types', [])):
                            price_data_source = meta['source'].title()
                
                # Helper to find specific indicator values in categories
                def find_ind_val(ind_name, key='value'):
                    for cat in cats.values():
                        inds = cat.get('indicators', {})
                        if ind_name in inds:
                            return inds[ind_name].get(key)
                    return None
                
                
                lines.append("### 2. 技术指标组件 (Technical Indicator Components)\n")
                lines.append("| Component | 中文名称 | Value (数值) | Source | Context (参考) |")
                lines.append("|---|---|---|---|---|")
                
                
                # Market Data (Raw inputs for Position, Volume Ratio)
                latest_price = data_info.get('latest_price')
                high_52w = data_info.get('high_52w')
                low_52w = data_info.get('low_52w')
                
                lines.append(f"| Latest Price | 最新价格 | {format_val(latest_price, MetricFormat.CURRENCY)} | {price_data_source} | `Close Price` |")
                lines.append(f"| 52-Week High | 52周最高 | {format_val(high_52w, MetricFormat.CURRENCY)} | {price_data_source} | `Highest Price (1Y)` |")
                lines.append(f"| 52-Week Low | 52周最低 | {format_val(low_52w, MetricFormat.CURRENCY)} | {price_data_source} | `Lowest Price (1Y)` |")
                
                latest_vol = data_info.get('latest_volume')
                avg_vol = data_info.get('avg_volume')
                lines.append(f"| Latest Volume | 最新成交量 | {format_val(latest_vol, MetricFormat.DECIMAL)} | {price_data_source} | `Daily Volume` |")
                lines.append(f"| Avg Volume | 平均成交量 | {format_val(avg_vol, MetricFormat.DECIMAL)} | {price_data_source} | `20-Day Average` |")
                
                # Moving Averages (Trend inputs)
                sma_20 = find_ind_val('multi_ma', 'ma20')
                if sma_20:
                    lines.append(f"| SMA 20 | 20日均线 | {format_val(sma_20, MetricFormat.CURRENCY)} | {price_data_source} | `Short Trend` |")
                
                sma_50 = find_ind_val('multi_ma', 'ma50')
                if sma_50:
                    lines.append(f"| SMA 50 | 50日均线 | {format_val(sma_50, MetricFormat.CURRENCY)} | {price_data_source} | `Medium Trend` |")
                
                sma_200 = find_ind_val('multi_ma', 'ma200')
                if sma_200:
                    lines.append(f"| SMA 200 | 200日均线 | {format_val(sma_200, MetricFormat.CURRENCY)} | {price_data_source} | `Long Trend` |")
                
                # Volatility Components (Raw Bollinger Bands instead of Bandwidth)
                bb_upper = find_ind_val('bollinger', 'upper')
                bb_lower = find_ind_val('bollinger', 'lower')
                bb_middle = find_ind_val('bollinger', 'middle')
                
                if bb_upper:
                    lines.append(f"| BB Upper | 布林上轨 | {format_val(bb_upper, MetricFormat.CURRENCY)} | {price_data_source} | `20D SMA + 2*StdDev` |")
                if bb_middle:
                     lines.append(f"| BB Middle | 布林中轨 | {format_val(bb_middle, MetricFormat.CURRENCY)} | {price_data_source} | `20D SMA` |")
                if bb_lower:
                    lines.append(f"| BB Lower | 布林下轨 | {format_val(bb_lower, MetricFormat.CURRENCY)} | {price_data_source} | `20D SMA - 2*StdDev` |")
                
                # Momentum Raw Values
                rsi = find_ind_val('rsi', 'rsi')
                lines.append(f"| RSI (14) | 相对强弱指数 | {format_val(rsi, MetricFormat.DECIMAL)} | {price_data_source} | `Momentum (0-100)` |")
                
                roc = find_ind_val('roc', 'roc')
                if roc is not None:
                    lines.append(f"| ROC (20) | 变动率 | {format_val(roc, MetricFormat.PERCENT)} | {price_data_source} | `Price Rate of Change` |")
                
                macd_line = find_ind_val('macd', 'macd')
                signal_line = find_ind_val('macd', 'signal_line')
                macd_hist = find_ind_val('macd', 'histogram')
                
                if macd_line:
                    lines.append(f"| MACD Line | MACD线 | {format_val(macd_line, MetricFormat.DECIMAL)} | {price_data_source} | `12EMA - 26EMA` |")
                if signal_line:
                    lines.append(f"| Signal Line | 信号线 | {format_val(signal_line, MetricFormat.DECIMAL)} | {price_data_source} | `9EMA of MACD` |")
                if macd_hist:
                    lines.append(f"| MACD Hist | MACD柱 | {format_val(macd_hist, MetricFormat.DECIMAL)} | {price_data_source} | `MACD - Signal` |")
                
                # Trend Strength (ADX)
                adx = find_ind_val('adx', 'adx')
                if adx:
                    lines.append(f"| ADX | 趋势强度 | {format_val(adx, MetricFormat.DECIMAL)} | {price_data_source} | `>25=Strong Trend` |")
                
                # Structure
                supp = find_ind_val('support_resistance', 'nearest_support')
                res = find_ind_val('support_resistance', 'nearest_resistance')
                if supp:
                    lines.append(f"| Support | 最近支撑 | {format_val(supp, MetricFormat.CURRENCY)} | {price_data_source} | `Nearest Support Level` |")
                if res:
                    lines.append(f"| Resistance | 最近阻力 | {format_val(res, MetricFormat.CURRENCY)} | {price_data_source} | `Nearest Resistance Level` |")
                    
                hl_pattern = find_ind_val('high_low_structure', 'pattern')
                if hl_pattern:
                    lines.append(f"| Structure | 市场结构 | {format_val(hl_pattern, MetricFormat.STRING)} | {price_data_source} | `High/Low Pattern` |")

                # Volume Analysis
                obv = find_ind_val('obv', 'obv')
                if obv:
                    # OBV is cumulative, formatting as large currency just to get B/M suffix but no currency sign logic?
                    # format_val uses currency logic if fmt=CURRENCY. We can use DECIMAL or just force string.
                    # Let's use DECIMAL for now, or add a CUSTOM handling if easy.
                    lines.append(f"| OBV | 能量潮 | {format_val(obv, MetricFormat.DECIMAL)} | {price_data_source} | `On-Balance Volume` |")
                    
                vol_ratio = find_ind_val('volume_strength', 'volume_ratio')
                if vol_ratio:
                    lines.append(f"| Vol Ratio | 量比 | {format_val(vol_ratio, MetricFormat.DECIMAL)} | {price_data_source} | `Vol / AvgVol` |")

                # Volatility (ATR)
                atr = find_ind_val('atr', 'atr') # Raw value
                atr_pct = find_ind_val('atr', 'atr_pct') # Percentage
                if atr_pct:
                    lines.append(f"| ATR % | 波动率百分比 | {format_val(atr_pct, MetricFormat.PERCENT)} | {price_data_source} | `ATR / Price` |")
                
                lines.append("")

        # === Valuation Input Data (Source: Initial Data + Financial Data) ===
        # Path finding moved to top of function
        
        if raw_path or fin_data_path:
            lines.append("### 3. 估值基础数据 (Valuation Input Data)\n")
            lines.append("| English Name | 中文名称 | Value (数值) | Source | Field Name (字段) |")
            lines.append("|---|---|---|---|---|")
            
            # Load data sources
            raw_data = self._load_json(raw_path) if raw_path else {}
            fin_metrics_data = self._load_json(fin_data_path) if fin_data_path else {}
            fin_metrics = fin_metrics_data.get('metrics', {})
            
            # Extract profile and latest statement data
            profile = raw_data.get('profile', {})
            income_stmts = raw_data.get('income_statements', [])
            balance_stmts = raw_data.get('balance_sheets', [])
            cf_stmts = raw_data.get('cash_flows', [])
            
            # Helper to get field value and source
            def get_field_val(obj, field):
                """Extract value only (backward compatible)."""
                if not obj: return None
                f = obj.get(field)
                if isinstance(f, dict) and 'value' in f:
                     return f.get('value')
                return f
            
            def get_field_with_source(obj, field):
                """Extract both value and source."""
                if not obj: return None, 'N/A'
                f = obj.get(field)
                if isinstance(f, dict):
                    val = f.get('value')
                    src = f.get('source', 'N/A')
                    return val, src.title() if src != 'N/A' else 'N/A'
                return f, 'N/A'
            
            # 1. Growth Metrics (CAGR - Calculated, no source)
            # Try to resolve sources if possible
            rev_cagr_val = fin_metrics.get('growth', {}).get('revenue_cagr_5y')
            ni_cagr_val = fin_metrics.get('growth', {}).get('net_income_cagr_5y')
            fcf_cagr_val = fin_metrics.get('growth', {}).get('fcf_cagr_5y')

            def get_cagr_src(metric_name):
                 # We don't have easy access to the exact source list used for CAGR here without deeper digging
                 # But we can check if the value object itself has a source now (since we updated GrowthMetrics)
                 obj = fin_metrics.get('growth', {}).get(metric_name)
                 if isinstance(obj, dict) and 'source' in obj:
                     return obj['source']
                 return "Calculated"

            lines.append(f"| Revenue CAGR (5Y) | 营收增速 | {format_val(rev_cagr_val, MetricFormat.PERCENT)} | {get_cagr_src('revenue_cagr_5y')} | `revenue_cagr_5y` |")
            lines.append(f"| Net Income CAGR (5Y) | 净利增速 | {format_val(ni_cagr_val, MetricFormat.PERCENT)} | {get_cagr_src('net_income_cagr_5y')} | `net_income_cagr_5y` |")
            lines.append(f"| FCF CAGR (5Y) | FCF增速 | {format_val(fcf_cagr_val, MetricFormat.PERCENT)} | {get_cagr_src('fcf_cagr_5y')} | `fcf_cagr_5y` |")
            
            # 2. Latest Financials (Verification Data)
            if income_stmts:
                latest_is = income_stmts[0]
                ni_val, ni_src = get_field_with_source(latest_is, 'std_net_income')
                rev_val, rev_src = get_field_with_source(latest_is, 'std_revenue')
                ebitda_val, ebitda_src = get_field_with_source(latest_is, 'std_ebitda')
                lines.append(f"| Net Income (Latest) | 最新净利润 | {format_val(ni_val, MetricFormat.CURRENCY_LARGE)} | {ni_src} | `std_net_income` |")
                lines.append(f"| Revenue (Latest) | 最新营收 | {format_val(rev_val, MetricFormat.CURRENCY_LARGE)} | {rev_src} | `std_revenue` |")
                lines.append(f"| EBITDA | EBITDA | {format_val(ebitda_val, MetricFormat.CURRENCY_LARGE)} | {ebitda_src} | `std_ebitda` |")

            if cf_stmts:
                latest_cf = cf_stmts[0]
                # FCF Calculation Components
                ocf_val, ocf_src = get_field_with_source(latest_cf, 'std_operating_cash_flow')
                capex_val, capex_src = get_field_with_source(latest_cf, 'std_capex')
                fcf_val, fcf_src = get_field_with_source(latest_cf, 'std_free_cash_flow')
                sbc_val, sbc_src = get_field_with_source(latest_cf, 'std_stock_based_compensation')
                sr_val, sr_src = get_field_with_source(latest_cf, 'std_repurchase_of_stock')
                
                # If FCF missing, calculate
                if fcf_val is None and ocf_val is not None and capex_val is not None:
                    fcf_val = ocf_val + capex_val # Capex is usually negative
                    fcf_src = "Calculated"
                    
                lines.append(f"| Operating Cash Flow | 经营现金流 | {format_val(ocf_val, MetricFormat.CURRENCY_LARGE)} | {ocf_src} | `std_operating_cash_flow` |")
                lines.append(f"| Capital Expenditure | 资本支出 | {format_val(capex_val, MetricFormat.CURRENCY_LARGE)} | {capex_src} | `std_capex` |")
                lines.append(f"| Free Cash Flow | 自由现金流 | {format_val(fcf_val, MetricFormat.CURRENCY_LARGE)} | {fcf_src} | `OCF - CapEx` |")
                
                lines.append(f"| Stock Based Comp | 股权激励金额 | {format_val(sbc_val, MetricFormat.CURRENCY_LARGE)} | {sbc_src} | `std_stock_based_compensation` |")
                lines.append(f"| Stock Repurchase | 股票回购金额 | {format_val(sr_val, MetricFormat.CURRENCY_LARGE)} | {sr_src} | `std_repurchase_of_stock` |")
            
            if balance_stmts:
                latest_bs = balance_stmts[0]
                debt_val, debt_src = get_field_with_source(latest_bs, 'std_total_debt')
                cash_val, cash_src = get_field_with_source(latest_bs, 'std_cash')
                cash_val2, cash_src2 = get_field_with_source(latest_bs, 'std_cash_and_equivalents')
                if not cash_val:
                    cash_val, cash_src = cash_val2, cash_src2
                equity_val, equity_src = get_field_with_source(latest_bs, 'std_shareholder_equity')
                
                lines.append(f"| Total Debt | 总债务 | {format_val(debt_val, MetricFormat.CURRENCY_LARGE)} | {debt_src} | `std_total_debt` |")
                lines.append(f"| Cash & Equiv | 现金及等价物 | {format_val(cash_val, MetricFormat.CURRENCY_LARGE)} | {cash_src} | `std_cash` |")
                lines.append(f"| Shareholder Equity | 股东权益 | {format_val(equity_val, MetricFormat.CURRENCY_LARGE)} | {equity_src} | `std_shareholder_equity` |")
            
            # 3. Quality & Allocation Ratios (Calculated)
            # Access nested metrics correctly
            metrics_growth = fin_metrics.get('growth', {})
            metrics_cap = fin_metrics.get('capital_allocation', {})
            metrics_prof = fin_metrics.get('profitability', {})
            
            lines.append(f"| Earnings Quality | 盈利质量 | {format_val(metrics_growth.get('earnings_quality_3y') or metrics_prof.get('earnings_quality'), MetricFormat.DECIMAL)} | Calculated | `OCF / Net Income` |")
            lines.append(f"| CapEx Intensity | 资本开支占比 | {format_val(metrics_cap.get('capex_intensity_3y'), MetricFormat.PERCENT)} | Calculated | `CapEx / OCF (Avg 3Y)` |")
            lines.append(f"| SBC Impact | SBC营收占比 | {format_val(metrics_cap.get('sbc_impact_3y'), MetricFormat.PERCENT)} | Calculated | `SBC / Revenue (Avg 3Y)` |")

            # Market data from profile
            mc_val, mc_src = get_field_with_source(profile, 'std_market_cap')
            lines.append(f"| Market Cap | 市值 | {format_val(mc_val, MetricFormat.CURRENCY_LARGE)} | {mc_src} | `profile.std_market_cap` |")
            
            # Price ratios
            pe_val, pe_src = get_field_with_source(profile, 'std_pe_ratio')
            pb_val, pb_src = get_field_with_source(profile, 'std_pb_ratio')
            ps_val, ps_src = get_field_with_source(profile, 'std_ps_ratio')
            peg_val, peg_src = get_field_with_source(profile, 'std_peg_ratio')
            div_val, div_src = get_field_with_source(profile, 'std_dividend_yield')
            
            lines.append(f"| P/E Ratio | 市盈率 | {format_val(pe_val, MetricFormat.DECIMAL)} | {pe_src} | `profile.std_pe_ratio` |")
            lines.append(f"| P/B Ratio | 市净率 | {format_val(pb_val, MetricFormat.DECIMAL)} | {pb_src} | `profile.std_pb_ratio` |")
            lines.append(f"| P/S Ratio | 市销率 | {format_val(ps_val, MetricFormat.DECIMAL)} | {ps_src} | `profile.std_ps_ratio` |")
            lines.append(f"| PEG Ratio | PEG比率 | {format_val(peg_val, MetricFormat.DECIMAL)} | {peg_src} | `profile.std_peg_ratio` |")
            lines.append(f"| Dividend Yield | 股息率 | {format_val(div_val, MetricFormat.PERCENT)} | {div_src} | `profile.std_dividend_yield` |")

            # EPS
            eps_val, eps_src = get_field_with_source(profile, 'std_eps')
            fwd_eps_val, fwd_eps_src = get_field_with_source(profile, 'std_forward_eps')
            bv_val, bv_src = get_field_with_source(profile, 'std_book_value_per_share')
            eg_val, eg_src = get_field_with_source(profile, 'std_earnings_growth')
            
            lines.append(f"| EPS (TTM) | 每股收益 | {format_val(eps_val, MetricFormat.CURRENCY)} | {eps_src} | `profile.std_eps` |")
            lines.append(f"| Forward EPS | 前瞻每股收益 | {format_val(fwd_eps_val, MetricFormat.CURRENCY)} | {fwd_eps_src} | `profile.std_forward_eps` |")
            lines.append(f"| Book Value/Share | 每股账面价值 | {format_val(bv_val, MetricFormat.CURRENCY)} | {bv_src} | `std_book_value_per_share` |")
            lines.append(f"| Earnings Growth | 盈利增长率 | {format_val(eg_val, MetricFormat.PERCENT)} | {eg_src} | `profile.std_earnings_growth` |")
            
            # === NEW: Forward Estimates from forecast_data ===
            lines.append("")
            lines.append("#### 前瞻预测数据 (Forward Estimates)")
            lines.append("")
            lines.append("\u003e 注:以下数据来自forecast_data,已通过智能合并(Yahoo→FMP→Finnhub)。部分字段可能与profile中的值不同。")
            lines.append("")
            lines.append("| Category | English Name | 中文名称 | Value | Source | Field |")
            lines.append("|---|---|---|---|---|---|")
            
            # Load forecast_data
            forecast_data = raw_data.get('forecast_data') or {}
            
            def get_forecast_val(field):
                """Extract value and source from forecast_data field."""
                obj = forecast_data.get(field)
                if isinstance(obj, dict):
                    val = obj.get('value')
                    src = obj.get('source', 'N/A')
                    return val, src.title() if src != 'N/A' else 'N/A'
                return None, 'N/A'
            
            # Estimates Section
            fwd_eps, fwd_eps_src = get_forecast_val('std_forward_eps')
            fwd_pe, fwd_pe_src = get_forecast_val('std_forward_pe')
            eg_cy, eg_cy_src = get_forecast_val('std_earnings_growth_current_year')
            rg_ny, rg_ny_src = get_forecast_val('std_revenue_growth_next_year')
            
            lines.append(f"| **Estimates** | Forward EPS | 前瞻每股收益 | {format_val(fwd_eps, MetricFormat.CURRENCY)} | {fwd_eps_src} | `forecast_data.std_forward_eps` |")
            lines.append(f"| | Forward P/E | 前瞻市盈率 | {format_val(fwd_pe, MetricFormat.DECIMAL)} | {fwd_pe_src} | `forecast_data.std_forward_pe` |")
            lines.append(f"| | Earnings Growth (CY) | 本年盈利增长 | {format_val(eg_cy, MetricFormat.PERCENT)} | {eg_cy_src} | `forecast_data.std_earnings_growth_current_year` |")
            lines.append(f"| | Revenue Growth (NY) | 明年营收增长 | {format_val(rg_ny, MetricFormat.PERCENT)} | {rg_ny_src} | `forecast_data.std_revenue_growth_next_year` |")
            
            # Price Targets Section
            pt_low, pt_low_src = get_forecast_val('std_price_target_low')
            pt_high, pt_high_src = get_forecast_val('std_price_target_high')
            pt_cons, pt_cons_src = get_forecast_val('std_price_target_consensus')
            
            lines.append(f"| **Price Targets** | Analyst Low | 分析师最低价 | {format_val(pt_low, MetricFormat.CURRENCY)} | {pt_low_src} | `forecast_data.std_price_target_low` |")
            lines.append(f"| | Analyst High | 分析师最高价 | {format_val(pt_high, MetricFormat.CURRENCY)} | {pt_high_src} | `forecast_data.std_price_target_high` |")
            lines.append(f"| | Analyst Consensus | 分析师共识价 | {format_val(pt_cons, MetricFormat.CURRENCY)} | {pt_cons_src} | `forecast_data.std_price_target_consensus` |")
            
            # Earnings Surprises Section
            surprises = forecast_data.get('std_earnings_surprise_history', [])
            if surprises and isinstance(surprises, list):
                lines.append(f"| **Surprises** | Earnings Surprises | 盈利意外 | {len(surprises)} records | Finnhub | `forecast_data.std_earnings_surprise_history` |")
                
                # Detailed Surprise Table
                lines.append("")
                lines.append("##### Earnings Surprise详细记录 (Latest 4 Quarters)")
                lines.append("")
                lines.append("| Period | Actual EPS | Estimate EPS | Surprise | Surprise % |")
                lines.append("|--------|-----------|-------------|----------|-----------|")
                
                for s in surprises[:4]:  # Latest 4 quarters
                    period = s.get('period', 'N/A')
                    actual = s.get('actual', 0)
                    estimate = s.get('estimate', 0)
                    surprise = actual - estimate if (actual and estimate) else 0
                    surprise_pct = s.get('surprise_percent', 0)
                    sign = "+" if surprise >= 0 else ""
                    lines.append(f"| {period} | ${actual:.2f} | ${estimate:.2f} | {sign}${surprise:.2f} | {sign}{surprise_pct:.2f}% |")
                
                lines.append("")
            
            # === End of forecast_data section ===
            
            # === Supplemental Data ===
            
            # Fetch analyst targets for display
            analyst_targets = {}
            if raw_path:
                raw_d = self._load_json(raw_path)
                analyst_targets = raw_d.get('analyst_targets', {})

            def get_target(key):
                obj = analyst_targets.get(key)
                if isinstance(obj, dict): return obj.get('value')
                return obj

            lines.append("")
            lines.append("### 4. 补充数据 (Supplemental Data)\n")
            lines.append("| Category | English Name | 中文名称 | Value (数值) | Source | Logic (逻辑) |")
            lines.append("|---|---|---|---|---|---|")
            
            
            # Group 1: Analyst Consensus
            rec_key_val, rec_key_src = get_field_with_source(profile, 'std_recommendation_key')
            target_high_val, target_high_src = get_field_with_source(analyst_targets, 'std_price_target_high')
            target_low_val, target_low_src = get_field_with_source(analyst_targets, 'std_price_target_low')
            num_analysts_val, num_analysts_src = get_field_with_source(analyst_targets, 'std_number_of_analysts')
            
            lines.append(f"| **Analyst** | Recommendation | 评级建议 | {format_val(rec_key_val, MetricFormat.STRING)} | {rec_key_src} | Analyst Recommendation |")
            lines.append(f"| | Target High | 目标价上限 | {format_val(target_high_val, MetricFormat.CURRENCY)} | {target_high_src} | Highest Price Target |")
            lines.append(f"| | Target Low | 目标价下限 | {format_val(target_low_val, MetricFormat.CURRENCY)} | {target_low_src} | Lowest Price Target |")
            lines.append(f"| | Num Analysts | 分析师数量 | {format_val(num_analysts_val, MetricFormat.DECIMAL)} | {num_analysts_src} | Number of Analysts |")

            # Group 2: Relative Strength & Risk
            change_52w_val, change_52w_src = get_field_with_source(profile, 'std_52_week_change')
            sp_change_val, sp_change_src = get_field_with_source(profile, 'std_sandp_52_week_change')
            audit_risk_val, audit_risk_src = get_field_with_source(profile, 'std_audit_risk')
            board_risk_val, board_risk_src = get_field_with_source(profile, 'std_board_risk')
            
            lines.append(f"| **Risk/Trend** | 52W Change | 年涨跌幅 | {format_val(change_52w_val, MetricFormat.PERCENT)} | {change_52w_src} | 52-Week Price Change |")
            lines.append(f"| | vs S&P 500 | 标普同期 | {format_val(sp_change_val, MetricFormat.PERCENT)} | {sp_change_src} | S&P 500 Performance |")
            lines.append(f"| | Audit Risk | 审计风险 | {format_val(audit_risk_val, MetricFormat.DECIMAL)} | {audit_risk_src} | Audit Risk Score |")
            lines.append(f"| | Board Risk | 董事会风险 | {format_val(board_risk_val, MetricFormat.DECIMAL)} | {board_risk_src} | Board Risk Score |")

            # Group 3: Liquidity & Per Share
            current_ratio_val, current_ratio_src = get_field_with_source(profile, 'std_current_ratio')
            quick_ratio_val, quick_ratio_src = get_field_with_source(profile, 'std_quick_ratio')
            cash_per_share_val, cash_per_share_src = get_field_with_source(profile, 'std_total_cash_per_share')
            rev_per_share_val, rev_per_share_src = get_field_with_source(profile, 'std_revenue_per_share')
            
            lines.append(f"| **Liquidity** | Current Ratio | 流动比率 | {format_val(current_ratio_val, MetricFormat.DECIMAL)} | {current_ratio_src} | Current Assets / Current Liabilities |")
            lines.append(f"| | Quick Ratio | 速动比率 | {format_val(quick_ratio_val, MetricFormat.DECIMAL)} | {quick_ratio_src} | Quick Assets / Current Liabilities |")
            lines.append(f"| | Cash/Share | 每股现金 | {format_val(cash_per_share_val, MetricFormat.CURRENCY)} | {cash_per_share_src} | Cash Per Share |")
            lines.append(f"| | Rev/Share | 每股营收 | {format_val(rev_per_share_val, MetricFormat.CURRENCY)} | {rev_per_share_src} | Revenue Per Share |")

            # Group 4: Ownership & Sentiment
            insiders_held_val, insiders_held_src = get_field_with_source(profile, 'std_held_percent_insiders')
            institutions_val, institutions_src = get_field_with_source(profile, 'std_held_percent_institutions')
            short_ratio_val, short_ratio_src = get_field_with_source(profile, 'std_short_ratio')
            short_pct_val, short_pct_src = get_field_with_source(profile, 'std_short_percent_of_float')
            ent_value_val, ent_value_src = get_field_with_source(profile, 'std_enterprise_value')
            ev_ebitda_val, ev_ebitda_src = get_field_with_source(profile, 'std_enterprise_to_ebitda')
            
            lines.append(f"| **Sentiment** | Insiders Held | 内部持股 | {format_val(insiders_held_val, MetricFormat.PERCENT)} | {insiders_held_src} | Insider Ownership % |")
            lines.append(f"| | Institutions | 机构持股 | {format_val(institutions_val, MetricFormat.PERCENT)} | {institutions_src} | Institutional Ownership % |")
            lines.append(f"| | Short Ratio | 做空比率 | {format_val(short_ratio_val, MetricFormat.DECIMAL)} | {short_ratio_src} | Days to Cover Short |")
            lines.append(f"| | Short % Float | 做空流通比 | {format_val(short_pct_val, MetricFormat.PERCENT)} | {short_pct_src} | Short % of Float |")
            lines.append(f"| | Ent Value | 企业价值 | {format_val(ent_value_val, MetricFormat.CURRENCY_LARGE)} | {ent_value_src} | Enterprise Value |")
            lines.append(f"| | EV/EBITDA | EV/EBITDA | {format_val(ev_ebitda_val, MetricFormat.DECIMAL)} | {ev_ebitda_src} | EV / EBITDA Ratio |")

        lines.append("")
        return "\n".join(lines)

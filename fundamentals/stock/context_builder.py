"""
Context Builder Module
======================

Responsible for transforming raw data bundles into simplified, AI-ready contexts.
Handles formatting, field extraction, and appendix generation.
"""

from typing import Dict, Any, List, Optional
from utils.metric_registry import (
    FINANCIAL_METRICS, TECHNICAL_INDICATORS, VALUATION_MODELS, MetricFormat
)
from utils.helpers import format_large_number

class ContextBuilder:
    """Builds AI context from aggregated data bundle."""
    
    def build_context(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw data bundle into simplified context.
        """
        symbol = bundle['symbol']
        data = bundle['data']
        
        fin_score = data['financial_score']
        tech_score = data['technical_score']
        val_data = data['valuation']
        raw_data = data['initial_data']
        
        # 1. Stock Info
        stock_info = self._build_stock_info(symbol, bundle)
        
        # 2. Simplified Sections
        context = {
            "stock_info": stock_info,
            "financial_score": self._simplify_financial(fin_score.get('score', {})),
            "technical_score": self._simplify_technical(tech_score.get('score', {})),
            "valuation": self._simplify_valuation(val_data)
        }
        
        # 3. Forecast Data
        forecast = raw_data.get('forecast_data', {})
        if forecast:
            context["forecast"] = self._simplify_forecast(forecast, context, raw_data)
            
        # 4. Advanced Metrics
        adv_metrics = self._extract_advanced_metrics(raw_data)
        if adv_metrics:
            context["advanced_metrics"] = adv_metrics
            
        # 5. Market Intelligence (News/Sentiment)
        mkt_intel = self._extract_market_intelligence(raw_data)
        if mkt_intel:
            context["market_intelligence"] = mkt_intel
            
        # Cross-fill gaps
        if context['stock_info']['sector'] == 'Unknown':
             context['stock_info']['sector'] = val_data.get('sector', 'Unknown')
        if context['stock_info']['price'] == 0:
            context['stock_info']['price'] = val_data.get('current_price', 0)
            
        return context

    def _build_stock_info(self, symbol: str, bundle: Dict) -> Dict:
        data = bundle['data']
        raw_data = data['initial_data']
        fin_data = data['financial_score']
        tech_data = data['technical_score']
        
        # History Years Calculation
        history_years = 0
        latest_period = "Unknown"
        
        stmts = raw_data.get('income_statements', [])
        if stmts:
            latest_period = stmts[0].get('std_period', 'Unknown')
            history_years = sum(1 for s in stmts if s.get('std_period_type', 'FY') in ['FY', 'TTM'])
            
        return {
            "symbol": symbol,
            "sector": fin_data.get('metadata', {}).get('sector', 'Unknown'),
            "price": tech_data.get('score', {}).get('data_info', {}).get('current_price', 0),
            "date": bundle['metadata']['date'],
            "latest_period": latest_period,
            "history_years": history_years
        }

    def _simplify_financial(self, score_data: Dict) -> Dict:
        """Simplify financial score data."""
        cats = score_data.get('category_scores', {})
        
        def get_metric(metric_name):
            for cat_val in cats.values():
                metrics = cat_val.get('metrics', {})
                if metric_name in metrics:
                    m = metrics[metric_name]
                    raw_val = m.get('value', 0)

                    # Cap earnings_quality display: OCF/NI can diverge wildly when NI → 0.
                    # Values beyond ±10 (i.e. >1000%) convey no useful signal to the LLM
                    # and can trigger hallucinated commentary. Replace with None (→ "N/A").
                    # This does NOT affect the score, which is computed upstream and stored
                    # separately in 'weighted_score'.
                    if metric_name == 'earnings_quality_3y' and isinstance(raw_val, (int, float)):
                        if abs(raw_val) > 10:
                            raw_val = None  # render as N/A in report

                    return {
                        "val": raw_val,
                        "score": m.get('weighted_score', 0),
                        "max": m.get('weight', 0),
                        "rank": m.get('interpretation', 'N/A').split('(')[-1].strip(')')
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
                "rev_cagr": get_metric('revenue_cagr_5y'),
                "ni_cagr": get_metric('net_income_cagr_5y'),
                "fcf_cagr": get_metric('fcf_cagr_5y'),
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
        cats = score_data.get('categories', {})
        
        def fmt(cat_key, ind_key):
             if cat_key not in cats: return {"val": 0, "score": 0, "max": 0, "signal": "N/A"}
             d = cats[cat_key].get('indicators', {}).get(ind_key, {})
             
             # Extract simple value
             val = 0
             for k in ['value', 'current_price', 'adx', 'rsi', 'roc', 'atr_pct', 'position', 'bandwidth']:
                 if k in d:
                     val = d[k]
                     break
                     
             return {
                 "val": val, 
                 "score": d.get('score', 0), 
                 "max": d.get('max_score', 0),
                 "signal": d.get('explanation', 'N/A')
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
        methods = val_data.get('method_results', {})
        
        def fmt(key):
            m = methods.get(key, {})
            return {
                "fair": m.get('fair_value', 0),
                "wt": int(m.get('weight', 0) * 100),
                "up": m.get('upside_pct', 0),
                "mult": m.get('industry_multiple')
            }
            
        return {
            "fair": val_data.get('weighted_fair_value', 0),
            "current": val_data.get('current_price', 0),
            "upside": val_data.get('price_difference_pct', 0),
            "pe": fmt('pe'),
            "ps": fmt('ps'),
            "pb": fmt('pb'),
            "ev_ebitda": fmt('ev_ebitda'),
            "ev_sales": fmt('ev_sales'),
            "peg": fmt('peg'),
            "ddm": fmt('ddm'),
            "analyst": fmt('analyst'),
            "dcf": fmt('dcf'),
            "graham": fmt('graham'),
            "lynch": fmt('peter_lynch')
        }

    def _extract_advanced_metrics(self, raw_data: Dict) -> Dict:
        profile = raw_data.get('profile', {})
        def get_val(key):
            obj = profile.get(key)
            if isinstance(obj, dict): return obj.get('value')
            return obj
            
        forecast_data = raw_data.get('forecast_data', {})
        def get_target(key):
            obj = forecast_data.get(key)
            if isinstance(obj, dict): return obj.get('value')
            return obj

        # Format enterprise value to human-readable B/M/T to prevent AI from
        # displaying a raw integer (e.g. 47330594816 instead of "$47.33B").
        # Reuses utils.helpers.format_large_number to avoid duplicating unit logic.
        raw_ev = get_val('std_enterprise_value')
        if isinstance(raw_ev, (int, float)) and raw_ev is not None:
            formatted_ev = f"${format_large_number(raw_ev)}"
        else:
            formatted_ev = raw_ev

        return {
            "ownership": {
                "insiders_pct": get_val('std_held_percent_insiders'),
                "institutions_pct": get_val('std_held_percent_institutions')
            },
            "short_interest": {
                "ratio": get_val('std_short_ratio'),
                "float_pct": get_val('std_short_percent_of_float')
            },
            "valuation_extended": {
                "enterprise_value": formatted_ev,
                "ev_to_ebitda": get_val('std_enterprise_to_ebitda')
            },
            "analyst_details": {
                "rec_key": get_val('std_recommendation_key') or "N/A",
                "target_high": get_target('std_price_target_high') or "N/A",
                "target_low": get_target('std_price_target_low') or "N/A",
                "num_analysts": get_target('std_number_of_analysts') or "N/A"
            },
            "relative_strength": {
                "stock_52w_change": get_val('std_52_week_change'),
                # Renamed from 'sp500_52w_change' to 'alpha_vs_sp500' to prevent the LLM
                # from interpreting this field as "what the S&P 500 returned" rather than
                # "how much this stock outperformed/underperformed the market".
                # Value = stock_52W_change - sp500_52W_change (computed below).
                "alpha_vs_sp500": (
                    (get_val('std_52_week_change') - get_val('std_sandp_52_week_change'))
                    if (isinstance(get_val('std_52_week_change'), (int, float))
                        and isinstance(get_val('std_sandp_52_week_change'), (int, float)))
                    else get_val('std_sandp_52_week_change')  # fallback if either is missing
                )
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

    def _extract_market_intelligence(self, raw_data: Dict) -> Dict:
        """
        Extract News, Sentiment, and Peers.
        """
        news = raw_data.get('news', [])
        sentiment = raw_data.get('sentiment', {})
        peers = raw_data.get('peers', [])
        
        # 1. News (Top 5 recent)
        top_news = []
        if news:
            # Sort by datetime desc if not already
            sorted_news = sorted(news, key=lambda x: x.get('datetime', 0), reverse=True)
            for n in sorted_news[:5]:
                top_news.append({
                    "headline": n.get('headline'),
                    "summary": n.get('summary'),
                    "source": n.get('source'),
                    "url": n.get('url'),
                    "date": n.get('datetime')
                })
                
        # 2. Sentiment
        insider_sent = []
        if sentiment:
            # Sentiment might be a dict or object. accessing as dict here since raw_data is dict
            sent_list = sentiment.get('insider_sentiment', [])
            for s in sent_list:
                insider_sent.append({
                    "month": s.get('month'),
                    "year": s.get('year'),
                    "change": s.get('change'),
                    "mspr": s.get('mspr')
                })
        
        return {
            "news": top_news,
            "insider_sentiment": insider_sent,
            "peers": peers
        }

    def _simplify_forecast(self, forecast_data: Dict, aggregated_base: Dict, raw_data: Dict) -> Dict:
        def get_val(field):
            obj = forecast_data.get(field)
            if isinstance(obj, dict):
                return obj.get('value')
            return obj
        
        # Extract current values for comparison
        profile = raw_data.get('profile', {})
        def get_profile_val(field):
            obj = profile.get(field)
            if isinstance(obj, dict): return obj.get('value')
            return obj
        
        current_pe = get_profile_val('std_pe_ratio')
        current_eps = get_profile_val('std_eps')
        
        fin_score = aggregated_base.get('financial_score', {})
        growth = fin_score.get('growth', {})
        current_earnings_growth_5y = growth.get('ni_cagr', {}).get('val', 0) if growth.get('ni_cagr') else 0
        current_revenue_growth_5y = growth.get('rev_cagr', {}).get('val', 0) if growth.get('rev_cagr') else 0
        
        surprises = forecast_data.get('std_earnings_surprise_history', [])
        if isinstance(surprises, dict): surprises = surprises.get('value', [])
        if not isinstance(surprises, list): surprises = []
        
        surprise_summary = None
        if surprises:
            def get_surprise_pct(s):
                spct = s.get('surprise_percent')
                if spct is None: spct = s.get('surprisePercent')
                if spct is None:
                    act = s.get('actual')
                    est = s.get('estimate')
                    if act is not None and est is not None and est != 0:
                        spct = (act - est) / abs(est) * 100
                    else:
                        spct = 0
                return spct

            def get_surprise_amt(s):
                amt = s.get('surprise')
                if amt is None:
                    act = s.get('actual')
                    est = s.get('estimate')
                    if act is not None and est is not None:
                        amt = act - est
                    else:
                        amt = 0
                return amt

            avg_surprise = sum(get_surprise_pct(s) for s in surprises) / len(surprises) if surprises else 0
            positive_count = sum(1 for s in surprises if get_surprise_pct(s) > 0)
            
            surprise_summary = {
                "avg_surprise_pct": avg_surprise,
                "positive_count": positive_count,
                "total_count": len(surprises),
                "latest_4": [
                    {
                        "period": s.get('period', 'N/A'),
                        "actual": s.get('actual', 0),
                        "estimate": s.get('estimate', 0),
                        "surprise": get_surprise_amt(s),
                        "surprise_pct": get_surprise_pct(s)
                    }
                    for s in surprises[:4]
                ]
            }
        
        return {
            "current_pe": current_pe,
            "current_eps": current_eps,
            "current_earnings_growth_5y": current_earnings_growth_5y,
            "current_revenue_growth_5y": current_revenue_growth_5y,
            "forward_eps": get_val('std_eps_estimate_current_year') or get_val('std_forward_eps'),
            "forward_pe": get_val('std_forward_pe_current_year') or get_val('std_forward_pe'),
            "earnings_growth_current_year": get_val('std_earnings_growth_current_year'),
            "quarterly_earnings_growth_yoy": get_val('std_quarterly_earnings_growth_yoy'),
            "revenue_growth_next_year": get_val('std_revenue_growth_next_year'),
            "price_target_low": get_val('std_price_target_low'),
            "price_target_high": get_val('std_price_target_high'),
            "price_target_consensus": get_val('std_price_target_consensus'),
            "surprises": surprise_summary
        }
    
    def generate_appendix(self, bundle: Dict[str, Any]) -> str:
        """
        Generate a comprehensive markdown appendix with all raw data.
        """
        symbol = bundle['symbol'].upper()
        data = bundle['data']
        
        # Access raw objects
        raw_data = data.get('initial_data', {})
        fin_score = data.get('financial_score', {})
        tech_score = data.get('technical_score', {})
        val_data = data.get('valuation', {})
        forecast_data = raw_data.get('forecast_data', {})
        profile = raw_data.get('profile', {})
        
        # Statements shortcuts
        stmts = raw_data.get('income_statements', [])
        cf_stmts = raw_data.get('cash_flows', [])
        bs_stmts = raw_data.get('balance_sheets', [])
        
        lines = []
        lines.append("\n---\n")
        lines.append("## 📊 原始数据附表 (Raw Data Appendix)\n")
        lines.append("> 方便查阅每个指标的原始值和程序字段名。\n")
        
        # Helper: Format Value
        def fmt(val, fmt_type=MetricFormat.DECIMAL, default="N/A"):
            if isinstance(val, dict) and 'value' in val: val = val['value']
            if val is None or val == 'N/A': return default
            
            try:
                if isinstance(val, (int, float)):
                    if fmt_type == MetricFormat.PERCENT: return f"{val*100:.2f}%"
                    elif fmt_type == MetricFormat.CURRENCY: return f"${val:.2f}"
                    elif fmt_type == MetricFormat.CURRENCY_LARGE:
                        abs_val = abs(val)
                        if abs_val >= 1e9: return f"${val/1e9:.2f}B"
                        elif abs_val >= 1e6: return f"${val/1e6:.2f}M"
                        return f"${val:.2f}"
                    elif fmt_type == MetricFormat.DECIMAL:
                        return f"{val:.4f}" if abs(val) < 10 else f"{val:.2f}"
                return str(val)
            except:
                return str(val)

        # Helper: Get value and source
        def get_val_src(obj, key, default_src="Calculated"):
            if not obj: return None, "N/A"
            item = obj.get(key)
            if isinstance(item, dict):
                src = item.get('source', default_src)
                # Helper to format source nicely
                if src and src != 'N/A': 
                    src = src.replace('_', ' ').title()
                    if src.lower() == 'sec edgar': src = 'SEC Edgar'
                    if src.lower() == 'yahoo': src = 'Yahoo'
                
                val = item.get('value')
                # If val is missing/None/0, maybe mark source as N/A?
                if val is None or val == 'N/A': 
                    return val, "Calculated (N/A)"
                
                # If default_src was "Calculated" but we found a real source, combine them?
                # The user wants to see the underlying source for Calculated fields if possible.
                # But here we are just extracting raw items.
                return val, src
            return item, default_src
            
        def safe_div(n, d, default=0):
            try:
                return n / d if d and d != 0 else default
            except:
                return default

        def get_raw_val(item):
            if isinstance(item, dict) and 'value' in item:
                return item['value']
            return item
            
        def get_raw_src(item, default="Calculated"):
             if isinstance(item, dict) and 'source' in item:
                 s = item['source']
                 if s == 'sec_edgar': return 'SEC Edgar'
                 return s.title()
             return default

        # === 1. Financial Calculation Components ===
        lines.append("### 1. 财务计算组件 (Financial Calculation Components)\n")
        lines.append("| Component | 中文名称 | Value (数值) | Source (来源) | Logic (逻辑) |")
        lines.append("|---|---|---|---|---|")
        
        # --- Calculations ---
        # 1. Tax Rate & NOPAT
        tax_rate = 0.21 # Default fallback
        nopat_val = None
        tax_src = "Estimated"
        nopat_src = "Calculated"
        
        if stmts:
            curr_is = stmts[0]
            tax_exp_item = curr_is.get('std_income_tax_expense', 0)
            pretax_item = curr_is.get('std_pretax_income', 0)
            op_inc_item = curr_is.get('std_operating_income', 0)
            
            tax_exp = get_raw_val(tax_exp_item)
            pretax = get_raw_val(pretax_item)
            op_inc = get_raw_val(op_inc_item)
            
            # Source derivation
            base_src = get_raw_src(op_inc_item, "Yahoo")
            
            if pretax and pretax != 0 and tax_exp is not None:
                tax_rate = abs(safe_div(tax_exp, pretax)) 
                tax_src = f"Calculated ({get_raw_src(tax_exp_item, 'Yahoo')})"
            
            if op_inc is not None:
                nopat_val = op_inc * (1 - tax_rate)
                nopat_src = f"Calculated ({base_src})"
            else:
                nopat_val = None
                nopat_src = "Calculated (Missing Input)"
            
            lines.append(f"| NOPAT | 税后营业利润 | {fmt(nopat_val, MetricFormat.CURRENCY_LARGE)} | {nopat_src} | `Operating Income * (1 - {tax_rate:.1%})` |")
        else:
            lines.append(f"| NOPAT | 税后营业利润 | N/A | Missing Data | `Operating Income * (1 - Tax Rate)` |")

        # 2. Invested Capital
        # Use the FY/TTM balance sheet aligned with latest income statement to avoid
        # using an incomplete quarterly snapshot (e.g., FMP Q1 mis-labeled as FY).
        ic_val = None
        ic_src = "Calculated"
        _anchor_period = stmts[0].get('std_period', '') if stmts else ''
        _annual_bs = None
        if bs_stmts:
            for _bs in bs_stmts:
                if _bs.get('std_period_type', '') not in ['FY', 'TTM']:
                    continue
                if _bs.get('std_period', '') <= _anchor_period:
                    _annual_bs = _bs
                    break
            if _annual_bs is None:
                _annual_bs = bs_stmts[0]
            # Sanity check: debt drop > 95% in one period is almost certainly corrupt data
            _sel_debt_raw = get_raw_val(_annual_bs.get('std_total_debt', 0)) or 0
            _sel_period = _annual_bs.get('std_period', '')
            for _bs2 in bs_stmts:
                if _bs2.get('std_period_type', '') not in ['FY', 'TTM']:
                    continue
                if _bs2.get('std_period', '') < _sel_period:
                    _prev_debt = get_raw_val(_bs2.get('std_total_debt', 0)) or 0
                    if _prev_debt > 1e8 and _sel_debt_raw < _prev_debt * 0.05:
                        _annual_bs = _bs2  # fall back to prior reliable period
                    break
        
        if _annual_bs:
            curr_bs = _annual_bs
            equity_item = curr_bs.get('std_shareholder_equity', 0)
            debt_item = curr_bs.get('std_total_debt', 0)
            cash_item = curr_bs.get('std_cash', 0)
            
            equity = get_raw_val(equity_item) or 0
            debt = get_raw_val(debt_item) or 0
            cash = get_raw_val(cash_item) or 0
            
            base_src = get_raw_src(equity_item, "Yahoo")
            ic_src = f"Calculated ({base_src})"
            
            if equity or debt:
                ic_val = (equity + debt) - cash
                lines.append(f"| Invested Capital | 投入资本 | {fmt(ic_val, MetricFormat.CURRENCY_LARGE)} | {ic_src} | `Equity({fmt(equity, MetricFormat.CURRENCY_LARGE)}) + Debt({fmt(debt, MetricFormat.CURRENCY_LARGE)}) - Cash({fmt(cash, MetricFormat.CURRENCY_LARGE)})` |")
            else:
                 lines.append(f"| Invested Capital | 投入资本 | N/A | Missing Data | `Total Equity + Total Debt - Cash` |")
        else:
            lines.append(f"| Invested Capital | 投入资本 | N/A | Missing Data | `Total Equity + Total Debt - Cash` |")

        # 3. Tax Rate Display
        lines.append(f"| Tax Rate | 有效税率 | {fmt(tax_rate, MetricFormat.PERCENT)} | {tax_src} | `Income Tax / Pretax Income` |")
        
        # Raw Income Statement Items (Existing)
        if stmts:
            curr = stmts[0]
            val, src = get_val_src(curr, 'std_gross_profit', 'Yahoo')
            lines.append(f"| Gross Profit | 毛利润 | {fmt(val, MetricFormat.CURRENCY_LARGE)} | {src} | `Revenue - Cost of Revenue` |")
            
            val, src = get_val_src(curr, 'std_operating_income', 'Yahoo')
            lines.append(f"| Operating Income | 营业利润 | {fmt(val, MetricFormat.CURRENCY_LARGE)} | {src} | `Gross Profit - OpEx` |")
            
        # 4. Cash Flow (FCF)
        # FIX: Prefer FY/TTM annual cash flow to avoid displaying a Q1-only
        # quarterly snapshot (which may have negative OCF) as the "latest" FCF.
        # This keeps the appendix display consistent with the FCF/Debt calculation.
        fcf_val = None
        if cf_stmts:
            # Prefer the latest FY or TTM cash flow statement
            _annual_cf = next(
                (cf for cf in cf_stmts
                 if cf.get('std_period_type', '') in ['FY', 'TTM']),
                cf_stmts[0]  # fallback to first if no annual found
            )
            curr_cf = _annual_cf
            ocf_item = curr_cf.get('std_operating_cash_flow', 0)
            capex_item = curr_cf.get('std_capex', 0)
            cf_period_type = curr_cf.get('std_period_type', '')

            ocf = get_raw_val(ocf_item)
            capex = get_raw_val(capex_item)

            base_src = get_raw_src(ocf_item, "Yahoo")
            period_tag = "Normalized" if cf_period_type in ['FY', 'TTM'] else "Normalized (Quarterly)"
            fcf_src = f"Calculated ({base_src})"

            if ocf is not None and capex is not None:
                fcf_val = ocf - abs(capex)
                lines.append(f"| FCF (Latest) | 自由现金流 | {fmt(fcf_val, MetricFormat.CURRENCY_LARGE)} | {fcf_src} | `OCF({fmt(ocf, MetricFormat.CURRENCY_LARGE)}) - abs(CapEx)({fmt(abs(capex), MetricFormat.CURRENCY_LARGE)})` |")
            else:
                lines.append(f"| FCF (Latest) | 自由现金流 | N/A | Calculated (Missing) | `OCF - abs(CapEx)` |")
        else:
            lines.append(f"| FCF (Latest) | 自由现金流 | N/A | Missing Data | `OCF - CapEx` |")

        # 5. SBC Impact
        # FIX: scoring system (capital_allocation.py) uses SBC/OCF as the denominator,
        # not SBC/Revenue. Align the appendix display with the actual metric definition.
        # If OCF is negative or zero (can happen in seasonal quarters), fallback to Revenue
        # and flag it clearly, so readers know the denominator differs.
        sbc_val = None
        if cf_stmts and stmts:
            sbc_item = cf_stmts[0].get('std_stock_based_compensation', 0)
            sbc_val = get_raw_val(sbc_item)
            base_src = get_raw_src(sbc_item, "Yahoo")

            # Prefer OCF from the FY/TTM annual CF (same as scoring logic)
            _annual_cf_sbc = next(
                (cf for cf in cf_stmts if cf.get('std_period_type', '') in ['FY', 'TTM']),
                cf_stmts[0]
            )
            ocf_item_sbc = _annual_cf_sbc.get('std_operating_cash_flow', 0)
            ocf_val_sbc = get_raw_val(ocf_item_sbc)

            if sbc_val is not None and ocf_val_sbc and ocf_val_sbc > 0:
                sbc_pct = safe_div(sbc_val, ocf_val_sbc)
                lines.append(f"| SBC Impact | 股权激励 | {fmt(sbc_pct, MetricFormat.PERCENT)} | Calculated ({base_src}) | `SBC({fmt(sbc_val, MetricFormat.CURRENCY_LARGE)}) / OCF` |")
            elif sbc_val is not None:
                # Fallback: use Revenue if OCF is unavailable/negative
                rev_item_sbc = stmts[0].get('std_revenue', 0)
                rev_val_sbc = get_raw_val(rev_item_sbc)
                if rev_val_sbc and rev_val_sbc != 0:
                    sbc_pct = safe_div(sbc_val, rev_val_sbc)
                    lines.append(f"| SBC Impact | 股权激励 | {fmt(sbc_pct, MetricFormat.PERCENT)} | Calculated ({base_src}) | `SBC({fmt(sbc_val, MetricFormat.CURRENCY_LARGE)}) / Revenue (OCF unavail)` |")
                else:
                    lines.append(f"| SBC Impact | 股权激励 | N/A | Low Revenue | `SBC / OCF (fallback Revenue)` |")
            else:
                lines.append(f"| SBC Impact | 股权激励 | N/A | Missing Data | `SBC / OCF` |")
        else:
            lines.append(f"| SBC Impact | 股权激励 | N/A | Missing Data | `SBC / OCF` |")
        
        # 6. Dilution (Share Count CAGR)
        if stmts and len(stmts) > 1:
            latest_shares_item = stmts[0].get('std_basic_average_shares', 0)
            oldest_shares_item = stmts[-1].get('std_basic_average_shares', 0)
            
            latest_shares = get_raw_val(latest_shares_item)
            oldest_shares = get_raw_val(oldest_shares_item)
            
            base_src = get_raw_src(latest_shares_item, "Yahoo")
            
            years = len(stmts) - 1
            if latest_shares > 0 and oldest_shares > 0 and years > 0:
                cagr = (latest_shares / oldest_shares)**(1/years) - 1
                lines.append(f"| Dilution Rate | 稀释率 | {fmt(cagr, MetricFormat.PERCENT)} | Calculated ({base_src}) | `CAGR of Shares (Spread {years}Y)` |")
            else:
                 lines.append(f"| Dilution Rate | 稀释率 | 0.00% | Calculated ({base_src}) | `Share Count Change` |")
        else:
            lines.append(f"| Dilution Rate | 稀释率 | N/A | Insufficient Data | `Share Count CAGR` |")
        
        lines.append("")

        # === 2. Technical Indicator Components ===
        lines.append("### 2. 技术指标组件 (Technical Indicator Components)\n")
        lines.append("| Component | 中文名称 | Value (数值) | Source (来源) | Context (参考) |")
        lines.append("|---|---|---|---|---|")
        
        tech_cats = tech_score.get('score', {}).get('categories', {})
        tech_info = tech_score.get('score', {}).get('data_info', {})
        
        # Helper for Tech Source
        def tech_src(val):
             if val is None or val == 'N/A' or val == 0: return "Calculated (N/A)"
             return "Calculated (Yahoo)"

        # Prices
        val = tech_info.get('latest_price')
        lines.append(f"| Latest Price | 最新价格 | {fmt(val, MetricFormat.CURRENCY)} | {tech_src(val)} | `Close Price` |")
        val = tech_info.get('high_52w')
        lines.append(f"| 52-Week High | 52周最高 | {fmt(val, MetricFormat.CURRENCY)} | {tech_src(val)} | `Highest Price (1Y)` |")
        val = tech_info.get('low_52w')
        lines.append(f"| 52-Week Low | 52周最低 | {fmt(val, MetricFormat.CURRENCY)} | {tech_src(val)} | `Lowest Price (1Y)` |")
        
        # Volumes
        vol_cat = tech_cats.get('volume_price', {}).get('indicators', {})
        val = tech_info.get('latest_volume')
        lines.append(f"| Latest Volume | 最新成交量 | {fmt(val, MetricFormat.DECIMAL)} | {tech_src(val)} | `Daily Volume` |")
        val = tech_info.get('avg_volume')
        lines.append(f"| Avg Volume | 平均成交量 | {fmt(val, MetricFormat.DECIMAL)} | {tech_src(val)} | `20-Day Average` |")

        # Trend & Momentum
        trend_cat = tech_cats.get('trend_strength', {}).get('indicators', {})
        mom_cat = tech_cats.get('momentum', {}).get('indicators', {})
        vol_cat = tech_cats.get('volatility', {}).get('indicators', {})
        struct_cat = tech_cats.get('price_structure', {}).get('indicators', {})
        vp_cat = tech_cats.get('volume_price', {}).get('indicators', {})

        # MA
        ma = trend_cat.get('multi_ma', {})
        val = ma.get('ma20')
        lines.append(f"| SMA 20 | 20日均线 | {fmt(val, MetricFormat.CURRENCY)} | {tech_src(val)} | `Short Trend` |")
        val = ma.get('ma50')
        lines.append(f"| SMA 50 | 50日均线 | {fmt(val, MetricFormat.CURRENCY)} | {tech_src(val)} | `Medium Trend` |")
        val = ma.get('ma200')
        lines.append(f"| SMA 200 | 200日均线 | {fmt(val, MetricFormat.CURRENCY)} | {tech_src(val)} | `Long Trend` |")
        
        # Bollinger
        boll = vol_cat.get('bollinger', {})
        val = boll.get('upper')
        lines.append(f"| BB Upper | 布林上轨 | {fmt(val, MetricFormat.CURRENCY)} | {tech_src(val)} | `20D SMA + 2*StdDev` |")
        val = boll.get('middle')
        lines.append(f"| BB Middle | 布林中轨 | {fmt(val, MetricFormat.CURRENCY)} | {tech_src(val)} | `20D SMA` |")
        val = boll.get('lower')
        lines.append(f"| BB Lower | 布林下轨 | {fmt(val, MetricFormat.CURRENCY)} | {tech_src(val)} | `20D SMA - 2*StdDev` |")
        
        # RSI, ROC, MACD
        val = mom_cat.get('rsi', {}).get('rsi')
        lines.append(f"| RSI (14) | 相对强弱指数 | {fmt(val, MetricFormat.DECIMAL)} | {tech_src(val)} | `Momentum (0-100)` |")
        val = mom_cat.get('roc', {}).get('roc')
        lines.append(f"| ROC (20) | 变动率 | {fmt(val, MetricFormat.DECIMAL)}% | {tech_src(val)} | `Price Rate of Change` |")
        
        macd = mom_cat.get('macd', {})
        val = macd.get('macd')
        lines.append(f"| MACD Line | MACD线 | {fmt(val, MetricFormat.DECIMAL)} | {tech_src(val)} | `12EMA - 26EMA` |")
        val = macd.get('signal_line')  # Key from momentum_indicators.calculate_macd()
        lines.append(f"| Signal Line | 信号线 | {fmt(val, MetricFormat.DECIMAL)} | {tech_src(val)} | `9EMA of MACD` |")
        val = macd.get('histogram')    # Key from momentum_indicators.calculate_macd()
        lines.append(f"| MACD Hist | MACD柱 | {fmt(val, MetricFormat.DECIMAL)} | {tech_src(val)} | `MACD - Signal` |")
        
        # ADX
        adx = trend_cat.get('adx', {})
        val = adx.get('adx')
        lines.append(f"| ADX | 趋势强度 | {fmt(val, MetricFormat.DECIMAL)} | {tech_src(val)} | `>25=Strong Trend` |")
        
        # Support/Resistance
        sr = struct_cat.get('support_resistance', {})
        val = sr.get('support')
        lines.append(f"| Support | 最近支撑 | {fmt(val, MetricFormat.CURRENCY)} | {tech_src(val)} | `Nearest Support Level` |")
        val = sr.get('resistance')
        lines.append(f"| Resistance | 最近阻力 | {fmt(val, MetricFormat.CURRENCY)} | {tech_src(val)} | `Nearest Resistance Level` |")
        val = sr.get('explanation', 'N/A')
        lines.append(f"| Structure | 市场结构 | {val} | {tech_src(val if val!='N/A' else None)} | `High/Low Pattern` |")
        
        # Volume
        val = vp_cat.get('obv', {}).get('obv')
        lines.append(f"| OBV | 能量潮 | {fmt(val, MetricFormat.DECIMAL)} | {tech_src(val)} | `On-Balance Volume` |")
        # FIX: Correct key is volume_ratio
        val = vp_cat.get('volume_strength', {}).get('volume_ratio')
        lines.append(f"| Vol Ratio | 量比 | {fmt(val, MetricFormat.DECIMAL)} | {tech_src(val)} | `Vol / AvgVol` |")
        val = vol_cat.get('atr', {}).get('atr_pct')
        lines.append(f"| ATR % | 波动率百分比 | {fmt(val, MetricFormat.DECIMAL)}% | {tech_src(val)} | `ATR / Price` |")
        lines.append("")

        # === 3. Valuation Input Data ===
        lines.append("### 3. 估值基础数据 (Valuation Input Data)\n")
        lines.append("| English Name | 中文名称 | Value (数值) | Source (来源) | Field Name (字段) |")
        lines.append("|---|---|---|---|---|")
        
        # CAGRs
        gr = fin_score.get('score', {}).get('category_scores', {}).get('growth', {}).get('metrics', {})
        rev = gr.get('revenue_cagr_5y', {})
        ni = gr.get('net_income_cagr_5y', {})
        fcf = gr.get('fcf_cagr_5y', {})
        
        lines.append(f"| Revenue CAGR (5Y) | 营收增速 | {fmt(rev.get('value'), MetricFormat.PERCENT)} | {rev.get('source','Calculated')} | `revenue_cagr_5y` |")
        lines.append(f"| Net Income CAGR (5Y) | 净利增速 | {fmt(ni.get('value'), MetricFormat.PERCENT)} | {ni.get('source','Calculated')} | `net_income_cagr_5y` |")
        lines.append(f"| FCF CAGR (5Y) | FCF增速 | {fmt(fcf.get('value'), MetricFormat.PERCENT)} | {fcf.get('source','Calculated')} | `fcf_cagr_5y` |")
        
        # Profile Data (Actually from Income Statement)
        if stmts:
             curr_is = stmts[0]
             val, src = get_val_src(curr_is, 'std_net_income')
             lines.append(f"| Net Income (Latest) | 最新净利润 | {fmt(val, MetricFormat.CURRENCY_LARGE)} | {src} | `std_net_income` |")
             
             val, src = get_val_src(curr_is, 'std_revenue')
             lines.append(f"| Revenue (Latest) | 最新营收 | {fmt(val, MetricFormat.CURRENCY_LARGE)} | {src} | `std_revenue` |")
             
             val, src = get_val_src(curr_is, 'std_ebitda')
             lines.append(f"| EBITDA | EBITDA | {fmt(val, MetricFormat.CURRENCY_LARGE)} | {src} | `std_ebitda` |")
        else:
             lines.append(f"| Net Income (Latest) | 最新净利润 | N/A | Missing Data | `std_net_income` |")
             lines.append(f"| Revenue (Latest) | 最新营收 | N/A | Missing Data | `std_revenue` |")
             lines.append(f"| EBITDA | EBITDA | N/A | Missing Data | `std_ebitda` |")
        
        # Cash Flow Details
        # FIX: Use the same FY/TTM priority logic as the FCF appendix to ensure
        # the displayed OCF/CapEx reflects annual figures, not a partial Q1 snapshot.
        if cf_stmts:
            _annual_cf_val = next(
                (cf for cf in cf_stmts
                 if cf.get('std_period_type', '') in ['FY', 'TTM']),
                cf_stmts[0]  # fallback to first if no annual statement found
            )
            val, src = get_val_src(_annual_cf_val, 'std_operating_cash_flow')
            lines.append(f"| Operating Cash Flow | 经营现金流 | {fmt(val, MetricFormat.CURRENCY_LARGE)} | {src} | `std_operating_cash_flow` |")
            val, src = get_val_src(_annual_cf_val, 'std_capex')
            lines.append(f"| Capital Expenditure | 资本支出 | {fmt(val, MetricFormat.CURRENCY_LARGE)} | {src} | `std_capex` |")
        else:
            lines.append(f"| Operating Cash Flow | 经营现金流 | N/A | Missing Data | `std_operating_cash_flow` |")
            lines.append(f"| Capital Expenditure | 资本支出 | N/A | Missing Data | `std_capex` |")
        
        # Balance Sheet Items (use the same reliable FY/TTM BS selected above for IC)
        if _annual_bs:
            curr_bs = _annual_bs
            val, src = get_val_src(curr_bs, 'std_total_debt')
            lines.append(f"| Total Debt | 总债务 | {fmt(val, MetricFormat.CURRENCY_LARGE)} | {src} | `std_total_debt` |")
            val, src = get_val_src(curr_bs, 'std_cash')
            lines.append(f"| Cash & Equiv | 现金及等价物 | {fmt(val, MetricFormat.CURRENCY_LARGE)} | {src} | `std_cash` |")
            val, src = get_val_src(curr_bs, 'std_shareholder_equity')
            lines.append(f"| Shareholder Equity | 股东权益 | {fmt(val, MetricFormat.CURRENCY_LARGE)} | {src} | `std_shareholder_equity` |")
            
        # Ratios
        val, src = get_val_src(profile, 'std_market_cap')
        lines.append(f"| Market Cap | 市值 | {fmt(val, MetricFormat.CURRENCY_LARGE)} | {src} | `profile.std_market_cap` |")
        
        val, src = get_val_src(profile, 'std_pe_ratio')
        lines.append(f"| P/E Ratio | 市盈率 | {fmt(val, MetricFormat.DECIMAL)} | {src} | `profile.std_pe_ratio` |")
        
        val, src = get_val_src(profile, 'std_pb_ratio')
        lines.append(f"| P/B Ratio | 市净率 | {fmt(val, MetricFormat.DECIMAL)} | {src} | `profile.std_pb_ratio` |")
        
        val, src = get_val_src(profile, 'std_ps_ratio')
        lines.append(f"| P/S Ratio | 市销率 | {fmt(val, MetricFormat.DECIMAL)} | {src} | `profile.std_ps_ratio` |")
        
        val, src = get_val_src(profile, 'std_peg_ratio')
        lines.append(f"| PEG Ratio | PEG比率 | {fmt(val, MetricFormat.DECIMAL)} | {src} | `profile.std_peg_ratio` |")
        
        val, src = get_val_src(profile, 'std_dividend_yield')
        # Yahoo returns dividendYield as a decimal (e.g. 0.0092 = 0.92%).
        # Using MetricFormat.PERCENT would multiply by 100 again → WRONG (92%).
        # Use DECIMAL and append '%' manually.
        lines.append(f"| Dividend Yield | 股息率 | {fmt(val, MetricFormat.DECIMAL)}% | {src} | `profile.std_dividend_yield` |")
        
        val, src = get_val_src(profile, 'std_eps')
        lines.append(f"| EPS (TTM) | 每股收益 | {fmt(val, MetricFormat.CURRENCY)} | {src} | `profile.std_eps` |")

        # === Forward Estimates & Surprises ===
        lines.append("\n#### 前瞻预测数据 (Forward Estimates)\n")
        lines.append("| Category | English Name | 中文名称 | Value | Source (来源) | Field |")
        lines.append("|---|---|---|---|---|---|")
        
        # Forward Logic
        val, src = get_val_src(forecast_data, 'std_eps_estimate_current_year')
        lines.append(f"| **Estimates** | Current Year EPS (FY1) | 本年EPS预期 (FY1) | {fmt(val, MetricFormat.CURRENCY)} | {src} | `forecast_data.std_eps_estimate_current_year` |")

        val, src = get_val_src(forecast_data, 'std_forward_eps')
        lines.append(f"| | Next Year EPS (FY2) | 明年EPS预期 (FY2) | {fmt(val, MetricFormat.CURRENCY)} | {src} | `forecast_data.std_forward_eps` |")
        
        val, src = get_val_src(forecast_data, 'std_forward_pe_current_year')
        lines.append(f"| | Current Year P/E (FY1) | 本年前瞻市盈率 (FY1) | {fmt(val, MetricFormat.DECIMAL)} | {src} | `forecast_data.std_forward_pe_current_year` |")
        
        val, src = get_val_src(forecast_data, 'std_forward_pe')
        lines.append(f"| | Next Year P/E (FY2) | 明年前瞻市盈率 (FY2) | {fmt(val, MetricFormat.DECIMAL)} | {src} | `forecast_data.std_forward_pe` |")
        
        val, src = get_val_src(forecast_data, 'std_earnings_growth_current_year')
        lines.append(f"| | Full Year Earnings Growth | 本年预计总盈利增长 | {fmt(val, MetricFormat.PERCENT)} | {src} | `forecast_data.std_earnings_growth_current_year` |")
        
        val, src = get_val_src(forecast_data, 'std_quarterly_earnings_growth_yoy')
        lines.append(f"| | Quarterly Earnings Growth YoY | 最近季度盈利同比 | {fmt(val, MetricFormat.PERCENT)} | {src} | `forecast_data.std_quarterly_earnings_growth_yoy` |")
        
        val, src = get_val_src(forecast_data, 'std_revenue_growth_next_year')
        lines.append(f"| | Revenue Growth (NY) | 明年营收增长 | {fmt(val, MetricFormat.PERCENT)} | {src} | `forecast_data.std_revenue_growth_next_year` |")
        
        val, src = get_val_src(forecast_data, 'std_price_target_low')
        lines.append(f"| **Price Targets** | Analyst Low | 分析师最低价 | {fmt(val, MetricFormat.CURRENCY)} | {src} | `forecast_data.std_price_target_low` |")
        
        val, src = get_val_src(forecast_data, 'std_price_target_high')
        lines.append(f"| | Analyst High | 分析师最高价 | {fmt(val, MetricFormat.CURRENCY)} | {src} | `forecast_data.std_price_target_high` |")
        
        val, src = get_val_src(forecast_data, 'std_price_target_consensus')
        lines.append(f"| | Analyst Consensus | 分析师共识价 | {fmt(val, MetricFormat.CURRENCY)} | {src} | `forecast_data.std_price_target_consensus` |")
        
        surprises = forecast_data.get('std_earnings_surprise_history', {})
        if isinstance(surprises, dict): surprises = surprises.get('value', [])
        if not isinstance(surprises, list): surprises = []
        
        lines.append(f"| **Surprises** | Earnings Surprises | 盈利意外 | {len(surprises)} records | Finnhub | `forecast_data.std_earnings_surprise_history` |")
        lines.append("")
        
        if surprises:
            lines.append("##### Earnings Surprise详细记录 (Latest 4 Quarters)\n")
            lines.append("| Period(日历季) | Actual EPS | Estimate EPS | Surprise | Surprise % |")
            lines.append("|--------|-----------|-------------|----------|-----------|")
            for s in surprises[:4]:
                # Surprise % might be missing or raw. Finnhub sometimes returns it as 'surprisePercent' or we calculate it.
                # Inspecting typical Finnhub response: {'period': '...', 'actual': 1.2, 'estimate': 1.1, 'surprise': 0.1, 'surprisePercent': 9.09}
                # But UnifiedSchema might mapped it differently?
                # Check how unified_schema defines it? It usually just passes dict.
                
                spct = s.get('surprise_percent')
                if spct is None: spct = s.get('surprisePercent')
                
                # If still None, calculate manually
                act = s.get('actual')
                est = s.get('estimate')
                if spct is None and act is not None and est is not None and est != 0:
                     spct = (act - est) / abs(est) * 100
                elif spct is None:
                     spct = 0

                lines.append(f"| {s.get('period')} | {fmt(s.get('actual'), MetricFormat.CURRENCY)} | {fmt(s.get('estimate'), MetricFormat.CURRENCY)} | {fmt(s.get('surprise'), MetricFormat.CURRENCY)} | {fmt(spct, MetricFormat.DECIMAL)}% |")
            lines.append("")

        # === 4. Supplemental Data ===
        lines.append("\n### 4. 补充数据 (Supplemental Data)\n")
        lines.append("| Category | English Name | 中文名称 | Value (数值) | Source (来源) | Logic (逻辑) |")
        lines.append("|---|---|---|---|---|---|")
        
        # Supplemental Logic (mix of profile and forecast_data)
        # Re-using internal val extraction
        
        val, src = get_val_src(profile, 'std_recommendation_key', default_src="Yahoo")
        if val == 'N/A' or val is None: src = "N/A"
        lines.append(f"| **Analyst** | Recommendation | 评级建议 | {fmt(val, MetricFormat.STRING)} | {src} | `recommendationKey` |")
        
        val, src = get_val_src(forecast_data, 'std_number_of_analysts')
        lines.append(f"| | Num Analysts | 分析师数量 | {fmt(val, MetricFormat.DECIMAL)} | {src} | `numberOfAnalystOpinions` |")
        
        stock_52w_val, stock_52w_src = get_val_src(profile, 'std_52_week_change')
        lines.append(f"| **Risk/Trend** | 52W Change | 年涨跌幅 | {fmt(stock_52w_val, MetricFormat.PERCENT)} | {stock_52w_src} | `52WeekChange` |")

        # FIX: 'std_sandp_52_week_change' is the S&P 500 index's own 52W return, not the
        # stock's relative Alpha. We compute Alpha = stock52W - sp500_52W so that the value
        # consistently means "how much this stock outperformed / underperformed the market".
        sp500_val, sp500_src = get_val_src(profile, 'std_sandp_52_week_change')
        if isinstance(stock_52w_val, (int, float)) and isinstance(sp500_val, (int, float)):
            alpha_val = stock_52w_val - sp500_val
            alpha_src = stock_52w_src  # inherits stock data source
        else:
            alpha_val = sp500_val  # fallback: show raw value if either is missing
            alpha_src = sp500_src
        lines.append(f"| | vs S&P 500 | 标普超额Alpha | {fmt(alpha_val, MetricFormat.PERCENT)} | {alpha_src} | `52WeekChange - SandP52WeekChange` |")
        
        val, src = get_val_src(profile, 'std_audit_risk')
        lines.append(f"| | Audit Risk | 审计风险 | {fmt(val, MetricFormat.DECIMAL)} | {src} | `auditRisk` |")
        
        val, src = get_val_src(profile, 'std_board_risk')
        lines.append(f"| | Board Risk | 董事会风险 | {fmt(val, MetricFormat.DECIMAL)} | {src} | `boardRisk` |")
        
        val, src = get_val_src(profile, 'std_current_ratio')
        lines.append(f"| **Liquidity** | Current Ratio | 流动比率 | {fmt(val, MetricFormat.DECIMAL)} | {src} | `currentRatio` |")
        
        val, src = get_val_src(profile, 'std_quick_ratio')
        lines.append(f"| | Quick Ratio | 速动比率 | {fmt(val, MetricFormat.DECIMAL)} | {src} | `quickRatio` |")
        
        # === 5. Market Intelligence ===
        lines.append("\n### 5. 市场情报 (Market Intelligence)\n")
        
        # Peers
        peers = raw_data.get('peers', [])
        if peers:
            lines.append(f"**同类标的（Competitors/Peers）:** {', '.join(peers[:10])}\n")
        
        # Always attribute to Finnhub as the API provider
        news_source_note = "via Finnhub API"
        news = raw_data.get('news', [])

        if news:
            # Sort by datetime desc
            sorted_news = sorted(news, key=lambda x: x.get('datetime', 0), reverse=True)
            lines.append(f"\n**近期新闻（Recent News，Top 5）— {news_source_note}:**\n")
            lines.append("| # | Headline（标题） | Source（来源） | Date（日期） |")
            lines.append("|---|---|---|---|")
            from datetime import datetime as dt
            for i, n in enumerate(sorted_news[:5], 1):
                ts = n.get('datetime', 0)
                date_str = dt.fromtimestamp(ts).strftime('%Y-%m-%d') if ts else '-'
                headline_raw = n.get('headline', '-') or '-'
                headline = headline_raw[:80]
                url = n.get('url', '')
                source = n.get('source', '-') or '-'
                # Use markdown link if URL is available
                if url:
                    headline_cell = f"[{headline}]({url})"
                else:
                    headline_cell = headline
                lines.append(f"| {i} | {headline_cell} | {source} | {date_str} |")
            lines.append("")
        
        # Insider Sentiment Table
        sentiment = raw_data.get('sentiment', {})
        if sentiment:
            insider_sent = sentiment.get('insider_sentiment', [])
            if insider_sent:
                lines.append("\n**内部人士情绪（Insider Sentiment，近6个月）:**\n")
                lines.append("| Year（年） | Month（月） | Net Change（净变化，股数） | MSPR（月度购股比率） |")
                lines.append("|---|---|---|---|")
                for s in insider_sent:
                     lines.append(f"| {s.get('year')} | {s.get('month')} | {fmt(s.get('change'), MetricFormat.DECIMAL)} | {fmt(s.get('mspr'), MetricFormat.DECIMAL)} |")
                lines.append("> MSPR (Monthly Share Purchase Ratio): Proportional indicator of buying activity.\n")
                
            insider_trans = sentiment.get('insider_transactions', [])
            if insider_trans:
                lines.append("\n**内部人士交易（Insider Transactions，近10条）:**\n")
                lines.append("| Date（日期） | Name（姓名） | Shares（持股量） | Change（变化量） | Price（成交价） |")
                lines.append("|---|---|---|---|---|")
                for t in insider_trans[:10]:
                    lines.append(f"| {t.get('transaction_date')} | {t.get('name')} | {t.get('share')} | {t.get('change')} | {fmt(t.get('transaction_price'), MetricFormat.CURRENCY)} |")
        
        return "\n".join(lines)


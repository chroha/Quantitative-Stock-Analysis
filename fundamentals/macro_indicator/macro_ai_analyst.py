"""
Macro AI Analyst (V4.0 CIO Edition)

Interprets macro data (Cycle, Risk, Valuation, Sectors) and generates a strategic commentary
in both Chinese and English (Single-shot generation).
"""

import json
import requests
import logging
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
from fundamentals.reporting.llm_client import LLMClient
from utils.logger import setup_logger
from config.constants import DATA_CACHE_MACRO
from utils import safe_format

logger = setup_logger('macro_ai_analyst')

class MacroAIAnalyst:
    """
    AI Analyst for Macro Strategy.
    Generates bilingual commentary based on processed macro indicators.
    """
    
    def __init__(self):
        self.client = LLMClient()
        
    def generate_commentary(self, data: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate bilingual commentary using the V4.0 "Cynical CIO" approach.
        Returns: {'cn': '...', 'en': '...'}
        """
        # 1. Prepare Data Buffet (Full Context + Pre-computed Signals)
        ai_context = self._prepare_v4_context(data, analysis)
        
        # DEBUG: Save context to file for user inspection
        try:
            project_root = Path(__file__).parent.parent.parent
            debug_path = project_root / DATA_CACHE_MACRO / "debug_ai_context.json"
            if not debug_path.parent.exists():
                debug_path.parent.mkdir(parents=True, exist_ok=True)
            with open(debug_path, 'w', encoding='utf-8') as f:
                json.dump(ai_context, f, indent=2, ensure_ascii=False)
            print(f"  [AI] V4 Context saved to: {debug_path}")
        except Exception as e:
            # Import DATA_CACHE_MACRO locally if needed or assume it's available via previous import logic?
            # Actually constants might not be imported here. 
            # Looking at original code, it didn't import constants explicitly in snippet?
            # Ah, lines 1-60 didn't show imports of constants.
            # Let's hope constants are imported or just catch exception.
            print(f"  [AI] Failed to save debug context: {e}")

        # 2. Build V4.0 Prompt
        prompt = self._build_v4_prompt(ai_context)
        
        # 3. Call API via LLMClient
        print(f"  [AI] Requesting analysis from AI...")
        response_text = self.client.generate_text(prompt)
        
        if response_text:
            result = self._parse_response(response_text)
            
            # Extract headline translations and store in data for report renderer
            news_cn = result.pop('news_cn', [])
            if news_cn and isinstance(news_cn, list):
                # Build lookup: English -> Chinese
                headlines = ai_context.get('headlines_to_translate', [])
                translations = {}
                for en, cn in zip(headlines, news_cn):
                    translations[en] = cn
                data['news_translations'] = translations
                logger.info(f"Extracted {len(translations)} headline translations from AI response")
            
            return result
                
        return {'cn': 'AI Generation Failed.', 'en': 'AI Generation Failed.'}

    def _prepare_v4_context(self, data: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build the V4 context with explicit Outliers, Divergences, and Data Quality warnings.
        """
        dash = data.get('dashboard_data', {})
        assets = dash.get('assets', {})
        econ = dash.get('economic', {})
        internals = dash.get('internals', {})
        
        # --- 1. Data Quality Check ---
        quality_warnings = []
        cpi_meta = econ.get('Inflation', {}).get('CPI Context', {})
        if cpi_meta.get('data_age_days', 0) > 40:
            quality_warnings.append(f"CPI Data is STALE ({cpi_meta.get('data_age_days')} days old). Treat Inflation signals with skepticism.")
            
        ts = data.get('snapshot_date', '')
        if not ts: quality_warnings.append("Snapshot date missing.")

        # --- 2. Outlier Detection ---
        outliers = []
        
        def check_outlier(name, val, type_threshold):
            if val is None: return
            if abs(val) > type_threshold:
                label = "CRASH" if val < -0.05 else "SURGE" if val > 0.05 else "DUMP" if val < 0 else "PUMP"
                outliers.append(f"{name}: {val:.2%} ({label})")

        # Scan Indices (Thresh 2%)
        for k, v in assets.get('Indices', {}).items(): check_outlier(k, v.get('change_1d_safe'), 0.02)
        # Scan Commodities (Thresh 3%)
        for k, v in assets.get('Commodities', {}).items(): check_outlier(k, v.get('change_1d_safe'), 0.03)
        # Scan Key Sectors
        for k, v in assets.get('sectors', {}).items(): check_outlier(k, v.get('change_1d_safe'), 0.025)
        # Crypto
        for k, v in assets.get('Crypto', {}).items(): check_outlier(k, v.get('change_1d_safe'), 0.05)

        # --- 3. Divergence Hunting ---
        divergences = []
        
        # Gold vs DXY
        gold_chg = assets.get('Commodities', {}).get('Gold', {}).get('change_1d_safe', 0)
        dxy_chg = assets.get('Currencies', {}).get('DXY (USD)', {}).get('change_1d_safe', 0)
        if gold_chg < -0.015 and dxy_chg > 0.005:
            divergences.append("LIQUIDITY SQUEEZE: Gold dumping (>1.5%) while USD surging.")
            
        # Credit vs Equity
        spy_chg = assets.get('Indices', {}).get('S&P 500', {}).get('change_1d_safe', 0)
        hy_spread_val = econ.get('Rates & liquidity', {}).get('HY Spread', {}).get('value', 0)
        hy_prev = econ.get('Rates & liquidity', {}).get('HY Spread', {}).get('prev_value', 0)
        if spy_chg > 0 and (hy_spread_val > hy_prev + 0.05):
            divergences.append("CREDIT DIVERGENCE: Equities up but Credit Spreads widening (Fake Rally?).")
            
        # Small Cap vs ERP
        erp = analysis.get('valuation', {}).get('erp', 0) or 0
        iwm_chg = assets.get('Indices', {}).get('Russell 2000', {}).get('change_1d_safe', 0)
        if erp < 0.01 and iwm_chg > 0.01:
            divergences.append("JUNK RALLY: Low ERP (<1%) but Small Caps rallying. High Risk behavior.")

        # --- 4. Assemble Context ---
        context = {
            "meta_date": ts,
            "data_quality_roast": quality_warnings,
            "major_outliers": outliers,
            "structural_divergences": divergences,
            "regime": analysis, # Pass full analysis dict
            "market_summary": {
                "indices": {k: safe_format(v.get('change_1d_safe'), format_spec="+.2%") for k, v in assets.get('Indices', {}).items()},
                "commodities": {k: safe_format(v.get('change_1d_safe'), format_spec="+.2%") for k, v in assets.get('Commodities', {}).items()},
                "rates": {
                    "10y": econ.get('Rates & liquidity', {}).get('10Y Treasury', {}),
                    "hy_spread": econ.get('Rates & liquidity', {}).get('HY Spread', {})
                }
            },
            "aussie_inputs": {
                "aud_usd": assets.get('Currencies', {}).get('AUD/USD', {}),
                "copper": assets.get('Commodities', {}).get('Copper', {}),
                "china_proxy": assets.get('Currencies', {}).get('AUD/CNY', {})
            },
            "news_intelligence": {
                "general": [x.model_dump() for x in data.get('market_news', {}).get('general', [])[:10]],
                "forex": [x.model_dump() for x in data.get('market_news', {}).get('forex', [])[:3]],
                "crypto": [x.model_dump() for x in data.get('market_news', {}).get('crypto', [])[:5]]
            },
            # Headlines to translate for Chinese report (must match report display counts)
            "headlines_to_translate": [
                x.headline for x in data.get('market_news', {}).get('general', [])[:10] if hasattr(x, 'headline')
            ] + [
                x.headline for x in data.get('market_news', {}).get('forex', [])[:3] if hasattr(x, 'headline')
            ] + [
                x.headline for x in data.get('market_news', {}).get('crypto', [])[:5] if hasattr(x, 'headline')
            ]
        }
        return context

    def _build_v4_prompt(self, context: Dict[str, Any]) -> str:
        """Construct the V4.0 Cynical/Quant Prompt."""
        
        json_str = json.dumps(context, indent=2, ensure_ascii=False)
        
        prompt = f'''
### ROLE: Global Macro CIO (Institutional Grade)
**Client:** Sophisticated Australian Portfolio Manager.
**Tone:** **Dispassionate, Sharp, High-Conviction.** Avoid emotional language. Use precise financial terminology. 
**Style:** Think like a risk manager at a major hedge fund. Focus on **asymmetries** and **tail risks**.

### INPUT DATAPOINTS (Processed)
{json_str}

### ANALYTICAL PROTOCOL (V5.0)

**1. DATA INTEGRITY CHECK (Review 'data_quality_roast'):**
   - If CPI is stale (>60 days), objectively flag the **"Information Asymmetry"**. 
   - *Phrasing:* Instead of "roasting", state that "Policy expectations are anchored on stale data, increasing execution risk."

**2. IDIOSYNCRATIC RISKS (Review 'major_outliers' & 'divergences'):**
   - **Liquidity Stress:** If Gold drops >5% while Equities hold, frame this as a **"Collateral Squeeze"** (not just a "crash"). Analyze if this implies forced deleveraging.
   - **Signal Noise:** If Credit (HY Spread) contradicts Equities, prioritize the Credit signal as the "Leading Indicator".

**3. VALUATION & ASYMMETRY:**
   - ERP < 1%: Frame this as **"Poor Risk Reward"** or **"Negative Convexity"**. Avoid metaphors like "pennies in front of steamroller" unless used strictly to describe PnL profile.
   - Link low ERP to rate sensitivity: "Equity duration is at record highs."

**4. PROBABILISTIC OUTLOOK:**
   - Define scenarios based on **Triggers** (e.g., Rates, VIX).
   - **Bear Case:** "Liquidity Withdrawal" (Trigger: 10Y > X%).
   - **Bull Case:** "Multiple Expansion" (Trigger: Yields fade).

**5. THE AUSSIE VIEW (Quantitative Divergence):**
   - Focus on **Terms of Trade**. If Copper/Iron Ore diverge from AUD, label AUD as **"Fundamentally Mispriced"**.
   - Provide a trade structure (Entry/Stop/Target) based on this divergence.

**6. NEWS INTELLIGENCE (Synthesize 'news_intelligence'):**
   - Correlate top news headlines with market moves.
   - If Crypto news is bullish but price is flat, flag **"Seller Exhaustion"** or **"Hidden Distribution"**.
   - Use Forex news to explain AUD/USD anomalies.

**7. HEADLINE TRANSLATION:**
   - Translate ALL headlines listed in `headlines_to_translate` to concise Chinese (~20 chars, financial-professional tone).
   - Return them as a `news_cn` array in the same order as the input list.

### OUTPUT FORMAT (Strict JSON)
Return JSON with "cn", "en", and "news_cn". Content in Markdown.
**IMPORTANT:** For the Chinese version ("cn"), use ONLY Chinese titles without any English in parentheses.

{{
  "cn": "### 🦅 首席视点\\\\n\\\\n**📉 核心逻辑：{{Professional Title in Chinese, e.g., 流动性压力与估值错配}}**\\\\n{{Paragraph: A cold, hard look at the macro regime.}}\\\\n\\\\n**🔍 结构性脆弱诊断:**\\\\n- **信息时滞:** {{Discuss CPI latency objectively}}\\\\n- **抵押品压力:** {{Analyze Gold drop as a liquidity/collateral signal}}\\\\n- **信用背离:** {{Discuss Credit vs Equity gap}}\\\\n\\\\n**📰 关键情报:**\\\\n- {{Synthesize key news impact on assets}}\\\\n\\\\n**⚖️ 情景概率:**\\\\n- 🔻 **去杠杆风险 (概率: X%):** {{Mechanism: Margin calls -> Selling}}\\\\n- 🔼 **通胀交易 (概率: Y%):** {{Mechanism: Real assets rally}}\\\\n\\\\n**🇦🇺 澳洲策略:**\\\\n{{Trade Idea based on Terms of Trade divergence}}\\\\n\\\\n**🛡️ 风险管理指令:**\\\\n1. {{Capital Preservation Step}}\\\\n2. {{Alpha Generation Step}}\\\\n3. {{Liquidity Management}}",
  "en": "...",
  "news_cn": ["华尔街资深人士建议抛售美股", "原油期货因美伊紧张攀升", ...]
}}
'''
        return prompt

    def _parse_response(self, text: str) -> Dict[str, str]:
        """Parse JSON response, handling potential code blocks."""
        import re
        clean = text.strip()
        
        # Strategy 1: Regex-based code block removal (handles all variations)
        block_match = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?\s*```', clean)
        if block_match:
            clean = block_match.group(1).strip()
        
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            pass
        
        # Strategy 2: Extract outermost JSON object by finding first { and last }
        first_brace = clean.find('{')
        last_brace = clean.rfind('}')
        if first_brace >= 0 and last_brace > first_brace:
            try:
                return json.loads(clean[first_brace:last_brace + 1])
            except json.JSONDecodeError:
                pass
        
        # Strategy 3: Same on original text (in case stripping removed needed chars)
        first_brace = text.find('{')
        last_brace = text.rfind('}')
        if first_brace >= 0 and last_brace > first_brace:
            try:
                return json.loads(text[first_brace:last_brace + 1])
            except json.JSONDecodeError:
                pass
        
        logger.error(f"Failed to decode AI JSON after all strategies: {text[:200]}...")
        # Final fallback: strip code block markers and return cleaned text
        fallback = re.sub(r'```(?:json)?', '', text).strip().rstrip('`').strip()
        return {'cn': fallback, 'en': fallback}




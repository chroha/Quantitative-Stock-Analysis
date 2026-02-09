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
from config.settings import settings
from config.constants import DATA_CACHE_MACRO
from utils.logger import setup_logger
from utils.numeric_utils import safe_format  # Centralized numeric formatting

logger = setup_logger('macro_ai_analyst')

class MacroAIAnalyst:
    """
    AI Analyst for Macro Strategy.
    Generates bilingual commentary based on processed macro indicators.
    """
    
    def __init__(self):
        self.api_key = settings.GOOGLE_AI_KEY
        # Aligning with known working models from commentary_generator.py
        self.models = [
            "gemini-3-flash-preview",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.0-flash-exp",
            "gemini-1.5-pro",
            "gemini-1.5-flash"
        ]
        
    def generate_commentary(self, data: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate bilingual commentary using the V4.0 "Cynical CIO" approach.
        Returns: {'cn': '...', 'en': '...'}
        """
        if not self.api_key:
            print("  [AI] ERROR: Google AI Key is missing in settings.")
            return {'cn': 'AI API Key missing.', 'en': 'AI API Key missing.'}
            
        # 1. Prepare Data Buffet (Full Context + Pre-computed Signals)
        ai_context = self._prepare_v4_context(data, analysis)
        
        # DEBUG: Save context to file for user inspection
        try:
            project_root = Path(__file__).parent.parent.parent
            debug_path = project_root / DATA_CACHE_MACRO / "debug_ai_context.json"
            with open(debug_path, 'w', encoding='utf-8') as f:
                json.dump(ai_context, f, indent=2, ensure_ascii=False)
            print(f"  [AI] V4 Context saved to: {debug_path}")
        except Exception as e:
            print(f"  [AI] Failed to save debug context: {e}")

        # 2. Build V4.0 Prompt
        prompt = self._build_v4_prompt(ai_context)
        
        # 3. Call API
        for model in self.models:
            print(f"  [AI] Attempting model: {model}...")
            response_text = self._call_api(model, prompt)
            if response_text:
                print(f"  [AI] Success with {model}")
                return self._parse_response(response_text)
            else:
                print(f"  [AI] Failed with {model}")
                
        return {'cn': 'AI Generation Failed (All models).', 'en': 'AI Generation Failed (All models).'}

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
                "indices": {k: safe_format(v.get('change_1d_safe')) for k, v in assets.get('Indices', {}).items()},
                "commodities": {k: safe_format(v.get('change_1d_safe')) for k, v in assets.get('Commodities', {}).items()},
                "rates": {
                    "10y": econ.get('Rates & liquidity', {}).get('10Y Treasury', {}),
                    "hy_spread": econ.get('Rates & liquidity', {}).get('HY Spread', {})
                }
            },
            "aussie_inputs": {
                "aud_usd": assets.get('Currencies', {}).get('AUD/USD', {}),
                "copper": assets.get('Commodities', {}).get('Copper', {}),
                "china_proxy": assets.get('Currencies', {}).get('AUD/CNY', {})
            }
        }
        return context

    def _build_v4_prompt(self, context: Dict[str, Any]) -> str:
        """Construct the V4.0 Cynical/Quant Prompt."""
        
        json_str = json.dumps(context, indent=2, ensure_ascii=False)
        
        prompt = f"""
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

### OUTPUT FORMAT (Strict JSON)
Return JSON with "cn" and "en". Content in Markdown.
**IMPORTANT:** For the Chinese version ("cn"), use ONLY Chinese titles without any English in parentheses.

{{
  "cn": "### 🦅 首席视点\\n\\n**📉 核心逻辑：{{Professional Title in Chinese, e.g., 流动性压力与估值错配}}**\\n{{Paragraph: A cold, hard look at the macro regime.}}\\n\\n**🔍 结构性脆弱诊断:**\\n- **信息时滞:** {{Discuss CPI latency objectively}}\\n- **抵押品压力:** {{Analyze Gold drop as a liquidity/collateral signal}}\\n- **信用背离:** {{Discuss Credit vs Equity gap}}\\n\\n**⚖️ 情景概率:**\\n- 🔻 **去杠杆风险 (概率: X%):** {{Mechanism: Margin calls -> Selling}}\\n- 🔼 **通胀交易 (概率: Y%):** {{Mechanism: Real assets rally}}\\n\\n**🇦🇺 澳洲策略:**\\n{{Trade Idea based on Terms of Trade divergence}}\\n\\n**🛡️ 风险管理指令:**\\n1. {{Capital Preservation Step}}\\n2. {{Alpha Generation Step}}\\n3. {{Liquidity Management}}",
  "en": "..."
}}
"""
        return prompt

    def _parse_response(self, text: str) -> Dict[str, str]:
        """Parse JSON response, handling potential code blocks."""
        clean_text = text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text.strip("`")
        if clean_text.endswith("```"): # Remove trailing block format if any
             clean_text = clean_text[:-3]
             
        try:
            return json.loads(clean_text)
        except json.JSONDecodeError:
            logger.error(f"Failed to decode AI JSON: {text[:100]}...")
            # Fallback: return raw text in both if parse fails
            return {'cn': text, 'en': text}

    def _call_api(self, model_name: str, prompt: str) -> Optional[str]:
        """Call Gemini API with retry logic and graceful error handling."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.5, "responseMimeType": "application/json"}
        }
        
        max_retries = 1
        for attempt in range(max_retries + 1):
            try:
                # Keep timeout at 60s
                resp = requests.post(url, headers=headers, json=payload, timeout=60)
                
                if resp.status_code == 200:
                    result = resp.json()
                    
                    # Print Token Usage
                    usage = result.get('usageMetadata', {})
                    if usage:
                        prompt_tok = usage.get('promptTokenCount', 0)
                        cand_tok = usage.get('candidatesTokenCount', 0)
                        total_tok = usage.get('totalTokenCount', 0)
                        print(f"  [AI] Token Usage: Input={prompt_tok}, Output={cand_tok}, Total={total_tok}")
                    
                    try:
                        return result['candidates'][0]['content']['parts'][0]['text']
                    except (KeyError, IndexError):
                        print(f"  [AI] Parse Error: No candidates in {model_name} response.")
                        return None
                
                # Handle Rate Limits (429) or Server Overload (503)
                elif resp.status_code in [429, 503]:
                    code_msg = "Rate limit" if resp.status_code == 429 else "Server overloaded"
                    wait_time = 3 * (attempt + 1)
                    if attempt < max_retries:
                        print(f"  [AI] {code_msg} ({resp.status_code}). Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"  [AI] {code_msg} ({resp.status_code}). Moving to next model.")
                        return None
                
                # Handle 404
                elif resp.status_code == 404:
                    print(f"  [AI] Model {model_name} not found (404).")
                    return None
                    
                else:
                    logger.warning(f"AI Error {resp.status_code}: {resp.text}")
                    print(f"  [AI] HTTP Error {resp.status_code}")
                    return None

            except Exception as e:
                logger.error(f"AI Exception: {e}")
                print(f"  [AI] Connection failed: {e}")
                if attempt < max_retries:
                    time.sleep(2)
                    continue
            
        return None

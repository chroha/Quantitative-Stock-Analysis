"""
AI Commentary Generator.
Uses Google Gemini API to generate investment analysis reports.
"""

import json
import logging
import requests
import time
from config.settings import settings
from typing import Dict, Optional, List, Any

# Setup logger with secure formatting (already in utils.logger)
# But we can just use print or standard logging if imported
from utils.logger import setup_logger

logger = setup_logger('ai_commentary')

class CommentaryGenerator:
    """Generates AI commentary using Google Gemini."""
    
    def __init__(self):
        self.api_key = settings.GOOGLE_AI_KEY
        if not self.api_key:
            logger.warning("Google AI Key not found. AI commentary will be disabled.")
            
        self.models_to_try = [
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite"
        ]

    def generate_report(self, aggregated_data: Dict[str, Any]) -> Optional[str]:
        """
        Generate markdown report from aggregated data.
        """
        if not self.api_key:
            return None
            
        prompt = self._build_prompt(aggregated_data)
        
        for model_name in self.models_to_try:
            try:
                print(f"   [AI] Attempting model: {model_name}...")
                logger.info(f"Attempting valid model: {model_name}")
                response = self._call_api(model_name, prompt)
                if response:
                    return response
            except Exception as e:
                logger.warning(f"Model {model_name} failed: {e}")
                continue
                
        return None

    def _build_prompt(self, data: Dict[str, Any]) -> str:
        """Construct the prompt from the template."""
        # Optimize: Remove indentation to save tokens
        json_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        
        # Helper to get max score safely
        fin = data.get('financial_score', {})
        prof = fin.get('profitability', {})
        growth = fin.get('growth', {})
        cap = fin.get('capital', {})
        
        def g(d, k): 
            val = d.get(k, {}).get('max', '-')
            # If value is 0 (disabled), keep it as 0 to indicate not used
            return val
            
        stock_info = data.get('stock_info', {})
        latest_period = stock_info.get('latest_period', 'Unknown')
        history_years = stock_info.get('history_years', '?')
            
        return f"""
<stock_data>
{json_str}
</stock_data>

基于数据生成Markdown分析报告。
**核心指令：**
1. 全文所有"X"均需用`<stock_data>`真实数据替换，无数据填"-"。
2. 需要考虑分析公司所在的行业，不同行业各指标的重要性不一，特别是估值模型。
3. 结构严谨，无代码块，言简意赅。

# 📊 X 分析报告 (X)
**行业:** X | **价格:** $X
> **数据来源:** 基于最新至 {latest_period} 财报数据，涵盖过去 {history_years} 年财务历史。

## 一、财务基本面 (得分:X)
**评:** [总评]

### 1. 盈利能力 (X/X)
| 指标 | 数值 | 得分 | 解读 |
|------|------|------|----|
| ROIC | X% | X/{g(prof, 'roic')} | [解读] |
| ROE | X% | X/{g(prof, 'roe')} | [解读] |
| 营业利润率 | X% | X/{g(prof, 'op_margin')} | [解读] |
| 毛利率 | X% | X/{g(prof, 'gross_margin')} | [解读] |
| 净利率 | X% | X/{g(prof, 'net_margin')} | [解读] |

### 2. 成长性 (X/X)
| 指标 | 数值 | 得分 | 解读 |
|------|------|------|----|
| FCF增速(5年) | X% | X/{g(growth, 'fcf_cagr')} | [解读] |
| 净利增速(5年) | X% | X/{g(growth, 'ni_cagr')} | [解读] |
| 营收增速(5年) | X% | X/{g(growth, 'rev_cagr')} | [解读] |
| 盈利质量 | X | X/{g(growth, 'quality')} | [解读] |
| FCF/债务 | X | X/{g(growth, 'debt')} | [解读] |

### 3. 资本配置 (X/X)
| 指标 | 数值 | 得分 | 解读 |
|------|------|------|----|
| 回购收益率 | X% | X/{g(cap, 'buyback')} | [解读] |
| 资本支出 | X | X/{g(cap, 'capex')} | [解读] |
| 股权激励 | X | X/{g(cap, 'sbc')} | [解读] |

## 二、技术面 (得分:X)
**评:** [总评]

### 1. 趋势与动量 (X/X)
| 指标 | 数值 | 信号 | 解读 |
|------|------|------|----|
| ADX | X | [信号] | [解读] |
| 52周位置 | X% | [信号] | [解读] |
| RSI | X | [信号] | [解读] |
| MACD | X | [信号] | [解读] |

### 2. 波动与结构 (X/X)
| 指标 | 数值 | 信号 | 解读 |
|------|------|------|----|
| ATR | X% | [信号] | [解读] |
| 布林带 | - | [信号] | [解读] |
| 支撑/阻力 | - | [信号] | [解读] |

## 三、估值分析 (加权估价:$X)
**当前价:** $X | 上行空间:X%

| 模型 | 公允价 | 权重 | 偏离度 | 解读 |
|------|--------|------|--------|----|
| PE估值 | $X | X% | X% | [解读] |
| PS估值 | $X | X% | X% | [解读] |
| PB估值 | $X | X% | X% | [解读] |
| EV/EBITDA| $X | X% | X% | [解读] |
| PEG估值 | $X | X% | X% | [解读] |
| DDM模型 | $X | X% | X% | [解读] |
| DCF模型 | $X | X% | X% | [解读] |
| 分析师目标| $X | X% | X% | [解读] |

## 四、总结与建议
**核心优势:** [要点分析]
**主要风险:** [要点分析]
**综合结论:** [约200字逻辑]

> **X 操作:** [买入|持有|观望|卖出]
**理由:** [约100字分析]
"""

    def _call_api(self, model_name: str, prompt: str) -> Optional[str]:
        """Call Gemini API with retry logic."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.7,
                # Maximizing output tokens for Gemini 1.5 Series (often caps at 8192, but 1.5 Pro/Flash can do more)
                "maxOutputTokens": 65536 
            }
        }
        
        max_retries = 1
        for attempt in range(max_retries):
            try:
                # Keep timeout at 120s to allow for long generations
                response = requests.post(url, json=payload, timeout=120)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Extract usage metadata
                    usage = result.get("usageMetadata", {})
                    total_tokens = usage.get("totalTokenCount", 0)
                    print(f"   [AI] Success! Model: {model_name} | Tokens Used: {total_tokens}")
                    
                    candidates = result.get("candidates", [])
                    if candidates:
                        candidate = candidates[0]
                        finish_reason = candidate.get("finishReason", "")
                        
                        # Warn if truncated
                        if finish_reason == "MAX_TOKENS":
                            logger.warning(f"Response truncated (MAX_TOKENS). Consider increasing limit.")
                            print(f"   [WARN] Response may be incomplete (hit token limit)")
                        
                        return candidate.get("content", {}).get("parts", [])[0].get("text", "")
                    return None # Empty response
                
                # Handle Rate Limits (429) or Server Overload (503)
                if response.status_code in [429, 503]:
                    code_msg = "Rate limit" if response.status_code == 429 else "Server overloaded"
                    wait_time = 5 * (attempt + 1)
                    print(f"   [AI] {code_msg} ({response.status_code}) on {model_name}. Retrying in {wait_time}s...")
                    logger.warning(f"{code_msg} (429/503) on {model_name}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                # Handle 404
                if response.status_code == 404:
                    print(f"   [AI] Model {model_name} not found.")
                    logger.warning(f"Model {model_name} not found (404).")
                    return None
                    
                logger.warning(f"API Error {model_name} ({response.status_code}): {response.text}")
                return None
                
            except Exception as e:
                logger.warning(f"Exception calling {model_name}: {e}")
                
                # If specific timeout error, log it clearly
                if "timed out" in str(e).lower():
                     print(f"   [AI] Request timed out (took >120s). Retrying...")
                
                if attempt < max_retries - 1:
                    time.sleep(5) # Standard wait for network errors
                    continue
        return None

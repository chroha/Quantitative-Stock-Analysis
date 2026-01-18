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

## 一、财务基本面 (得分:X)
**评:** [50字总评]

### 1. 盈利能力 (X/X)
| 指标 | 数值 | 得分 | 评 |
|------|------|------|----|
| ROIC | X% | X/{g(prof, 'roic')} | [评] |
| ROE | X% | X/{g(prof, 'roe')} | [评] |
| 营业利润率 | X% | X/{g(prof, 'op_margin')} | [评] |
| 毛利率 | X% | X/{g(prof, 'gross_margin')} | [评] |
| 净利率 | X% | X/{g(prof, 'net_margin')} | [评] |

### 2. 成长性 (X/X)
| 指标 | 数值 | 得分 | 评 |
|------|------|------|----|
| FCF增速(5年) | X% | X/{g(growth, 'fcf_cagr')} | [评] |
| 净利增速(5年) | X% | X/{g(growth, 'ni_cagr')} | [评] |
| 营收增速(5年) | X% | X/{g(growth, 'rev_cagr')} | [评] |
| 盈利质量 | X | X/{g(growth, 'quality')} | [评] |
| FCF/债务 | X | X/{g(growth, 'debt')} | [评] |

### 3. 资本配置 (X/X)
| 指标 | 数值 | 得分 | 评 |
|------|------|------|----|
| 回购收益率 | X% | X/{g(cap, 'buyback')} | [评] |
| 资本支出 | X | X/{g(cap, 'capex')} | [评] |
| 股权激励 | X | X/{g(cap, 'sbc')} | [评] |

## 二、技术面 (得分:X)
**评:** [50字总评]

### 1. 趋势与动量 (X/X)
| 指标 | 数值 | 信号 | 评 |
|------|------|------|----|
| ADX | X | [信号] | [评] |
| 52周位置 | X% | [信号] | [评] |
| RSI | X | [信号] | [评] |
| MACD | X | [信号] | [评] |

### 2. 波动与结构 (X/X)
| 指标 | 数值 | 信号 | 评 |
|------|------|------|----|
| ATR | X% | [信号] | [评] |
| 布林带 | - | [信号] | [评] |
| 支撑/阻力 | - | [信号] | [评] |

## 三、估值分析 (公允价:$X | 上行空间:X%)
**当前价:** $X

| 模型 | 公允价 | 权重 | 偏离度 | 评 |
|------|--------|------|--------|----|
| PE估值 | $X | X% | X% | [评] |
| PS估值 | $X | X% | X% | [评] |
| PB估值 | $X | X% | X% | [评] |
| EV/EBITDA| $X | X% | X% | [评] |
| PEG估值 | $X | X% | X% | [评] |
| DDM模型 | $X | X% | X% | [评] |
| DCF模型 | $X | X% | X% | [评] |
| 分析师目标| $X | X% | X% | [评] |

## 四、总结与建议
**核心优势:** [3点短语]
**主要风险:** [3点短语]
**综合结论:** [约200字逻辑]

> **X 操作:** [买入|持有|观望|卖出]
**理由:** [100字内]
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
                "maxOutputTokens": 16384  # Increased for complete reports
            }
        }
        
        max_retries = 1
        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=payload, timeout=60)
                
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
                
                # Handle Rate Limits (429)
                if response.status_code == 429:
                    wait_time = 5 * (attempt + 1)
                    print(f"   [AI] Rate limited on {model_name}. Retrying in {wait_time}s...")
                    logger.warning(f"Rate limited (429) on {model_name}. Retrying in {wait_time}s...")
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
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
        return None

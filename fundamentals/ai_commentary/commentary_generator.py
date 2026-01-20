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
from fundamentals.ai_commentary.prompts import build_analysis_prompt

logger = setup_logger('ai_commentary')

class CommentaryGenerator:
    """Generates AI commentary using Google Gemini."""
    
    def __init__(self):
        self.api_key = settings.GOOGLE_AI_KEY
        if not self.api_key:
            logger.warning("Google AI Key not found. AI commentary will be disabled.")
            
        self.models_to_try = [
            "gemini-3-flash-preview",
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
        return build_analysis_prompt(data)








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

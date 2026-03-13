"""
LLM Client Module
=================

Infrastructure layer for connecting to Generative AI providers (Google Gemini).
Handles authentication, retries, and model selection.
Agnostic to the content being generated.
"""

import logging
import requests
import time
from typing import Optional, List
from config.settings import settings
from utils.logger import setup_logger

logger = setup_logger('llm_client')

class LLMClient:
    """
    Client for interacting with Google Gemini API.
    """
    
    DEFAULT_MODELS = [
        "gemini-3-flash-preview",
        "gemini-3.1-flash-lite-preview",
        "gemini-2.5-flash"
    ]

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GOOGLE_AI_KEY
        self.last_generation_info = None  # To track token usage and model stats
        if not self.api_key:
            logger.warning("Google AI Key not provided. AI generation will be disabled.")

    def generate_text(self, prompt: str, model_hint: Optional[str] = None) -> Optional[str]:
        """
        Generate text from a prompt using reliable models with fallback.
        """
        if not self.api_key:
            return None
            
        # Prioritize hinted model if provided
        models = self.DEFAULT_MODELS.copy()
        if model_hint and model_hint not in models:
            models.insert(0, model_hint)
        elif model_hint:
            # Move hint to front
            models.remove(model_hint)
            models.insert(0, model_hint)
        
        for model in models:
            try:
                response = self._call_api(model, prompt)
                if response:
                    return response
            except Exception as e:
                logger.warning(f"Model {model} failed due to timeout or error. Attempting next fallback model... Details: {e}")
                continue
                
        logger.error("All models failed to generate valid text.")
        return None

    def _call_api(self, model_name: str, prompt: str) -> Optional[str]:
        """Call Gemini API with retry logic."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 65536 
            }
        }
        
        max_retries = 1
        for attempt in range(max_retries + 1):
            try:
                # Reduced timeout to 45 seconds for faster failover
                response = requests.post(url, json=payload, timeout=45)
                
                if response.status_code == 200:
                    result = response.json()
                    candidates = result.get("candidates", [])
                    if candidates:
                        candidate = candidates[0]
                        finish_reason = candidate.get("finishReason", "UNKNOWN")
                        
                        if finish_reason not in ["", "STOP", "MAX_TOKENS"]:
                            logger.warning(f"Generation stopped: {finish_reason} ({model_name})")
                            return None

                        content_parts = candidate.get("content", {}).get("parts", [])
                        if content_parts:
                            text = content_parts[0].get("text", "")
                            if text:
                                # Track token usage and model info on success
                                usage = result.get("usageMetadata", {})
                                self.last_generation_info = {
                                    'model_name': model_name,
                                    'total_tokens': usage.get("totalTokenCount", 0),
                                    'prompt_tokens': usage.get("promptTokenCount", 0),
                                    'candidates_tokens': usage.get("candidatesTokenCount", 0)
                                }
                                return text
                        return None
                    return None
                
                # Retry on Rate Limit (429) or Service Unavailable (503)
                if response.status_code in [429, 503]:
                    time.sleep(5 * (attempt + 1))
                    continue
                
                # 404 means model not found, silent fail to next
                if response.status_code == 404:
                    return None
                    
                logger.warning(f"API Error {model_name} ({response.status_code}): {response.text[:200]}")
                return None
                
            except Exception as e:
                logger.warning(f"Exception calling {model_name}: {e}")
                if attempt < max_retries:
                    time.sleep(2)
                    continue
        return None

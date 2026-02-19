"""
Stock AI Analyst
================

Domain-specific analyst for individual stock reports.
Uses generic LLMClient for generation and ContextBuilder for data prep.
"""

from typing import Dict, Any, Optional
from fundamentals.reporting.llm_client import LLMClient
from fundamentals.stock.context_builder import ContextBuilder
from fundamentals.stock.prompts import build_analysis_prompt, build_executive_summary_prompt

class StockAIAnalyst:
    """
    Orchestrates the generation of AI-driven stock analysis reports.
    """
    
    def __init__(self):
        self.client = LLMClient()
        self.builder = ContextBuilder()

    def generate_report(self, data_bundle: Dict[str, Any]) -> Optional[str]:
        """
        Generate a full comprehensive stock analysis report.
        Args:
            data_bundle: Processed AI Context (from DataAggregator).
            
        Note: The input 'data_bundle' is expected to be the SIMPLIFIED context, 
        not the raw bundle, if called from run_analysis.py.
        """
        # 2. Construct Prompt
        prompt = build_analysis_prompt(data_bundle)
        
        # 3. Generate Text
        return self.client.generate_text(prompt)

    def generate_executive_summary(self, data_bundle: Dict[str, Any]) -> Optional[str]:
        """
        Generate a concise executive summary.
        """
        prompt = build_executive_summary_prompt(data_bundle)
        return self.client.generate_text(prompt, model_hint="gemini-1.5-flash")



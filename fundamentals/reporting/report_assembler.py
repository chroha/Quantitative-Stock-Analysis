"""
Report Assembler Module
=======================

Centralizes the assembly of AI-generated reports.
Handles uniform formatting of Disclaimers, Appendices, and Headers across Stock and Macro reports.
"""

from datetime import datetime
from typing import Optional

class ReportAssembler:
    """
    Static utility class for assembling final markdown reports.
    """

    @staticmethod
    def get_disclaimer(lang: str = 'bilingual') -> str:
        """
        Returns the standardized disclaimer text.
        
        Args:
            lang: 'en', 'cn', or 'bilingual' (default)
        """
        en_text = """
**English:**
This report is for informational and educational purposes only and does not constitute financial product advice. It has been prepared without taking into account your personal objectives, financial situation, or needs. Past performance is not a reliable indicator of future performance. You should consider seeking independent professional advice before making any investment decisions.
"""
        cn_text = """
**中文：**
本报告仅供信息参考及教育用途，不构成任何金融产品建议。本报告内容在编制时未考虑您的个人投资目标、财务状况或特定需求。历史表现并非未来表现的可靠指标。在做出任何投资决策之前，您应考虑寻求独立的专业咨询。
"""
        
        header = "\n\n---\n\n### Disclaimer / 免责声明\n"
        
        if lang == 'en':
            return header + en_text
        elif lang == 'cn':
            return header + cn_text
        else:
            return header + en_text + "\n" + cn_text

    @staticmethod
    def assemble_stock_report(ai_content: str, appendix: Optional[str] = None) -> str:
        """
        Assemble a complete Stock Analysis Report.
        
        Structure:
        1. AI Content (Main Report)
        2. Appendix (Raw Data)
        3. Disclaimer
        """
        components = []
        
        # 1. Main Content
        if ai_content:
            components.append(ai_content.strip())
        else:
            components.append("# Analysis Report (Generation Failed)\n\n> [!WARNING]\n> AI commentary could not be generated.")

        # 2. Appendix
        if appendix:
            components.append("\n\n" + appendix.strip())
            
        # 3. Disclaimer
        components.append(ReportAssembler.get_disclaimer('bilingual'))
        
        return "\n".join(components)

    @staticmethod
    def assemble_macro_report(markdown_content: str) -> str:
        """
        Assemble a complete Macro Strategy Report.
        
        Structure:
        1. Generated Markdown Dashboard (includes AI commentary)
        2. Disclaimer
        """
        components = []
        
        if markdown_content:
            components.append(markdown_content.strip())
            
        components.append(ReportAssembler.get_disclaimer('bilingual'))
        
        return "\n".join(components)

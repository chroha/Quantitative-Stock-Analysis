from typing import Dict, Any
from .cycle_analyzer import CycleAnalyzer
from .risk_assessor import RiskAssessor
from .valuation_allocator import ValuationAllocator

class MacroReportGenerator:
    """Generates comprehensive macro analysis report."""
    
    def __init__(self):
        self.cycle_analyzer = CycleAnalyzer()
        self.risk_assessor = RiskAssessor()
        self.valuation_allocator = ValuationAllocator()
        
    def generate_report(self, data: Dict[str, Any]) -> str:
        """
        Generate text report from macro data.
        
        Args:
            data: Macro data snapshot
            
        Returns:
            Formatted text report
        """
        # Run analyses
        cycle = self.cycle_analyzer.analyze(data)
        risk = self.risk_assessor.analyze(data)
        valuation = self.valuation_allocator.analyze(data)
        
        # Build Report
        lines = []
        lines.append("=" * 60)
        lines.append("MACRO STRATEGY REPORT")
        lines.append(f"Date: {data.get('snapshot_date', 'Unknown')}")
        lines.append("=" * 60)
        
        # 1. Economic Cycle
        lines.append(f"\n1. ECONOMIC CYCLE: {cycle['phase']}")
        lines.append(f"   Score: {cycle['score']} (Spread + Inflation + Employment)")
        lines.append("   Key Drivers:")
        for detail in cycle['details']:
            lines.append(f"   - {detail}")
            
        # 2. Risk Environment
        lines.append(f"\n2. RISK ENVIRONMENT: {risk['environment']}")
        lines.append(f"   Position Sizing: {risk['position_sizing']}")
        lines.append("   Key Drivers:")
        for detail in risk['details']:
            lines.append(f"   - {detail}")
            
        # 3. Valuation & Allocation
        lines.append(f"\n3. VALUATION & ALLOCATION")
        lines.append(f"   Equity/Bond: {valuation['equity_bond_allocation']}")
        lines.append(f"   Geographic:  {valuation['geographic_bias']}")
        if valuation['erp'] is not None:
            lines.append(f"   ERP:         {valuation['erp']*100:.2f}%")
        lines.append("   details:")
        for detail in valuation['details']:
            lines.append(f"   - {detail}")
            
        # Warnings
        if 'trailing_proxy' in valuation['pe_source']:
            lines.append("\n⚠️  NOTE: Valuation uses Trailing PE as Forward Proxy (Forward PE unavailable).")
            
        lines.append("=" * 60)
        
        return "\n".join(lines)

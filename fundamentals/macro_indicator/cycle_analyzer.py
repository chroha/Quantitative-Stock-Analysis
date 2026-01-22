from typing import Dict, Any, Optional
from enum import Enum

class EconomicPhase(Enum):
    RECOVERY = "Recovery"
    EXPANSION = "Expansion" 
    NEUTRAL_EXPANSION = "Neutral Expansion"
    OVERHEATING = "Overheating"
    SLOWDOWN = "Slowdown"
    RECESSION_WATCH = "Recession Watch"

class CycleAnalyzer:
    """Analyzes economic cycle positioning."""
    
    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze economic cycle based on yield curve, inflation, and employment.
        
        Args:
            data: Macro data snapshot
            
        Returns:
            Analysis result dictionary
        """
        treasury = data.get('treasury_yields', {})
        inflation = data.get('inflation', {})
        employment = data.get('employment', {})
        
        # 1. Yield Spread (10Y - 2Y)
        yield_spread = treasury.get('yield_curve_10y_2y')
        
        # 2. YoY Inflation Calculation
        cpi_latest = inflation.get('CPI_latest')
        cpi_history = inflation.get('CPI_history', [])
        cpi_yoy = None
        
        if cpi_history and len(cpi_history) >= 13:
            # Sort by date (oldest first) just in case
            sorted_hist = sorted(cpi_history, key=lambda x: x['date'])
            # Compare latest with 12 months ago
            cpi_last_year = sorted_hist[-13]['value']
            if cpi_last_year > 0:
                cpi_yoy = (cpi_latest / cpi_last_year) - 1.0
        
        # 3. Unemployment
        unrate = employment.get('UNRATE_current')
        
        # Scoring Logic
        score = 0
        details = []
        
        # Spread Logic (Weight: 2)
        if yield_spread is not None:
            if yield_spread > 0.5:
                score += 2
                details.append("Yield Spread Healthy (>0.5%)")
            elif yield_spread < 0:
                score -= 2
                details.append("Yield Curve Inverted (<0%)")
            else:
                score += 1 # 0-0.5 is still positive
                details.append("Yield Spread Positive but Low")
                
        # Inflation Logic (Weight: 1)
        if cpi_yoy is not None:
            cpi_pct = cpi_yoy * 100
            if cpi_pct < 2.0:
                score -= 1 # Deflation risk? Or just cool?
                details.append(f"Inflation Low ({cpi_pct:.1f}%)")
            elif cpi_pct <= 3.0:
                score += 1 # Goldilocks
                details.append(f"Inflation Moderate ({cpi_pct:.1f}%)")
            elif cpi_pct > 4.0:
                score -= 1 # Overheating
                details.append(f"Inflation High ({cpi_pct:.1f}%)")
            else:
                # 3-4% Neutral/Warning
                details.append(f"Inflation Elevated ({cpi_pct:.1f}%)")
                
        # Unemployment Logic (Weight: 1)
        if unrate is not None:
            if unrate < 5.0:
                score += 1
                details.append(f"Unemployment Low ({unrate:.1f}%)")
            elif unrate > 6.0:
                score -= 2
                details.append(f"Unemployment High ({unrate:.1f}%)")
        
        # Determine Phase
        # Max score approx: 2 (spread) + 1 (cpi) + 1 (unrate) = 4
        # Min score: -2 -1 -2 = -5
        
        if score >= 3:
            phase = EconomicPhase.NEUTRAL_EXPANSION
        elif score >= 1:
            phase = EconomicPhase.EXPANSION
        elif score >= -1:
            phase = EconomicPhase.SLOWDOWN
        else:
            phase = EconomicPhase.RECESSION_WATCH
            
        # Refined Overheating check
        if cpi_yoy and cpi_yoy > 0.04 and unrate and unrate < 4.0:
            phase = EconomicPhase.OVERHEATING
            
        return {
            "phase": phase.value,
            "score": score,
            "details": details,
            "metrics": {
                "spread": yield_spread,
                "cpi_yoy": cpi_yoy,
                "unrate": unrate
            }
        }

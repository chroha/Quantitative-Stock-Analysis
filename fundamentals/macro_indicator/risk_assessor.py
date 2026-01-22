from typing import Dict, Any

class RiskAssessor:
    """Analyzes market risk environment."""
    
    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze risk based on VIX, Dollar, and FX.
        
        Args:
            data: Macro data snapshot
            
        Returns:
            Risk analysis dictionary
        """
        market_risk = data.get('market_risk', {})
        currencies = data.get('currencies', {})
        
        # VIX Analysis
        vix = market_risk.get('VIX_current')
        vix_trend = market_risk.get('VIX_trend_direction', 'stable')
        
        # DXY Analysis
        dxy = currencies.get('DXY_current')
        
        # USD/JPY (Carry Trade)
        usdjpy = currencies.get('USDJPY_current')
        
        # Base Risk Score (0 = Off, 3 = High Risk)
        risk_score = 1 # Start at medium-low
        details = []
        
        # VIX Logic
        if vix:
            if vix < 15:
                details.append("VIX Low (<15)")
            elif vix > 20:
                risk_score += 1
                details.append("VIX Elevated (>20)")
            
            if vix_trend == "rising":
                risk_score += 1
                details.append("VIX Trend Rising")
        
        # DXY Logic
        if dxy and dxy > 100:
            # Strong dollar often means risk-off (flight to safety)
            # But could also just be US strong growth. 
            # User said: >100 = Non-Risk Off? Wait. 
            # User plan: "DXY Level (> 100 Risk Off)"
            # User prompt: "DXY 98.76 (<100=Non-Risk Off, flows to emerging)"
            # So > 100 adds to risk.
            risk_score += 1
            details.append("Dollar Strong (>100)")
            
        # Carry Trade Bonus (Risk-ON signal)
        # User: "USD/JPY > 150 -1 risk if risk-on"
        if usdjpy and usdjpy > 150:
            risk_score -= 1
            details.append("Carry Trade Active (USD/JPY > 150) -> Risk-ON Bonus")
            
        # Clamp score 0-3
        risk_score = max(0, min(3, risk_score))
        
        # Map to Environment
        env_map = {
            0: "Risk On (Low Risk)",
            1: "Neutral (Medium Risk)",
            2: "Cautious (High Risk)",
            3: "Risk Off (Extreme Risk)"
        }
        environment = env_map.get(risk_score, "Unknown")
        
        # Position Sizing
        pos_map = {
            0: "100%",
            1: "70-80%", # User suggestion for Medium
            2: "40-50%",
            3: "0-20% (Cash limit)"
        }
        allocation = pos_map.get(risk_score, "Unknown")
        
        return {
            "environment": environment,
            "risk_score": risk_score,
            "position_sizing": allocation,
            "details": details,
            "metrics": {
                "vix": vix,
                "dxy": dxy,
                "usdjpy": usdjpy
            }
        }

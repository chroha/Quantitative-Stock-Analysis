from typing import Dict, Any

class ValuationAllocator:
    """Analyzes valuation and suggests asset allocation."""
    
    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze valuation, ERP, and regional bias.
        
        Args:
            data: Macro data snapshot
            
        Returns:
            Allocation suggestion dictionary
        """
        equity = data.get('equity_market', {})
        treasury = data.get('treasury_yields', {})
        currencies = data.get('currencies', {})
        
        # Metrics
        pe = equity.get('SPX_forward_pe')
        yield_10y = treasury.get('GS10_current')
        aud_usd = currencies.get('AUDUSD_current')
        
        details = []
        equity_allocation = "60/40 (Neutral)"
        geo_bias = "Neutral"
        
        # ERP Calculation
        erp = None
        if pe and yield_10y and pe > 0:
            earnings_yield = 1 / pe
            risk_free = yield_10y / 100.0
            erp = earnings_yield - risk_free
            
        # Asset Allocation Logic
        if erp is not None:
            erp_pct = erp * 100
            if erp_pct < 0:
                equity_allocation = "Underweight Stocks / Overweight Bonds"
                details.append(f"ERP Negative ({erp_pct:.2f}%) -> Stocks Expensive")
            elif erp_pct > 3.0: # User said: ">3% stock bias (aggressive)"
                equity_allocation = "Overweight Stocks (Aggressive)"
                details.append(f"ERP Attractive ({erp_pct:.2f}%)")
            else:
                equity_allocation = "Neutral (60/40)"
                details.append(f"ERP Fair ({erp_pct:.2f}%)")
                
        # Geographic Bias
        # AUD/USD logic: < 0.7 -> AUD Weak -> Buy Local (Cheaper for USD holders? Or hedge?)
        # User: "AUD/USD < 0.7 (Weak IDR/AUD) -> Local Asset Bias (Hedge)."
        # User: "AUD/USD > 0.8 -> US Bias (Unhedged)."
        if aud_usd:
            if aud_usd < 0.70:
                geo_bias = "Local Bias (Australia/Emerging)"
                details.append(f"AUD Weak ({aud_usd:.4f}) -> Prioritize Local Assets")
            elif aud_usd > 0.80:
                geo_bias = "US Bias"
                details.append(f"AUD Strong ({aud_usd:.4f}) -> Prioritize US Assets")
            else:
                geo_bias = "Global Diversified"
        
        return {
            "equity_bond_allocation": equity_allocation,
            "geographic_bias": geo_bias,
            "erp": erp,
            "details": details,
            "pe_source": equity.get('SPX_forward_pe_source', 'unknown')
        }

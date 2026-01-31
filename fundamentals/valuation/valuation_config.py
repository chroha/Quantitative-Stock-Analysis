"""
Valuation Configuration
Sector-specific weights for different valuation methods.
"""

# Sector-specific method weights
# Each sector uses different valuation approaches based on industry characteristics
# 10 Models: pe, pb, ps, ev_ebitda, dcf, ddm, graham, peter_lynch, peg, analyst
SECTOR_WEIGHTS = {
    "Technology": {
        # Core logic: Growth pricing > Revenue pricing > Earnings pricing
        "peg": 0.15,           # Core growth metric, corrects pure PE limitations
        "ps": 0.20,            # Revenue growth critical for tech (SaaS/Cloud)
        "dcf": 0.15,           # Long-term cash flow matters, but don't over-rely
        "peter_lynch": 0.15,   # Suitable for mature tech (FAANG-type)
        "pe": 0.15,            # Traditional earnings valuation
        "ev_ebitda": 0.10,     # Reference metric
        "analyst": 0.10,       # Innovation-driven, market expectations important
        "ddm": 0.00,           # Tech rarely pays dividends
        "pb": 0.00,            # Asset-light, book value irrelevant
        "graham": 0.00         # Too conservative for high-growth stocks
    },
    
    "Healthcare": {
        # Core logic: Growth potential + Cash flow stability
        "peg": 0.15,           # Biotech/Pharma must consider growth rate
        "dcf": 0.15,           # Relatively stable cash flows
        "pe": 0.15,            # Standard valuation metric
        "ev_ebitda": 0.15,     # Key metric for pharma manufacturing
        "analyst": 0.10,       # Clinical trial results highly influential
        "peter_lynch": 0.10,   # Suitable for stable healthcare stocks
        "ps": 0.10,            # Revenue scale reference
        "graham": 0.05,        # Applicable for mature pharma companies
        "ddm": 0.05,           # Some big pharma pays dividends
        "pb": 0.00             # Not asset-intensive
    },
    
    "Financials": {
        # Core logic: Book value + Dividends + Value investing
        "pb": 0.30,            # Core metric (bank/insurance book value)
        "ddm": 0.20,           # Financials are major dividend payers
        "graham": 0.15,        # Graham method ideal for asset safety
        "pe": 0.15,            # Cyclical-adjusted PE needed
        "analyst": 0.15,       # Regulatory policy impact significant
        "dcf": 0.00,           # Financial cash flows hard to predict
        "peter_lynch": 0.05,   # Can find undervalued bank stocks
        "peg": 0.00,           # Growth rate not key for financials
        "ps": 0.00,            # Revenue less meaningful for finance
        "ev_ebitda": 0.00      # Invalid metric for financials
    },
    
    "Consumer Discretionary": {
        # Core logic: Earnings quality + Growth + Lynch preference
        "pe": 0.20,            # Primary valuation metric
        "peter_lynch": 0.15,   # Lynch's favorite sector ("buy what you know")
        "ps": 0.15,            # Revenue growth important
        "ev_ebitda": 0.15,     # Enterprise value assessment
        "peg": 0.10,           # Growth reference
        "dcf": 0.10,           # Cash flow affected by economic cycle
        "graham": 0.05,        # Applicable for traditional retail
        "analyst": 0.05,       # Consumer trend forecasting
        "ddm": 0.05,           # Some mature companies pay dividends
        "pb": 0.00             # Mostly asset-light
    },
    
    "Consumer Staples": {
        # Core logic: Stable dividends + Value investing + Defensive
        "pe": 0.20,            # Primary metric
        "ddm": 0.20,           # Stable high dividends
        "graham": 0.15,        # Defensive value stocks, stable assets
        "dcf": 0.15,           # Extremely stable cash flows
        "ev_ebitda": 0.10,     # Enterprise value reference
        "analyst": 0.10,       # Market share forecasting
        "ps": 0.05,            # Limited revenue growth
        "peter_lynch": 0.05,   # Low growth, less suitable
        "pb": 0.00,            # Limited reference value
        "peg": 0.00            # Slow growth
    },
    
    "Energy": {
        # Core logic: Enterprise value + Cycle prediction
        "ev_ebitda": 0.35,     # Core metric (capital-intensive + high depreciation)
        "analyst": 0.20,       # Highly cyclical, oil price expectations key
        "graham": 0.10,        # Traditional energy asset value floor
        "dcf": 0.10,           # Cash flow volatile but needed
        "ddm": 0.10,           # Traditional energy pays high dividends
        "pe": 0.05,            # Cyclicality causes PE volatility
        "pb": 0.05,            # Asset reference
        "ps": 0.05,            # Revenue affected by oil prices
        "peter_lynch": 0.00,   # Not suitable for cyclicals
        "peg": 0.00            # Unstable growth
    },
    
    "Industrials": {
        # Core logic: Enterprise value + Asset quality + Order expectations
        "ev_ebitda": 0.25,     # Core metric for heavy-asset sector
        "pe": 0.20,            # Primary earnings metric
        "graham": 0.15,        # Heavy equipment, Graham method suitable
        "analyst": 0.10,       # Order expectations and economic cycle
        "dcf": 0.10,           # Relatively stable cash flows
        "ps": 0.05,            # Revenue scale reference
        "pb": 0.05,            # Asset value reference
        "peter_lynch": 0.05,   # Can capture cycle bottom opportunities
        "ddm": 0.05,           # Some industrials pay dividends
        "peg": 0.00            # Unstable growth
    },
    
    "Materials": {
        # Core logic: Enterprise value + Asset safety
        "ev_ebitda": 0.30,     # Core metric (heavy assets + high debt)
        "graham": 0.20,        # Strong cyclical + heavy assets, high Graham weight
        "pe": 0.15,            # Cyclical PE
        "pb": 0.15,            # Tangible assets important
        "analyst": 0.10,       # Commodity price expectations
        "dcf": 0.10,           # Cash flow volatility
        "ddm": 0.00,           # Unstable dividends
        "ps": 0.00,            # Revenue highly volatile
        "peter_lynch": 0.00,   # Not suitable
        "peg": 0.00            # Unstable growth
    },
    
    "Real Estate": {
        # Core logic: Dividend yield + Asset value (NAV)
        "ddm": 0.30,           # REITs core is dividends (legally required)
        "pb": 0.20,            # NAV (Net Asset Value) key metric
        "analyst": 0.15,       # Interest rate expectations highly impactful
        "graham": 0.15,        # Substantial tangible assets, value investing
        "dcf": 0.10,           # Rental cash flow forecasting
        "pe": 0.10,            # Note: Use P/FFO instead of P/E
        "ev_ebitda": 0.00,     # Not applicable for real estate
        "peter_lynch": 0.00,   # Limited growth
        "peg": 0.00,           # Not applicable
        "ps": 0.00             # Revenue not relevant
    },
    
    "Utilities": {
        # Core logic: Dividends are king + Defensive value
        "ddm": 0.35,           # Highest weight (stable high dividends)
        "graham": 0.20,        # Heavy utility assets, Graham effective
        "pe": 0.15,            # Stable earnings
        "dcf": 0.15,           # Highly predictable cash flows
        "analyst": 0.10,       # Regulatory policy impact
        "pb": 0.05,            # Asset reference
        "ev_ebitda": 0.00,     # Limited reference value
        "peter_lynch": 0.00,   # Low growth
        "peg": 0.00,           # Very limited growth
        "ps": 0.00             # Revenue not relevant
    },
    
    "Communication Services": {
        # Core logic: Bifurcated sector (Telecom operators vs Internet media)
        "pe": 0.20,            # Primary metric
        "ev_ebitda": 0.15,     # Core metric for telecom operators
        "ps": 0.15,            # Internet companies focus on revenue
        "peg": 0.15,           # Media/gaming growth potential
        "dcf": 0.15,           # Cash flow assessment
        "analyst": 0.10,       # User growth expectations
        "ddm": 0.05,           # Telecom operators pay dividends
        "peter_lynch": 0.05,   # Partially applicable
        "graham": 0.00,        # Not very applicable
        "pb": 0.00             # Mostly asset-light
    }
}


def get_sector_weights(sector: str) -> dict:
    """
    Get valuation method weights for a given sector.
    
    Args:
        sector: GICS sector name
        
    Returns:
        Dictionary of method weights, or empty dict if sector not found
    """
    return SECTOR_WEIGHTS.get(sector, {})


def get_all_sectors() -> list:
    """Get list of all supported sectors."""
    return list(SECTOR_WEIGHTS.keys())

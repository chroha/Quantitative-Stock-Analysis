"""
Valuation Configuration
Sector-specific weights for different valuation methods.
"""

# Sector-specific method weights
# Each sector uses different valuation approaches based on industry characteristics
SECTOR_WEIGHTS = {
    "Technology": {
        "pe": 0.30,
        "ps": 0.20,
        "ev_ebitda": 0.15,
        "dcf": 0.15,
        "analyst": 0.20
    },
    "Healthcare": {
        "pe": 0.30,
        "ev_ebitda": 0.20,
        "analyst": 0.20,
        "dcf": 0.15,
        "ps": 0.10,
        "ddm": 0.05
    },
    "Financials": {
        "pb": 0.35,
        "pe": 0.25,
        "analyst": 0.20,
        "ddm": 0.15,
        "dcf": 0.05
    },
    "Consumer Discretionary": {
        "pe": 0.30,
        "ev_ebitda": 0.20,
        "ps": 0.15,
        "analyst": 0.15,
        "dcf": 0.10,
        "ddm": 0.05,
        "pb": 0.05
    },
    "Consumer Staples": {
        "pe": 0.30,
        "ddm": 0.20,
        "dcf": 0.15,
        "analyst": 0.10,
        "ps": 0.10,
        "ev_ebitda": 0.10,
        "pb": 0.05
    },
    "Energy": {
        "ev_ebitda": 0.40,
        "pe": 0.15,
        "analyst": 0.15,
        "ddm": 0.10,
        "dcf": 0.10,
        "ps": 0.05,
        "pb": 0.05
    },
    "Industrials": {
        "pe": 0.30,
        "ev_ebitda": 0.25,
        "analyst": 0.15,
        "ps": 0.10,
        "dcf": 0.10,
        "pb": 0.05,
        "ddm": 0.05
    },
    "Materials": {
        "ev_ebitda": 0.30,
        "pe": 0.25,
        "analyst": 0.15,
        "pb": 0.10,
        "dcf": 0.10,
        "ddm": 0.05,
        "ps": 0.05
    },
    "Real Estate": {
        "ddm": 0.30,
        "pb": 0.20,
        "pe": 0.20,
        "analyst": 0.20,
        "dcf": 0.10
    },
    "Utilities": {
        "ddm": 0.35,
        "pe": 0.25,
        "analyst": 0.10,
        "pb": 0.10,
        "dcf": 0.10,
        "ps": 0.05,
        "ev_ebitda": 0.05
    },
    "Communication Services": {
        "pe": 0.30,
        "ps": 0.20,
        "ev_ebitda": 0.20,
        "analyst": 0.15,
        "dcf": 0.10,
        "ddm": 0.05
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

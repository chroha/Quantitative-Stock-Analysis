"""
Absolute threshold configurations for Tier 3 metrics.
Cross-industry standards that apply regardless of sector.
"""

# Growth metrics - CAGR thresholds
TIER3_THRESHOLDS = {
    # FCF CAGR (5-year, time-weighted)
    'fcf_cagr_5y': {
        'score_100': 0.25,   # 25%+ growth = excellent
        'score_75': 0.15,    # 15% growth = good
        'score_50': 0.10,    # 10% growth = acceptable
        'score_25': 0.05,    # 5% growth = poor
        'score_0': 0.00      # zero/negative = failing
    },
    
    # Revenue CAGR (5-year, time-weighted)
    'revenue_cagr_5y': {
        'score_100': 0.20,   # 20%+ = excellent
        'score_75': 0.15,    # 15% = good
        'score_50': 0.10,    # 10% = acceptable
        'score_25': 0.05,    # 5% = poor
        'score_0': 0.00
    },
    
    # Net Income CAGR (5-year, time-weighted)
    'net_income_cagr_5y': {
        'score_100': 0.25,   # 25%+ = excellent
        'score_75': 0.15,    # 15% = good
        'score_50': 0.10,    # 10% = acceptable
        'score_25': 0.05,    # 5% = poor
        'score_0': 0.00
    },
    
    # Earnings Quality (OCF/NI, 3-year average)
    'earnings_quality_3y': {
        'score_100': 1.30,   # 30%+ premium (OCF > NI)
        'score_75': 1.10,    # 10%+ premium
        'score_50': 0.90,    # Within 10%
        'score_25': 0.70,    # 30% discount
        'score_0': 0.50      # <50% conversion
    },
    
    # FCF to Debt Ratio
    'fcf_to_debt_ratio': {
        'score_100': 0.50,   # >50% = strong coverage
        'score_75': 0.30,    # >30% = good
        'score_50': 0.15,    # >15% = acceptable
        'score_25': 0.05,    # >5% = weak
        'score_0': 0.00      # no coverage
    },
    
    # SBC Impact (% of OCF, 3-year average)
    'sbc_impact_3y': {
        'score_100': 0.05,   # <5% = excellent
        'score_75': 0.10,    # <10% = good
        'score_50': 0.15,    # <15% = acceptable (tech companies)
        'score_25': 0.20,    # <20% = concerning
        'score_0': 0.25,     # >25% = excessive
        'inverse': True      # Lower is better
    },
}

# Special scoring functions for non-standard metrics

def score_share_dilution(value: float) -> float:
    """
    Custom bucket scoring for share dilution.
    Negative values = buybacks = good.
    
    Args:
        value: Share dilution CAGR (-0.05 = 5% annual buyback)
        
    Returns:
        Score 0-100
    """
    if value <= -0.05:
        return 100  # 5%+ annual buyback
    elif value <= -0.03:
        return 90   # 3-5% buyback
    elif value <= 0.00:
        return 70   # 0-3% buyback
    elif value <= 0.02:
        return 40   # 0-2% dilution
    elif value <= 0.05:
        return 20   # 2-5% dilution
    else:
        return 0    # 5%+ dilution


def score_capex_intensity(value: float) -> float:
    """
    U-curve scoring for CapEx intensity.
    Optimal range is 20-40% (healthy reinvestment without over-spending).
    
    Args:
        value: CapEx as % of OCF (0.30 = 30%)
        
    Returns:
        Score 0-100
    """
    optimal_min, optimal_max = 0.20, 0.40
    
    if optimal_min <= value <= optimal_max:
        return 100  # In optimal range
    elif 0.15 <= value < optimal_min or optimal_max < value <= 0.60:
        return 75   # Slightly outside optimal
    elif 0.10 <= value < 0.15 or 0.60 < value <= 0.80:
        return 50   # Moderately outside optimal
    elif 0.05 <= value < 0.10 or 0.80 < value <= 1.00:
        return 25   # Significantly outside optimal
    else:
        return 0    # Extreme values


# Weight configurations for different categories
# Weight configurations for different categories
# Default weights (Standard)
CATEGORY_WEIGHTS = {
    'profitability': {
        'max_score': 40,
        'metrics': {
            'roic': 15,
            'roe': 10,
            'operating_margin': 8,
            'gross_margin': 4,
            'net_margin': 3
        }
    },
    'growth': {
        'max_score': 35,
        'metrics': {
            'fcf_cagr_5y': 12,
            'net_income_cagr_5y': 8,
            'revenue_cagr_5y': 6,
            'earnings_quality_3y': 5,
            'fcf_to_debt_ratio': 4
        }
    },
    'capital_allocation': {
        'max_score': 25,
        'metrics': {
            'share_dilution_cagr_5y': 10,
            'capex_intensity_3y': 10,
            'sbc_impact_3y': 5,
            'debt_to_equity': 0  # Not used in new scheme
        }
    }
}

# Sector-specific weight overrides
SECTOR_WEIGHT_OVERRIDES = {
    'Technology': {
        'profitability': {
            'max_score': 35,
            'metrics': {'roic': 12, 'roe': 8, 'operating_margin': 8, 'gross_margin': 4, 'net_margin': 3}
        },
        'growth': {
            'max_score': 45,
            'metrics': {'fcf_cagr_5y': 15, 'net_income_cagr_5y': 12, 'revenue_cagr_5y': 8, 'earnings_quality_3y': 6, 'fcf_to_debt_ratio': 4}
        },
        'capital_allocation': {
            'max_score': 20,
            'metrics': {'share_dilution_cagr_5y': 7, 'capex_intensity_3y': 8, 'sbc_impact_3y': 5}
        }
    },
    'Healthcare': {
        'profitability': {
            'max_score': 38,
            'metrics': {'roic': 14, 'roe': 10, 'operating_margin': 8, 'gross_margin': 3, 'net_margin': 3}
        },
        'growth': {
            'max_score': 40,
            'metrics': {'fcf_cagr_5y': 13, 'net_income_cagr_5y': 10, 'revenue_cagr_5y': 7, 'earnings_quality_3y': 6, 'fcf_to_debt_ratio': 4}
        },
        'capital_allocation': {
            'max_score': 22,
            'metrics': {'share_dilution_cagr_5y': 8, 'capex_intensity_3y': 9, 'sbc_impact_3y': 5}
        }
    },
    'Financials': {
        'profitability': {
            'max_score': 45,
            'metrics': {'roic': 8, 'roe': 20, 'operating_margin': 0, 'gross_margin': 0, 'net_margin': 17}
        },
        'growth': {
            'max_score': 25,
            'metrics': {'fcf_cagr_5y': 0, 'net_income_cagr_5y': 12, 'revenue_cagr_5y': 6, 'earnings_quality_3y': 5, 'fcf_to_debt_ratio': 2}
        },
        'capital_allocation': {
            'max_score': 30,
            'metrics': {'share_dilution_cagr_5y': 12, 'capex_intensity_3y': 3, 'sbc_impact_3y': 15}
        }
    },
    'Consumer Discretionary': {
        'profitability': {
            'max_score': 38,
            'metrics': {'roic': 14, 'roe': 10, 'operating_margin': 8, 'gross_margin': 3, 'net_margin': 3}
        },
        'growth': {
            'max_score': 38,
            'metrics': {'fcf_cagr_5y': 12, 'net_income_cagr_5y': 10, 'revenue_cagr_5y': 8, 'earnings_quality_3y': 5, 'fcf_to_debt_ratio': 3}
        },
        'capital_allocation': {
            'max_score': 24,
            'metrics': {'share_dilution_cagr_5y': 10, 'capex_intensity_3y': 9, 'sbc_impact_3y': 5}
        }
    },
    'Consumer Cyclical': {  # Alias for Consumer Discretionary (Yahoo Finance convention)
        'profitability': {
            'max_score': 38,
            'metrics': {'roic': 14, 'roe': 10, 'operating_margin': 8, 'gross_margin': 3, 'net_margin': 3}
        },
        'growth': {
            'max_score': 38,
            'metrics': {'fcf_cagr_5y': 12, 'net_income_cagr_5y': 10, 'revenue_cagr_5y': 8, 'earnings_quality_3y': 5, 'fcf_to_debt_ratio': 3}
        },
        'capital_allocation': {
            'max_score': 24,
            'metrics': {'share_dilution_cagr_5y': 10, 'capex_intensity_3y': 9, 'sbc_impact_3y': 5}
        }
    },
    'Consumer Staples': {
        'profitability': {
            'max_score': 40,
            'metrics': {'roic': 15, 'roe': 10, 'operating_margin': 8, 'gross_margin': 4, 'net_margin': 3}
        },
        'growth': {
            'max_score': 28,
            'metrics': {'fcf_cagr_5y': 10, 'net_income_cagr_5y': 7, 'revenue_cagr_5y': 5, 'earnings_quality_3y': 4, 'fcf_to_debt_ratio': 2}
        },
        'capital_allocation': {
            'max_score': 32,
            'metrics': {'share_dilution_cagr_5y': 10, 'capex_intensity_3y': 6, 'sbc_impact_3y': 16}
        }
    },
    'Energy': {
        'profitability': {
            'max_score': 35,
            'metrics': {'roic': 12, 'roe': 8, 'operating_margin': 8, 'gross_margin': 4, 'net_margin': 3}
        },
        'growth': {
            'max_score': 30,
            'metrics': {'fcf_cagr_5y': 10, 'net_income_cagr_5y': 6, 'revenue_cagr_5y': 5, 'earnings_quality_3y': 5, 'fcf_to_debt_ratio': 4}
        },
        'capital_allocation': {
            'max_score': 35,
            'metrics': {'share_dilution_cagr_5y': 10, 'capex_intensity_3y': 20, 'sbc_impact_3y': 5}
        }
    },
    'Industrials': {
        # Matches Default, likely redundant but kept for explicit clarity
         'profitability': {
            'max_score': 40,
            'metrics': {'roic': 15, 'roe': 10, 'operating_margin': 8, 'gross_margin': 4, 'net_margin': 3}
        },
        'growth': {
            'max_score': 35,
            'metrics': {'fcf_cagr_5y': 12, 'net_income_cagr_5y': 8, 'revenue_cagr_5y': 6, 'earnings_quality_3y': 5, 'fcf_to_debt_ratio': 4}
        },
        'capital_allocation': {
            'max_score': 25,
            'metrics': {'share_dilution_cagr_5y': 10, 'capex_intensity_3y': 10, 'sbc_impact_3y': 5}
        }
    },
    'Materials': {
        'profitability': {
            'max_score': 38,
            'metrics': {'roic': 14, 'roe': 10, 'operating_margin': 8, 'gross_margin': 3, 'net_margin': 3}
        },
        'growth': {
            'max_score': 30,
            'metrics': {'fcf_cagr_5y': 10, 'net_income_cagr_5y': 7, 'revenue_cagr_5y': 5, 'earnings_quality_3y': 5, 'fcf_to_debt_ratio': 3}
        },
        'capital_allocation': {
            'max_score': 32,
            'metrics': {'share_dilution_cagr_5y': 10, 'capex_intensity_3y': 17, 'sbc_impact_3y': 5}
        }
    },
    'Real Estate': {
        'profitability': {
            'max_score': 35,
            'metrics': {'roic': 10, 'roe': 8, 'operating_margin': 10, 'gross_margin': 4, 'net_margin': 3}
        },
        'growth': {
            'max_score': 25,
            'metrics': {'fcf_cagr_5y': 8, 'net_income_cagr_5y': 6, 'revenue_cagr_5y': 5, 'earnings_quality_3y': 4, 'fcf_to_debt_ratio': 2}
        },
        'capital_allocation': {
            'max_score': 40,
            'metrics': {'share_dilution_cagr_5y': 6, 'capex_intensity_3y': 8, 'sbc_impact_3y': 26}
        }
    },
    'Utilities': {
        'profitability': {
            'max_score': 38,
            'metrics': {'roic': 12, 'roe': 10, 'operating_margin': 10, 'gross_margin': 3, 'net_margin': 3}
        },
        'growth': {
            'max_score': 22,
            'metrics': {'fcf_cagr_5y': 7, 'net_income_cagr_5y': 6, 'revenue_cagr_5y': 4, 'earnings_quality_3y': 3, 'fcf_to_debt_ratio': 2}
        },
        'capital_allocation': {
            'max_score': 40,
            'metrics': {'share_dilution_cagr_5y': 5, 'capex_intensity_3y': 8, 'sbc_impact_3y': 27}
        }
    },
    'Communication Services': {
        'profitability': {
            'max_score': 38,
            'metrics': {'roic': 14, 'roe': 10, 'operating_margin': 8, 'gross_margin': 3, 'net_margin': 3}
        },
        'growth': {
            'max_score': 38,
            'metrics': {'fcf_cagr_5y': 12, 'net_income_cagr_5y': 10, 'revenue_cagr_5y': 7, 'earnings_quality_3y': 5, 'fcf_to_debt_ratio': 4}
        },
        'capital_allocation': {
            'max_score': 24,
            'metrics': {'share_dilution_cagr_5y': 10, 'capex_intensity_3y': 9, 'sbc_impact_3y': 5}
        }
    }
}

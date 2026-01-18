"""
Metric scorer - Individual metric evaluation using tier-based scoring.

Implements three scoring tiers:
- Tier 1: Synthetic Z-Score (uses mean + derived_sigma from benchmarks)
- Tier 2: Mean Multiplier Heuristics (uses mean × 1.25/0.75 thresholds)
- Tier 3: Absolute Standards (cross-industry thresholds)
"""

import pandas as pd
from typing import Optional, Dict, Any
from utils.logger import setup_logger
from fundamentals.financial_scorers.scoring_config import (
    TIER3_THRESHOLDS,
    score_share_dilution,
    score_capex_intensity
)

logger = setup_logger('metric_scorer')


class MetricScorer:
    """
    Scores individual metrics using tier-based approach.
    """
    
    def score_metric(
        self,
        metric_name: str,
        company_value: Optional[float],
        metric_config: Dict[str, Any],
        global_defaults: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main scoring dispatcher - routes to appropriate tier.
        
        Args:
            metric_name: Name of metric (e.g., 'roic', 'fcf_cagr_5y')
            company_value: Company's actual value for this metric
            metric_config: Configuration from sector_benchmarks.json
            global_defaults: Global default parameters
            
        Returns:
            {
                'raw_score': 75.3,
                'tier': 'tier_1_synthetic',
                'z_score': 0.68,  # Only for tier 1
                'percentile': 75,
                'interpretation': 'Above average'
            }
        """
        # Handle null values
        if company_value is None or pd.isna(company_value):
            return {
                'raw_score': None,
                'tier': 'null',
                'percentile': None,
                'interpretation': 'Data not available'
            }
        
        # Get scoring mode
        mode = metric_config.get('scoring_mode')
        
        if mode == 'tier_1_synthetic':
            return self._score_tier1_synthetic(company_value, metric_config)
        
        elif mode == 'tier_2_multiplier':
            return self._score_tier2_multiplier(company_value, metric_config, global_defaults or {})
        
        elif mode == 'tier_3_absolute':
            return self._score_tier3_absolute(metric_name, company_value, metric_config)
        
        elif mode == 'disabled':
            return {
                'raw_score': 0,
                'tier': 'disabled',
                'percentile': None,
                'interpretation': 'Metric disabled for this sector'
            }
        
        else:
            logger.error(f"Unknown scoring mode: {mode} for metric {metric_name}")
            raise ValueError(f"Unknown scoring_mode: {mode}")
    
    def _score_tier1_synthetic(
        self,
        company_value: float,
        metric_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Tier 1: Synthetic Z-Score using pre-calculated breakpoints.
        
        Formula:
            Z = (company_value - mean) / derived_sigma
            score = 50 + (Z × 37)
        """
        mean = metric_config['mean']
        sigma = metric_config['derived_sigma']
        
        # Handle edge case: sigma=0 (no variance)
        if sigma == 0 or sigma is None:
            logger.warning(f"Sigma is zero/null, falling back to Tier 2")
            return self._score_tier2_multiplier(company_value, metric_config, {})
        
        # Calculate Z-score
        z_score = (company_value - mean) / sigma
        
        # Map Z-score to 0-100 scale
        raw_score = 50 + (z_score * 37)
        
        # Clamp to [0, 100]
        final_score = max(0, min(100, raw_score))
        
        # Determine percentile bucket
        breakpoints = metric_config.get('synthetic_breakpoints', {})
        if company_value >= breakpoints.get('p90', float('inf')):
            percentile = 90
            interpretation = 'Excellent (Top 10%)'
        elif company_value >= breakpoints.get('p75', float('inf')):
            percentile = 75
            interpretation = 'Good (Top 25%)'
        elif company_value >= breakpoints.get('p50', float('inf')):
            percentile = 50
            interpretation = 'Average'
        elif company_value >= breakpoints.get('p25', float('inf')):
            percentile = 25
            interpretation = 'Below Average'
        else:
            percentile = 10
            interpretation = 'Poor (Bottom 10%)'
        
        return {
            'raw_score': round(final_score, 1),
            'tier': 'tier_1_synthetic',
            'z_score': round(z_score, 2),
            'percentile': percentile,
            'interpretation': interpretation,
            'mean': mean,
            'sigma': sigma
        }
    
    def _score_tier2_multiplier(
        self,
        company_value: float,
        metric_config: Dict[str, Any],
        global_defaults: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Tier 2: Mean Multiplier Heuristics.
        
        Uses empirical rules:
            P75 ≈ mean × 1.25 (good companies)
            P25 ≈ mean × 0.75 (acceptable companies)
        """
        mean = metric_config['mean']
        is_inverse = metric_config.get('inverse_metric', False)
        
        # Get multipliers
        if 'multiplier_override' in metric_config:
            multipliers = metric_config['multiplier_override']
        else:
            multipliers = global_defaults.get('tier2_multipliers', {
                'p75_proxy': 1.25,
                'p25_proxy': 0.75
            })
        
        if not is_inverse:
            # Normal: higher is better
            p75_threshold = mean * multipliers.get('p75_proxy', 1.25)
            p25_threshold = mean * multipliers.get('p25_proxy', 0.75)
            
            if company_value >= p75_threshold:
                # 75-100 range
                extra_ratio = (company_value - p75_threshold) / (mean * 0.25)
                score = 75 + 25 * min(1.0, extra_ratio)
                interpretation = 'Good to Excellent'
            elif company_value >= p25_threshold:
                # 25-75 range
                progress = (company_value - p25_threshold) / (p75_threshold - p25_threshold)
                score = 25 + 50 * progress
                interpretation = 'Acceptable to Good'
            else:
                # 0-25 range
                ratio = max(0, company_value / p25_threshold)
                score = 25 * ratio
                interpretation = 'Poor'
        else:
            # Inverse: lower is better
            good_threshold = mean * 0.8
            bad_threshold = mean * 1.2
            
            if company_value <= good_threshold:
                extra_ratio = (good_threshold - company_value) / (mean * 0.2)
                score = 75 + 25 * min(1.0, extra_ratio)
                interpretation = 'Good to Excellent (Low)'
            elif company_value <= bad_threshold:
                progress = (bad_threshold - company_value) / (bad_threshold - good_threshold)
                score = 25 + 50 * progress
                interpretation = 'Acceptable'
            else:
                ratio = max(0, 1 - (company_value - bad_threshold) / mean)
                score = 25 * ratio
                interpretation = 'Poor (High)'
        
        percentile = int(score / 25) * 25 if score > 0 else 0
        
        return {
            'raw_score': round(score, 1),
            'tier': 'tier_2_multiplier',
            'percentile': percentile,
            'interpretation': interpretation
        }
    
    def _score_tier3_absolute(
        self,
        metric_name: str,
        company_value: float,
        metric_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Tier 3: Absolute Standards (cross-industry thresholds).
        """
        # Check for special scoring functions
        if metric_name == 'share_dilution_cagr_5y':
            score = score_share_dilution(company_value)
            return {
                'raw_score': score,
                'tier': 'tier_3_absolute',
                'bucket': self._get_dilution_bucket(company_value),
                'interpretation': self._interpret_dilution(score)
            }
        
        elif metric_name == 'capex_intensity_3y':
            score = score_capex_intensity(company_value)
            return {
                'raw_score': score,
                'tier': 'tier_3_absolute',
                'bucket': self._get_capex_bucket(company_value),
                'interpretation': self._interpret_capex(score)
            }
        
        else:
            # Standard bucket scoring
            thresholds = metric_config.get('absolute_thresholds') or TIER3_THRESHOLDS.get(metric_name, {})
            
            if not thresholds:
                logger.warning(f"No thresholds found for {metric_name}, returning 50")
                return {'raw_score': 50, 'tier': 'tier_3_absolute', 'bucket': 'default'}
            
            # Check if inverse metric
            is_inverse = thresholds.get('inverse', False)
            
            if not is_inverse:
                # Normal: higher is better
                if company_value >= thresholds.get('score_100', float('inf')):
                    return {'raw_score': 100, 'tier': 'tier_3_absolute', 'bucket': 'excellent', 'interpretation': 'Excellent'}
                elif company_value >= thresholds.get('score_75', float('inf')):
                    return {'raw_score': 75, 'tier': 'tier_3_absolute', 'bucket': 'good', 'interpretation': 'Good'}
                elif company_value >= thresholds.get('score_50', float('inf')):
                    return {'raw_score': 50, 'tier': 'tier_3_absolute', 'bucket': 'acceptable', 'interpretation': 'Acceptable'}
                elif company_value >= thresholds.get('score_25', float('inf')):
                    return {'raw_score': 25, 'tier': 'tier_3_absolute', 'bucket': 'poor', 'interpretation': 'Poor'}
                else:
                    return {'raw_score': 0, 'tier': 'tier_3_absolute', 'bucket': 'failing', 'interpretation': 'Failing'}
            else:
                # Inverse: lower is better
                if company_value <= thresholds.get('score_100', float('-inf')):
                    return {'raw_score': 100, 'tier': 'tier_3_absolute', 'bucket': 'excellent', 'interpretation': 'Excellent (Low)'}
                elif company_value <= thresholds.get('score_75', float('-inf')):
                    return {'raw_score': 75, 'tier': 'tier_3_absolute', 'bucket': 'good', 'interpretation': 'Good (Low)'}
                elif company_value <= thresholds.get('score_50', float('-inf')):
                    return {'raw_score': 50, 'tier': 'tier_3_absolute', 'bucket': 'acceptable', 'interpretation': 'Acceptable'}
                elif company_value <= thresholds.get('score_25', float('-inf')):
                    return {'raw_score': 25, 'tier': 'tier_3_absolute', 'bucket': 'poor', 'interpretation': 'Poor (High)'}
                else:
                    return {'raw_score': 0, 'tier': 'tier_3_absolute', 'bucket': 'failing', 'interpretation': 'Excessive'}
    
    @staticmethod
    def _get_dilution_bucket(value):
        if value <= -0.05: return 'strong_buyback'
        if value <= -0.03: return 'moderate_buyback'
        if value <= 0.00: return 'light_buyback'
        if value <= 0.02: return 'minor_dilution'
        if value <= 0.05: return 'moderate_dilution'
        return 'high_dilution'
    
    @staticmethod
    def _interpret_dilution(score):
        if score >= 90: return 'Strong buyback program'
        if score >= 70: return 'Active buybacks'
        if score >= 40: return 'Minor dilution'
        if score >= 20: return 'Moderate dilution'
        return 'High dilution'
    
    @staticmethod
    def _get_capex_bucket(value):
        if 0.20 <= value <= 0.40: return 'optimal'
        if 0.15 <= value < 0.20 or 0.40 < value <= 0.60: return 'acceptable'
        if 0.10 <= value < 0.15 or 0.60 < value <= 0.80: return 'suboptimal'
        return 'extreme'
    
    @staticmethod
    def _interpret_capex(score):
        if score >= 90: return 'Optimal reinvestment level'
        if score >= 70: return 'Good reinvestment'
        if score >= 50: return 'Moderate reinvestment'
        return 'Suboptimal reinvestment'

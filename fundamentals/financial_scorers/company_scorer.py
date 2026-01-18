"""
Company scorer - Comprehensive company evaluation system.

Takes calculator outputs (ProfitabilityMetrics, GrowthMetrics, CapitalAllocationMetrics)
and scores against sector_benchmarks.json to generate 0-100 score.
"""

import json
from pathlib import Path
from typing import Optional
from dataclasses import asdict
from utils.logger import setup_logger
from fundamentals.financial_data import (
    ProfitabilityMetrics,
    GrowthMetrics,
    CapitalAllocationMetrics
)
from fundamentals.financial_scorers.metric_scorer import MetricScorer
from fundamentals.financial_scorers.scoring_config import (
    CATEGORY_WEIGHTS,
    SECTOR_WEIGHT_OVERRIDES,
    TIER3_THRESHOLDS
)

logger = setup_logger('company_scorer')


class CompanyScorer:
    """
    Comprehensive company scoring system.
    Evaluates companies on 0-100 scale.
    """
    
    def __init__(self, benchmarks_path: str = 'user_config/sector_benchmarks.json'):
        """Initialize company scorer with industry benchmarks."""
        with open(benchmarks_path, encoding='utf-8') as f:
            self.benchmarks = json.load(f)
        
        self.metric_scorer = MetricScorer()
        logger.info(f"CompanyScorer initialized with {len(self.benchmarks['sectors'])} sectors")
    
    def score_company(
        self,
        profitability: ProfitabilityMetrics,
        growth: GrowthMetrics,
        capital_allocation: CapitalAllocationMetrics,
        sector: str,
        company_name: Optional[str] = None
    ) -> dict:
        """
        Score a company comprehensively across all categories.
        
        Args:
            profitability: ProfitabilityMetrics from calculator
            growth: GrowthMetrics from calculator
            capital_allocation: CapitalAllocationMetrics from calculator
            sector: GICS sector name ('Technology', etc.)
            company_name: Optional company name for logging
            
        Returns:
            {
                'company': '...',
                'sector': '...',
                'total_score': 72.8,
                'category_scores': {...},
                'warnings': [...]
            }
        """
        if sector not in self.benchmarks['sectors']:
            raise ValueError(f"Unknown sector: {sector}. Available: {list(self.benchmarks['sectors'].keys())}")
        
        sector_config = self.benchmarks['sectors'][sector]
        global_defaults = self.benchmarks['defaults']
        
        logger.info(f"Scoring company: {company_name or 'Unknown'} (Sector: {sector})")
        
        # Get weights (with sector overrides)
        weights = self._get_weights(sector)
        
        # Score each category
        prof_score = self._score_profitability(profitability, sector_config, global_defaults, weights['profitability'])
        growth_score = self._score_growth(growth, sector_config, global_defaults, weights['growth'])
        capital_score = self._score_capital_allocation(capital_allocation, sector_config, global_defaults, weights['capital_allocation'])
        
        # Calculate total
        total_score = prof_score['score'] + growth_score['score'] + capital_score['score']
        
        # Collect all warnings
        all_warnings = []
        all_warnings.extend(prof_score.get('warnings', []))
        all_warnings.extend(growth_score.get('warnings', []))
        all_warnings.extend(capital_score.get('warnings', []))
        
        result = {
            'company': company_name or 'Unknown',
            'sector': sector,
            'total_score': round(total_score, 1),
            'category_scores': {
                'profitability': prof_score,
                'growth': growth_score,
                'capital_allocation': capital_score
            },
            'warnings': all_warnings
        }
        
        logger.info(f"{result['company']}: {result['total_score']}/100")
        
        return result
    
    def _get_weights(self, sector: str) -> dict:
        """Get weights for sector (with overrides)."""
        import copy
        base_weights = copy.deepcopy(CATEGORY_WEIGHTS)
        
        # Apply sector-specific overrides
        if sector in SECTOR_WEIGHT_OVERRIDES:
            overrides = SECTOR_WEIGHT_OVERRIDES[sector]
            for category, cat_data in overrides.items():
                if category in base_weights:
                    # Update max_score if present
                    if 'max_score' in cat_data:
                        base_weights[category]['max_score'] = cat_data['max_score']
                    
                    # Update individual metric weights
                    if 'metrics' in cat_data:
                        base_weights[category]['metrics'].update(cat_data['metrics'])
        
        return base_weights
    
    def _score_profitability(self, profitability, sector_config, global_defaults, weights) -> dict:
        """Score profitability category (40 points max)."""
        metrics_config = sector_config.get('metrics', {})
        metric_weights = weights['metrics']
        max_score = weights['max_score']
        
        total_score = 0
        metric_details = {}
        warnings = []
        
        # Map metric names
        metric_mapping = {
            'roic': profitability.roic,
            'roe': profitability.roe,
            'operating_margin': profitability.operating_margin,
            'gross_margin': profitability.gross_margin,
            'net_margin': profitability.net_margin
        }
        
        # Score each profitability metric
        active_weight = 0
        total_possible_weight = sum(metric_weights.values())
        
        for metric_name, company_value in metric_mapping.items():
            weight = metric_weights.get(metric_name, 0)
            
            if weight == 0:
                # Metric disabled for this sector, but still save the value for display
                metric_details[metric_name] = {
                    'disabled': True, 
                    'weight': 0,
                    'value': company_value,  # Include value for display
                    'note': 'Not used for this sector'
                }
                continue
            
            # Get config from benchmarks
            metric_config = metrics_config.get(metric_name)
            
            if metric_config is None:
                warnings.append(f"{metric_name}: not available in benchmarks (weight {weight} excluded)")
                continue
            
            active_weight += weight
            
            # Score the metric
            score_result = self.metric_scorer.score_metric(
                metric_name, company_value, metric_config, global_defaults
            )
            
            if score_result['raw_score'] is not None:
                # Weighted contribution
                # calculation: (raw_score / 100) * weight
                weighted_contribution = (score_result['raw_score'] / 100) * weight
                total_score += weighted_contribution
                
                metric_details[metric_name] = {
                    'value': company_value,
                    'raw_score': score_result['raw_score'],
                    'weight': weight,
                    'weighted_score': round(weighted_contribution, 2),
                    'tier': score_result['tier'],
                    'percentile': score_result.get('percentile'),
                    'interpretation': score_result.get('interpretation')
                }
        
        # Normalize score if some weights were skipped
        final_score = total_score
        if 0 < active_weight < total_possible_weight:
            scale_factor = total_possible_weight / active_weight
            final_score = total_score * scale_factor
            warnings.append(f"Score normalized by {scale_factor:.2f}x (missing benchmarks)")
            
        return {
            'score': round(final_score, 2),
            'max': max_score,
            'percentage': round((final_score / max_score) * 100, 1) if max_score > 0 else 0,
            'metrics': metric_details,
            'warnings': warnings
        }
    
    def _score_growth(self, growth, sector_config, global_defaults, weights) -> dict:
        """Score growth category (35 points max)."""
        metric_weights = weights['metrics']
        max_score = weights['max_score']
        
        total_score = 0
        metric_details = {}
        warnings = []
        
        # === FCF CAGR (special handling) ===
        fcf_cagr = growth.fcf_cagr_5y
        fcf_weight = metric_weights.get('fcf_cagr_5y', 12)
        
        if fcf_cagr is not None and fcf_cagr < 0:
            # Negative FCF growth - check for compensation
            # TODO: Access capital_allocation for dilution check
            metric_config = {
                'scoring_mode': 'tier_3_absolute',
               'absolute_thresholds': TIER3_THRESHOLDS['fcf_cagr_5y']
            }
            score_result = self.metric_scorer.score_metric(
                'fcf_cagr_5y', fcf_cagr, metric_config, global_defaults
            )
            
            weighted_score = (score_result['raw_score'] / 100) * fcf_weight
            total_score += weighted_score
            metric_details['fcf_cagr_5y'] = {
                'value': fcf_cagr,
                'raw_score': score_result['raw_score'],
                'weight': fcf_weight,
                'weighted_score': round(weighted_score, 2),
                'tier': score_result['tier'],
                'interpretation': score_result.get('interpretation')
            }
        elif fcf_cagr is not None:
            # Positive FCF growth
            metric_config = {
                'scoring_mode': 'tier_3_absolute',
                'absolute_thresholds': TIER3_THRESHOLDS['fcf_cagr_5y']
            }
            score_result = self.metric_scorer.score_metric(
                'fcf_cagr_5y', fcf_cagr, metric_config, global_defaults
            )
            
            weighted_score = (score_result['raw_score'] / 100) * fcf_weight
            total_score += weighted_score
            metric_details['fcf_cagr_5y'] = {
                'value': fcf_cagr,
                'raw_score': score_result['raw_score'],
                'weight': fcf_weight,
                'weighted_score': round(weighted_score, 2),
                'tier': score_result['tier'],
                'interpretation': score_result.get('interpretation')
            }
        
        # === Other growth metrics (standard Tier 3) ===
        tier3_metrics = {
            'net_income_cagr_5y': (growth.net_income_cagr_5y, metric_weights.get('net_income_cagr_5y', 8)),
            'revenue_cagr_5y': (growth.revenue_cagr_5y, metric_weights.get('revenue_cagr_5y', 6)),
            'earnings_quality_3y': (growth.earnings_quality_3y, metric_weights.get('earnings_quality_3y', 5)),
            'fcf_to_debt_ratio': (growth.fcf_to_debt_ratio, metric_weights.get('fcf_to_debt_ratio', 4)),
        }
        
        for metric_name, (value, weight) in tier3_metrics.items():
            if value is None:
                continue
            
            metric_config = {
                'scoring_mode': 'tier_3_absolute',
                'absolute_thresholds': TIER3_THRESHOLDS.get(metric_name, {})
            }
            score_result = self.metric_scorer.score_metric(
                metric_name, value, metric_config, global_defaults
            )
            
            if score_result['raw_score'] is not None:
                weighted_score = (score_result['raw_score'] / 100) * weight
                total_score += weighted_score
                metric_details[metric_name] = {
                    'value': value,
                    'raw_score': score_result['raw_score'],
                    'weight': weight,
                    'weighted_score': round(weighted_score, 2),
                    'tier': score_result['tier'],
                    'interpretation': score_result.get('interpretation')
                }
        
        return {
            'score': round(total_score, 2),
            'max': max_score,
            'percentage': round((total_score / max_score) * 100, 1) if max_score > 0 else 0,
            'metrics': metric_details,
            'warnings': warnings
        }
    
    def _score_capital_allocation(self, capital_allocation, sector_config, global_defaults, weights) -> dict:
        """Score capital allocation category (25 points max)."""
        metric_weights = weights['metrics']
        max_score = weights['max_score']
        
        total_score = 0
        metric_details = {}
        warnings = []
        
        # Share Dilution (Tier 3 custom)
        share_dilution = capital_allocation.share_dilution_cagr_5y
        dilution_weight = metric_weights.get('share_dilution_cagr_5y', 10)
        
        if share_dilution is not None:
            metric_config = {'scoring_mode': 'tier_3_absolute'}
            score_result = self.metric_scorer.score_metric(
                'share_dilution_cagr_5y', share_dilution, metric_config, global_defaults
            )
            
            weighted_score = (score_result['raw_score'] / 100) * dilution_weight
            total_score += weighted_score
            metric_details['share_dilution_cagr_5y'] = {
                'value': share_dilution,
                'raw_score': score_result['raw_score'],
                'weight': dilution_weight,
                'weighted_score': round(weighted_score, 2),
                'tier': score_result['tier'],
                'bucket': score_result.get('bucket'),
                'interpretation': score_result.get('interpretation')
            }
        
        # CapEx Intensity (Tier 3 U-curve)
        capex_intensity = capital_allocation.capex_intensity_3y
        capex_weight = metric_weights.get('capex_intensity_3y', 8)
        
        if capex_intensity is not None:
            metric_config = {'scoring_mode': 'tier_3_absolute'}
            score_result = self.metric_scorer.score_metric(
                'capex_intensity_3y', capex_intensity, metric_config, global_defaults
            )
            
            weighted_score = (score_result['raw_score'] / 100) * capex_weight
            total_score += weighted_score
            metric_details['capex_intensity_3y'] = {
                'value': capex_intensity,
                'raw_score': score_result['raw_score'],
                'weight': capex_weight,
                'weighted_score': round(weighted_score, 2),
                'tier': score_result['tier'],
                'bucket': score_result.get('bucket'),
                'interpretation': score_result.get('interpretation')
            }
        
        # SBC Impact (Tier 3)
        sbc_impact = capital_allocation.sbc_impact_3y
        sbc_weight = metric_weights.get('sbc_impact_3y', 4)
        
        if sbc_impact is not None:
            metric_config = {
                'scoring_mode': 'tier_3_absolute',
                'absolute_thresholds': TIER3_THRESHOLDS['sbc_impact_3y']
            }
            score_result = self.metric_scorer.score_metric(
                'sbc_impact_3y', sbc_impact, metric_config, global_defaults
            )
            
            weighted_score = (score_result['raw_score'] / 100) * sbc_weight
            total_score += weighted_score
            metric_details['sbc_impact_3y'] = {
                'value': sbc_impact,
                'raw_score': score_result['raw_score'],
                'weight': sbc_weight,
                'weighted_score': round(weighted_score, 2),
                'tier': score_result['tier'],
                'interpretation': score_result.get('interpretation')
            }
        
        # Debt to Equity (Tier 2 from benchmarks if available)
        debt_to_equity = capital_allocation.debt_to_equity
        de_weight = metric_weights.get('debt_to_equity', 3)
        
        if debt_to_equity is not None:
            metrics_config = sector_config.get('metrics', {})
            if 'debt_to_equity' in metrics_config:
                metric_config = metrics_config['debt_to_equity']
                score_result = self.metric_scorer.score_metric(
                    'debt_to_equity', debt_to_equity, metric_config, global_defaults
                )
                
                weighted_score = (score_result['raw_score'] / 100) * de_weight
                total_score += weighted_score
                metric_details['debt_to_equity'] = {
                    'value': debt_to_equity,
                    'raw_score': score_result['raw_score'],
                    'weight': de_weight,
                    'weighted_score': round(weighted_score, 2),
                    'tier': score_result['tier'],
                    'interpretation': score_result.get('interpretation')
                }
        
        return {
            'score': round(total_score, 2),
            'max': max_score,
            'percentage': round((total_score / max_score) * 100, 1) if max_score > 0 else 0,
            'metrics': metric_details,
            'warnings': warnings
        }
    


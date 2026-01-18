"""
Benchmark calculator - processes Damodaran data and calculates sector statistics.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from utils.logger import setup_logger
from .industry_mapper import SECTOR_MAPPING

logger = setup_logger('benchmark_calculator')


class BenchmarkCalculator:
    """
    Calculate sector-level statistics from Damodaran industry data.
    Aggregates 100+ industries into 11 GICS sectors with synthetic statistics.
    """
    
    # Column name mappings for Damodaran HTML tables
    # Column name mappings for Damodaran HTML tables
    ROC_COLUMNS = {
        'industry': 'Industry Name',
        'num_firms': 'Number of firms',
        'roic': 'Lease & R&D adjusted after-tax ROIC',  # Most comprehensive ROIC measure
    }
    
    ROE_COLUMNS = {
        'industry': 'Industry Name',
        'num_firms': 'Number of firms',
        'roe': 'ROE (adjusted for R&D)'
    }
    
    WACC_COLUMNS = {
        'industry': 'Industry Name',
        'num_firms': 'Number of Firms',  # Note: capital F in HTML
    }
    
    BETA_COLUMNS = {
        'industry': 'Industry Name',
        'num_firms': 'Number of firms',
        'beta': 'Beta',
        'cv_operating_income': 'Standard deviation in operating income (last 10  years)',  # Note: double space
    }
    
    # New column mappings for valuation multiples
    PBV_COLUMNS = {
        'industry': 'Industry Name',
        'num_firms': 'Number of firms',
        'pb_ratio': 'PBV',  # Actual column name, not 'Current Price to Book'
    }
    
    PE_COLUMNS = {
        'industry': 'Industry  Name',  # Note: two spaces in actual HTML
        'num_firms': 'Number of firms',
        'pe_current': 'Current PE',
        'pe_trailing': 'Trailing PE',
        'pe_forward': 'Forward PE',
    }
    
    PS_COLUMNS = {
        'industry': 'Industry  Name',  # Note: two spaces
        'num_firms': 'Number  of firms',  # Note: two spaces
        'ps_ratio': 'Price/Sales',
        'ev_sales': 'EV/Sales',
    }
    
    EV_EBITDA_COLUMNS = {
        'industry': 'Industry Name',  # Real column name after skipping first row
        'num_firms': 'Number of firms',
        'ev_ebitda': 'EV/EBITDA',  # From "Only positive EBITDA firms" section
    }
    
    MARGIN_COLUMNS = {
        'industry': 'Industry Name',
        'num_firms': 'Number of Firms',
        'net_margin': 'Net Margin',
        'operating_margin': 'Operating Margin',
        'pretax_margin': 'Pre-tax Margin',
    }
    
    DIV_YIELD_COLUMNS = {
        'industry': 'Industry Name',
        'num_firms': 'Number of firms',
        'dividend_yield': 'Dividend Yield',
        'payout_ratio': 'Dividend Payout',  # Note: "Dividend Payout" not "Payout Ratio"
        'roe': 'ROE',  # Bonus: ROE is also in divfund!
    }
    
    # Damping factors for different metrics
    DAMPING_FACTORS = {
        'roic': 0.85,
        'roe': 0.80,
        'operating_margin': 1.0,
        'net_margin': 0.90,
        'gross_margin': 0.95,
    }
    
    def __init__(self, roc_df: pd.DataFrame, wacc_df: pd.DataFrame, beta_df: pd.DataFrame, 
                 roe_df: pd.DataFrame = None, pbv_df: pd.DataFrame = None, 
                 pe_df: pd.DataFrame = None, ps_df: pd.DataFrame = None,
                 ev_ebitda_df: pd.DataFrame = None, margins_df: pd.DataFrame = None,
                 div_yield_df: pd.DataFrame = None):
        """
        Initialize calculator with Damodaran DataFrames.
        
        Args:
            roc_df: ROC DataFrame
            wacc_df: WACC DataFrame
            beta_df: Beta DataFrame
            roe_df: ROE DataFrame (optional)
            pbv_df: Price/Book DataFrame (optional)
            pe_df: PE Ratio DataFrame (optional)
            ps_df: Price/Sales DataFrame (optional)
            ev_ebitda_df: EV/EBITDA DataFrame (optional)
            margins_df: Margins DataFrame (optional)
            div_yield_df: Dividend Yield DataFrame (optional)
        """
        logger.info("Initializing benchmark calculator with DataFrames...")
        
        # Existing data
        self.roc_df = roc_df
        self.wacc_df = wacc_df
        self.beta_df = beta_df
        self.roe_df = roe_df
        
        # New valuation multiples data
        self.pbv_df = pbv_df
        self.pe_df = pe_df
        self.ps_df = ps_df
        self.ev_ebitda_df = ev_ebitda_df
        self.margins_df = margins_df
        self.div_yield_df = div_yield_df
        
        logger.info(f"ROC data: {len(self.roc_df)} industries")
        logger.info(f"WACC data: {len(self.wacc_df)} industries")
        logger.info(f"Beta data: {len(self.beta_df)} industries")
        if self.roe_df is not None:
             logger.info(f"ROE data: {len(self.roe_df)} industries")
        if self.pbv_df is not None:
             logger.info(f"PBV data: {len(self.pbv_df)} industries")
        if self.pe_df is not None:
             logger.info(f"PE data: {len(self.pe_df)} industries")
        if self.ps_df is not None:
             logger.info(f"PS data: {len(self.ps_df)} industries")
        if self.ev_ebitda_df is not None:
             logger.info(f"EV/EBITDA data: {len(self.ev_ebitda_df)} industries")
        if self.margins_df is not None:
             logger.info(f"Margins data: {len(self.margins_df)} industries")
        if self.div_yield_df is not None:
             logger.info(f"Dividend Yield data: {len(self.div_yield_df)} industries")
    

    
    def _get_column_safe(self, df: pd.DataFrame, expected_name: str, alternatives: List[str] = None) -> Optional[str]:
        """
        Safely get column name, trying alternatives if needed.
        
        Args:
            df: DataFrame
            expected_name: Expected column name
            alternatives: Alternative column names to try
            
        Returns:
            Actual column name or None
        """
        if expected_name in df.columns:
            return expected_name
        
        if alternatives:
            for alt in alternatives:
                if alt in df.columns:
                    logger.warning(f"Using alternative column name: '{alt}' instead of '{expected_name}'")
                    return alt
        
        logger.error(f"Column '{expected_name}' not found. Available columns: {list(df.columns)}")
        return None
    
    def aggregate_sector(self, sector_name: str, industries: List[str]) -> Dict:
        """
        Aggregate statistics for one sector.
        
        Args:
            sector_name: GICS sector name
            industries: List of Damodaran industry names to aggregate
            
        Returns:
            Dictionary with sector statistics
        """
        logger.info(f"Aggregating sector: {sector_name} ({len(industries)} industries)")
        
        # Filter data for this sector's industries
        sector_roc = self.roc_df[self.roc_df[self.ROC_COLUMNS['industry']].isin(industries)]
        sector_wacc = self.wacc_df[self.wacc_df[self.WACC_COLUMNS['industry']].isin(industries)]
        sector_beta = self.beta_df[self.beta_df[self.BETA_COLUMNS['industry']].isin(industries)]
        
        if len(sector_roc) == 0:
            logger.warning(f"No ROC data found for {sector_name}")
            return None
        
        # Extract weighted metrics from ROC data
        total_firms = sector_roc[self.ROC_COLUMNS['num_firms']].sum()
        
        if total_firms == 0:
            logger.warning(f"No firms found for {sector_name}")
            return None
        
        # Get ROIC data
        roic_series = sector_roc[self.ROC_COLUMNS['roic']]
        
        # Handle percentage strings (e.g., "15.23%")
        if roic_series.dtype == 'object':
            roic_series = roic_series.str.strip('%').astype(float) / 100
        
        mean_roic = (
            roic_series * 
            sector_roc[self.ROC_COLUMNS['num_firms']]
        ).sum() / total_firms
        
        # Estimate operating margin from ROIC (rough approximation)
        # Operating margin is typically 50-70% of ROIC for most industries
        mean_operating_margin = mean_roic * 0.6
        
        # ROE from WACC data (if available) - NOT PRESENT in current HTML
        mean_roe = None
        
        # CV (Coefficient of Variation) from Beta data
        cv_series = sector_beta[self.BETA_COLUMNS['cv_operating_income']] if len(sector_beta) > 0 else None
        
        if cv_series is not None:
            # Handle percentage strings
            if cv_series.dtype == 'object':
                cv_series = cv_series.str.strip('%').astype(float) / 100
            cv = cv_series.mean()
        else:
            cv = 0.5
        
        if pd.isna(cv) or cv <= 0:
            cv = 0.5  # Default fallback
            logger.warning(f"{sector_name}: Using default CV of 0.5")
        
        # Build metrics dictionary
        metrics = {}
        
        # === ROIC (Tier 1: Synthetic Z-Score) ===
        if not pd.isna(mean_roic) and mean_roic > 0:
            metrics['roic'] = self._calculate_tier1_metric(
                'roic', mean_roic, cv, weight=0.18
            )
        
        # === ROE (Tier 1: Synthetic Z-Score) ===
        mean_roe = None
        if self.roe_df is not None:
             sector_roe = self.roe_df[self.roe_df[self.ROE_COLUMNS['industry']].isin(industries)]
             if len(sector_roe) > 0:
                 roe_firms = sector_roe[self.ROE_COLUMNS['num_firms']]
                 roe_vals = sector_roe[self.ROE_COLUMNS['roe']]
                 
                 # Clean percentage strings
                 if roe_vals.dtype == 'object':
                     roe_vals = roe_vals.str.strip('%').astype(float) / 100
                 
                 total_roe_firms = roe_firms.sum()
                 if total_roe_firms > 0:
                     mean_roe = (roe_vals * roe_firms).sum() / total_roe_firms
        
        if not pd.isna(mean_roe) and mean_roe != 0:
             metrics['roe'] = self._calculate_tier1_metric(
                 'roe', mean_roe, cv, weight=0.10  # Typically 10 weight unless overridden
             )
        
        # === Operating Margin (Tier 1: Synthetic Z-Score) ===
        # Estimated from ROIC since not directly in HTML data
        if not pd.isna(mean_operating_margin):
            metrics['operating_margin'] = self._calculate_tier1_metric(
                'operating_margin', mean_operating_margin, cv, weight=0.08
            )
        
        # === Tier 2 Metrics (Multiplier-based, estimated) ===
        # These don't have direct Damodaran data, so we use estimated values
        metrics['gross_margin'] = {
            'scoring_mode': 'tier_2_multiplier',
            'mean': self._estimate_gross_margin(sector_name),
            'inverse_metric': False,
            'weight': 0.02,
            'data_quality': 'estimated'
        }
        
        metrics['net_margin'] = {
            'scoring_mode': 'tier_2_multiplier',
            'mean': self._estimate_net_margin(mean_operating_margin) if not pd.isna(mean_operating_margin) else 0.10,
            'weight': 0.02,
            'data_quality': 'derived'
        }
        
        # === Beta (for DCF WACC calculation) ===
        # Extract average Beta from beta_df for this sector  
        mean_beta = None
        if len(sector_beta) > 0:
            beta_col = self._get_column_safe(self.beta_df, self.BETA_COLUMNS['beta'])
            num_firms_col = self._get_column_safe(self.beta_df, self.BETA_COLUMNS['num_firms'])
            
            if beta_col:
                beta_series = pd.to_numeric(sector_beta[beta_col], errors='coerce')
                
                # Calculate weighted mean if we have firm counts
                if num_firms_col and num_firms_col in sector_beta.columns:
                    total_firms_beta = sector_beta[num_firms_col].sum()
                    if total_firms_beta > 0:
                        mean_beta = (beta_series * sector_beta[num_firms_col]).sum() / total_firms_beta
                else:
                    mean_beta = beta_series.mean()
                
                if not pd.isna(mean_beta) and mean_beta > 0:
                    metrics['beta'] = {
                        'mean': float(mean_beta),
                        'note': 'Industry average Beta (not stock-specific)',
                        'usage': 'DCF WACC calculation'
                    }
        
        # === NEW: Valuation Multiples (for valuation module) ===
        # These are stored as raw values, not scoring dicts
        valuation_multiples = {}
        
        # PE Ratio
        if self.pe_df is not None:
            # Safely check if required columns exist
            industry_col = self._get_column_safe(self.pe_df, self.PE_COLUMNS['industry'])
            num_firms_col = self._get_column_safe(self.pe_df, self.PE_COLUMNS['num_firms'])
            
            if industry_col and num_firms_col:
                sector_pe = self.pe_df[self.pe_df[industry_col].isin(industries)]
                if len(sector_pe) > 0:
                    pe_firms = sector_pe[num_firms_col]
                    total_pe_firms = pe_firms.sum()
                    
                    if total_pe_firms > 0:
                        # Current PE
                        pe_current_col = self._get_column_safe(sector_pe, self.PE_COLUMNS['pe_current'])
                        if pe_current_col:
                            pe_vals = pd.to_numeric(sector_pe[pe_current_col], errors='coerce')
                            valuation_multiples['pe_current'] = float((pe_vals * pe_firms).sum() / total_pe_firms)
                        
                        # Trailing PE
                        pe_trailing_col = self._get_column_safe(sector_pe, self.PE_COLUMNS['pe_trailing'])
                        if pe_trailing_col:
                            pe_vals = pd.to_numeric(sector_pe[pe_trailing_col], errors='coerce')
                            valuation_multiples['pe_trailing'] = float((pe_vals * pe_firms).sum() / total_pe_firms)
                        
                        # Forward PE
                        pe_forward_col = self._get_column_safe(sector_pe, self.PE_COLUMNS['pe_forward'])
                        if pe_forward_col:
                            pe_vals = pd.to_numeric(sector_pe[pe_forward_col], errors='coerce')
                            valuation_multiples['pe_forward'] = float((pe_vals * pe_firms).sum() / total_pe_firms)
        
        # PB Ratio
        if self.pbv_df is not None:
            industry_col = self._get_column_safe(self.pbv_df, self.PBV_COLUMNS['industry'])
            num_firms_col = self._get_column_safe(self.pbv_df, self.PBV_COLUMNS['num_firms'])
            
            if industry_col and num_firms_col:
                sector_pb = self.pbv_df[self.pbv_df[industry_col].isin(industries)]
                if len(sector_pb) > 0:
                    pb_firms = sector_pb[num_firms_col]
                    total_pb_firms = pb_firms.sum()
                    
                    if total_pb_firms > 0:
                        pb_col = self._get_column_safe(sector_pb, self.PBV_COLUMNS['pb_ratio'])
                        if pb_col:
                            pb_vals = pd.to_numeric(sector_pb[pb_col], errors='coerce')
                            valuation_multiples['pb_ratio'] = float((pb_vals * pb_firms).sum() / total_pb_firms)
        
        # PS Ratio
        if self.ps_df is not None:
            industry_col = self._get_column_safe(self.ps_df, self.PS_COLUMNS['industry'])
            num_firms_col = self._get_column_safe(self.ps_df, self.PS_COLUMNS['num_firms'])
            
            if industry_col and num_firms_col:
                sector_ps = self.ps_df[self.ps_df[industry_col].isin(industries)]
                if len(sector_ps) > 0:
                    ps_firms = sector_ps[num_firms_col]
                    total_ps_firms = ps_firms.sum()
                    
                    if total_ps_firms > 0:
                        ps_col = self._get_column_safe(sector_ps, self.PS_COLUMNS['ps_ratio'])
                        if ps_col:
                            ps_vals = pd.to_numeric(sector_ps[ps_col], errors='coerce')
                            valuation_multiples['ps_ratio'] = float((ps_vals * ps_firms).sum() / total_ps_firms)

                        # EV/Sales (moved from EV/EBITDA block)
                        ev_sales_col = self._get_column_safe(sector_ps, self.PS_COLUMNS['ev_sales'])
                        if ev_sales_col:
                            ev_vals = pd.to_numeric(sector_ps[ev_sales_col], errors='coerce')
                            valuation_multiples['ev_sales'] = float((ev_vals * ps_firms).sum() / total_ps_firms)
        
        # EV/EBITDA
        if self.ev_ebitda_df is not None:
            industry_col = self._get_column_safe(self.ev_ebitda_df, self.EV_EBITDA_COLUMNS['industry'])
            num_firms_col = self._get_column_safe(self.ev_ebitda_df, self.EV_EBITDA_COLUMNS['num_firms'])
            
            if industry_col and num_firms_col:
                sector_ev = self.ev_ebitda_df[self.ev_ebitda_df[industry_col].isin(industries)]
                if len(sector_ev) > 0:
                    ev_firms = sector_ev[num_firms_col]
                    total_ev_firms = ev_firms.sum()
                    
                    if total_ev_firms > 0:
                        # EV/EBITDA
                        ev_ebitda_col = self._get_column_safe(sector_ev, self.EV_EBITDA_COLUMNS['ev_ebitda'])
                        if ev_ebitda_col:
                            ev_vals = pd.to_numeric(sector_ev[ev_ebitda_col], errors='coerce')
                            valuation_multiples['ev_ebitda'] = float((ev_vals * ev_firms).sum() / total_ev_firms)
                        

        
        # Dividend Yield
        if self.div_yield_df is not None:
            industry_col = self._get_column_safe(self.div_yield_df, self.DIV_YIELD_COLUMNS['industry'])
            num_firms_col = self._get_column_safe(self.div_yield_df, self.DIV_YIELD_COLUMNS['num_firms'])
            
            if industry_col and num_firms_col:
                sector_div = self.div_yield_df[self.div_yield_df[industry_col].isin(industries)]
                if len(sector_div) > 0:
                    div_firms = sector_div[num_firms_col]
                    total_div_firms = div_firms.sum()
                    
                    if total_div_firms > 0:
                        # Dividend Yield
                        div_yield_col = self._get_column_safe(sector_div, self.DIV_YIELD_COLUMNS['dividend_yield'])
                        if div_yield_col:
                            div_vals = sector_div[div_yield_col]
                            # Handle percentage strings and #DIV/0! errors
                            if div_vals.dtype == 'object':
                                # Replace #DIV/0! with NaN before conversion
                                div_vals = div_vals.replace('#DIV/0!', pd.NA)
                                div_vals = div_vals.str.strip('%')
                            div_vals = pd.to_numeric(div_vals, errors='coerce')  # Coerce errors to NaN
                            # Calculate weighted average, ignoring NaN values
                            valid_mask = ~div_vals.isna()
                            if valid_mask.sum() > 0:
                                valuation_multiples['dividend_yield'] = float(
                                    (div_vals[valid_mask] * div_firms[valid_mask]).sum() / div_firms[valid_mask].sum()
                                )
                        
                        # Payout Ratio
                        payout_col = self._get_column_safe(sector_div, self.DIV_YIELD_COLUMNS['payout_ratio'])
                        if payout_col:
                            payout_vals = sector_div[payout_col]
                            # Handle percentage strings and #DIV/0! errors
                            if payout_vals.dtype == 'object':
                                payout_vals = payout_vals.replace('#DIV/0!', pd.NA)
                                payout_vals = payout_vals.str.strip('%')
                            payout_vals = pd.to_numeric(payout_vals, errors='coerce')
                            valid_mask = ~payout_vals.isna()
                            if valid_mask.sum() > 0:
                                valuation_multiples['payout_ratio'] = float(
                                    (payout_vals[valid_mask] * div_firms[valid_mask]).sum() / div_firms[valid_mask].sum()
                                )
        
        # Add valuation_multiples to metrics if any exist
        if valuation_multiples:
            metrics['valuation_multiples'] = valuation_multiples
            logger.info(f"{sector_name}: Valuation multiples - {list(valuation_multiples.keys())}")
        
        # Build sector summary
        sector_data = {
            'id': sector_name.upper().replace(' ', '_')[:4],
            'sample_size': int(total_firms),
            'volatility_profile': {
                'cv_operating_income': round(float(cv), 4),
                'risk_rating': self._classify_risk(cv)
            },
            'metrics': metrics
        }
        
        logger.info(f"{sector_name}: {total_firms} firms, CV={cv:.4f}, {len(metrics)} metrics")
        return sector_data
    
    def _calculate_tier1_metric(self, metric_name: str, mean: float, cv: float, weight: float) -> Dict:
        """
        Calculate Tier 1 (Synthetic Z-Score) metric with breakpoints.
        
        Args:
            metric_name: Metric identifier
            mean: Mean value
            cv: Coefficient of variation
            weight: Scoring weight
            
        Returns:
            Metric dictionary with synthetic breakpoints
        """
        damping = self.DAMPING_FACTORS.get(metric_name, 1.0)
        derived_sigma = mean * cv * damping
        
        return {
            'scoring_mode': 'tier_1_synthetic',
            'unit': 'percentage',
            'mean': round(float(mean), 4),
            'cv_source': round(float(cv), 4),
            'damping_factor': damping,
            'derived_sigma': round(float(derived_sigma), 4),
            'synthetic_breakpoints': {
                'p10': round(float(mean - 1.282 * derived_sigma), 4),
                'p25': round(float(mean - 0.675 * derived_sigma), 4),
                'p50': round(float(mean), 4),
                'p75': round(float(mean + 0.675 * derived_sigma), 4),
                'p90': round(float(mean + 1.282 * derived_sigma), 4),
            },
            'weight': weight,
            'data_quality': 'high'
        }
    
    @staticmethod
    def _classify_risk(cv: float) -> str:
        """Classify risk level based on CV."""
        if cv < 0.4:
            return 'Low'
        elif cv < 0.6:
            return 'Medium'
        elif cv < 0.8:
            return 'High'
        else:
            return 'Very High'
    
    @staticmethod
    def _estimate_gross_margin(sector_name: str) -> float:
        """
        Estimate gross margin for sector (no direct Damodaran data).
        These are rough industry averages.
        """
        estimates = {
            'Technology': 0.62,
            'Healthcare': 0.55,
            'Financials': 0.85,  # Financials have different structure
            'Consumer Discretionary': 0.35,
            'Consumer Staples': 0.30,
            'Energy': 0.40,
            'Industrials': 0.30,
            'Materials': 0.25,
            'Real Estate': 0.65,
            'Utilities': 0.50,
            'Communication Services': 0.55,
        }
        return estimates.get(sector_name, 0.40)
    
    @staticmethod
    def _estimate_net_margin(operating_margin: float) -> float:
        """
        Estimate net margin from operating margin.
        Typically net margin is ~60-70% of operating margin (after interest & tax).
        """
        return operating_margin * 0.65
    
    def generate_all_sectors(self) -> Dict[str, Dict]:
        """
        Generate statistics for all 11 GICS sectors.
        
        Returns:
            Dictionary of sector data
        """
        logger.info("Generating statistics for all sectors...")
        
        all_sectors = {}
        for sector_name, industries in SECTOR_MAPPING.items():
            sector_data = self.aggregate_sector(sector_name, industries)
            if sector_data:
                all_sectors[sector_name] = sector_data
        
        logger.info(f"Generated data for {len(all_sectors)} sectors")
        return all_sectors

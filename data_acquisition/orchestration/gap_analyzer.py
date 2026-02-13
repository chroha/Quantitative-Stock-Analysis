"""
Gap Analyzer - Data Integrity & Completeness Check
"""
from typing import Dict, Any, List
from utils.unified_schema import StockData
from utils.logger import setup_logger
from config.analysis_config import GAP_THRESHOLDS

logger = setup_logger('gap_analyzer')

class GapAnalyzer:
    """
    Analyzes StockData to identify missing critical information.
    Drives the decision logic for fallback strategies.
    
    Checks for:
    1. Valuation Metrics (PE, PB, PS)
    2. Basic Info (Sector, Industry, Market Cap)
    3. Forward Estimates (EPS, Revenue)
    4. EBITDA (Critical for Valuation)
    5. Historical Financial Depth (min 4 years)
    """
    
    def analyze(self, data: StockData) -> Dict[str, Any]:
        """
        Run comprehensive gap analysis.
        Returns a dictionary of flags indicating what is missing.
        """
        if not data or not data.profile:
            return {'critical_error': 'No profile data'}
            
        profile = data.profile
        
        # 1. Valuation Gaps
        missing_valuation = False
        if not profile.std_pe_ratio or not profile.std_pe_ratio.value: missing_valuation = True
        if not profile.std_pb_ratio or not profile.std_pb_ratio.value: missing_valuation = True
        if not profile.std_ps_ratio or not profile.std_ps_ratio.value: missing_valuation = True
        
        # 2. Basic Info Gaps
        missing_basic = False
        if not profile.std_sector or not profile.std_sector.value: missing_basic = True
        if not profile.std_industry or not profile.std_industry.value: missing_basic = True
        if not profile.std_market_cap or not profile.std_market_cap.value: missing_basic = True
        
        # 3. Estimates Gaps
        missing_estimates = False
        if not data.analyst_targets: missing_estimates = True
        if not profile.std_forward_pe or not profile.std_forward_pe.value: missing_estimates = True
        
        # 3.5 Surprise History (for Forecast Data completeness)
        missing_surprise_history = False
        if data.forecast_data:
            if not data.forecast_data.std_earnings_surprise_history:
                missing_surprise_history = True
        else:
            missing_surprise_history = True
        
        # 4. EBITDA Gap (Critical)
        missing_ebitda = True
        # Check Income Statements (TTM or recent FY)
        if data.income_statements:
            # Check latest statement (usually TTM or recent FY)
            latest = data.income_statements[0]
            if latest.std_ebitda and latest.std_ebitda.value:
                missing_ebitda = False
            
        # 5. Financial History Depth
        history_gaps = self._check_history_depth(data)
        
        # 6. Critical Financial Fields (Tax, Interest, etc)
        financial_gaps = self._check_financial_fields(data)
        
        # Decision Logic
        needs_phase3_fmp = False
        if GAP_THRESHOLDS.get('PHASE3_FMP_ENABLED', True):
            if missing_valuation and GAP_THRESHOLDS.get('FETCH_ON_MISSING_VALUATION', True):
                needs_phase3_fmp = True
            elif missing_estimates and GAP_THRESHOLDS.get('FETCH_ON_MISSING_ESTIMATES', True):
                needs_phase3_fmp = True
            elif history_gaps['is_shallow']:
                needs_phase3_fmp = True
            elif missing_ebitda: # FMP often has EBITDA
                needs_phase3_fmp = True
                
        needs_phase4_av = False
        if GAP_THRESHOLDS.get('PHASE4_AV_ENABLED', True):
            # If still missing critical financials after FMP (or if FMP disabled)
            if financial_gaps['is_incomplete']:
                needs_phase4_av = True
            elif missing_basic:
                needs_phase4_av = True

        return {
            'missing_valuation': missing_valuation,
            'missing_basic': missing_basic,
            'missing_estimates': missing_estimates,
            'missing_surprise_history': missing_surprise_history,
            'missing_ebitda': missing_ebitda,
            'history_gaps': history_gaps,
            'financial_gaps': financial_gaps,
            'needs_phase3_fmp': needs_phase3_fmp,
            'needs_phase4_av': needs_phase4_av
        }

    def _check_history_depth(self, data: StockData) -> Dict[str, Any]:
        """Check if we have enough historical years (FY only)."""
        min_years = 4
        
        # Count only Annual statements (FY) to avoid counting Quarters as Years
        inc_count = len([s for s in data.income_statements if s.std_period_type == 'FY'])
        bal_count = len([s for s in data.balance_sheets if s.std_period_type == 'FY'])
        cf_count = len([s for s in data.cash_flows if s.std_period_type == 'FY'])
        
        # If no FY data found at all (e.g. only TTM/Q), fall back to raw count but warn?
        # Actually, for deep history we WANT FY. 
        # But some sources might not label correctly? 
        # Taking a safe bet: if FY count is 0 but len > 4, we might have an issue with labeling.
        # For now, strict FY check is safer for "History Depth".
        
        is_shallow = (inc_count < min_years) or (bal_count < min_years) or (cf_count < min_years)
        
        return {
            'is_shallow': is_shallow,
            'income_years': inc_count,
            'balance_years': bal_count,
            'cashflow_years': cf_count
        }

    def _check_financial_fields(self, data: StockData) -> Dict[str, Any]:
        """Check for specific critical fields in latest statement."""
        if not data.income_statements:
            return {'is_incomplete': True, 'reason': 'No income statements'}
            
        latest = data.income_statements[0]
        missing = {}
        
        # Check specific fields
        if not latest.std_income_tax_expense or not latest.std_income_tax_expense.value:
            missing['tax'] = True
        if not latest.std_interest_expense or not latest.std_interest_expense.value:
            missing['interest'] = True
        if not latest.std_operating_income or not latest.std_operating_income.value:
            missing['op_income'] = True
            
        return {
            'is_incomplete': len(missing) > 0,
            'details': missing
        }

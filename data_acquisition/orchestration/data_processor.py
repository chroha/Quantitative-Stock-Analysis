"""
Data Processor - Post-Fetching Sanitization & Logic
"""
from typing import List, Optional
from datetime import datetime
import pandas as pd

from utils.unified_schema import StockData, IncomeStatement, FieldWithSource, DataSource
from utils.logger import setup_logger

logger = setup_logger('data_processor')

class DataProcessor:
    """
    Handles data transformation after fetching is complete.
    Responsibilities:
    1. Sanitize/Normalize data (cleaning None values etc)
    2. Construct Synthetic TTM (Trailing Twelve Months) if missing
    3. Calculate derived metrics
    """
    
    def sanitize_data(self, data: StockData) -> StockData:
        """Run standard sanitization."""
        # Ensure lists are sorted by date descending
        if data.income_statements:
            data.income_statements.sort(key=lambda x: str(x.std_period), reverse=True)
        if data.balance_sheets:
            data.balance_sheets.sort(key=lambda x: str(x.std_period), reverse=True)
        if data.cash_flows:
            data.cash_flows.sort(key=lambda x: str(x.std_period), reverse=True)
            
        return data

    def construct_synthetic_ttm(self, data: StockData) -> StockData:
        """
        Construct a TTM Income Statement if one is clearly missing.
        Logic: TTM = Sum of latest 4 consecutive quarters.
        """
        if not data.income_statements:
            return data
            
        # 1. Check if TTM already exists
        # Check explicit 'TTM' type or string label
        has_ttm = any(s.std_period_type == 'TTM' or 'TTM' in str(s.std_period).upper() for s in data.income_statements)
        
        if has_ttm:
            logger.info("TTM data already present, skipping synthesis.")
            return data

        # 2. Gather Quarterly Data
        quarters = [s for s in data.income_statements if s.std_period_type == 'Q']
        # Sort descending (latest first)
        quarters.sort(key=lambda x: str(x.std_period), reverse=True)
        
        if len(quarters) < 4:
            logger.warning(f"Insufficient quarterly data for TTM synthesis (Found {len(quarters)}, need 4)")
            return data
            
        # 3. Validation: Are they consecutive?
        if not self._validate_consecutive_quarters(quarters[:4]):
            logger.warning(f"Top 4 quarters are not consecutive,aborting TTM synthesis")
            return data
            
        target_qs = quarters[:4]
        
        logger.info(f"Synthesizing TTM from consecutive quarters: {[q.std_period for q in target_qs]}")
        
        # 4. Summation Logic
        ttm_stmt = self._sum_quarters(target_qs)
        
        # 5. Insert at top
        data.income_statements.insert(0, ttm_stmt)
        
        return data

    def _sum_quarters(self, quarters: List[IncomeStatement]) -> IncomeStatement:
        """Sum 4 quarters into one TTM statement."""
        # Create empty statement
        ttm = IncomeStatement(
            std_period="Synthetic_TTM",
            std_period_type="TTM"
        )
        
        # List of fields to sum (Numeric Flow Variables)
        # We need to explicitly check schema fields.
        sum_fields = [
            'std_revenue', 'std_cost_of_revenue', 'std_gross_profit', 
            'std_operating_expenses', 'std_operating_income', 'std_pretax_income', 
            'std_interest_expense', 'std_income_tax_expense', 'std_net_income', 
            'std_ebitda'
        ]
        
        # Initialize fields with 0
        for field in sum_fields:
            total = 0.0
            count = 0
            sources = set()
            
            for q in quarters:
                val_obj = getattr(q, field, None)
                if val_obj and val_obj.value is not None:
                    total += val_obj.value
                    count += 1
                    if val_obj.source:
                        sources.add(val_obj.source)
            
            # Only set if we have data from all 4 quarters? 
            # Or at least 1? Ideally 4 for accuracy. 
            # If we sum 3 quarters, TTM is wrong.
            if count == 4:
                source_str = f"synthetic_sum({','.join(sources)})"
                setattr(ttm, field, FieldWithSource(value=total, source='normalized'))
            else:
                # If incomplete data for a field, leave as None
                pass
                
        # Non-Sum fields (e.g. EPS is weighted average, but simple sum of 4 Qs is a decent approximation for Basic EPS)
        # EPS is strictly: Net Income / Weighted Shares.
        # Summing EPS is "okay" approximation but not exact if shares changed.
        # Let's sum EPS for simplicity as per common practice if shares stable.
        eps_total = 0.0
        eps_count = 0
        for q in quarters:
            if q.std_eps and q.std_eps.value:
                eps_total += q.std_eps.value
                eps_count += 1
        
        if eps_count == 4:
            ttm.std_eps = FieldWithSource(value=eps_total, source='normalized')

        # Also sum Diluted EPS
        eps_diluted_total = 0.0
        eps_diluted_count = 0
        for q in quarters:
            if q.std_eps_diluted and q.std_eps_diluted.value:
                eps_diluted_total += q.std_eps_diluted.value
                eps_diluted_count += 1
        
        if eps_diluted_count == 4:
            ttm.std_eps_diluted = FieldWithSource(value=eps_diluted_total, source='normalized')
            
        # Copy Shares Outstanding from latest quarter (Best point-in-time approximation)
        latest_q = quarters[0] # Sorted descending above
        if latest_q.std_shares_outstanding:
             ttm.std_shares_outstanding = latest_q.std_shares_outstanding
             
        return ttm
    
    def _validate_consecutive_quarters(self, quarters: List[IncomeStatement]) -> bool:
        """
        Validate that quarters are truly consecutive (Q4, Q3, Q2, Q1 of same year, or across year boundary).
        
        Args:
            quarters: List of 4 quarterly statements (sorted desc, newest first)
            
        Returns:
            True if consecutive, False otherwise
        """
        if len(quarters) != 4:
            return False
        
        try:
            # Parse dates
            dates = []
            for q in quarters:
                period_str = q.std_period
                if period_str.startswith('TTM-'):
                    period_str = period_str[4:]
                dt = datetime.strptime(period_str, '%Y-%m-%d')
                dates.append(dt)
            
            # Check intervals (should be ~91 days between consecutive quarters)
            # Allow 80-100 days to account for fiscal calendar variations
            for i in range(len(dates) - 1):
                days_diff = (dates[i] - dates[i+1]).days
                if not (80 <= days_diff <= 100):
                    logger.warning(f"Non-consecutive quarters detected: {dates[i]} to {dates[i+1]} = {days_diff} days")
                    return False
            
            return True
        except Exception as e:
            logger.warning(f"Could not validate quarter consecutiveness: {e}")
            # If we can't parse, fall back to allowing synthesis (backward compatibility)
            return True

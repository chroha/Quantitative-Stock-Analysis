"""
Completeness Reporter - Visual Scorecard for Data Acquisition.

Generates a terminal-based report showing the status of profile, prices,
and financial statement completeness with a year-by-year matrix.
"""

from typing import Dict, Any
from utils.unified_schema import StockData
from data_acquisition.stock_data.field_validator import OverallValidationResult, FieldValidator

class CompletenessReporter:
    """
    Generates a visual scorecard for stock data completeness.
    """
    
    @staticmethod
    def generate_scorecard(symbol: str, data: StockData, validation_result: OverallValidationResult):
        """
        Print a formatted scorecard to the terminal.
        """
        print(f"\n{'='*60}")
        print(f" DATA COMPLETENESS SCORECARD: {symbol}")
        print(f"{'='*60}")
        
        # 1. Profile Health
        profile = data.profile
        profile_fields = ['std_sector', 'std_industry', 'std_market_cap', 'std_beta', 'std_pe_ratio']
        filled_profile = [f for f in profile_fields if profile and getattr(profile, f, None) is not None]
        
        print(f" PROFILE HEALTH:  [{'#' * len(filled_profile)}{' ' * (len(profile_fields)-len(filled_profile))}] "
              f"{len(filled_profile)}/{len(profile_fields)} Core Fields")
        if profile and profile.std_sector:
            print(f"   Sector:   {profile.std_sector.value}")
        
        # 2. Price History Depth
        price_depth = len(data.price_history)
        print(f" PRICE HISTORY:  {price_depth} Days Found")
        
        # 3. Financial Statement Matrix
        validator = FieldValidator()
        matrix = validator.get_completeness_matrix(validation_result)
        
        if not matrix:
            print("\n FINANCIALS:      NO DATA FOUND")
        else:
            print("\n FINANCIALS MATRIX (FY/Q):")
            years = sorted(matrix.keys(), reverse=True)
            print(f" {'Year':<6} | {'Income':<12} | {'Balance':<12} | {'CashFlow':<12}")
            print(f" {'-'*6}-+-{'-'*12}-+-{'-'*12}-+-{'-'*12}")
            
            for year in years[:6]: # Show last 6 years
                row = matrix[year]
                inc = row.get('income', 'N/A')
                bal = row.get('balance', 'N/A')
                cf = row.get('cashflow', 'N/A')
                
                # Format to be concise
                def fmt(s):
                    if s == "OK": return "√ OK"
                    if "MISSING" in s: return f"!! {s}"
                    return s
                
                print(f" {year:<6} | {fmt(inc):<12} | {fmt(bal):<12} | {fmt(cf):<12}")
        
        # 4. Critical Missing Fields Summary
        missing = validator.get_missing_fields_summary(validation_result)
        req = missing.get('required', [])
        if req:
            print("\n [!] CRITICAL MISSING FIELDS (Blocks Calculations):")
            print(f"     {', '.join(req)}")
            
        print(f"{'='*60}\n")

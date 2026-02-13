"""
Capital Allocation & Shareholder Returns Calculators.

Calculates:
1. Share Dilution (5-year time-weighted CAGR)
2. Capex Intensity (3-year average)
3. SBC Impact (3-year average)
4. Debt to Equity
"""

from typing import Optional, List, Any
from dataclasses import dataclass, field
from datetime import datetime
from fundamentals.financial_data.calculator_base import CalculatorBase, CalculationResult, MetricWarning


@dataclass
class CapitalAllocationMetrics:
    """Container for capital allocation metrics (value + source)."""
    share_dilution_cagr_5y: Optional[Any] = None
    capex_intensity_3y: Optional[Any] = None
    sbc_impact_3y: Optional[Any] = None
    debt_to_equity: Optional[Any] = None
    
    calculation_date: datetime = field(default_factory=datetime.now)
    warnings: list[MetricWarning] = field(default_factory=list)


class CapitalAllocationCalculator(CalculatorBase):
    """Calculates capital allocation and shareholder return metrics with source tracking."""
    
    def calculate_share_dilution_cagr(
        self,
        shares_outstanding_data: List[tuple[float, str]]
    ) -> CalculationResult:
        """Calculate 5-year time-weighted Share Dilution CAGR with source tracking."""
        # Unpack
        shares_outstanding = [x[0] for x in shares_outstanding_data]
        sources = [x[1] for x in shares_outstanding_data]
        
        result = self.calculate_time_weighted_cagr(shares_outstanding, 'share_dilution_cagr_5y')
        
        # Merge sources
        result.source = self.merge_sources(sources)
        
        if result.value is not None:
            if result.value < 0:
                result.add_warning('share_dilution', 'out_of_bounds', f'Share count decreased by {abs(result.value)*100:.2f}% (buybacks)', 'info', result.value)
            elif result.value > 0.05:
                result.add_warning('share_dilution', 'out_of_bounds', f'High dilution: {result.value*100:.2f}% CAGR', 'warning', result.value)
        
        return result
    
    def calculate_capex_intensity(
        self,
        capex_values_data: List[tuple[float, str]],
        ocf_values_data: List[tuple[float, str]]
    ) -> CalculationResult:
        """Calculate Capex Intensity (3-year average) with source tracking."""
        result = CalculationResult(value=None)
        
        capex_values = [x[0] for x in capex_values_data]
        ocf_values = [x[0] for x in ocf_values_data]
        all_sources = [x[1] for x in capex_values_data] + [x[1] for x in ocf_values_data]
        
        if len(capex_values) < 3 or len(ocf_values) < 3:
            result.add_warning('capex_intensity', 'data_missing', f'Need 3 years of data', 'error')
            return result
        
        capex_3y = capex_values[:3]
        ocf_3y = ocf_values[:3]
        
        ratios = []
        for i, (capex, ocf) in enumerate(zip(capex_3y, ocf_3y)):
            if capex is None or ocf is None: continue
            if ocf == 0: continue
            ratio = abs(capex) / ocf
            ratios.append(ratio)
            
            if ratio > 1.0:
                 result.add_warning('capex_intensity', 'out_of_bounds', f'Year {i}: CapEx exceeds OCF', 'warning', ratio)
        
        if ratios:
            avg_intensity = sum(ratios) / len(ratios)
            result.value = avg_intensity
            result.source = self.merge_sources(all_sources)
            result.intermediate_values = {'yearly_ratios': ratios, 'num_years_used': len(ratios)}
        else:
            result.add_warning('capex_intensity', 'calculation_error', 'No valid ratios calculated', 'error')
            
        return result
    
    def calculate_sbc_impact(
        self,
        sbc_values_data: List[tuple[float, str]],
        ocf_values_data: List[tuple[float, str]]
    ) -> CalculationResult:
        """Calculate SBC Impact (3-year average) with source tracking."""
        result = CalculationResult(value=None)
        
        sbc_values = [x[0] for x in sbc_values_data]
        ocf_values = [x[0] for x in ocf_values_data]
        all_sources = [x[1] for x in sbc_values_data] + [x[1] for x in ocf_values_data]
        
        if len(sbc_values) < 3 or len(ocf_values) < 3:
            result.add_warning('sbc_impact', 'data_missing', 'Need 3 years of data', 'error')
            return result
        
        sbc_3y = sbc_values[:3]
        ocf_3y = ocf_values[:3]
        
        ratios = []
        for i, (sbc, ocf) in enumerate(zip(sbc_3y, ocf_3y)):
            if sbc is None or ocf is None: continue
            if ocf == 0: continue
            ratio = sbc / ocf
            ratios.append(ratio)
            
            if ratio > 0.3:
                result.add_warning('sbc_impact', 'out_of_bounds', f'Year {i}: High SBC ({ratio*100:.1f}% of OCF)', 'warning', ratio)
        
        if ratios:
            avg_impact = sum(ratios) / len(ratios)
            result.value = avg_impact
            result.source = self.merge_sources(all_sources)
            result.intermediate_values = {'yearly_ratios': ratios, 'num_years_used': len(ratios)}
        else:
             result.add_warning('sbc_impact', 'calculation_error', 'No valid ratios calculated', 'error')
        
        return result
    
    def calculate_debt_to_equity(
        self,
        total_debt_data: tuple[Optional[float], str],
        shareholders_equity_data: tuple[Optional[float], str]
    ) -> CalculationResult:
        """Calculate Debt to Equity ratio with source tracking."""
        total_debt, debt_src = total_debt_data
        equity, eq_src = shareholders_equity_data
        
        result = CalculationResult(value=None)
        
        if equity is not None and equity <= 0:
            result.add_warning('debt_to_equity', 'calculation_error', f"Shareholders' equity is {equity} (<=0)", 'error')
            return result
        
        ratio = self.safe_divide(total_debt, equity, 'debt_to_equity', result)
        result.value = ratio
        result.source = self.merge_sources([debt_src, eq_src])
        
        return result
    
    def calculate_all(self, stock_data) -> CapitalAllocationMetrics:
        """Calculate all capital allocation metrics from stock data."""
        metrics = CapitalAllocationMetrics()
        
        # Extract shares outstanding (5 years, oldest to newest)
        shares_data = []
        # Filter for Annual statements first, consistent with other calculators
        annual_income = [s for s in stock_data.income_statements 
                         if getattr(s, 'std_period_type', 'FY') in ['FY', 'TTM']]
        
        for stmt in reversed(annual_income[:5]):
            shares_data.append(self.get_field_with_source(stmt, 'std_shares_outstanding'))
        
        # Calculate Share Dilution CAGR
        if len(shares_data) >= 2:
            dilution_result = self.calculate_share_dilution_cagr(shares_data)
            metrics.share_dilution_cagr_5y = {'value': dilution_result.value, 'source': dilution_result.source}
            metrics.warnings.extend(dilution_result.warnings)
        
        # Get most recent 3 years of cash flow data
        annual_cashflow = [s for s in stock_data.cash_flows 
                           if getattr(s, 'std_period_type', 'FY') in ['FY', 'TTM']]
                           
        if len(annual_cashflow) >= 3:
            # Newest first
            recent_cfs = annual_cashflow[:3]
            ocfs_data = [self.get_field_with_source(cf, 'std_operating_cash_flow') for cf in recent_cfs]
            capexs_data = [self.get_field_with_source(cf, 'std_capex') for cf in recent_cfs]
            sbcs_data = [self.get_field_with_source(cf, 'std_stock_based_compensation') for cf in recent_cfs]
            
            # Calculate Capex Intensity
            capex_result = self.calculate_capex_intensity(capexs_data, ocfs_data)
            metrics.capex_intensity_3y = {'value': capex_result.value, 'source': capex_result.source}
            metrics.warnings.extend(capex_result.warnings)
            
            # Calculate SBC Impact
            sbc_result = self.calculate_sbc_impact(sbcs_data, ocfs_data)
            metrics.sbc_impact_3y = {'value': sbc_result.value, 'source': sbc_result.source}
            metrics.warnings.extend(sbc_result.warnings)
        
        # Calculate Debt to Equity
        annual_balance = [s for s in stock_data.balance_sheets 
                          if getattr(s, 'std_period_type', 'FY') in ['FY', 'TTM']]
        
        if annual_balance:
            latest_bs = annual_balance[0]
            total_debt_data = self.get_field_with_source(latest_bs, 'std_total_debt')
            equity_data = self.get_field_with_source(latest_bs, 'std_shareholder_equity')
            
            de_result = self.calculate_debt_to_equity(total_debt_data, equity_data)
            metrics.debt_to_equity = {'value': de_result.value, 'source': de_result.source}
            metrics.warnings.extend(de_result.warnings)
        
        return metrics


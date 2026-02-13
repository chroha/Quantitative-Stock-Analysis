"""
Growth Quality Calculators.

Calculates:
1. FCF CAGR (5-year time-weighted)
2. Net Income CAGR (5-year time-weighted)
3. Revenue CAGR (5-year time-weighted)
4. Earnings Quality (3-year average)
5. FCF to Debt Ratio
"""

from typing import Optional, List, Any
from dataclasses import dataclass, field
from datetime import datetime
from fundamentals.financial_data.calculator_base import CalculatorBase, CalculationResult, MetricWarning


@dataclass
class GrowthMetrics:
    """Container for growth quality metrics (value + source)."""
    fcf_cagr_5y: Optional[Any] = None
    net_income_cagr_5y: Optional[Any] = None
    revenue_cagr_5y: Optional[Any] = None
    
    earnings_quality_3y: Optional[Any] = None
    fcf_to_debt_ratio: Optional[Any] = None
    fcf_to_debt_is_debt_free: bool = False
    
    calculation_date: datetime = field(default_factory=datetime.now)
    warnings: list[MetricWarning] = field(default_factory=list)
    fcf_latest: Optional[Any] = None  # Added for appendix display


class GrowthCalculator(CalculatorBase):
    """Calculates growth quality indicators with source tracking."""
    
    def calculate_fcf_cagr(
        self,
        operating_cash_flows_data: List[tuple[float, str]],
        capex_values_data: List[tuple[float, str]]
    ) -> CalculationResult:
        """
        Calculate 5-year time-weighted FCF CAGR with source tracking.
        """
        result = CalculationResult(value=None)
        
        # Unpack values for calculation
        operating_cash_flows = [x[0] for x in operating_cash_flows_data]
        capex_values = [x[0] for x in capex_values_data]
        
        if len(operating_cash_flows) != len(capex_values):
            result.add_warning('fcf_cagr', 'data_missing', f'OCF periods ({len(operating_cash_flows)}) != CapEx periods ({len(capex_values)})', 'error')
            return result
        
        # Calculate FCF for each period
        fcf_values = []
        fcf_sources = []
        
        for i, ((ocf, ocf_src), (capex, capex_src)) in enumerate(zip(operating_cash_flows_data, capex_values_data)):
            if ocf is None or capex is None:
                result.add_warning('fcf_cagr', 'data_missing', f'Missing OCF or CapEx at period {i}', 'warning')
                fcf_values.append(None)
                fcf_sources.append('N/A')
            else:
                fcf = ocf + capex  # capex is negative
                fcf_values.append(fcf)
                fcf_sources.append(self.merge_sources([ocf_src, capex_src]))
        
        # Calculate time-weighted CAGR
        cagr_result = self.calculate_time_weighted_cagr(fcf_values, 'fcf_cagr_5y')
        
        # Merge all sources for the CAGR provenance
        cagr_source = self.merge_sources(fcf_sources)
        
        result.value = cagr_result.value
        result.source = cagr_source
        result.warnings.extend(cagr_result.warnings)
        
        # Store detailed provenance for latest FCF
        fcf_values_with_source = []
        for v, s in zip(fcf_values, fcf_sources):
             if v is not None:
                 fcf_values_with_source.append({'value': v, 'source': s})
             else:
                 fcf_values_with_source.append(None)

        result.intermediate_values = {
            'fcf_values': fcf_values, # raw values for other calcs if needed
            'fcf_values_with_source': fcf_values_with_source,
            'growth_rates': cagr_result.intermediate_values.get('growth_rates'),
            'weights': cagr_result.intermediate_values.get('weights_used')
        }
        
        return result
    
    def calculate_net_income_cagr(
        self,
        net_income_values_data: List[tuple[float, str]]
    ) -> CalculationResult:
        """Calculate 5-year time-weighted Net Income CAGR."""
        # Unpack for calculation
        values = [x[0] for x in net_income_values_data]
        sources = [x[1] for x in net_income_values_data]
        
        cagr_res = self.calculate_time_weighted_cagr(values, 'net_income_cagr_5y')
        cagr_res.source = self.merge_sources(sources)
        return cagr_res
    
    def calculate_revenue_cagr(
        self,
        revenue_values_data: List[tuple[float, str]]
    ) -> CalculationResult:
        """Calculate 5-year time-weighted Revenue CAGR."""
        values = [x[0] for x in revenue_values_data]
        sources = [x[1] for x in revenue_values_data]
        
        cagr_res = self.calculate_time_weighted_cagr(values, 'revenue_cagr_5y')
        cagr_res.source = self.merge_sources(sources)
        return cagr_res
    
    def calculate_earnings_quality(
        self,
        operating_cash_flows_data: List[tuple[float, str]],
        net_incomes_data: List[tuple[float, str]]
    ) -> CalculationResult:
        """Calculate Earnings Quality (3-year average)."""
        result = CalculationResult(value=None)
        
        operating_cash_flows = [x[0] for x in operating_cash_flows_data]
        net_incomes = [x[0] for x in net_incomes_data]
        
        # Sources for merging
        all_sources = [x[1] for x in operating_cash_flows_data] + [x[1] for x in net_incomes_data]
        
        if len(operating_cash_flows) < 3 or len(net_incomes) < 3:
            result.add_warning('earnings_quality', 'data_missing', 'Need 3 years of data', 'error')
            return result
        
        ocf_recent = operating_cash_flows[:3]
        ni_recent = net_incomes[:3]
        
        ratios = []
        for i, (ocf, ni) in enumerate(zip(ocf_recent, ni_recent)):
            if ocf is None or ni is None: continue
            if ni == 0: continue
            ratio = ocf / ni
            ratios.append(ratio)
        
        if ratios:
            avg_quality = sum(ratios) / len(ratios)
            result.value = avg_quality
            result.source = self.merge_sources(all_sources)
        
        return result
    
    def calculate_fcf_to_debt_ratio(
        self,
        free_cash_flow_data: tuple[Optional[float], str],
        total_debt_data: tuple[Optional[float], str]
    ) -> CalculationResult:
        """Calculate FCF to Debt Ratio."""
        fcf, fcf_src = free_cash_flow_data
        total_debt, debt_src = total_debt_data
        
        result = CalculationResult(value=None)
        
        if total_debt is not None and total_debt == 0:
            result.add_warning('fcf_to_debt', 'data_missing', 'Company is debt-free', 'info', 0.0)
            result.intermediate_values['debt_free'] = True
            result.source = debt_src
            return result
        
        ratio = self.safe_divide(fcf, total_debt, 'fcf_to_debt', result)
        result.value = ratio
        result.source = self.merge_sources([fcf_src, debt_src])
        result.intermediate_values['debt_free'] = False
        
        return result
    
    def calculate_all(self, stock_data) -> GrowthMetrics:
        """Calculate all growth quality metrics from stock data."""
        metrics = GrowthMetrics()
        
        annual_income = [s for s in stock_data.income_statements 
                         if getattr(s, 'std_period_type', 'FY') in ['FY', 'TTM']]
        
        annual_cashflow = [s for s in stock_data.cash_flows 
                           if getattr(s, 'std_period_type', 'FY') in ['FY', 'TTM']]

        if len(annual_income) < 5:
            self.logger.warning(f"Insufficient annual income statements: {len(annual_income)}")
        if len(annual_cashflow) < 5:
            self.logger.warning(f"Insufficient annual cash flows: {len(annual_cashflow)}")
        
        # Extract revenue and net income (5 years, oldest to newest)
        revenues_data = []
        net_incomes_data = []
        # Sorted desc (newest first). Slice first 5, then reverse to get Oldest->Newest
        for stmt in reversed(annual_income[:5]):
            revenues_data.append(self.get_field_with_source(stmt, 'std_revenue'))
            net_incomes_data.append(self.get_field_with_source(stmt, 'std_net_income'))
        
        # Extract OCF and CapEx (5 years, oldest to newest)
        ocfs_data = []
        capexs_data = []
        for cf in reversed(annual_cashflow[:5]):
            ocfs_data.append(self.get_field_with_source(cf, 'std_operating_cash_flow'))
            capexs_data.append(self.get_field_with_source(cf, 'std_capex'))
        
        # Calculate Revenue CAGR
        if len(revenues_data) >= 2:
            revenue_cagr = self.calculate_revenue_cagr(revenues_data)
            metrics.revenue_cagr_5y = {'value': revenue_cagr.value, 'source': revenue_cagr.source}
            metrics.warnings.extend(revenue_cagr.warnings)
        
        # Calculate Net Income CAGR
        if len(net_incomes_data) >= 2:
            ni_cagr = self.calculate_net_income_cagr(net_incomes_data)
            metrics.net_income_cagr_5y = {'value': ni_cagr.value, 'source': ni_cagr.source}
            metrics.warnings.extend(ni_cagr.warnings)
        
        # Calculate FCF CAGR
        if len(ocfs_data) >= 2 and len(capexs_data) >= 2:
            fcf_cagr = self.calculate_fcf_cagr(ocfs_data, capexs_data)
            metrics.fcf_cagr_5y = {'value': fcf_cagr.value, 'source': fcf_cagr.source}
            
            # Store latest FCF for appendix
            fcf_vals_detailed = fcf_cagr.intermediate_values.get('fcf_values_with_source')
            if fcf_vals_detailed:
                # Last one is latest -> {value: float, source: str}
                metrics.fcf_latest = fcf_vals_detailed[-1]
                
            metrics.warnings.extend(fcf_cagr.warnings)
        
        # Calculate Earnings Quality
        if len(ocfs_data) >= 3 and len(net_incomes_data) >= 3:
            # Reverse to Newest First for 3yr avg
            ocf_recent = list(reversed(ocfs_data))[:3]
            ni_recent = list(reversed(net_incomes_data))[:3]
            
            eq_result = self.calculate_earnings_quality(ocf_recent, ni_recent)
            metrics.earnings_quality_3y = {'value': eq_result.value, 'source': eq_result.source}
            metrics.warnings.extend(eq_result.warnings)
        
        # Calculate FCF to Debt
        if stock_data.cash_flows and stock_data.balance_sheets:
            latest_cf = stock_data.cash_flows[0]
            latest_bs = stock_data.balance_sheets[0]
            
            # Get latest FCF value/source
            # If standard field is empty, fallback to calculated "Latest FCF"
            std_fcf, std_fcf_src = self.get_field_with_source(latest_cf, 'std_free_cash_flow')
            total_debt_data = self.get_field_with_source(latest_bs, 'std_total_debt')
            
            fcf_data = (std_fcf, std_fcf_src)
            if std_fcf is None and metrics.fcf_latest is not None:
                # metrics.fcf_latest is {value, source}
                fcf_data = (metrics.fcf_latest.get('value'), metrics.fcf_latest.get('source'))
            
            fcf_debt_result = self.calculate_fcf_to_debt_ratio(fcf_data, total_debt_data)
            metrics.fcf_to_debt_ratio = {'value': fcf_debt_result.value, 'source': fcf_debt_result.source}
            metrics.fcf_to_debt_is_debt_free = fcf_debt_result.intermediate_values.get('debt_free', False)
            metrics.warnings.extend(fcf_debt_result.warnings)
        
        return metrics


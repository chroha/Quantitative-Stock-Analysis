"""
Growth Quality Calculators.

Calculates:
1. FCF CAGR (5-year time-weighted)
2. Net Income CAGR (5-year time-weighted)
3. Revenue CAGR (5-year time-weighted)
4. Earnings Quality (3-year average)
5. FCF to Debt Ratio
"""

from typing import Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from fundamentals.financial_data.calculator_base import CalculatorBase, CalculationResult, MetricWarning


@dataclass
class GrowthMetrics:
    """Container for growth quality metrics."""
    fcf_cagr_5y: Optional[float] = None
    net_income_cagr_5y: Optional[float] = None
    revenue_cagr_5y: Optional[float] = None
    
    earnings_quality_3y: Optional[float] = None
    fcf_to_debt_ratio: Optional[float] = None
    fcf_to_debt_is_debt_free: bool = False
    
    calculation_date: datetime = field(default_factory=datetime.now)
    warnings: list[MetricWarning] = field(default_factory=list)
    fcf_latest: Optional[float] = None  # Added for appendix display


class GrowthCalculator(CalculatorBase):
    """Calculates growth quality indicators."""
    
    def calculate_fcf_cagr(
        self,
        operating_cash_flows: List[float],
        capex_values: List[float]
    ) -> CalculationResult:
        """
        Calculate 5-year time-weighted FCF CAGR.
        
        Formula:
            FCF = Operating Cash Flow - Capital Expenditure
            FCF CAGR = time_weighted_cagr(fcf_values)
        
        Args:
            operating_cash_flows: List of OCF values (oldest to newest)
            capex_values: List of CapEx values (oldest to newest)
            
        Returns:
            CalculationResult with FCF CAGR
        """
        result = CalculationResult(value=None)
        
        if len(operating_cash_flows) != len(capex_values):
            result.add_warning(
                'fcf_cagr',
                'data_missing',
                f'OCF periods ({len(operating_cash_flows)}) != CapEx periods ({len(capex_values)})',
                'error'
            )
            return result
        
        # Calculate FCF for each period
        fcf_values = []
        for i, (ocf, capex) in enumerate(zip(operating_cash_flows, capex_values)):
            if ocf is None or capex is None:
                result.add_warning(
                    'fcf_cagr',
                    'data_missing',
                    f'Missing OCF or CapEx at period {i}',
                    'warning'
                )
                fcf_values.append(None)
            else:
                # CapEx is usually negative, so we subtract (which adds the absolute value)
                fcf = ocf + capex  # capex is negative
                fcf_values.append(fcf)
        
        # Calculate time-weighted CAGR
        cagr_result = self.calculate_time_weighted_cagr(
            fcf_values,
            'fcf_cagr_5y'
        )
        
        result.value = cagr_result.value
        result.warnings.extend(cagr_result.warnings)
        result.intermediate_values = {
            'fcf_values': fcf_values,
            'growth_rates': cagr_result.intermediate_values.get('growth_rates'),
            'weights': cagr_result.intermediate_values.get('weights_used')
        }
        
        return result
    
    def calculate_net_income_cagr(
        self,
        net_income_values: List[float]
    ) -> CalculationResult:
        """
        Calculate 5-year time-weighted Net Income CAGR.
        
        Args:
            net_income_values: List of net income (oldest to newest)
            
        Returns:
            CalculationResult with Net Income CAGR
        """
        return self.calculate_time_weighted_cagr(
            net_income_values,
            'net_income_cagr_5y'
        )
    
    def calculate_revenue_cagr(
        self,
        revenue_values: List[float]
    ) -> CalculationResult:
        """
        Calculate 5-year time-weighted Revenue CAGR.
        
        Args:
            revenue_values: List of revenue (oldest to newest)
            
        Returns:
            CalculationResult with Revenue CAGR
        """
        return self.calculate_time_weighted_cagr(
            revenue_values,
            'revenue_cagr_5y'
        )
    
    def calculate_earnings_quality(
        self,
        operating_cash_flows: List[float],
        net_incomes: List[float]
    ) -> CalculationResult:
        """
        Calculate Earnings Quality (3-year average).
        
        Formula:
            Earnings Quality = Operating Cash Flow / Net Income
            (Average of most recent 3 years)
        
        Higher is better (>1.0 means cash > accounting profit)
        
        Args:
            operating_cash_flows: List of OCF (most recent 3 years)
            net_incomes: List of net income (most recent 3 years)
            
        Returns:
            CalculationResult with earnings quality ratio
        """
        result = CalculationResult(value=None)
        
        if len(operating_cash_flows) < 3 or len(net_incomes) < 3:
            result.add_warning(
                'earnings_quality',
                'data_missing',
                f'Need 3 years of data, got OCF:{len(operating_cash_flows)}, NI:{len(net_incomes)}',
                'error'
            )
            return result
        
        # Take most recent 3 years
        # Inputs are expected to be Newest->Oldest (passed from calculate_all)
        # We just ensure we have the first 3 items (though caller passed 3)
        ocf_recent = operating_cash_flows[:3]
        ni_recent = net_incomes[:3]
        
        # Calculate ratio for each year
        ratios = []
        for i, (ocf, ni) in enumerate(zip(ocf_recent, ni_recent)):
            if ocf is None or ni is None:
                result.add_warning(
                    'earnings_quality',
                    'data_missing',
                    f'Missing OCF or NI at year {i}',
                    'warning'
                )
                continue
            
            if ni == 0:
                result.add_warning(
                    'earnings_quality',
                    'calculation_error',
                    f'Net income is zero at year {i}',
                    'warning'
                )
                continue
            
            ratio = ocf / ni
            ratios.append(ratio)
            
            # Warn if quality is low
            if ratio < 1.0:
                result.add_warning(
                    'earnings_quality',
                    'out_of_bounds',
                    f'Year {i}: OCF/NI = {ratio:.4f} (<1.0, cash < profit)',
                    'info',
                    ratio
                )
        
        if ratios:
            avg_quality = sum(ratios) / len(ratios)
            result.value = avg_quality
            result.intermediate_values = {
                'yearly_ratios': ratios,
                'num_years_used': len(ratios)
            }
        else:
            result.add_warning(
                'earnings_quality',
                'calculation_error',
                'No valid ratios calculated',
                'error'
            )
        
        return result
    
    def calculate_fcf_to_debt_ratio(
        self,
        free_cash_flow: Optional[float],
        total_debt: Optional[float]
    ) -> CalculationResult:
        """
        Calculate FCF to Debt Ratio.
        
        Formula:
            FCF to Debt Ratio = Free Cash Flow / Total Debt
        
        Special cases:
        - Total Debt = 0 → 'debt_free' (set flag in result)
        - FCF < 0 → Calculate anyway but warn
        
        Args:
            free_cash_flow: Most recent FCF
            total_debt: Total debt from balance sheet
            
        Returns:
            CalculationResult with FCF/Debt ratio
        """
        result = CalculationResult(value=None)
        
        if total_debt is not None and total_debt == 0:
            result.add_warning(
                'fcf_to_debt',
                'data_missing',
                'Company is debt-free',
                'info',
                0.0
            )
            result.intermediate_values['debt_free'] = True
            return result
        
        if free_cash_flow is not None and free_cash_flow < 0:
            result.add_warning(
                'fcf_to_debt',
                'out_of_bounds',
                f'Negative FCF: {free_cash_flow:,.0f} - debt repayment concern',
                'warning',
                free_cash_flow
            )
        
        ratio = self.safe_divide(free_cash_flow, total_debt, 'fcf_to_debt', result)
        
        result.value = ratio
        result.intermediate_values = {
            'free_cash_flow': free_cash_flow,
            'total_debt': total_debt,
            'debt_free': False
        }
        
        return result
    
    def calculate_all(self, stock_data) -> GrowthMetrics:
        """
        Calculate all growth quality metrics from stock data.
        
        Args:
            stock_data: StockData object with financial statements
            
        Returns:
            GrowthMetrics with all calculated values
        """
        metrics = GrowthMetrics()
        
        # Filter for Annual statements (Fiscal Year) to ensure valid CAGR
        # We might have mixed Annual (FY) and Quarterly (Q) data in the list.
        # Default to 'FY' if period_type is missing (backward compatibility).
        
        annual_income = [s for s in stock_data.income_statements 
                         if getattr(s, 'std_period_type', 'FY') in ['FY', 'TTM']]
        
        annual_cashflow = [s for s in stock_data.cash_flows 
                           if getattr(s, 'std_period_type', 'FY') in ['FY', 'TTM']]

        # Need at least 5 years for CAGR
        if len(annual_income) < 5:
            msg = f"Insufficient annual income statements: {len(annual_income)} (Preferred 5)"
            self.logger.warning(msg)
            metrics.warnings.append(MetricWarning(
                metric_name='growth_general',
                warning_type='data_insufficient',
                message=msg,
                severity='warning'
            ))
        
        if len(annual_cashflow) < 5:
            msg = f"Insufficient annual cash flows: {len(annual_cashflow)} (Preferred 5)"
            self.logger.warning(msg)
            metrics.warnings.append(MetricWarning(
                metric_name='growth_general',
                warning_type='data_insufficient',
                message=msg,
                severity='warning'
            ))
        
        # Extract revenue and net income (5 years, oldest to newest)
        revenues = []
        net_incomes = []
        # Use filtered annual list
        # Sorted desc (newest first). Slice first 5, then reverse to get Oldest->Newest
        for stmt in reversed(annual_income[:5]):
            revenues.append(self.get_field_value(stmt, 'std_revenue'))
            net_incomes.append(self.get_field_value(stmt, 'std_net_income'))
        
        # Extract OCF and CapEx (5 years, oldest to newest)
        ocfs = []
        capexs = []
        for cf in reversed(annual_cashflow[:5]):
            ocfs.append(self.get_field_value(cf, 'std_operating_cash_flow'))
            capexs.append(self.get_field_value(cf, 'std_capex'))
        
        # Calculate Revenue CAGR
        if len(revenues) >= 2:
            revenue_cagr = self.calculate_revenue_cagr(revenues)
            metrics.revenue_cagr_5y = revenue_cagr.value
            metrics.warnings.extend(revenue_cagr.warnings)
        
        # Calculate Net Income CAGR
        if len(net_incomes) >= 2:
            ni_cagr = self.calculate_net_income_cagr(net_incomes)
            metrics.net_income_cagr_5y = ni_cagr.value
            metrics.warnings.extend(ni_cagr.warnings)
        
        # Calculate FCF CAGR
        if len(ocfs) >= 2 and len(capexs) >= 2:
            fcf_cagr = self.calculate_fcf_cagr(ocfs, capexs)
            metrics.fcf_cagr_5y = fcf_cagr.value
            if fcf_cagr.intermediate_values.get('fcf_values'):
                # Store latest FCF for appendix
                fcf_values = fcf_cagr.intermediate_values.get('fcf_values')
                # fcf_values are oldest to newest, so -1 is latest
                if fcf_values:
                    metrics.fcf_latest = fcf_values[-1]
            metrics.warnings.extend(fcf_cagr.warnings)
        
        # Calculate Earnings Quality (most recent 3 years)
        if len(ocfs) >= 3 and len(net_incomes) >= 3:
            # Reverse to get newest first for 3-year average
            ocf_recent = list(reversed(ocfs))[:3]
            ni_recent = list(reversed(net_incomes))[:3]
            
            eq_result = self.calculate_earnings_quality(ocf_recent, ni_recent)
            metrics.earnings_quality_3y = eq_result.value
            metrics.warnings.extend(eq_result.warnings)
        
        # Calculate FCF to Debt
        if stock_data.cash_flows and stock_data.balance_sheets:
            latest_cf = stock_data.cash_flows[0]
            latest_bs = stock_data.balance_sheets[0]
            
            fcf = self.get_field_value(latest_cf, 'std_free_cash_flow')
            total_debt = self.get_field_value(latest_bs, 'std_total_debt')
            
            # Fallback calculate FCF if std_free_cash_flow is missing
            if fcf is None and metrics.fcf_latest is not None:
                fcf = metrics.fcf_latest
            
            fcf_debt_result = self.calculate_fcf_to_debt_ratio(fcf, total_debt)
            metrics.fcf_to_debt_ratio = fcf_debt_result.value
            metrics.fcf_to_debt_is_debt_free = fcf_debt_result.intermediate_values.get('debt_free', False)
            metrics.warnings.extend(fcf_debt_result.warnings)
        
        return metrics

"""
Capital Allocation & Shareholder Returns Calculators.

Calculates:
1. Share Dilution (5-year time-weighted CAGR)
2. Capex Intensity (3-year average)
3. SBC Impact (3-year average)
4. Debt to Equity
"""

from typing import Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from fundamentals.financial_data.calculator_base import CalculatorBase, CalculationResult, MetricWarning


@dataclass
class CapitalAllocationMetrics:
    """Container for capital allocation metrics."""
    share_dilution_cagr_5y: Optional[float] = None
    capex_intensity_3y: Optional[float] = None
    sbc_impact_3y: Optional[float] = None
    debt_to_equity: Optional[float] = None
    
    calculation_date: datetime = field(default_factory=datetime.now)
    warnings: list[MetricWarning] = field(default_factory=list)


class CapitalAllocationCalculator(CalculatorBase):
    """Calculates capital allocation and shareholder return metrics."""
    
    def calculate_share_dilution_cagr(
        self,
        shares_outstanding: List[float]
    ) -> CalculationResult:
        """
        Calculate 5-year time-weighted Share Dilution CAGR.
        
        Formula:
            Share Dilution CAGR = time_weighted_cagr(shares_outstanding)
        
        Interpretation:
        - Negative = Share buyback (good for shareholders)
        - Positive = Dilution (bad for shareholders)
        
        Args:
            shares_outstanding: List of shares outstanding (oldest to newest)
            
        Returns:
            CalculationResult with dilution CAGR
        """
        result = self.calculate_time_weighted_cagr(
            shares_outstanding,
            'share_dilution_cagr_5y'
        )
        
        if result.value is not None:
            if result.value < 0:
                result.add_warning(
                    'share_dilution',
                    'out_of_bounds',
                    f'Share count decreased by {abs(result.value)*100:.2f}% (buybacks)',
                    'info',
                    result.value
                )
            elif result.value > 0.05:  # >5% dilution
                result.add_warning(
                    'share_dilution',
                    'out_of_bounds',
                    f'High dilution: {result.value*100:.2f}% CAGR',
                    'warning',
                    result.value
                )
        
        return result
    
    def calculate_capex_intensity(
        self,
        capex_values: List[float],
        ocf_values: List[float]
    ) -> CalculationResult:
        """
        Calculate Capex Intensity (3-year average).
        
        Formula:
            Capex Intensity = Capital Expenditure / Operating Cash Flow
            (Average of most recent 3 years)
        
        Lower is better (capex is maintenance, high capex = capital-intensive business)
        
        Args:
            capex_values: List of CapEx (most recent 3 years)
            ocf_values: List of OCF (most recent 3 years)
            
        Returns:
            CalculationResult with capex intensity
        """
        result = CalculationResult(value=None)
        
        if len(capex_values) < 3 or len(ocf_values) < 3:
            result.add_warning(
                'capex_intensity',
                'data_missing',
                f'Need 3 years of data, got CapEx:{len(capex_values)}, OCF:{len(ocf_values)}',
                'error'
            )
            return result
        
        # Take most recent 3 years
        capex_3y = capex_values[:3]
        ocf_3y = ocf_values[:3]
        
        # Calculate ratio for each year
        ratios = []
        for i, (capex, ocf) in enumerate(zip(capex_3y, ocf_3y)):
            if capex is None or ocf is None:
                result.add_warning(
                    'capex_intensity',
                    'data_missing',
                    f'Missing CapEx or OCF at year {i}',
                    'warning'
                )
                continue
            
            if ocf == 0:
                result.add_warning(
                    'capex_intensity',
                    'calculation_error',
                    f'OCF is zero at year {i}',
                    'warning'
                )
                continue
            
            # CapEx is usually negative, take absolute value for ratio
            ratio = abs(capex) / ocf
            ratios.append(ratio)
            
            # Warn if capex exceeds OCF
            if ratio > 1.0:
                result.add_warning(
                    'capex_intensity',
                    'out_of_bounds',
                    f'Year {i}: CapEx ({abs(capex):,.0f}) exceeds OCF ({ocf:,.0f})',
                    'warning',
                    ratio
                )
        
        if ratios:
            avg_intensity = sum(ratios) / len(ratios)
            result.value = avg_intensity
            result.intermediate_values = {
                'yearly_ratios': ratios,
                'num_years_used': len(ratios)
            }
        else:
            result.add_warning(
                'capex_intensity',
                'calculation_error',
                'No valid ratios calculated',
                'error'
            )
        
        return result
    
    def calculate_sbc_impact(
        self,
        sbc_values: List[float],
        ocf_values: List[float]
    ) -> CalculationResult:
        """
        Calculate SBC Impact (3-year average).
        
        Formula:
            SBC Impact = Stock Based Compensation / Operating Cash Flow
            (Average of most recent 3 years)
        
        Lower is better. >30% is concerning.
        
        Args:
            sbc_values: List of SBC (most recent 3 years)
            ocf_values: List of OCF (most recent 3 years)
            
        Returns:
            CalculationResult with SBC impact ratio
        """
        result = CalculationResult(value=None)
        
        if len(sbc_values) < 3 or len(ocf_values) < 3:
            result.add_warning(
                'sbc_impact',
                'data_missing',
                f'Need 3 years of data, got SBC:{len(sbc_values)}, OCF:{len(ocf_values)}',
                'error'
            )
            return result
        
        # Take most recent 3 years
        sbc_3y = sbc_values[:3]
        ocf_3y = ocf_values[:3]
        
        # Calculate ratio for each year
        ratios = []
        for i, (sbc, ocf) in enumerate(zip(sbc_3y, ocf_3y)):
            if sbc is None or ocf is None:
                result.add_warning(
                    'sbc_impact',
                    'data_missing',
                    f'Missing SBC or OCF at year {i}',
                    'warning'
                )
                continue
            
            if ocf == 0:
                result.add_warning(
                    'sbc_impact',
                    'calculation_error',
                    f'OCF is zero at year {i}',
                    'warning'
                )
                continue
            
            ratio = sbc / ocf
            ratios.append(ratio)
            
            # Warn if SBC is high
            if ratio > 0.3:
                result.add_warning(
                    'sbc_impact',
                    'out_of_bounds',
                    f'Year {i}: High SBC ({ratio*100:.1f}% of OCF)',
                    'warning',
                    ratio
                )
        
        if ratios:
            avg_impact = sum(ratios) / len(ratios)
            result.value = avg_impact
            result.intermediate_values = {
                'yearly_ratios': ratios,
                'num_years_used': len(ratios)
            }
        else:
            result.add_warning(
                'sbc_impact',
                'calculation_error',
                'No valid ratios calculated',
                'error'
            )
        
        return result
    
    def calculate_debt_to_equity(
        self,
        total_debt: Optional[float],
        shareholders_equity: Optional[float]
    ) -> CalculationResult:
        """
        Calculate Debt to Equity ratio.
        
        Formula:
            Debt to Equity = Total Debt / Shareholders' Equity
        
        Lower is generally better (less leveraged).
        Acceptable levels vary by industry.
        
        Args:
            total_debt: Total debt from balance sheet
            shareholders_equity: Shareholders' equity from balance sheet
            
        Returns:
            CalculationResult with D/E ratio
        """
        result = CalculationResult(value=None)
        
        if shareholders_equity is not None and shareholders_equity <= 0:
            result.add_warning(
                'debt_to_equity',
                'calculation_error',
                f"Shareholders' equity is {shareholders_equity:,.0f} (≤0) - company may be insolvent",
                'error',
                shareholders_equity
            )
            return result
        
        ratio = self.safe_divide(total_debt, shareholders_equity, 'debt_to_equity', result)
        
        result.value = ratio
        result.intermediate_values = {
            'total_debt': total_debt,
            'shareholders_equity': shareholders_equity
        }
        
        return result
    
    def calculate_all(self, stock_data) -> CapitalAllocationMetrics:
        """
        Calculate all capital allocation metrics from stock data.
        
        Args:
            stock_data: StockData object with financial statements
            
        Returns:
            CapitalAllocationMetrics with all calculated values
        """
        metrics = CapitalAllocationMetrics()
        
        # Extract shares outstanding (5 years, oldest to newest)
        shares = []
        for stmt in reversed(stock_data.income_statements[:5]):
            shares.append(self.get_field_value(stmt, 'std_shares_outstanding'))
        
        # Calculate Share Dilution CAGR
        if len(shares) >= 2:
            dilution_result = self.calculate_share_dilution_cagr(shares)
            metrics.share_dilution_cagr_5y = dilution_result.value
            metrics.warnings.extend(dilution_result.warnings)
        
        # Get most recent 3 years of cash flow data
        if len(stock_data.cash_flows) >= 3:
            ocfs = [self.get_field_value(cf, 'std_operating_cash_flow') for cf in stock_data.cash_flows[:3]]
            capexs = [self.get_field_value(cf, 'std_capex') for cf in stock_data.cash_flows[:3]]
            sbcs = [self.get_field_value(cf, 'std_stock_based_compensation') for cf in stock_data.cash_flows[:3]]
            
            # Calculate Capex Intensity
            capex_result = self.calculate_capex_intensity(capexs, ocfs)
            metrics.capex_intensity_3y = capex_result.value
            metrics.warnings.extend(capex_result.warnings)
            
            # Calculate SBC Impact
            sbc_result = self.calculate_sbc_impact(sbcs, ocfs)
            metrics.sbc_impact_3y = sbc_result.value
            metrics.warnings.extend(sbc_result.warnings)
        
        # Calculate Debt to Equity
        if stock_data.balance_sheets:
            latest_bs = stock_data.balance_sheets[0]
            total_debt = self.get_field_value(latest_bs, 'std_total_debt')
            equity = self.get_field_value(latest_bs, 'std_shareholder_equity')
            
            de_result = self.calculate_debt_to_equity(total_debt, equity)
            metrics.debt_to_equity = de_result.value
            metrics.warnings.extend(de_result.warnings)
        
        return metrics

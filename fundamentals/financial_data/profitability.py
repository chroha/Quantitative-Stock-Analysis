"""
Profitability and Capital Efficiency Calculators.

Calculates:
1. ROIC (Return on Invested Capital)
2. ROE (Return on Equity)
3. Gross Margin
4. Net Margin
5. Operating Margin
"""

from typing import Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from fundamentals.financial_data.calculator_base import CalculatorBase, CalculationResult, MetricWarning


from config.analysis_config import METRIC_BOUNDS

@dataclass
class ProfitabilityMetrics:
    """Container for profitability metrics (value + source)."""
    # ROIC components
    roic: Optional[Any] = None  # Float or Dict
    roic_nopat: Optional[Any] = None
    roic_invested_capital: Optional[Any] = None
    roic_effective_tax_rate: Optional[Any] = None
    
    # Other metrics
    roe: Optional[Any] = None
    gross_margin: Optional[Any] = None
    net_margin: Optional[Any] = None
    operating_margin: Optional[Any] = None
    interest_coverage: Optional[Any] = None
    
    # Metadata
    calculation_date: datetime = field(default_factory=datetime.now)
    warnings: list[MetricWarning] = field(default_factory=list)


class ProfitabilityCalculator(CalculatorBase):
    """Calculates profitability and capital efficiency metrics with source tracking."""
    
    def calculate_roic(
        self,
        operating_income_data: tuple[Optional[float], str],
        income_tax_expense_data: tuple[Optional[float], str],
        pretax_income_data: tuple[Optional[float], str],
        total_equity_data: tuple[Optional[float], str],
        total_debt_data: tuple[Optional[float], str],
        cash_data: tuple[Optional[float], str]
    ) -> CalculationResult:
        """
        Calculate ROIC with source tracking.
        Args now expect (value, source) tuples.
        """
        # Unpack data
        operating_income, op_src = operating_income_data
        income_tax_expense, tax_src = income_tax_expense_data
        pretax_income, pretax_src = pretax_income_data
        total_equity, eq_src = total_equity_data
        total_debt, debt_src = total_debt_data
        cash, cash_src = cash_data

        result = CalculationResult(value=None)
        
        # Calculate effective tax rate
        effective_tax_rate = self.safe_divide(
            income_tax_expense,
            pretax_income,
            'effective_tax_rate',
            result
        )
        tax_rate_src = self.merge_sources([tax_src, pretax_src])
        
        # Fallback for tax rate
        if effective_tax_rate is None:
             result.add_warning('ROIC', 'data_missing', 'Missing effective tax rate', 'warning')
        else:
            bounds = METRIC_BOUNDS.get('effective_tax_rate', {'min': 0.0, 'max': 1.0})
            self.check_bounds(effective_tax_rate, 'effective_tax_rate', result=result, min_value=bounds['min'], max_value=bounds['max'])
            
        # Calculate NOPAT
        if operating_income is not None and effective_tax_rate is not None:
            nopat = operating_income * (1 - effective_tax_rate)
        else:
            nopat = None
        nopat_src = self.merge_sources([op_src, tax_rate_src])
        
        # Calculate Invested Capital
        if total_equity is not None:
             debt_val = total_debt if total_debt is not None else 0
             cash_val = cash if cash is not None else 0
             invested_capital = total_equity + debt_val - cash_val
             
             if invested_capital <= 0:
                result.add_warning('ROIC', 'out_of_bounds', f'Invested capital is {invested_capital} (<=0)', 'error')
                invested_capital = None
        else:
            invested_capital = None
            result.add_warning('ROIC', 'data_missing', 'Missing total equity', 'error')
            
        ic_src = self.merge_sources([eq_src, debt_src, cash_src])
        
        # Calculate ROIC
        roic = self.safe_divide(nopat, invested_capital, 'ROIC', result)
        roic_src = self.merge_sources([nopat_src, ic_src])
        
        if roic is not None:
            bounds = METRIC_BOUNDS.get('ROIC', {'min': -0.5, 'max': 1.0})
            self.check_bounds(roic, 'ROIC', result=result, min_value=bounds['min'], max_value=bounds['max'])
        
        result.value = roic
        result.source = roic_src
        
        # Store components with their specifc sources for Report
        result.intermediate_values = {
            'nopat': {'value': nopat, 'source': nopat_src},
            'effective_tax_rate': {'value': effective_tax_rate, 'source': tax_rate_src},
            'invested_capital': {'value': invested_capital, 'source': ic_src},
            # Raw debug inputs
            'operating_income': operating_income,
            'total_equity': total_equity
        }
        
        return result
    
    def calculate_roe(
        self,
        net_income_data: tuple[Optional[float], str],
        shareholders_equity_data: tuple[Optional[float], str]
    ) -> CalculationResult:
        """Calculate ROE with source tracking."""
        net_income, net_src = net_income_data
        shareholders_equity, eq_src = shareholders_equity_data
        
        result = CalculationResult(value=None)
        
        if shareholders_equity is not None and shareholders_equity <= 0:
            result.add_warning('ROE', 'calculation_error', 'Negative Equity', 'error')
            return result
        
        roe = self.safe_divide(net_income, shareholders_equity, 'ROE', result)
        roe_src = self.merge_sources([net_src, eq_src])
        
        if roe is not None:
            bounds = METRIC_BOUNDS.get('ROE', {'min': -0.5, 'max': 2.0})
            self.check_bounds(roe, 'ROE', result=result, min_value=bounds['min'], max_value=bounds['max'])
        
        result.value = roe
        result.source = roe_src
        return result
    
    def calculate_gross_margin(
        self,
        revenue_data: tuple[Optional[float], str],
        gross_profit_data: tuple[Optional[float], str] = (None, 'N/A'),
        cost_of_revenue_data: tuple[Optional[float], str] = (None, 'N/A')
    ) -> CalculationResult:
        """Calculate Gross Margin with source tracking."""
        revenue, rev_src = revenue_data
        gross_profit, gp_src = gross_profit_data
        cost_of_revenue, cor_src = cost_of_revenue_data
        
        result = CalculationResult(value=None)
        
        # Try primary calculation
        if gross_profit is not None:
            margin = self.safe_divide(gross_profit, revenue, 'gross_margin', result)
            margin_src = self.merge_sources([gp_src, rev_src])
            result.intermediate_values['method'] = 'direct'
        elif cost_of_revenue is not None and revenue is not None:
            # Fallback calculation
            gross_profit_calc = revenue - cost_of_revenue
            margin = self.safe_divide(gross_profit_calc, revenue, 'gross_margin', result)
            margin_src = self.merge_sources([rev_src, cor_src])
            result.intermediate_values['method'] = 'calculated'
            result.intermediate_values['gross_profit_calculated'] = gross_profit_calc
            result.add_warning('gross_margin', 'data_missing', 'Using calculated gross profit', 'info')
        else:
            result.add_warning('gross_margin', 'data_missing', 'Insufficient data', 'error')
            margin = None
            margin_src = "N/A"
        
        if margin is not None:
            bounds = METRIC_BOUNDS.get('gross_margin', {'min': -1.0, 'max': 1.0})
            self.check_bounds(margin, 'gross_margin', result=result, min_value=bounds['min'], max_value=bounds['max'])
        
        result.value = margin
        result.source = margin_src
        return result
    
    def calculate_net_margin(
        self,
        net_income_data: tuple[Optional[float], str],
        revenue_data: tuple[Optional[float], str]
    ) -> CalculationResult:
        """Calculate Net Margin with source tracking."""
        net_income, net_src = net_income_data
        revenue, rev_src = revenue_data
        
        result = CalculationResult(value=None)
        
        margin = self.safe_divide(net_income, revenue, 'net_margin', result)
        margin_src = self.merge_sources([net_src, rev_src])
        
        if margin is not None:
            bounds = METRIC_BOUNDS.get('net_margin', {'min': -1.0, 'max': 0.5})
            self.check_bounds(margin, 'net_margin', result=result, min_value=bounds['min'], max_value=bounds['max'])
        
        result.value = margin
        result.source = margin_src
        return result
    
    def calculate_operating_margin(
        self,
        operating_income_data: tuple[Optional[float], str],
        revenue_data: tuple[Optional[float], str]
    ) -> CalculationResult:
        """Calculate Operating Margin with source tracking."""
        operating_income, op_src = operating_income_data
        revenue, rev_src = revenue_data
        
        result = CalculationResult(value=None)
        
        margin = self.safe_divide(operating_income, revenue, 'operating_margin', result)
        margin_src = self.merge_sources([op_src, rev_src])
        
        result.value = margin
        result.source = margin_src
        return result
    
    def calculate_interest_coverage(
        self,
        operating_income_data: tuple[Optional[float], str],
        interest_expense_data: tuple[Optional[float], str]
    ) -> CalculationResult:
        """Calculate Interest Coverage with source tracking."""
        operating_income, op_src = operating_income_data
        interest_expense, int_src = interest_expense_data
        
        result = CalculationResult(value=None)
        
        if interest_expense == 0:
             result.add_warning('interest_coverage', 'calculation_error', 'Interest expense is 0', 'info')
             return result

        coverage = self.safe_divide(operating_income, interest_expense, 'interest_coverage', result)
        source = self.merge_sources([op_src, int_src])
        
        result.value = coverage
        result.source = source
        return result
    
    def calculate_all(self, stock_data) -> ProfitabilityMetrics:
        """
        Calculate all profitability metrics from stock data.
        """
        metrics = ProfitabilityMetrics()
        
        if not stock_data.income_statements or not stock_data.balance_sheets:
            self.logger.error("Missing income statements or balance sheets")
            return metrics
        
        # Find latest Annual (FY) or TTM financial data
        latest_income = next((s for s in stock_data.income_statements if getattr(s, 'std_period_type', 'FY') in ['FY', 'TTM']), None)
        latest_balance = next((s for s in stock_data.balance_sheets if getattr(s, 'std_period_type', 'FY') in ['FY', 'TTM']), None)
        
        if not latest_income or not latest_balance:
            latest_income = stock_data.income_statements[0]
            latest_balance = stock_data.balance_sheets[0]
            self.logger.warning("No Annual (FY) or TTM statements found. Using latest available.")
        else:
             self.logger.debug(f"Using Latest Annual/TTM Report: {latest_income.std_period}")
        
        # Extract values WITH sources
        # Income inputs
        op_inc_data = self.get_field_with_source(latest_income, 'std_operating_income')
        net_inc_data = self.get_field_with_source(latest_income, 'std_net_income')
        rev_data = self.get_field_with_source(latest_income, 'std_revenue')
        gp_data = self.get_field_with_source(latest_income, 'std_gross_profit')
        cor_data = self.get_field_with_source(latest_income, 'std_cost_of_revenue')
        pretax_data = self.get_field_with_source(latest_income, 'std_pretax_income')
        tax_data = self.get_field_with_source(latest_income, 'std_income_tax_expense')
        int_exp_data = self.get_field_with_source(latest_income, 'std_interest_expense')
        
        # Balance inputs
        equity_data = self.get_field_with_source(latest_balance, 'std_shareholder_equity')
        debt_data = self.get_field_with_source(latest_balance, 'std_total_debt')
        cash_data = self.get_field_with_source(latest_balance, 'std_cash')
        
        # Log inputs
        self.logger.debug(f"ROIC Inputs: OpInc={op_inc_data[0]}, Tax={tax_data[0]}")
        
        # Calculate ROIC
        roic_result = self.calculate_roic(
            op_inc_data, tax_data, pretax_data,
            equity_data, debt_data, cash_data
        )
        # Store as dict {value, source}
        metrics.roic = {'value': roic_result.value, 'source': roic_result.source}
        metrics.roic_nopat = roic_result.intermediate_values.get('nopat') # Already a dict inside calculate_roic
        metrics.roic_invested_capital = roic_result.intermediate_values.get('invested_capital')
        metrics.roic_effective_tax_rate = roic_result.intermediate_values.get('effective_tax_rate')
        metrics.warnings.extend(roic_result.warnings)
        
        # Calculate ROE
        roe_result = self.calculate_roe(net_inc_data, equity_data)
        metrics.roe = {'value': roe_result.value, 'source': roe_result.source}
        metrics.warnings.extend(roe_result.warnings)
        
        # Calculate Margins
        gross_margin_result = self.calculate_gross_margin(rev_data, gp_data, cor_data)
        metrics.gross_margin = {'value': gross_margin_result.value, 'source': gross_margin_result.source}
        metrics.warnings.extend(gross_margin_result.warnings)
        
        net_margin_result = self.calculate_net_margin(net_inc_data, rev_data)
        metrics.net_margin = {'value': net_margin_result.value, 'source': net_margin_result.source}
        metrics.warnings.extend(net_margin_result.warnings)
        
        op_margin_result = self.calculate_operating_margin(op_inc_data, rev_data)
        metrics.operating_margin = {'value': op_margin_result.value, 'source': op_margin_result.source}
        metrics.warnings.extend(op_margin_result.warnings)
        
        # Calculate Interest Coverage
        int_cov_result = self.calculate_interest_coverage(op_inc_data, int_exp_data)
        metrics.interest_coverage = {'value': int_cov_result.value, 'source': int_cov_result.source}
        metrics.warnings.extend(int_cov_result.warnings)
        
        return metrics

"""
Profitability and Capital Efficiency Calculators.

Calculates:
1. ROIC (Return on Invested Capital)
2. ROE (Return on Equity)
3. Gross Margin
4. Net Margin
5. Operating Margin
"""

from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime
from fundamentals.financial_data.calculator_base import CalculatorBase, CalculationResult, MetricWarning


@dataclass
class ProfitabilityMetrics:
    """Container for profitability metrics."""
    # ROIC components
    roic: Optional[float] = None
    roic_nopat: Optional[float] = None
    roic_invested_capital: Optional[float] = None
    roic_effective_tax_rate: Optional[float] = None
    
    # Other metrics
    roe: Optional[float] = None
    gross_margin: Optional[float] = None
    net_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    interest_coverage: Optional[float] = None
    
    # Metadata
    calculation_date: datetime = field(default_factory=datetime.now)
    warnings: list[MetricWarning] = field(default_factory=list)


class ProfitabilityCalculator(CalculatorBase):
    """Calculates profitability and capital efficiency metrics."""
    
    def calculate_roic(
        self,
        operating_income: Optional[float],
        income_tax_expense: Optional[float],
        pretax_income: Optional[float],
        total_equity: Optional[float],
        total_debt: Optional[float],
        cash: Optional[float]
    ) -> CalculationResult:
        """
        Calculate ROIC (Return on Invested Capital).
        
        Formula:
            ROIC = NOPAT / Invested Capital
            
            Where:
            - NOPAT = Operating Income × (1 - Effective Tax Rate)
            - Effective Tax Rate = Income Tax Expense / Income Before Tax
            - Invested Capital = Total Equity + Total Debt - Cash
        
        Args:
            operating_income: Operating income from income statement
            income_tax_expense: Income tax expense
            pretax_income: Income before tax
            total_equity: Shareholder's equity
            total_debt: Total debt
            cash: Cash and cash equivalents
            
        Returns:
            CalculationResult with ROIC value and intermediate calculations
        """
        result = CalculationResult(value=None)
        
        # Calculate effective tax rate
        # Calculate effective tax rate with fallback
        effective_tax_rate = self.safe_divide(
            income_tax_expense,
            pretax_income,
            'effective_tax_rate',
            result
        )
        
        # Fallback for tax rate
        if effective_tax_rate is None:
             result.add_warning('ROIC', 'data_missing', 'Missing effective tax rate', 'warning')
        else:
            # Check bounds
            self.check_bounds(
                effective_tax_rate,
                'effective_tax_rate',
                min_value=0.0,
                max_value=1.0,
                result=result
            )
            
        # Calculate NOPAT
        nopat = operating_income * (1 - effective_tax_rate) if operating_income else None
        
        # Calculate Invested Capital (Lenient)
        # If cash is missing, assume 0. If debt missing, assume 0. Equity is critical.
        if total_equity is not None:
             debt_val = total_debt if total_debt is not None else 0
             cash_val = cash if cash is not None else 0
             invested_capital = total_equity + debt_val - cash_val
             
             if invested_capital <= 0:
                result.add_warning(
                    'ROIC',
                    'out_of_bounds',
                    f'Invested capital is {invested_capital:,.0f} (≤0)',
                    'error',
                    invested_capital
                )
                invested_capital = None
        else:
            invested_capital = None
            result.add_warning(
                'ROIC',
                'data_missing',
                'Missing total equity for invested capital metrics',
                'error'
            )
        
        # Calculate ROIC
        roic = self.safe_divide(nopat, invested_capital, 'ROIC', result)
        
        if roic is not None:
            # Check extreme values
            self.check_bounds(
                roic,
                'ROIC',
                min_value=-0.5,
                max_value=1.0,
                result=result
            )
        
        result.value = roic
        result.intermediate_values = {
            'nopat': nopat,
            'effective_tax_rate': effective_tax_rate,
            'invested_capital': invested_capital,
            'operating_income': operating_income,
            'total_equity': total_equity,
            'total_debt': total_debt,
            'cash': cash
        }
        
        return result
    
    def calculate_roe(
        self,
        net_income: Optional[float],
        shareholders_equity: Optional[float]
    ) -> CalculationResult:
        """
        Calculate ROE (Return on Equity).
        
        Formula:
            ROE = Net Income / Shareholder's Equity
        
        Args:
            net_income: Net income from income statement
            shareholders_equity: Shareholders' equity from balance sheet
            
        Returns:
            CalculationResult with ROE value
        """
        result = CalculationResult(value=None)
        
        # Check for insolvency
        if shareholders_equity is not None and shareholders_equity <= 0:
            result.add_warning(
                'ROE',
                'calculation_error',
                f"Shareholders' equity is {shareholders_equity:,.0f} (≤0) - company may be insolvent",
                'error',
                shareholders_equity
            )
            return result
        
        # Calculate ROE
        roe = self.safe_divide(net_income, shareholders_equity, 'ROE', result)
        
        if roe is not None:
            # Check extreme values
            self.check_bounds(
                roe,
                'ROE',
                min_value=-0.5,
                max_value=2.0,
                result=result
            )
        
        result.value = roe
        result.intermediate_values = {
            'net_income': net_income,
            'shareholders_equity': shareholders_equity
        }
        
        return result
    
    def calculate_gross_margin(
        self,
        revenue: Optional[float],
        gross_profit: Optional[float] = None,
        cost_of_revenue: Optional[float] = None
    ) -> CalculationResult:
        """
        Calculate Gross Margin.
        
        Formula (primary):
            Gross Margin = Gross Profit / Revenue
            
        Formula (fallback):
            Gross Margin = (Revenue - Cost of Revenue) / Revenue
        
        Args:
            revenue: Total revenue
            gross_profit: Gross profit (if available)
            cost_of_revenue: Cost of revenue (fallback)
            
        Returns:
            CalculationResult with gross margin
        """
        result = CalculationResult(value=None)
        
        # Try primary calculation
        if gross_profit is not None:
            margin = self.safe_divide(gross_profit, revenue, 'gross_margin', result)
            result.intermediate_values['method'] = 'direct'
        elif cost_of_revenue is not None and revenue is not None:
            # Fallback calculation
            gross_profit_calc = revenue - cost_of_revenue
            margin = self.safe_divide(gross_profit_calc, revenue, 'gross_margin', result)
            result.intermediate_values['method'] = 'calculated'
            result.intermediate_values['gross_profit_calculated'] = gross_profit_calc
            result.add_warning(
                'gross_margin',
                'data_missing',
                'Using calculated gross profit (revenue - cost_of_revenue)',
                'info'
            )
        else:
            result.add_warning(
                'gross_margin',
                'data_missing',
                'Insufficient data for gross margin calculation',
                'error'
            )
            margin = None
        
        if margin is not None:
            self.check_bounds(
                margin,
                'gross_margin',
                min_value=-1.0,
                max_value=1.0,
                result=result
            )
        
        result.value = margin
        result.intermediate_values.update({
            'revenue': revenue,
            'gross_profit': gross_profit,
            'cost_of_revenue': cost_of_revenue
        })
        
        return result
    
    def calculate_net_margin(
        self,
        net_income: Optional[float],
        revenue: Optional[float]
    ) -> CalculationResult:
        """
        Calculate Net Margin.
        
        Formula:
            Net Margin = Net Income / Revenue
        
        Args:
            net_income: Net income
            revenue: Total revenue
            
        Returns:
            CalculationResult with net margin
        """
        result = CalculationResult(value=None)
        
        margin = self.safe_divide(net_income, revenue, 'net_margin', result)
        
        if margin is not None:
            self.check_bounds(
                margin,
                'net_margin',
                min_value=-1.0,
                max_value=0.5,
                result=result
            )
        
        result.value = margin
        result.intermediate_values = {
            'net_income': net_income,
            'revenue': revenue
        }
        
        return result
    
    def calculate_operating_margin(
        self,
        operating_income: Optional[float],
        revenue: Optional[float]
    ) -> CalculationResult:
        """
        Calculate Operating Margin.
        
        Formula:
            Operating Margin = Operating Income / Revenue
        
        Args:
            operating_income: Operating income
            revenue: Total revenue
            
        Returns:
            CalculationResult with operating margin
        """
        result = CalculationResult(value=None)
        
        margin = self.safe_divide(operating_income, revenue, 'operating_margin', result)
        
        result.value = margin
        result.intermediate_values = {
            'operating_income': operating_income,
            'revenue': revenue
        }
        
        return result
    
    def calculate_interest_coverage(
        self,
        operating_income: Optional[float],
        interest_expense: Optional[float]
    ) -> CalculationResult:
        """
        Calculate Interest Coverage Ratio.
        
        Formula:
            Interest Coverage = Operating Income / Interest Expense
            
        Args:
            operating_income: Operating income (EBIT)
            interest_expense: Interest expense
            
        Returns:
            CalculationResult with interest coverage
        """
        result = CalculationResult(value=None)
        
        # Interest expense is often positive in DB but check if it's 0
        if interest_expense == 0:
             # If no interest expense, coverage is technically infinite, but we can return None or a high number.
             # Or warnings.
             result.add_warning(
                 'interest_coverage',
                 'calculation_error',
                 'Interest expense is 0',
                 'info'
             )
             return result

        coverage = self.safe_divide(operating_income, interest_expense, 'interest_coverage', result)
        
        if coverage is not None:
            # Check bounds (negative coverage is possible if loss making)
            pass
            
        result.value = coverage
        result.intermediate_values = {
            'operating_income': operating_income,
            'interest_expense': interest_expense
        }
        
        return result
    
    def calculate_all(self, stock_data) -> ProfitabilityMetrics:
        """
        Calculate all profitability metrics from stock data.
        
        Args:
            stock_data: StockData object with financial statements
            
        Returns:
            ProfitabilityMetrics with all calculated values
        """
        metrics = ProfitabilityMetrics()
        
        # Get most recent financial data
        if not stock_data.income_statements or not stock_data.balance_sheets:
            self.logger.error("Missing income statements or balance sheets")
            return metrics
        
        # Find latest Annual (FY) or TTM financial data
        # We prefer FY to ensure annualized metrics (ROIC, ROE) are correct.
        # But if TTM is available (synthesized from quarters), it's even better for timeliness.
        
        latest_income = next((s for s in stock_data.income_statements if getattr(s, 'std_period_type', 'FY') in ['FY', 'TTM']), None)
        latest_balance = next((s for s in stock_data.balance_sheets if getattr(s, 'std_period_type', 'FY') in ['FY', 'TTM']), None)
        
        if not latest_income or not latest_balance:
            # Fallback to latest available if no Annual found (e.g. only have Qs?)
            # or if period_type logic fails.
            latest_income = stock_data.income_statements[0]
            latest_balance = stock_data.balance_sheets[0]
            self.logger.warning("No Annual (FY) or TTM statements found. Using latest available (Warning: Metrics might be quarterly).")
        else:
             self.logger.debug(f"Using Latest Annual/TTM Report for Profitability: {latest_income.std_period} ({getattr(latest_income, 'std_period_type', 'FY')})")
        
        # Extract values from income statement
        operating_income = self.get_field_value(latest_income, 'std_operating_income')
        net_income = self.get_field_value(latest_income, 'std_net_income')
        revenue = self.get_field_value(latest_income, 'std_revenue')
        gross_profit = self.get_field_value(latest_income, 'std_gross_profit')
        cost_of_revenue = self.get_field_value(latest_income, 'std_cost_of_revenue')
        
        # Extract tax fields for ROIC
        pretax_income = self.get_field_value(latest_income, 'std_pretax_income')
        income_tax_expense = self.get_field_value(latest_income, 'std_income_tax_expense')
        interest_expense = self.get_field_value(latest_income, 'std_interest_expense')
        
        # Extract balance sheet values
        total_equity = self.get_field_value(latest_balance, 'std_shareholder_equity')
        total_debt = self.get_field_value(latest_balance, 'std_total_debt')
        cash = self.get_field_value(latest_balance, 'std_cash')
        
        # Log inputs for debugging discrepancies
        op_inc_str = f"{operating_income:,.0f}" if operating_income is not None else "None"
        tax_str = f"{income_tax_expense:,.0f}" if income_tax_expense is not None else "None"
        self.logger.debug(f"ROIC Inputs: OpInc={op_inc_str}, Tax={tax_str}")
        
        eq_str = f"{total_equity:,.0f}" if total_equity is not None else "None"
        debt_str = f"{total_debt:,.0f}" if total_debt is not None else "None"
        cash_str = f"{cash:,.0f}" if cash is not None else "None"
        self.logger.debug(f"IC Inputs: Equity={eq_str}, Debt={debt_str}, Cash={cash_str}")
        
        # Calculate ROIC (now with tax data)
        roic_result = self.calculate_roic(
            operating_income,
            income_tax_expense,
            pretax_income,
            total_equity,
            total_debt,
            cash
        )
        metrics.roic = roic_result.value
        metrics.roic_nopat = roic_result.intermediate_values.get('nopat')
        metrics.roic_invested_capital = roic_result.intermediate_values.get('invested_capital')
        metrics.roic_effective_tax_rate = roic_result.intermediate_values.get('effective_tax_rate')
        metrics.warnings.extend(roic_result.warnings)
        
        # Calculate ROE
        roe_result = self.calculate_roe(net_income, total_equity)
        metrics.roe = roe_result.value
        metrics.warnings.extend(roe_result.warnings)
        
        # Calculate Gross Margin
        gross_margin_result = self.calculate_gross_margin(revenue, gross_profit, cost_of_revenue)
        metrics.gross_margin = gross_margin_result.value
        metrics.warnings.extend(gross_margin_result.warnings)
        
        # Calculate Net Margin
        net_margin_result = self.calculate_net_margin(net_income, revenue)
        metrics.net_margin = net_margin_result.value
        metrics.warnings.extend(net_margin_result.warnings)
        
        # Calculate Operating Margin
        operating_margin_result = self.calculate_operating_margin(operating_income, revenue)
        metrics.operating_margin = operating_margin_result.value
        metrics.warnings.extend(operating_margin_result.warnings)
        
        # Calculate Interest Coverage
        int_cov_result = self.calculate_interest_coverage(operating_income, interest_expense)
        metrics.interest_coverage = int_cov_result.value
        metrics.warnings.extend(int_cov_result.warnings)
        
        return metrics

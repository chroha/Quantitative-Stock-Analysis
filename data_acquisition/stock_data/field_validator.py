"""
Field Validator - Fine-grained validation of financial statement fields.
Validates that required fields exist for each period and tracks data completeness.
"""

from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from utils.logger import setup_logger

logger = setup_logger('field_validator')


@dataclass
class FieldValidationResult:
    """Result of validating a single statement period."""
    period: str
    statement_type: str  # 'income', 'balance', 'cashflow'
    is_complete: bool
    missing_required: List[str] = field(default_factory=list)
    missing_important: List[str] = field(default_factory=list)
    completeness_score: float = 0.0  # 0.0 - 1.0


@dataclass
class OverallValidationResult:
    """Overall validation result for all statements."""
    symbol: str
    is_complete: bool = False
    total_periods_validated: int = 0
    incomplete_periods: int = 0
    period_results: List[FieldValidationResult] = field(default_factory=list)
    average_completeness: float = 0.0
    expected_periods: int = 18  # Expected number of period validations (6 years * 3 statement types)
    
    def add_result(self, result: FieldValidationResult):
        self.period_results.append(result)
        self.total_periods_validated += 1
        if not result.is_complete:
            self.incomplete_periods += 1
            self.is_complete = False
        
        # Recalculate average using expected_periods as denominator floor
        # This ensures if we have fewer periods than expected, completeness is penalized
        total_score = sum(r.completeness_score for r in self.period_results)
        denominator = max(len(self.period_results), self.expected_periods)
        self.average_completeness = total_score / denominator if denominator > 0 else 0


class FieldValidator:
    """
    Validates financial statement fields at a granular level.
    Tracks which required vs important vs optional fields are missing.
    
    Field classifications are based on actual downstream module requirements:
    - financial_data: ProfitabilityCalculator, GrowthCalculator, CapitalAllocationCalculator
    - financial_scorers: CompanyScorer, MetricScorer
    """
    
    # =========================================================================
    # REQUIRED FIELDS - Missing these will BLOCK downstream calculations
    # These trigger Alpha Vantage fallback if missing after Yahoo + FMP
    # =========================================================================
    
    # Income Statement - Required for: ROE, margins, CAGR calculations
    REQUIRED_INCOME_FIELDS = [
        'std_revenue',           # Margins, Revenue CAGR
        'std_net_income',        # ROE, Net Income CAGR, Earnings Quality
        'std_operating_income',  # ROIC, Operating Margin
    ]
    
    # Balance Sheet - Required for: ROIC, ROE, D/E ratio
    REQUIRED_BALANCE_FIELDS = [
        'std_shareholder_equity',  # ROE, ROIC, Debt to Equity
        'std_total_debt',          # ROIC, D/E, FCF to Debt
    ]
    
    # Cash Flow - Required for: FCF metrics, Earnings Quality, Capex Intensity
    REQUIRED_CASHFLOW_FIELDS = [
        'std_operating_cash_flow',  # FCF, Earnings Quality, Capex Intensity, SBC Impact
        'std_capex',                # FCF CAGR, Capex Intensity
    ]
    
    # =========================================================================
    # IMPORTANT FIELDS - Used by downstream but have fallbacks or optional
    # Lower priority for data fetching, but still tracked for completeness
    # =========================================================================
    
    # Income Statement - Important for: tax calculations, margin variants
    IMPORTANT_INCOME_FIELDS = [
        'std_pretax_income',       # ROIC effective tax rate
        'std_income_tax_expense',  # ROIC effective tax rate
        'std_gross_profit',        # Gross Margin (has fallback)
        'std_cost_of_revenue',     # Gross Margin fallback calculation
        'std_shares_outstanding',  # Share Dilution CAGR
        'std_eps',                 # Per-share metrics
        'std_ebitda',              # Valuation
    ]
    
    # Balance Sheet - Important for: ROIC calculation, liquidity
    IMPORTANT_BALANCE_FIELDS = [
        'std_cash',                # ROIC Invested Capital
        'std_total_assets',        # Balance sheet integrity check
        'std_total_liabilities',   # Balance sheet integrity check
        'std_current_assets',      # Liquidity ratios
        'std_current_liabilities', # Liquidity ratios
    ]
    
    # Cash Flow - Important for: FCF detail, capital allocation
    IMPORTANT_CASHFLOW_FIELDS = [
        'std_free_cash_flow',          # FCF to Debt (has calculation fallback)
        'std_stock_based_compensation', # SBC Impact metric
        'std_investing_cash_flow',      # Cash flow analysis
        'std_financing_cash_flow',      # Cash flow analysis
        'std_dividends_paid',           # Valuation (DDM model)
    ]
    
    def __init__(self):
        self.field_configs = {
            'income': {
                'required': self.REQUIRED_INCOME_FIELDS,
                'important': self.IMPORTANT_INCOME_FIELDS,
            },
            'balance': {
                'required': self.REQUIRED_BALANCE_FIELDS,
                'important': self.IMPORTANT_BALANCE_FIELDS,
            },
            'cashflow': {
                'required': self.REQUIRED_CASHFLOW_FIELDS,
                'important': self.IMPORTANT_CASHFLOW_FIELDS,
            }
        }
    
    def _has_value(self, field_data: Any) -> bool:
        """Check if a field has valid data."""
        if field_data is None:
            return False
        # Handle FieldWithSource structure
        if hasattr(field_data, 'value'):
            return field_data.value is not None
        # Handle dict structure (from JSON)
        if isinstance(field_data, dict):
            return field_data.get('value') is not None
        return True
    
    def validate_statement(self, statement: Any, statement_type: str) -> FieldValidationResult:
        """
        Validate a single financial statement period.
        
        Args:
            statement: Statement object (IncomeStatement, BalanceSheet, or CashFlow)
            statement_type: 'income', 'balance', or 'cashflow'
            
        Returns:
            FieldValidationResult with completeness info
        """
        config = self.field_configs.get(statement_type, {})
        required_fields = config.get('required', [])
        important_fields = config.get('important', [])
        
        # Get period identifier
        period = getattr(statement, 'std_period', None)
        if period is None and hasattr(statement, '__dict__'):
            period = statement.__dict__.get('std_period')
        if period is None:
            period = 'unknown'
        
        # Check required fields
        missing_required = []
        for field_name in required_fields:
            field_data = getattr(statement, field_name, None)
            if field_data is None and hasattr(statement, '__dict__'):
                field_data = statement.__dict__.get(field_name)
            
            if not self._has_value(field_data):
                missing_required.append(field_name)
        
        # Check important fields
        missing_important = []
        for field_name in important_fields:
            field_data = getattr(statement, field_name, None)
            if field_data is None and hasattr(statement, '__dict__'):
                field_data = statement.__dict__.get(field_name)
            
            if not self._has_value(field_data):
                missing_important.append(field_name)
        
        # Calculate completeness score
        total_fields = len(required_fields) + len(important_fields)
        filled_fields = total_fields - len(missing_required) - len(missing_important)
        completeness_score = filled_fields / total_fields if total_fields > 0 else 1.0
        
        # Period is complete only if all required fields are present
        is_complete = len(missing_required) == 0
        
        return FieldValidationResult(
            period=period,
            statement_type=statement_type,
            is_complete=is_complete,
            missing_required=missing_required,
            missing_important=missing_important,
            completeness_score=completeness_score
        )
    
    def validate_all_statements(
        self, 
        symbol: str,
        income_statements: List[Any],
        balance_sheets: List[Any],
        cash_flows: List[Any],
        expected_years: int = 6
    ) -> OverallValidationResult:
        """
        Validate all financial statements for a stock.
        
        Args:
            symbol: Stock ticker symbol
            income_statements: List of income statement objects
            balance_sheets: List of balance sheet objects  
            cash_flows: List of cash flow objects
            expected_years: Expected number of fiscal years (default 6)
            
        Returns:
            OverallValidationResult with complete validation info
        """
        # Multiply by 3 because we validate 3 statement types per year
        expected_total = expected_years * 3
        result = OverallValidationResult(symbol=symbol, expected_periods=expected_total)
        
        # Validate income statements
        for stmt in income_statements:
            period_result = self.validate_statement(stmt, 'income')
            result.add_result(period_result)
            
            if period_result.missing_required:
                logger.warning(
                    f"{symbol} [{period_result.period}] Income: Missing required fields: "
                    f"{period_result.missing_required}"
                )
        
        # Validate balance sheets
        for stmt in balance_sheets:
            period_result = self.validate_statement(stmt, 'balance')
            result.add_result(period_result)
            
            if period_result.missing_required:
                logger.warning(
                    f"{symbol} [{period_result.period}] Balance: Missing required fields: "
                    f"{period_result.missing_required}"
                )
        
        # Validate cash flows
        for stmt in cash_flows:
            period_result = self.validate_statement(stmt, 'cashflow')
            result.add_result(period_result)
            
            if period_result.missing_required:
                logger.warning(
                    f"{symbol} [{period_result.period}] CashFlow: Missing required fields: "
                    f"{period_result.missing_required}"
                )
        
        if result.is_complete:
            logger.info(f"{symbol}: All required fields present (completeness: {result.average_completeness:.1%})")
        else:
            logger.warning(
                f"{symbol}: Incomplete data - {result.incomplete_periods}/{result.total_periods_validated} "
                f"periods missing required fields"
            )
        
        return result
    
    def get_missing_fields_summary(self, result: OverallValidationResult) -> Dict[str, List[str]]:
        """
        Get a summary of all missing fields across all periods.
        
        Returns:
            Dict with 'required' and 'important' keys, each containing unique missing field names
        """
        missing_required = set()
        missing_important = set()
        
        for period_result in result.period_results:
            missing_required.update(period_result.missing_required)
            missing_important.update(period_result.missing_important)
        
        return {
            'required': sorted(list(missing_required)),
            'important': sorted(list(missing_important))
        }

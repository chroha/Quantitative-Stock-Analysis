"""
Centralized Field Registry - Single source of truth for all data field mappings.

This registry defines:
1. All unified schema field names (std_*)
2. Mappings from each data source's field names to unified names
3. Priority ordering for intelligent field-level merging
4. Required vs optional field classification

统一字段注册表 - 所有数据字段映射的唯一真相来源。
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class DataSource(Enum):
    """Enumeration of data sources in priority order."""
    YAHOO = 'yahoo'
    SEC_EDGAR = 'sec_edgar'
    FMP = 'fmp'
    ALPHAVANTAGE = 'alphavantage'
    MANUAL = 'manual'


@dataclass
class FieldDefinition:
    """Definition of a unified schema field with source mappings."""
    unified_name: str
    description: str
    required: bool = False  # Required for downstream calculations
    important: bool = False  # Important but has fallbacks
    
    # Source-specific field names (None = not available from this source)
    yahoo_names: Optional[List[str]] = None  # List for alternatives
    edgar_tags: Optional[List[str]] = None   # XBRL tags in priority order
    fmp_names: Optional[List[str]] = None
    av_names: Optional[List[str]] = None
    
    # Merge priority (first available wins)
    priority: List[DataSource] = None
    
    def __post_init__(self):
        if self.priority is None:
            # Default priority: Yahoo > FMP > EDGAR > AlphaVantage
            self.priority = [DataSource.YAHOO, DataSource.FMP, DataSource.SEC_EDGAR, DataSource.ALPHAVANTAGE]


# =============================================================================
# INCOME STATEMENT FIELDS
# =============================================================================

INCOME_FIELDS: Dict[str, FieldDefinition] = {
    'std_revenue': FieldDefinition(
        unified_name='std_revenue',
        description='Total revenue',
        required=True,
        yahoo_names=['Total Revenue'],
        edgar_tags=['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'SalesRevenueNet', 'SalesRevenueServicesNet', 'SalesRevenueGoodsNet'],
        fmp_names=['revenue'],
        av_names=['totalRevenue'],
    ),
    'std_cost_of_revenue': FieldDefinition(
        unified_name='std_cost_of_revenue',
        description='Cost of revenue',
        important=True,
        yahoo_names=['Cost Of Revenue'],
        edgar_tags=['CostOfRevenue', 'CostOfGoodsAndServicesSold', 'CostOfGoodsSold', 'CostOfServices'],
        fmp_names=['costOfRevenue'],
        av_names=['costOfRevenue', 'costofGoodsAndServicesSold'],
    ),
    'std_gross_profit': FieldDefinition(
        unified_name='std_gross_profit',
        description='Gross profit',
        important=True,
        yahoo_names=['Gross Profit'],
        edgar_tags=['GrossProfit'],
        fmp_names=['grossProfit'],
        av_names=['grossProfit'],
    ),
    'std_operating_expenses': FieldDefinition(
        unified_name='std_operating_expenses',
        description='Operating expenses',
        yahoo_names=['Operating Expense'],
        edgar_tags=['OperatingExpenses'],
        fmp_names=['operatingExpenses'],
        av_names=['operatingExpenses'],
    ),
    'std_operating_income': FieldDefinition(
        unified_name='std_operating_income',
        description='Operating income',
        required=True,
        yahoo_names=['Operating Income'],
        edgar_tags=['OperatingIncomeLoss'],
        fmp_names=['operatingIncome'],
        av_names=['operatingIncome'],
    ),
    'std_pretax_income': FieldDefinition(
        unified_name='std_pretax_income',
        description='Income before tax',
        important=True,
        yahoo_names=['Pretax Income'],
        edgar_tags=['IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest', 'IncomeLossFromContinuingOperationsBeforeIncomeTaxes'],
        fmp_names=['incomeBeforeTax'],
        av_names=['incomeBeforeTax'],
    ),
    'std_income_tax_expense': FieldDefinition(
        unified_name='std_income_tax_expense',
        description='Income tax expense',
        important=True,
        yahoo_names=['Tax Provision'],
        edgar_tags=['IncomeTaxExpenseBenefit'],
        fmp_names=['incomeTaxExpense'],
        av_names=['incomeTaxExpense'],
    ),
    'std_net_income': FieldDefinition(
        unified_name='std_net_income',
        description='Net income',
        required=True,
        yahoo_names=['Net Income'],
        edgar_tags=['NetIncomeLoss', 'ProfitLoss'],
        fmp_names=['netIncome'],
        av_names=['netIncome'],
    ),
    'std_eps': FieldDefinition(
        unified_name='std_eps',
        description='Earnings per share (basic)',
        important=True,
        yahoo_names=['Basic EPS'],
        edgar_tags=['EarningsPerShareBasic'],
        fmp_names=['eps'],
        av_names=None,  # AV doesn't provide EPS directly in income statement
    ),
    'std_eps_diluted': FieldDefinition(
        unified_name='std_eps_diluted',
        description='Diluted EPS',
        yahoo_names=['Diluted EPS'],
        edgar_tags=['EarningsPerShareDiluted'],
        fmp_names=['epsdiluted'],
        av_names=None,
    ),
    'std_shares_outstanding': FieldDefinition(
        unified_name='std_shares_outstanding',
        description='Shares outstanding',
        important=True,
        yahoo_names=['Basic Average Shares'],
        edgar_tags=['WeightedAverageNumberOfSharesOutstandingBasic'],
        fmp_names=['weightedAverageShsOut'],
        av_names=None,
    ),
    'std_ebitda': FieldDefinition(
        unified_name='std_ebitda',
        description='EBITDA',
        important=True,
        yahoo_names=['EBITDA'],
        edgar_tags=None,  # Calculated from operating_income + D&A
        fmp_names=['ebitda'],
        av_names=['ebitda'],
    ),
}


# =============================================================================
# BALANCE SHEET FIELDS
# =============================================================================

BALANCE_FIELDS: Dict[str, FieldDefinition] = {
    'std_total_assets': FieldDefinition(
        unified_name='std_total_assets',
        description='Total assets',
        important=True,
        yahoo_names=['Total Assets'],
        edgar_tags=['Assets'],
        fmp_names=['totalAssets'],
        av_names=['totalAssets'],
    ),
    'std_current_assets': FieldDefinition(
        unified_name='std_current_assets',
        description='Current assets',
        important=True,
        yahoo_names=['Current Assets'],
        edgar_tags=['AssetsCurrent'],
        fmp_names=['totalCurrentAssets'],
        av_names=['totalCurrentAssets'],
    ),
    'std_cash': FieldDefinition(
        unified_name='std_cash',
        description='Cash and equivalents',
        important=True,
        yahoo_names=['Cash And Cash Equivalents'],
        edgar_tags=['CashAndCashEquivalentsAtCarryingValue'],
        fmp_names=['cashAndCashEquivalents'],
        av_names=['cashAndCashEquivalentsAtCarryingValue', 'cashAndShortTermInvestments'],
    ),
    'std_accounts_receivable': FieldDefinition(
        unified_name='std_accounts_receivable',
        description='Accounts receivable',
        yahoo_names=['Accounts Receivable'],
        edgar_tags=['AccountsReceivableNetCurrent', 'ReceivablesNetCurrent'],
        fmp_names=['netReceivables'],
        av_names=['currentNetReceivables'],
    ),
    'std_inventory': FieldDefinition(
        unified_name='std_inventory',
        description='Inventory',
        yahoo_names=['Inventory'],
        edgar_tags=['InventoryNet', 'InventoryFinishedGoodsNetOfReserves'],
        fmp_names=['inventory'],
        av_names=['inventory'],
    ),
    'std_total_liabilities': FieldDefinition(
        unified_name='std_total_liabilities',
        description='Total liabilities',
        important=True,
        yahoo_names=['Total Liabilities Net Minority Interest'],
        edgar_tags=['Liabilities'],
        fmp_names=['totalLiabilities'],
        av_names=['totalLiabilities'],
    ),
    'std_current_liabilities': FieldDefinition(
        unified_name='std_current_liabilities',
        description='Current liabilities',
        important=True,
        yahoo_names=['Current Liabilities'],
        edgar_tags=['LiabilitiesCurrent'],
        fmp_names=['totalCurrentLiabilities'],
        av_names=['totalCurrentLiabilities'],
    ),
    'std_total_debt': FieldDefinition(
        unified_name='std_total_debt',
        description='Total debt',
        required=True,
        yahoo_names=['Total Debt'],
        edgar_tags=['LongTermDebt', 'LongTermDebtNoncurrent', 'DebtInstrumentCarryingAmount'],
        fmp_names=['totalDebt'],
        av_names=['shortTermDebt', 'longTermDebt'],  # Will need combining
    ),
    'std_shareholder_equity': FieldDefinition(
        unified_name='std_shareholder_equity',
        description='Total shareholder equity',
        required=True,
        yahoo_names=['Stockholders Equity'],
        edgar_tags=['StockholdersEquity', 'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'],
        fmp_names=['totalStockholdersEquity'],
        av_names=['totalShareholderEquity'],
    ),
}


# =============================================================================
# CASH FLOW FIELDS
# =============================================================================

CASHFLOW_FIELDS: Dict[str, FieldDefinition] = {
    'std_operating_cash_flow': FieldDefinition(
        unified_name='std_operating_cash_flow',
        description='Operating cash flow',
        required=True,
        yahoo_names=['Operating Cash Flow'],
        edgar_tags=['NetCashProvidedByUsedInOperatingActivities'],
        fmp_names=['operatingCashFlow'],
        av_names=['operatingCashflow'],
    ),
    'std_investing_cash_flow': FieldDefinition(
        unified_name='std_investing_cash_flow',
        description='Investing cash flow',
        important=True,
        yahoo_names=['Investing Cash Flow'],
        edgar_tags=['NetCashProvidedByUsedInInvestingActivities'],
        fmp_names=['netCashUsedForInvestingActivites'],
        av_names=['cashflowFromInvestment'],
    ),
    'std_financing_cash_flow': FieldDefinition(
        unified_name='std_financing_cash_flow',
        description='Financing cash flow',
        important=True,
        yahoo_names=['Financing Cash Flow'],
        edgar_tags=['NetCashProvidedByUsedInFinancingActivities'],
        fmp_names=['netCashUsedProvidedByFinancingActivities'],
        av_names=['cashflowFromFinancing'],
    ),
    'std_capex': FieldDefinition(
        unified_name='std_capex',
        description='Capital expenditure',
        required=True,
        yahoo_names=['Capital Expenditure'],
        edgar_tags=['PaymentsToAcquireProductiveAssets', 'PaymentsToAcquirePropertyPlantAndEquipment', 'CapitalExpendituresIncurredButNotYetPaid'],
        fmp_names=['capitalExpenditure'],
        av_names=['capitalExpenditures'],
    ),
    'std_free_cash_flow': FieldDefinition(
        unified_name='std_free_cash_flow',
        description='Free cash flow',
        important=True,
        yahoo_names=['Free Cash Flow'],
        edgar_tags=None,  # Calculated: OCF - Capex
        fmp_names=['freeCashFlow'],
        av_names=None,  # Calculated
    ),
    'std_stock_based_compensation': FieldDefinition(
        unified_name='std_stock_based_compensation',
        description='Stock-based compensation expense',
        important=True,
        yahoo_names=['Stock Based Compensation'],
        edgar_tags=['ShareBasedCompensation', 'ShareBasedCompensationArrangementByShareBasedPaymentAwardEquityInstrumentsOtherThanOptionsVestedInPeriod'],
        fmp_names=['stockBasedCompensation'],
        av_names=None,
    ),
    'std_dividends_paid': FieldDefinition(
        unified_name='std_dividends_paid',
        description='Dividends paid (cash)',
        important=True,
        yahoo_names=['Cash Dividends Paid', 'Dividends Paid'],
        edgar_tags=['PaymentsOfDividends', 'PaymentsOfDividendsCommonStock', 'PaymentsOfDividendsMinorityInterest'],
        fmp_names=['dividendsPaid'],
        av_names=['dividendPayout', 'dividendPayoutCommonStock'],
    ),
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_all_fields() -> Dict[str, FieldDefinition]:
    """Get all field definitions across all statement types."""
    return {**INCOME_FIELDS, **BALANCE_FIELDS, **CASHFLOW_FIELDS}


def get_required_fields(statement_type: str) -> List[str]:
    """Get list of required field names for a statement type."""
    fields = {
        'income': INCOME_FIELDS,
        'balance': BALANCE_FIELDS,
        'cashflow': CASHFLOW_FIELDS,
    }.get(statement_type, {})
    
    return [name for name, defn in fields.items() if defn.required]


def get_important_fields(statement_type: str) -> List[str]:
    """Get list of important field names for a statement type."""
    fields = {
        'income': INCOME_FIELDS,
        'balance': BALANCE_FIELDS,
        'cashflow': CASHFLOW_FIELDS,
    }.get(statement_type, {})
    
    return [name for name, defn in fields.items() if defn.important]


def get_source_field_name(unified_name: str, source: DataSource) -> Optional[List[str]]:
    """Get source-specific field name(s) for a unified field."""
    all_fields = get_all_fields()
    defn = all_fields.get(unified_name)
    
    if not defn:
        return None
    
    mapping = {
        DataSource.YAHOO: defn.yahoo_names,
        DataSource.SEC_EDGAR: defn.edgar_tags,
        DataSource.FMP: defn.fmp_names,
        DataSource.ALPHAVANTAGE: defn.av_names,
    }
    
    return mapping.get(source)


def get_merge_priority(unified_name: str) -> List[DataSource]:
    """Get merge priority for a specific field."""
    all_fields = get_all_fields()
    defn = all_fields.get(unified_name)
    
    if defn and defn.priority:
        return defn.priority
    
    # Default priority
    return [DataSource.YAHOO, DataSource.FMP, DataSource.SEC_EDGAR, DataSource.ALPHAVANTAGE]

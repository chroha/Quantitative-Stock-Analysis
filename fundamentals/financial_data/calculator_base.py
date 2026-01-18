"""
Base calculator class with anomaly detection framework.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from utils.logger import setup_logger

logger = setup_logger('calculator_base')


@dataclass
class MetricWarning:
    """Represents a warning/anomaly detected during calculation."""
    metric_name: str
    warning_type: str  # 'out_of_bounds', 'data_missing', 'calculation_error', 'negative_base'
    message: str
    severity: str  # 'info', 'warning', 'error'
    value: Optional[float] = None


@dataclass
class CalculationResult:
    """Generic calculation result with warnings."""
    value: Optional[float]
    intermediate_values: Dict[str, Any] = field(default_factory=dict)
    warnings: List[MetricWarning] = field(default_factory=list)
    calculation_date: datetime = field(default_factory=datetime.now)
    
    def add_warning(
        self,
        metric_name: str,
        warning_type: str,
        message: str,
        severity: str = 'warning',
        value: Optional[float] = None
    ):
        """Add a warning to this result."""
        warning = MetricWarning(
            metric_name=metric_name,
            warning_type=warning_type,
            message=message,
            severity=severity,
            value=value
        )
        self.warnings.append(warning)
        logger.warning(f"[{metric_name}] {message}")


class CalculatorBase:
    """
    Base class for all financial calculators.
    Provides common utilities and anomaly detection framework.
    """
    
    def __init__(self, symbol: str):
        """
        Initialize calculator.
        
        Args:
            symbol: Stock ticker symbol
        """
        self.symbol = symbol
        self.logger = setup_logger(f'{self.__class__.__name__}_{symbol}')
    
    def safe_divide(
        self,
        numerator: Optional[float],
        denominator: Optional[float],
        metric_name: str,
        result: CalculationResult
    ) -> Optional[float]:
        """
        Safely divide two numbers with error handling.
        
        Args:
            numerator: Numerator value
            denominator: Denominator value
            metric_name: Name of metric being calculated (for warnings)
            result: CalculationResult to add warnings to
            
        Returns:
            Division result or None if invalid
        """
        if numerator is None:
            result.add_warning(
                metric_name,
                'data_missing',
                f'Numerator is None',
                'error'
            )
            return None
        
        if denominator is None:
            result.add_warning(
                metric_name,
                'data_missing',
                f'Denominator is None',
                'error'
            )
            return None
        
        if denominator == 0:
            result.add_warning(
                metric_name,
                'calculation_error',
                f'Division by zero (denominator={denominator})',
                'error'
            )
            return None
        
        return numerator / denominator
    
    def check_bounds(
        self,
        value: Optional[float],
        metric_name: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        result: CalculationResult = None
    ) -> bool:
        """
        Check if value is within expected bounds.
        
        Args:
            value: Value to check
            metric_name: Metric name
            min_value: Minimum expected value (None = no check)
            max_value: Maximum expected value (None = no check)
            result: CalculationResult to add warnings to
            
        Returns:
            True if in bounds, False otherwise
        """
        if value is None:
            return True  # None is handled elsewhere
        
        in_bounds = True
        
        if min_value is not None and value < min_value:
            if result:
                result.add_warning(
                    metric_name,
                    'out_of_bounds',
                    f'Value {value:.4f} below minimum {min_value}',
                    'warning',
                    value
                )
            in_bounds = False
        
        if max_value is not None and value > max_value:
            if result:
                result.add_warning(
                    metric_name,
                    'out_of_bounds',
                    f'Value {value:.4f} above maximum {max_value}',
                    'warning',
                    value
                )
            in_bounds = False
        
        return in_bounds
    
    def get_field_value(self, data_obj, field_name: str) -> Optional[float]:
        """
        Safely extract field value from Pydantic model.
        
        Args:
            data_obj: Pydantic model instance
            field_name: Field name to extract
            
        Returns:
            Field value or None
        """
        field = getattr(data_obj, field_name, None)
        if field and hasattr(field, 'value'):
            return field.value
        return None
    
    def calculate_time_weighted_cagr(
        self,
        values: List[float],
        metric_name: str,
        weights: List[float] = None
    ) -> CalculationResult:
        """
        Calculate time-weighted CAGR.
        More recent years get higher weights.
        
        Args:
            values: List of values (oldest to newest)
            metric_name: Metric name for warnings
            weights: Optional custom weights (default: [0.10, 0.15, 0.20, 0.25, 0.30])
        
        Returns:
            CalculationResult with weighted CAGR
        """
        result = CalculationResult(value=None)
        
        if weights is None:
            weights = [0.10, 0.15, 0.20, 0.25, 0.30]  # 5-year default
        
        if len(values) < 2:
            result.add_warning(
                metric_name,
                'data_missing',
                f'Need at least 2 years of data, got {len(values)}',
                'error'
            )
            return result
        
        # Calculate year-over-year growth rates
        growth_rates = []
        for i in range(len(values) - 1):
            if values[i] is None or values[i+1] is None:
                result.add_warning(
                    metric_name,
                    'data_missing',
                    f'Missing value at year {i} or {i+1}',
                    'warning'
                )
                growth_rates.append(0.0)
                continue
            
            if values[i] <= 0:
                result.add_warning(
                    metric_name,
                    'negative_base',
                    f'Year {i} base value is {values[i]:.2f} (≤0), using 0% growth',
                    'warning',
                    values[i]
                )
                growth_rates.append(0.0)
            else:
                growth_rate = (values[i+1] / values[i]) - 1
                growth_rates.append(growth_rate)
        
        # Align weights to growth rates (use most recent weights)
        # e.g. if we have 4 growth rates, use the last 4 weights [0.15, 0.20, 0.25, 0.30]
        # This ensures the most recent year always gets the highest weight
        num_rates = len(growth_rates)
        if num_rates > len(weights):
            # Extend weights if needed (repeat max weight or just truncate data? Truncate data for now or warn)
            # But normally we have 5 years max.
            # Let's just take the last N items of weights if N < len(weights)
            # If N > len(weights), we'll pad or handle? 
            # Given the 'weights' default is just 5 items, let's just use what we have.
             weights_subset = weights[-num_rates:] if num_rates <= len(weights) else weights
        else:
            weights_subset = weights[-num_rates:]
            
        total_weight = sum(weights_subset)
        
        if total_weight == 0:
             result.add_warning(metric_name, 'calculation_error', 'Total weight is zero', 'error')
             return result

        # Apply weights
        # We need to match oldest growth rate with lowest weight in the subset
        # growth_rates are Oldest -> Newest.
        # weights_subset should be Lowest -> Highest.
        # So we just zip them.
        
        weighted_sum = sum(
            g * w for g, w in zip(growth_rates, weights_subset)
        )
        
        weighted_cagr = weighted_sum / total_weight
        
        result.value = weighted_cagr
        result.intermediate_values = {
            'growth_rates': growth_rates,
            'weights_used': weights_subset,
            'total_weight': total_weight,
            'num_years': len(values)
        }
        
        return result

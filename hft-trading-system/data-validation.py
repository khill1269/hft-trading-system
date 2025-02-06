from typing import Dict, Any, Optional, List
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass, field

@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

class BaseModel:
    """Base class for all data models with validation"""
    
    def validate(self) -> ValidationResult:
        """
        Validate the model data
        Returns:
            ValidationResult object containing validation status and any errors/warnings
        """
        result = ValidationResult(is_valid=True)
        
        # Get validation rules for this class
        validation_rules = getattr(self, '_validation_rules', {})
        
        for field_name, rules in validation_rules.items():
            value = getattr(self, field_name, None)
            
            for rule in rules:
                rule_result = rule(value, field_name)
                if not rule_result.is_valid:
                    result.is_valid = False
                    result.errors.extend(rule_result.errors)
                result.warnings.extend(rule_result.warnings)
        
        return result

@dataclass
class Trade(BaseModel):
    """Example trade data model"""
    symbol: str
    quantity: Decimal
    price: Decimal
    side: str  # 'BUY' or 'SELL'
    order_type: str  # 'MARKET' or 'LIMIT'
    timestamp: datetime
    order_id: Optional[str] = None
    status: str = 'PENDING'  # PENDING, FILLED, CANCELLED, REJECTED
    
    _validation_rules = {
        'symbol': [
            lambda x, f: ValidationResult(
                is_valid=bool(x and isinstance(x, str)),
                errors=[f"{f} must be a non-empty string"] if not (x and isinstance(x, str)) else []
            )
        ],
        'quantity': [
            lambda x, f: ValidationResult(
                is_valid=isinstance(x, Decimal) and x > 0,
                errors=[f"{f} must be a positive number"] if not (isinstance(x, Decimal) and x > 0) else []
            )
        ],
        'price': [
            lambda x, f: ValidationResult(
                is_valid=isinstance(x, Decimal) and x > 0,
                errors=[f"{f} must be a positive number"] if not (isinstance(x, Decimal) and x > 0) else []
            )
        ],
        'side': [
            lambda x, f: ValidationResult(
                is_valid=x in {'BUY', 'SELL'},
                errors=[f"{f} must be either 'BUY' or 'SELL'"] if x not in {'BUY', 'SELL'} else []
            )
        ],
        'order_type': [
            lambda x, f: ValidationResult(
                is_valid=x in {'MARKET', 'LIMIT'},
                errors=[f"{f} must be either 'MARKET' or 'LIMIT'"] if x not in {'MARKET', 'LIMIT'} else []
            )
        ],
        'timestamp': [
            lambda x, f: ValidationResult(
                is_valid=isinstance(x, datetime),
                errors=[f"{f} must be a datetime object"] if not isinstance(x, datetime) else []
            )
        ],
        'status': [
            lambda x, f: ValidationResult(
                is_valid=x in {'PENDING', 'FILLED', 'CANCELLED', 'REJECTED'},
                errors=[f"{f} must be a valid status"] if x not in {'PENDING', 'FILLED', 'CANCELLED', 'REJECTED'} else []
            )
        ]
    }

@dataclass
class Position(BaseModel):
    """Example position data model"""
    symbol: str
    quantity: Decimal
    average_price: Decimal
    current_price: Decimal
    timestamp: datetime
    unrealized_pnl: Decimal = field(init=False)
    position_value: Decimal = field(init=False)
    
    def __post_init__(self):
        self.unrealized_pnl = (self.current_price - self.average_price) * self.quantity
        self.position_value = self.current_price * self.quantity
    
    _validation_rules = {
        'symbol': [
            lambda x, f: ValidationResult(
                is_valid=bool(x and isinstance(x, str)),
                errors=[f"{f} must be a non-empty string"] if not (x and isinstance(x, str)) else []
            )
        ],
        'quantity': [
            lambda x, f: ValidationResult(
                is_valid=isinstance(x, Decimal),
                errors=[f"{f} must be a number"] if not isinstance(x, Decimal) else []
            )
        ],
        'average_price': [
            lambda x, f: ValidationResult(
                is_valid=isinstance(x, Decimal) and x > 0,
                errors=[f"{f} must be a positive number"] if not (isinstance(x, Decimal) and x > 0) else []
            )
        ],
        'current_price': [
            lambda x, f: ValidationResult(
                is_valid=isinstance(x, Decimal) and x > 0,
                errors=[f"{f} must be a positive number"] if not (isinstance(x, Decimal) and x > 0) else []
            )
        ],
        'timestamp': [
            lambda x, f: ValidationResult(
                is_valid=isinstance(x, datetime),
                errors=[f"{f} must be a datetime object"] if not isinstance(x, datetime) else []
            )
        ]
    }

class ValidationUtils:
    """Utility class for common validation functions"""
    
    @staticmethod
    def validate_price_precision(price: Decimal, max_decimals: int = 8) -> ValidationResult:
        """Validate price precision"""
        try:
            str_price = str(price)
            decimals = len(str_price.split('.')[1]) if '.' in str_price else 0
            return ValidationResult(
                is_valid=decimals <= max_decimals,
                errors=[f"Price has too many decimal places (max {max_decimals})"] if decimals > max_decimals else []
            )
        except Exception:
            return ValidationResult(is_valid=False, errors=["Invalid price format"])
    
    @staticmethod
    def validate_quantity_precision(quantity: Decimal, max_decimals: int = 8) -> ValidationResult:
        """Validate quantity precision"""
        try:
            str_qty = str(quantity)
            decimals = len(str_qty.split('.')[1]) if '.' in str_qty else 0
            return ValidationResult(
                is_valid=decimals <= max_decimals,
                errors=[f"Quantity has too many decimal places (max {max_decimals})"] if decimals > max_decimals else []
            )
        except Exception:
            return ValidationResult(is_valid=False, errors=["Invalid quantity format"])

    @staticmethod
    def validate_timestamp_range(timestamp: datetime, max_future_seconds: int = 60) -> ValidationResult:
        """Validate timestamp is not too far in the future"""
        now = datetime.utcnow()
        if timestamp > now:
            future_diff = (timestamp - now).total_seconds()
            return ValidationResult(
                is_valid=future_diff <= max_future_seconds,
                errors=[f"Timestamp is too far in the future"] if future_diff > max_future_seconds else []
            )
        return ValidationResult(is_valid=True)

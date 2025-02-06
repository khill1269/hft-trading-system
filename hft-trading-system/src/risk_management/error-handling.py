from enum import Enum
from typing import Optional, Any, Dict
from datetime import datetime
import traceback
from functools import wraps

class ErrorSeverity(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class TradingSystemError(Exception):
    """Base exception class for the trading system"""
    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.severity = severity
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.utcnow()
        self.traceback = traceback.format_exc()

class ValidationError(TradingSystemError):
    """Raised when data validation fails"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            error_code="VALIDATION_ERROR",
            details=details
        )

class TradeExecutionError(TradingSystemError):
    """Raised when trade execution fails"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            error_code="TRADE_EXECUTION_ERROR",
            details=details
        )

class MarketDataError(TradingSystemError):
    """Raised when there are issues with market data"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            error_code="MARKET_DATA_ERROR",
            details=details
        )

class SystemError(TradingSystemError):
    """Raised for critical system errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            severity=ErrorSeverity.CRITICAL,
            error_code="SYSTEM_ERROR",
            details=details
        )

def handle_errors(logger):
    """
    Decorator for handling errors in a consistent way
    
    Args:
        logger: Logger instance to use for error logging
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except TradingSystemError as e:
                logger.log_error(e, context=func.__name__)
                if e.severity == ErrorSeverity.CRITICAL:
                    # Implement emergency shutdown if needed
                    raise
                return None
            except Exception as e:
                # Wrap unknown exceptions
                system_error = SystemError(
                    f"Unexpected error in {func.__name__}: {str(e)}",
                    details={"original_error": str(e)}
                )
                logger.log_error(system_error, context=func.__name__)
                raise system_error
        return wrapper
    return decorator

class ErrorHandler:
    """Central error handling facility"""
    
    def __init__(self, logger):
        self.logger = logger
        self._error_counts: Dict[str, int] = {}
        self._error_thresholds = {
            ErrorSeverity.LOW: 100,
            ErrorSeverity.MEDIUM: 50,
            ErrorSeverity.HIGH: 10,
            ErrorSeverity.CRITICAL: 1
        }
    
    def handle_error(self, error: TradingSystemError) -> None:
        """
        Handle an error based on its severity and type
        
        Args:
            error: The error to handle
        """
        # Log the error
        self.logger.log_error(error, context=error.__class__.__name__)
        
        # Update error counts
        error_type = error.__class__.__name__
        self._error_counts[error_type] = self._error_counts.get(error_type, 0) + 1
        
        # Check thresholds
        if self._error_counts[error_type] >= self._error_thresholds[error.severity]:
            self._handle_threshold_exceeded(error)
    
    def _handle_threshold_exceeded(self, error: TradingSystemError) -> None:
        """Handle cases where error thresholds are exceeded"""
        message = (
            f"Error threshold exceeded for {error.__class__.__name__} "
            f"with severity {error.severity.value}"
        )
        self.logger.log_event(
            "ERROR_THRESHOLD_EXCEEDED",
            message,
            level="CRITICAL",
            extra_data={"error_counts": self._error_counts}
        )
        
        if error.severity in {ErrorSeverity.HIGH, ErrorSeverity.CRITICAL}:
            # Implement emergency shutdown or circuit breaker logic here
            pass

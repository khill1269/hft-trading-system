from enum import Enum
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable, Any
from threading import Lock
import time

class CircuitState(Enum):
    CLOSED = "CLOSED"  # Normal operation
    OPEN = "OPEN"      # No operations allowed
    HALF_OPEN = "HALF_OPEN"  # Testing if system can resume

class CircuitBreakerStatus:
    def __init__(self, name: str, state: CircuitState):
        self.name = name
        self.state = state
        self.last_state_change = datetime.utcnow()
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.successful_test_calls = 0

class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        reset_timeout: int = 60,
        half_open_timeout: int = 30,
        test_calls_required: int = 3,
        logger: Any = None
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.half_open_timeout = half_open_timeout
        self.test_calls_required = test_calls_required
        self.logger = logger
        
        self.status = CircuitBreakerStatus(name, CircuitState.CLOSED)
        self._lock = Lock()
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute the protected function with circuit breaker logic"""
        with self._lock:
            if not self._can_execute():
                raise CircuitBreakerError(f"Circuit {self.name} is {self.status.state.value}")
            
            try:
                result = func(*args, **kwargs)
                self._handle_success()
                return result
            except Exception as e:
                self._handle_failure(e)
                raise
    
    def _can_execute(self) -> bool:
        """Determine if execution is allowed based on current state"""
        current_time = datetime.utcnow()
        
        if self.status.state == CircuitState.CLOSED:
            return True
            
        elif self.status.state == CircuitState.OPEN:
            # Check if enough time has passed to move to HALF_OPEN
            if (current_time - self.status.last_state_change).total_seconds() >= self.reset_timeout:
                self._transition_to(CircuitState.HALF_OPEN)
                return True
            return False
            
        elif self.status.state == CircuitState.HALF_OPEN:
            # Only allow limited test calls in HALF_OPEN state
            return True
            
        return False
    
    def _handle_success(self) -> None:
        """Handle successful execution"""
        if self.status.state == CircuitState.HALF_OPEN:
            self.status.successful_test_calls += 1
            if self.status.successful_test_calls >= self.test_calls_required:
                self._transition_to(CircuitState.CLOSED)
        
        # Reset failure count on success in CLOSED state
        elif self.status.state == CircuitState.CLOSED:
            self.status.failure_count = 0
    
    def _handle_failure(self, error: Exception) -> None:
        """Handle execution failure"""
        self.status.last_failure_time = datetime.utcnow()
        
        if self.status.state == CircuitState.HALF_OPEN:
            self._transition_to(CircuitState.OPEN)
            
        elif self.status.state == CircuitState.CLOSED:
            self.status.failure_count += 1
            if self.status.failure_count >= self.failure_threshold:
                self._transition_to(CircuitState.OPEN)
    
    def _transition_to(self, new_state: CircuitState) -> None:
        """Handle state transition"""
        old_state = self.status.state
        self.status.state = new_state
        self.status.last_state_change = datetime.utcnow()
        
        if new_state == CircuitState.CLOSED:
            self.status.failure_count = 0
            self.status.successful_test_calls = 0
        elif new_state == CircuitState.HALF_OPEN:
            self.status.successful_test_calls = 0
            
        if self.logger:
            self.logger.log_event(
                "CIRCUIT_BREAKER_TRANSITION",
                f"Circuit {self.name} transitioned from {old_state.value} to {new_state.value}",
                level="WARNING" if new_state == CircuitState.OPEN else "INFO"
            )

class CircuitBreakerError(Exception):
    """Raised when circuit breaker prevents execution"""
    pass

class CircuitBreakerRegistry:
    """Central registry for managing multiple circuit breakers"""
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = Lock()
    
    def register(self, breaker: CircuitBreaker) -> None:
        """Register a new circuit breaker"""
        with self._lock:
            if breaker.name in self._breakers:
                raise ValueError(f"Circuit breaker {breaker.name} already registered")
            self._breakers[breaker.name] = breaker
    
    def get_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """Get a circuit breaker by name"""
        return self._breakers.get(name)
    
    def get_all_statuses(self) -> Dict[str, CircuitBreakerStatus]:
        """Get status of all circuit breakers"""
        return {name: breaker.status for name, breaker in self._breakers.items()}

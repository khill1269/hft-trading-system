import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional
import threading

class LoggingManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    def __init__(self):
        self.logger = None
        
    def setup_logging(
        self,
        log_dir: str = "logs",
        filename: str = "trading_system.log",
        level: int = logging.INFO,
        max_bytes: int = 10_000_000,  # 10MB
        backup_count: int = 5,
        console_output: bool = True
    ) -> None:
        """
        Initialize logging with rotation and console output options
        
        Args:
            log_dir: Directory to store log files
            filename: Name of the log file
            level: Logging level
            max_bytes: Maximum size of each log file
            backup_count: Number of backup files to keep
            console_output: Whether to also log to console
        """
        try:
            # Ensure log directory exists
            log_path = Path(log_dir)
            log_path.mkdir(parents=True, exist_ok=True)
            
            # Create full file path
            full_path = log_path / filename
            
            # Configure logger
            self.logger = logging.getLogger('TradingSystem')
            self.logger.setLevel(level)
            
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s'
            )
            
            # Setup file handler with rotation
            file_handler = RotatingFileHandler(
                filename=str(full_path),
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
            
            # Add console handler if requested
            if console_output:
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(formatter)
                self.logger.addHandler(console_handler)
                
        except Exception as e:
            raise RuntimeError(f"Failed to initialize logging: {str(e)}")
    
    def log_event(
        self,
        event_type: str,
        message: str,
        level: str = "INFO",
        extra_data: Optional[dict] = None
    ) -> None:
        """
        Log an event with optional extra data
        
        Args:
            event_type: Type of event being logged
            message: Main log message
            level: Logging level (INFO, WARNING, ERROR, CRITICAL, DEBUG)
            extra_data: Optional dictionary of additional data to log
        """
        if self.logger is None:
            raise RuntimeError("Logging has not been initialized. Call setup_logging first.")
            
        log_message = f"{event_type}: {message}"
        if extra_data:
            log_message += f" | Additional Data: {extra_data}"
            
        log_level = getattr(logging, level.upper(), logging.INFO)
        self.logger.log(log_level, log_message)
    
    def log_error(self, error: Exception, context: str = "") -> None:
        """
        Specialized method for logging exceptions
        
        Args:
            error: The exception to log
            context: Additional context about where/why the error occurred
        """
        if self.logger is None:
            raise RuntimeError("Logging has not been initialized. Call setup_logging first.")
            
        error_message = f"Error in {context}: {str(error)}"
        self.logger.error(error_message, exc_info=True)

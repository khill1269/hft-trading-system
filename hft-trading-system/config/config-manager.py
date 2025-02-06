from dataclasses import dataclass
from pathlib import Path
import yaml
import os
from typing import Dict, Any, Optional
from threading import Lock

@dataclass
class DatabaseConfig:
    host: str
    port: int
    database: str
    username: str
    password: str
    pool_size: int = 5
    timeout: int = 30

@dataclass
class TradingConfig:
    max_position_size: float
    risk_limit_percent: float
    max_trades_per_day: int
    trading_hours_start: str
    trading_hours_end: str
    emergency_stop_loss: float

@dataclass
class LoggingConfig:
    log_level: str
    log_dir: str
    max_file_size_mb: int
    backup_count: int

class ConfigurationManager:
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    def __init__(self):
        self._config: Dict[str, Any] = {}
        self._config_file: Optional[Path] = None
        self._env: str = os.getenv('TRADING_ENV', 'development')
        
    def load_config(self, config_path: str = "config") -> None:
        """Load configuration from YAML files based on environment"""
        self._config_file = Path(config_path) / f"{self._env}.yaml"
        
        if not self._config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {self._config_file}")
            
        with open(self._config_file, 'r') as f:
            self._config = yaml.safe_load(f)
            
        # Validate required sections
        required_sections = {'database', 'trading', 'logging'}
        missing_sections = required_sections - set(self._config.keys())
        if missing_sections:
            raise ValueError(f"Missing required configuration sections: {missing_sections}")
    
    @property
    def database(self) -> DatabaseConfig:
        """Get database configuration"""
        db_config = self._config.get('database', {})
        return DatabaseConfig(
            host=db_config['host'],
            port=db_config['port'],
            database=db_config['database'],
            username=db_config['username'],
            password=db_config['password'],
            pool_size=db_config.get('pool_size', 5),
            timeout=db_config.get('timeout', 30)
        )
    
    @property
    def trading(self) -> TradingConfig:
        """Get trading configuration"""
        trading_config = self._config.get('trading', {})
        return TradingConfig(
            max_position_size=trading_config['max_position_size'],
            risk_limit_percent=trading_config['risk_limit_percent'],
            max_trades_per_day=trading_config['max_trades_per_day'],
            trading_hours_start=trading_config['trading_hours_start'],
            trading_hours_end=trading_config['trading_hours_end'],
            emergency_stop_loss=trading_config['emergency_stop_loss']
        )
    
    @property
    def logging(self) -> LoggingConfig:
        """Get logging configuration"""
        logging_config = self._config.get('logging', {})
        return LoggingConfig(
            log_level=logging_config['log_level'],
            log_dir=logging_config['log_dir'],
            max_file_size_mb=logging_config['max_file_size_mb'],
            backup_count=logging_config['backup_count']
        )
    
    def get_value(self, key_path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation
        Example: config.get_value('database.host')
        """
        keys = key_path.split('.')
        value = self._config
        for key in keys:
            value = value.get(key, default)
            if value == default:
                return default
        return value

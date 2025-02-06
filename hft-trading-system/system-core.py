from typing import Dict, Any, Optional
import yaml
import os
import json
from pathlib import Path
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
import redis
from pymongo import MongoClient
import logging
import threading
from datetime import datetime
import asyncio

class DatabaseManager:
    """Centralized database management system"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    def __init__(self):
        self.config = ConfigManager().get_config()
        self.sql_engine = None
        self.sql_session = None
        self.redis_client = None
        self.mongo_client = None
        self.Base = declarative_base()
        self.metadata = MetaData()
        
        # Initialize connections
        self._initialize_sql()
        self._initialize_redis()
        self._initialize_mongo()
    
    def _initialize_sql(self) -> None:
        """Initialize SQL database connection"""
        try:
            db_config = self.config['database']['sql']
            connection_string = (
                f"postgresql://{db_config['user']}:{db_config['password']}@"
                f"{db_config['host']}:{db_config['port']}/{db_config['database']}"
            )
            
            self.sql_engine = create_engine(
                connection_string,
                pool_size=db_config.get('pool_size', 5),
                max_overflow=db_config.get('max_overflow', 10),
                pool_timeout=db_config.get('timeout', 30)
            )
            
            session_factory = sessionmaker(bind=self.sql_engine)
            self.sql_session = scoped_session(session_factory)
            
            # Create tables
            self.Base.metadata.create_all(self.sql_engine)
            
        except Exception as e:
            logging.error(f"SQL initialization failed: {str(e)}")
            raise
    
    def _initialize_redis(self) -> None:
        """Initialize Redis connection"""
        try:
            redis_config = self.config['database']['redis']
            self.redis_client = redis.Redis(
                host=redis_config['host'],
                port=redis_config['port'],
                password=redis_config.get('password'),
                db=redis_config.get('db', 0),
                decode_responses=True
            )
            
            # Test connection
            self.redis_client.ping()
            
        except Exception as e:
            logging.error(f"Redis initialization failed: {str(e)}")
            raise
    
    def _initialize_mongo(self) -> None:
        """Initialize MongoDB connection"""
        try:
            mongo_config = self.config['database']['mongo']
            connection_string = (
                f"mongodb://{mongo_config['user']}:{mongo_config['password']}@"
                f"{mongo_config['host']}:{mongo_config['port']}"
            )
            
            self.mongo_client = MongoClient(connection_string)
            self.mongo_db = self.mongo_client[mongo_config['database']]
            
            # Test connection
            self.mongo_client.server_info()
            
        except Exception as e:
            logging.error(f"MongoDB initialization failed: {str(e)}")
            raise
    
    def get_sql_session(self):
        """Get SQL session"""
        return self.sql_session()
    
    def get_redis_client(self):
        """Get Redis client"""
        return self.redis_client
    
    def get_mongo_db(self):
        """Get MongoDB database"""
        return self.mongo_db

class ConfigManager:
    """Configuration management system"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    def __init__(self):
        self._config = {}
        self._env_vars = {}
        self._load_config()
        self._load_env_vars()
    
    def _load_config(self) -> None:
        """Load configuration from files"""
        try:
            config_dir = Path("config")
            env = os.getenv("TRADING_ENV", "development")
            
            # Load base config
            base_config = self._load_yaml(config_dir / "base.yaml")
            
            # Load environment specific config
            env_config = self._load_yaml(config_dir / f"{env}.yaml")
            
            # Merge configurations
            self._config = self._deep_merge(base_config, env_config)
            
        except Exception as e:
            logging.error(f"Configuration loading failed: {str(e)}")
            raise
    
    def _load_yaml(self, path: Path) -> Dict:
        """Load YAML configuration file"""
        try:
            if path.exists():
                with open(path, 'r') as f:
                    return yaml.safe_load(f)
            return {}
        except Exception as e:
            logging.error(f"YAML loading failed for {path}: {str(e)}")
            return {}
    
    def _load_env_vars(self) -> None:
        """Load environment variables"""
        prefix = "TRADING_"
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower()
                self._env_vars[config_key] = value
    
    def _deep_merge(self, dict1: Dict, dict2: Dict) -> Dict:
        """Deep merge two dictionaries"""
        result = dict1.copy()
        
        for key, value in dict2.items():
            if (
                key in result and 
                isinstance(result[key], dict) and 
                isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def get_config(self) -> Dict:
        """Get complete configuration"""
        return self._config
    
    def get_env_vars(self) -> Dict:
        """Get environment variables"""
        return self._env_vars
    
    def get_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        # Check environment variables first
        env_key = f"TRADING_{key.upper()}"
        if env_key in os.environ:
            return os.environ[env_key]
        
        # Check loaded config
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        
        return value if value is not None else default

class MessageQueue:
    """Message queueing system"""
    
    def __init__(self):
        self.config = ConfigManager().get_config()
        self.redis_client = DatabaseManager().get_redis_client()
        self._subscribers: Dict[str, List[callable]] = {}
    
    async def publish(self, channel: str, message: Dict) -> None:
        """Publish message to channel"""
        try:
            message_str = json.dumps({
                'timestamp': datetime.utcnow().isoformat(),
                'channel': channel,
                'data': message
            })
            
            await self.redis_client.publish(channel, message_str)
            
        except Exception as e:
            logging.error(f"Message publishing failed: {str(e)}")
            raise
    
    async def subscribe(self, channel: str, callback: callable) -> None:
        """Subscribe to channel"""
        try:
            if channel not in self._subscribers:
                self._subscribers[channel] = []
                
                # Start listening if first subscriber
                if len(self._subscribers[channel]) == 0:
                    asyncio.create_task(self._start_listener(channel))
            
            self._subscribers[channel].append(callback)
            
        except Exception as e:
            logging.error(f"Subscription failed: {str(e)}")
            raise
    
    async def _start_listener(self, channel: str) -> None:
        """Start listening for messages"""
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(channel)
        
        try:
            while True:
                message = await pubsub.get_message()
                if message and message['type'] == 'message':
                    data = json.loads(message['data'])
                    
                    # Notify subscribers
                    for callback in self._subscribers.get(channel, []):
                        try:
                            await callback(data)
                        except Exception as e:
                            logging.error(f"Callback error: {str(e)}")
                
                await asyncio.sleep(0.001)
                
        except Exception as e:
            logging.error(f"Message listener failed: {str(e)}")
            await pubsub.unsubscribe(channel)
            
            # Retry connection
            await asyncio.sleep(5)
            asyncio.create_task(self._start_listener(channel))

class SystemMonitor:
    """System monitoring and health checks"""
    
    def __init__(self):
        self.config = ConfigManager().get_config()
        self.db_manager = DatabaseManager()
        self._components = {}
        self._status = {}
        self._last_heartbeat = {}
        
        # Start monitoring
        self._start_monitor()
    
    def register_component(
        self,
        component_name: str,
        health_check: callable
    ) -> None:
        """Register component for monitoring"""
        self._components[component_name] = health_check
        self._status[component_name] = True
        self._last_heartbeat[component_name] = datetime.utcnow()
    
    def heartbeat(self, component_name: str) -> None:
        """Record component heartbeat"""
        self._last_heartbeat[component_name] = datetime.utcnow()
    
    def get_system_status(self) -> Dict:
        """Get complete system status"""
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'components': {
                name: {
                    'status': self._status[name],
                    'last_heartbeat': self._last_heartbeat[name].isoformat()
                }
                for name in self._components
            },
            'database': {
                'sql': self._check_sql_connection(),
                'redis': self._check_redis_connection(),
                'mongo': self._check_mongo_connection()
            }
        }
    
    def _start_monitor(self) -> None:
        """Start monitoring thread"""
        def monitor():
            while True:
                try:
                    self._check_components()
                    self._check_database_connections()
                    self._cleanup_stale_data()
                except Exception as e:
                    logging.error(f"System monitoring failed: {str(e)}")
                time.sleep(5)
        
        threading.Thread(target=monitor, daemon=True).start()
    
    def _check_components(self) -> None:
        """Check all registered components"""
        for name, health_check in self._components.items():
            try:
                status = health_check()
                self._status[name] = status
                
                if not status:
                    logging.warning(f"Component {name} health check failed")
                    
            except Exception as e:
                self._status[name] = False
                logging.error(f"Component {name} check failed: {str(e)}")
    
    def _check_sql_connection(self) -> bool:
        """Check SQL database connection"""
        try:
            session = self.db_manager.get_sql_session()
            session.execute("SELECT 1")
            return True
        except Exception:
            return False
        finally:
            session.close()
    
    def _check_redis_connection(self) -> bool:
        """Check Redis connection"""
        try:
            return self.db_manager.redis_client.ping()
        except Exception:
            return False
    
    def _check_mongo_connection(self) -> bool:
        """Check MongoDB connection"""
        try:
            self.db_manager.mongo_client.server_info()
            return True
        except Exception:
            return False
    
    def _cleanup_stale_data(self) -> None:
        """Clean up old monitoring data"""
        try:
            # Clean up old heartbeats
            current_time = datetime.utcnow()
            for component in list(self._last_heartbeat.keys()):
                if component not in self._components:
                    del self._last_heartbeat[component]
                    del self._status[component]
                    
        except Exception as e:
            logging.error(f"Data cleanup failed: {str(e)}")

class Error(Exception):
    """Base error class"""
    pass

class ConfigError(Error):
    """Configuration error"""
    pass

class DatabaseError(Error):
    """Database error"""
    pass

class MessageQueueError(Error):
    """Message queue error"""
    pass

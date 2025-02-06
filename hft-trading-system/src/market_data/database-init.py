from typing import Dict, List, Optional
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, DateTime, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
import redis
from pymongo import MongoClient
import logging
import yaml
import os
from datetime import datetime

Base = declarative_base()

class MarketData(Base):
    """Market data table"""
    __tablename__ = 'market_data'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String, index=True)
    timestamp = Column(DateTime, index=True)
    price = Column(Float)
    volume = Column(Float)
    bid = Column(Float)
    ask = Column(Float)
    trade_id = Column(String)
    source = Column(String)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class Trade(Base):
    """Trade execution table"""
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(String, index=True)
    symbol = Column(String, index=True)
    side = Column(String)
    quantity = Column(Float)
    price = Column(Float)
    execution_time = Column(DateTime, index=True)
    venue = Column(String)
    strategy_id = Column(String, index=True)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class Order(Base):
    """Order table"""
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(String, unique=True, index=True)
    symbol = Column(String, index=True)
    side = Column(String)
    order_type = Column(String)
    quantity = Column(Float)
    price = Column(Float)
    status = Column(String, index=True)
    strategy_id = Column(String, index=True)
    parent_order_id = Column(String)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Position(Base):
    """Position table"""
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String, unique=True, index=True)
    quantity = Column(Float)
    average_cost = Column(Float)
    market_value = Column(Float)
    unrealized_pnl = Column(Float)
    realized_pnl = Column(Float)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class RiskMetrics(Base):
    """Risk metrics table"""
    __tablename__ = 'risk_metrics'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, index=True)
    var_95 = Column(Float)
    cvar_95 = Column(Float)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)
    beta = Column(Float)
    volatility = Column(Float)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class ModelPerformance(Base):
    """Model performance metrics table"""
    __tablename__ = 'model_performance'
    
    id = Column(Integer, primary_key=True)
    model_id = Column(String, index=True)
    model_type = Column(String, index=True)
    metrics = Column(JSON)
    training_time = Column(Float)
    inference_time = Column(Float)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

def init_databases(config: Dict) -> None:
    """Initialize all databases"""
    try:
        # Initialize PostgreSQL
        init_postgresql(config['database']['postgresql'])
        
        # Initialize MongoDB
        init_mongodb(config['database']['mongodb'])
        
        # Initialize Redis
        init_redis(config['database']['redis'])
        
        logging.info("Database initialization completed successfully")
        
    except Exception as e:
        logging.error(f"Database initialization failed: {str(e)}")
        raise

def init_postgresql(config: Dict) -> None:
    """Initialize PostgreSQL database"""
    try:
        # Create connection string
        connection_string = (
            f"postgresql://{config['user']}:{config['password']}@"
            f"{config['host']}:{config['port']}/{config['database']}"
        )
        
        # Create engine
        engine = create_engine(connection_string)
        
        # Create tables
        Base.metadata.create_all(engine)
        
        # Create indexes (in addition to SQLAlchemy's default indexes)
        create_postgresql_indexes(engine)
        
        logging.info("PostgreSQL initialization completed")
        
    except Exception as e:
        logging.error(f"PostgreSQL initialization failed: {str(e)}")
        raise

def create_postgresql_indexes(engine) -> None:
    """Create additional PostgreSQL indexes"""
    indexes = [
        # Market data indexes
        "CREATE INDEX IF NOT EXISTS idx_market_data_symbol_timestamp ON market_data (symbol, timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_market_data_timestamp_desc ON market_data (timestamp DESC)",
        
        # Trade indexes
        "CREATE INDEX IF NOT EXISTS idx_trades_symbol_time ON trades (symbol, execution_time)",
        "CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades (strategy_id, execution_time)",
        
        # Order indexes
        "CREATE INDEX IF NOT EXISTS idx_orders_status_time ON orders (status, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_orders_strategy_status ON orders (strategy_id, status)",
        
        # Position indexes
        "CREATE INDEX IF NOT EXISTS idx_positions_value ON positions (market_value)",
        
        # Risk metrics indexes
        "CREATE INDEX IF NOT EXISTS idx_risk_metrics_time ON risk_metrics (timestamp DESC)",
        
        # Model performance indexes
        "CREATE INDEX IF NOT EXISTS idx_model_perf_type_time ON model_performance (model_type, created_at)"
    ]
    
    with engine.connect() as conn:
        for index in indexes:
            conn.execute(index)

def init_mongodb(config: Dict) -> None:
    """Initialize MongoDB database"""
    try:
        # Create connection string
        connection_string = (
            f"mongodb://{config['user']}:{config['password']}@"
            f"{config['host']}:{config['port']}"
        )
        
        # Connect to MongoDB
        client = MongoClient(connection_string)
        db = client[config['database']]
        
        # Create collections
        collections = [
            'market_data_raw',  # Raw market data
            'order_book_snapshots',  # Order book snapshots
            'trade_flow',  # Detailed trade flow
            'sentiment_data',  # Market sentiment data
            'model_artifacts',  # Model artifacts and metadata
            'system_logs',  # System logs
            'analytics'  # Analytics results
        ]
        
        for collection in collections:
            if collection not in db.list_collection_names():
                db.create_collection(collection)
        
        # Create indexes
        create_mongodb_indexes(db)
        
        logging.info("MongoDB initialization completed")
        
    except Exception as e:
        logging.error(f"MongoDB initialization failed: {str(e)}")
        raise

def create_mongodb_indexes(db) -> None:
    """Create MongoDB indexes"""
    try:
        # Market data indexes
        db.market_data_raw.create_index([
            ('symbol', 1),
            ('timestamp', -1)
        ])
        
        # Order book indexes
        db.order_book_snapshots.create_index([
            ('symbol', 1),
            ('timestamp', -1)
        ])
        
        # Trade flow indexes
        db.trade_flow.create_index([
            ('symbol', 1),
            ('timestamp', -1)
        ])
        
        # Sentiment data indexes
        db.sentiment_data.create_index([
            ('symbol', 1),
            ('timestamp', -1)
        ])
        db.sentiment_data.create_index([
            ('source', 1),
            ('timestamp', -1)
        ])
        
        # Model artifacts indexes
        db.model_artifacts.create_index([
            ('model_id', 1),
            ('version', -1)
        ])
        
        # System logs indexes
        db.system_logs.create_index('timestamp', expireAfterSeconds=7*24*60*60)  # 7 days TTL
        
        # Analytics indexes
        db.analytics.create_index([
            ('type', 1),
            ('timestamp', -1)
        ])
        
    except Exception as e:
        logging.error(f"MongoDB index creation failed: {str(e)}")
        raise

def init_redis(config: Dict) -> None:
    """Initialize Redis database"""
    try:
        # Connect to Redis
        redis_client = redis.Redis(
            host=config['host'],
            port=config['port'],
            password=config.get('password'),
            db=0  # Use default database
        )
        
        # Test connection
        redis_client.ping()
        
        # Set up key spaces
        key_spaces = {
            'market_data_cache': {'ttl': 3600},  # 1 hour
            'order_cache': {'ttl': 86400},  # 24 hours
            'position_cache': {'ttl': 3600},  # 1 hour
            'model_cache': {'ttl': 3600},  # 1 hour
            'rate_limits': {'ttl': 60}  # 1 minute
        }
        
        # Initialize key spaces
        for space, config in key_spaces.items():
            redis_client.set(f"{space}:config", str(config['ttl']))
        
        logging.info("Redis initialization completed")
        
    except Exception as e:
        logging.error(f"Redis initialization failed: {str(e)}")
        raise

def load_config() -> Dict:
    """Load database configuration"""
    config_path = os.getenv('DB_CONFIG_PATH', 'config/database.yaml')
    
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logging.error(f"Failed to load configuration: {str(e)}")
        raise

def main():
    """Main initialization function"""
    try:
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Load configuration
        config = load_config()
        
        # Initialize databases
        init_databases(config)
        
        print("Database initialization completed successfully")
        return 0
        
    except Exception as e:
        print(f"Database initialization failed: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())

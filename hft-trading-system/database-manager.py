from typing import Optional, Any, Dict
from contextlib import contextmanager
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from psycopg2.extras import RealDictCursor
import threading
from datetime import datetime

class DatabaseManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    def __init__(self):
        self._pool: Optional[SimpleConnectionPool] = None
        self._config: Optional[Dict[str, Any]] = None
        self._is_initialized = False
        self._last_health_check = None
        self._health_check_interval = 300  # 5 minutes
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the database connection pool"""
        if self._is_initialized:
            return
            
        with self._lock:
            if self._is_initialized:  # Double-check pattern
                return
                
            self._config = config
            try:
                self._pool = SimpleConnectionPool(
                    minconn=config.get('min_connections', 1),
                    maxconn=config.get('max_connections', 10),
                    database=config['database'],
                    user=config['username'],
                    password=config['password'],
                    host=config['host'],
                    port=config['port'],
                    cursor_factory=RealDictCursor
                )
                self._is_initialized = True
                self._last_health_check = datetime.utcnow()
            except Exception as e:
                raise DatabaseError(f"Failed to initialize database pool: {str(e)}")
    
    @contextmanager
    def get_connection(self):
        """Get a database connection from the pool"""
        if not self._is_initialized:
            raise DatabaseError("Database manager not initialized")
            
        conn = None
        try:
            conn = self._pool.getconn()
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise DatabaseError(f"Database operation failed: {str(e)}")
        finally:
            if conn:
                self._pool.putconn(conn)
    
    @contextmanager
    def get_cursor(self):
        """Get a database cursor"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
            finally:
                cursor.close()
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> list:
        """Execute a query and return results"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchall()
    
    def execute_batch(self, query: str, params_list: list) -> None:
        """Execute a batch of queries"""
        with self.get_cursor() as cursor:
            cursor.executemany(query, params_list)
    
    def health_check(self) -> bool:
        """Check database connection health"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                is_healthy = result is not None and result[0] == 1
                self._last_health_check = datetime.utcnow()
                return is_healthy
        except Exception as e:
            return False
    
    def close(self) -> None:
        """Close all database connections"""
        if self._pool:
            self._pool.closeall()
            self._is_initialized = False

class DatabaseError(Exception):
    """Custom exception for database operations"""
    pass

class QueryBuilder:
    """Helper class for building SQL queries"""
    
    @staticmethod
    def build_select(
        table: str,
        columns: list,
        where: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None
    ) -> tuple:
        """Build a SELECT query"""
        query = f"SELECT {', '.join(columns)} FROM {table}"
        params = []
        
        if where:
            conditions = []
            for key, value in where.items():
                conditions.append(f"{key} = %s")
                params.append(value)
            query += " WHERE " + " AND ".join(conditions)
        
        if order_by:
            query += f" ORDER BY {order_by}"
            
        if limit:
            query += f" LIMIT {limit}"
            
        return query, tuple(params)
    
    @staticmethod
    def build_insert(table: str, data: Dict[str, Any]) -> tuple:
        """Build an INSERT query"""
        columns = list(data.keys())
        values = list(data.values())
        placeholders = ["%s"] * len(values)
        
        query = f"""
            INSERT INTO {table} ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            RETURNING id
        """
        
        return query, tuple(values)
    
    @staticmethod
    def build_update(
        table: str,
        data: Dict[str, Any],
        where: Dict[str, Any]
    ) -> tuple:
        """Build an UPDATE query"""
        set_values = [f"{key} = %s" for key in data.keys()]
        where_conditions = [f"{key} = %s" for key in where.keys()]
        
        query = f"""
            UPDATE {table}
            SET {', '.join(set_values)}
            WHERE {' AND '.join(where_conditions)}
        """
        
        params = tuple(list(data.values()) + list(where.values()))
        return query, params

class DatabaseMigration:
    """Handle database migrations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        
    def create_tables(self) -> None:
        """Create all necessary tables"""
        migrations = [
            self._create_trades_table,
            self._create_positions_table,
            self._create_market_data_table,
            self._create_audit_log_table
        ]
        
        for migration in migrations:
            migration()
    
    def _create_trades_table(self) -> None:
        """Create trades table"""
        query = """
        CREATE TABLE IF NOT EXISTS trades (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            quantity DECIMAL NOT NULL,
            price DECIMAL NOT NULL,
            side VARCHAR(4) NOT NULL,
            order_type VARCHAR(10) NOT NULL,
            status VARCHAR(10) NOT NULL,
            order_id VARCHAR(50),
            timestamp TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        with self.db_manager.get_cursor() as cursor:
            cursor.execute(query)
    
    def _create_positions_table(self) -> None:
        """Create positions table"""
        query = """
        CREATE TABLE IF NOT EXISTS positions (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            quantity DECIMAL NOT NULL,
            average_price DECIMAL NOT NULL,
            current_price DECIMAL NOT NULL,
            unrealized_pnl DECIMAL NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol)
        )
        """
        with self.db_manager.get_cursor() as cursor:
            cursor.execute(query)
    
    def _create_market_data_table(self) -> None:
        """Create market data table"""
        query = """
        CREATE TABLE IF NOT EXISTS market_data (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            price DECIMAL NOT NULL,
            volume DECIMAL NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        with self.db_manager.get_cursor() as cursor:
            cursor.execute(query)
    
    def _create_audit_log_table(self) -> None:
        """Create audit log table"""
        query = """
        CREATE TABLE IF NOT EXISTS audit_log (
            id SERIAL PRIMARY KEY,
            event_type VARCHAR(50) NOT NULL,
            description TEXT NOT NULL,
            data JSONB,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        with self.db_manager.get_cursor() as cursor:
            cursor.execute(query)

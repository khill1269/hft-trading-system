from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
import websockets
import asyncio
import json
from decimal import Decimal
import threading
from dataclasses import dataclass
from collections import deque

@dataclass
class MarketTick:
    """Represents a single market data tick"""
    symbol: str
    price: Decimal
    volume: Decimal
    timestamp: datetime
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    trade_id: Optional[str] = None

class MarketDataBuffer:
    """Buffer for temporary storage of market data"""
    
    def __init__(self, max_size: int = 1000):
        self._data: Dict[str, deque] = {}
        self._max_size = max_size
        self._lock = threading.Lock()
    
    def add_tick(self, tick: MarketTick) -> None:
        """Add a new tick to the buffer"""
        with self._lock:
            if tick.symbol not in self._data:
                self._data[tick.symbol] = deque(maxlen=self._max_size)
            self._data[tick.symbol].append(tick)
    
    def get_latest_price(self, symbol: str) -> Optional[Decimal]:
        """Get the latest price for a symbol"""
        with self._lock:
            if symbol in self._data and self._data[symbol]:
                return self._data[symbol][-1].price
        return None
    
    def get_ticks(self, symbol: str, count: int = 100) -> List[MarketTick]:
        """Get recent ticks for a symbol"""
        with self._lock:
            if symbol not in self._data:
                return []
            return list(self._data[symbol])[-count:]

class MarketDataManager:
    """Manages market data operations including real-time and historical data"""
    
    def __init__(
        self,
        db_manager,
        config: Dict[str, Any],
        logger,
        error_handler
    ):
        self.db_manager = db_manager
        self.config = config
        self.logger = logger
        self.error_handler = error_handler
        
        self.buffer = MarketDataBuffer()
        self.websocket = None
        self.running = False
        self._symbols: Set[str] = set()
        self._lock = threading.Lock()
        
        # Callbacks for price updates
        self._price_callbacks: List[callable] = []
        
        # Circuit breaker for data quality
        self.circuit_breaker = CircuitBreaker(
            name="market_data",
            failure_threshold=5,
            reset_timeout=30,
            logger=logger
        )
    
    async def start(self, symbols: List[str]) -> None:
        """Start market data collection"""
        self._symbols = set(symbols)
        self.running = True
        
        # Start WebSocket connection in a separate task
        asyncio.create_task(self._maintain_websocket_connection())
        
        # Start database writer in a separate thread
        self._start_database_writer()
        
        self.logger.log_event(
            "MARKET_DATA_START",
            f"Started market data collection for symbols: {symbols}"
        )
    
    async def stop(self) -> None:
        """Stop market data collection"""
        self.running = False
        if self.websocket:
            await self.websocket.close()
        self.logger.log_event("MARKET_DATA_STOP", "Stopped market data collection")
    
    def register_price_callback(self, callback: callable) -> None:
        """Register a callback for price updates"""
        self._price_callbacks.append(callback)
    
    async def _maintain_websocket_connection(self) -> None:
        """Maintain WebSocket connection with retry logic"""
        while self.running:
            try:
                uri = self.config['websocket_uri']
                async with websockets.connect(uri) as websocket:
                    self.websocket = websocket
                    
                    # Subscribe to market data
                    await self._subscribe_to_market_data()
                    
                    # Process incoming messages
                    while self.running:
                        message = await websocket.recv()
                        await self._process_market_data(message)
                        
            except Exception as e:
                self.error_handler.handle_error(
                    MarketDataError(f"WebSocket error: {str(e)}")
                )
                await asyncio.sleep(5)  # Wait before retry
    
    async def _subscribe_to_market_data(self) -> None:
        """Subscribe to market data for configured symbols"""
        if not self.websocket:
            return
            
        subscribe_message = {
            "type": "subscribe",
            "symbols": list(self._symbols)
        }
        await self.websocket.send(json.dumps(subscribe_message))
    
    async def _process_market_data(self, message: str) -> None:
        """Process incoming market data"""
        try:
            data = json.loads(message)
            
            tick = MarketTick(
                symbol=data['symbol'],
                price=Decimal(str(data['price'])),
                volume=Decimal(str(data['volume'])),
                timestamp=datetime.fromtimestamp(data['timestamp']),
                bid=Decimal(str(data['bid'])) if 'bid' in data else None,
                ask=Decimal(str(data['ask'])) if 'ask' in data else None,
                trade_id=data.get('trade_id')
            )
            
            # Validate data
            if not self._validate_tick(tick):
                return
                
            # Add to buffer
            self.buffer.add_tick(tick)
            
            # Notify callbacks
            for callback in self._price_callbacks:
                try:
                    callback(tick)
                except Exception as e:
                    self.logger.log_error(e, "Price callback error")
                    
        except Exception as e:
            self.error_handler.handle_error(
                MarketDataError(f"Error processing market data: {str(e)}")
            )
    
    def _validate_tick(self, tick: MarketTick) -> bool:
        """Validate market data tick"""
        try:
            return self.circuit_breaker.execute(self._do_validate_tick, tick)
        except CircuitBreakerError:
            return False
    
    def _do_validate_tick(self, tick: MarketTick) -> bool:
        """Perform actual tick validation"""
        # Check timestamp is reasonable
        if tick.timestamp > datetime.utcnow() + timedelta(seconds=5):
            raise MarketDataError("Future timestamp detected")
            
        # Check price is positive
        if tick.price <= 0:
            raise MarketDataError("Invalid price")
            
        # Check volume is positive
        if tick.volume < 0:
            raise MarketDataError("Invalid volume")
            
        # Check bid/ask relationship if both are present
        if tick.bid is not None and tick.ask is not None:
            if tick.bid >= tick.ask:
                raise MarketDataError("Invalid bid/ask relationship")
        
        return True
    
    def _start_database_writer(self) -> None:
        """Start background thread for writing to database"""
        def writer_thread():
            while self.running:
                try:
                    self._write_buffer_to_database()
                except Exception as e:
                    self.error_handler.handle_error(
                        MarketDataError(f"Database writer error: {str(e)}")
                    )
                time.sleep(self.config.get('db_write_interval', 1))
        
        thread = threading.Thread(target=writer_thread, daemon=True)
        thread.start()
    
    def _write_buffer_to_database(self) -> None:
        """Write buffered data to database"""
        for symbol in self._symbols:
            ticks = self.buffer.get_ticks(symbol)
            if not ticks:
                continue
                
            # Prepare batch insert
            values = [(
                tick.symbol,
                float(tick.price),
                float(tick.volume),
                tick.timestamp
            ) for tick in ticks]
            
            query = """
                INSERT INTO market_data (symbol, price, volume, timestamp)
                VALUES (%s, %s, %s, %s)
            """
            
            self.db_manager.execute_batch(query, values)
    
    def get_historical_data(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[MarketTick]:
        """Get historical market data"""
        query = """
            SELECT symbol, price, volume, timestamp
            FROM market_data
            WHERE symbol = %s
            AND timestamp BETWEEN %s AND %s
            ORDER BY timestamp ASC
        """
        
        results = self.db_manager.execute_query(
            query,
            (symbol, start_time, end_time)
        )
        
        return [
            MarketTick(
                symbol=row['symbol'],
                price=Decimal(str(row['price'])),
                volume=Decimal(str(row['volume'])),
                timestamp=row['timestamp']
            )
            for row in results
        ]

class MarketDataError(Exception):
    """Custom exception for market data operations"""
    pass

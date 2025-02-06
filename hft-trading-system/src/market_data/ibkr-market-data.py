from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from decimal import Decimal
import threading
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.common import TickerId, BarData
from ibapi.ticktype import TickType
import queue
import pandas as pd

class IBKRMarketDataWrapper(EWrapper):
    """Custom wrapper for IBKR market data handling"""
    
    def __init__(self):
        EWrapper.__init__(self)
        self.data_queue = queue.Queue()
        self.contract_details = {}
        self._req_id_to_symbol = {}
        self.errors = queue.Queue()
        
    def error(self, req_id: TickerId, error_code: int, error_string: str):
        """Handle error messages"""
        self.errors.put({
            'req_id': req_id,
            'code': error_code,
            'message': error_string
        })
    
    def tickPrice(
        self,
        req_id: TickerId,
        tick_type: TickType,
        price: float,
        attrib: dict
    ):
        """Handle price updates"""
        if price <= 0:
            return
            
        symbol = self._req_id_to_symbol.get(req_id)
        if not symbol:
            return
            
        data = {
            'symbol': symbol,
            'type': tick_type,
            'price': Decimal(str(price)),
            'timestamp': datetime.utcnow()
        }
        self.data_queue.put(data)
    
    def tickSize(
        self,
        req_id: TickerId,
        tick_type: TickType,
        size: int
    ):
        """Handle size updates"""
        symbol = self._req_id_to_symbol.get(req_id)
        if not symbol:
            return
            
        data = {
            'symbol': symbol,
            'type': tick_type,
            'size': size,
            'timestamp': datetime.utcnow()
        }
        self.data_queue.put(data)
    
    def historicalData(
        self,
        req_id: int,
        bar: BarData
    ):
        """Handle historical data"""
        symbol = self._req_id_to_symbol.get(req_id)
        if not symbol:
            return
            
        data = {
            'symbol': symbol,
            'timestamp': datetime.strptime(bar.date, '%Y%m%d %H:%M:%S'),
            'open': Decimal(str(bar.open)),
            'high': Decimal(str(bar.high)),
            'low': Decimal(str(bar.low)),
            'close': Decimal(str(bar.close)),
            'volume': bar.volume
        }
        self.data_queue.put(data)

class IBKRMarketDataClient(EClient):
    """Custom client for IBKR market data"""
    
    def __init__(self, wrapper):
        EClient.__init__(self, wrapper)
        self._req_id = 0
        self._lock = threading.Lock()
    
    def get_next_req_id(self) -> int:
        """Get next request ID"""
        with self._lock:
            self._req_id += 1
            return self._req_id
    
    def create_contract(
        self,
        symbol: str,
        sec_type: str = 'STK',
        exchange: str = 'SMART',
        currency: str = 'USD'
    ) -> Contract:
        """Create IBKR contract object"""
        contract = Contract()
        contract.symbol = symbol
        contract.secType = sec_type
        contract.exchange = exchange
        contract.currency = currency
        return contract

class IBKRMarketDataManager:
    """Market data manager for IBKR integration"""
    
    def __init__(
        self,
        config: Dict,
        logger,
        error_handler
    ):
        self.config = config
        self.logger = logger
        self.error_handler = error_handler
        
        # Initialize IBKR components
        self.wrapper = IBKRMarketDataWrapper()
        self.client = IBKRMarketDataClient(self.wrapper)
        
        # Data management
        self._subscribed_symbols: Set[str] = set()
        self._last_prices: Dict[str, Decimal] = {}
        self._callbacks: Dict[str, List[Callable]] = {}
        self._historical_data: Dict[str, pd.DataFrame] = {}
        
        # Connection management
        self._is_connected = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = config.get('max_reconnect_attempts', 5)
        
        # Start connection
        self._connect()
        
        # Start data processing
        self._start_data_processing()
    
    def _connect(self) -> None:
        """Connect to IBKR TWS"""
        try:
            host = self.config.get('tws_host', '127.0.0.1')
            port = self.config.get('tws_port', 7497)
            client_id = self.config.get('client_id', 1)
            
            self.client.connect(host, port, client_id)
            
            # Start client thread
            thread = threading.Thread(target=self.client.run)
            thread.daemon = True
            thread.start()
            
            self._is_connected = True
            self.logger.log_event(
                "IBKR_CONNECTION",
                "Connected to TWS"
            )
            
        except Exception as e:
            self.error_handler.handle_error(
                MarketDataError(f"Failed to connect to TWS: {str(e)}")
            )
            self._handle_connection_error()
    
    def _handle_connection_error(self) -> None:
        """Handle connection errors"""
        self._is_connected = False
        self._reconnect_attempts += 1
        
        if self._reconnect_attempts < self._max_reconnect_attempts:
            self.logger.log_event(
                "IBKR_RECONNECT",
                f"Attempting reconnection {self._reconnect_attempts}"
            )
            time.sleep(5)  # Wait before retry
            self._connect()
        else:
            self.error_handler.handle_error(
                MarketDataError("Max reconnection attempts reached")
            )
    
    def _start_data_processing(self) -> None:
        """Start data processing thread"""
        def process_data():
            while True:
                try:
                    # Process market data
                    while not self.wrapper.data_queue.empty():
                        data = self.wrapper.data_queue.get()
                        self._process_market_data(data)
                    
                    # Process errors
                    while not self.wrapper.errors.empty():
                        error = self.wrapper.errors.get()
                        self._handle_error(error)
                        
                except Exception as e:
                    self.error_handler.handle_error(
                        MarketDataError(f"Data processing error: {str(e)}")
                    )
                
                time.sleep(0.1)
        
        thread = threading.Thread(target=process_data, daemon=True)
        thread.start()
    
    def subscribe_market_data(
        self,
        symbol: str,
        callback: Optional[Callable] = None
    ) -> bool:
        """Subscribe to market data for symbol"""
        try:
            if not self._is_connected:
                raise MarketDataError("Not connected to TWS")
            
            if symbol in self._subscribed_symbols:
                if callback:
                    self._callbacks.setdefault(symbol, []).append(callback)
                return True
            
            # Create contract
            contract = self.client.create_contract(symbol)
            
            # Request market data
            req_id = self.client.get_next_req_id()
            self.wrapper._req_id_to_symbol[req_id] = symbol
            
            self.client.reqMktData(
                req_id,
                contract,
                "",  # genericTickList
                False,  # snapshot
                False,  # regulatorySnapshot
                []  # mktDataOptions
            )
            
            self._subscribed_symbols.add(symbol)
            if callback:
                self._callbacks.setdefault(symbol, []).append(callback)
            
            self.logger.log_event(
                "MARKET_DATA_SUBSCRIPTION",
                f"Subscribed to {symbol}"
            )
            return True
            
        except Exception as e:
            self.error_handler.handle_error(
                MarketDataError(f"Subscription failed for {symbol}: {str(e)}")
            )
            return False
    
    def unsubscribe_market_data(self, symbol: str) -> None:
        """Unsubscribe from market data"""
        try:
            if symbol not in self._subscribed_symbols:
                return
            
            # Find request ID for symbol
            req_id = None
            for rid, sym in self.wrapper._req_id_to_symbol.items():
                if sym == symbol:
                    req_id = rid
                    break
            
            if req_id is not None:
                self.client.cancelMktData(req_id)
                del self.wrapper._req_id_to_symbol[req_id]
            
            self._subscribed_symbols.remove(symbol)
            self._callbacks.pop(symbol, None)
            
            self.logger.log_event(
                "MARKET_DATA_UNSUBSCRIPTION",
                f"Unsubscribed from {symbol}"
            )
            
        except Exception as e:
            self.error_handler.handle_error(
                MarketDataError(f"Unsubscription failed for {symbol}: {str(e)}")
            )
    
    async def get_historical_data(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        bar_size: str = '1 min'
    ) -> Optional[pd.DataFrame]:
        """Get historical market data"""
        try:
            if not self._is_connected:
                raise MarketDataError("Not connected to TWS")
            
            # Create contract
            contract = self.client.create_contract(symbol)
            
            # Request historical data
            req_id = self.client.get_next_req_id()
            self.wrapper._req_id_to_symbol[req_id] = symbol
            
            self.client.reqHistoricalData(
                req_id,
                contract,
                end_time.strftime('%Y%m%d %H:%M:%S'),
                f"{(end_time - start_time).days} D",
                bar_size,
                "TRADES",
                1,  # useRTH
                1,  # formatDate
                False,  # keepUpToDate
                []  # chartOptions
            )
            
            # Wait for and process data
            timeout = time.time() + 30  # 30 second timeout
            data = []
            
            while time.time() < timeout:
                try:
                    bar_data = self.wrapper.data_queue.get(timeout=1)
                    if bar_data['symbol'] == symbol:
                        data.append(bar_data)
                except queue.Empty:
                    continue
            
            if not data:
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            self.error_handler.handle_error(
                MarketDataError(f"Historical data request failed: {str(e)}")
            )
            return None
    
    def get_latest_price(self, symbol: str) -> Optional[Decimal]:
        """Get latest price for symbol"""
        return self._last_prices.get(symbol)
    
    def _process_market_data(self, data: Dict) -> None:
        """Process incoming market data"""
        try:
            symbol = data['symbol']
            
            # Update last price if available
            if 'price' in data:
                self._last_prices[symbol] = data['price']
            
            # Notify callbacks
            if symbol in self._callbacks:
                for callback in self._callbacks[symbol]:
                    try:
                        callback(data)
                    except Exception as e:
                        self.error_handler.handle_error(
                            MarketDataError(f"Callback error: {str(e)}")
                        )
                        
        except Exception as e:
            self.error_handler.handle_error(
                MarketDataError(f"Data processing error: {str(e)}")
            )
    
    def _handle_error(self, error: Dict) -> None:
        """Handle IBKR API errors"""
        error_code = error['code']
        message = error['message']
        
        # Connection-related errors
        if error_code in [1100, 1101, 1102]:
            self._is_connected = False
            self._handle_connection_error()
        
        # Market data errors
        elif error_code in [200, 201, 202, 203]:
            symbol = self.wrapper._req_id_to_symbol.get(error['req_id'])
            if symbol:
                self.unsubscribe_market_data(symbol)
        
        self.error_handler.handle_error(
            MarketDataError(f"IBKR Error {error_code}: {message}")
        )

class MarketDataError(Exception):
    """Custom exception for market data errors"""
    pass

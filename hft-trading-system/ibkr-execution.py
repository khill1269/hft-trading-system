from typing import Dict, List, Optional, Union, Tuple
from decimal import Decimal
from datetime import datetime
import threading
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.common import OrderId
from ibapi.execution import Execution
from ibapi.commission_report import CommissionReport
import queue
from enum import Enum

class OrderStatus(Enum):
    PENDING = "Pending"
    SUBMITTED = "Submitted"
    FILLED = "Filled"
    CANCELLED = "Cancelled"
    REJECTED = "Rejected"
    PARTIAL = "PartiallyFilled"

class IBKRExecutionWrapper(EWrapper):
    """Custom wrapper for IBKR execution handling"""
    
    def __init__(self):
        EWrapper.__init__(self)
        self.order_queue = queue.Queue()
        self.execution_queue = queue.Queue()
        self.errors = queue.Queue()
        self._order_status = {}
        self._executions = {}
        self._commissions = {}
        
    def error(self, req_id: int, error_code: int, error_string: str):
        """Handle error messages"""
        self.errors.put({
            'req_id': req_id,
            'code': error_code,
            'message': error_string
        })
    
    def orderStatus(
        self,
        orderId: OrderId,
        status: str,
        filled: float,
        remaining: float,
        avgFillPrice: float,
        permId: int,
        parentId: int,
        lastFillPrice: float,
        clientId: int,
        whyHeld: str,
        mktCapPrice: float
    ):
        """Handle order status updates"""
        self._order_status[orderId] = {
            'status': status,
            'filled': filled,
            'remaining': remaining,
            'avgFillPrice': avgFillPrice,
            'lastFillPrice': lastFillPrice,
            'whyHeld': whyHeld
        }
        
        self.order_queue.put({
            'order_id': orderId,
            'type': 'STATUS',
            'data': self._order_status[orderId]
        })
    
    def execDetails(
        self,
        reqId: int,
        contract: Contract,
        execution: Execution
    ):
        """Handle execution details"""
        exec_id = execution.execId
        self._executions[exec_id] = {
            'order_id': execution.orderId,
            'time': execution.time,
            'side': execution.side,
            'shares': execution.shares,
            'price': execution.price,
            'commission': None  # Will be updated with commission report
        }
        
        self.execution_queue.put({
            'exec_id': exec_id,
            'type': 'EXECUTION',
            'data': self._executions[exec_id]
        })
    
    def commissionReport(self, commission_report: CommissionReport):
        """Handle commission reports"""
        exec_id = commission_report.execId
        if exec_id in self._executions:
            self._executions[exec_id]['commission'] = commission_report.commission
            
            self.execution_queue.put({
                'exec_id': exec_id,
                'type': 'COMMISSION',
                'data': {'commission': commission_report.commission}
            })

class IBKRExecutionClient(EClient):
    """Custom client for IBKR execution"""
    
    def __init__(self, wrapper):
        EClient.__init__(self, wrapper)
        self._next_order_id = None
        self._lock = threading.Lock()
    
    def nextValidId(self, orderId: int):
        """Handle next valid order ID"""
        super().nextValidId(orderId)
        self._next_order_id = orderId
    
    def get_next_order_id(self) -> Optional[int]:
        """Get next valid order ID"""
        with self._lock:
            if self._next_order_id is None:
                return None
            order_id = self._next_order_id
            self._next_order_id += 1
            return order_id

class IBKRTradeExecutor:
    """Trade execution manager for IBKR"""
    
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
        self.wrapper = IBKRExecutionWrapper()
        self.client = IBKRExecutionClient(self.wrapper)
        
        # Order management
        self._orders: Dict[int, Dict] = {}
        self._order_callbacks: Dict[int, List[callable]] = {}
        self._execution_callbacks: Dict[str, List[callable]] = {}
        
        # Status tracking
        self._is_connected = False
        self._reconnect_attempts = 0
        
        # Start connection
        self._connect()
        
        # Start order processing
        self._start_order_processing()
    
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
                "Connected to TWS for execution"
            )
            
        except Exception as e:
            self.error_handler.handle_error(
                ExecutionError(f"Failed to connect to TWS: {str(e)}")
            )
            self._handle_connection_error()
    
    def _start_order_processing(self) -> None:
        """Start order processing thread"""
        def process_orders():
            while True:
                try:
                    # Process order updates
                    while not self.wrapper.order_queue.empty():
                        update = self.wrapper.order_queue.get()
                        self._process_order_update(update)
                    
                    # Process executions
                    while not self.wrapper.execution_queue.empty():
                        execution = self.wrapper.execution_queue.get()
                        self._process_execution(execution)
                    
                    # Process errors
                    while not self.wrapper.errors.empty():
                        error = self.wrapper.errors.get()
                        self._handle_error(error)
                        
                except Exception as e:
                    self.error_handler.handle_error(
                        ExecutionError(f"Order processing error: {str(e)}")
                    )
                
                time.sleep(0.1)
        
        thread = threading.Thread(target=process_orders, daemon=True)
        thread.start()
    
    async def submit_order(
        self,
        symbol: str,
        side: str,
        quantity: Union[int, float],
        order_type: str = "MKT",
        price: Optional[float] = None,
        tif: str = "DAY",
        **kwargs
    ) -> Optional[int]:
        """Submit order to IBKR"""
        try:
            if not self._is_connected:
                raise ExecutionError("Not connected to TWS")
            
            # Get next order ID
            order_id = self.client.get_next_order_id()
            if order_id is None:
                raise ExecutionError("Failed to get order ID")
            
            # Create contract
            contract = Contract()
            contract.symbol = symbol
            contract.secType = "STK"
            contract.exchange = "SMART"
            contract.currency = "USD"
            
            # Create order
            order = Order()
            order.action = side.upper()
            order.totalQuantity = quantity
            order.orderType = order_type
            order.tif = tif
            
            if price is not None:
                order.lmtPrice = price
            
            # Add additional parameters
            for key, value in kwargs.items():
                setattr(order, key, value)
            
            # Store order details
            self._orders[order_id] = {
                'contract': contract,
                'order': order,
                'status': OrderStatus.PENDING,
                'filled_quantity': 0,
                'average_price': None,
                'executions': []
            }
            
            # Submit order
            self.client.placeOrder(order_id, contract, order)
            
            self.logger.log_event(
                "ORDER_SUBMITTED",
                f"Submitted order {order_id}",
                extra_data={
                    'symbol': symbol,
                    'side': side,
                    'quantity': quantity,
                    'type': order_type
                }
            )
            
            return order_id
            
        except Exception as e:
            self.error_handler.handle_error(
                ExecutionError(f"Order submission failed: {str(e)}")
            )
            return None
    
    async def cancel_order(self, order_id: int) -> bool:
        """Cancel order"""
        try:
            if order_id not in self._orders:
                raise ExecutionError(f"Order {order_id} not found")
            
            order_data = self._orders[order_id]
            if order_data['status'] in [
                OrderStatus.FILLED,
                OrderStatus.CANCELLED,
                OrderStatus.REJECTED
            ]:
                return False
            
            self.client.cancelOrder(order_id)
            
            self.logger.log_event(
                "ORDER_CANCELLED",
                f"Cancelled order {order_id}"
            )
            
            return True
            
        except Exception as e:
            self.error_handler.handle_error(
                ExecutionError(f"Order cancellation failed: {str(e)}")
            )
            return False
    
    def get_order_status(self, order_id: int) -> Optional[Dict]:
        """Get current order status"""
        return self._orders.get(order_id)
    
    def register_order_callback(
        self,
        order_id: int,
        callback: callable
    ) -> None:
        """Register callback for order updates"""
        if order_id not in self._order_callbacks:
            self._order_callbacks[order_id] = []
        self._order_callbacks[order_id].append(callback)
    
    def register_execution_callback(
        self,
        symbol: str,
        callback: callable
    ) -> None:
        """Register callback for executions"""
        if symbol not in self._execution_callbacks:
            self._execution_callbacks[symbol] = []
        self._execution_callbacks[symbol].append(callback)
    
    def _process_order_update(self, update: Dict) -> None:
        """Process order status update"""
        order_id = update['order_id']
        if order_id not in self._orders:
            return
        
        order_data = self._orders[order_id]
        status_data = update['data']
        
        # Update order status
        order_data['status'] = OrderStatus(status_data['status'])
        order_data['filled_quantity'] = status_data['filled']
        order_data['average_price'] = status_data['avgFillPrice']
        
        # Notify callbacks
        if order_id in self._order_callbacks:
            for callback in self._order_callbacks[order_id]:
                try:
                    callback(order_data)
                except Exception as e:
                    self.error_handler.handle_error(
                        ExecutionError(f"Callback error: {str(e)}")
                    )
    
    def _process_execution(self, execution: Dict) -> None:
        """Process execution update"""
        exec_id = execution['exec_id']
        data = execution['data']
        order_id = data['order_id']
        
        if order_id not in self._orders:
            return
        
        order_data = self._orders[order_id]
        
        # Update executions
        if execution['type'] == 'EXECUTION':
            order_data['executions'].append(data)
        elif execution['type'] == 'COMMISSION':
            # Update last execution with commission
            if order_data['executions']:
                order_data['executions'][-1].update(data)
        
        # Notify callbacks
        symbol = order_data['contract'].symbol
        if symbol in self._execution_callbacks:
            for callback in self._execution_callbacks[symbol]:
                try:
                    callback(data)
                except Exception as e:
                    self.error_handler.handle_error(
                        ExecutionError(f"Callback error: {str(e)}")
                    )
    
    def _handle_error(self, error: Dict) -> None:
        """Handle IBKR API errors"""
        error_code = error['code']
        message = error['message']
        
        # Connection-related errors
        if error_code in [1100, 1101, 1102]:
            self._is_connected = False
            self._handle_connection_error()
        
        # Order errors
        elif error_code in [201, 202, 203]:
            order_id = error.get('req_id')
            if order_id in self._orders:
                self._orders[order_id]['status'] = OrderStatus.REJECTED
        
        self.error_handler.handle_error(
            ExecutionError(f"IBKR Error {error_code}: {message}")
        )
    
    def _handle_connection_error(self) -> None:
        """Handle connection errors"""
        self._is_connected = False
        self._reconnect_attempts += 1
        
        if self._reconnect_attempts < self.config.get('max_reconnect_attempts', 5):
            self.logger.log_event(
                "IBKR_RECONNECT",
                f"Attempting reconnection {self._reconnect_attempts}"
            )
            time.sleep(5)  # Wait before retry
            self._connect()
        else:
            self.error_handler.handle_error(
                ExecutionError("Max reconnection attempts reached")
            )

class ExecutionError(Exception):
    """Custom exception for execution errors"""
    pass

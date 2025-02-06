from typing import Dict, Optional, List, Callable
from decimal import Decimal
from datetime import datetime
from enum import Enum
import uuid
import asyncio
from dataclasses import dataclass
import threading

class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"

class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"

@dataclass
class OrderRequest:
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    time_in_force: str = "DAY"
    client_order_id: Optional[str] = None

@dataclass
class Order:
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Optional[Decimal]
    stop_price: Optional[Decimal]
    status: OrderStatus
    filled_quantity: Decimal = Decimal('0')
    average_fill_price: Optional[Decimal] = None
    client_order_id: Optional[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    time_in_force: str = "DAY"
    error_message: Optional[str] = None

class TradeExecutionEngine:
    """Main trade execution engine"""
    
    def __init__(
        self,
        db_manager,
        market_data_manager,
        config: Dict,
        logger,
        error_handler
    ):
        self.db_manager = db_manager
        self.market_data_manager = market_data_manager
        self.config = config
        self.logger = logger
        self.error_handler = error_handler
        
        # Order management
        self._orders: Dict[str, Order] = {}
        self._order_callbacks: Dict[str, List[Callable]] = {}
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Circuit breaker for execution
        self.circuit_breaker = CircuitBreaker(
            name="trade_execution",
            failure_threshold=3,
            reset_timeout=60,
            logger=logger
        )
        
        # Initialize order book
        self._order_book = OrderBook()
        
        # Start order status monitor
        self._start_order_monitor()
    
    async def submit_order(self, request: OrderRequest) -> Order:
        """Submit a new order"""
        try:
            return await self.circuit_breaker.execute(self._do_submit_order, request)
        except Exception as e:
            self.error_handler.handle_error(
                TradeExecutionError(f"Order submission failed: {str(e)}")
            )
            raise
    
    async def _do_submit_order(self, request: OrderRequest) -> Order:
        """Internal order submission logic"""
        # Validate order
        self._validate_order_request(request)
        
        # Create order object
        order = Order(
            order_id=str(uuid.uuid4()),
            symbol=request.symbol,
            side=request.side,
            order_type=request.order_type,
            quantity=request.quantity,
            price=request.price,
            stop_price=request.stop_price,
            status=OrderStatus.PENDING,
            client_order_id=request.client_order_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            time_in_force=request.time_in_force
        )
        
        # Store order
        with self._lock:
            self._orders[order.order_id] = order
        
        # Log order creation
        self.logger.log_event(
            "ORDER_CREATED",
            f"Order created: {order.order_id}",
            extra_data={
                "symbol": order.symbol,
                "side": order.side.value,
                "quantity": str(order.quantity)
            }
        )
        
        # Submit to execution
        await self._execute_order(order)
        
        return order
    
    def _validate_order_request(self, request: OrderRequest) -> None:
        """Validate order request"""
        # Check symbol
        if not self.market_data_manager.get_latest_price(request.symbol):
            raise ValidationError("Invalid symbol")
        
        # Check quantity
        if request.quantity <= 0:
            raise ValidationError("Invalid quantity")
        
        # Check price for limit orders
        if request.order_type == OrderType.LIMIT and not request.price:
            raise ValidationError("Limit order requires price")
        
        # Check stop price for stop orders
        if request.order_type in {OrderType.STOP, OrderType.STOP_LIMIT} and not request.stop_price:
            raise ValidationError("Stop order requires stop price")
    
    async def _execute_order(self, order: Order) -> None:
        """Execute the order based on type"""
        try:
            if order.order_type == OrderType.MARKET:
                await self._execute_market_order(order)
            elif order.order_type == OrderType.LIMIT:
                await self._execute_limit_order(order)
            elif order.order_type in {OrderType.STOP, OrderType.STOP_LIMIT}:
                await self._execute_stop_order(order)
        except Exception as e:
            self._handle_execution_error(order, str(e))
    
    async def _execute_market_order(self, order: Order) -> None:
        """Execute a market order"""
        current_price = self.market_data_manager.get_latest_price(order.symbol)
        if not current_price:
            self._handle_execution_error(order, "Unable to get current price")
            return
        
        # Simulate market impact and slippage
        executed_price = self._calculate_execution_price(
            current_price,
            order.quantity,
            order.side
        )
        
        # Execute the order
        await self._process_execution(order, executed_price)
    
    async def _execute_limit_order(self, order: Order) -> None:
        """Execute a limit order"""
        current_price = self.market_data_manager.get_latest_price(order.symbol)
        if not current_price:
            self._handle_execution_error(order, "Unable to get current price")
            return
        
        # Check if limit price is favorable
        if self._is_limit_price_favorable(current_price, order):
            executed_price = order.price
            await self._process_execution(order, executed_price)
        else:
            # Add to order book for later execution
            self._order_book.add_order(order)
            self._update_order_status(order, OrderStatus.SUBMITTED)
    
    async def _execute_stop_order(self, order: Order) -> None:
        """Execute a stop order"""
        current_price = self.market_data_manager.get_latest_price(order.symbol)
        if not current_price:
            self._handle_execution_error(order, "Unable to get current price")
            return
        
        # Check if stop price is triggered
        if self._is_stop_triggered(current_price, order):
            if order.order_type == OrderType.STOP:
                # Convert to market order
                await self._execute_market_order(order)
            else:
                # Convert to limit order
                await self._execute_limit_order(order)
        else:
            # Add to order book for monitoring
            self._order_book.add_order(order)
            self._update_order_status(order, OrderStatus.SUBMITTED)
    
    async def _process_execution(self, order: Order, executed_price: Decimal) -> None:
        """Process order execution"""
        try:
            # Update order status
            order.filled_quantity = order.quantity
            order.average_fill_price = executed_price
            self._update_order_status(order, OrderStatus.FILLED)
            
            # Record execution in database
            await self._record_execution(order)
            
            # Notify callbacks
            self._notify_order_update(order)
            
        except Exception as e:
            self._handle_execution_error(order, str(e))
    
    async def _record_execution(self, order: Order) -> None:
        """Record order execution in database"""
        query = """
            INSERT INTO executions (
                order_id, symbol, side, quantity, price,
                execution_time, client_order_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        values = (
            order.order_id,
            order.symbol,
            order.side.value,
            float(order.filled_quantity),
            float(order.average_fill_price),
            datetime.utcnow(),
            order.client_order_id
        )
        
        await self.db_manager.execute(query, values)
    
    def _update_order_status(self, order: Order, status: OrderStatus) -> None:
        """Update order status"""
        with self._lock:
            order.status = status
            order.updated_at = datetime.utcnow()
        
        self.logger.log_event(
            "ORDER_STATUS_UPDATE",
            f"Order {order.order_id} status updated to {status.value}"
        )
    
    def _handle_execution_error(self, order: Order, error_msg: str) -> None:
        """Handle order execution error"""
        order.error_message = error_msg
        self._update_order_status(order, OrderStatus.REJECTED)
        
        self.error_handler.handle_error(
            TradeExecutionError(f"Order execution failed: {error_msg}")
        )
    
    def _start_order_monitor(self) -> None:
        """Start order monitoring thread"""
        def monitor_thread():
            while True:
                try:
                    self._check_pending_orders()
                    self._check_order_expiry()
                except Exception as e:
                    self.error_handler.handle_error(
                        TradeExecutionError(f"Order monitor error: {str(e)}")
                    )
                time.sleep(1)
        
        thread = threading.Thread(target=monitor_thread, daemon=True)
        thread.start()
    
    def _check_pending_orders(self) -> None:
        """Check and update pending orders"""
        current_time = datetime.utcnow()
        
        with self._lock:
            for order in self._orders.values():
                if order.status not in {OrderStatus.SUBMITTED, OrderStatus.PARTIAL}:
                    continue
                    
                current_price = self.market_data_manager.get_latest_price(order.symbol)
                if not current_price:
                    continue
                
                if order.order_type == OrderType.LIMIT:
                    if self._is_limit_price_favorable(current_price, order):
                        asyncio.create_task(self._execute_limit_order(order))
                
                elif order.order_type in {OrderType.STOP, OrderType.STOP_LIMIT}:
                    if self._is_stop_triggered(current_price, order):
                        asyncio.create_task(self._execute_stop_order(order))
    
    def _check_order_expiry(self) -> None:
        """Check for expired orders"""
        current_time = datetime.utcnow()
        
        with self._lock:
            for order in self._orders.values():
                if order.status not in {OrderStatus.SUBMITTED, OrderStatus.PARTIAL}:
                    continue
                    
                if order.time_in_force == "DAY":
                    # Check if order is from previous day
                    if order.created_at.date() < current_time.date():
                        self._expire_order(order)
    
    def _expire_order(self, order: Order) -> None:
        """Expire an order"""
        self._update_order_status(order, OrderStatus.EXPIRED)
        self._order_book.remove_order(order)
        
        self.logger.log_event(
            "ORDER_EXPIRED",
            f"Order {order.order_id} expired"
        )

class OrderBook:
    """Manages pending orders"""
    
    def __init__(self):
        self._buy_orders: Dict[str, List[Order]] = {}
        self._sell_orders: Dict[str, List[Order]] = {}
        self._lock = threading.Lock()
    
    def add_order(self, order: Order) -> None:
        """Add order to book"""
        with self._lock:
            orders_dict = (
                self._buy_orders if order.side == OrderSide.BUY
                else self._sell_orders
            )
            
            if order.symbol not in orders_dict:
                orders_dict[order.symbol] = []
            
            orders_dict[order.symbol].append(order)
            self._sort_orders(orders_dict[order.symbol])
    
    def remove_order(self, order: Order) -> None:
        """Remove order from book"""
        with self._lock:
            orders_dict = (
                self._buy_orders if order.side == OrderSide.BUY
                else self._sell_orders
            )
            
            if order.symbol in orders_dict:
                orders_dict[order.symbol] = [
                    o for o in orders_dict[order.symbol]
                    if o.order_id != order.order_id
                ]
    
    def _sort_orders(self, orders: List[Order]) -> None:
        """Sort orders by price and time"""
        orders.sort(
            key=lambda x: (x.price or Decimal('0'), x.created_at),
            reverse=True
        )

class TradeExecutionError(Exception):
    """Custom exception for trade execution errors"""
    pass

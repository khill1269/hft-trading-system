from typing import Dict, Optional, List, Set
from decimal import Decimal
from datetime import datetime, timedelta
import threading
from dataclasses import dataclass
from enum import Enum

class RiskLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class PositionLimit:
    max_position_size: Decimal
    max_notional_value: Decimal
    max_daily_trades: int
    max_daily_volume: Decimal
    max_concentration: Decimal  # Max % of portfolio in single position

@dataclass
class RiskMetrics:
    total_exposure: Decimal
    largest_position: Decimal
    position_count: int
    daily_pnl: Decimal
    daily_trades: int
    daily_volume: Decimal
    var_95: Decimal  # 95% Value at Risk
    current_drawdown: Decimal

class RiskManager:
    """Manages trading risk and position limits"""
    
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
        
        # Position tracking
        self._positions: Dict[str, Decimal] = {}
        self._position_costs: Dict[str, Decimal] = {}
        self._daily_trades: Dict[str, int] = {}
        self._daily_volume: Dict[str, Decimal] = {}
        
        # Risk limits
        self._position_limits: Dict[str, PositionLimit] = {}
        self._default_limit = self._create_default_limit()
        
        # Stop loss tracking
        self._stop_levels: Dict[str, Decimal] = {}
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Initialize risk monitoring
        self._start_risk_monitor()
    
    def check_order_risk(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal
    ) -> bool:
        """
        Check if an order complies with risk limits
        Returns True if order is acceptable, False otherwise
        """
        try:
            with self._lock:
                # Get position limit
                limit = self._position_limits.get(symbol, self._default_limit)
                
                # Calculate post-trade position
                current_pos = self._positions.get(symbol, Decimal('0'))
                post_trade_pos = (
                    current_pos + quantity if side == "BUY"
                    else current_pos - quantity
                )
                
                # Check position size limit
                if abs(post_trade_pos) > limit.max_position_size:
                    self.logger.log_event(
                        "RISK_LIMIT_EXCEEDED",
                        f"Position size limit exceeded for {symbol}"
                    )
                    return False
                
                # Check notional value limit
                notional_value = abs(post_trade_pos * price)
                if notional_value > limit.max_notional_value:
                    self.logger.log_event(
                        "RISK_LIMIT_EXCEEDED",
                        f"Notional value limit exceeded for {symbol}"
                    )
                    return False
                
                # Check daily trade count
                daily_trades = self._daily_trades.get(symbol, 0)
                if daily_trades >= limit.max_daily_trades:
                    self.logger.log_event(
                        "RISK_LIMIT_EXCEEDED",
                        f"Daily trade limit exceeded for {symbol}"
                    )
                    return False
                
                # Check daily volume
                daily_volume = self._daily_volume.get(symbol, Decimal('0'))
                if daily_volume + quantity > limit.max_daily_volume:
                    self.logger.log_event(
                        "RISK_LIMIT_EXCEEDED",
                        f"Daily volume limit exceeded for {symbol}"
                    )
                    return False
                
                # Check portfolio concentration
                total_exposure = self._calculate_total_exposure()
                concentration = notional_value / total_exposure
                if concentration > limit.max_concentration:
                    self.logger.log_event(
                        "RISK_LIMIT_EXCEEDED",
                        f"Concentration limit exceeded for {symbol}"
                    )
                    return False
                
                return True
                
        except Exception as e:
            self.error_handler.handle_error(
                RiskManagementError(f"Risk check failed: {str(e)}")
            )
            return False
    
    def update_position(
        self,
        symbol: str,
        quantity: Decimal,
        price: Decimal,
        side: str
    ) -> None:
        """Update position after trade execution"""
        with self._lock:
            # Update position
            current_pos = self._positions.get(symbol, Decimal('0'))
            if side == "BUY":
                new_pos = current_pos + quantity
            else:
                new_pos = current_pos - quantity
            
            self._positions[symbol] = new_pos
            
            # Update position cost
            current_cost = self._position_costs.get(symbol, Decimal('0'))
            trade_cost = quantity * price
            if side == "BUY":
                new_cost = current_cost + trade_cost
            else:
                new_cost = current_cost - trade_cost
            
            self._position_costs[symbol] = new_cost
            
            # Update daily statistics
            self._daily_trades[symbol] = self._daily_trades.get(symbol, 0) + 1
            self._daily_volume[symbol] = (
                self._daily_volume.get(symbol, Decimal('0')) + quantity
            )
            
            # Log position update
            self.logger.log_event(
                "POSITION_UPDATE",
                f"Position updated for {symbol}",
                extra_data={
                    "new_position": str(new_pos),
                    "average_cost": str(new_cost / new_pos if new_pos != 0 else 0)
                }
            )
    
    def get_risk_metrics(self) -> RiskMetrics:
        """Get current risk metrics"""
        with self._lock:
            total_exposure = self._calculate_total_exposure()
            largest_pos = max(
                (abs(pos) for pos in self._positions.values()),
                default=Decimal('0')
            )
            
            return RiskMetrics(
                total_exposure=total_exposure,
                largest_position=largest_pos,
                position_count=len(self._positions),
                daily_pnl=self._calculate_daily_pnl(),
                daily_trades=sum(self._daily_trades.values()),
                daily_volume=sum(self._daily_volume.values()),
                var_95=self._calculate_var(),
                current_drawdown=self._calculate_drawdown()
            )
    
    def set_position_limit(
        self,
        symbol: str,
        limit: PositionLimit
    ) -> None:
        """Set position limit for a symbol"""
        with self._lock:
            self._position_limits[symbol] = limit
            
            self.logger.log_event(
                "LIMIT_UPDATE",
                f"Position limit updated for {symbol}",
                extra_data={
                    "max_position": str(limit.max_position_size),
                    "max_notional": str(limit.max_notional_value)
                }
            )
    
    def set_stop_loss(
        self,
        symbol: str,
        stop_level: Decimal
    ) -> None:
        """Set stop loss level for a symbol"""
        with self._lock:
            self._stop_levels[symbol] = stop_level
            
            self.logger.log_event(
                "STOP_LOSS_SET",
                f"Stop loss set for {symbol}",
                extra_data={"stop_level": str(stop_level)}
            )
    
    def _calculate_total_exposure(self) -> Decimal:
        """Calculate total portfolio exposure"""
        total = Decimal('0')
        for symbol, position in self._positions.items():
            price = self.market_data_manager.get_latest_price(symbol)
            if price:
                total += abs(position * price)
        return total
    
    def _calculate_daily_pnl(self) -> Decimal:
        """Calculate daily P&L"""
        total_pnl = Decimal('0')
        for symbol, position in self._positions.items():
            price = self.market_data_manager.get_latest_price(symbol)
            if price and symbol in self._position_costs:
                cost = self._position_costs[symbol]
                market_value = position * price
                total_pnl += market_value - cost
        return total_pnl
    
    def _calculate_var(self) -> Decimal:
        """Calculate Value at Risk"""
        # Simplified VaR calculation
        total_exposure = self._calculate_total_exposure()
        return total_exposure * Decimal('0.02')  # 2% VaR
    
    def _calculate_drawdown(self) -> Decimal:
        """Calculate current drawdown"""
        daily_pnl = self._calculate_daily_pnl()
        total_exposure = self._calculate_total_exposure()
        
        if total_exposure == 0:
            return Decimal('0')
            
        return -min(daily_pnl / total_exposure, Decimal('0'))
    
    def _create_default_limit(self) -> PositionLimit:
        """Create default position limit"""
        return PositionLimit(
            max_position_size=Decimal(self.config.get('default_max_position', '1000')),
            max_notional_value=Decimal(self.config.get('default_max_notional', '100000')),
            max_daily_trades=int(self.config.get('default_max_trades', '100')),
            max_daily_volume=Decimal(self.config.get('default_max_volume', '10000')),
            max_concentration=Decimal(self.config.get('default_max_concentration', '0.2'))
        )
    
    def _start_risk_monitor(self) -> None:
        """Start risk monitoring thread"""
        def monitor_thread():
            while True:
                try:
                    self._check_risk_limits()
                    self._check_stop_losses()
                    self._reset_daily_metrics_if_needed()
                except Exception as e:
                    self.error_handler.handle_error(
                        RiskManagementError(f"Risk monitor error: {str(e)}")
                    )
                time.sleep(1)
        
        thread = threading.Thread(target=monitor_thread, daemon=True)
        thread.start()
    
    def _check_risk_limits(self) -> None:
        """Check if any risk limits are breached"""
        metrics = self.get_risk_metrics()
        
        # Check overall exposure
        max_exposure = Decimal(self.config.get('max_total_exposure', '1000000'))
        if metrics.total_exposure > max_exposure:
            self._handle_limit_breach(
                "TOTAL_EXPOSURE",
                f"Total exposure {metrics.total_exposure} exceeds limit {max_exposure}"
            )
        
        # Check drawdown
        max_drawdown = Decimal(self.config.get('max_drawdown', '0.1'))
        if metrics.current_drawdown > max_drawdown:
            self._handle_limit_breach(
                "DRAWDOWN",
                f"Current drawdown {metrics.current_drawdown} exceeds limit {max_drawdown}"
            )
    
    def _check_stop_losses(self) -> None:
        """Check if any stop losses are triggered"""
        for symbol, stop_level in self._stop_levels.items():
            if symbol not in self._positions:
                continue
                
            current_price = self.market_data_manager.get_latest_price(symbol)
            if not current_price:
                continue
                
            position = self._positions[symbol]
            if position > 0 and current_price <= stop_level:
                self._handle_stop_loss(symbol, "LONG", current_price, stop_level)
            elif position < 0 and current_price >= stop_level:
                self._handle_stop_loss(symbol, "SHORT", current_price, stop_level)
    
    def _handle_limit_breach(self, breach_type: str, message: str) -> None:
        """Handle risk limit breach"""
        self.logger.log_event(
            "RISK_LIMIT_BREACH",
            message,
            level="CRITICAL"
        )
        # Implement emergency procedures here
    
    def _handle_stop_loss(
        self,
        symbol: str,
        position_type: str,
        current_price: Decimal,
        stop_level: Decimal
    ) -> None:
        """Handle stop loss trigger"""
        self.logger.log_event(
            "STOP_LOSS_TRIGGERED",
            f"Stop loss triggered for {symbol} {position_type} position",
            level="WARNING",
            extra_data={
                "current_price": str(current_price),
                "stop_level": str(stop_level)
            }
        )
        # Implement stop loss procedures here
    
    def _reset_daily_metrics_if_needed(self) -> None:
        """Reset daily metrics at start of new trading day"""
        current_time = datetime.utcnow()
        if current_time.hour == 0 and current_time.minute == 0:
            with self._lock:
                self._daily_trades.clear()
                self._daily_volume.clear()

class RiskManagementError(Exception):
    """Custom exception for risk management errors"""
    pass

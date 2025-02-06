"""
Advanced metrics collection and monitoring for HFT system
"""
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import time
from dataclasses import dataclass
from prometheus_client import (
    Counter, Gauge, Histogram, Summary,
    CollectorRegistry, start_http_server
)
import numpy as np
from decimal import Decimal

@dataclass
class MetricsConfig:
    """Configuration for metrics collection"""
    enable_prometheus: bool = True
    prometheus_port: int = 8000
    collection_interval: float = 1.0  # seconds
    latency_buckets: List[float] = None

    def __post_init__(self):
        if self.latency_buckets is None:
            # Default latency buckets in microseconds
            self.latency_buckets = [
                1, 5, 10, 50, 100, 500,
                1000, 5000, 10000
            ]

class MetricsCollector:
    """Centralized metrics collection system"""
    
    def __init__(
        self,
        config: MetricsConfig,
        logger,
        error_handler
    ):
        self.config = config
        self.logger = logger
        self.error_handler = error_handler
        
        # Initialize Prometheus registry
        self.registry = CollectorRegistry()
        
        # Order metrics
        self.order_counter = Counter(
            'hft_orders_total',
            'Total number of orders processed',
            ['type', 'status'],
            registry=self.registry
        )
        self.order_latency = Histogram(
            'hft_order_latency_seconds',
            'Order processing latency',
            ['type'],
            buckets=self.config.latency_buckets,
            registry=self.registry
        )
        
        # Trade metrics
        self.trade_counter = Counter(
            'hft_trades_total',
            'Total number of trades executed',
            ['symbol'],
            registry=self.registry
        )
        self.trade_volume = Counter(
            'hft_trade_volume_total',
            'Total trading volume',
            ['symbol'],
            registry=self.registry
        )
        
        # Position metrics
        self.position_value = Gauge(
            'hft_position_value',
            'Current position value',
            ['symbol'],
            registry=self.registry
        )
        self.pnl_gauge = Gauge(
            'hft_pnl_total',
            'Total P&L',
            ['timeframe'],
            registry=self.registry
        )
        
        # Risk metrics
        self.var_gauge = Gauge(
            'hft_value_at_risk',
            'Value at Risk (95%)',
            registry=self.registry
        )
        self.exposure_gauge = Gauge(
            'hft_total_exposure',
            'Total market exposure',
            registry=self.registry
        )
        
        # System metrics
        self.latency_summary = Summary(
            'hft_system_latency_seconds',
            'System component latency',
            ['component'],
            registry=self.registry
        )
        self.error_counter = Counter(
            'hft_errors_total',
            'Total number of errors',
            ['type', 'severity'],
            registry=self.registry
        )
        
        # Market data metrics
        self.market_data_counter = Counter(
            'hft_market_data_updates_total',
            'Total market data updates',
            ['source', 'type'],
            registry=self.registry
        )
        self.market_data_latency = Histogram(
            'hft_market_data_latency_seconds',
            'Market data processing latency',
            ['source'],
            buckets=self.config.latency_buckets,
            registry=self.registry
        )
        
        # Performance metrics
        self._last_update = time.time()
        self._execution_times: List[float] = []
        
    async def start(self) -> None:
        """Start metrics collection"""
        if self.config.enable_prometheus:
            # Start Prometheus HTTP server
            start_http_server(
                self.config.prometheus_port,
                registry=self.registry
            )
            self.logger.info(
                f"Prometheus metrics server started on port {self.config.prometheus_port}"
            )
    
    def record_order(
        self,
        order_type: str,
        status: str,
        latency: float
    ) -> None:
        """Record order metrics"""
        try:
            # Increment order counter
            self.order_counter.labels(
                type=order_type,
                status=status
            ).inc()
            
            # Record latency
            self.order_latency.labels(
                type=order_type
            ).observe(latency)
            
        except Exception as e:
            self.error_handler.handle_error(f"Failed to record order metrics: {e}")
    
    def record_trade(
        self,
        symbol: str,
        quantity: Decimal,
        price: Decimal
    ) -> None:
        """Record trade metrics"""
        try:
            # Increment trade counter
            self.trade_counter.labels(symbol=symbol).inc()
            
            # Add trade volume
            volume = float(quantity * price)
            self.trade_volume.labels(symbol=symbol).inc(volume)
            
        except Exception as e:
            self.error_handler.handle_error(f"Failed to record trade metrics: {e}")
    
    def update_position(
        self,
        symbol: str,
        value: Decimal,
        pnl: Decimal
    ) -> None:
        """Update position metrics"""
        try:
            # Update position value
            self.position_value.labels(symbol=symbol).set(float(value))
            
            # Update P&L
            self.pnl_gauge.labels(timeframe='daily').set(float(pnl))
            
        except Exception as e:
            self.error_handler.handle_error(f"Failed to update position metrics: {e}")
    
    def update_risk_metrics(
        self,
        var_95: float,
        exposure: float
    ) -> None:
        """Update risk metrics"""
        try:
            self.var_gauge.set(var_95)
            self.exposure_gauge.set(exposure)
            
        except Exception as e:
            self.error_handler.handle_error(f"Failed to update risk metrics: {e}")
    
    def record_latency(
        self,
        component: str,
        latency: float
    ) -> None:
        """Record component latency"""
        try:
            self.latency_summary.labels(component=component).observe(latency)
            
            # Store execution time for performance analysis
            self._execution_times.append(latency)
            if len(self._execution_times) > 1000:
                self._execution_times = self._execution_times[-1000:]
                
        except Exception as e:
            self.error_handler.handle_error(f"Failed to record latency: {e}")
    
    def record_error(
        self,
        error_type: str,
        severity: str
    ) -> None:
        """Record error occurrence"""
        try:
            self.error_counter.labels(
                type=error_type,
                severity=severity
            ).inc()
            
        except Exception as e:
            self.error_handler.handle_error(f"Failed to record error: {e}")
    
    def record_market_data(
        self,
        source: str,
        update_type: str,
        latency: float
    ) -> None:
        """Record market data metrics"""
        try:
            # Increment update counter
            self.market_data_counter.labels(
                source=source,
                type=update_type
            ).inc()
            
            # Record latency
            self.market_data_latency.labels(source=source).observe(latency)
            
        except Exception as e:
            self.error_handler.handle_error(f"Failed to record market data metrics: {e}")
    
    def get_performance_metrics(self) -> Dict:
        """Get system performance metrics"""
        if not self._execution_times:
            return {}
            
        return {
            'latency_mean': np.mean(self._execution_times),
            'latency_median': np.median(self._execution_times),
            'latency_95th': np.percentile(self._execution_times, 95),
            'latency_99th': np.percentile(self._execution_times, 99),
            'latency_max': np.max(self._execution_times),
            'sample_count': len(self._execution_times)
        }

class MetricsError(Exception):
    """Custom exception for metrics collection errors"""
    pass
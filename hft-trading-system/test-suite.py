import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch
import asyncio

from data_validation import Trade, Position, ValidationUtils
from error_handling import TradingSystemError, ErrorSeverity, ErrorHandler
from config_manager import ConfigurationManager
from market_data import MarketDataManager
from risk_manager import RiskManager

class TestDataValidation:
    def test_trade_validation(self):
        # Valid trade
        valid_trade = Trade(
            symbol="AAPL",
            quantity=Decimal("100"),
            price=Decimal("150.50"),
            side="BUY",
            order_type="MARKET",
            timestamp=datetime.utcnow()
        )
        result = valid_trade.validate()
        assert result.is_valid
        assert not result.errors

        # Invalid trade
        invalid_trade = Trade(
            symbol="",  # Invalid: empty symbol
            quantity=Decimal("-100"),  # Invalid: negative quantity
            price=Decimal("0"),  # Invalid: zero price
            side="INVALID",  # Invalid: wrong side
            order_type="UNKNOWN",  # Invalid: wrong order type
            timestamp=datetime.utcnow()
        )
        result = invalid_trade.validate()
        assert not result.is_valid
        assert len(result.errors) >= 5

    def test_position_validation(self):
        # Valid position
        valid_position = Position(
            symbol="GOOGL",
            quantity=Decimal("50"),
            average_price=Decimal("2500.75"),
            current_price=Decimal("2600.00"),
            timestamp=datetime.utcnow()
        )
        result = valid_position.validate()
        assert result.is_valid
        assert not result.errors

        # Test PnL calculation
        expected_pnl = (Decimal("2600.00") - Decimal("2500.75")) * Decimal("50")
        assert valid_position.unrealized_pnl == expected_pnl

    def test_validation_utils(self):
        # Test price precision
        result = ValidationUtils.validate_price_precision(Decimal("123.45678"), max_decimals=4)
        assert not result.is_valid
        assert len(result.errors) == 1

        # Test quantity precision
        result = ValidationUtils.validate_quantity_precision(Decimal("100.0"), max_decimals=8)
        assert result.is_valid
        assert not result.errors

        # Test timestamp validation
        future_time = datetime.utcnow() + timedelta(seconds=120)
        result = ValidationUtils.validate_timestamp_range(future_time, max_future_seconds=60)
        assert not result.is_valid
        assert len(result.errors) == 1

class TestErrorHandling:
    @pytest.fixture
    def error_handler(self):
        mock_logger = Mock()
        return ErrorHandler(mock_logger)

    def test_error_severity_escalation(self, error_handler):
        # Test low severity error
        error = TradingSystemError("Test error", severity=ErrorSeverity.LOW)
        error_handler.handle_error(error)
        assert error_handler._error_counts[error.__class__.__name__] == 1

        # Test threshold exceeded
        for _ in range(100):
            error_handler.handle_error(error)
        assert error_handler._error_counts[error.__class__.__name__] == 101
        error_handler.logger.log_event.assert_called_with(
            "ERROR_THRESHOLD_EXCEEDED",
            mock.ANY,
            level="CRITICAL",
            extra_data=mock.ANY
        )

    @pytest.mark.asyncio
    async def test_error_handling_decorator(self):
        mock_logger = Mock()

        @handle_errors(mock_logger)
        async def test_function():
            raise TradingSystemError("Test error", severity=ErrorSeverity.HIGH)

        await test_function()
        mock_logger.log_error.assert_called_once()

class TestConfigurationManager:
    @pytest.fixture
    def config_manager(self):
        manager = ConfigurationManager()
        manager._config = {
            'database': {
                'host': 'localhost',
                'port': 5432,
                'database': 'trading',
                'username': 'test',
                'password': 'test',
                'pool_size': 5
            },
            'trading': {
                'max_position_size': 1000000,
                'risk_limit_percent': 0.02,
                'max_trades_per_day': 1000,
                'trading_hours_start': '09:30',
                'trading_hours_end': '16:00',
                'emergency_stop_loss': 0.05
            },
            'logging': {
                'log_level': 'INFO',
                'log_dir': 'logs',
                'max_file_size_mb': 100,
                'backup_count': 5
            }
        }
        return manager

    def test_config_loading(self, config_manager):
        db_config = config_manager.database
        assert db_config.host == 'localhost'
        assert db_config.port == 5432

        trading_config = config_manager.trading
        assert trading_config.max_position_size == 1000000
        assert trading_config.risk_limit_percent == 0.02

    def test_nested_config_access(self, config_manager):
        value = config_manager.get_value('database.host')
        assert value == 'localhost'

        # Test default value for non-existent path
        value = config_manager.get_value('invalid.path', default='default')
        assert value == 'default'

class TestMarketDataManager:
    @pytest.fixture
    def market_data_manager(self):
        mock_db = Mock()
        mock_config = {
            'websocket_uri': 'ws://test.com',
            'max_reconnect_attempts': 3
        }
        mock_logger = Mock()
        mock_error_handler = Mock()
        
        return MarketDataManager(mock_db, mock_config, mock_logger, mock_error_handler)

    @pytest.mark.asyncio
    async def test_market_data_processing(self, market_data_manager):
        # Test market data processing
        mock_message = {
            'symbol': 'AAPL',
            'price': '150.50',
            'volume': '1000',
            'timestamp': datetime.utcnow().timestamp(),
            'bid': '150.45',
            'ask': '150.55'
        }
        
        await market_data_manager._process_market_data(json.dumps(mock_message))
        
        # Verify data was added to buffer
        price = market_data_manager.buffer.get_latest_price('AAPL')
        assert price == Decimal('150.50')

    def test_market_data_validation(self, market_data_manager):
        valid_tick = MarketTick(
            symbol='AAPL',
            price=Decimal('150.50'),
            volume=Decimal('1000'),
            timestamp=datetime.utcnow()
        )
        assert market_data_manager._validate_tick(valid_tick)

        future_tick = MarketTick(
            symbol='AAPL',
            price=Decimal('150.50'),
            volume=Decimal('1000'),
            timestamp=datetime.utcnow() + timedelta(seconds=10)
        )
        assert not market_data_manager._validate_tick(future_tick)

class TestRiskManager:
    @pytest.fixture
    def risk_manager(self):
        mock_config = {
            'position_limits': {
                'max_position_size': Decimal('1000000'),
                'max_concentration': Decimal('0.2'),
                'max_leverage': Decimal('2.0')
            }
        }
        mock_logger = Mock()
        mock_error_handler = Mock()
        
        return RiskManager(mock_config, mock_logger, mock_error_handler)

    def test_position_limits(self, risk_manager):
        # Test normal position
        assert risk_manager.check_order_risk(
            symbol='AAPL',
            side='BUY',
            quantity=Decimal('100'),
            price=Decimal('150.50')
        )

        # Test position limit breach
        assert not risk_manager.check_order_risk(
            symbol='AAPL',
            side='BUY',
            quantity=Decimal('10000'),
            price=Decimal('150.50')
        )

    def test_risk_metrics(self, risk_manager):
        # Add test position
        risk_manager.update_position(
            symbol='AAPL',
            quantity=Decimal('100'),
            price=Decimal('150.50'),
            side='BUY'
        )

        metrics = risk_manager.get_risk_metrics()
        assert metrics.position_count == 1
        assert metrics.largest_position > 0

    def test_emergency_procedures(self, risk_manager):
        # Simulate emergency condition
        with pytest.raises(TradingSystemError):
            risk_manager._handle_critical_margin()
            
        risk_manager.logger.log_event.assert_called_with(
            "CRITICAL_MARGIN_ACTION",
            mock.ANY,
            level="ERROR"
        )

if __name__ == '__main__':
    pytest.main(['-v'])
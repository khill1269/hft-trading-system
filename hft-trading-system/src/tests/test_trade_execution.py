import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from trade_execution.trade_execution import TradeExecution

class TestTradeExecution:
    def test_execute_trade(self):
        trade_exec = TradeExecution()
        result = trade_exec.execute_trade_ibkr("AAPL", 10, "BUY")
        assert result is None  # Adjust based on actual return


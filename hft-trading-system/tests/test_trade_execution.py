import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from trade_execution import trade_execution

class TestTradeExecution:
    def test_execute_trade(self):
        trade_exec = trade_execution.TradeExecution()
        result = trade_exec.execute_trade_ibkr("AAPL", 10, "BUY")
        assert result is None  # Adjust based on actual return


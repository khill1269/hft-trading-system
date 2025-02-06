import unittest
from src.trade_execution.trade_execution import TradeExecution

class TestTradeExecution(unittest.TestCase):
    def test_execute_trade(self):
        trade_exec = TradeExecution()
        result = trade_exec.execute_trade_ibkr("AAPL", 10, "BUY")
        self.assertIsNone(result)

if __name__ == "__main__":
    unittest.main()


import unittest
from src.market_data.market_data import MarketData

class TestMarketData(unittest.TestCase):
    def test_fetch_live_data(self):
        market = MarketData()
        result = market.fetch_live_data("AAPL")
        self.assertIsNotNone(result)

if __name__ == "__main__":
    unittest.main()


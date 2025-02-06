import unittest
from src.risk_management.risk_manager import RiskManager

class TestRiskManagement(unittest.TestCase):
    def test_evaluate_risk(self):
        risk_manager = RiskManager()
        result = risk_manager.evaluate_risk({"symbol": "AAPL", "quantity": 10})
        self.assertEqual(result, "LOW RISK")

if __name__ == "__main__":
    unittest.main()


import yaml
from ib_insync import IB
import logging

logging.basicConfig(level=logging.INFO)

class TradeExecution:
    def __init__(self):
        self.config = self.load_config()
        self.ib = IB()

    def load_config(self):
        with open("config/settings.yaml", "r") as file:
            return yaml.safe_load(file)

    def connect_ibkr(self):
        mode = self.config["trading_mode"]
        host = self.config["execution"]["trading_environment"][mode]["host"]
        port = self.config["execution"]["trading_environment"][mode]["port"]
        client_id = self.config["execution"]["trading_environment"][mode]["client_id"]

        try:
            self.ib.connect(host, port, clientId=client_id)
            logging.info(f"✅ Connected to IBKR in {mode.upper()} mode.")
            return True
        except Exception as e:
            logging.error(f"❌ Connection to IBKR failed: {e}")
            return False

    def execute_trade_ibkr(self, symbol, quantity, action, order_type="MKT", limit_price=None):
        if not self.ib.isConnected():
            logging.error("❌ Not connected to IBKR. Cannot execute trade.")
            return None
        
        logging.info(f"Executing trade: {action} {quantity} of {symbol}, Type: {order_type}, Limit: {limit_price}")
        # Actual IBKR order execution logic goes here
        return {"status": "executed", "symbol": symbol, "quantity": quantity, "action": action}


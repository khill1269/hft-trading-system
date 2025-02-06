import logging
import random

class AITrader:
    def decide_trade(self, market_data):
        logging.info("Analyzing market data using AI model")
        action = random.choice(["BUY", "SELL", "HOLD"])
        return action


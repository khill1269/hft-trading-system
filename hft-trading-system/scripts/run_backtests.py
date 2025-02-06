import logging

logging.basicConfig(level=logging.INFO)

class BacktestEngine:
    def __init__(self):
        logging.info("Initializing Backtesting Engine")

    def run_strategy(self, strategy_name):
        logging.info(f"Running backtest for strategy: {strategy_name}")
        return {"strategy": strategy_name, "profit": 5.2}

if __name__ == "__main__":
    backtester = BacktestEngine()
    result = backtester.run_strategy("AI Momentum")
    print(result)


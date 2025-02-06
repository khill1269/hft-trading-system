import requests
import logging

logging.basicConfig(level=logging.INFO)

def fetch_market_data(symbol, api_key):
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=1min&apikey={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        logging.info(f"Fetched market data for {symbol}")
        return response.json()
    else:
        logging.error(f"Failed to fetch data for {symbol}")
        return None

if __name__ == "__main__":
    API_KEY = "your_alpha_vantage_api_key_here"
    print(fetch_market_data("AAPL", API_KEY))


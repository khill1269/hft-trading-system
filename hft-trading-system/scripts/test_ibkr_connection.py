from ib_insync import IB
import logging

logging.basicConfig(level=logging.INFO)

def test_ibkr_connection(host="127.0.0.1", port=7497, client_id=1):
    ib = IB()
    try:
        ib.connect(host, port, clientId=client_id)
        if ib.isConnected():
            logging.info("✅ IBKR API Connected Successfully!")
            return True
        else:
            logging.error("❌ IBKR API Connection Failed!")
            return False
    except Exception as e:
        logging.error(f"Error connecting to IBKR: {e}")
        return False
    finally:
        ib.disconnect()

if __name__ == "__main__":
    test_ibkr_connection()


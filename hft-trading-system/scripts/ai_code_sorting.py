import os
import shutil
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Define file categories based on naming conventions
CATEGORIES = {
    "market_data": ["data", "scraper", "fetch", "api", "ibkr"],
    "trade_execution": ["execution", "order", "trade", "route"],
    "risk_management": ["risk", "hedging", "monitor", "margin"],
    "ai_models": ["ai", "ml", "nn", "rl", "model", "predict"],
    "utils": ["helper", "util", "common", "tools"],
    "config": ["config", "setup", "settings"]
}

# Define source and destination directories
SOURCE_DIR = "pre_existing_code_upload/"
DESTINATION_DIRS = {
    "market_data": "src/market_data/",
    "trade_execution": "src/trade_execution/",
    "risk_management": "src/risk_management/",
    "ai_models": "src/ai_models/",
    "utils": "src/utils/",
    "config": "config/"
}

def categorize_and_move_files():
    """Sorts and moves files from the unstructured directory to the appropriate categorized directories."""
    if not os.path.exists(SOURCE_DIR):
        logging.warning("No files found in pre_existing_code_upload/")
        return

    for file in os.listdir(SOURCE_DIR):
        file_path = os.path.join(SOURCE_DIR, file)
        if not os.path.isfile(file_path):
            continue  # Skip directories

        category_found = False
        for category, keywords in CATEGORIES.items():
            if any(keyword in file.lower() for keyword in keywords):
                dest_dir = DESTINATION_DIRS[category]
                os.makedirs(dest_dir, exist_ok=True)
                shutil.move(file_path, os.path.join(dest_dir, file))
                logging.info(f"Moved {file} to {dest_dir}")
                category_found = True
                break

        if not category_found:
            logging.warning(f"Could not categorize {file}, leaving in pre_existing_code_upload/")

if __name__ == "__main__":
    categorize_and_move_files()


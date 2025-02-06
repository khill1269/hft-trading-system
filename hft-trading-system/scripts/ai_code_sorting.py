import os
import shutil
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Define file categories based on naming conventions
CATEGORIES = {
    "market_data": ["data", "market", "scraper", "fetch", "api", "ibkr"],
    "trade_execution": ["execution", "order", "trade", "route", "ibkr"],
    "risk_management": ["risk", "hedging", "monitor", "margin"],
    "ai_models": ["ai", "ml", "nn", "rl", "model", "predict"],
    "utils": ["helper", "util", "common", "tools"],
    "config": ["config", "setup", "settings"],
    "logs": ["log", "logs"],
    "tests": ["test", "testing"],
    "scripts": ["script", "setup", "install"]
}

# Define the source directory as the current directory
SOURCE_DIR = "."  

# Define destination directories
DESTINATION_DIRS = {
    "market_data": "src/market_data/",
    "trade_execution": "src/trade_execution/",
    "risk_management": "src/risk_management/",
    "ai_models": "src/ai_models/",
    "utils": "src/utils/",
    "config": "config/",
    "logs": "logs/",
    "tests": "tests/",
    "scripts": "scripts/"
}

# Ensure destination directories exist
for directory in DESTINATION_DIRS.values():
    os.makedirs(directory, exist_ok=True)

def categorize_and_move_files():
    """Sorts and moves files from the main directory into structured subdirectories."""
    for file in os.listdir(SOURCE_DIR):
        file_path = os.path.join(SOURCE_DIR, file)

        # Skip directories and this script itself
        if not os.path.isfile(file_path) or file == "ai_code_sorting.py":
            continue  

        # Categorize the file
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
            logging.warning(f"Could not categorize {file}, leaving in the main directory.")

if __name__ == "__main__":
    categorize_and_move_files()


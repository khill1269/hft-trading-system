import os

def check_installed_packages():
    try:
        import ib_insync
        import pytest
        print("✅ All required packages are installed.")
    except ImportError as e:
        print(f"⚠ Missing package: {e}")

if __name__ == "__main__":
    check_installed_packages()



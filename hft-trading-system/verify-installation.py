import sys
import importlib
from typing import List, Tuple
import subprocess
import os

def check_dependency(module_name: str) -> Tuple[bool, str]:
    """Check if a Python module is installed and get its version"""
    try:
        module = importlib.import_module(module_name)
        version = getattr(module, '__version__', 'unknown')
        return True, version
    except ImportError:
        return False, "Not installed"

def check_gpu_support() -> bool:
    """Check for GPU support"""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False

def check_database_connection() -> bool:
    """Check database connections"""
    try:
        # Check PostgreSQL
        from sqlalchemy import create_engine
        engine = create_engine('postgresql://localhost:5432/')
        engine.connect()
        
        # Check Redis
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        
        # Check MongoDB
        from pymongo import MongoClient
        client = MongoClient('localhost', 27017)
        client.server_info()
        
        return True
    except Exception as e:
        print(f"Database connection error: {str(e)}")
        return False

def check_trading_api() -> bool:
    """Check trading API connection"""
    try:
        from ibapi.client import EClient
        from ibapi.wrapper import EWrapper
        
        class TestWrapper(EWrapper):
            pass
        
        class TestClient(EClient):
            def __init__(self, wrapper):
                EClient.__init__(self, wrapper)
        
        wrapper = TestWrapper()
        client = TestClient(wrapper)
        
        return True
    except Exception as e:
        print(f"Trading API error: {str(e)}")
        return False

def main():
    print("Verifying Trading System Installation...")
    print("-" * 50)
    
    # Core dependencies to check
    dependencies = [
        # Core ML
        'numpy', 'pandas', 'sklearn', 'torch', 'tensorflow',
        
        # Database
        'sqlalchemy', 'redis', 'pymongo',
        
        # Trading
        'ibapi', 'talib', 'yfinance',
        
        # ML/AI
        'transformers', 'stable_baselines3',
        
        # Quantum
        'qiskit', 'pennylane',
        
        # Optimization
        'numba', 'ray'
    ]
    
    all_passed = True
    
    # Check Python version
    python_version = sys.version.split()[0]
    print(f"Python Version: {python_version}")
    
    # Check dependencies
    print("\nChecking Dependencies:")
    for dep in dependencies:
        installed, version = check_dependency(dep)
        status = "✓" if installed else "✗"
        print(f"{dep:20} [{status}] {version}")
        if not installed:
            all_passed = False
    
    # Check GPU support
    print("\nChecking GPU Support:")
    gpu_available = check_gpu_support()
    print(f"GPU Support: {'✓' if gpu_available else '✗'}")
    
    # Check database connections
    print("\nChecking Database Connections:")
    db_connected = check_database_connection()
    print(f"Database Connections: {'✓' if db_connected else '✗'}")
    if not db_connected:
        all_passed = False
    
    # Check trading API
    print("\nChecking Trading API:")
    api_working = check_trading_api()
    print(f"Trading API: {'✓' if api_working else '✗'}")
    if not api_working:
        all_passed = False
    
    # Check disk space
    print("\nChecking System Resources:")
    disk_space = os.statvfs('/')
    free_space_gb = (disk_space.f_bavail * disk_space.f_frsize) / (1024 ** 3)
    print(f"Free Disk Space: {free_space_gb:.2f} GB")
    
    # Memory check
    if sys.platform == "linux" or sys.platform == "linux2":
        with open('/proc/meminfo') as f:
            mem = f.readline()
            total_memory_gb = int(mem.split()[1]) / (1024 ** 2)
            print(f"Total Memory: {total_memory_gb:.2f} GB")
    
    print("\nVerification Summary:")
    if all_passed:
        print("✓ All components installed and working correctly")
    else:
        print("✗ Some components need attention")
        print("Please check the output above and install missing dependencies")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())

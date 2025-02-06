#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Setting up High-Frequency Trading System...${NC}"

# Create main project directory
PROJECT_DIR="hft_trading_system"
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# Create directory structure
echo -e "${GREEN}Creating directory structure...${NC}"
directories=(
    "src/core"
    "src/hft"
    "src/ml"
    "src/risk"
    "src/data"
    "src/utils"
    "config/development"
    "config/production"
    "tests/unit"
    "tests/integration"
    "tests/performance"
    "docs/api"
    "docs/architecture"
    "logs"
    "scripts"
    "tools"
    "models"
)

for dir in "${directories[@]}"; do
    mkdir -p "$dir"
    touch "$dir/__init__.py"
done

# Create virtual environment
echo -e "${GREEN}Creating virtual environment...${NC}"
python -m venv venv

# Create setup.py
echo -e "${GREEN}Creating setup.py...${NC}"
cat > setup.py << EOL
from setuptools import setup, find_packages

setup(
    name="hft_trading_system",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        'numpy>=1.21.0',
        'pandas>=1.3.0',
        'scikit-learn>=0.24.0',
        'torch>=1.9.0',
        'tensorflow>=2.6.0',
        'sqlalchemy>=1.4.0',
        'redis>=4.0.0',
        'pymongo>=3.12.0',
        'fastapi>=0.68.0',
        'websockets>=10.0',
        'ibapi>=9.81.1',
        'ta-lib>=0.4.0',
        'qiskit>=0.34.0',
        'numba>=0.54.0',
        'matplotlib>=3.4.0',
    ],
    extras_require={
        'dev': [
            'pytest>=6.2.5',
            'pytest-asyncio>=0.16.0',
            'pytest-cov>=2.12.0',
            'black>=21.7b0',
            'mypy>=0.910',
            'pylint>=2.8.0',
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="High-Frequency Trading System with ML capabilities",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/hft_trading_system",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
)
EOL

# Create README.md
echo -e "${GREEN}Creating README.md...${NC}"
cat > README.md << EOL
# High-Frequency Trading System

## Overview
Advanced trading system with ultra-low latency execution, machine learning integration, and real-time analytics.

## Features
- Ultra-low latency order execution with FPGA integration
- Advanced machine learning models for prediction
- Real-time market data processing
- Risk management and monitoring
- Network optimization for co-location
- Comprehensive backtesting framework

## Installation

### Prerequisites
- Python 3.8+
- FPGA development tools (for FPGA features)
- Redis
- MongoDB
- PostgreSQL

### Setup
1. Clone the repository:
\`\`\`bash
git clone https://github.com/yourusername/hft_trading_system.git
cd hft_trading_system
\`\`\`

2. Create and activate virtual environment:
\`\`\`bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\\Scripts\\activate  # Windows
\`\`\`

3. Install dependencies:
\`\`\`bash
pip install -e ".[dev]"
\`\`\`

## Configuration
1. Copy example config:
\`\`\`bash
cp config/example.yaml config/development/config.yaml
\`\`\`

2. Edit configuration file with your settings.

## Running Tests
\`\`\`bash
pytest tests/
\`\`\`

## Documentation
See \`docs/\` directory for detailed documentation.

## License
MIT License
EOL

# Create GitHub Actions workflow
echo -e "${GREEN}Creating GitHub Actions workflow...${NC}"
mkdir -p .github/workflows
cat > .github/workflows/ci.yml << EOL
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9]

    steps:
    - uses: actions/checkout@v2
    - name: Set up Python \${{ matrix.python-version }}
      uses: actions/setup-python@v2
      with:
        python-version: \${{ matrix.python-version }}
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e ".[dev]"
    - name: Run tests
      run: |
        pytest tests/ --cov=src --cov-report=xml
    - name: Upload coverage
      uses: codecov/codecov-action@v2
      with:
        file: ./coverage.xml

  lint:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.8
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install black pylint mypy
    - name: Run linters
      run: |
        black --check src tests
        pylint src tests
        mypy src tests
EOL

# Create example config
echo -e "${GREEN}Creating example config...${NC}"
cat > config/example.yaml << EOL
database:
  postgresql:
    host: localhost
    port: 5432
    database: trading_system
    user: trading_user
    password: your_password
    pool_size: 5
  
  redis:
    host: localhost
    port: 6379
    db: 0
  
  mongodb:
    host: localhost
    port: 27017
    database: trading_system
    user: trading_user
    password: your_password

trading:
  enabled: true
  paper_trading: true
  risk_limits:
    max_position_size: 100000
    max_leverage: 2.0
    max_concentration: 0.2
    max_drawdown: 0.1

hft:
  fpga_enabled: false
  latency_threshold_ns: 100000
  network_optimization:
    enabled: true
    interface: eth0
  
  colocated_exchanges:
    - name: exchange1
      ip: 10.0.0.1
      port: 5555
      latency_threshold_ns: 50000

ml:
  enabled: true
  models:
    - type: price_prediction
      lookback_window: 100
      prediction_horizon: 10
    - type: sentiment_analysis
      update_interval: 300

logging:
  level: INFO
  file: logs/trading_system.log
  max_size: 1024000000
  backup_count: 5
EOL

# Create .gitignore
echo -e "${GREEN}Creating .gitignore...${NC}"
cat > .gitignore << EOL
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
ENV/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Logs
logs/
*.log

# Config
config/*/*.yaml
!config/example.yaml

# Database
*.db
*.sqlite3

# Coverage
.coverage
coverage.xml
htmlcov/

# FPGA
*.bit
*.bin
*.hex

# Environment variables
.env
.env.*

# Certificates
*.pem
*.key
*.crt

# Documentation build
docs/_build/
EOL

# Create initial git repository
echo -e "${GREEN}Initializing git repository...${NC}"
git init
git add .
git commit -m "Initial commit"

# Create activation script
echo -e "${GREEN}Creating activation script...${NC}"
cat > activate.sh << EOL
#!/bin/bash
source venv/bin/activate
export PYTHONPATH=\$PYTHONPATH:\$(pwd)
export TRADING_ENV=development
EOL
chmod +x activate.sh

echo -e "${BLUE}Project setup complete!${NC}"
echo -e "${GREEN}Next steps:${NC}"
echo "1. Edit setup.py with your information"
echo "2. Create virtual environment: python -m venv venv"
echo "3. Activate virtual environment: source venv/bin/activate"
echo "4. Install dependencies: pip install -e .[dev]"
echo "5. Copy and edit config: cp config/example.yaml config/development/config.yaml"
echo "6. Run tests: pytest tests/"

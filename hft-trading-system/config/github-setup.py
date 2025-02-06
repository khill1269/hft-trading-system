#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Setting up HFT Trading System Project...${NC}"

# Create main project structure
mkdir -p hft_trading_system/{src,tests,config,docs,scripts,tools}

# Create source code directories
mkdir -p hft_trading_system/src/{core,market_data,execution,risk,analysis,utils}

# Create test directories
mkdir -p hft_trading_system/tests/{unit,integration,performance}

# Create configuration directories
mkdir -p hft_trading_system/config/{development,staging,production}

# Create documentation directories
mkdir -p hft_trading_system/docs/{api,architecture,deployment}

# Initialize Python packages
touch hft_trading_system/src/__init__.py
touch hft_trading_system/tests/__init__.py

# Create README.md
cat > hft_trading_system/README.md << EOL
# High-Frequency Trading System

## Overview
Advanced high-frequency trading system with support for:
- Market data processing and analysis
- Ultra-low latency execution
- Risk management
- Algorithmic trading strategies
- Real-time monitoring and alerts

## Project Structure
\`\`\`
hft_trading_system/
├── src/                    # Source code
│   ├── core/              # Core system components
│   ├── market_data/       # Market data handling
│   ├── execution/         # Order execution
│   ├── risk/              # Risk management
│   ├── analysis/          # Market analysis
│   └── utils/             # Utilities
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── performance/      # Performance tests
├── config/               # Configuration files
│   ├── development/     # Development environment
│   ├── staging/        # Staging environment
│   └── production/     # Production environment
├── docs/                # Documentation
│   ├── api/            # API documentation
│   ├── architecture/   # System architecture
│   └── deployment/     # Deployment guides
├── scripts/            # Utility scripts
└── tools/              # Development tools
\`\`\`

## Setup
1. Clone the repository
2. Install dependencies: \`pip install -r requirements.txt\`
3. Configure environment: \`cp config/example.yaml config/development/config.yaml\`
4. Run tests: \`pytest tests/\`

## Development Guidelines
- Use Python 3.8+
- Follow PEP 8 style guide
- Write tests for all new features
- Update documentation accordingly

## License
MIT License - See LICENSE file for details
EOL

# Create requirements.txt
cat > hft_trading_system/requirements.txt << EOL
# Core Dependencies
numpy>=1.21.0
pandas>=1.3.0
scipy>=1.7.0

# Market Data
websockets>=10.0
aiohttp>=3.8.0

# Database
sqlalchemy>=1.4.0
asyncpg>=0.25.0
redis>=4.0.0

# Risk Management
ta-lib>=0.4.0
statsmodels>=0.13.0

# API and Web
fastapi>=0.68.0
uvicorn>=0.15.0

# Monitoring
prometheus-client>=0.11.0
grafana-api>=1.0.0

# Testing
pytest>=6.2.5
pytest-asyncio>=0.16.0
pytest-cov>=2.12.0

# Development
black>=21.7b0
mypy>=0.910
pylint>=2.9.6
EOL

# Create setup.py
cat > hft_trading_system/setup.py << EOL
from setuptools import setup, find_packages

setup(
    name="hft_trading_system",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        line.strip()
        for line in open("requirements.txt")
        if not line.startswith("#") and line.strip()
    ],
    author="Your Name",
    author_email="your.email@example.com",
    description="High-Frequency Trading System",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
    ],
)
EOL

# Create .gitignore
cat > hft_trading_system/.gitignore << EOL
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

# Config files
config/development/*.yaml
config/staging/*.yaml
config/production/*.yaml
!config/example.yaml

# Cache
.cache/
.pytest_cache/

# Coverage reports
.coverage
coverage.xml
htmlcov/

# Build files
*.o
*.so
*.dylib

# Environment variables
.env
.env.*

# Local development
local_settings.py
EOL

# Create example config
cat > hft_trading_system/config/example.yaml << EOL
database:
  host: localhost
  port: 5432
  name: hft_trading
  user: trading_user
  password: your_password
  pool_size: 5

market_data:
  websocket_uri: ws://market.data.com
  symbols: [AAPL, GOOGL, MSFT]
  reconnect_attempts: 3

execution:
  max_slippage: 0.001
  order_timeout: 5
  retry_attempts: 3

risk:
  max_position_size: 1000000
  max_drawdown: 0.1
  daily_loss_limit: 50000
  position_limits:
    stock: 1000000
    option: 500000
    futures: 2000000

monitoring:
  latency_threshold_ms: 10
  error_threshold: 100
  alert_endpoints:
    - type: email
      address: alerts@yourdomain.com
    - type: slack
      webhook: https://hooks.slack.com/...

logging:
  level: INFO
  file: logs/trading_system.log
  rotate_size: 10485760  # 10MB
  keep_logs: 30
EOL

# Create example documentation
cat > hft_trading_system/docs/README.md << EOL
# HFT Trading System Documentation

## Contents

### API Documentation
- REST API endpoints
- WebSocket streams
- Data models

### Architecture Documentation
- System overview
- Component interactions
- Data flow diagrams

### Deployment Documentation
- Installation guide
- Configuration guide
- Scaling guide
EOL

# Initialize git repository
cd hft_trading_system
git init
git add .
git commit -m "Initial commit"

echo -e "${GREEN}Project structure created successfully!${NC}"
echo -e "${BLUE}Next steps:${NC}"
echo "1. Edit setup.py with your information"
echo "2. Create a GitHub repository"
echo "3. Push the code: git remote add origin <your-repo-url>"
echo "4. Configure your development environment"

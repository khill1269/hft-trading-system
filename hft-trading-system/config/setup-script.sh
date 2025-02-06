#!/bin/bash

# Create directory structure
mkdir -p trading_system/src
mkdir -p trading_system/config
mkdir -p trading_system/tests
mkdir -p trading_system/logs
mkdir -p trading_system/docs

# Move into the trading system directory
cd trading_system

# Create a virtual environment
python -m venv venv

# Create empty __init__.py files
touch src/__init__.py
touch tests/__init__.py

# Create requirements.txt
cat > requirements.txt << EOL
numpy>=1.21.0
pandas>=1.3.0
scikit-learn>=0.24.0
torch>=1.9.0
tensorflow>=2.6.0
sqlalchemy>=1.4.0
redis>=4.0.0
pymongo>=3.12.0
fastapi>=0.68.0
websockets>=10.0
ibapi>=9.81.1
ta-lib>=0.4.0
qiskit>=0.34.0
numba>=0.54.0
matplotlib>=3.4.0
pytest>=6.2.5
black>=21.7b0
EOL

# Create README.md
cat > README.md << EOL
# High-Frequency Trading System

Advanced trading system with HFT capabilities, machine learning integration, and real-time analytics.

## Components
- Ultra-low latency execution
- FPGA integration
- Network optimization
- Real-time analytics
- Machine learning models
- Risk management

## Setup
1. Create virtual environment: \`python -m venv venv\`
2. Activate virtual environment: \`source venv/bin/activate\` (Linux/Mac) or \`venv\\Scripts\\activate\` (Windows)
3. Install requirements: \`pip install -r requirements.txt\`

## Configuration
Configure the system in \`config/config.yaml\`

## Running Tests
\`pytest tests/\`
EOL

# Create .gitignore
cat > .gitignore << EOL
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
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
config/*.yaml
!config/example.yaml

# Certificates and keys
*.pem
*.key
*.crt

# Database
*.db
*.sqlite3

EOL

echo "Project structure created successfully!"

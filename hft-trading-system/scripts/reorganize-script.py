#!/usr/bin/env python3
"""
Script to reorganize and consolidate HFT trading system files.
"""
import os
import shutil
from pathlib import Path
import re
from typing import Dict, List, Set
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Project structure definition
PROJECT_STRUCTURE = {
    'src': {
        'core': [
            '__init__.py',
            'engine.py',
            'settings.py',
            'models.py',
            'exceptions.py',
            'infrastructure.py'
        ],
        'market_data': {
            '__init__.py': None,
            'connectors': {
                '__init__.py': None,
                'ibkr.py': None,
                'base.py': None
            },
            'processors': {
                '__init__.py': None,
                'orderbook.py': None,
                'aggregator.py': None
            }
        },
        'execution': {
            '__init__.py': None,
            'engine.py': None,
            'handlers': {
                '__init__.py': None,
                'order.py': None,
                'trade.py': None
            }
        },
        'risk': {
            '__init__.py': None,
            'manager.py': None,
            'calculators': {
                '__init__.py': None,
                'var.py': None,
                'exposure.py': None
            },
            'limits': {
                '__init__.py': None,
                'position.py': None,
                'trading.py': None
            }
        },
        'ai': {
            '__init__.py': None,
            'engine.py': None,
            'models': {
                '__init__.py': None,
                'base.py': None,
                'implementations.py': None
            },
            'optimizers': {
                '__init__.py': None,
                'quantum.py': None
            }
        },
        'monitoring': {
            '__init__.py': None,
            'service.py': None,
            'metrics.py': None,
            'ui': {
                '__init__.py': None,
                'dashboard.tsx': None
            }
        },
        'database': {
            '__init__.py': None,
            'manager.py': None,
            'migrations': {
                '__init__.py': None
            }
        },
        'config': {
            '__init__.py': None,
            'manager.py': None,
            'validators.py': None
        }
    },
    'tests': {
        'unit': {'__init__.py': None},
        'integration': {'__init__.py': None},
        'performance': {'__init__.py': None}
    },
    'scripts': {
        '__init__.py': None,
        'setup.sh': None
    },
    'docs': {
        'api': {},
        'architecture': {},
        'deployment': {}
    }
}

# File consolidation mappings
FILE_CONSOLIDATION = {
    'market_data': {
        'output': 'src/market_data/connectors/ibkr.py',
        'inputs': ['ibkr-market-data.py', 'market-data.py'],
        'merge_strategy': 'class_based'
    },
    'core': {
        'output': 'src/core/engine.py',
        'inputs': ['core-system.py', 'core-infrastructure.txt', 'core-structure.txt'],
        'merge_strategy': 'sequential'
    },
    'monitoring': {
        'output': 'src/monitoring/service.py',
        'inputs': ['monitoring-service.txt', 'improved-logging.py'],
        'merge_strategy': 'class_based'
    },
    'database': {
        'output': 'src/database/manager.py',
        'inputs': ['database-init.py', 'database-manager.py'],
        'merge_strategy': 'class_based'
    }
}

def create_directory_structure(base_path: Path) -> None:
    """Create the new directory structure"""
    def create_recursive(path: Path, structure: Dict) -> None:
        path.mkdir(parents=True, exist_ok=True)
        for name, content in structure.items():
            full_path = path / name
            if isinstance(content, dict):
                create_recursive(full_path, content)
            elif content is None:
                full_path.touch()
            else:
                with open(full_path, 'w') as f:
                    f.write(content)

    create_recursive(base_path, PROJECT_STRUCTURE)
    logger.info(f"Created directory structure at {base_path}")

def merge_files(consolidation: Dict, base_path: Path) -> None:
    """Merge files according to consolidation mapping"""
    for component, config in consolidation.items():
        output_path = base_path / config['output']
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        content = []
        for input_file in config['inputs']:
            input_path = base_path / input_file
            if input_path.exists():
                with open(input_path, 'r') as f:
                    content.append(f.read())
        
        if config['merge_strategy'] == 'class_based':
            merged_content = merge_class_based(content, component)
        else:
            merged_content = merge_sequential(content)
        
        with open(output_path, 'w') as f:
            f.write(merged_content)
        
        logger.info(f"Merged {len(config['inputs'])} files into {output_path}")

def merge_class_based(contents: List[str], component: str) -> str:
    """Merge content by combining classes and removing duplicates"""
    # Extract imports
    imports = set()
    for content in contents:
        imports.update(re.findall(r'^(?:from|import).*$', content, re.MULTILINE))
    
    # Extract classes
    classes = {}
    for content in contents:
        for class_match in re.finditer(r'class\s+(\w+).*?(?=class|\Z)', content, re.DOTALL):
            class_name = class_match.group(1)
            if class_name not in classes:
                classes[class_name] = class_match.group(0)
    
    # Combine content
    merged = f"# Generated {component} module\n\n"
    merged += "\n".join(sorted(imports)) + "\n\n"
    merged += "\n".join(classes.values())
    
    return merged

def merge_sequential(contents: List[str]) -> str:
    """Merge content sequentially with duplicate removal"""
    seen_lines = set()
    merged = []
    
    for content in contents:
        for line in content.split('\n'):
            line = line.strip()
            if line and line not in seen_lines:
                seen_lines.add(line)
                merged.append(line)
    
    return "\n".join(merged)

def update_imports(base_path: Path) -> None:
    """Update import statements in all Python files"""
    for py_file in base_path.rglob('*.py'):
        with open(py_file, 'r') as f:
            content = f.read()
        
        # Update import patterns
        content = re.sub(
            r'from \.market_data import IBKRMarketData',
            'from .market_data.connectors.ibkr import IBKRConnector',
            content
        )
        
        with open(py_file, 'w') as f:
            f.write(content)
            
        logger.info(f"Updated imports in {py_file}")

def main():
    """Main reorganization function"""
    try:
        # Create new project directory
        base_path = Path('hft_trading_system_new')
        base_path.mkdir(exist_ok=True)
        
        # Create directory structure
        create_directory_structure(base_path)
        
        # Merge files
        merge_files(FILE_CONSOLIDATION, base_path)
        
        # Update imports
        update_imports(base_path)
        
        # Create README
        with open(base_path / 'README.md', 'w') as f:
            f.write("# HFT Trading System\n\nReorganized project structure.\n")
        
        logger.info("Project reorganization completed successfully")
        
    except Exception as e:
        logger.error(f"Reorganization failed: {e}")
        raise

if __name__ == '__main__':
    main()
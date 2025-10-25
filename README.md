# pycensuskr

A Python package template for Korean census data processing.

## Installation

### From source

```bash
git clone https://github.com/sigmafelix/pycensuskr.git
cd pycensuskr
pip install -e .
```

### For development

```bash
git clone https://github.com/sigmafelix/pycensuskr.git
cd pycensuskr
pip install -e ".[dev]"
```

## Usage

```python
from pycensuskr import __version__
from pycensuskr.core import hello, CensusData

# Print version
print(__version__)

# Use the hello function
print(hello())

# Create a CensusData instance
census = CensusData(data={"region": "Seoul", "population": 9700000})
print(census.get_data())
```

## Development

### Running tests

```bash
pytest
```

### Running tests with coverage

```bash
pytest --cov=pycensuskr --cov-report=html
```

### Code formatting

```bash
black pycensuskr tests
```

### Linting

```bash
flake8 pycensuskr tests
```

### Type checking

```bash
mypy pycensuskr
```

## Project Structure

```
pycensuskr/
├── pycensuskr/          # Main package directory
│   ├── __init__.py      # Package initialization
│   └── core.py          # Core functionality
├── tests/               # Test directory
│   ├── __init__.py
│   └── test_core.py     # Core tests
├── .gitignore           # Git ignore file
├── LICENSE              # MIT License
├── README.md            # This file
├── pyproject.toml       # Modern Python packaging configuration
├── setup.py             # Setup script (for compatibility)
└── requirements-dev.txt # Development dependencies
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
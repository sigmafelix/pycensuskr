# pycensuskr

A Python package template for Korean census data processing.

## Installation

### From source

```bash
git clone https://github.com/sigmafelix/pycensuskr.git
cd pycensuskr
pip install -e .

# python setup.py install
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
from pycensuskr import CensusKR

# Print version
print(__version__)

# Create a CensusData instance
census = CensusKR()

# load specific year data
data_2010 = census.load_data(2010)
print(data_2010)

# load district boundaries for a specific year
districts_2010 = census.load_districts(2010)
print(districts_2010)

# cleaned data with variable types
df_tax_2020 = census.anycensus(year = 2020, type = "tax", aggregator = "sum")

```

## Development

### Running tests

```bash
pytest
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

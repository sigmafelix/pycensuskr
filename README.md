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
from matplotlib import pyplot as plt
import geopandas as gpd

# Print version
print(__version__)

# Create a CensusData instance
census = CensusKR()

# load specific year data
data_2020 = census.load_data(2020)
print(data_2020)

# load district boundaries for a specific year
districts_2020 = census.load_districts(2020)
districts_2020["adm2_re"] = districts_2020["adm2_code"].astype(str).str.slice(0,4)
# aggregate geometries by adm2_re
districts_2020 = districts_2020.dissolve(by="adm2_re", as_index=False)
districts_2020["adm2_code"] = districts_2020["adm2_re"] + "0"
districts_2020["adm2_code"] = districts_2020["adm2_code"].astype(int)

# cleaned data with variable types
df_tax_2020 = census.anycensus(year = 2020, type = "tax", aggregator = "sum")

districts_tax_2020 = districts_2020.merge(df_tax_2020, on="adm2_code")
print(districts_tax_2020)

districts_tax_2020.plot("income_labor_mil")
plt.show()
```

## Development

### Running tests

```bash
pytest
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

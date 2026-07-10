# pycensuskr

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/sigmafelix/pycensuskr/HEAD?urlpath=%2Fdoc%2Ftree%2Fexamples%2Fpycensuskr_example.ipynb)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/pycensuskr?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/pycensuskr)

A Python package for Korean district-level census and geographic data.

## Installation

### PyPI

```bash
pip install pycensuskr
```

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
from pycensuskr import CensusKR
from matplotlib import pyplot as plt
import geopandas as gpd

# Create a CensusData instance
census = CensusKR()

# load specific year data
data_2020 = census.load_data(year = 2020)
print(data_2020)

# load district boundaries for a specific year
districts_2020 = census.load_districts(year = 2020)
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

## Filter non-/autonomous district codes
```python
from pycensuskr import CensusKR

# Create a CensusData instance
census = CensusKR()

# load population data
pop20 = census.anycensus(year=2020, type="population")
pop20_nonauto = census.detect_adm2_type(df=pop20, mode="non")
```


## Notes on data updates
Our data cleaning and processing pipeline is based on the original R package `tidycensuskr`. We periodically synchronize the bundled datasets used in this package with those in R `tidycensuskr` and `tidycensussfkr` to ensure accuracy and relevance. Please refer to the [tidycensuskr webpage](https://github.com/sigmafelix/tidycensuskr) for details on the latest data updates and changes.

## Data license disclaimer

* The data is provided under the [Korea Open Government License Type 1 (Attribution)](https://www.kogl.or.kr/info/license.do) (Note: in Korean). Each raw data table is available for download from the [Public Data Portal](https://www.data.go.kr/) and [KOSIS](https://kosis.kr/) with no cost.

![](resources/kogl_type1.jpg){style="fig-align: center; width: 200px;"}



## Development

### Running tests

```bash
pytest
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

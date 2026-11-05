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
For overlapping city and district observations, `anycensus(adm2_type="all")`
excludes the city count for each indicator with district values while retaining
city and district rates. `"atn"` sums available district counts into the city
and keeps its rate unless weights are supplied; `"non"` returns district rows.
Incomplete district sums produce a warning.

Parent and non-autonomous district codes are compared separately for each
year when the input contains a `year` column.

```python
from pycensuskr import CensusKR

# Create a CensusData instance
census = CensusKR()

# load population data
pop20 = census.anycensus(year=2020, type="population")
pop20_nonauto = census.detect_adm2_type(df=pop20, mode="non")
```

## Load adm3-level data
- ADM3 (_Eup/Myeon/Dong_) boundaries are available through 2025. ADM3 population and housing data is available for 2015, 2020, and 2025; economy and mortality ADM3 data is available for 2020.

ADM2 boundaries are available for 2010, 2015, 2020, and 2025. The 2025 ADM2 layer is based on KOSTAT's 2025 second-quarter boundary file, reference date **2025-06-30**.

```python
from pycensuskr import CensusKR

# Create a CensusData instance
census = CensusKR()

# load population data
pop20_adm3 = census.anycensus(year = 2020, type = "population", level = "adm3")

# load housing data
housing20_adm3 = census.anycensus(year = 2020, type = "housing", level = "adm3")

# load 2025 neighborhood-level housing data (tabular; no 2025 boundaries are bundled)
housing25_adm3 = census.anycensus(year = 2025, type = "housing", level = "adm3")

```


## Notes on data updates
Our data cleaning and processing pipeline is based on the original R package `tidycensuskr`. We periodically synchronize the bundled datasets used in this package with those in R `tidycensuskr` and `tidycensuskr.sf` to ensure accuracy and relevance. Please refer to the [tidycensuskr webpage](https://github.com/sigmafelix/tidycensuskr) for details on the latest data updates and changes.

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

## Supplemental spatial weights

Binary NumPy arrays `w_mat_YYYY.npy` (Queen plus marine road bridges/subsea
 tunnels open by December 31) and `w_mat_o_YYYY.npy` (Queen only) are bundled
for 2010, 2015, 2020 and 2025. Load with `numpy.load(..., allow_pickle=False)`;
the matching `*_order.json` gives the exact `adm2_code_order`. Always align
observations by these codes; arrays have zero diagonals and are not row
standardized. Shapes are 251, 252, 250 and 252 square, respectively.

The boundary GeoPackage is distributed as `pycensuskr/data/boundaries.gpkg.xz`.
`load_districts()` unpacks it to a temporary directory for each call; to use the
GeoPackage directly in other software, decompress the `.xz` file first.

All four ADM2 GeoPackage layers use the validated tidycensuskr boundaries,
with the original fields and row order retained. 2010/2015 overlapping faces
were repaired using their own boundary networks; the 2020 repair uses 2015
historical evidence and 2020 geometry. 2025 contacts match its same-year raw
source. Source holes are retained without evidence for filling. Islands and
unresolved historical contacts are
recorded in the metadata and [connection inventory](pycensuskr/data/sgg_connection_list.md).
See the executed [Moran's I example](examples/v06_spatial_weights_moran.ipynb)
for code alignment, libpysal conversion, and a reproducible permutation test.
Install its optional dependencies with `pip install libpysal esda nbformat nbclient ipykernel`.

The 2025 weight arrays include the confirmed shared-vertex adjacency among
Guro, Yeongdeungpo, Dongjak and Gwanak (all six pairs). Geometry is unchanged;
`w_mat_o_2025` has 646 pairs and `w_mat_2025` has 664. The source geometric
graph has 645 pairs; the documented correction adds Guro–Dongjak only.
See `queen_adjacency_overrides.csv` and `queen_overrides_2025.csv` in package data.

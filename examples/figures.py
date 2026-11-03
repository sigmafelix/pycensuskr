# ---------------------------------------------------------------
# Python (pycensuskr >= 0.3.0)
# ---------------------------------------------------------------
from functools import reduce
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from pycensuskr import CensusKR

census = CensusKR()

# ---- Case 1: choropleth map of the 2020 total population ----
adm2_2020 = census.load_districts(year=2020)          # GeoDataFrame
pop2020   = census.anycensus(year=2020, type="population", level="adm2")

map2020 = adm2_2020.merge(
    pop2020[["adm2_code", "all households_total_per"]],
    on="adm2_code", how="left")

ax = map2020.plot(column="all households_total_per", scheme="quantiles", k=7,
                  cmap="Blues", legend=True, linewidth=0.2, edgecolor="grey",
                  figsize=(7, 8))
ax.set_title("Total population, 2020")
ax.set_axis_off()
plt.show()

# ---- Case 2: PCA of a five-variable socioeconomic profile, 2020 ----
# Each query returns a wide table; aggregated to basic local governments
# (adm2_type = "atn"), summing counts and population-weighting rates.
weighted = dict(aggregator=lambda x, weights: np.average(x, weights=weights),
                weight_type="population",
                weight_column="all households_total_per")
hou  = census.anycensus(year=2020, type="housing",    level="adm2", adm2_type="atn")
pop  = census.anycensus(year=2020, type="population", level="adm2", adm2_type="atn")
pop  = pop.filter(regex="^(adm|year)|^all households")
fert = census.anycensus(year=2020, type="population", level="adm2", adm2_type="atn",
                        **weighted).filter(regex="adm|year|fertility")
mort = census.anycensus(year=2020, type="mortality",  level="adm2", adm2_type="atn",
                        **weighted).drop(columns=["all households_total_per"])
ss   = census.anycensus(year=2020, type="social security", level="adm2")

keys = ["adm1", "adm1_code", "adm2", "adm2_code", "year"]
dfs  = [d.drop(columns=["type"], errors="ignore") for d in [hou, pop, fert, mort, ss]]
for d in dfs:   # weighted queries return string codes; align before joining
    d["adm2_code"] = pd.to_numeric(d["adm2_code"]).astype("Int64")
wide = reduce(lambda l, r: l.merge(r, on=keys, how="left"), dfs)

# Aggregate nonautonomous districts to basic local governments
wide["blg_code"] = wide["adm2_code"].astype(str).str[:4] + "0"
sum_cols  = [c for c in wide.columns
             if any(k in c for k in ["households", "housing", "security"])]
mean_cols = [c for c in wide.columns
             if any(k in c for k in ["fertility", "causes"])]
blg = (wide.groupby("blg_code")
           .agg({**{c: "sum" for c in sum_cols},
                 **{c: "mean" for c in mean_cols},
                 "adm2": "first"})
           .reset_index())

profile = pd.DataFrame({
    "persons_per_housing": blg["all households_total_per"] / blg["housing types_total_cou"],
    "sex_ratio":      100 * blg["all households_male_per"] / blg["all households_female_per"],
    "mortality_rate": blg["all causes_total_per"],
    "fertility_rate": blg["fertility_total_bir"],
    "security_rate":  100 * (blg["basic living security_female_per"]
                             + blg["basic living security_male_per"])
                          / blg["all households_total_per"],
}).dropna()

X   = StandardScaler().fit_transform(profile)
pca = PCA().fit(X)
# Eigenvector signs are arbitrary (R's prcomp and sklearn can disagree);
# fix them so the largest absolute loading of each component is positive
components = pca.components_ * np.sign(
    pca.components_[np.arange(X.shape[1]), np.abs(pca.components_).argmax(axis=1)]
)[:, None]
loadings = pd.DataFrame(components.T,
                        index=profile.columns,
                        columns=[f"PC{i+1}" for i in range(X.shape[1])])
print(loadings.round(3))                 # loadings reported in Table 4
print(pca.explained_variance_ratio_.round(3))

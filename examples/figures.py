# ---------------------------------------------------------------
# Python (pycensuskr >= 0.3.0)
# ---------------------------------------------------------------
from functools import reduce
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
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

ax = map2020.plot(column="all households_total_per", scheme="quantiles", k=5,
                  cmap="Blues", legend=True, linewidth=0.2, edgecolor="grey",
                  figsize=(7, 8),
                  legend_kwds={"fontsize": 12, "frameon": False,
                               "title": "Total population, 2020", "title_fontsize": 12,
                               "alignment": "left", "fmt": "{:,.0f}",
                               "loc": "lower right",
                               "labelspacing": plt.rcParams["legend.labelspacing"] * 1.10})
# Match the tmap map panel while retaining equal map-unit scaling.
ax.set_position([-0.008, 0.0165, 1.016, 0.966])
legend = ax.get_legend()
legend.set_bbox_to_anchor((1.0025, 0.146), transform=ax.figure.transFigure)
for label in legend.get_texts():
    label.set_text(" - ".join(part.strip() for part in label.get_text().split(", ")))
ax.set_axis_off()

# EPSG:5179 is in metres; each alternating segment represents 50 km.
xmin, xmax = ax.get_xlim()
segment = 50_000 / (xmax - xmin)
x, y, height = 0.855 - 2 * segment, 0.1226, 0.0092
for i, color in enumerate(("white", "black")):
    ax.add_patch(Rectangle((x + i * segment, y), segment, height,
                           transform=ax.transAxes, facecolor=color,
                           edgecolor="black", linewidth=1, clip_on=False))
for offset, label in ((0, "0"), (segment, "50"), (2 * segment, "100")):
    ax.text(x + offset, y - 0.008, label, transform=ax.transAxes,
            ha="center", va="top", fontsize=10)
ax.annotate("km", xy=(x + 2 * segment, y - 0.008), xycoords="axes fraction",
            xytext=(12, 0), textcoords="offset points", ha="left", va="top", fontsize=10)

ax.annotate("", xy=(0.95, 0.945), xytext=(0.95, 0.905),
            xycoords="figure fraction", annotation_clip=False,
            arrowprops={"arrowstyle": "-|>", "linewidth": 1.2, "color": "black"})
ax.figure.text(0.95, 0.955, "N", ha="center", va="center", fontsize=11)
plt.show()

# ---- Case 1b: small multiples of population by sex, 2010-2020 ----
# This example uses the same 2020 district grid as tidycensuskr.
grid = pd.read_csv(Path(__file__).with_name("kr_grid_adm2_sgis_2020.csv"),
                   dtype={"code": str})
prov_abbr = {"11": "SE", "21": "BS", "22": "DG", "23": "IC", "24": "GJ",
             "25": "DJ", "26": "UL", "29": "SJ", "31": "GG", "32": "GW",
             "33": "CB", "34": "CN", "35": "JB", "36": "JN", "37": "GB",
             "38": "GN", "39": "JJ"}
duplicate_names = grid["name"].duplicated(keep=False)
grid.loc[duplicate_names, "name"] += (
    " (" + grid.loc[duplicate_names, "code"].str[:2].map(prov_abbr) + ")"
)

pop = census.load_data([2010, 2015, 2020])
pop = pop.loc[(pop["type"] == "population") & (pop["class1"] == "all households") &
              pop["class2"].isin(["female", "male"]) & pop["adm3_code"].isna()].copy()
pop["code"] = (pop["adm2_code"].replace({23030: 23090, 31320: 31280, 34390: 34080})
               .astype(int).astype(str))
pop["value"] /= 1000
missing_codes = sorted(set(pop["code"]) - set(grid["code"]))
if missing_codes:
    print("District codes absent from the 2020 grid:", ", ".join(missing_codes))

fig = plt.figure(figsize=(14, 15))
facets = fig.add_gridspec(int(grid["row"].max()), int(grid["col"].max()),
                          left=0.005, right=0.91, bottom=0.06, top=0.955,
                          wspace=0.08, hspace=0.42)
year_axes = {}
colors = {"female": "#F44336", "male": "#2196F3"}
for district in grid.itertuples(index=False):
    ax = fig.add_subplot(facets[district.row - 1, district.col - 1])
    year_axes[district.col] = ax
    series = pop.loc[pop["code"] == district.code]
    for sex, color in colors.items():
        values = series.loc[series["class2"] == sex].sort_values("year")
        ax.plot(values["year"], values["value"], color=color, alpha=0.5,
                linewidth=2.5 * 72 / 25.4)
    ax.set_title(district.name, fontsize=5, pad=1)
    ax.set_xlim(2009.5, 2020.5)
    ax.set_xticks([2010, 2015, 2020])
    ax.tick_params(axis="x", length=0, labelbottom=False)
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

for ax in year_axes.values():
    for year in (2010, 2015, 2020):
        x = fig.transFigure.inverted().transform(ax.transData.transform((year, 0)))[0]
        fig.text(x, 0.055, str(year), ha="center", va="top", rotation=90, fontsize=7.2)

plot_title = fig.text(0.005, 0.995, "Population trends by district and sex, 2010-2020",
                      ha="left", va="top", fontsize=20)
caption = fig.text(0.995, 0.005, "Y-axis values are not commensurate with the original scale",
                   ha="right", va="bottom", fontsize=20)
fig.text(0.88, 0.55, "Sex", ha="left", va="bottom", fontsize=16, fontweight="bold")
fig.legend(handles=[Line2D([0], [0], color=color, alpha=0.5, linewidth=2.5 * 72 / 25.4,
                           label=sex.capitalize()) for sex, color in colors.items()],
           loc="upper left", bbox_to_anchor=(0.88, 0.54), borderaxespad=0,
           fontsize=16, frameon=False, labelspacing=0.9)
fig.canvas.draw()
renderer = fig.canvas.get_renderer()
for text, fraction in ((plot_title, 0.85), (caption, 0.5)):
    for _ in range(2):
        text.set_fontsize(text.get_fontsize() * fraction * fig.bbox.width /
                          text.get_window_extent(renderer).width)
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

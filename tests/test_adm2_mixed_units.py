import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from pycensuskr import CensusKR


def test_modes_separate_city_counts_and_rates():
    census = CensusKR()
    results = {mode: census.anycensus(2020, codes=["Gyeonggi-do"], type="population", adm2_type=mode)
               for mode in ("all", "atn", "non")}
    def row(mode, code):
        data = results[mode]
        return data.loc[pd.to_numeric(data.adm2_code) == code].iloc[0]

    assert np.isnan(row("all", 31010)["all households_total_per"])
    assert row("all", 31010)["fertility_total_bir"] == pytest.approx(0.796)
    assert row("atn", 31010)["all households_total_per"] == sum(
        row("all", code)["all households_total_per"] for code in range(31011, 31015)
    )
    assert row("atn", 31010)["fertility_total_bir"] == pytest.approx(0.796)
    assert 31010 not in pd.to_numeric(results["non"].adm2_code).values
    assert set(range(31011, 31015)).issubset(pd.to_numeric(results["non"].adm2_code))

    for mode in ("all", "atn", "non"):
        actual = census.anycensus(2020, codes=[31010], type="population", adm2_type=mode)
        target_codes = list(range(31011, 31015)) if mode == "non" else [31010]
        target = results[mode][pd.to_numeric(results[mode].adm2_code).isin(target_codes)]
        cols = ["adm2_code", "all households_total_per", "fertility_total_bir"]
        assert_frame_equal(actual[cols].sort_values("adm2_code").reset_index(drop=True),
                           target[cols].sort_values("adm2_code").reset_index(drop=True))


@pytest.mark.parametrize("mode", ["all", "atn", "non"])
def test_province_counts_and_weighted_rates_do_not_double_count(mode):
    census = CensusKR()
    count = census.anycensus(2020, codes=["Gyeonggi-do"], type="population", level="adm1", adm2_type=mode)
    assert count["all households_total_per"].iloc[0] == 12930625
    rate = census.anycensus(2020, codes=["Gyeonggi-do"], type="mortality", level="adm1", adm2_type=mode,
                            weight_type="population", aggregator=lambda v, weights: np.average(v, weights=weights))
    assert rate["all households_total_per"].iloc[0] == 12930625
    assert rate["all causes_total_per"].iloc[0] == pytest.approx(285.992614)


def test_partial_gu_count_replaces_source_city_with_warning():
    data = pd.DataFrame({"year": [2020]*3, "type": ["population"]*3,
                         "adm1": ["Seoul"]*3, "adm1_code": [11]*3,
                         "adm2": ["Example-si", "A-gu Example-si", "B-gu Example-si"],
                         "adm2_code": [11010, 11011, 11012],
                         "count": [999, 10, 20], "rate": [5, 6, 8]})
    refs = {(2020, "11010"): {"11011", "11012", "11013"}}
    with pytest.warns(UserWarning, match="incomplete set"):
        result = CensusKR()._collapse_to_atn(data, refs, rate_columns={"rate"})
    assert result["count"].iloc[0] == 30
    assert result["rate"].iloc[0] == 5


def test_multiple_years_filter_within_same_year():
    census = CensusKR()
    for mode in ("all", "atn", "non"):
        kw = dict(codes=["Gyeonggi-do"], type="population", adm2_type=mode)
        both = census.anycensus([2015, 2020], **kw)
        separate = pd.concat([census.anycensus(y, **kw) for y in (2015, 2020)])
        cols = ["year", "adm2_code", "all households_total_per", "fertility_total_bir"]
        assert_frame_equal(both[cols].sort_values(cols[:2]).reset_index(drop=True),
                           separate[cols].sort_values(cols[:2]).reset_index(drop=True),
                           check_dtype=False)


def test_overlap_is_per_indicator_and_year_with_duplicate_input_index():
    records = []
    def add(year, code, label, category, unit, value):
        records.append({"year": year, "type": "population", "adm1": "Gyeonggi-do",
                        "adm1_code": 31, "adm2": label, "adm2_code": code,
                        "adm3": None, "adm3_code": None, "class1": category,
                        "class2": "total", "unit": unit, "value": value})
    add(2015, 31010, "Suwon-si", "people", "persons", 50)
    for code, name, count, rate in [(31010, "Suwon-si", 100, 1.2),
                                     (31011, "A-gu Suwon-si", 40, 0.9),
                                     (31012, "B-gu Suwon-si", 60, 1.1)]:
        add(2020, code, name, "people", "persons", count)
        add(2020, code, name, "fertility", "births per woman", rate)
    add(2020, 31010, "Suwon-si", "city-only", "persons", 7)
    source = pd.DataFrame(records, index=[0, 1, 1, 2, 2, 3, 3, 4])
    census = CensusKR()
    census.load_data = lambda year: source
    out = census.anycensus([2015, 2020], type="population", adm2_type="all")
    city15 = out[(out.year == 2015) & (out.adm2_code == 31010)].iloc[0]
    city20 = out[(out.year == 2020) & (out.adm2_code == 31010)].iloc[0]
    assert city15["people_total_per"] == 50
    assert np.isnan(city20["people_total_per"])
    assert city20["city-only_total_per"] == 7
    assert city20["fertility_total_bir"] == pytest.approx(1.2)


def test_count_only_city_can_produce_empty_all_result_with_schema():
    out = CensusKR().anycensus(2020, codes=[31010], type="landuse", adm2_type="all")
    assert out.empty
    assert "park_neighborhood_parks_cou" in out.columns


def test_weighted_single_city_uses_gu_weights():
    result = CensusKR().anycensus(
        2020, codes=[31010], type="mortality", adm2_type="atn",
        weight_type="population", aggregator=lambda values, weights: np.average(values, weights=weights),
    )
    assert result["all households_total_per"].iloc[0] == 1156179
    assert result["all causes_total_per"].iloc[0] == pytest.approx(289.177403)

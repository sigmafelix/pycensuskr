import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from pycensuskr import CensusKR


def test_detect_adm2_type_filters_each_year_and_preserves_order_and_index():
    data = pd.DataFrame(
        {"year": [2020, 2015, 2010, 2015, 2020, 2015],
         "adm2_code": [31050, 31050, 29010, 31051, 31010, 31052]},
        index=[9, 1, 9, 2, 7, 2],
    )
    census = CensusKR()
    assert_frame_equal(census.detect_adm2_type(data, mode="non"), data.iloc[[0, 2, 3, 4, 5]])
    assert_frame_equal(census.detect_adm2_type(data, mode="atn"), data.iloc[[0, 1, 2, 4]])
    assert_frame_equal(census.detect_adm2_type(data, year=2015, mode="non"), data.iloc[[3, 5]])


def test_non_warns_when_parent_exists_only_in_another_year():
    data = pd.DataFrame({"year": [2015, 2020], "adm2_code": [31050, 31051]})
    with pytest.warns(UserWarning, match="do not have corresponding upper level"):
        result = CensusKR().detect_adm2_type(data, mode="non")
    assert_frame_equal(result, data)


def test_non_supports_missing_year_and_data_without_year_column():
    census = CensusKR()
    data = pd.DataFrame({"year": [2015, np.nan, np.nan], "adm2_code": [31050, 31050, 31051]})
    assert_frame_equal(census.detect_adm2_type(data, mode="non"), data.iloc[[0, 2]])
    assert_frame_equal(census.detect_adm2_type(data.drop(columns="year"), mode="non"),
                       data.iloc[[2]].drop(columns="year"))
    assert_frame_equal(census.detect_adm2_type(data.iloc[:0], mode="non"), data.iloc[:0])
    data["year"] = pd.Categorical(data["year"], categories=[2015, 2020])
    assert_frame_equal(census.detect_adm2_type(data, mode="non"), data.iloc[[0, 2]])


@pytest.mark.parametrize("mode", ["atn", "non"])
@pytest.mark.parametrize("level", ["adm2", "adm1"])
def test_anycensus_multiple_years_matches_separate_queries(mode, level):
    census = CensusKR()
    args = dict(codes=["Gyeonggi-do"], type="population", level=level, adm2_type=mode)
    combined = census.anycensus(year=[2015, 2020], **args)
    separate = pd.concat([census.anycensus(year=year, **args) for year in [2015, 2020]])
    sort_cols = ["year", "adm2_code"] if level == "adm2" else ["year"]
    assert_frame_equal(combined.sort_values(sort_cols).reset_index(drop=True),
                       separate.sort_values(sort_cols).reset_index(drop=True))
    if level == "adm2" and mode == "non":
        codes = pd.to_numeric(combined["adm2_code"])
        assert ((combined["year"] == 2020) & (codes == 31050)).sum() == 1
        assert not ((combined["year"] == 2015) & (codes == 31050)).any()

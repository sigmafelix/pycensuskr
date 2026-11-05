"""
Test suite for pycensuskr package.
"""

from pycensuskr import __version__
from pycensuskr.pycensuskr import CensusKR
import geopandas
import numpy as np
import pandas as pd
import pytest

def test_version():
    """Test that version is defined and is a string."""
    assert __version__
    assert isinstance(__version__, str)
    assert __version__ == "0.4.2"


def test_get_version():
    """Test the get_version function."""
    version = __version__
    assert version == "0.4.2"


class TestCensusData:
    """Tests for the CensusData class."""

    # def test_init_empty(self):
    #     """Test initialization without data."""
    #     census = CensusKR()
    #     assert census.get_data() == {}

    def test_load_data(self):
        """Test initialization with data."""
        census = CensusKR()
        # should be edited
        assert census.load_data(2010) is not None

    # def test_set_data(self):
    #     """Test setting data."""
    #     census = CensusKR()

    def test_load_districts(self):
        """Test getting data."""
        test_data = {"region": "Seoul"}
        census = CensusKR()
        retrieved_data = census.load_districts(2020)
        assert isinstance(retrieved_data, geopandas.GeoDataFrame)


class TestDetectAdm2Type:
    """Tests for detect_adm2_type behavior."""

    def test_detect_adm2_type_non(self):
        census = CensusKR()
        df = pd.DataFrame(
            {
                "year": [2020, 2020, 2020, 2020],
                "adm2_code": ["11110", "11111", "22220", "33331"],
            }
        )

        with pytest.warns(UserWarning, match="Inconsistent codes"):
            out = census.detect_adm2_type(df, mode="non")
        assert set(out["adm2_code"]) == {"11111", "22220", "33331"}

    def test_detect_adm2_type_atn(self):
        census = CensusKR()
        df = pd.DataFrame(
            {
                "year": [2020, 2020, 2020],
                "adm2_code": ["11110", "11111", "22220"],
            }
        )

        out = census.detect_adm2_type(df, mode="atn")
        assert set(out["adm2_code"]) == {"11110", "22220"}

    def test_detect_adm2_type_atn_float_codes(self):
        # adm2_code is float in the bundled data (e.g. 31011.0)
        census = CensusKR()
        df = pd.DataFrame({"adm2_code": [31010.0, 31011.0, 31012.0, 11010.0]})

        out = census.detect_adm2_type(df, mode="atn")
        assert set(out["adm2_code"]) == {31010.0, 11010.0}

    def test_detect_adm2_type_year_filter(self):
        census = CensusKR()
        df = pd.DataFrame(
            {
                "year": [2015, 2020, 2020],
                "adm2_code": ["11110", "11110", "11111"],
            }
        )

        out = census.detect_adm2_type(df, year=2015, mode="atn")
        assert len(out) == 1
        assert out.iloc[0]["year"] == 2015
        assert out.iloc[0]["adm2_code"] == "11110"

    def test_detect_adm2_type_invalid_mode_raises(self):
        census = CensusKR()
        df = pd.DataFrame({"adm2_code": ["11110"]})

        with pytest.raises(ValueError, match="mode must be 'atn' or 'non'"):
            census.detect_adm2_type(df, mode="auto")

    def test_detect_adm2_type_missing_column_raises(self):
        census = CensusKR()
        df = pd.DataFrame({"other_code": ["11110"]})

        with pytest.raises(KeyError, match="adm2_code"):
            census.detect_adm2_type(df)


class TestAnycensusWeighted:
    def test_weight_type_query_with_default_codes(self):
        # mortality adm2_code is float; default codes must not leak into the weight query
        census = CensusKR()
        out = census.anycensus(
            2020, type="mortality", level="adm2", adm2_type="atn",
            aggregator=lambda x, weights: np.average(x, weights=weights),
            weight_type="population", weight_column="all households_total_per",
        )
        assert len(out) > 0
        assert out["all households_total_per"].notna().all()

    def test_adm2_query_excludes_adm3_rows(self):
        # Jongno-gu all-cause mortality (2020) must not be summed with its dong rows
        census = CensusKR()
        out = census.anycensus(2020, codes=[11010], type="mortality", level="adm2")
        assert out["all causes_total_per"].iloc[0] == pytest.approx(261.7)

    def test_weighted_atn_recalculates_parent_from_children(self):
        # Suwon-si (31010) mortality = population-weighted mean of its four gu
        census = CensusKR()
        out = census.anycensus(
            2020, type="mortality", level="adm2", adm2_type="atn",
            aggregator=lambda x, weights: np.average(x, weights=weights),
            weight_type="population", weight_column="all households_total_per",
        )
        codes = pd.to_numeric(out["adm2_code"]).astype(int)
        assert not codes.between(31011, 31019).any()
        suwon = out.loc[codes == 31010, "all causes_total_per"].iloc[0]
        assert suwon == pytest.approx(289.177, abs=0.001)


class TestAtnMissingParents:
    # medicine reports only the Gu of cities such as Suwon-si (31011-31014)
    COL = "doctors_anesthesiology and pain medicine_per"

    def test_atn_rebuilds_city_from_gu_rows(self):
        census = CensusKR()
        out = census.anycensus(2020, type="medicine", level="adm2", adm2_type="atn")
        codes = pd.to_numeric(out["adm2_code"]).astype(int)
        suwon = out.loc[codes == 31010]
        assert len(suwon) == 1
        assert suwon["adm2"].iloc[0] == "Suwon-si"
        assert suwon[self.COL].iloc[0] == 16 + 11 + 45 + 44
        assert not codes.between(31011, 31019).any()

    def test_atn_adm1_keeps_gu_only_cities(self):
        census = CensusKR()
        atn = census.anycensus(2020, type="medicine", level="adm1", adm2_type="atn")
        with pytest.warns(UserWarning, match="Inconsistent codes"):
            non = census.anycensus(2020, type="medicine", level="adm1", adm2_type="non")
        gyeonggi = lambda d: d.loc[d["adm1_code"] == 31, self.COL].iloc[0]
        assert gyeonggi(atn) == gyeonggi(non) == 998

    def test_weighted_atn_keeps_gu_only_cities(self):
        census = CensusKR()
        out = census.anycensus(
            2020, type="medicine", level="adm2", adm2_type="atn",
            aggregator=lambda x, weights: np.average(x, weights=weights),
            weight_type="population",
        )
        assert (pd.to_numeric(out["adm2_code"]).astype(int) == 31010).any()


class TestAdm2TypeMultiYear:
    def test_non_keeps_city_after_gu_abolition(self):
        # Bucheon-si (31050) abolished its Gu in 2016; 2010 Gu must not drop 2020
        census = CensusKR()
        out = census.anycensus([2010, 2020], type="population", adm2_type="non")
        codes = pd.to_numeric(out["adm2_code"]).astype(int)
        assert ((out["year"] == 2020) & (codes == 31050)).any()
        assert not ((out["year"] == 2010) & (codes == 31050)).any()


class TestAtnVariableRules:
    """adm2_type='atn' resolves each city with Gu variable by variable."""

    @staticmethod
    def value(df, code, col):
        return df.loc[pd.to_numeric(df["adm2_code"]).astype(int) == code, col].iloc[0]

    def test_count_uses_gu_sum_when_city_row_is_averaged(self):
        # landuse city rows hold the mean of their Gu (Suwon-si: 89 = 356 / 4)
        census = CensusKR()
        out = census.anycensus(2020, type="landuse", adm2_type="atn")
        assert self.value(out, 31010, "park_neighborhood_parks_cou") == 356

    def test_count_uses_gu_sum_when_city_row_is_zero(self):
        # Bucheon-si 2015 medicine city row is all zeros
        census = CensusKR()
        out = census.anycensus(2015, type="medicine", adm2_type="atn")
        assert self.value(out, 31050, "doctors_anesthesiology and pain medicine_per") == 48 + 19 + 2

    def test_count_fills_variable_missing_from_city_row(self):
        # Seongnam-si 2015: population only in its Gu, fertility rate in the city row
        census = CensusKR()
        out = census.anycensus(2015, type="population", adm2_type="atn")
        assert self.value(out, 31020, "all households_total_per") == 918710
        assert self.value(out, 31020, "fertility_total_bir") == pytest.approx(1.159)

    def test_partial_gu_set_warns(self):
        # Cheongju-si 2015 environment has 2 of its 4 Gu
        census = CensusKR()
        with pytest.warns(UserWarning, match="incomplete set of non-autonomous Gu"):
            out = census.anycensus(2015, type="environment", adm2_type="atn")
        assert self.value(out, 33040, "organic_matter_discharge_kg_") == 892

    def test_weighted_query_sums_counts_and_recalculates_rates(self):
        census = CensusKR()
        out = census.anycensus(
            2020, type="population", adm2_type="atn",
            aggregator=lambda x, weights: np.average(x, weights=weights),
            weight_type="population",
        )
        assert self.value(out, 31010, "all households_male_per") == 576792
        assert self.value(out, 31010, "fertility_total_bir") == pytest.approx(0.787, abs=1e-3)

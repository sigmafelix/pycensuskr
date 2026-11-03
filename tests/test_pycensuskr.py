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
    assert __version__ == "0.4.1"


def test_get_version():
    """Test the get_version function."""
    version = __version__
    assert version == "0.4.1"


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

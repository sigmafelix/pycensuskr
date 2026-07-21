"""
Test suite for pycensuskr package.
"""

from pycensuskr import __version__
from pycensuskr.pycensuskr import CensusKR
import geopandas
import pandas as pd
import pytest

def test_version():
    """Test that version is defined and is a string."""
    assert __version__
    assert isinstance(__version__, str)
    assert __version__ == "0.3.0"


def test_get_version():
    """Test the get_version function."""
    version = __version__
    assert version == "0.3.0"


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

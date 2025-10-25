"""
Test suite for pycensuskr package.
"""

from pycensuskr import __version__
from pycensuskr.pycensuskr import CensusKR
import geopandas

def test_version():
    """Test that version is defined and is a string."""
    assert __version__
    assert isinstance(__version__, str)
    assert __version__ == "0.1.0"


def test_get_version():
    """Test the get_version function."""
    version = __version__
    assert version == "0.1.0"


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

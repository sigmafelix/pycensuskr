"""
Test suite for pycensuskr package.
"""

from pycensuskr import __version__
from pycensuskr.pycensuskr import hello, get_version, CensusData


def test_version():
    """Test that version is defined and is a string."""
    assert __version__
    assert isinstance(__version__, str)
    assert __version__ == "0.1.0"


def test_hello():
    """Test the hello function."""
    result = hello()
    assert isinstance(result, str)
    assert result == "Hello from pycensuskr!"


def test_get_version():
    """Test the get_version function."""
    version = get_version()
    assert version == "0.1.0"


class TestCensusData:
    """Tests for the CensusData class."""

    def test_init_empty(self):
        """Test initialization without data."""
        census = CensusData()
        assert census.get_data() == {}

    def test_init_with_data(self):
        """Test initialization with data."""
        test_data = {"key": "value"}
        census = CensusData(data=test_data)
        assert census.get_data() == test_data

    def test_set_data(self):
        """Test setting data."""
        census = CensusData()
        test_data = {"population": 50000000}
        census.set_data(test_data)
        assert census.get_data() == test_data

    def test_get_data(self):
        """Test getting data."""
        test_data = {"region": "Seoul"}
        census = CensusData(data=test_data)
        retrieved_data = census.get_data()
        assert retrieved_data == test_data

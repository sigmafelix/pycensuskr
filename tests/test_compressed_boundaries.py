import pytest
from pycensuskr import CensusKR


@pytest.mark.parametrize(
    ("level", "year", "count"),
    [("adm2", 2010, 251), ("adm2", 2015, 252),
     ("adm2", 2020, 250), ("adm2", 2025, 252),
     ("adm3", 2010, 3472), ("adm3", 2015, 3496),
     ("adm3", 2020, 3501), ("adm3", 2025, 3559)],
)
def test_compressed_boundary_layers(level, year, count):
    boundaries = CensusKR().load_districts(year, level)
    assert len(boundaries) == count
    assert boundaries.crs.to_epsg() == 5179
    assert list(boundaries.columns) == (
        ["year", "adm2_code", "geometry"] if level == "adm2"
        else ["adm3_code", "adm3_name_kr", "geometry"]
    )

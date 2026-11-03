"""Integrity and geometry alignment of bundled supplemental weights."""
from importlib.resources import files
import json
import numpy as np
import pytest
import shapely
from pycensuskr import CensusKR

DATA = files('pycensuskr').joinpath('data')

@pytest.mark.parametrize('year,n', [(2010,251),(2015,252),(2020,250),(2025,252)])
def test_weights(year,n):
    x = CensusKR().load_districts(year)
    geoms = x.geometry.to_numpy()
    assert x.geometry.is_valid.all()
    assert shapely.coverage_is_valid(geoms)
    pairs = []
    for prefix in ('w_mat_', 'w_mat_o_'):
        name = f'{prefix}{year}'
        a = np.load(str(DATA.joinpath(name+'.npy')), allow_pickle=False)
        meta = json.loads(DATA.joinpath(name+'_order.json').read_text())
        codes = meta['adm2_code_order']
        assert a.dtype == np.int8 and a.shape == (n,n)
        assert len(codes) == len(set(codes)) == n
        assert np.isin(a,[0,1]).all() and not a.diagonal().any()
        assert np.array_equal(a,a.T)
        assert CensusKR().load_districts(year).adm2_code.astype(str).tolist() == codes
        pairs.append((a,codes))
    assert pairs[0][1] == pairs[1][1]
    assert (pairs[0][0] >= pairs[1][0]).all()
    expected = shapely.touches(geoms[:,None],geoms[None,:])
    if year == 2025:
        ids = [pairs[1][1].index(c) for c in ('11170','11190','11200','11210')]
        assert not expected[ids[0],ids[2]]
        expected[ids[0],ids[2]] = expected[ids[2],ids[0]] = True
        upper = np.triu_indices(4,1)
        for matrix,_ in pairs:
            assert matrix[np.ix_(ids,ids)][upper].all()
        assert pairs[1][0].sum()//2 == 646
        assert pairs[0][0].sum()//2 == 664
    assert np.array_equal(pairs[1][0], expected)


def test_2020_repaired_queen_and_moran():
    pytest.importorskip("libpysal")
    pytest.importorskip("esda")
    from libpysal.weights import full2W
    from esda import Moran
    x = CensusKR().load_districts(2020)
    assert x.geometry.is_valid.all()
    geoms = x.geometry.to_numpy()
    assert not shapely.overlaps(geoms[:,None],geoms[None,:]).any()
    queen = np.load(str(DATA.joinpath('w_mat_o_2020.npy')), allow_pickle=False)
    assert np.array_equal(queen,shapely.touches(geoms[:,None],geoms[None,:]))
    ids = x.adm2_code.astype(str).tolist()
    code_set = {'11170','11190','11200','11210'}
    junction = shapely.intersection_all(geoms[np.isin(ids,list(code_set))])
    assert junction.geom_type == 'Point' and not junction.is_empty
    w = full2W(queen,ids=ids,silence_warnings=True)
    assert w.id_order == ids and len(w.islands) == 8
    y = np.arange(len(ids),dtype=float)
    np.random.seed(2020)
    result = Moran(y,w,permutations=9)
    assert np.isfinite(result.I)

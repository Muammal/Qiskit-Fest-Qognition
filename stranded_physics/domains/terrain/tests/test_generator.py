import numpy as np
import pytest
from scipy.ndimage import label
from stranded_physics.core.api import InterfaceError, GridSpec
from stranded_physics.core.fields import FieldStore, ScopedFields
from stranded_physics.domains.terrain.generator import GeneratedTerrain, sample_island
from stranded_physics.domains.terrain.model import ST_VINCENT_GRID
from stranded_physics.domains.terrain.drainage import route, share_draining_out


def pytest_generate_tests(metafunc):
    # Required duplicate test basenames need path-based imports during joint collection.
    metafunc.config.option.importmode = "importlib"


def build(seed, summit=1000, area=100):
    model = GeneratedTerrain(ST_VINCENT_GRID,(697000.,1471000.),summit,area)
    store = FieldStore()
    model.run(ScopedFields(store,model.id,model.inputs,model.outputs),np.random.default_rng(seed))
    return model,store


@pytest.mark.parametrize("summit,area",[(100,10),(3000,250),(1700,137)])
def test_geometry(summit,area):
    model,store = build(18,summit,area)
    _,again = build(18,summit,area)
    for name in store.names():
        np.testing.assert_array_equal(store.stored(name).data,again.stored(name).data)
    z = store.get("terrain.elevation","m")
    land = store.get("terrain.land_mask","dimensionless")>0
    assert label(land)[1]==1
    assert not (land[0].any() or land[-1].any() or land[:,0].any() or land[:,-1].any())
    assert abs(land.sum()*ST_VINCENT_GRID.dx_m**2/1e6/area-1)<.05
    assert z.max()==pytest.approx(summit)
    assert share_draining_out(route(z,land,ST_VINCENT_GRID.dx_m),land)==1
    assert model.summit_xy is not None


def test_refusals_and_catalogue():
    with pytest.raises(InterfaceError):
        build(0,99,100)
    model = GeneratedTerrain(GridSpec("EPSG:32620",0,1000,100,10,10),(500,500),1000,100)
    assert model.check_validity(None)
    assert sample_island(np.random.default_rng(8))==sample_island(np.random.default_rng(8))
    assert not np.array_equal(build(1)[1].get("terrain.elevation","m"),build(2)[1].get("terrain.elevation","m"))

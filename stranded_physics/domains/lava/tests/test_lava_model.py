from datetime import datetime, timezone
import numpy as np
import pytest
from stranded_physics.core.api import GridSpec, TimeAxis, InterfaceError
from stranded_physics.core.fields import FieldStore

def setup():
    return GridSpec("EPSG:32620", -150., 150., 100., 3, 3), TimeAxis(datetime(2021,4,8,tzinfo=timezone.utc), 60., 3)


from stranded_physics.domains.lava.model import Lava, SETTINGS, huppert_radius_m, dome_radius_m, dome_volume_m3

def test_spreading_and_volume():
    assert huppert_radius_m(2,1e5,400)/huppert_radius_m(2,1e5,100) == pytest.approx(2)
    assert huppert_radius_m(16,1e5,100)/huppert_radius_m(2,1e5,100) == pytest.approx(8**(3/8))
    assert dome_volume_m3(2,100) == 200
    assert dome_radius_m(100,1,1e9) == SETTINGS["max_dome_radius"]
    with pytest.raises(InterfaceError):
        huppert_radius_m(1,0,1)

def test_destroyed_at_current_frame_and_never_regrows():
    grid,time = setup()
    for events in ([0,1,0],[0,0,1]):
        store=FieldStore()
        store.put("eruption.explosion",np.array(events),"dimensionless",time=time)
        Lava(grid,time,(0,0)).run(store,np.random.default_rng(1))
        frames=store.get("lava.footprint","dimensionless")
        assert frames[0].sum() > 0
        assert frames[np.flatnonzero(events)[0]:].sum() == 0
    store=FieldStore()
    store.put("eruption.explosion",np.zeros(3),"dimensionless",time=time)
    Lava(grid,time,(0,0),grown_before_s=0).run(store,np.random.default_rng(1))
    assert store.get("lava.footprint","dimensionless")[0].sum() == 0

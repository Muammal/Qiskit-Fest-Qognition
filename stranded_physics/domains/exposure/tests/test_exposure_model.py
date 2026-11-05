from datetime import datetime, timezone
import numpy as np
import pytest
from stranded_physics.core.api import GridSpec, TimeAxis, InterfaceError
from stranded_physics.core.fields import FieldStore

def setup():
    return GridSpec("EPSG:32620", -150., 150., 100., 3, 3), TimeAxis(datetime(2021,4,8,tzinfo=timezone.utc), 60., 3)


from stranded_physics.domains.exposure.model import Exposure, SETTINGS, roof_failure_fraction, flow_death_probability, ash_energy_cost_per_hour

def test_fragility_and_shelter():
    median=SETTINGS["roof_collapse_load"]
    assert roof_failure_fraction(median) == pytest.approx(.5)
    values=roof_failure_fraction(np.array([0,median/2,median,median*2,median*1e6]))
    assert values[0] == 0
    assert np.all(np.diff(values)>0)
    assert values[-1] <= 1
    assert flow_death_probability(True) < flow_death_probability(False)
    assert ash_energy_cost_per_hour(100,True) < ash_energy_cost_per_hour(100,False)
    assert ash_energy_cost_per_hour(1e9,False) == SETTINGS["ash_fatigue_per_hour"]
    with pytest.raises(InterfaceError):
        roof_failure_fraction(-1)

def test_frame_local_load():
    grid,time=setup()
    store=FieldStore()
    load=np.array([np.zeros((3,3)),np.full((3,3),SETTINGS["roof_collapse_load"]),np.full((3,3),1000)])
    store.put("tephra.deposit_load",load,"kg/m**2",grid,time)
    Exposure(grid,time).run(store,np.random.default_rng(1))
    frames=store.get("exposure.roof_failure","dimensionless")
    assert np.all(frames[0]==0)
    assert np.all(frames[1]==.5)
    assert np.all(frames[2]>.5)

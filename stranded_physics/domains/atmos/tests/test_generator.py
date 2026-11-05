from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pytest
from stranded_physics.core.api import TimeAxis, InterfaceError
from stranded_physics.core.fields import FieldStore, ScopedFields
from stranded_physics.domains.atmos.generator import WeatherWindow, WeatherDials, ISLANDS

RAW = Path(__file__).resolve().parents[4] / "artifacts/physics/raw/atmos"
HAS_RAW = RAW.is_dir() and any(RAW.iterdir())
needs_raw = pytest.mark.skipif(not HAS_RAW, reason="raw data is not held in this checkout")
AXIS = TimeAxis(datetime(2000,1,1,tzinfo=timezone.utc),7200,8)


def pytest_generate_tests(metafunc):
    # Required duplicate test basenames need path-based imports during joint collection.
    metafunc.config.option.importmode = "importlib"


def run(model,seed=1):
    store = FieldStore()
    model.run(ScopedFields(store,model.id,model.inputs,model.outputs),np.random.default_rng(seed))
    return store


@needs_raw
@pytest.mark.parametrize("island",ISLANDS)
def test_windows(island):
    a,b = WeatherWindow(AXIS,island,12),WeatherWindow(AXIS,island,12)
    sa,sb = run(a),run(b)
    assert a.window_start_utc.month==12
    for name in sa.names():
        np.testing.assert_array_equal(sa.stored(name).data,sb.stored(name).data)
        assert sa.stored(name).time==AXIS


def test_dials():
    store = run(WeatherDials(AXIS,200,80,360,-40,120,360))
    assert np.all(store.get("atmos.rain_rate","mm/h")==200)
    assert np.all(store.get("atmos.wind_speed_200hpa","m/s")==120)
    for args in [(-1,0,0,0,0,0),(0,81,0,0,0,0),(0,0,361,0,0,0),(0,0,0,51,0,0),(0,0,0,0,121,0),(0,0,0,0,0,-1)]:
        with pytest.raises(InterfaceError):
            WeatherDials(AXIS,*args)


def test_refusals():
    for island,month in [("unknown",None),("st_vincent",0),("st_vincent",13)]:
        with pytest.raises(InterfaceError):
            WeatherWindow(AXIS,island,month)
    for dt,n in [(1800,5),(3600,8761)]:
        with pytest.raises(InterfaceError):
            WeatherWindow(TimeAxis(AXIS.t0_utc,dt,n),"st_vincent")


@needs_raw
@pytest.mark.parametrize("last",[False,True])
def test_year_edges_match_raw(last):
    import json
    class Edge:
        def integers(self,n):
            return n-1 if last else 0
    axis = TimeAxis(AXIS.t0_utc,10800,5)
    model = WeatherWindow(axis,"st_vincent")
    store = FieldStore()
    model.run(ScopedFields(store,model.id,model.inputs,model.outputs),Edge())
    assert model.window_start_utc.year==2023
    raw = json.loads(model.files["surface"][0].read_text())["hourly"]
    i = raw["time"].index(model.window_start_utc.strftime("%Y-%m-%dT%H:%M"))
    expected = [raw["precipitation"][i]] + [sum(raw["precipitation"][i+3*k-j] for j in range(3))/3 for k in range(1,5)]
    np.testing.assert_allclose(store.get("atmos.rain_rate","mm/h"),expected,rtol=0,atol=1e-14)


def test_changed_file_is_refused(tmp_path):
    model = WeatherWindow(AXIS,"st_vincent")
    changed = tmp_path/"changed.json"
    changed.write_text("{}")
    model.files["surface"] = changed,model.files["surface"][1]
    assert model.check_validity(None)
    with pytest.raises(InterfaceError):
        run(model)

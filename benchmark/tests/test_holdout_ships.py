"""Build physics packs only; never execute passenger minds."""
from datetime import datetime, timedelta
from pathlib import Path
import re
import tomllib

import numpy as np
import pytest

from stranded_physics.entities.api import load_scenario
from stranded_physics.entities.build import to_spec
from stranded_physics.packs.builder import build_pack


SCENARIOS = Path(__file__).resolve().parents[1] / "scenarios"
# Elinder and Erixson 2012, PNAS 109(33):13220, Table 1.
CASES = [
    ("principessa_mafalda_1927", 1186, 27.0, 295, 0, "1927-10-25T17:15:00+00:00", 26),
    ("admiral_nakhimov_1986", 1243, 47.9, 7, 0, "1986-08-31T23:12:00+00:00", 24),
]


@pytest.mark.parametrize("event,aboard,women_share,expected,order,impact_local,water_c", CASES)
def test_holdout_builds_and_sinks_on_time(event, aboard, women_share, expected, order, impact_local, water_c):
    path = SCENARIOS / f"{event}.toml"
    text = path.read_text(encoding="utf-8")
    sink_minutes = float(re.search(r"^# sink_minutes = ([\d.]+)$", text, re.M)[1])
    assert sink_minutes == pytest.approx(expected)
    scenario = load_scenario(path)
    assert all(e.source == "dials" for e in scenario.entities)
    assert {e.kind for e in scenario.entities} == {
        "ship", "breach", "lifeboats", "sea", "weather", "passengers"
    }
    cohorts = [e for e in scenario.entities if e.kind == "passengers"]
    assert sum(e.settings[k] for e in cohorts for k in ("men", "women", "children")) == aboard
    passengers = [e for e in cohorts if not e.name.startswith("crew")]
    pax_count = sum(e.settings[k] for e in passengers for k in ("men", "women", "children"))
    assert sum(e.settings["women"] for e in passengers) == round(pax_count * women_share / 100)
    boats = next(e for e in scenario.entities if e.kind == "lifeboats")
    assert boats.settings["women_first"] == order
    breach = next(e for e in scenario.entities if e.kind == "breach")
    step_minutes = scenario.step_s / 60
    assert sink_minutes / step_minutes >= 10
    assert breach.settings["impact_minutes"] / step_minutes >= 10
    data = tomllib.loads(text)
    impact = datetime.fromisoformat(data["start_utc"]) + timedelta(
        minutes=breach.settings["impact_minutes"], hours=data["local_utc_offset"]
    )
    assert abs((impact - datetime.fromisoformat(impact_local)).total_seconds()) <= scenario.step_s
    sea = next(e for e in scenario.entities if e.kind == "sea")
    assert sea.settings["temperature_c"] == water_c
    spec = to_spec(scenario)
    ship = next(d for d in spec.domains if d.id == "ship")
    assert ship.recorded_sinking is None
    pack = build_pack(spec, seed=1)
    sunk = np.flatnonzero(pack.series("ship.afloat") <= 0)
    assert sunk.size, "ship never sinks within the scenario horizon"
    elapsed = sunk[0] * step_minutes - breach.settings["impact_minutes"]
    assert abs(elapsed - sink_minutes) <= step_minutes + 1e-8
    assert np.all(pack.series("ship.afloat")[sunk[0]:] <= 0)

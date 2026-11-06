"""Calibration inputs and flooding only; no minds are run."""
from pathlib import Path
import re
import tomllib
from datetime import datetime, timedelta

import numpy as np
import pytest

from stranded_physics.entities.api import load_scenario
from stranded_physics.entities.build import to_spec
from stranded_physics.packs.builder import build_pack

SCENARIOS = Path(__file__).resolve().parents[1] / "scenarios"
# Elinder and Erixson 2012, PNAS 109(33):13220, Table 1.
SHIPS = (
    ("birkenhead_1852", 556, 1.4, True, "quick"),
    ("arctic_1854", 268, 39.7, True, "slow"),
    ("northfleet_1873", 367, 22.8, True, "slow"),
    ("atlantic_1873", 868, 29.6, False, "slow"),
    ("norge_1904", 795, 51.0, False, "quick"),
)


# Recorded inputs supplied with the calibration task; URLs and quotes are in ship_facts_calibration.md.
FACTS = {
    "birkenhead_1852": (20, "1852-02-26", "01:50", 20),
    "arctic_1854": (240, "1854-09-27", None, 10),
    "northfleet_1873": (30, "1873-01-22", "22:30", 7),
    "atlantic_1873": (None, "1873-04-01", "03:15", 3),
    "norge_1904": (12, "1904-06-28", None, 11),
}


@pytest.mark.parametrize("event,aboard,women_share,order,duration", SHIPS, ids=[s[0] for s in SHIPS])
def test_calibration_builds_and_sinks(event, aboard, women_share, order, duration):
    path = SCENARIOS / f"{event}.toml"
    text = path.read_text(encoding="utf-8")
    minutes = float(re.search(r"^# sink_minutes = ([\d.]+)$", text, re.M).group(1))
    recorded, date, local_time, water_c = FACTS[event]
    expected = recorded if recorded is not None else (0.5 if duration == "quick" else 3) * 30 * aboard / 686
    assert minutes == pytest.approx(expected)
    for line in text.splitlines():
        code = line.split("#", 1)[0]
        if "=" in code and re.search(r"\d", code.split("=", 1)[1]):
            assert "#" in line, line
    scenario = load_scenario(path)
    assert scenario.id == event
    assert {e.kind for e in scenario.entities} == {"ship", "breach", "lifeboats", "sea", "weather", "passengers"}
    assert all(e.source == "dials" for e in scenario.entities)
    cohorts = [e for e in scenario.entities if e.kind == "passengers"]
    assert all(e.name == "passengers" or e.name.startswith("crew") for e in cohorts)
    assert sum(sum(e.settings[k] for k in ("men", "women", "children")) for e in cohorts) == aboard
    passengers = [e for e in cohorts if not e.name.startswith("crew")]
    count = sum(sum(e.settings[k] for k in ("men", "women", "children")) for e in passengers)
    women = sum(e.settings["women"] for e in passengers)
    assert women == round(count * women_share / 100)
    boats = next(e for e in scenario.entities if e.kind == "lifeboats")
    assert boats.settings["women_first"] == int(order)
    pack = build_pack(to_spec(scenario, 1), 1)
    breach = next(e for e in scenario.entities if e.kind == "breach")
    raw = tomllib.loads(text)
    assert raw["local_utc_offset"] == 0
    local_impact = datetime.fromisoformat(raw["start_utc"]) + timedelta(
        hours=raw["local_utc_offset"], minutes=breach.settings["impact_minutes"])
    assert local_impact.date().isoformat() == date
    if local_time is not None:
        wanted = datetime.fromisoformat(date + "T" + local_time + ":00+00:00")
        assert abs((local_impact - wanted).total_seconds()) <= pack.time.dt_s
    sea = next(e for e in scenario.entities if e.kind == "sea")
    assert sea.settings["temperature_c"] == water_c
    assert breach.settings["impact_minutes"] >= 10 * pack.time.dt_s / 60
    afloat = pack.series("ship.afloat")
    sunk = np.flatnonzero(afloat <= 0)
    assert sunk.size, event
    first = int(sunk[0])
    step = pack.time.dt_s / 60
    elapsed = first * step - breach.settings["impact_minutes"]
    assert elapsed >= 10 * step
    assert abs(elapsed - minutes) <= step
    assert np.all(afloat[:first] > 0)
    assert np.all(afloat[first:] <= 0)


def test_fire_is_explicitly_unmodelled():
    text = (SCENARIOS / "UNMODELLED_calibration.md").read_text(encoding="utf-8")
    assert "golden_gate_1862" in text and "fire" in text.lower()
    assert not (SCENARIOS / "golden_gate_1862.toml").exists()
    assert {p.stem for p in SCENARIOS.glob("*.toml")} >= {s[0] for s in SHIPS}


def test_structural_failure_is_explicitly_unmodelled():
    text = (SCENARIOS / "UNMODELLED_calibration.md").read_text(encoding="utf-8")
    assert "princess_alice_1878" in text and "split in two" in text
    assert not (SCENARIOS / "princess_alice_1878.toml").exists()


def test_recorded_fact_audit_covers_all_ships():
    text = (SCENARIOS / "ship_facts_calibration.md").read_text(encoding="utf-8")
    for event in (*FACTS, "golden_gate_1862", "princess_alice_1878"):
        assert event in text
    assert "7:45" in text

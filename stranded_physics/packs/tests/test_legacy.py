"""Compare the adapter to the unchanged legacy forecast and exercise pack play."""

import numpy as np
import pytest

from engine.events import EventGenerator
from engine.simulation import DEFAULT_STEPS
from engine.volcano import VolcanoModel
from engine.world import IslandWorld, MAP_SEED, SCALE_M_PER_TILE
from stranded_physics.core.api import InterfaceError
from stranded_physics.packs.legacy import (
    LEGACY_ASH_FULL_KG_M2,
    LEGACY_LAHAR_M,
    LEGACY_RAIN_MM_H,
    LEGACY_STORM_MM_H,
    build_legacy_pack,
    legacy_scenario,
)
from stranded_physics.runtime.perception import perceive
from stranded_physics.runtime.simulation import PackSimulation


@pytest.mark.parametrize("seed", [0, 1, 2, 19, 42, 8731])
def test_every_field_and_site(seed):
    world = IslandWorld(seed=MAP_SEED, scenario="volcano")
    weather = EventGenerator(seed).weather
    volcano = VolcanoModel(seed, world, weather=weather)
    pack = build_legacy_pack(seed)
    assert pack.grid == pack.contract_grid
    assert (pack.grid.nx, pack.grid.ny, pack.grid.dx_m) == (40, 40, SCALE_M_PER_TILE)
    assert (pack.time.n, pack.time.dt_s, pack.t0_local_hour) == (DEFAULT_STEPS, 7200, 8)
    assert not pack.has("terrain.flow_accumulation")
    assert not pack.has("terrain.height_above_drainage")
    for name, expected in (("elevation", world.elevation), ("land_mask", np.array(world.elevation) > 0), ("land_cover", world.tiles), ("zone", world.zones)):
        np.testing.assert_array_equal(pack.frame(f"terrain.{name}"), expected)
    for name, tiles in (
        ("spawn", [world.spawn_pos]),
        ("vent", [world.vent]),
        ("assembly", world.assembly_points),
        ("water", world.freshwater_tiles),
        ("food", world.food_tiles),
    ):
        assert pack.sites[name] == [pack.grid.centre(y, x) for x, y in tiles]
        assert [pack.grid.locate(p) for p in pack.sites[name]] == [(y, x) for x, y in tiles]
    np.testing.assert_array_equal(pack.series("atmos.rain_rate"), [{"calm": 0, "rain": LEGACY_RAIN_MM_H, "storm": LEGACY_STORM_MM_H}[w] for w in weather])
    np.testing.assert_array_equal(pack.series("eruption.phase"), [{"unrest": 0, "escalating": 1, "erupting": 2, "fading": 3}[p] for p in volcano.phases])
    for name, event in (("tremor", "tremor"), ("gas", "gas_plume"), ("explosion", "eruption")):
        np.testing.assert_array_equal(pack.series(f"eruption.{name}"), [e == event for e in volcano.world_events])
    arrival = np.full((40, 40), np.inf)
    lava = np.zeros((40, 40))
    for k, hazard in enumerate(volcano.hazard_by_step):
        pdc, lahar = np.zeros((40, 40)), np.zeros((40, 40))
        for x, y in hazard["active_pdc"]:
            pdc[y, x] = 1
            arrival[y, x] = min(arrival[y, x], k * 7200)
        for x, y in hazard["active_lahar"]:
            lahar[y, x] = LEGACY_LAHAR_M
        for x, y in hazard["new_lava"]:
            lava[y, x] = 1
        ash = np.array([[int(d) for d in row] for row in hazard["ash_grid"]]) / 9 * LEGACY_ASH_FULL_KG_M2
        for name, expected in (("pdc.active", pdc), ("lahar.depth", lahar), ("lava.footprint", lava), ("tephra.deposit_load", ash)):
            np.testing.assert_array_equal(pack.frame(name, k * 7200), expected)
            np.testing.assert_array_equal(pack.frame(name, k * 7200 + 7199), expected)
    np.testing.assert_array_equal(pack.frame("pdc.arrival"), arrival)


def test_repeatability():
    first = build_legacy_pack(19)
    build_legacy_pack(2)
    second = build_legacy_pack(19)
    assert first.content_hash == second.content_hash
    for name in first.header["fields"]:
        np.testing.assert_array_equal(first._arrays[name], second._arrays[name])
        assert not first._arrays[name].flags.writeable
    assert build_legacy_pack(20).content_hash != first.content_hash


@pytest.mark.parametrize("mind", ["classical", "classical_mixture", "quantum"])
def test_full_runtime_run(mind):
    pack = build_legacy_pack(2)
    simulation = PackSimulation(pack, mind_type=mind)
    result = simulation.run()
    assert result["steps"]
    assert len(result["steps"]) == DEFAULT_STEPS or not simulation.agent.alive
    assert simulation.step() is None
    assert result["world"]["weather"] == EventGenerator(2).weather
    assert result["world"]["pack_hash"] == pack.content_hash


def test_no_future_percept():
    pack = build_legacy_pack(1)
    arrival = pack.frame("pdc.arrival")
    row, col = np.argwhere(np.isfinite(arrival))[0]
    when = arrival[row, col]
    point = pack.grid.centre(row, col)
    assert when > 0
    assert not perceive(pack, point, when - 1).flow_visible
    assert perceive(pack, point, when).flow_visible


def test_invalid_axes_raise(monkeypatch):
    from stranded_physics.packs import legacy

    monkeypatch.setattr(legacy, "DEFAULT_STEPS", 35)
    with pytest.raises(InterfaceError):
        legacy_scenario(1)

"""Tests for the Waterloo chlorine leak scenario."""
import json

import numpy as np
import pytest

from engine.chlorine import LEAK_SITES, LEAK_START_STEP, SOURCE_PPM, ChlorineModel, exposure_level, wind_at
from engine.site import BUILDING, DOORS, POOL, POOL_GATES, PROVENANCE, SITE_M_PER_TILE, SiteWorld
from engine.world import IslandWorld


@pytest.fixture(scope="module")
def world():
    return SiteWorld()


def reach(world, start):
    seen, stack = {start}, [start]
    while stack:
        for q in world.neighbors(stack.pop()):
            if q not in seen and world.walkable(q):
                seen.add(q)
                stack.append(q)
    return seen


def polygon_area(points):
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1]))) / 2


def test_map_keeps_the_island_world_interface(world):
    assert isinstance(world, IslandWorld)
    assert (world.width, world.height) == (40, 40)
    json.dumps(world.export_dict(), default=list)


def test_building_and_pool_areas_match_their_outlines(world):
    tile = SITE_M_PER_TILE ** 2
    drawn = {(x, y) for y in range(40) for x in range(40) if (x, y) in world.areas["indoors"]} | set(DOORS.values())
    drawn |= {p for p in world.wall_tiles if p not in world.areas["pool_deck"]} - _fence(world)
    assert abs(len(drawn) * tile / polygon_area(BUILDING) - 1) < .05
    assert abs(len(world.pool_tiles) * tile / polygon_area(POOL) - 1) < .05


def _fence(world):
    return {p for p in world.wall_tiles if any(q in world.areas["pool"] | world.areas["pool_deck"] for q in world.neighbors(p)) and
            not any(q in world.areas["indoors"] for q in world.neighbors(p))}


def test_every_walkable_tile_can_reach_every_exit(world):
    everywhere = reach(world, tuple(world.spawn_pos))
    walkable = {(x, y) for y in range(40) for x in range(40) if world.walkable((x, y))}
    assert set(world.exits.values()) <= everywhere
    # Only the far bank of Laurel Creek is cut off; its other crossings lie beyond this map.
    assert all(x <= 4 and y <= 17 for x, y in walkable - everywhere)
    assert world.areas["indoors"] | world.pool_tiles <= everywhere


def test_exits_are_on_the_map_edge(world):
    assert len(world.exits) == 5
    for x, y in world.exits.values():
        assert x in (0, 39) or y in (0, 39)


def test_doors_are_the_only_ways_out_of_the_building(world):
    indoors = world.areas["indoors"]
    crossings = {q for p in indoors for q in world.neighbors(p) if q not in indoors and world.walkable(q)}
    assert crossings == set(DOORS.values())


def test_blocking_any_one_door_still_leaves_a_way_out(world):
    for door in DOORS.values():
        blocked = SiteWorld()
        x, y = door
        blocked.tiles[y][x] = 3
        assert set(blocked.exits.values()) <= reach(blocked, (18, 12))


def test_pool_deck_only_opens_through_the_door_and_gates(world):
    fenced = world.areas["pool"] | world.areas["pool_deck"]
    crossings = {q for p in fenced for q in world.neighbors(p) if q not in fenced and world.walkable(q)}
    assert crossings == set(POOL_GATES.values()) | {DOORS["pool_south"]}


def test_pool_is_walkable_but_slower(world):
    x, y = next(iter(world.pool_tiles))
    assert world.walkable((x, y))
    assert world.travel_minutes((0, 0), (x, y)) > world.travel_minutes((0, 0), (5, 5))


def test_creek_blocks_walking_except_at_the_crossing(world):
    assert world.creek_tiles
    assert not any(world.walkable(p) for p in world.creek_tiles)


def test_map_never_sets_risk_by_location(world):
    assert {z for row in world.zones for z in row} == {0}


def test_every_provenance_entry_has_a_status_and_sourced_ones_have_a_link():
    for entry in PROVENANCE.values():
        assert entry["status"] in {"sourced", "assumption", "unconfirmed"}
        if entry["status"] == "sourced":
            assert entry["url"].startswith("https://")


# --- Chlorine model ---

@pytest.fixture(scope="module")
def leak(world):
    return ChlorineModel(1, world)


def test_nothing_before_the_leak_and_a_two_hour_run(leak):
    assert leak.horizon == 721
    assert leak.ppm[:LEAK_START_STEP].max() == 0
    assert leak.world_events[LEAK_START_STEP] == "chlorine_leak"
    assert leak.world_events.count("chlorine_leak") == 1


def test_source_holds_its_level_only_while_leaking_then_fades(leak):
    x, y = leak.source
    assert leak.ppm[leak.leak_end_step - 1, y, x] == pytest.approx(SOURCE_PPM, rel=.15)
    assert leak.ppm[-1].max() < leak.ppm[leak.leak_end_step - 1].max() / 2


def test_forecast_never_depends_on_the_seed(world):
    assert (ChlorineModel(1, world).ppm == ChlorineModel(2, world).ppm).all()


def test_solid_walls_hold_no_gas(world, leak):
    for x, y in world.nearby_building_tiles:
        assert leak.ppm[:, y, x].max() == 0


def test_gas_only_gets_outside_through_doors(world):
    # A leak inside the north end: gas is always stronger in the doorway than just beyond it.
    model = ChlorineModel(1, world, leak_site="north_end")
    x, y = world.doors["north"]
    during = range(LEAK_START_STEP, model.leak_end_step)
    assert all(model.ppm[t, y - 1, x] < model.ppm[t, y, x] for t in during)
    # With no door nearby, the far side of the solid east wall stays almost clear.
    assert model.ppm[:, 12, 24].max() < .1 * model.ppm[:, 12, 22].max()


def test_outdoor_gas_drifts_downwind(world):
    # At 14:00 the wind comes from about 223 degrees, so gas should lean north-east of a deck leak.
    model = ChlorineModel(1, world, leak_site="deck")
    x, y = model.source
    t = model.leak_end_step - 1
    assert model.ppm[t, y - 3, x + 3] > model.ppm[t, y + 3, x - 3]


def test_level_scales_with_the_source(world):
    low, high = ChlorineModel(1, world), ChlorineModel(1, world, source_ppm=110.)
    assert high.ppm.max() == pytest.approx(low.ppm.max() * 5, rel=.05)


def test_all_leak_sites_are_settings_on_open_tiles(world):
    for name, p in LEAK_SITES.items():
        assert p not in world.wall_tiles
        assert ChlorineModel(1, world, leak_site=name).ppm.max() > 0


def test_exposure_levels_follow_the_epa_table():
    steps = lambda minutes: minutes * 6
    assert exposure_level([0.] * steps(60)) == 0
    assert exposure_level([.6] * steps(10)) == 1
    assert exposure_level([3.] * steps(10)) == 2
    assert exposure_level([2.1] * steps(60)) == 2
    assert exposure_level([60.] * steps(10)) == 3
    assert exposure_level([21.] * steps(60)) == 3


def test_brief_exposure_is_averaged_over_the_full_window():
    assert exposure_level([3.] * 6) == 0  # one minute at 3 ppm averages 0.3 ppm over ten minutes


def test_wind_table_uses_the_day_s_values():
    assert wind_at(0, 14) == pytest.approx((6.4 / 3.6, 223))

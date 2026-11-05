"""Tests for the Waterloo chlorine leak scenario."""
import json

import pytest

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

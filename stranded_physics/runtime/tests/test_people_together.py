"""People noticing and helping each other, wood, built shelters and healing, on a small flat pack with no hazards."""

from datetime import datetime, timezone

import numpy as np
import pytest

from stranded_physics.core.api import GridSpec, ScenarioSpec, TimeAxis
from stranded_physics.core.fields import spec
from stranded_physics.packs.builder import build_pack
from stranded_physics.runtime.body import STATE_KEYS
from stranded_physics.runtime.group import HELP_M, NOTICE_M, notice_each_other, play_people
from stranded_physics.runtime.simulation import INJURY_STEPS, PackSimulation, WOOD_PER_SHELTER

GRID = GridSpec("EPSG:32620", 0.0, 20000.0, 500.0, 40, 40)
TIME = TimeAxis(datetime(2021, 4, 8, tzinfo=timezone.utc), 7200.0, 24)


class FlatLand:
    id, tier, parameters = "terrain", "T0", ()
    inputs = ()
    outputs = (spec("terrain.elevation"), spec("terrain.land_mask"), spec("terrain.zone"))

    def check_validity(self, fields):
        return []

    def run(self, fields, rng):
        fields.put("terrain.elevation", np.full((40, 40), 10.0), "m", GRID)
        fields.put("terrain.land_mask", np.ones((40, 40)), "dimensionless", GRID)
        fields.put("terrain.zone", np.zeros((40, 40)), "dimensionless", GRID)
        return {}


class NoRain:
    id, tier, parameters = "atmos", "T0", ()
    inputs = ()
    outputs = (spec("atmos.rain_rate"),)

    def check_validity(self, fields):
        return []

    def run(self, fields, rng):
        fields.put("atmos.rain_rate", np.zeros(TIME.n), "mm/h", time=TIME)
        return {}


def pack(spawns, **sites):
    return build_pack(
        ScenarioSpec(
            "flat", GRID, GRID, TIME, 8, (FlatLand(), NoRain()), {"spawn": spawns, "assembly": [(1250.0, 1250.0)], "water": [(10250.0, 10250.0)], **sites}
        ),
        1,
    )


def doing(action):
    return lambda state: {"action": action, "probs": {action: 1.0}, "reason": "test"}


def two_people(gap_m):
    built = pack([(5250.0, 5250.0), (5250.0 + gap_m, 5250.0)])
    return [PackSimulation(built, decide_fn=doing("rest"), person=index) for index in range(2)]


def test_someone_who_sees_a_warned_neighbour_is_warned():
    near = two_people(NOTICE_M - 100.0)
    near[0].warned = True
    notice_each_other(near)
    assert near[1].warned


def test_someone_too_far_away_is_not():
    far = two_people(NOTICE_M + 100.0)
    far[0].warned = True
    notice_each_other(far)
    assert not far[1].warned


def test_a_dead_neighbour_warns_and_helps_nobody():
    near = two_people(100.0)
    near[0].warned, near[0].agent.alive = True, False
    notice_each_other(near)
    assert not near[1].warned and not near[1].helped


def test_only_an_able_bodied_neighbour_helps():
    near = two_people(HELP_M - 50.0)
    near[0].agent.injured = True
    notice_each_other(near)
    assert near[0].helped and not near[1].helped
    near[1].agent.injured = True
    notice_each_other(near)
    assert not near[0].helped


def test_help_lets_an_injured_person_walk_further():
    built = pack([(5250.0, 5250.0), (5250.0, 5400.0)])
    walking = [PackSimulation(built, decide_fn=doing("drink"), person=0) for _ in range(2)]
    for person in walking:
        person.agent.injured, person.injury_steps_left = True, 99
    walking[1].helped = True
    for person in walking:
        person.step()
    start = np.array((5250.0, 5250.0))
    assert np.linalg.norm(np.array(walking[1].agent.xy_m) - start) > 1.5 * np.linalg.norm(np.array(walking[0].agent.xy_m) - start)


def test_being_near_people_never_reaches_a_mind():
    seen = []

    def watching(state):
        seen.append(set(state))
        return doing("rest")(state)

    near = two_people(100.0)
    near[0].decide_fn = watching
    notice_each_other(near)
    near[0].step()
    assert seen == [STATE_KEYS]


def test_list_order_changes_nothing():
    built = pack([(5250.0, 5250.0), (5350.0, 5250.0), (9000.0, 9000.0)])
    forward = play_people(built, ["classical", "classical", "classical"])
    backward = play_people(pack([(9000.0, 9000.0), (5350.0, 5250.0), (5250.0, 5250.0)]), ["classical", "classical", "classical"])
    assert [r["pos_after"] for r in forward[0]["steps"]] == [r["pos_after"] for r in backward[2]["steps"]]


def test_wood_is_gathered_only_near_wood_and_builds_a_shelter():
    built = pack([(5250.0, 5250.0)], wood=[(5250.0, 5250.0)])
    person = PackSimulation(built, decide_fn=doing("forage"))
    for _ in range(WOOD_PER_SHELTER):
        person.step()
    assert person.agent.inventory["wood"] == WOOD_PER_SHELTER and not person._sheltered()
    person.decide_fn = doing("build_shelter")
    person.step()
    assert person.agent.inventory["wood"] == 0 and person._sheltered() and len(person.built) == 1
    far = PackSimulation(pack([(5250.0, 5250.0)]), decide_fn=doing("forage"))
    far.step()
    assert far.agent.inventory["wood"] == 0


def test_building_needs_wood():
    person = PackSimulation(pack([(5250.0, 5250.0)]), decide_fn=doing("build_shelter"))
    person.step()
    assert not person.built


def test_a_shelter_someone_built_is_theirs_alone():
    built = pack([(5250.0, 5250.0), (5250.0, 5250.0)], wood=[(5250.0, 5250.0)])
    builder, other = PackSimulation(built, person=0, decide_fn=doing("rest")), PackSimulation(built, person=1, decide_fn=doing("rest"))
    builder.built.append(builder.agent.xy_m)
    assert builder._sheltered() and not other._sheltered()


def test_a_tool_uses_wood():
    person = PackSimulation(pack([(5250.0, 5250.0)]), decide_fn=doing("craft"))
    person.agent.inventory["wood"] = 1
    person.step()
    assert person.agent.inventory == {"wood": 0, "food": 0, "tools": 1}


@pytest.mark.parametrize("action, steps", [("explore", INJURY_STEPS), ("rest", INJURY_STEPS // 2)])
def test_injuries_heal_and_rest_heals_faster(action, steps):
    person = PackSimulation(pack([(5250.0, 5250.0)]), decide_fn=doing(action))
    person._injure()
    for _ in range(steps - 1):
        person.step()
    assert person.agent.injured
    person.step()
    assert not person.agent.injured

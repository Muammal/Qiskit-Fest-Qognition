"""Hazards meeting a body: flows, ash, roofs, gas and lava, on a small flat pack."""

import numpy as np
import pytest

from stranded_physics.core.api import ScenarioSpec
from stranded_physics.core.fields import spec
from stranded_physics.domains.exposure.model import SETTINGS, roof_failure_fraction
from stranded_physics.domains.agent.physiology import needs
from stranded_physics.packs.builder import build_pack
from stranded_physics.runtime.perception import SO2_SMELL_UG_M3, perceive
from stranded_physics.runtime.simulation import PackSimulation
from stranded_physics.runtime.tests.test_people_together import FlatLand, GRID, NoRain, TIME, doing

HOME, SHELTER = (5250.0, 5250.0), (15250.0, 15250.0)


class Fields:
    tier, parameters, inputs = "T0", (), ()

    def __init__(self, category, **arrays):
        self.id, self.arrays = category, {name.replace("__", "."): value for name, value in arrays.items()}
        self.outputs = tuple(spec(name) for name in self.arrays)

    def check_validity(self, fields):
        return []

    def run(self, fields, rng):
        for name, value in self.arrays.items():
            kind = spec(name).kind
            fields.put(name, value, spec(name).unit, GRID, TIME if kind == "frames" else None)
        return {}


def flow_everywhere():
    return Fields("pdc", pdc__arrival=np.zeros((40, 40)), pdc__active=np.ones((TIME.n, 40, 40)))


def pack(*domains, spawn=HOME, seed=1, assembly=SHELTER):
    return build_pack(
        ScenarioSpec("flat", GRID, GRID, TIME, 8, (FlatLand(), NoRain(), *domains), {"spawn": [spawn], "assembly": [assembly], "water": [(10250.0, 10250.0)]}),
        seed,
    )


def one_step_outcomes(spawn, count=300):
    outcomes = []
    for seed in range(count):
        person = PackSimulation(pack(flow_everywhere(), spawn=spawn, seed=seed), decide_fn=doing("rest"))
        person.step()
        outcomes.append((person.agent.alive, person.agent.injured))
    return outcomes


def test_most_people_outdoors_die_in_a_flow_and_survivors_are_injured():
    outcomes = one_step_outcomes(HOME)
    dead = sum(not alive for alive, _ in outcomes) / len(outcomes)
    assert abs(dead - SETTINGS["flow_death_outdoors"]) < 0.05
    assert all(injured for alive, injured in outcomes if alive)


def test_shelter_improves_the_odds():
    outcomes = one_step_outcomes(SHELTER)
    dead = sum(not alive for alive, _ in outcomes) / len(outcomes)
    assert abs(dead - SETTINGS["flow_death_sheltered"]) < 0.1


def test_no_flow_means_no_harm():
    person = PackSimulation(pack(Fields("pdc", pdc__arrival=np.full((40, 40), np.inf), pdc__active=np.zeros((TIME.n, 40, 40)))), decide_fn=doing("rest"))
    person.run()
    assert person.agent.alive and not person.agent.injured


def test_the_same_seed_gives_the_same_fate():
    fates = {PackSimulation(pack(flow_everywhere(), seed=3), decide_fn=doing("rest")).run()["outcome"] for _ in range(3)}
    assert len(fates) == 1


def test_a_flow_is_one_roll_per_step():
    person = PackSimulation(pack(flow_everywhere(), seed=1), decide_fn=doing("rest"))
    calls = []
    original = person.luck.random

    class Counting:
        def random(self):
            calls.append(1)
            return 0.99

    person.luck = Counting()
    person.step()
    assert len(calls) == 1 and person.agent.alive
    assert original


def ash(load):
    return Fields("tephra", tephra__deposit_load=np.full((TIME.n, 40, 40), float(load)))


def test_ash_tires_a_person_and_shelter_helps():
    outdoors = PackSimulation(pack(ash(50.0)), decide_fn=doing("explore"))
    clean = PackSimulation(pack(ash(0.0)), decide_fn=doing("explore"))
    indoors = PackSimulation(pack(ash(50.0), spawn=SHELTER), decide_fn=doing("explore"))
    for person in (outdoors, clean, indoors):
        person.step()
    assert needs(outdoors.agent.balance)["energy"] < needs(indoors.agent.balance)["energy"] < needs(clean.agent.balance)["energy"]


def roofs(share):
    return Fields("exposure", exposure__roof_failure=np.full((TIME.n, 40, 40), float(share)))


def test_a_failed_roof_injures_and_ends_the_shelter():
    person = PackSimulation(pack(ash(1000.0), roofs(1.0), spawn=SHELTER), decide_fn=doing("rest"))
    assert person._sheltered()
    person.step()
    assert person.agent.injured and not person._sheltered()


def test_roofs_fail_only_as_the_load_grows():
    person = PackSimulation(pack(ash(100.0), roofs(0.0), spawn=SHELTER), decide_fn=doing("rest"))
    person.step()
    assert not person.agent.injured and person._sheltered()
    assert roof_failure_fraction(0.0) == 0.0


def test_a_person_outdoors_has_no_roof_to_lose():
    person = PackSimulation(pack(ash(1000.0), roofs(1.0)), decide_fn=doing("rest"))
    person.step()
    assert not person.roof_lost


@pytest.mark.parametrize("level, smelled", [(SO2_SMELL_UG_M3 * 2, True), (SO2_SMELL_UG_M3 / 2, False)])
def test_gas_is_noticed_only_where_it_is_strong(level, smelled):
    field = np.zeros((TIME.n, 40, 40))
    row, col = GRID.locate(HOME)
    field[:, row, col] = level
    built = pack(Fields("gas", gas__so2_concentration=field))
    assert perceive(built, HOME, 0.0).gas_smell is smelled
    assert perceive(built, SHELTER, 0.0).gas_smell is False


def test_lava_kills_at_the_end_of_a_walk_through_it():
    person = PackSimulation(pack(Fields("lava", lava__footprint=np.ones((TIME.n, 40, 40)))), decide_fn=doing("rest"))
    person.step()
    assert person.agent.cause == "lava"

"""Plays many people on one pack. Hazards never react to people, so each plays separately and sees only their own state."""
from __future__ import annotations

from stranded_physics.core.api import ScenarioPack
from stranded_physics.runtime.simulation import PackSimulation, Shared


def play_people(pack: ScenarioPack, minds: list[str]) -> list[dict]:
    """One timeline per person, in order. People don't yet see or help each other."""
    shared = Shared(pack)
    return [PackSimulation(pack, mind_type=mind, person=index, shared=shared).run() for index, mind in enumerate(minds)]

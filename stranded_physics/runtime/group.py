"""Plays many people on one pack, step by step together. Hazards never react to people, and each mind sees only its own state.

People affect each other only through their bodies: someone who sees a neighbour leaving knows to go, and an able-bodied neighbour
helps an injured person keep up. Nothing about anyone else ever reaches a mind, because the frozen contract has no place for it.
"""

from __future__ import annotations

import numpy as np

from stranded_physics.core.api import ScenarioPack
from stranded_physics.runtime.simulation import PackSimulation, Shared

NOTICE_M = 500.0  # assumption: close enough to see that a neighbour has been warned and is acting on it.
HELP_M = 200.0  # assumption: close enough to help someone walk.


def notice_each_other(people: list[PackSimulation]) -> None:
    """Uses only where everyone is at the start of this step, so the order people are listed in changes nothing."""
    alive = np.array([person.agent.alive for person in people])
    warned = np.array([person.warned for person in people]) & alive
    able = np.array([not person.agent.injured for person in people]) & alive
    where = np.array([person.agent.xy_m for person in people])
    distance = np.hypot(*(where[:, None, :] - where[None, :, :]).transpose(2, 0, 1))
    np.fill_diagonal(distance, np.inf)
    sees_warned = ((distance < NOTICE_M) & warned[None, :]).any(axis=1)
    has_help = ((distance < HELP_M) & able[None, :]).any(axis=1)
    for index, person in enumerate(people):
        person.warned = person.warned or bool(sees_warned[index])
        person.helped = bool(has_help[index])


def play_people(pack: ScenarioPack, minds: list[str]) -> list[dict]:
    """One timeline per person, in order."""
    shared = Shared(pack)
    people = [PackSimulation(pack, mind_type=mind, person=index, shared=shared) for index, mind in enumerate(minds)]
    for _ in range(pack.time.n):
        notice_each_other(people)
        for person in people:
            person.step()
    return [person.timeline() for person in people]

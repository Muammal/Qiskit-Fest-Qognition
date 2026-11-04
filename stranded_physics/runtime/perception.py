"""The only path from hazards to a mind. It reads the past, at the agent's own position."""
from __future__ import annotations

from stranded_physics.core.api import Percept, ScenarioPack, XY

FLOW_SIGHT_M = 1000.  # assumption: T0 sighting distance for a moving flow front. WS6 replaces this.


def perceive(pack: ScenarioPack, xy_m: XY, t_s: float) -> Percept:
    """Never reads a value later than t_s, and never a place the agent can't sense."""
    now = pack.time.index_at(t_s)
    arrived = False
    for dx, dy in ((0, 0), (FLOW_SIGHT_M, 0), (-FLOW_SIGHT_M, 0), (0, FLOW_SIGHT_M), (0, -FLOW_SIGHT_M)):
        if pack.sample("pdc.arrival", (xy_m[0] + dx, xy_m[1] + dy)) <= t_s:
            arrived = True
    return Percept(
        t_s=t_s,
        felt_tremor=bool(pack.series("eruption.tremor")[now] > 0),
        gas_smell=bool(pack.series("eruption.gas")[now] > 0),
        explosion_heard=bool(pack.series("eruption.explosion")[now] > 0),
        ash_kg_m2=pack.sample("tephra.deposit_load", xy_m, t_s),
        rain_mm_h=float(pack.series("atmos.rain_rate")[now]),
        flow_visible=arrived,
    )

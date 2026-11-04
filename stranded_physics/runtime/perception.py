"""The only path from hazards to a mind. It reads the past, at the agent's own position."""
from __future__ import annotations

from stranded_physics.core.api import Percept, ScenarioPack, XY

FLOW_SIGHT_M = 1000.  # assumption: T0 sighting distance for a moving flow front. WS6 replaces this.


def perceive(pack: ScenarioPack, xy_m: XY, t_s: float) -> Percept:
    """Never reads a value later than t_s, and never a place the agent can't sense."""
    now = pack.time.index_at(t_s)
    arrived = False
    if pack.has("pdc.arrival"):
        for dx, dy in ((0, 0), (FLOW_SIGHT_M, 0), (-FLOW_SIGHT_M, 0), (0, FLOW_SIGHT_M), (0, -FLOW_SIGHT_M)):
            if pack.sample("pdc.arrival", (xy_m[0] + dx, xy_m[1] + dy)) <= t_s:
                arrived = True

    def sign(name: str) -> bool:
        return pack.has(name) and bool(pack.series(name)[now] > 0)

    return Percept(
        t_s=t_s,
        felt_tremor=sign("eruption.tremor"),
        gas_smell=sign("eruption.gas"),
        explosion_heard=sign("eruption.explosion"),
        ash_kg_m2=pack.sample("tephra.deposit_load", xy_m, t_s) if pack.has("tephra.deposit_load") else 0.,
        rain_mm_h=float(pack.series("atmos.rain_rate")[now]),
        flow_visible=arrived,
        wind_m_s=float(pack.series("storm.max_wind")[now]) if pack.has("storm.max_wind") else 0.,
    )

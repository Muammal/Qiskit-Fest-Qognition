"""A plain water and energy balance for the survivor, replacing placeholder rates.

Water and survival limits come from Tipton and Montgomery (2025). Walking energy uses Pandolf et al. (1977).
It is not ISO 7933, which is paywalled and unread. It ignores humidity, ash and heat stress, which belong to T-603.
The needs a mind sees stay on the frozen 0 to 1 scale, where 1 is well and 0 is the limit.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from stranded_physics.core.records import load_parameters

PARAMETERS = load_parameters(Path(__file__).resolve().parent / "params.toml")
_BY_NAME = {p.id.split(".", 1)[1]: p.value for p in PARAMETERS}
LITRES_PER_KG_SWEAT = 1.  # Water, to the accuracy needed here.
MINIMUM_GRADE = 0.  # Pandolf's equation is for level or uphill walking, so downhill is priced as level.


def setting(name: str, unit: str) -> float:
    return float(_BY_NAME[name].to(unit).magnitude)


BODY_KG = setting("body_mass", "kg")
LETHAL_DEFICIT_L = BODY_KG * setting("body_water_fraction", "dimensionless") * setting("lethal_water_loss", "dimensionless")
REST_WATTS = setting("rest_energy", "W")
REST_KCAL_PER_HOUR = setting("rest_energy", "kcal/hour")
REST_WATER_L_PER_HOUR = setting("rest_water_need", "liter/hour")
JOULES_PER_KCAL = 4184.
SECONDS_PER_HOUR = 3600.
HOURS_PER_DAY = 24.


@dataclass(frozen=True)
class Body:
    """What the body has lost so far. Never handed to a mind directly."""

    water_deficit_l: float
    food_deficit_kcal: float
    fatigue_kcal: float


def pandolf_watts(speed_m_s: float, grade_percent: float, mass_kg: float = BODY_KG, load_kg: float = 0., terrain: float | None = None) -> float:
    """Pandolf et al. (1977): M = 1.5 W + 2 (W + L)(L / W)^2 + eta (W + L)(1.5 V^2 + 0.35 V G)."""
    eta = setting("terrain_factor", "dimensionless") if terrain is None else terrain
    grade = max(grade_percent, MINIMUM_GRADE)
    return 1.5 * mass_kg + 2. * (mass_kg + load_kg) * (load_kg / mass_kg) ** 2 + eta * (mass_kg + load_kg) * (1.5 * speed_m_s ** 2 + .35 * speed_m_s * grade)


def sweat_l_per_hour(watts: float) -> float:
    """Extra metabolic heat above rest, carried off by evaporating sweat, up to the published limit."""
    extra = max(0., watts - REST_WATTS)
    return min(extra / setting("sweat_heat", "J/kg") * LITRES_PER_KG_SWEAT * SECONDS_PER_HOUR, setting("sweat_limit", "liter/hour"))


def start_body(thirst: float, hunger: float, energy: float) -> Body:
    """Places the starting needs on the balance scale, so runs begin with the frozen contract's values."""
    return Body((1. - thirst) * LETHAL_DEFICIT_L, (1. - hunger) * setting("felt_hunger_span", "kcal"), (1. - energy) * setting("fatigue_span", "kcal"))


def advance(body: Body, hours: float, walking_hours: float = 0., walking_watts: float = 0., drank: bool = False, rested: bool = False) -> Body:
    """One stretch of time. Returns a new Body."""
    extra_kcal = max(0., walking_watts - REST_WATTS) * walking_hours * SECONDS_PER_HOUR / JOULES_PER_KCAL
    water = body.water_deficit_l + REST_WATER_L_PER_HOUR * hours + sweat_l_per_hour(walking_watts) * walking_hours
    if drank:
        water = max(0., water - setting("drink_per_step", "liter"))
    fatigue = body.fatigue_kcal + extra_kcal
    if rested:
        fatigue = max(0., fatigue - setting("rest_recovery", "kcal"))
    return replace(body, water_deficit_l=water, food_deficit_kcal=body.food_deficit_kcal + REST_KCAL_PER_HOUR * hours + extra_kcal, fatigue_kcal=fatigue)


def needs(body: Body) -> dict[str, float]:
    return {"thirst": max(0., 1. - body.water_deficit_l / LETHAL_DEFICIT_L),
            "hunger": max(0., 1. - body.food_deficit_kcal / setting("felt_hunger_span", "kcal")),
            "energy": max(0., 1. - body.fatigue_kcal / setting("fatigue_span", "kcal"))}


def cause_of_death(body: Body) -> str | None:
    if body.water_deficit_l >= LETHAL_DEFICIT_L:
        return "dehydration"
    if body.food_deficit_kcal >= setting("starvation_days", "day") * HOURS_PER_DAY * REST_KCAL_PER_HOUR:
        return "starvation"
    return None

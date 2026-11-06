"""Historical gate observables; inquiry tons are long tons, not metric tonnes."""

import json
import sys

from .model import KG_PER_LONG_TON, KG_PER_TONNE, SECONDS_PER_MINUTE, SETTINGS, flood, titanic_breach, titanic_ship


def water_at_40_minutes():
    result = flood(titanic_ship(), titanic_breach(), SETTINGS["water_measure_min"] * SECONDS_PER_MINUTE)
    print(json.dumps({"value": float(result.water_t[-1].sum() * KG_PER_TONNE / KG_PER_LONG_TON)}))


def foundering_minutes():
    ship, breach = titanic_ship(), titanic_breach()
    result = flood(ship, breach, SETTINGS["duration"])
    value = (
        {"value": SETTINGS["not_foundered_minutes"], "foundered": False} if result.foundered_s is None else {"value": result.foundered_s / SECONDS_PER_MINUTE}
    )
    if result.foundered_s is not None:
        result = flood(ship, breach, result.foundered_s)
    value.update(
        water_tons=float(result.water_t[-1].sum() * KG_PER_TONNE / KG_PER_LONG_TON),
        bow_draught_m=float(result.draught_bow_m[-1]),
        stern_draught_m=float(result.draught_stern_m[-1]),
    )
    print(json.dumps(value))


if __name__ == "__main__":
    commands = {"water_at_40_minutes": water_at_40_minutes, "foundering_minutes": foundering_minutes}
    if len(sys.argv) != 2 or sys.argv[1] not in commands:
        raise SystemExit("choose water_at_40_minutes or foundering_minutes")
    commands[sys.argv[1]]()

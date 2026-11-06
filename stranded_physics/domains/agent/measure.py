"""Measurements behind the body model's anchor gates. Each prints a final JSON line.

python -m stranded_physics.domains.agent.measure water_need_walking|days_without_water
"""

from __future__ import annotations

import json
import sys

from stranded_physics.domains.agent.physiology import HOURS_PER_DAY, LETHAL_DEFICIT_L, REST_WATER_L_PER_HOUR, pandolf_watts, setting, sweat_l_per_hour
from stranded_physics.domains.agent.walking import tobler_speed_m_s

PERCENT = 100.0


def water_need_walking() -> float:
    """Litres a day, walking the reference hours at Tobler's speed on the reference grade."""
    grade = setting("reference_grade", "dimensionless")
    watts = pandolf_watts(tobler_speed_m_s(grade / PERCENT), grade)
    return REST_WATER_L_PER_HOUR * HOURS_PER_DAY + sweat_l_per_hour(watts) * setting("reference_walk_hours", "hour")


def days_without_water() -> float:
    return LETHAL_DEFICIT_L / water_need_walking()


def main(argv: list[str]) -> int:
    modes = {"water_need_walking": water_need_walking, "days_without_water": days_without_water}
    if len(argv) != 1 or argv[0] not in modes:
        print(__doc__)
        return 2
    print(json.dumps({"value": modes[argv[0]]()}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

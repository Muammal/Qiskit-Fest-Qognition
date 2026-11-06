import json
import sys
from datetime import datetime, timezone
from .model import SETTINGS, dome_volume_m3, dome_radius_m

M3_PER_MILLION_M3 = 1e6


def main():
    axis = datetime.fromtimestamp(SETTINGS["measure_axis_start"], timezone.utc)
    first = datetime.fromtimestamp(SETTINGS["first_explosion_epoch"], timezone.utc)
    age = SETTINGS["growth_before_axis"] + (first - axis).total_seconds()
    if sys.argv[1:] == ["dome_volume_mm3"]:
        value = dome_volume_m3(SETTINGS["flux"], age) / M3_PER_MILLION_M3
    elif sys.argv[1:] == ["dome_radius_m"]:
        value = dome_radius_m(SETTINGS["flux"], SETTINGS["viscosity"], age)
    else:
        return 2
    print(json.dumps({"value": float(value)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

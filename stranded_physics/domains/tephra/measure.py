"""Local analytic measurement helpers; scenario coupling lives in validation."""
import json
import sys

from .model import SETTINGS, grain_classes, settling_speed_m_s


def main(argv):
    if argv != ["fine_settling"]:
        return 2
    value = settling_speed_m_s(min(grain_classes(int(SETTINGS["grain_count"]))[0]), SETTINGS["particle_density"], SETTINGS["air_density"], SETTINGS["air_viscosity"])
    print(json.dumps({"value": value}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

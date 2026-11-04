"""Local analytic measurement helpers; scenario coupling lives in validation."""
import json
import sys

from .model import SETTINGS, stokes_settling_m_s


def main(argv):
    if argv != ["fine_settling"]:
        return 2
    value = stokes_settling_m_s(SETTINGS["fine_diameter"], SETTINGS["particle_density"], SETTINGS["air_density"], SETTINGS["air_viscosity"])
    print(json.dumps({"value": value}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

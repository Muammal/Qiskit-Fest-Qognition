"""Log-log height versus mass-rate exponent of the implemented Mastin relation."""
import json
import sys

import numpy as np
from scipy.optimize import brentq

from .model import mastin_mass_rate_kg_s


def main(argv):
    if argv != ["mastin_slope"]:
        return 2
    rates = np.array([1e6, 1e8])
    heights = [brentq(lambda h: mastin_mass_rate_kg_s(h) - rate, 0., 100000.) for rate in rates]
    print(json.dumps({"value": float(np.log(heights[1] / heights[0]) / np.log(rates[1] / rates[0]))}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

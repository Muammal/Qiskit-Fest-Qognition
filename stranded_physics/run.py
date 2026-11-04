"""Play one pack from the command line. Only fake packs exist so far, and it says so.

    python -m stranded_physics.run --seed 1 --mind quantum
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter

from stranded_physics.core.fakes import fake_scenario
from stranded_physics.packs.builder import build_pack
from stranded_physics.runtime.simulation import PackSimulation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--mind", choices=("quantum", "classical"), default="quantum")
    args = parser.parse_args(argv)
    pack = build_pack(fake_scenario(), args.seed)
    timeline = PackSimulation(pack, mind_type=args.mind).run()
    tiers = {row["id"]: row["tier"] for row in pack.header["domains"]}
    print(f"pack {pack.content_hash[:12]}  scenario {pack.scenario}  tiers {tiers}")
    print("FAKE T0 PHYSICS: this checks the interfaces only. Do not cite any result from it.")
    print(f"outcome {timeline['outcome']}  cause {timeline['cause']}  steps {len(timeline['steps'])}")
    print("events", Counter(step["event"] for step in timeline["steps"]).most_common())
    return 0


if __name__ == "__main__":
    sys.exit(main())

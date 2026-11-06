"""Play one pack from the command line, and say plainly how far its result can be trusted.

    python -m stranded_physics.run --scenario st_vincent_2021 --seed 1 --mind quantum
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter

from stranded_physics.pack import SCENARIOS
from stranded_physics.packs.builder import build_pack
from stranded_physics.runtime.simulation import PackSimulation

CAVEATS = {
    "fake": "FAKE T0 PHYSICS: this checks the interfaces only. Do not cite any result from it.",
    "st_vincent_2021": ("REAL PLACE AND TIMELINE, SIMPLE MODELS: see python -m stranded_physics.check stranded_physics/scenario_cards/st_vincent_2021.toml for what agrees "
                        "with 2021 records and what doesn't. Thirst, hunger and energy are still placeholder rates, so survival numbers are not findings about people."),
}
CAVEATS["st_vincent_2021_richmond"] = CAVEATS["st_vincent_2021"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="fake")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--mind", choices=("quantum", "classical"), default="quantum")
    args = parser.parse_args(argv)
    pack = build_pack(SCENARIOS[args.scenario](), args.seed)
    timeline = PackSimulation(pack, mind_type=args.mind).run()
    tiers = {row["id"]: row["tier"] for row in pack.header["domains"]}
    print(f"pack {pack.content_hash[:12]}  scenario {pack.scenario}  tiers {tiers}")
    print(CAVEATS[args.scenario])
    print(f"outcome {timeline['outcome']}  cause {timeline['cause']}  steps {len(timeline['steps'])}")
    print("events", Counter(step["event"] for step in timeline["steps"]).most_common())
    return 0


if __name__ == "__main__":
    sys.exit(main())

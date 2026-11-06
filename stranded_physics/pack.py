"""Build a scenario pack offline.

python -m stranded_physics.pack build --scenario st_vincent_2021 --seed 1
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from stranded_physics.core.fakes import fake_scenario
from stranded_physics.packs.builder import build_pack, save_pack


def st_vincent_scenario(spawn: str = "chateaubelair"):
    from stranded_physics.packs.st_vincent_2021 import scenario  # Needs the raw data, so it loads only when asked for.

    return scenario(spawn)


SCENARIOS = {"fake": fake_scenario, "st_vincent_2021": st_vincent_scenario, "st_vincent_2021_richmond": lambda: st_vincent_scenario("richmond")}
PACK_DIR = Path(__file__).resolve().parents[1] / "artifacts" / "physics" / "packs"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build",))
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), required=True)
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args(argv)
    pack = build_pack(SCENARIOS[args.scenario](), args.seed)
    path = PACK_DIR / f"{pack.scenario}_{pack.seed}.npz"
    save_pack(pack, path)
    print(f"{path}  {pack.content_hash}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

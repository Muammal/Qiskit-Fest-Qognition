"""Build a scenario pack offline. Only the fake scenario exists until real categories arrive.

    python -m stranded_physics.pack build --scenario fake --seed 1
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from stranded_physics.core.fakes import fake_scenario
from stranded_physics.packs.builder import build_pack, save_pack

SCENARIOS = {"fake": fake_scenario}
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

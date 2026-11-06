"""The Titanic against the 1912 record. Each mode prints a final JSON line for the gate runner.

python -m stranded_physics.validation.titanic saved_all|saved_adult_male|saved_adult_female|saved_child|saved_first_class|saved_second_class|saved_third_class|saved_crew
python -m stranded_physics.validation.titanic minds     every mind side by side, reported with no target
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

from stranded_physics.entities.api import load_scenario
from stranded_physics.entities.build import to_spec
from stranded_physics.packs.builder import build_pack
from stranded_physics.runtime.ship import play_ship, summary

ROOT = Path(__file__).resolve().parents[2]
CARD = ROOT / "stranded_physics/scenario_cards/titanic_1912.toml"
CACHE = ROOT / "artifacts/physics/cache"
SEED = 1  # One seed. Fixed before any run, and the same for every gate.
CREW = ("crew_deck", "crew_engine", "crew_victualling")


def run(mind: str | None = None) -> dict[str, object]:
    """One full run takes minutes, and there are eight gates, so the result is kept against a hash of everything it depends on."""
    digest = hashlib.sha256((mind or "card").encode())
    for pattern in (
        "stranded_physics/runtime/*.py",
        "stranded_physics/domains/ship/*",
        "stranded_physics/domains/sea/*",
        "stranded_physics/entities/*.py",
        "stranded_physics/validation/titanic.py",
        "stranded_physics/scenario_cards/titanic_1912.toml",
        "mind/*.py",
        "contracts.py",
    ):
        for path in sorted(ROOT.glob(pattern)):
            if path.is_file():
                digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
    kept = CACHE / f"titanic_{digest.hexdigest()[:24]}.json"
    if kept.exists():
        return json.loads(kept.read_text(encoding="utf-8"))
    scenario = load_scenario(CARD)
    if mind:
        scenario = replace(scenario, entities=tuple(replace(e, mind=mind) if e.kind == "passengers" else e for e in scenario.entities))
    pack = build_pack(to_spec(scenario, SEED), SEED)
    people = play_ship(pack, scenario)
    result = summary(people)
    crew = [p for p in people if p.passenger.cohort in CREW]
    result["crew"] = sum(p.agent.alive for p in crew) / len(crew)
    foundered = [i for i, value in enumerate(pack.series("ship.afloat")) if value == 0]
    result["foundered_step"] = foundered[0] if foundered else None
    result["water_deaths"] = sum(p.agent.cause == "immersion" for p in people)
    result["other_deaths"] = sum(not p.agent.alive and p.agent.cause != "immersion" for p in people)
    result["people"] = len(people)
    CACHE.mkdir(parents=True, exist_ok=True)
    kept.write_text(json.dumps(result), encoding="utf-8")
    return result


def main(argv: list[str]) -> int:
    if argv == ["minds"]:
        print(json.dumps({mind: run(mind) for mind in ("quantum", "classical_mixture", "classical")}))
        return 0
    if len(argv) != 1 or not argv[0].startswith("saved_"):
        print(__doc__)
        return 2
    result = run()
    print(json.dumps({"value": result[argv[0].removeprefix("saved_")], "people": result["people"], "in_boats": result["in_boats"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

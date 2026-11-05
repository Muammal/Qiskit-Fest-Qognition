"""Checks a scenario against the engine. A scenario lists the parts it uses, and this reports what each part can honestly support.

    python -m stranded_physics.check stranded_physics/scenario_cards/st_vincent_2021.toml

Exits nonzero when a part has no model, or a model has not passed its own tests. A passing check doesn't mean a scenario is true:
it says which claims have evidence. Agreement with reality counts only for the place a gate measured, and never carries over.
"""
from __future__ import annotations

import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from stranded_physics import gates
from stranded_physics.core.api import InterfaceError
from stranded_physics.core.records import load_parameters
from stranded_physics.entities.api import parse_scenario

CARD_KEYS = {"id", "title", "place", "uses"}
PLACES = ("real", "fictional", "generated")
NOT_MODEL_FILES = {"__init__.py", "measure.py", "fetch.py"}
CANNOT_RUN, NOT_VERIFIED = "CANNOT RUN", "NOT VERIFIED"
DISAGREES = "DISAGREES WITH EVERY SCORED OBSERVATION"
NOT_VALIDATED, PARTLY, AGREES = "VERIFIED, NOT VALIDATED HERE", "PARTLY VALIDATED", "AGREES WITH EVERY SCORED OBSERVATION"


@dataclass(frozen=True)
class Card:
    id: str
    title: str
    place: str
    uses: tuple[str, ...]
    evidence: frozenset[str] = frozenset()  # Gate scenarios that speak about this one. Its own id is always among them.
    variants: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class PartReport:
    category: str
    has_model: bool
    verification: str  # PASS, FAIL, NOT_RUN or NONE.
    agrees: tuple[str, ...]
    disagrees: tuple[str, ...]
    anchors_failing: tuple[str, ...]
    unscored: tuple[str, ...]
    assumptions: int
    parameters: int


def read_card(path: Path) -> Card:
    table = tomllib.loads(path.read_text(encoding="utf-8"))
    if "entity" in table:  # A full scenario file: its parts come from its entities.
        scenario = parse_scenario(table, str(path))
        return Card(scenario.id, scenario.title, scenario.place, scenario.uses(), scenario.evidence_ids(), scenario.variants())
    unknown = set(table) - CARD_KEYS
    missing = CARD_KEYS - set(table)
    if unknown or missing:
        raise InterfaceError(f"{path}: unknown keys {sorted(unknown)}, missing keys {sorted(missing)}")
    if table["place"] not in PLACES:
        raise InterfaceError(f"{path}: place must be one of {PLACES}")
    known = gates.categories()
    strange = [c for c in table["uses"] if c not in known]
    if strange:
        raise InterfaceError(f"{path}: no such categories {strange}. Known: {known}")
    return Card(table["id"], table["title"], table["place"], tuple(table["uses"]))


def has_model(category: str) -> bool:
    return any(p.name not in NOT_MODEL_FILES for p in (gates.DOMAINS / category).glob("*.py"))


def sort_gates(rows: list[tuple[dict, str]], card_id: str | frozenset[str], variant: str | None = None) -> dict[str, list[str]]:
    """Files each gate under what it can honestly say about this scenario. Pure, so its rules can be tested directly.

    A real-world result belongs to the model that produced it, so one model's result never counts for another.
    """
    ids = {card_id} if isinstance(card_id, str) else card_id
    sorted_rows: dict[str, list[str]] = {"verification": [], "agrees": [], "disagrees": [], "anchors_failing": [], "unscored": []}
    for gate, verdict in rows:
        title = gate.get("title", gate["id"])
        if gate["kind"] != "validation":
            sorted_rows["verification"].append(verdict)
            continue
        if gate.get("scenario") not in ids or gate.get("model") != variant:
            continue  # Evidence from another place, or another model, says nothing here.
        if gate.get("role") == "prediction" and gate.get("split") == "holdout" and verdict in ("PASS", "FAIL"):
            sorted_rows["agrees" if verdict == "PASS" else "disagrees"].append(title)
        elif verdict == "FAIL":
            sorted_rows["anchors_failing"].append(title)
        elif verdict == "PASS" and gate.get("role") == "prediction":
            sorted_rows["unscored"].append(f"{title} (passed, but not a blind test, so it isn't counted)")
        elif verdict != "PASS":
            sorted_rows["unscored"].append(f"{title} ({verdict})")
    return sorted_rows


def verification_status(verdicts: list[str]) -> str:
    if not verdicts:
        return "NONE"
    if "FAIL" in verdicts:
        return "FAIL"
    return "PASS" if all(v == "PASS" for v in verdicts) else "NOT_RUN"


def assess(category: str, card_id: str | frozenset[str], variant: str | None = None) -> PartReport:
    rows = [(gate, gates.current_verdict(category, gate)) for gate in gates.load_gates(category)]
    filed = sort_gates(rows, card_id, variant)
    parameters = load_parameters(gates.DOMAINS / category / "params.toml")
    return PartReport(category, has_model(category), verification_status(filed["verification"]), tuple(filed["agrees"]), tuple(filed["disagrees"]),
                      tuple(filed["anchors_failing"]), tuple(filed["unscored"]), sum(p.status == "assumption" for p in parameters), len(parameters))


def overall(parts: list[PartReport]) -> str:
    if any(not p.has_model for p in parts):
        return CANNOT_RUN
    if any(p.verification != "PASS" for p in parts):
        return NOT_VERIFIED
    agrees, disagrees = sum(len(p.agrees) for p in parts), sum(len(p.disagrees) for p in parts)
    if not agrees and not disagrees:
        return NOT_VALIDATED
    if not agrees:
        return DISAGREES
    return AGREES if not disagrees else PARTLY


def report(card: Card, parts: list[PartReport]) -> str:
    lines = [f"Scenario: {card.title} ({card.id}), {card.place} place", "",
             f"{'Part':<10}{'Model':<7}{'Own tests':<11}{'Agrees':<8}{'Disagrees':<11}Assumed values"]
    for part in parts:
        lines.append(f"{part.category:<10}{'yes' if part.has_model else 'NO':<7}{part.verification:<11}{len(part.agrees):<8}{len(part.disagrees):<11}{part.assumptions} of {part.parameters}")
    lines += ["", f"Result: {overall(parts)}"]
    for label, attribute in (("Agrees with reality", "agrees"), ("Disagrees with reality", "disagrees"), ("Reference checks failing", "anchors_failing"), ("Reported, not scored", "unscored")):
        items = [f"  {part.category}: {item}" for part in parts for item in getattr(part, attribute)]
        if items:
            lines += ["", f"{label}:", *items]
    missing = [part.category for part in parts if not part.has_model]
    if missing:
        lines += ["", f"No model yet: {', '.join(missing)}. Add one in that category's folder, with gates, before this scenario can run."]
    if card.place == "fictional":
        lines += ["", "This place is fictional, so no result can be compared with reality. Each part's own tests still apply."]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    card = read_card(Path(argv[0]))
    parts = [assess(category, card.evidence or card.id, card.variants.get(category)) for category in card.uses]
    print(report(card, parts))
    return 1 if overall(parts) in (CANNOT_RUN, NOT_VERIFIED) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

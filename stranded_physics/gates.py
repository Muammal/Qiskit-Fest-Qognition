"""Runs and checks gates. Exits nonzero on failure, so a bad merge cannot pass quietly.

    python -m stranded_physics.gates run <category>     run a category's gates, record verdicts
    python -m stranded_physics.gates check <gate ids>   must all hold, with fresh input hashes
    python -m stranded_physics.gates required           check every required gate (used by CI)
    python -m stranded_physics.gates claims             regenerate workboard/CLAIMS.md from verdicts
"""
from __future__ import annotations

import hashlib
import json
import shlex
import subprocess
import sys
import tomllib
from pathlib import Path

from stranded_physics.core.api import InterfaceError
from stranded_physics.core.verdicts import judge_rate, judge_value

ROOT = Path(__file__).resolve().parents[1]
DOMAINS = Path(__file__).resolve().parent / "domains"
GATE_KEYS = {"id", "title", "kind", "command", "inputs", "required", "target", "tolerance", "rate_low", "rate_high", "role", "split", "expect", "source", "scenario"}
OK_FOR_DONE = {"PASS"}


def load_gates(category: str) -> list[dict]:
    path = DOMAINS / category / "gates.toml"
    table = tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    gates = table.get("gate", [])
    for gate in gates:
        unknown = set(gate) - GATE_KEYS
        if unknown:
            raise InterfaceError(f"{path}: {gate.get('id')}: unknown keys {sorted(unknown)}")
        if gate.get("kind") not in ("verification", "validation", "invariant"):
            raise InterfaceError(f"{path}: {gate.get('id')}: kind must be verification, validation or invariant")
    return gates


def categories() -> list[str]:
    return sorted(p.name for p in DOMAINS.iterdir() if (p / "category.toml").exists())


def all_gates() -> dict[str, tuple[str, dict]]:
    return {gate["id"]: (category, gate) for category in categories() for gate in load_gates(category)}


def input_hash(gate: dict) -> str:
    """Covers the inputs and the committed target. Changing either makes the old verdict stale."""
    digest = hashlib.sha256(json.dumps({k: gate.get(k) for k in ("command", "target", "tolerance", "rate_low", "rate_high")}, sort_keys=True).encode())
    for pattern in gate.get("inputs", []):
        for path in sorted(ROOT.glob(pattern)):
            if path.is_file():
                digest.update(path.relative_to(ROOT).as_posix().encode())
                digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()


def _verdict_path(category: str) -> Path:
    return DOMAINS / category / "verdicts.json"


def read_verdicts(category: str) -> dict:
    path = _verdict_path(category)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def judge(gate: dict, returncode: int, output: str) -> dict:
    """A command prints a final JSON line of {"value": x} or {"successes": k, "trials": n}, or just exits."""
    measured: dict = {}
    for line in reversed(output.strip().splitlines()):
        if line.startswith("{"):
            try:
                measured = json.loads(line)
            except ValueError:
                continue
            break
    if returncode != 0:
        return {"verdict": "FAIL", **measured}
    if "rate_low" in gate or "rate_high" in gate:
        return {"verdict": judge_rate(measured.get("successes", 0), measured.get("trials", 0), gate.get("rate_low"), gate.get("rate_high")), **measured}
    if "target" in gate:
        return {"verdict": judge_value(measured.get("value"), gate.get("target"), gate.get("tolerance")), **measured}
    # An analytic or invariant test holds its tolerance in committed test code, so a clean exit is a pass.
    if gate["kind"] in ("verification", "invariant"):
        return {"verdict": "PASS", **measured}
    return {"verdict": "NO_TARGET", **measured}


def run_category(category: str) -> int:
    results = read_verdicts(category)
    failed = 0
    for gate in load_gates(category):
        done = subprocess.run([sys.executable if part == "python" else part for part in shlex.split(gate["command"])],
                              cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        result = judge(gate, done.returncode, done.stdout)
        results[gate["id"]] = {**result, "hash": input_hash(gate)}
        failed += result["verdict"] == "FAIL"
        print(f"{gate['id']}: {result['verdict']}")
    _verdict_path(category).write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return 1 if failed else 0


def current_verdict(category: str, gate: dict) -> str:
    recorded = read_verdicts(category).get(gate["id"])
    if recorded is None or recorded.get("hash") != input_hash(gate):
        return "NOT_RUN"
    return recorded["verdict"]


def check(gate_ids: list[str]) -> int:
    known, bad = all_gates(), 0
    for gate_id in gate_ids:
        if gate_id not in known:
            print(f"{gate_id}: unknown gate")
            bad += 1
            continue
        category, gate = known[gate_id]
        verdict = current_verdict(category, gate)
        allowed = {gate["expect"]} if "expect" in gate else OK_FOR_DONE
        print(f"{gate_id}: {verdict}")
        bad += verdict not in allowed
    return 1 if bad else 0


def required() -> int:
    return check([gate_id for gate_id, (_, gate) in all_gates().items() if gate.get("required")])


def claims() -> int:
    rows = ["# Claims", "", "Generated by `python -m stranded_physics.gates claims`. Do not edit by hand.", "",
            "| Category | Gate | Kind | Role | Split | Verdict |", "|---|---|---|---|---|---|"]
    for gate_id, (category, gate) in all_gates().items():
        rows.append(f"| {category} | {gate.get('title', gate_id)} | {gate['kind']} | {gate.get('role', '-')} | {gate.get('split', '-')} | {current_verdict(category, gate)} |")
    (ROOT / "workboard" / "CLAIMS.md").write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    command, *rest = argv
    if command == "run" and len(rest) == 1:
        return run_category(rest[0])
    if command == "check" and rest:
        return check(rest)
    if command == "required":
        return required()
    if command == "claims":
        return claims()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

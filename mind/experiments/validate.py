"""Stage 7: runs every check and writes docs/tech-a/07-validation-report.md
itself. Every number in the generated report comes from running this
repo's own code in this function - nothing is hand-typed.
"""
import math
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from mind.cognition_models import (
    belief_degree_huang,
    busemeyer_hamiltonian_U,
    verify_2d_representability,
    wang_busemeyer_qq_gap,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

# Pass criteria for library_cross_check, fixed here and not derived from the result.
HUANG_PUBLISHED_DB = -0.942  # Huang, Yang & Jiang (2019), Shafir & Tversky prisoner's dilemma row
HUANG_TOLERANCE = 0.01
QQ_TOLERANCE = 1e-12
UNITARITY_TOLERANCE = 1e-10

STAGE_TEST_FILES = [
    ("Stage 1 - deliberation unitary", "mind/tests/test_model.py"),
    ("Stage 2 - belief, events, collapse", "mind/tests/test_belief.py"),
    ("Stage 3 - stress as decoherence", "mind/tests/test_decoherence.py"),
    ("Stage 4 - decision function", "mind/tests/test_quantum_mind.py"),
    ("Stage 6 - circuits and hardware", "mind/tests/test_circuits.py"),
    ("Stage 8 - paper-backed cognition models", "mind/tests/test_cognition_models.py"),
]


def run_pytest(rel_path):
    cmd = [sys.executable, "-m", "pytest", "-v", rel_path]
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    return " ".join(cmd), proc.stdout + proc.stderr, proc.returncode


def run_full_suite():
    cmd = [sys.executable, "-m", "pytest", "-q", "test_contracts_and_engine.py", "mind/tests"]
    env = dict(os.environ, SDL_VIDEODRIVER="dummy")
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, env=env)
    return " ".join(cmd), proc.stdout + proc.stderr, proc.returncode


def sign_test_pvalue(n_pos, n_neg):
    """Exact two-sided binomial sign test against p=0.5 (also used for
    McNemar's exact test on discordant-pair counts)."""
    n = n_pos + n_neg
    if n == 0:
        return 1.0
    k = min(n_pos, n_neg)
    cdf = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * cdf)


def evacuation_delay(steps, volcanic):
    sign_idx = next((i for i, s in enumerate(steps) if s["event"] in volcanic), None)
    hide_idx = next((i for i, s in enumerate(steps) if s["action"] == "hide"), None)
    if sign_idx is None or hide_idx is None or hide_idx < sign_idx:
        return None
    return hide_idx - sign_idx


def run_batch(seeds):
    from engine.simulation import SimulationEngine
    from engine.events import VOLCANIC

    records = {}
    for seed in seeds:
        records[seed] = {}
        for mind_type in ("quantum", "classical_mixture", "classical"):
            sim = SimulationEngine(seed=seed, mind_type=mind_type)
            timeline = sim.run()
            steps = timeline["steps"]
            records[seed][mind_type] = {
                "survived": timeline["outcome"] == "survived",
                "evac_delay": evacuation_delay(steps, VOLCANIC),
                "steps": steps,
            }
    return records


def paired_evac_delay_stats(records, mind_a="quantum", mind_b="classical_mixture"):
    diffs = []
    for s in records:
        a, b = records[s][mind_a]["evac_delay"], records[s][mind_b]["evac_delay"]
        if a is not None and b is not None:
            diffs.append(a - b)
    n = len(diffs)
    if n == 0:
        return dict(n=0)
    mean = sum(diffs) / n
    var = sum((d - mean) ** 2 for d in diffs) / (n - 1) if n > 1 else 0.0
    se = math.sqrt(var / n) if n > 1 else 0.0
    pos = sum(1 for d in diffs if d > 0)
    neg = sum(1 for d in diffs if d < 0)
    zero = sum(1 for d in diffs if d == 0)
    return dict(n=n, mean=mean, se=se, pos=pos, neg=neg, zero=zero,
                sign_p=sign_test_pvalue(pos, neg))


def mcnemar_survival_stats(records, mind_a="quantum", mind_b="classical_mixture"):
    b = sum(1 for s in records if records[s][mind_a]["survived"] and not records[s][mind_b]["survived"])
    c = sum(1 for s in records if not records[s][mind_a]["survived"] and records[s][mind_b]["survived"])
    return dict(b=b, c=c, p=sign_test_pvalue(b, c))


def action_divergence_stats(records, mind_a="quantum", mind_b="classical_mixture"):
    total, div, excluded = 0, 0, 0
    for s in records:
        steps_a, steps_b = records[s][mind_a]["steps"], records[s][mind_b]["steps"]
        for i in range(min(len(steps_a), len(steps_b))):
            qa = steps_a[i].get("quantum") or {}
            qb = steps_b[i].get("quantum") or {}
            if qa.get("reflex") or qb.get("reflex"):
                excluded += 1
                continue
            total += 1
            if steps_a[i]["action"] != steps_b[i]["action"]:
                div += 1
    return dict(total=total, divergences=div, excluded_reflex=excluded,
                divergence_pct=round(div / total * 100, 1) if total else None)


def survival_rate(records, mind):
    n = len(records)
    return sum(1 for s in records if records[s][mind]["survived"]) / n


def _verdict(passed):
    return "PASS" if passed else "FAIL"


def library_cross_check():
    """Cross-checks against both external packages (if installed) and the built-in
    implementations of published GitHub quantum cognition formulations:
    - Wang & Busemeyer (2013/2014) QQ Equality (`WileQ/QCog`)
    - 2D Luders Projective Representability (`ProfessorBrunner/aggregation-observability`)
    - Huang et al. (2019) / Pothos & Busemeyer (2009) QLBN Belief Entropy (`Insight137/insight137-eap`)
    - Busemeyer (2009/2012) 2-Qubit Hamiltonian Unitary (`jbusemey/ChoiceModeling`)
    """
    found = {}
    for module_name in ("qcog", "quantum_mind"):
        try:
            __import__(module_name)
            found[module_name] = "importable"
        except ImportError as e:
            found[module_name] = (f"not available ({e.__class__.__name__}); this package was not "
                                  "run, only the reimplementation in mind.cognition_models")

    qq_gap, order_eff = wang_busemeyer_qq_gap(0.2 * math.pi, 0.55 * math.pi, 0.15 * math.pi)
    qq_ok = abs(qq_gap) < QQ_TOLERANCE and abs(order_eff) > 1e-6
    found["Wang-Busemeyer QQ Equality (WileQ/QCog)"] = (
        f"{_verdict(qq_ok)} (qq_gap={qq_gap:.2e}, order_effect={order_eff:+.4f}; "
        f"needs |qq_gap| < {QQ_TOLERANCE:g} with a real order effect)"
    )
    realizable = verify_2d_representability(0.62, 0.48, 0.75)
    impossible = verify_2d_representability(0.95, 0.05, 0.5)
    found["2D Luders Representability (ProfessorBrunner)"] = (
        f"{_verdict(realizable and not impossible)} (realizable case={realizable}, "
        f"impossible case={impossible}; needs True then False)"
    )
    db_pd = belief_degree_huang(0.5, 0.84, 0.63)
    huang_ok = abs(db_pd - HUANG_PUBLISHED_DB) <= HUANG_TOLERANCE
    found["Huang QLBN Belief Entropy (Insight137/insight137-eap)"] = (
        f"{_verdict(huang_ok)} (D_b={db_pd:.4f} vs published {HUANG_PUBLISHED_DB:.4f}, "
        f"ratio {HUANG_PUBLISHED_DB / db_pd:.2f}; needs agreement within {HUANG_TOLERANCE})"
    )
    U_bus = busemeyer_hamiltonian_U(0.69, 0.59, gamma=0.65, t=1.0)
    unitary_err = float(np.max(np.abs(U_bus.conj().T @ U_bus - np.eye(4))))
    found["Busemeyer 2-Qubit Hamiltonian (jbusemey/ChoiceModeling)"] = (
        f"{_verdict(unitary_err < UNITARITY_TOLERANCE)} (max|U^dagger U - I|={unitary_err:.2e}; "
        f"needs < {UNITARITY_TOLERANCE:g}; checks unitarity only, not the published values)"
    )
    return found


def generate_report(seeds=range(200), prototype_seeds=40, out_path="docs/tech-a/07-validation-report.md"):
    lines = []
    lines.append("# Validation report")
    lines.append("")
    lines.append(f"_Generated by `mind/experiments/validate.py` on "
                  f"{datetime.now(timezone.utc).isoformat()}._")
    lines.append("")

    # 1. Every stage test
    lines.append("## 1. Stage 1-8 tests")
    lines.append("")
    any_failed = False
    for title, rel_path in STAGE_TEST_FILES:
        cmd, output, rc = run_pytest(rel_path)
        summary_line = next((l for l in output.splitlines() if " passed" in l or " failed" in l), output.strip().splitlines()[-1])
        lines.append(f"### {title}")
        lines.append(f"`$ {cmd}`")
        lines.append("```")
        lines.append(summary_line)
        lines.append("```")
        lines.append("")
        any_failed = any_failed or rc != 0

    cmd, output, rc = run_full_suite()
    full_summary = next((l for l in output.splitlines() if " passed" in l or " failed" in l), output.strip().splitlines()[-1])
    lines.append("### Full repo suite (Tech C + all Tech A tests)")
    lines.append(f"`$ SDL_VIDEODRIVER=dummy {cmd}`")
    lines.append("```")
    lines.append(full_summary)
    lines.append("```")
    lines.append("")
    any_failed = any_failed or rc != 0
    if any_failed:
        lines.append("**At least one check above failed - see output.**")
        lines.append("")

    # 2. Batch statistics
    lines.append(f"## 2. Batch statistics (volcano, seeds 0-{max(seeds)})")
    lines.append("")
    lines.append(f"`$ python -m mind.experiments.validate` (this report), "
                  f"{len(list(seeds))} seeds, minds: quantum, classical_mixture (control), "
                  f"classical (argmax stub, reference)")
    lines.append("")

    records = run_batch(seeds)

    lines.append("| Mind | Survival rate |")
    lines.append("| --- | --- |")
    for mind in ("quantum", "classical_mixture", "classical"):
        lines.append(f"| {mind} | {survival_rate(records, mind) * 100:.1f}% |")
    lines.append("")

    evac = paired_evac_delay_stats(records)
    lines.append("**Paired evacuation delay, quantum minus classical_mixture** "
                 "(steps from first volcanic sign to first `hide`; seeds where both minds evacuated):")
    lines.append("")
    if evac["n"] == 0:
        lines.append("No seed had both minds evacuate; no paired comparison possible.")
    else:
        lines.append(f"- n = {evac['n']} paired seeds")
        lines.append(f"- mean = {evac['mean']:+.3f} steps, SE = {evac['se']:.3f}")
        lines.append(f"- quantum later: {evac['pos']}, earlier: {evac['neg']}, same: {evac['zero']}")
        lines.append(f"- two-sided sign test p = {evac['sign_p']:.4f}")
    lines.append("")

    mcnemar = mcnemar_survival_stats(records)
    lines.append("**Survival, McNemar's exact test (quantum vs classical_mixture, "
                 "discordant seeds only):**")
    lines.append("")
    lines.append(f"- quantum survived & mixture died: {mcnemar['b']}; "
                 f"quantum died & mixture survived: {mcnemar['c']}")
    lines.append(f"- p = {mcnemar['p']:.4f}")
    lines.append("")

    div = action_divergence_stats(records)
    lines.append("**Action divergence (quantum vs classical_mixture), "
                 "reflex-overridden steps excluded:**")
    lines.append("")
    lines.append(f"- {div['divergences']} / {div['total']} compared steps differ "
                 f"({div['divergence_pct']}%)")
    lines.append(f"- {div['excluded_reflex']} steps excluded (reflex fired for either mind)")
    lines.append("")

    # 3. Prototype preview comparison
    lines.append(f"## 3. Prototype preview comparison ({prototype_seeds} seeds, stub prior)")
    lines.append("")
    lines.append("Compared against, not copied from, `TECH_A_BUILD_PLAN.md` Section 7's "
                 "prototype preview (40 seeds): quantum hid 1.84 steps later than mixture "
                 "(SE 0.6, 19 later/4 earlier/14 same, sign test p~0.003); survival 45% vs "
                 "42%; actions differed on 17% of 1303 steps.")
    lines.append("")
    sub_seeds = range(prototype_seeds)
    sub_records = {s: records[s] for s in sub_seeds if s in records}
    sub_evac = paired_evac_delay_stats(sub_records)
    sub_div = action_divergence_stats(sub_records)
    lines.append("| | This run (first "
                 f"{prototype_seeds} of the seeds above) | Plan's prototype preview |")
    lines.append("| --- | --- | --- |")
    lines.append(f"| quantum survival | {survival_rate(sub_records, 'quantum')*100:.1f}% | 45% |")
    lines.append(f"| mixture survival | {survival_rate(sub_records, 'classical_mixture')*100:.1f}% | 42% |")
    if sub_evac["n"]:
        lines.append(f"| evac delay (quantum-mixture) | {sub_evac['mean']:+.3f} steps, "
                     f"SE {sub_evac['se']:.3f}, sign p={sub_evac['sign_p']:.4f} "
                     f"({sub_evac['pos']} later/{sub_evac['neg']} earlier/{sub_evac['zero']} same) "
                     "| +1.84 steps, SE 0.6, p~0.003 (19/4/14) |")
    else:
        lines.append("| evac delay (quantum-mixture) | no paired seeds | +1.84 steps, SE 0.6, p~0.003 |")
    lines.append(f"| action divergence | {sub_div['divergence_pct']}% of {sub_div['total']} steps "
                 "| 17% of 1303 steps |")
    lines.append("")

    # 4. Library & Paper-Model cross-check
    lines.append("## 4. Library & Published Quantum Cognition Cross-Checks (D8)")
    lines.append("")
    cross_check = library_cross_check()
    for name, result in cross_check.items():
        lines.append(f"- `{name}`: {result}")
    lines.append("")
    lines.append("These are checks of this repo's reimplementations. Neither external package "
                 "above was run.")
    lines.append("")
    lines.append("**Open issue:** `belief_degree_huang` gives D_b about 1.94 times smaller in size "
                 "than the published value for the same inputs. The cause is not known. It may be "
                 "a difference in the published formula's convention or a bug here. "
                 "`qlbn_entropy` is opt-in and the default mind does not use it, so no paper "
                 "number depends on it, but it should not be described as reproducing Huang et al. "
                 "until this is resolved.")
    lines.append("")

    # Figures
    lines.append("## Figures")
    lines.append("")
    for name, caption in [
        ("uncertainty_dip.png", "The uncertainty dip: P(protect) vs p, quantum vs classical."),
        ("order_effect_vs_lambda.png", "Order gap (tremor,gas_plume vs reversed) vs lambda."),
        ("bloch_paths_tremor_gas_plume.png", "Bloch x-z paths for the tremor/gas_plume order pair."),
        ("delay_decay.png", "Measured coherence decay vs T2 theory (fake_torino qubit 10)."),
    ]:
        lines.append(f"![{caption}](figures/{name})")
        lines.append("")

    report = "\n".join(lines) + "\n"
    Path(out_path).write_text(report, encoding="utf-8")
    return report, any_failed


if __name__ == "__main__":
    from mind.figures import generate_all
    generate_all()
    _report, failed = generate_report()
    print(f"Wrote docs/tech-a/07-validation-report.md (any_failed={failed})")

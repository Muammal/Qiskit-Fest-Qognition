"""Extra analyses on the published human data. Protocol: docs/protocols/2c_human_data.md.

    python -m mind.human_tests.extended

Writes mind/human_tests/extended_results.json and docs/HUMAN_DATA_RESULTS.md.
PRE_REGISTERED.md and contest.py are not changed: Tests 1 to 3 stand as they were
scored. Everything here is additional, and every row is reported.
"""
from __future__ import annotations

import itertools
import json
from datetime import date
from pathlib import Path

import numpy as np

from mind.config import ETA, MARKOV_HESITATION, SUPERPOSED_PHI
from mind.human_tests.contest import CELLS, _rows, first_order_angles, first_order_table, question_order, report
from mind.model import kappa_max, p_protect_closed_form, p_protect_superposed

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PHI_GRID = np.linspace(-np.pi, np.pi, 721)


def known_rows():
    return [dict(study=r["study"], a=float(r["known_a"]), b=float(r["known_b"]), seen=float(r["unknown"]),
                 scored=r["scored"] == "yes") for r in _rows("disjunction.csv")]


def markov_prediction(row, hesitation):
    return (1 - hesitation) * (row["a"] + row["b"]) / 2


def fit_markov(rows):
    """Least-squares h for (1 - h) * average, clipped to [0, 1]."""
    means = np.array([(r["a"] + r["b"]) / 2 for r in rows])
    seen = np.array([r["seen"] for r in rows])
    return float(np.clip(1 - means @ seen / (means @ means), 0.0, 1.0))


def markov_split_half(rows):
    """Every way of fitting on half the scored rows and scoring on the rest. 7 rows split 3/4 and 4/3."""
    fits, errors, per_row = [], [], {r["study"]: [] for r in rows}
    for size in (len(rows) // 2, len(rows) - len(rows) // 2):
        for train in itertools.combinations(range(len(rows)), size):
            hesitation = fit_markov([rows[i] for i in train])
            fits.append(hesitation)
            held = [rows[i] for i in range(len(rows)) if i not in train]
            errors.append(float(np.mean([abs(markov_prediction(r, hesitation) - r["seen"]) for r in held])))
            for r in held:
                per_row[r["study"]].append(markov_prediction(r, hesitation))
    return dict(splits=len(fits), h_median=float(np.median(fits)), h_min=min(fits), h_max=max(fits),
                held_out_error=float(np.mean(errors)), prediction={k: float(np.mean(v)) for k, v in per_row.items()})


def study_eta(row):
    """The eta that would hit this study exactly, before and after the [-1, 1] limit."""
    k_max = kappa_max(row["a"], row["b"])
    raw = (row["seen"] - (row["a"] + row["b"]) / 2) / (np.sqrt(row["a"] * row["b"]) * k_max)
    return float(raw), float(np.clip(raw, -1.0, 1.0))


def predict_eta(row, eta):
    return float(p_protect_closed_form(.5, 1., row["a"], row["b"], eta))


def eta_leave_one_out(rows):
    out = []
    for i, row in enumerate(rows):
        others = [study_eta(r)[1] for j, r in enumerate(rows) if j != i]
        eta = float(np.mean(others))
        raw, clipped = study_eta(row)
        out.append(dict(study=row["study"], eta_exact=raw, eta_usable=clipped, blocked=abs(raw) > 1,
                        own_eta_prediction=predict_eta(row, clipped), eta_from_others=eta, loo_prediction=predict_eta(row, eta)))
    return out


def fit_phi(rows):
    errors = [np.mean([abs(p_protect_superposed(.5, 1., r["a"], r["b"], ETA, phi) - r["seen"]) for r in rows]) for phi in PHI_GRID]
    return float(PHI_GRID[int(np.argmin(errors))])


def phi_leave_one_out(rows):
    out = []
    for i, row in enumerate(rows):
        phi = fit_phi([r for j, r in enumerate(rows) if j != i])
        reach = [p_protect_superposed(.5, 1., row["a"], row["b"], ETA, value) for value in PHI_GRID]
        out.append(dict(study=row["study"], phi_from_others=phi, loo_prediction=float(p_protect_superposed(.5, 1., row["a"], row["b"], ETA, phi)),
                        reach_low=float(min(reach)), reach_high=float(max(reach)),
                        bound_low=float((row["a"] + row["b"]) / 2 - np.sqrt((1 - row["a"]) * (1 - row["b"])))))
    return out


def first_order_fit():
    """How well the two-angle model can describe the first order it is fitted to."""
    out = {}
    for row in _rows("question_order.csv"):
        ab = np.array([float(row["ab_" + cell]) for cell in CELLS])
        a, b = first_order_angles(ab)
        fit_gap = .5 * float(np.abs(first_order_table(a, b) - ab).sum())
        out[row["study"]] = dict(fit_tvd=fit_gap, p_b_given_a=float(ab[0] / (ab[0] + ab[1])), p_notb_given_nota=float(ab[3] / (ab[2] + ab[3])))
    return out


def analyse():
    all_rows = known_rows()
    scored = [r for r in all_rows if r["scored"]]
    one, two, summary = report()
    markov = markov_split_half(scored)
    etas = eta_leave_one_out(scored)
    phis = phi_leave_one_out(scored)
    final_phi = fit_phi(scored)
    fit = first_order_fit()
    by_study = {r["study"]: r for r in one}

    def mae(pairs):
        return float(np.mean([abs(p - o) for p, o in pairs]))

    rows = []
    for row, eta, phi in zip(scored, etas, phis):
        base = by_study[row["study"]]
        rows.append(dict(study=row["study"], a=row["a"], b=row["b"], observed=row["seen"], quantum_fixed=base["quantum"],
                         classical_average=base["classical_average"], classical_best=base["classical_best"],
                         markov_held_out=markov["prediction"][row["study"]], **{k: eta[k] for k in ("eta_exact", "blocked", "own_eta_prediction", "eta_from_others", "loo_prediction")},
                         superposed_loo=phi["loo_prediction"], superposed_reach_low=phi["reach_low"], superposed_reach_high=phi["reach_high"], unitary_bound_low=phi["bound_low"]))
    scores = dict(
        quantum_fixed_eta=mae((r["quantum_fixed"], r["observed"]) for r in rows),
        classical_average=mae((r["classical_average"], r["observed"]) for r in rows),
        classical_best=mae((r["classical_best"], r["observed"]) for r in rows),
        markov_held_out=markov["held_out_error"],
        per_study_eta_in_sample=mae((r["own_eta_prediction"], r["observed"]) for r in rows),
        per_study_eta_loo=mae((r["loo_prediction"], r["observed"]) for r in rows),
        superposed_loo=mae((r["superposed_loo"], r["observed"]) for r in rows),
    )
    return dict(eta=ETA, rows=rows, markov=markov, scores=scores, final_phi=final_phi, config_phi=SUPERPOSED_PHI, config_markov=MARKOV_HESITATION,
                test2=two, first_order_fit=fit, summary=summary, not_scored=[r for r in one if not r["scored"]])


def render(result):
    s = result["scores"]
    test2, fit = result["test2"], result["first_order_fit"]
    lines = [
        "# Human data results",
        "",
        f"_Generated by `python -m mind.human_tests.extended` on {date.today().isoformat()}. Do not edit by hand._",
        "",
        "Every row is here, including the ones that go against the quantum model. Tests 1 to 3 follow "
        "[`mind/human_tests/PRE_REGISTERED.md`](../mind/human_tests/PRE_REGISTERED.md) and their scoring code is unchanged. "
        "The extra columns follow [`docs/protocols/2c_human_data.md`](protocols/2c_human_data.md). "
        "A win on any of these rows means a model fits this data better than a rival. It does not show minds are quantum.",
        "",
        "## Test 1: predicting the unknown rate (7 scored rows)",
        "",
        "| Study | Observed | Quantum, fixed η | Classical average | Best classical | Markov, held out | Per-study η, leave-one-out | Superposed, leave-one-out |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in result["rows"]:
        lines.append(f"| {r['study']} | {r['observed']:.2f} | {r['quantum_fixed']:.3f} | {r['classical_average']:.3f} | {r['classical_best']:.3f} | "
                     f"{r['markov_held_out']:.3f} | {r['loo_prediction']:.3f} | {r['superposed_loo']:.3f} |")
    lines += [
        f"| **Mean absolute error** | | **{s['quantum_fixed_eta']:.3f}** | **{s['classical_average']:.3f}** | **{s['classical_best']:.3f}** | "
        f"**{s['markov_held_out']:.3f}** | **{s['per_study_eta_loo']:.3f}** | **{s['superposed_loo']:.3f}** |",
        "",
        "Best classical picks its weight after seeing the answer, so it is deliberately generous. "
        f"Markov is `(1 - h) * average`, fitted on half the rows in every one of {result['markov']['splits']} splits and scored on the rest "
        f"(fitted h ranged {result['markov']['h_min']:.3f} to {result['markov']['h_max']:.3f}, median {result['markov']['h_median']:.3f}). "
        "Its mean is over splits, so it is not exactly the mean of the column.",
        "",
        "Not scored, because `ETA` was solved from this experiment:",
        "",
        "| Study | Observed | Quantum |",
        "| --- | --- | --- |",
    ]
    lines += [f"| {r['study']} | {r['observed']:.2f} | {r['quantum']:.3f} |" for r in result["not_scored"]]
    lines += [
        "",
        "## Per-study η",
        "",
        "`η exact` is the value that would hit the study. Beyond ±1 the study is out of reach of this unitary, however η is chosen. "
        "`Own η` uses that study's own η, limited to ±1, so it is in-sample and only shows the reach. "
        "`Leave-one-out` predicts each study from the mean η of the other six.",
        "",
        "| Study | η exact | Out of reach | Own η | η from others | Leave-one-out | Observed |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in result["rows"]:
        lines.append(f"| {r['study']} | {r['eta_exact']:+.2f} | {'yes' if r['blocked'] else 'no'} | {r['own_eta_prediction']:.3f} | {r['eta_from_others']:+.3f} | {r['loo_prediction']:.3f} | {r['observed']:.2f} |")
    blocked = sum(r["blocked"] for r in result["rows"])
    lines += [
        "",
        f"Mean absolute error: fixed η {s['quantum_fixed_eta']:.3f}; own η (in-sample) {s['per_study_eta_in_sample']:.3f}; leave-one-out {s['per_study_eta_loo']:.3f}. "
        f"{blocked} of 7 studies need |η| > 1.",
        "",
        "## `qr_unitary_superposed`",
        "",
        "`Bound` is the lowest value the default unitary can reach. `Reach` is the range over the angle φ, which shows only that the bound is gone: "
        "reaching a value by choosing φ for that row is not a test. The test is the leave-one-out column above, which picks one φ from the other rows.",
        "",
        "| Study | Observed | Bound | Reach low | Reach high |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r in result["rows"]:
        lines.append(f"| {r['study']} | {r['observed']:.2f} | {r['unitary_bound_low']:.3f} | {r['superposed_reach_low']:.3f} | {r['superposed_reach_high']:.3f} |")
    lines += [
        "",
        f"The one φ fitted on all seven rows is {result['final_phi']:+.3f} rad, stored as `SUPERPOSED_PHI`.",
        "",
        "**What the prompt asked for and what was built differ.** Starting the decision qubit in one fixed superposition in every condition does not remove the bound: "
        "`U|safe,s>` and `U|danger,s>` are still orthogonal, so the same Cauchy-Schwarz argument applies to the new conditional rates. "
        "`mind/tests/test_extended_models.py` shows this numerically. The variant here ties the angle to belief coherence, so a settled belief starts at `|carry>` "
        "and reproduces q_S and q_D, and only an unsettled belief starts in superposition. That adds one fitted parameter, and the model is more flexible as a result, which is not by itself evidence for it.",
        "",
        "## Test 2: predicting the other question order (13 rows)",
        "",
        "`Fit gap` is how far the two-angle model stays from the first order it was fitted to. "
        "The model forces P(B yes | A yes) = P(B no | A no), shown in the next two columns.",
        "",
        "| Study | Classical TVD | Quantum mean | Quantum, better sign | Fit gap | P(B yes given A yes) | P(B no given A no) |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in test2:
        f = fit[r["study"]]
        lines.append(f"| {r['study']} | {r['tvd_classical']:.3f} | {r['tvd_quantum_mean']:.3f} | {r['tvd_quantum_better']:.3f} | {f['fit_tvd']:.3f} | {f['p_b_given_a']:.2f} | {f['p_notb_given_nota']:.2f} |")
    two = result["summary"]["test2"]
    three = result["summary"]["test3"]
    lines += [
        f"| **Mean** | **{two['mean_tvd_classical']:.3f}** | **{two['mean_tvd_quantum']:.3f}** | **{two['mean_tvd_quantum_better_sign']:.3f}** | | | |",
        "",
        f"The quantum predictor loses on all {two['rows']} rows, including with the sign chosen after seeing the answer. The audit is in [`mind/human_tests/AUDIT_2026-11-06.md`](../mind/human_tests/AUDIT_2026-11-06.md). "
        "It found no convention bug: the loss is the two-angle model's own limit.",
        "",
        "## Test 3: each theory's own claim against sampling noise",
        "",
        "| Study | q | z | QQ equality holds | No order effect holds |",
        "| --- | --- | --- | --- | --- |",
    ]
    lines += [f"| {r['study']} | {r['q']:+.3f} | {r['z']:+.2f} | {'yes' if r['qq_survives'] else 'no'} | {'yes' if r['no_order_effect_survives'] else 'no'} |" for r in test2]
    lines += ["", f"QQ equality survives {three['qq_survives']} of {three['rows']}. No order effect survives {three['no_order_effect_survives']} of {three['rows']}. "
              "No order effect implies q = 0, so the classical claim is the stronger bet, and these are not the same size of bet.", ""]
    return "\n".join(lines)


def main():
    result = analyse()
    (HERE / "extended_results.json").write_text(json.dumps(result, indent=1, default=lambda v: v.item() if hasattr(v, "item") else str(v)), encoding="utf-8")
    (REPO / "docs" / "HUMAN_DATA_RESULTS.md").write_text(render(result), encoding="utf-8")
    print(json.dumps(result["scores"], indent=1))
    print("final phi", result["final_phi"], "config phi", result["config_phi"], "h median", result["markov"]["h_median"], "config h", result["config_markov"])


if __name__ == "__main__":
    main()

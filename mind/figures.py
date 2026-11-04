"""Stage 7: figures for docs/tech-a/figures/.

Every figure is generated from this repo's own mind/ code at the time it
runs - no numbers are hand-entered.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from mind.belief import apply_event, prepare_belief, run_events
from mind.model import bloch_vector, p_protect_closed_form

Q_S, Q_D, ETA = 0.69, 0.59, -0.7853897988344999


def fig_uncertainty_dip(out_dir):
    p = np.linspace(0, 1, 400)
    quantum = [p_protect_closed_form(pi, 1.0 if 0 < pi < 1 else 0.0, Q_S, Q_D, ETA) for pi in p]
    # "real belief" x: pure state at this p has x = sqrt(1-(1-2p)^2) (z=1-2p)
    x_pure = np.sqrt(np.clip(1 - (1 - 2 * p) ** 2, 0, 1))
    quantum = [p_protect_closed_form(pi, xi, Q_S, Q_D, ETA) for pi, xi in zip(p, x_pure)]
    classical = [(1 - pi) * Q_S + pi * Q_D for pi in p]

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(p, classical, "--", color="#888888", label="classical total probability")
    ax.plot(p, quantum, "-", color="#6929C4", label="quantum (pure real belief)")
    ax.set_xlabel("p = P(danger)")
    ax.set_ylabel("P(protect)")
    ax.set_title(f"Uncertainty dip (q_S={Q_S}, q_D={Q_D}, eta={ETA:.4f})")
    ax.legend()
    fig.tight_layout()
    fig.savefig(Path(out_dir) / "uncertainty_dip.png", dpi=150)
    plt.close(fig)


def fig_order_effect_vs_lambda(out_dir):
    lams = np.linspace(0, 1, 41)
    gaps = []
    safety = 0.85
    for lam in lams:
        rho0 = prepare_belief(safety)
        a = run_events(rho0, ["storm", "tremor", "gas_plume"], lam)
        b = run_events(rho0, ["storm", "gas_plume", "tremor"], lam)
        xa, _ya, za = bloch_vector(a)
        xb, _yb, zb = bloch_vector(b)
        pa, pb = (1 - za) / 2, (1 - zb) / 2
        Pa = p_protect_closed_form(pa, xa, Q_S, Q_D, ETA)
        Pb = p_protect_closed_form(pb, xb, Q_S, Q_D, ETA)
        gaps.append(Pa - Pb)

    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    ax.plot(lams, gaps, color="#1192E8")
    ax.axhline(0, color="#888888", linewidth=0.8)
    ax.set_xlabel("lambda (dephasing strength)")
    ax.set_ylabel("order gap: P(protect)\n[tremor,gas_plume] - [gas_plume,tremor]")
    ax.set_title("Order effect vanishes as lambda -> 1")
    fig.tight_layout()
    fig.savefig(Path(out_dir) / "order_effect_vs_lambda.png", dpi=150)
    plt.close(fig)


def fig_bloch_paths_tremor_gas_plume(out_dir):
    safety = 0.85
    rho0 = prepare_belief(safety)

    def path(events):
        pts = [bloch_vector(rho0)]
        rho = rho0
        for ev in events:
            rho = apply_event(rho, ev)
            pts.append(bloch_vector(rho))
        return pts

    path_a = path(["tremor", "gas_plume"])
    path_b = path(["gas_plume", "tremor"])

    fig, ax = plt.subplots(figsize=(5, 5))
    theta = np.linspace(0, 2 * np.pi, 200)
    ax.plot(np.cos(theta), np.sin(theta), color="#dddddd", linewidth=1, zorder=0)
    for pts, color, label in [(path_a, "#6929C4", "tremor, gas_plume"),
                               (path_b, "#D12771", "gas_plume, tremor")]:
        xs = [pt[0] for pt in pts]
        zs = [pt[2] for pt in pts]
        ax.plot(xs, zs, "-o", color=color, label=label)
        ax.annotate("start", (xs[0], zs[0]))
    ax.set_xlabel("x")
    ax.set_ylabel("z")
    ax.set_title("Bloch x-z paths: tremor/gas_plume order pair")
    ax.set_aspect("equal")
    ax.legend()
    fig.tight_layout()
    fig.savefig(Path(out_dir) / "bloch_paths_tremor_gas_plume.png", dpi=150)
    plt.close(fig)


def fig_delay_decay(out_dir, delay_json_path="mind/results/delay_experiment.json"):
    import json
    with open(delay_json_path, encoding="utf-8") as f:
        data = json.load(f)

    ts = [row["t_us"] for row in data["rows"]]
    measured = [row["coherence_x_measured"] for row in data["rows"]]
    theory = [row["coherence_theory_exp_t_over_t2"] for row in data["rows"]]

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(ts, theory, "--", color="#888888", label="e^(-t/T2) (theory)")
    ax.plot(ts, measured, "-o", color="#198038", label="measured (fake_torino q10)")
    ax.set_xlabel("delay t (us)")
    ax.set_ylabel("coherence |x|")
    ax.set_title(f"Delay decay vs T2={data['t2_us']:.1f}us ({data['backend']})")
    ax.legend()
    fig.tight_layout()
    fig.savefig(Path(out_dir) / "delay_decay.png", dpi=150)
    plt.close(fig)


def generate_all(out_dir="docs/tech-a/figures"):
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    fig_uncertainty_dip(out_dir)
    fig_order_effect_vs_lambda(out_dir)
    fig_bloch_paths_tremor_gas_plume(out_dir)
    fig_delay_decay(out_dir)


if __name__ == "__main__":
    generate_all()
    print("Figures written to docs/tech-a/figures/")

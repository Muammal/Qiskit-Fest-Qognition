"""Stress as dephasing and open-system Lindblad dynamics (TECH_A_BUILD_PLAN.md Section 4.5).

The gamma trap: Aer's phase_damping_error(gamma) scales coherence by
sqrt(1-gamma), not (1-gamma). Passing lam straight through as gamma is
the bug the plan calls out. With gamma = 1 - (1-lam)**2, sqrt(1-gamma)
equals exactly (1-lam), so lam is a clean per-slot linear decay rate.

Also exports continuous-time GKSL Lindblad open-system evolution
(`lindblad_rhs`, `evolve_lindblad`) from `mind.cognition_models`.
"""
import numpy as np

from mind.cognition_models import evolve_lindblad, lindblad_rhs
from mind.config import REFERENCE_SLOT_SECONDS, STRESS_FLOOR, STRESS_SPAN

__all__ = [
    "decoherence_strength",
    "decoherence_time",
    "lam_for_interval",
    "apply_phase_damping",
    "lindblad_rhs",
    "evolve_lindblad",
]


def decoherence_strength(stress):
    """lam = clamp((stress - STRESS_FLOOR) / STRESS_SPAN, 0, 1). D5."""
    return float(np.clip((stress - STRESS_FLOOR) / STRESS_SPAN, 0.0, 1.0))


def decoherence_time(stress):
    """tau(stress) in seconds, chosen so a 2 h interval gives exactly lam(stress).

    lam = 0 gives inf (no dephasing) and lam = 1 gives 0 (instant dephasing).
    """
    lam = decoherence_strength(stress)
    if lam <= 0.0:
        return float("inf")
    if lam >= 1.0:
        return 0.0
    return float(-REFERENCE_SLOT_SECONDS / np.log1p(-lam))


def lam_for_interval(stress, dt_seconds):
    """lam_slot = 1 - exp(-dt / tau(stress)). At dt = 2 h this equals decoherence_strength."""
    tau = decoherence_time(stress)
    if tau == float("inf"):
        return 0.0
    if tau == 0.0:
        return 1.0 if dt_seconds > 0 else 0.0
    return float(-np.expm1(-dt_seconds / tau))


def apply_phase_damping(rho, lam):
    """Kraus phase-damping channel on a single-qubit density matrix."""
    gamma = 1 - (1 - lam) ** 2
    K0 = np.array([[1.0, 0.0], [0.0, np.sqrt(1 - gamma)]], dtype=complex)
    K1 = np.array([[0.0, 0.0], [0.0, np.sqrt(gamma)]], dtype=complex)
    return K0 @ rho @ K0.conj().T + K1 @ rho @ K1.conj().T

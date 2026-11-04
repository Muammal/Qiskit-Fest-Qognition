"""Stress as dephasing (TECH_A_BUILD_PLAN.md Section 4.5).

The gamma trap: Aer's phase_damping_error(gamma) scales coherence by
sqrt(1-gamma), not (1-gamma). Passing lam straight through as gamma is
the bug the plan calls out. With gamma = 1 - (1-lam)**2, sqrt(1-gamma)
equals exactly (1-lam), so lam is a clean per-slot linear decay rate.
"""
import numpy as np

from mind.config import STRESS_FLOOR, STRESS_SPAN


def decoherence_strength(stress):
    """lam = clamp((stress - STRESS_FLOOR) / STRESS_SPAN, 0, 1). D5."""
    return float(np.clip((stress - STRESS_FLOOR) / STRESS_SPAN, 0.0, 1.0))


def apply_phase_damping(rho, lam):
    """Kraus phase-damping channel on a single-qubit density matrix."""
    gamma = 1 - (1 - lam) ** 2
    K0 = np.array([[1.0, 0.0], [0.0, np.sqrt(1 - gamma)]], dtype=complex)
    K1 = np.array([[0.0, 0.0], [0.0, np.sqrt(gamma)]], dtype=complex)
    return K0 @ rho @ K0.conj().T + K1 @ rho @ K1.conj().T

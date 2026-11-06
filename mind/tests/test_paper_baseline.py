"""Phase 0 baseline guard: the numbers the Qognition paper quotes.

Everything added after this file is opt-in. If any assertion here moves, a
"new" feature changed default behaviour and that feature is wrong, not this
test. Do not relax a tolerance to make a later change pass.
"""
import pytest

from engine.agent import SurvivalAgent
from engine.events import VOLCANIC
from mind.belief import prepare_belief, run_events
from mind.config import ETA
from mind.experiments.validate import (
    mcnemar_survival_stats,
    paired_evac_delay_stats,
    run_batch,
    survival_rate,
)
from mind.model import bloch_vector, p_protect_closed_form
from mind.quantum_mind import classical_mixture_decide, quantum_decide

Q_S, Q_D = 0.69, 0.59


def _p_protect(events, lam, safety=0.85):
    x, _y, z = bloch_vector(run_events(prepare_belief(safety), events, lam))
    return p_protect_closed_form((1 - z) / 2, x, Q_S, Q_D, ETA)


def test_calibration_point():
    assert p_protect_closed_form(0.5, 1.0, Q_S, Q_D, ETA) == pytest.approx(0.36, abs=1e-9)


@pytest.mark.parametrize("lam, gap", [(0, 0.140), (0.25, 0.085), (0.5, 0.043), (0.75, 0.015), (1, 0.0)])
def test_order_gap_against_lambda(lam, gap):
    # The paper reports the size of the gap. Signed, it is negative for
    # (gas_plume, tremor) minus (tremor, gas_plume).
    plume_first = _p_protect(["storm", "gas_plume", "tremor"], lam)
    tremor_first = _p_protect(["storm", "tremor", "gas_plume"], lam)
    assert tremor_first - plume_first == pytest.approx(gap, abs=5e-4)


def test_single_tremor_from_default_start():
    state = SurvivalAgent().get_state()
    assert state["needs"]["safety"] == 0.85
    state["recent_events"] = ["none", "none", "tremor"]
    assert quantum_decide(state)["quantum"]["p_danger"] == pytest.approx(0.634, abs=5e-4)
    assert classical_mixture_decide(state)["quantum"]["p_danger"] == pytest.approx(0.325, abs=5e-4)


@pytest.fixture(scope="module")
def volcano_batch():
    return run_batch(range(200))


def test_volcano_survival(volcano_batch):
    assert survival_rate(volcano_batch, "quantum") == pytest.approx(0.995)
    assert survival_rate(volcano_batch, "classical_mixture") == pytest.approx(0.995)
    assert survival_rate(volcano_batch, "classical") == pytest.approx(1.0)


def test_volcano_paired_delay(volcano_batch):
    stats = paired_evac_delay_stats(volcano_batch)
    assert stats["mean"] == pytest.approx(0.55, abs=5e-4)
    assert stats["se"] == pytest.approx(0.091, abs=5e-4)
    assert (stats["pos"], stats["neg"], stats["zero"]) == (45, 5, 90)


def test_volcano_has_no_discordant_survival_pairs(volcano_batch):
    stats = mcnemar_survival_stats(volcano_batch)
    assert (stats["b"], stats["c"]) == (0, 0)


def test_volcanic_events_are_the_contract_names():
    assert set(VOLCANIC) == {"tremor", "gas_plume", "eruption", "ash_fall"}

"""The scenario checker must never let evidence travel, or count weak evidence as agreement."""
from __future__ import annotations

from pathlib import Path

import pytest

from stranded_physics import check
from stranded_physics.core.api import InterfaceError

CARDS = Path(check.__file__).resolve().parent / "scenario_cards"
PREDICTION = {"id": "g1", "title": "Reach", "kind": "validation", "role": "prediction", "split": "holdout", "scenario": "here"}
ANCHOR = {"id": "g2", "title": "Height", "kind": "validation", "role": "anchor", "split": "reference", "scenario": "here"}
TEST = {"id": "g3", "title": "Tests", "kind": "verification"}


def part(**changes) -> check.PartReport:
    base = dict(category="pdc", has_model=True, verification="PASS", agrees=(), disagrees=(), anchors_failing=(), unscored=(), assumptions=0, parameters=0)
    return check.PartReport(**{**base, **changes})


def test_a_pass_measured_elsewhere_does_not_count_here():
    filed = check.sort_gates([(PREDICTION, "PASS")], "another_island")
    assert filed["agrees"] == [] and filed["disagrees"] == []


def test_a_held_out_prediction_counts_where_it_was_measured():
    assert check.sort_gates([(PREDICTION, "PASS")], "here")["agrees"] == ["Reach"]
    assert check.sort_gates([(PREDICTION, "FAIL")], "here")["disagrees"] == ["Reach"]


def test_an_anchor_never_counts_as_agreement():
    filed = check.sort_gates([(ANCHOR, "PASS")], "here")
    assert filed["agrees"] == []
    assert check.sort_gates([(ANCHOR, "FAIL")], "here")["anchors_failing"] == ["Height"]


def test_a_prediction_without_held_out_data_never_counts_as_agreement():
    not_held_out = {**PREDICTION, "split": "calibration"}
    assert check.sort_gates([(not_held_out, "PASS")], "here")["agrees"] == []


def test_no_target_is_reported_and_never_passes():
    filed = check.sort_gates([(PREDICTION, "NO_TARGET")], "here")
    assert filed["agrees"] == [] and "NO_TARGET" in filed["unscored"][0]


def test_own_tests_must_all_pass_and_have_been_run():
    assert check.verification_status(["PASS", "PASS"]) == "PASS"
    assert check.verification_status(["PASS", "NOT_RUN"]) == "NOT_RUN"
    assert check.verification_status(["PASS", "FAIL", "NOT_RUN"]) == "FAIL"
    assert check.verification_status([]) == "NONE"


@pytest.mark.parametrize("parts, expected", [
    ([part(has_model=False)], check.CANNOT_RUN),
    ([part(verification="NOT_RUN")], check.NOT_VERIFIED),
    ([part(verification="NONE")], check.NOT_VERIFIED),
    ([part()], check.NOT_VALIDATED),
    ([part(agrees=("a",)), part(disagrees=("b",))], check.PARTLY),
    ([part(agrees=("a",))], check.AGREES),
])
def test_overall_result(parts, expected):
    assert check.overall(parts) == expected


def test_a_scenario_using_a_part_with_no_model_cannot_run():
    card = check.read_card(CARDS / "beryl_2024.toml")
    parts = [check.assess(category, card.id) for category in card.uses]
    assert check.overall(parts) == check.CANNOT_RUN
    assert {"storm"} <= {p.category for p in parts if not p.has_model}
    assert "No model yet" in check.report(card, parts) 


def test_a_card_with_a_strange_part_or_key_is_refused(tmp_path):
    path = tmp_path / "bad.toml"
    path.write_text('id = "x"\ntitle = "x"\nplace = "real"\nuses = ["dragons"]\n', encoding="utf-8")
    with pytest.raises(InterfaceError, match="dragons"):
        check.read_card(path)
    path.write_text('id = "x"\ntitle = "x"\nplace = "real"\nuses = []\nextra = 1\n', encoding="utf-8")
    with pytest.raises(InterfaceError, match="extra"):
        check.read_card(path)
    path.write_text('id = "x"\ntitle = "x"\nplace = "mars"\nuses = []\n', encoding="utf-8")
    with pytest.raises(InterfaceError, match="place"):
        check.read_card(path)

"""Body model checks against answers worked out by hand."""

from __future__ import annotations

import pytest

from stranded_physics.domains.agent.physiology import (
    BODY_KG,
    LETHAL_DEFICIT_L,
    REST_WATTS,
    Body,
    advance,
    cause_of_death,
    needs,
    pandolf_watts,
    setting,
    start_body,
    sweat_l_per_hour,
)
from stranded_physics.runtime.body import NEED_KEYS, STATE_KEYS, AgentBody, to_state


def test_pandolf_matches_a_hand_calculation():
    # 70 kg, 10 kg load, 1 m/s, 5% grade, terrain 1.2: 105 + 2 * 80 * (1/7)^2 + 1.2 * 80 * (1.5 + 1.75).
    assert pandolf_watts(1.0, 5.0, 70.0, 10.0, 1.2) == pytest.approx(105.0 + 160.0 / 49.0 + 96.0 * 3.25)


def test_standing_still_with_no_load_is_the_first_term_only():
    assert pandolf_watts(0.0, 0.0, 70.0, 0.0, 1.2) == pytest.approx(105.0)


def test_downhill_costs_no_more_than_level():
    assert pandolf_watts(1.0, -10.0) == pytest.approx(pandolf_watts(1.0, 0.0))


def test_lethal_deficit_is_the_stated_share_of_body_water():
    assert LETHAL_DEFICIT_L == pytest.approx(BODY_KG * 0.6 * 0.175)
    assert 6.3 <= LETHAL_DEFICIT_L <= 8.4  # 15 to 20% of 42 L, the published range.


def test_resting_a_day_needs_a_litre_of_water():
    after = advance(Body(0.0, 0.0, 0.0), 24.0)
    assert after.water_deficit_l == pytest.approx(1.0)
    assert after.food_deficit_kcal == pytest.approx(1400.0)


def test_no_sweat_at_or_below_resting_heat():
    assert sweat_l_per_hour(REST_WATTS) == 0.0 and sweat_l_per_hour(REST_WATTS - 10.0) == 0.0


def test_sweat_comes_from_extra_heat_and_stops_at_the_published_limit():
    assert sweat_l_per_hour(REST_WATTS + 674.0) == pytest.approx(674.0 * 3600.0 / 2426000.0)
    assert sweat_l_per_hour(1e5) == setting("sweat_limit", "liter/hour")


def test_starting_needs_come_back_unchanged():
    assert needs(start_body(0.8, 0.85, 0.9)) == pytest.approx({"thirst": 0.8, "hunger": 0.85, "energy": 0.9})


def test_drinking_never_gives_a_negative_deficit():
    assert advance(Body(0.1, 0.0, 0.0), 0.0, drank=True).water_deficit_l == 0.0
    assert advance(Body(3.0, 0.0, 0.0), 0.0, drank=True).water_deficit_l == pytest.approx(1.0)


def test_rest_recovers_fatigue_but_not_below_zero():
    assert advance(Body(0.0, 0.0, 100.0), 0.0, rested=True).fatigue_kcal == 0.0
    assert advance(Body(0.0, 0.0, 1000.0), 0.0, rested=True).fatigue_kcal == pytest.approx(760.0)


def test_walking_adds_fatigue_and_food_deficit_equally():
    after = advance(Body(0.0, 0.0, 0.0), 0.0, walking_hours=1.0, walking_watts=REST_WATTS + 418.4)
    assert after.fatigue_kcal == pytest.approx(360.0)
    assert after.food_deficit_kcal == pytest.approx(360.0)


def test_dehydration_kills_only_at_the_lethal_deficit():
    assert cause_of_death(Body(LETHAL_DEFICIT_L - 1e-6, 0.0, 0.0)) is None
    assert cause_of_death(Body(LETHAL_DEFICIT_L, 0.0, 0.0)) == "dehydration"


def test_resting_four_days_without_water_is_survivable():
    body = start_body(0.8, 0.85, 0.9)
    for _ in range(48):
        body = advance(body, 2.0)
    assert cause_of_death(body) is None


def test_nobody_starves_inside_a_run():
    body = start_body(0.8, 0.85, 0.9)
    for _ in range(48):
        body = advance(body, 2.0, walking_hours=2.0, walking_watts=400.0)
    assert body.food_deficit_kcal < setting("starvation_days", "day") * 24.0 * setting("rest_energy", "kcal/hour")


def test_a_mind_sees_only_the_frozen_contract_keys():
    state = to_state(AgentBody((0.0, 0.0), [0, 0], 8), ["none", "none"])
    assert set(state) == STATE_KEYS and set(state["needs"]) == NEED_KEYS


def test_every_need_stays_between_zero_and_one():
    assert all(0.0 <= v <= 1.0 for v in needs(Body(1e6, 1e9, 1e9)).values())
    assert all(0.0 <= v <= 1.0 for v in needs(Body(0.0, 0.0, 0.0)).values())

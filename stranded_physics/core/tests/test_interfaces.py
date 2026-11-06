"""Interface checks. Everything here must hold before any category code is written."""

from __future__ import annotations

import ast
import csv
import json
import subprocess
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

import contracts
from stranded_physics import catalog, gates
from stranded_physics.core.api import DatasetRecord, GridSpec, InterfaceError, Parameter, Q_
from stranded_physics.core.fakes import FAKE_GRID, FAKE_TIME, BoxEruption, BoxTephra, ConeTerrain, UniformWind, fake_scenario
from stranded_physics.core.fields import FieldStore, ScopedFields, spec
from stranded_physics.core.records import load_parameters, open_for_calibration, open_for_validation
from stranded_physics.core.verdicts import agreement, judge_rate, judge_value, wilson_interval
from stranded_physics.packs.builder import Pack, build_pack, dependency_order, load_pack, save_pack
from stranded_physics.runtime.body import NEED_KEYS, STATE_KEYS, to_state
from stranded_physics.runtime.perception import perceive
from stranded_physics.runtime.simulation import PackSimulation

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "stranded_physics"


def record(split="calibration"):
    return DatasetRecord("d", "terrain", "raster", "https://example.org/d", "2026-11-04T00:00Z", "a" * 64, "not confirmed", False, "x", split, "min_bytes:10")


# Records


def test_parameter_needs_a_source_unless_it_is_an_assumption():
    with pytest.raises(InterfaceError):
        Parameter("p", Q_(1, "m"), (Q_(0, "m"), Q_(2, "m")), "input", "literature")
    assert Parameter("p", Q_(1, "m"), (Q_(0, "m"), Q_(2, "m")), "input", "assumption").source is None


def test_parameter_outside_its_valid_range_is_rejected():
    with pytest.raises(InterfaceError):
        Parameter("p", Q_(3, "m"), (Q_(0, "m"), Q_(2, "m")), "input", "assumption")


def test_parameter_units_must_match_its_range():
    with pytest.raises(InterfaceError):
        Parameter("p", Q_(1, "m"), (Q_(0, "s"), Q_(2, "s")), "input", "assumption")


def test_unknown_keys_are_rejected(tmp_path):
    path = tmp_path / "params.toml"
    path.write_text(
        '[[parameter]]\nid="p"\nvalue=1.0\nunit="m"\nvalid_min=0.0\nvalid_max=2.0\nrole="input"\nstatus="assumption"\nmystery=1\n', encoding="utf-8"
    )
    with pytest.raises(InterfaceError, match="mystery"):
        load_parameters(path)


def test_holdout_data_is_refused_during_calibration():
    held = (record("holdout"),)
    with pytest.raises(InterfaceError):
        open_for_calibration(held, "d")
    assert open_for_validation(held, "d").id == "d"
    with pytest.raises(InterfaceError):
        open_for_validation((record("calibration"),), "d")


def test_dataset_needs_a_bot_page_check_and_a_real_hash():
    with pytest.raises(InterfaceError):
        replace(record(), content_check="")
    with pytest.raises(InterfaceError):
        replace(record(), sha256="short")


# Fields


def test_fields_convert_units():
    store = FieldStore()
    store.put("atmos.wind_speed", np.full(FAKE_TIME.n, 36.0), "km/h", time=FAKE_TIME)
    assert store.get("atmos.wind_speed", "m/s") == pytest.approx(np.full(FAKE_TIME.n, 10.0))
    with pytest.raises(InterfaceError):
        store.get("atmos.wind_speed", "kg")


def test_fields_reject_nan_duplicates_and_wrong_shapes():
    store = FieldStore()
    with pytest.raises(InterfaceError, match="NaN"):
        store.put("atmos.wind_speed", np.full(FAKE_TIME.n, np.nan), "m/s", time=FAKE_TIME)
    with pytest.raises(InterfaceError, match="shape"):
        store.put("atmos.wind_speed", np.zeros(3), "m/s", time=FAKE_TIME)
    store.put("atmos.wind_speed", np.zeros(FAKE_TIME.n), "m/s", time=FAKE_TIME)
    with pytest.raises(InterfaceError, match="already"):
        store.put("atmos.wind_speed", np.zeros(FAKE_TIME.n), "m/s", time=FAKE_TIME)


def test_fields_regrid_between_grids():
    coarse = GridSpec("EPSG:32620", 0.0, 400.0, 200.0, 2, 2)
    fine = GridSpec("EPSG:32620", 0.0, 400.0, 100.0, 4, 4)
    store = FieldStore()
    store.put("terrain.elevation", np.array([[1.0, 2.0], [3.0, 4.0]]), "m", coarse)
    out = store.get("terrain.elevation", "m", fine)
    assert out.shape == (4, 4) and out[0, 0] == 1 and out[0, 3] == 2 and out[3, 0] == 3 and out[3, 3] == 4
    with pytest.raises(InterfaceError, match="CRS"):
        store.get("terrain.elevation", "m", replace(fine, crs="EPSG:4326"))


def test_unknown_field_names_are_rejected():
    with pytest.raises(InterfaceError):
        spec("lahar.mystery")


def test_a_category_cannot_read_or_write_undeclared_fields():
    store = FieldStore()
    store.put("atmos.wind_speed", np.zeros(FAKE_TIME.n), "m/s", time=FAKE_TIME)
    scoped = ScopedFields(store, "tephra", (), (spec("tephra.deposit_load"),))
    with pytest.raises(InterfaceError, match="without declaring"):
        scoped.get("atmos.wind_speed", "m/s")
    with pytest.raises(InterfaceError, match="without declaring"):
        scoped.put("lahar.depth", np.zeros((FAKE_TIME.n, 50, 50)), "m", FAKE_GRID, FAKE_TIME)


def test_a_category_cannot_write_another_categorys_fields():
    scoped = ScopedFields(FieldStore(), "tephra", (), (spec("lahar.depth"),))
    with pytest.raises(InterfaceError, match="only write its own"):
        scoped.put("lahar.depth", np.zeros((FAKE_TIME.n, 50, 50)), "m", FAKE_GRID, FAKE_TIME)


def test_domain_folders_do_not_import_each_other():
    domains = PACKAGE / "domains"
    for path in domains.rglob("*.py"):
        own = path.relative_to(domains).parts[0]
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = [node.module or ""] if isinstance(node, ast.ImportFrom) else [a.name for a in node.names] if isinstance(node, ast.Import) else []
            for name in names:
                if name.startswith("stranded_physics.domains."):
                    assert name.split(".")[2] == own, f"{path} imports {name}"


def test_engine_never_imports_physics():
    for path in (ROOT / "engine").rglob("*.py"):
        assert "stranded_physics" not in path.read_text(encoding="utf-8"), path


# Pack building


def test_producers_run_before_consumers():
    order = [d.id for d in dependency_order(fake_scenario().domains)]
    assert order.index("eruption") < order.index("tephra") and order.index("atmos") < order.index("tephra")
    assert order.index("eruption") < order.index("pdc")


def test_missing_input_is_an_error():
    with pytest.raises(InterfaceError, match="nothing in this scenario"):
        dependency_order((BoxTephra(),))


def test_two_producers_of_one_field_is_an_error():
    with pytest.raises(InterfaceError, match="two producers"):
        dependency_order((UniformWind(), UniformWind(), BoxEruption()))


def test_circular_dependency_is_an_error():
    class A(ConeTerrain):
        id = "a"
        inputs = (spec("atmos.wind_speed"),)
        outputs = (spec("terrain.elevation"),)

    class B(UniformWind):
        id = "b"
        inputs = (spec("terrain.elevation"),)
        outputs = (spec("atmos.wind_speed"),)

    with pytest.raises(InterfaceError, match="circular"):
        dependency_order((A(), B()))


def test_same_seed_gives_the_same_hash_and_different_seeds_differ():
    first, second = build_pack(fake_scenario(), 7), build_pack(fake_scenario(), 7)
    assert first.content_hash == second.content_hash
    hashes = {build_pack(fake_scenario(), seed).content_hash for seed in range(6)}
    assert len(hashes) == 6


def test_pack_round_trips_and_detects_tampering(tmp_path):
    pack = build_pack(fake_scenario(), 3)
    path = tmp_path / "p.npz"
    save_pack(pack, path)
    assert load_pack(path).content_hash == pack.content_hash
    with np.load(path, allow_pickle=False) as archive:
        arrays = {k: archive[k] for k in archive.files}
    arrays["eruption.tremor"] = arrays["eruption.tremor"] * 0 + 1
    np.savez_compressed(path, **arrays)
    with pytest.raises(InterfaceError, match="content hash"):
        load_pack(path)


def test_pack_arrays_are_read_only():
    pack = build_pack(fake_scenario(), 3)
    with pytest.raises(ValueError):
        pack.series("eruption.tremor")[0] = 1


def test_a_validity_breach_blocks_play_unless_explicitly_allowed():
    class Strict(ConeTerrain):
        def check_validity(self, fields):
            return ["slope outside this model's range"]

    scenario = fake_scenario()
    pack = build_pack(replace(scenario, domains=(Strict(), *scenario.domains[1:])), 1)
    assert pack.verdicts["terrain.validity"] == "OUT_OF_DOMAIN"
    with pytest.raises(InterfaceError, match="valid range"):
        PackSimulation(pack)
    assert PackSimulation(pack, allow_out_of_domain=True).run()["steps"]


# Runtime and the mind


@pytest.mark.parametrize("mind", ["quantum", "classical"])
def test_real_contract_minds_play_a_full_run(mind):
    timeline = PackSimulation(build_pack(fake_scenario(erupts=False), 2), mind_type=mind).run()
    assert 1 <= len(timeline["steps"]) <= 36
    for step in timeline["steps"]:
        assert step["action"] in contracts.ACTIONS and step["event"] in contracts.EVENTS


def test_every_mind_gets_the_same_world():
    pack = build_pack(fake_scenario(), 4)
    first = PackSimulation(pack, "quantum").run()["world"]["volcano"]
    second = PackSimulation(pack, "classical").run()["world"]["volcano"]
    assert first["phases"] == second["phases"] and first["hazard_by_step"] == second["hazard_by_step"]


def test_state_has_exactly_the_contract_keys():
    sim = PackSimulation(build_pack(fake_scenario(), 1))
    sim.step()
    state = sim.steps[0]["state"]
    assert set(state) == STATE_KEYS and set(state["needs"]) == NEED_KEYS
    contracts.validate_state(state)
    assert set(to_state(sim.agent, ["none"])) == STATE_KEYS


def test_timeline_keeps_every_existing_json_key():
    existing = json.loads((ROOT / "demo-pack" / "run_01_heroic_survival.json").read_text(encoding="utf-8"))
    timeline = PackSimulation(build_pack(fake_scenario(), 1)).run()
    assert set(existing) <= set(timeline)
    assert set(existing["world"]) <= set(timeline["world"])
    assert set(existing["steps"][0]) <= set(timeline["steps"][0])
    assert set(existing["world"]["volcano"]) <= set(timeline["world"]["volcano"])
    assert set(existing["world"]["volcano"]["hazard_by_step"][0]) <= set(timeline["world"]["volcano"]["hazard_by_step"][0])
    assert set(existing["world"]["evacuation_map"]) <= set(timeline["world"]["evacuation_map"])
    json.dumps(timeline)


def test_world_view_has_what_the_legacy_gui_reads():
    world = PackSimulation(build_pack(fake_scenario(), 1)).world
    for name in (
        "width",
        "height",
        "tiles",
        "zones",
        "spawn_pos",
        "vent",
        "assembly_points",
        "freshwater_tiles",
        "clean_springs",
        "food_tiles",
        "shelter_tiles",
        "lava",
        "pdc",
        "lahar",
        "ash",
    ):
        assert hasattr(world, name), name
    assert world.get_tile(-1, 0) == 0 and world.get_tile(*world.spawn_pos) in contracts.TILE_TYPES
    assert world.is_in_shelter(*world.spawn_pos) is False and isinstance(world.ash_at(0, 0), float)


def _with_future_changed(pack: Pack, after_step: int) -> Pack:
    """A copy whose hazards differ only after one step, to prove the past can't see the future."""
    arrays = {k: np.array(v) for k, v in pack._arrays.items()}
    arrival = arrays["pdc.arrival"]
    cut = after_step * pack.time.dt_s
    arrays["pdc.arrival"] = np.where(arrival > cut, np.inf, arrival)
    arrays["pdc.active"][after_step + 1 :] = 0
    arrays["eruption.tremor"][after_step + 1 :] = 1 - arrays["eruption.tremor"][after_step + 1 :]
    arrays["tephra.deposit_load"][after_step + 1 :] = 0
    return Pack(dict(pack.header), arrays)


@pytest.mark.parametrize("seed", [2, 5, 11])
def test_minds_cannot_see_the_future(seed):
    pack = build_pack(fake_scenario(erupts=True), seed)
    cut = 10
    other = _with_future_changed(pack, cut)
    first, second = PackSimulation(pack), PackSimulation(other)
    for _ in range(cut + 1):
        if first.step() is None or second.step() is None:
            break
    assert [s["state"] for s in first.steps] == [s["state"] for s in second.steps]
    assert [s["event"] for s in first.steps] == [s["event"] for s in second.steps]


def test_perception_is_local_and_cannot_read_ahead():
    pack = build_pack(fake_scenario(erupts=True), 5)
    far = (pack.grid.x0_m + 50.0, pack.grid.y0_m - 50.0)
    arrival = pack.frame("pdc.arrival")
    first = float(arrival[np.isfinite(arrival)].min())
    near = pack.sites["vent"][0]
    assert perceive(pack, near, first - 1.0).flow_visible is False
    assert perceive(pack, near, first).flow_visible is True
    assert perceive(pack, far, first).flow_visible is False


def test_a_person_standing_in_a_flow_dies_and_one_who_leaves_lives():
    pack = build_pack(fake_scenario(erupts=True), 5)
    stay = PackSimulation(pack, decide_fn=lambda s: {"action": "rest", "probs": {"rest": 1.0}, "reason": "t"})
    assert stay.run()["cause"] == "pyroclastic_flow"
    leave = PackSimulation(pack, decide_fn=lambda s: {"action": "hide", "probs": {"hide": 1.0}, "reason": "t"})
    assert leave.run()["cause"] != "pyroclastic_flow"


# Verdicts


def test_no_target_is_never_a_pass():
    assert judge_value(1.0, None, None) == "NO_TARGET"
    assert judge_rate(5, 10, None, None) == "NO_TARGET"


def test_value_judged_against_the_committed_target():
    assert judge_value(10.5, 10.0, 1.0) == "PASS" and judge_value(12.0, 10.0, 1.0) == "FAIL"
    assert judge_value(None, 10.0, 1.0) == "NOT_RUN"


def test_zero_events_alone_do_not_pass_a_rare_event_bar():
    assert judge_rate(0, 10, None, 0.01) == "INSUFFICIENT_DATA"
    assert judge_rate(0, 100000, None, 0.01) == "PASS"
    assert judge_rate(500, 1000, None, 0.01) == "FAIL"
    assert judge_rate(0, 0, None, 0.01) == "NOT_RUN"


def test_wilson_interval_known_values():
    low, high = wilson_interval(0, 10)
    assert low == 0.0 and high == pytest.approx(0.2775, abs=0.001)
    low, high = wilson_interval(5, 10)
    assert low == pytest.approx(0.2366, abs=0.001) and high == pytest.approx(0.7634, abs=0.001)


def test_only_holdout_predictions_count_toward_agreement():
    rows = [
        {"role": "prediction", "split": "holdout", "verdict": "PASS"},
        {"role": "prediction", "split": "holdout", "verdict": "FAIL"},
        {"role": "input", "split": "holdout", "verdict": "PASS"},
        {"role": "anchor", "split": "calibration", "verdict": "PASS"},
        {"role": "prediction", "split": "calibration", "verdict": "PASS"},
        {"role": "prediction", "split": "holdout", "verdict": "NO_TARGET"},
    ]
    assert agreement(rows) == (1, 2)


def test_changing_a_target_makes_a_verdict_stale():
    gate = {"id": "g", "kind": "validation", "command": "python x", "target": 1.0, "tolerance": 0.1}
    assert gates.input_hash(gate) != gates.input_hash({**gate, "target": 2.0})


def test_gate_judgement_rules():
    verification = {"id": "g", "kind": "verification", "command": "x"}
    validation = {"id": "g", "kind": "validation", "command": "x"}
    assert gates.judge(verification, 0, "")["verdict"] == "PASS"
    assert gates.judge(verification, 1, "")["verdict"] == "FAIL"
    assert gates.judge(validation, 0, "")["verdict"] == "NO_TARGET"
    assert gates.judge({**validation, "target": 5.0, "tolerance": 1.0}, 0, '{"value": 5.5}')["verdict"] == "PASS"
    assert gates.judge({**validation, "target": 5.0, "tolerance": 1.0}, 0, '{"value": 9}')["verdict"] == "FAIL"
    assert gates.judge({**validation, "rate_high": 0.01}, 0, '{"successes": 0, "trials": 10}')["verdict"] == "INSUFFICIENT_DATA"


# Workboard and categories


def test_every_category_loads_with_strict_records():
    text = catalog.build()
    expected = {
        "ship",
        "sea",
        "terrain",
        "atmos",
        "storm",
        "eruption",
        "tephra",
        "pdc",
        "lahar",
        "lava",
        "gas",
        "exposure",
        "agent",
        "seismic",
        "tsunami",
        "impact",
    }
    assert expected == set(gates.categories())
    for category in expected:
        assert f"## {category}:" in text


def test_workboard_is_not_hidden_by_gitignore():
    paths = [p for p in (ROOT / "workboard").rglob("*") if p.is_file()]
    assert paths
    for path in paths:
        done = subprocess.run(["git", "check-ignore", "-q", str(path)], cwd=ROOT)
        assert done.returncode == 1, f"{path} is hidden by .gitignore"


def test_task_board_is_well_formed():
    with (ROOT / "workboard" / "tasks.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows
    ids = {row["id"] for row in rows}
    for row in rows:
        assert row["status"] in {"todo", "claimed", "blocked", "review", "done"}, row["id"]
        assert (ROOT / "workboard" / row["spec"]).exists(), row["spec"]
        for dependency in filter(None, row["depends"].split(";")):
            assert dependency in ids, dependency

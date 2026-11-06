"""The end-of-event report and its CSV and Excel export."""
import csv
import threading

import contracts  # noqa: F401  (must load before mind)
import pygame
import pytest
from openpyxl import load_workbook

from engine.gui import IslandVisualizerApp
from engine.pompeii import PompeiiSimulation
from engine.report import (CUE_TRANSLATIONS, SHEET_ORDER, build_report, export_report, key_lines, paired_rows, report_name, run_and_report, write_csv,
                           write_xlsx)
from engine.simulation import SimulationEngine
from engine.titanic import TitanicSimulation
from engine.waterloo import WaterlooSimulation


def values(rows):
    return {row["field"]: row["value"] for row in rows}


@pytest.fixture(scope="module")
def volcano():
    engine = SimulationEngine(seed=7, mind_type="quantum")
    engine.run()
    return engine


@pytest.fixture(scope="module")
def titanic():
    engine = TitanicSimulation(seed=42, mind_type="quantum")
    engine.run()
    return engine


def test_volcano_report_has_its_tables_in_order(volcano):
    report = build_report("volcano", volcano, "quantum", 7)
    assert list(report) == [name for name in SHEET_ORDER if name in report]
    assert {"Summary", "Key events", "Timeline", "Decisions", "Paired run", "Assumptions"} <= set(report)
    assert "Crowd over time" not in report


def test_timeline_covers_every_step_end_to_end(volcano):
    rows = build_report("volcano", volcano, "quantum", 7)["Timeline"]
    assert len(rows) == len(volcano.steps) and [r["step"] for r in rows] == list(range(len(rows)))
    first = rows[0]
    for key in ("clock", "event", "action", "stress", "hunger", "safety", "p_danger", "p_protect", "lambda", "coherence_x", "reason"):
        assert key in first
    assert first["p_protect"] == pytest.approx(volcano.steps[0]["quantum"]["p_protect"])


def test_summary_says_what_it_is(volcano):
    summary = values(build_report("volcano", volcano, "quantum", 7)["Summary"])
    assert summary["Seed"] == 7 and summary["Status"] == "A model, not a prediction."
    assert summary["Steps run"] == f"{len(volcano.steps)} of 36"
    assert "Survived" in summary["Followed person's outcome"] or "Died" in summary["Followed person's outcome"]


def test_titanic_totals_add_up(titanic):
    report = build_report("titanic", titanic, "quantum", 42)
    summary = values(report["Summary"])
    assert summary["Survived"] == titanic.counts()["boats"]
    assert summary["Survived"] + summary["Died"] == summary["People"] == len(titanic.people)
    assert sum(r["survived"] for r in report["Groups"]) == summary["Survived"]
    assert sum(r["people"] for r in report["Groups"]) == summary["People"]


def test_titanic_report_names_the_assumed_translation(titanic):
    report = build_report("titanic", titanic, "quantum", 42)
    assert "Rockets read as certain danger" in values(report["Summary"])["Cue translation (assumption)"]
    assert any(r["item"] == "Cue translation" for r in report["Assumptions"])


def test_crowd_over_time_has_a_row_per_step(titanic):
    rows = build_report("titanic", titanic, "quantum", 42)["Crowd over time"]
    assert len(rows) == len(titanic.steps)
    assert rows[-1]["boats"] == titanic.counts()["boats"]
    assert sum(rows[0][k] for k in ("aboard", "boats", "water", "dead")) == len(titanic.people)


def test_pompeii_and_waterloo_reports():
    pompeii = PompeiiSimulation(seed=3, population=800, event_mapping="C")
    pompeii.run()
    report = build_report("pompeii", pompeii, "quantum", 3)
    summary = values(report["Summary"])
    assert summary["Survived"] + summary["Died"] == 800
    assert "ambiguous" in summary["Cue translation (assumption)"]

    waterloo = WaterlooSimulation(seed=3)
    waterloo.run()
    report = build_report("waterloo", waterloo, "quantum", 3)
    summary = values(report["Summary"])
    assert summary["Off the site"] == waterloo.counts()["off_site"]
    assert any(r["event"].startswith("Exposure:") for r in report["Key events"])
    assert {"reached_aegl1", "reached_aegl2", "reached_aegl3"} <= set(report["Groups"][0])


def test_events_that_never_happened_say_so(volcano):
    rows = build_report("volcano", volcano, "quantum", 7)["Key events"]
    assert all(r["detail"] == "Did not happen" or r["step"] is not None or r["detail"] for r in rows)


def test_key_lines_are_short_and_skip_what_did_not_happen():
    report = {"Key events": [dict(event="A", step=1, when="Day 1 10:00", detail=""), dict(event="B", step=None, when=None, detail="Did not happen"),
                             dict(event="C", step=None, when=None, detail="4 h")]}
    assert key_lines(report) == ["A: Day 1 10:00   |   C: 4 h"]


def test_paired_rows_cover_both_shapes():
    assert values(paired_rows(None))["Paired run"] == "Not available"
    assert values(paired_rows(dict(mind="classical_mixture", survived=True, steps=36, hide_after_sign=2)))["Survived"] is True
    assert values(paired_rows(dict(mind="classical_mixture", survivors=536, deaths=1672, total=2208)))["Deaths"] == 1672


def test_csv_and_xlsx_match_the_report(volcano, tmp_path):
    report = build_report("volcano", volcano, "quantum", 7)
    workbook, folder = export_report(report, "run", tmp_path)
    with (folder / "timeline.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == len(report["Timeline"]) and rows[0]["action"] == report["Timeline"][0]["action"]
    book = load_workbook(workbook)
    assert book.sheetnames == list(report)
    assert book["Timeline"].max_row == len(report["Timeline"]) + 1
    assert book["Summary"].freeze_panes == "A2"
    assert {p.name for p in folder.iterdir()} == {n.lower().replace(" ", "_") + ".csv" for n in report}


def test_export_stamps_a_copy_and_leaves_the_report_alone(volcano, tmp_path):
    report = build_report("volcano", volcano, "quantum", 7)
    size = len(report["Summary"])
    workbook, _folder = export_report(report, "run", tmp_path)
    assert len(report["Summary"]) == size
    fields = [row[0].value for row in load_workbook(workbook)["Summary"].iter_rows(min_row=2)]
    assert "Generated" in fields and "Code version" in fields


def test_greek_letters_survive_a_csv_round_trip(tmp_path):
    path = write_csv({"Summary": [dict(field="Mind", value="Mixture control (λ=1)")]}, tmp_path)[0]
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")
    assert "λ=1" in path.read_text(encoding="utf-8-sig")


def test_xlsx_handles_rows_with_different_columns(tmp_path):
    path = write_xlsx({"Mixed": [dict(a=1), dict(b=2)]}, tmp_path / "x.xlsx")
    sheet = load_workbook(path)["Mixed"]
    assert [c.value for c in sheet[1]] == ["A", "B"] and sheet["B3"].value == 2


def test_report_name_is_safe_for_a_file(titanic):
    name = report_name("titanic", 42, "quantum", titanic, stamp="20261106-120000")
    assert name == "titanic_seed42_quantum_default_20261106-120000"


def test_building_a_report_does_not_change_the_run():
    engine = SimulationEngine(seed=5)
    engine.run()
    before = [dict(r) for r in engine.steps]
    build_report("volcano", engine, "quantum", 5)
    assert engine.steps == before


def test_pack_runs_from_the_scenario_builder_get_a_report(tmp_path):
    from stranded_physics.core.fakes import fake_scenario
    from stranded_physics.packs.builder import build_pack
    from stranded_physics.runtime.simulation import PackSimulation

    sim = PackSimulation(build_pack(fake_scenario(), 1))
    sim.run()
    report = build_report("volcano", sim, "quantum", 1, title="My scenario")
    assert values(report["Summary"])["Scenario"] == "My scenario"
    assert len(report["Timeline"]) == len(sim.steps)
    assert export_report(report, "pack", tmp_path)[0].exists()


def test_every_cue_translation_labels_a_real_choice():
    assert set(CUE_TRANSLATIONS) == {"titanic", "pompeii", "waterloo"}


def test_headless_run_writes_both_formats(tmp_path):
    report, workbook, folder = run_and_report("volcano", seed=9, out_dir=tmp_path)
    assert workbook.exists() and (folder / "summary.csv").exists()
    assert values(report["Paired run"])["Mind"].startswith("Mixture")


# The debrief ------------------------------------------------------------------

def make_app(scenario, tmp_path=None):
    app = IslandVisualizerApp(seed=42, mind_type="quantum", start_screen="sim", scenario=scenario)
    app.screen = pygame.display.set_mode((1920, 1080))
    if tmp_path is not None:
        app.report_dir = tmp_path
    return app


def finish(app, steps=36):
    for _ in range(steps):
        app.step_forward()
    app.show_debrief_modal = True
    app.draw((0, 0))


def wait_for_export(app):
    assert isinstance(app.report_thread, threading.Thread)
    app.report_thread.join(timeout=60)
    assert not app.report_thread.is_alive()


def test_debrief_shows_crucial_details():
    app = make_app("volcano")
    finish(app)
    shown = " ".join(text for text, _ in app.canvas.text_rects(1.2))
    assert "First sign reached the person" in shown and "Export Report" in shown


def test_debrief_text_stays_clear_of_its_buttons():
    app = make_app("volcano")
    finish(app)
    top = round(app.btn_modal_replay.rect.top * 1.2)
    rects = app.canvas.text_rects(1.2)
    above = [rect for text, rect in rects if rect.right < 1500 and rect.top < top and text not in ("Replay Run",)]
    assert above and max(r.bottom for r in above) <= top


def test_export_button_writes_both_formats(tmp_path):
    app = make_app("volcano", tmp_path)
    finish(app)
    app._handle_sim_click(app.btn_modal_report.rect.center)
    wait_for_export(app)
    assert len(list(tmp_path.glob("*.xlsx"))) == 1
    assert (next(p for p in tmp_path.iterdir() if p.is_dir()) / "timeline.csv").exists()
    assert "Saved" in app.report_status


def test_export_includes_the_paired_run_when_it_finishes(tmp_path):
    app = make_app("volcano", tmp_path)
    finish(app)
    app.paired.thread.join()
    app._handle_sim_click(app.btn_modal_report.rect.center)
    wait_for_export(app)
    book = load_workbook(next(tmp_path.glob("*.xlsx")))
    fields = [row[0].value for row in book["Paired run"].iter_rows(min_row=2)]
    assert "Survived" in fields


def test_export_key_in_the_debrief_writes_the_report(tmp_path):
    app = make_app("volcano", tmp_path)
    finish(app)
    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_k, mod=0, unicode="k"), (5, 5))
    wait_for_export(app)
    assert list(tmp_path.glob("*.xlsx"))


def test_a_new_run_clears_the_saved_message(tmp_path):
    app = make_app("volcano", tmp_path)
    finish(app)
    app._handle_sim_click(app.btn_modal_report.rect.center)
    wait_for_export(app)
    app._init_simulation()
    assert app.report_status == ""

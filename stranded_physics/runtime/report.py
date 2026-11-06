"""Runs a sim file without a window and writes its end-of-event report."""
from __future__ import annotations

from engine.report import build_report, export_report, report_name
from stranded_physics.entities import draft as edit
from stranded_physics.entities import simfile
from stranded_physics.runtime.game import build_game


def load(source: str) -> simfile.Sim:
    """A file on this computer, or an https link."""
    return simfile.fetch_sim(source) if str(source).startswith("https://") else simfile.read_path(source)


def report_sim(source: str, mind: str | None = None, out_dir=None) -> tuple:
    sim = load(source)
    game = build_game(edit.to_scenario(sim.draft), sim.seed)
    mind = mind or game.person.mind
    engine = game.simulation(mind)
    engine.run()
    report = build_report("volcano", engine, mind, sim.seed, title=sim.title, horizon=game.pack.time.n)
    report["Summary"] = report["Summary"] + [dict(field="Sim file hash", value=sim.sha256), dict(field="Made by", value=sim.author or "Anonymous"),
                                             dict(field="Checked by", value="Nobody. Community sims are not validated")]
    return export_report(report, report_name(str(sim.draft.header["id"]), sim.seed, mind), out_dir)

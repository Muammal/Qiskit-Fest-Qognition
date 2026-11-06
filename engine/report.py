"""The end-of-event report, and its CSV and Excel export.

    python main.py --report --scenario titanic --seed 42 --mind quantum

A report is a set of named tables built from the finished run:

    Summary          the crucial details on one page
    Key events       what happened, and when
    Timeline         every step, end to end, for the person followed
    Crowd over time  everyone's status at every step (crowd scenarios)
    Groups           outcomes by class, role or person
    Decisions        how often each action was chosen
    Paired run       the other mind on the same seed
    Assumptions      what this run assumed

Nothing here feeds back into a run. All of it is model output, not a prediction.
"""

import csv
import re
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path

from engine.debrief import MODEL_FOOTER, crowd_line, elapsed_text, paired_run
from engine.lifeboats import TOTAL_SEATS

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "exports" / "reports"
CROWD = ("titanic", "pompeii", "waterloo")
MIND_NAMES = {"quantum": "2-qubit quantum mind", "classical_mixture": "Mixture control (λ=1)", "classical": "Classical argmax"}
SCENARIO_NAMES = dict(
    island="Island wilderness",
    volcano="Volcano evacuation",
    titanic="Titanic evacuation, April 1912",
    pompeii="Pompeii evacuation, AD 79",
    waterloo="Waterloo chlorine leak (hypothetical)",
)
SHEET_ORDER = ("Summary", "Key events", "Timeline", "Crowd over time", "Groups", "Decisions", "Paired run", "Assumptions")

# The cue translation is an assumption: which model event a real-world cue reaches the mind as.
# (button, event_mapping value, what it assumes).
CUE_TRANSLATIONS = {
    "titanic": (
        ("A", "default", "Rockets read as certain danger, steward warnings as ambiguous"),
        ("B", "ambiguous_rockets", "Rockets read as ambiguous, like steward warnings"),
        ("C", "early_pa_alarm", "Steward warnings and crew orders read as certain danger"),
    ),
    "pompeii": (
        ("A", "A", "Column and falling pumice both read as certain danger"),
        ("B", "B", "Column ambiguous, pumice certain (the most literal)"),
        ("C", "C", "Column and pumice both ambiguous, as a gas plume"),
        ("D", "D", "Column and pumice both ambiguous, as a tremor"),
    ),
    "waterloo": (
        ("A", "A", "Every cue ambiguous, including the alarm"),
        ("B", "B", "Alarm read as certain danger, other cues ambiguous"),
        ("C", "C", "A milder reading: smell and talk as tremors, alarm ambiguous"),
    ),
}
TITANIC_HISTORY = dict(first=201, second=118, third=181)  # saved; Wikipedia casualty table, as shown in the debrief
TITANIC_CREW_HISTORY = 212
TITANIC_GROUPS = dict(first="First-class passengers", second="Second-class passengers", third="Third-class passengers")
EVENT_LABELS = dict(
    first_sign_step="First sign reached the person",
    first_evacuating_step="Person first chose to evacuate",
    left_danger_step="Left the danger zone",
    reached_safe_step="Reached the safe zone",
    reached_assembly_step="Reached an assembly point",
    boarded_step="Boarded a lifeboat",
    left_town_step="Left the town",
    onset_step="Hazard onset",
    first_pdc_step="First pyroclastic flow",
    sink_step="Ship gone from view",
    first_city_flow_step="First flow in the town",
)
VALUE_LABELS = dict(
    warning_lead_hours=("Warning lead", "h"),
    margin_hours=("Margin before the first flow", "h"),
    first_knew=("First person knew, after the leak", "s"),
    alarm=("Alarm, after the leak", "s"),
    first_off_site=("First person off site, after the leak", "s"),
    half_off_site=("Half off site, after the leak", "s"),
    all_off_site=("Everyone off site, after the leak", "s"),
)


def clock_at(scenario, t, state=None):
    """Scenario time for 0-indexed step t."""
    if scenario == "titanic":
        minutes = 23 * 60 + 30 + t * 5
        return f"{minutes // 60 % 24:02d}:{minutes % 60:02d}"
    if scenario == "pompeii":
        from engine.gui_city import clock_text

        return clock_text(t)
    if scenario == "waterloo":
        from engine.gui_site import clock_text

        return clock_text(t)
    hours = 8 + t * 2
    return f"Day {hours // 24 + 1} {hours % 24:02d}:00"


def _mapping_row(scenario, engine):
    value = getattr(engine, "event_mapping", None)
    return next((row for row in CUE_TRANSLATIONS.get(scenario, ()) if row[1] == value), None)


def _timeline_rows(scenario, steps):
    rows = []
    for record in steps:
        state = record.get("state") or {}
        needs = state.get("needs") or {}
        quantum = record.get("quantum") or {}
        position = record.get("pos_after") or [None, None]
        row = dict(
            step=record["t"],
            clock=clock_at(scenario, record["t"]),
            phase=record.get("phase"),
            event=record.get("event"),
            story=record.get("story", ""),
            action=record.get("action"),
            action_label=record.get("action_label", ""),
            status=record.get("status", ""),
            x=position[0],
            y=position[1],
            stress=state.get("stress"),
            injured=state.get("injured"),
            recent_cues=" > ".join(state.get("recent_events", [])),
        )
        for need in ("hunger", "thirst", "warmth", "energy", "safety", "morale"):
            row[need] = needs.get(need)
        for key, name in (
            ("p_danger", "p_danger"),
            ("p_protect", "p_protect"),
            ("p_classical", "p_classical"),
            ("coherence", "coherence_x"),
            ("lam", "lambda"),
            ("q_safe", "q_safe"),
            ("q_danger", "q_danger"),
            ("order_gap", "order_gap"),
            ("reflex", "reflex"),
        ):
            row[name] = quantum.get(key)
        row["p_hide"] = (record.get("probs") or {}).get("hide")
        row["reason"] = record.get("reason", "")
        rows.append(row)
    return rows


def _crowd_rows(scenario, steps):
    rows = []
    for record in steps:
        counts = record.get("counts")
        if counts:
            rows.append(dict(step=record["t"], clock=clock_at(scenario, record["t"]), phase=record.get("phase"), **counts))
    return rows


def _decision_rows(steps):
    decided = [r for r in steps if "no further decisions" not in r.get("reason", "") and "no new decision" not in r.get("reason", "")]
    tally = Counter(r.get("action") for r in decided)
    labels = {}
    for record in steps:
        if record.get("action_label"):
            labels.setdefault(record["action"], record["action_label"])
    total = sum(tally.values()) or 1
    return [dict(action=action, label=labels.get(action, action), times_chosen=count, share=round(count / total, 4)) for action, count in tally.most_common()]


def _group_rows(scenario, engine):
    if scenario == "titanic":
        table = engine.outcome_table()
        rows = []
        for key, name in TITANIC_GROUPS.items():
            row = table.get(key, dict(aboard=0, saved=0))
            rows.append(
                dict(
                    group=name,
                    people=row["aboard"],
                    survived=row["saved"],
                    survival_rate=round(row["saved"] / max(1, row["aboard"]), 4),
                    history_saved=TITANIC_HISTORY[key],
                )
            )
        crew = [row for key, row in table.items() if key not in TITANIC_GROUPS]
        aboard, saved = sum(r["aboard"] for r in crew), sum(r["saved"] for r in crew)
        rows.append(dict(group="Crew", people=aboard, survived=saved, survival_rate=round(saved / max(1, aboard), 4), history_saved=TITANIC_CREW_HISTORY))
        return rows
    if scenario == "pompeii":
        return [
            dict(
                group=role.replace("_", " ").capitalize(),
                people=row["total"],
                survived=row["survived"],
                survival_rate=round(row["survived"] / max(1, row["total"]), 4),
            )
            for role, row in engine.outcome_table().items()
        ]
    if scenario == "waterloo":
        return [
            dict(
                group=role.capitalize(),
                people=row["total"],
                off_site=row["off_site"],
                off_site_rate=round(row["off_site"] / max(1, row["total"]), 4),
                reached_aegl1=row["levels"]["1"],
                reached_aegl2=row["levels"]["2"],
                reached_aegl3=row["levels"]["3"],
            )
            for role, row in engine.outcome_table().items()
        ]
    return []


def _key_event_rows(scenario, engine, timeline):
    rows = []
    evacuation = timeline.get("evacuation") or {}
    for key, value in evacuation.items():
        if key in EVENT_LABELS:
            rows.append(
                dict(
                    event=EVENT_LABELS[key],
                    step=value,
                    when=None if value is None else clock_at(scenario, value),
                    detail="" if value is not None else "Did not happen",
                )
            )
        elif key in VALUE_LABELS:
            label, unit = VALUE_LABELS[key]
            rows.append(dict(event=label, step=None, when=None, detail="Did not happen" if value is None else f"{value} {unit}"))
    rows.sort(key=lambda row: (row["step"] is None, row["step"] or 0))
    if scenario == "titanic":
        boats = engine.boats
        used = sum(len(b.aboard) for b in boats.boats + boats.floating)
        rows.append(dict(event="Lifeboat seats used", step=None, when=None, detail=f"{used:,} of {TOTAL_SEATS:,}"))
    if scenario == "pompeii":
        causes = engine.death_breakdown()["causes"]
        for cause, count in causes.items():
            rows.append(dict(event=f"Deaths: {cause.replace('_', ' ')}", step=None, when=None, detail=f"{count:,}"))
    if scenario == "waterloo":
        for level, count in engine.exposure_summary().items():
            rows.append(dict(event=f"Exposure: {level}", step=None, when=None, detail=str(count)))
    return rows


def _summary_rows(scenario, engine, mind, seed, title, steps_run, horizon):
    agent = engine.agent
    alive = agent.is_alive
    rows = [("Scenario", title or SCENARIO_NAMES.get(scenario, scenario)), ("Seed", seed), ("Mind", MIND_NAMES.get(mind, mind)), ("Status", MODEL_FOOTER)]
    mapping = _mapping_row(scenario, engine)
    if mapping:
        rows.append(("Cue translation (assumption)", f"{mapping[0]}: {mapping[2]}"))
    rows += [("Steps run", f"{steps_run} of {horizon}"), ("Simulated time", elapsed_text(scenario, steps_run))]
    if scenario in CROWD:
        line = crowd_line(scenario, engine)
        rows.append(("People", line["total"]))
        if line["deaths"] is None:
            rows += [("Off the site", line["survivors"]), ("Off-site rate", round(line["survivors"] / line["total"], 4))]
        else:
            rows += [("Survived", line["survivors"]), ("Died", line["deaths"]), ("Survival rate", round(line["survivors"] / line["total"], 4))]
        if scenario == "titanic":
            rows.append(("History, for context", "About 712 of 2,208 survived"))
        rows.append(("Person followed", getattr(agent, "label", "Survivor")))
    rows.append(("Followed person's outcome", "Survived" if alive else f"Died: {str(agent.cause_of_death).replace('_', ' ')}"))
    rows += [("Final stress", round(agent.stress, 3))]
    return [dict(field=field, value=value) for field, value in rows]


def _assumption_rows(scenario, engine):
    from mind.config import DECISION_RULE, DEPHASING_MODE, ETA

    rows = [
        ("Decision rule", DECISION_RULE, "mind/config.py"),
        ("Dephasing", DEPHASING_MODE, "mind/config.py"),
        ("ETA", ETA, "Solved from Tversky & Shafir 1992"),
        ("Length of one decision", elapsed_text(scenario, 1), "Engine step"),
        ("Hazard timing and rates", "Assumed unless a source is cited", "See the scenario's document in docs/"),
    ]
    mapping = _mapping_row(scenario, engine)
    if mapping:
        rows.insert(0, ("Cue translation", f"{mapping[0]} ({mapping[1]}): {mapping[2]}", "An assumption. Results move with it"))
    notes = dict(
        titanic="A compressed demonstration, not a reconstruction. See docs/TITANIC_MODEL.md",
        pompeii="A demonstration, not a reconstruction. The default settings overstate escape. See docs/POMPEII_SOURCES.md",
        waterloo="A hypothetical at a real site. The leak, head-count and inside are assumed. See docs/WATERLOO_SOURCES.md",
        volcano="A fictional volcano with assumed rates. See docs/VOLCANO_MODEL.md",
    )
    if scenario in notes:
        rows.append(("Scope", notes[scenario], "Scenario document"))
    return [dict(item=item, value=value, source=source) for item, value, source in rows]


def paired_rows(paired):
    """The paired run as a table. None means it was not available when the report was built."""
    if paired is None:
        return [dict(field="Paired run", value="Not available")]
    rows = [dict(field="Mind", value=MIND_NAMES.get(paired["mind"], paired["mind"]))]
    labels = dict(
        survived="Survived", steps="Steps run", hide_after_sign="Steps from first sign to first hide", survivors="Survivors", deaths="Deaths", total="People"
    )
    rows += [dict(field=label, value=paired[key]) for key, label in labels.items() if key in paired]
    return rows


def build_report(scenario, engine, mind, seed, paired=None, title=None, horizon=None):
    """Every table for a finished run, as {sheet name: list of row dicts}."""
    steps = engine.steps
    timeline = engine.timeline()
    horizon = horizon or getattr(engine, "horizon", None) or 36
    sheets = {
        "Summary": _summary_rows(scenario, engine, mind, seed, title, len(steps), horizon),
        "Key events": _key_event_rows(scenario, engine, timeline),
        "Timeline": _timeline_rows(scenario, steps),
        "Crowd over time": _crowd_rows(scenario, steps),
        "Groups": _group_rows(scenario, engine),
        "Decisions": _decision_rows(steps),
        "Paired run": paired_rows(paired),
        "Assumptions": _assumption_rows(scenario, engine),
    }
    return {name: sheets[name] for name in SHEET_ORDER if sheets[name]}


def key_lines(report):
    """Up to three short lines of crucial events for the debrief, from the Key events table."""
    happened = [r for r in report.get("Key events", []) if r["detail"] != "Did not happen"]
    parts = [f"{r['event']}: {r['when'] or r['detail']}" for r in happened]
    lines, line = [], ""
    for part in parts:
        trial = f"{line}   |   {part}" if line else part
        if len(trial) > 96 and line:
            lines.append(line)
            line = part
        else:
            line = trial
    return (lines + [line] if line else lines)[:3]


def report_name(scenario, seed, mind, engine=None, stamp=None):
    mapping = getattr(engine, "event_mapping", None)
    parts = [scenario, f"seed{seed}", mind] + ([str(mapping)] if mapping else []) + [stamp or datetime.now().strftime("%Y%m%d-%H%M%S")]
    return re.sub(r"[^A-Za-z0-9_.-]", "-", "_".join(parts))


def _commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _columns(rows):
    columns = []
    for row in rows:
        columns += [key for key in row if key not in columns]
    return columns


def write_csv(report, folder):
    """One CSV per table. utf-8-sig, so Excel reads λ and ΔP correctly."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, rows in report.items():
        path = folder / (name.lower().replace(" ", "_") + ".csv")
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=_columns(rows))
            writer.writeheader()
            writer.writerows(rows)
        paths.append(path)
    return paths


def write_xlsx(report, path):
    """One workbook with a sheet per table."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    book = Workbook()
    book.remove(book.active)
    header_font, header_fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="6A401C")
    for name, rows in report.items():
        sheet = book.create_sheet(name)
        columns = _columns(rows)
        sheet.append([c.replace("_", " ").capitalize() for c in columns])
        for row in rows:
            sheet.append([row.get(c) for c in columns])
        for cell in sheet[1]:
            cell.font, cell.fill, cell.alignment = header_font, header_fill, Alignment(vertical="center")
        sheet.freeze_panes = "A2"
        for index, column in enumerate(columns, start=1):
            longest = max([len(str(column))] + [len(str(row.get(column, ""))) for row in rows[:200]])
            sheet.column_dimensions[sheet.cell(row=1, column=index).column_letter].width = min(60, longest + 3)
    book.properties.title = "Qognition report"
    book.properties.description = MODEL_FOOTER
    book.save(path)
    return path


def export_report(report, name, out_dir=DEFAULT_DIR):
    """Writes <name>.xlsx and a <name>/ folder of CSVs. Returns (xlsx path, csv folder)."""
    out_dir = Path(out_dir)
    stamped = dict(report)
    stamped["Summary"] = report["Summary"] + [
        dict(field="Generated", value=datetime.now().isoformat(timespec="seconds")),
        dict(field="Code version", value=_commit()),
    ]
    workbook = write_xlsx(stamped, out_dir / f"{name}.xlsx")
    write_csv(stamped, out_dir / name)
    return workbook, out_dir / name


def _simulation(scenario, seed, mind, settings):
    if scenario == "titanic":
        from engine.titanic import TitanicSimulation as Simulation
    elif scenario == "pompeii":
        from engine.pompeii import PompeiiSimulation as Simulation
    elif scenario == "waterloo":
        from engine.waterloo import WaterlooSimulation as Simulation
    else:
        from engine.simulation import SimulationEngine as Simulation

        return Simulation(seed=seed, mind_type=mind, scenario=scenario)
    return Simulation(seed=seed, mind_type=mind, **settings)


def run_and_report(scenario, seed=42, mind="quantum", settings=None, out_dir=DEFAULT_DIR):
    """Headless: run the event, then its paired run, then write the report."""
    settings = settings or {}
    engine = _simulation(scenario, seed, mind, settings)
    engine.run()
    paired = paired_run(scenario, seed, mind, settings)
    report = build_report(scenario, engine, mind, seed, paired=paired)
    return (report, *export_report(report, report_name(scenario, seed, mind, engine), out_dir))


__all__ = ["CUE_TRANSLATIONS", "build_report", "export_report", "key_lines", "paired_rows", "report_name", "run_and_report", "write_csv", "write_xlsx"]

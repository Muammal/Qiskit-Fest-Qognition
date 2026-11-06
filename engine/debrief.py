"""Numbers for the end-of-run debrief, kept out of the drawing code.

One debrief at the end, no mid-run cutscenes. Titles are based on the steps actually
endured, and the paired comparison reruns the same seed with the other mind.
"""

import threading

from engine.events import VOLCANIC

HOURS_PER_STEP = {"titanic": 5 / 60, "pompeii": 0.25, "waterloo": 10 / 3600}
MODEL_FOOTER = "A model, not a prediction."


def elapsed_text(scenario, steps):
    hours = steps * HOURS_PER_STEP.get(scenario, 2)
    if hours >= 1:
        return f"{hours:.0f} h" if float(hours).is_integer() else f"{hours:.1f} h"
    return f"{round(hours * 60)} min"


def run_title(alive, steps, horizon, cause, scenario="volcano"):
    """The banner. Survival is only claimed for the whole horizon."""
    span = elapsed_text(scenario, steps)
    if not alive:
        return f"DIED AFTER {span}: {str(cause).replace('_', ' ').upper()}"
    if steps >= horizon:
        return f"SURVIVED THE FULL {span}"
    return f"RUN STOPPED AT {span}, STILL ALIVE"


def control_for(mind):
    return "classical_mixture" if mind == "quantum" else "quantum"


def first_hide(steps):
    sign = next((s["t"] for s in steps if s["event"] in VOLCANIC), None)
    if sign is None:
        return None
    return next((s["t"] - sign for s in steps if s["action"] == "hide" and s["t"] >= sign), None)


def crowd_line(scenario, sim):
    counts = sim.counts()
    total = len(sim.people)
    if scenario == "titanic":
        return dict(survivors=counts["boats"], deaths=total - counts["boats"], total=total)
    if scenario == "pompeii":
        return dict(survivors=total - counts["dead"], deaths=counts["dead"], total=total)
    return dict(survivors=counts["off_site"], deaths=None, total=total)


def paired_run(scenario, seed, mind, settings):
    """The other mind on the same seed and settings. Returns a plain summary."""
    other = control_for(mind)
    if scenario in ("island", "volcano"):
        from engine.simulation import SimulationEngine

        timeline = SimulationEngine(seed=seed, mind_type=other, scenario=scenario).run()
        return dict(mind=other, survived=timeline["outcome"] == "survived", steps=len(timeline["steps"]), hide_after_sign=first_hide(timeline["steps"]))
    if scenario == "titanic":
        from engine.titanic import TitanicSimulation as Simulation
    elif scenario == "pompeii":
        from engine.pompeii import PompeiiSimulation as Simulation
    else:
        from engine.waterloo import WaterlooSimulation as Simulation
    sim = Simulation(seed=seed, mind_type=other, **settings)
    sim.run()
    return dict(mind=other, **crowd_line(scenario, sim))


class PairedResult:
    """Runs the comparison on a thread, so the debrief opens at once."""

    def __init__(self):
        self.key, self.value, self.thread = None, None, None

    def request(self, scenario, seed, mind, settings):
        key = (scenario, seed, mind, tuple(sorted((k, str(v)) for k, v in settings.items())))
        if key == self.key:
            return
        self.key, self.value = key, None

        def work():
            result = paired_run(scenario, seed, mind, settings)
            if self.key == key:
                self.value = result

        self.thread = threading.Thread(target=work, daemon=True)
        self.thread.start()


def paired_text(mine, other):
    """One line comparing this run with the paired run."""
    label = {"quantum": "Quantum", "classical_mixture": "Mixture control", "classical": "Classical"}
    if other is None:
        return "Paired run on this seed: computing..."
    name = label[other["mind"]]
    if "survived" in other:
        steps = other["hide_after_sign"]
        delay = "never hid" if steps is None else f"hid {steps} step{'' if steps == 1 else 's'} after the first sign"
        fate = "survived" if other["survived"] else f"died at step {other['steps']}"
        return f"{name} on this seed: {fate}, {delay}."
    if other["deaths"] is None:
        return f"{name} on this seed: {other['survivors']} of {other['total']} off site. This run: {mine['survivors']}."
    return f"{name} on this seed: {other['survivors']:,} survived, {other['deaths']:,} died. This run: {mine['survivors']:,} and {mine['deaths']:,}."

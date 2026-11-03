# Roles

**3 tech + 2 product.** Each person owns one area, their own demo moment, and their own slide content.

## How we stay independent

The tech side and the product side touch at only **three hand-off points**, all files rather than conversations:

1. **Tuesday:** a sample `timeline.json` (Tech C → Product D), so the website can be built immediately
2. **Thursday 6pm:** the `demo-pack/` folder (Tech → Product): curated runs, plots, short explainers
3. **Friday:** full-team rehearsal

Inside the tech team, everyone codes against **frozen interfaces with stubs** (see `TECH_STACK.md`), so nobody waits on anybody.

---

## Tech A: Quantum Mind

**Owns:** `mind/`

- Build the 2-qubit mind circuit: priors → rotation angles, events → belief rotations, measurement → action
- Implement `quantum_decide(state)` returning action, probabilities, and a plain-language `reason`
- Build the **delay-decoherence circuits** (same decision circuit with increasing idle time) for the hardware stress experiment
- Validate against an existing quantum cognition library (order effect + QQ-equality test)
- **Tuesday gate:** an Aer notebook showing a clear order effect
- **Demos owned:** order effect, uncertainty paralysis, stress = decoherence
- **Demo pack:** 3 short explainers (about 5 sentences + 1 figure each)
- **Also:** fields quantum questions from judges; gives the 20-minute science briefing to Product on Wednesday

## Tech B: Data, Classical Baseline, Hardware

**Owns:** `data/`, `baseline/`, `hardware/`

- Turn the American Time Use Survey **published summary tables** into `priors.json` + `get_prior(state)`. No scraping, no model training.
- Implement `classical_decide(state)`, the "normal human with no quantum quirks" baseline
- Set up IBM Quantum access, run the Tuesday test job, **submit the batched hardware job on Wednesday**, fetch results, write `hardware_results.json`
- Build the **fake-backend fallback** first, so the sim always has data
- **Demos owned:** classical vs. quantum divergence chart (from Tech C's batch runs)
- **Demo pack:** 2 explainers + plots
- **Optional (if ahead Thursday noon):** quantum walk exploration via `explore_step`

## Tech C: World, Engine, Integration

**Owns:** `engine/`, `contracts.py`, `requirements.txt`

- Day 1: commit `contracts.py` with working stubs, a pinned `requirements.txt`, and a hand-written sample `timeline.json`
- World generation from seed (terrain, water, food, shelter spots)
- Needs decay, events, action effects, survival/death conditions
- Game loop calling the contract functions; writes `timeline.json`
- Batch runner: many runs × {quantum, classical} for Tech B's chart
- **Runs the full loop every evening from Tuesday** (daily integration, no Thursday big bang)
- **Demos owned:** live run from a random seed
- **Demo pack:** 5–6 curated runs (best order-effect pair, a dramatic death, a survival)

## Product D: Website + Replay Viewer (builder)

**Owns:** `site/`

- Static website (HTML/JS, no backend), hosted on GitHub Pages or Netlify
- Landing page: hook, what Stranded is, call to action
- **Replay viewer:** loads `timeline.json` and shows the map, agent movement, need bars, event pop-ups
- **"Why did he do that?" panel:** shows `probs` and `reason` for each step
- "The science" page rendering Product E's markdown + Tech's figures
- **Optional:** side-by-side mode (two timelines at once)
- Builds entirely off the sample JSON until Thursday

## Product E: Story, Pitch, Submission (storyteller)

**Owns:** `pitch/`, `site/content/` (markdown only)

- **Tuesday first:** check the event rules (prompts/tracks, judging criteria, submission requirements) and share them
- Name, tagline, an original logo/visual identity, a style file for Product D
- Pitch deck: hook → what Stranded is → 3 quantum ideas in plain language → demo → what's real vs. metaphor → team
- Demo script (who clicks what, timings)
- **Demo video** (1–2 minutes, recorded Thursday night): backup for the live demo
- Website copy + submission write-up
- One-page judge FAQ (from `RISKS_AND_FAQ.md`)
- Runs rehearsals and times the pitch

---

## Rules

- **One folder per person.** Never edit someone else's folder.
- **Tech never edits `site/`; Product never edits Python.** `demo-pack/` is the only shared folder.
- **Contract or JSON format changes need the whole team**, in one dedicated channel. Everything else, decide yourself.
- **Waiting on someone? Use the stub or sample.** Never block.
- **Evening check-in (5–10 min):** done / next / stuck.

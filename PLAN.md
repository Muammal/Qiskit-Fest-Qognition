# Plan

Lean scope for a week-long hackathon. Catch the big risks early (Tuesday/Wednesday) and always have something presentable.

## Scope

**Must have (this is the project):**
- Quantum mind (2 qubits) with an order effect
- Stress as real hardware decoherence (delay experiment) + fake-backend fallback
- Classical-mind baseline
- World + survival loop writing `timeline.json`
- Replay website + "why" panel
- Demo video

**Only if ahead by Thursday noon:** quantum walk exploration, side-by-side viewer mode

**Cut:** QAOA planner, settlement/civilization ending, IBM random seeds, web scraping, ML training

## Go/no-go checkpoints

| When | Check | If it fails |
|---|---|---|
| **Tue evening** | Event rules checked and shared | Adjust scope to fit prompts/judging before building |
| **Tue evening** | Everyone's IBM account works (Bell test submitted) | Use the accounts that work; fake backend covers the rest |
| **Tue evening** | Tech A's Aer notebook shows a **clear order effect** | Tune angles Wednesday morning; if still weak, lead with stress-decoherence as the main story |
| **Wed evening** | Fake-backend results saved **and** hardware job submitted | Demo on the fake backend, labelled "simulated device noise" |
| **Thu noon** | Full end-to-end run produces a JSON the site plays | Cut optional features; fix only |
| **Thu night** | 3 curated runs + demo video recorded | Friday = polish only |

## Daily schedule

| Day | Tech (A, B, C) | Product (D, E) |
|---|---|---|
| **Tue** | C: `contracts.py` + stubs, pinned `requirements.txt`, sample `timeline.json`. Everyone: IBM account + test job. A: order-effect notebook (**gate**) + library check. B: ATUS tables → draft priors. | E: check event rules, name, style file, pitch outline. D: site skeleton playing the sample JSON. |
| **Wed** | A: final mind circuit + delay-decoherence circuits. B: priors + classical baseline + fake-backend runs, then **submit the hardware job**. C: world + loop; evening integration run. | D: replay viewer + "why" panel. E: deck draft, FAQ, website copy. **20-minute science briefing** from Tech A. |
| **Thu** | Hardware results loaded into sim. **Noon gate.** Afternoon: curate runs, plots, explainers → `demo-pack/` by 6pm. Feature freeze. | Swap in real JSON + figures. Science page done. **E records demo video** Thursday night. |
| **Fri** | Bug fixes only. Rehearse answering judge questions. | Final polish, 2 full rehearsals, **submit early**. |

## Daily integration

Tech C runs the **full loop every evening from Tuesday**, using whatever is real so far and stubs for the rest. Problems surface one at a time instead of all at once on Thursday.

## Cut order (if behind)

1. Side-by-side viewer mode
2. Quantum walk exploration
3. Real hardware runs (fall back to fake backend, labelled)

**Never cut:** quantum mind, order effect, stress-decoherence (fake backend at minimum), classical baseline, replay viewer, demo video.

## Definition of done

- [ ] `quantum_decide` shows an order effect the classical baseline doesn't
- [ ] Stress visibly changes decisions (hardware or labelled fake backend)
- [ ] 3+ curated runs play on the website with the "why" panel
- [ ] Demo video recorded
- [ ] Repo README with setup, what's real vs. metaphor, and library credits
- [ ] Pitch rehearsed twice; everyone knows the FAQ
- [ ] Submitted before the deadline

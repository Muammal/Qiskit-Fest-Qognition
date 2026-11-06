# Risks and FAQ

_Written for the hackathon judging, and corrected since. The numbers are current._

## Risks and mitigations

| Risk | Mitigation | Owner |
|---|---|---|
| **No visible quantum vs. classical difference** | Checked **Tuesday night** in Aer before anything is built on it. Design scenarios (order swaps, uncertainty) where interference matters. If weak, lead with stress-decoherence. | Tech A |
| **IBM queue or access fails** | Sim never calls hardware live. **No IBM hardware job was submitted.** The only backend run is `FakeTorino`, a simulator using a saved calibration snapshot (`mind/results/fake_backend_run.json`). | Tech B |
| **Qiskit version breakage** | Exact versions pinned Tuesday; one shared environment. | Tech C |
| **Library conflicts or bugs** | Libraries are validation only; our circuit is the core. Drop the library if it conflicts. | Tech A |
| **Integration breaks** | Frozen contracts + stubs from day one; full loop run every evening from Tuesday. | Tech C |
| **Data work eats the week** | Published ATUS summary tables only; half-day limit; hand-set priors as fallback. | Tech B |
| **Live demo crashes** | Website replays recorded JSON; demo video as backup. | Product D + E |
| **Scope creep** | Cut list + feature freeze Thursday night. | Everyone |
| **Overclaiming in the pitch** | Banned phrases: "understands how humans think," "faster," "brains are quantum." Also banned: "runs on real hardware," "prediction." Use "models," "fits human decision patterns," "simulated with a saved IBM noise snapshot." | Product E |
| **Product teammates get a technical question** | Everyone learns this FAQ; Tech A takes quantum questions. | Product E + Tech A |
| **Rules mismatch** (set prompts, code-only judging) | Checked Tuesday. If judging is on code, make the repo/notebook clean and runnable; the website is a bonus. | Product E |
| **Last-minute submission problems** | Submit Friday early; keep polishing only if re-submission is allowed. | Product E |
| **API keys leaked** | `.env` in `.gitignore`; never paste keys in code or chat. | Everyone |

---

## FAQ

### "Why Qiskit instead of NumPy?"
> At this size a classical computer runs our model easily, since quantum cognition models are linear algebra. We used Qiskit because (1) the model is naturally quantum: beliefs are states, decisions are measurements, and order effects come from measurements that don't commute; (2) the same circuits could be sent to IBM hardware, although we have not done that: only `FakeTorino` simulation was run, so no part of the model's stress comes from physical decoherence; (3) richer minds scale exponentially, since many interacting beliefs need 2ⁿ amplitudes, which is where quantum hardware becomes the natural home for models like this. We don't claim a speedup today.

*Have ready:* a check that our circuit's output matches the analytic formula for a simple case.

### "Is stress = decoherence real?"
> It's a modelling choice, not a claim about the brain. In quantum cognition, the "irrational" effects come from interference terms. Decoherence destroys those terms, so as stress rises his choices drift toward classical-probability behaviour and get noisier. In the game this is a simulated dephasing channel. The delay experiment measures the same decay on `FakeTorino`'s simulated noise, not on a chip. Whether human stress works this way is a hypothesis our model makes, not something we claim.

*Have ready:* "What's real vs. metaphor" slide; plot of interference shrinking with delay.

### "Is quantum cognition legit? Are you saying brains are quantum?"
> No. Quantum cognition uses quantum probability as math that fits human decision data. It's an established research area (Busemeyer & Bruza), and a 2014 PNAS study found survey order effects matched a quantum probability prediction (the QQ equality). It's also debated, and we treat it as a model, not a fact.

*Have ready:* our reproduction of the order effect + QQ-equality check.

### "What does the data add?"
> His starting habits come from real time-use data, so he begins from how people actually spend their time instead of numbers we invented. The quantum layer models how he deviates from those habits under order, uncertainty, and stress.

### "How do you know the quantum mind behaves differently?"
> We ran 200 identical volcano worlds with each mind. The quantum mind's actions differ from the mixture control on 12.6% of compared steps, and it hides 0.55 steps later on average (SE 0.091; 45 later, 5 earlier, 90 same). Survival is the same, 99.5%, because this volcano leaves far more time than that delay costs. In simple situations they agree, which is expected, since quantum and classical probability only differ when interference matters. Source: `docs/tech-a/07-validation-report.md`.

### "Isn't the simulation itself classical?"
> Yes. The world, needs, and events are ordinary code. Only decision-making is quantum. We put quantum where it changes behaviour, not everywhere.

### "What did you build vs. use?"
> We built the mind circuits, the simulated backend experiments, the world and engine, the classical baseline, and the interface. We used Qiskit Aer and `qiskit-ibm-runtime`'s `FakeTorino` to check the circuits against the closed form under simulated noise. Neither `qcog` nor any other external cognition package was run; we reimplemented published formulas, and one of them (Huang belief entropy) fails its check. See `docs/tech-a/07-validation-report.md`.

### "Which machine did you run on?"
> None. No IBM hardware job was submitted, so there are no job IDs. We ran `FakeTorino`, a simulator with a saved noise snapshot, on 2026-11-04: 3 circuits at 4,000 shots each (`mind/results/fake_backend_run.json`), plus the delay experiment (`mind/results/delay_experiment.json`).

# Risks and Judge FAQ

## Risks and mitigations

| Risk | Mitigation | Owner |
|---|---|---|
| **No visible quantum vs. classical difference** | Checked **Tuesday night** in Aer before anything is built on it. Design scenarios (order swaps, uncertainty) where interference matters. If weak, lead with stress-decoherence. | Tech A |
| **IBM queue or access fails** | Sim never calls hardware live. Fake-backend results saved **first**; one batched job submitted Wednesday; save the job ID. Hardware is an upgrade, not a dependency. | Tech B |
| **Qiskit version breakage** | Exact versions pinned Tuesday; one shared environment. | Tech C |
| **Library conflicts or bugs** | Libraries are validation only; our circuit is the core. Drop the library if it conflicts. | Tech A |
| **Integration breaks** | Frozen contracts + stubs from day one; full loop run every evening from Tuesday. | Tech C |
| **Data work eats the week** | Published ATUS summary tables only; half-day limit; hand-set priors as fallback. | Tech B |
| **Live demo crashes** | Website replays recorded JSON; demo video as backup. | Product D + E |
| **Scope creep** | Cut list + feature freeze Thursday night. | Everyone |
| **Overclaiming in the pitch** | Banned phrases: "understands how humans think," "faster," "brains are quantum." Use "models," "fits human decision patterns," "runs on real hardware." | Product E |
| **Product teammates get a technical question** | Everyone learns this FAQ; Tech A takes quantum questions. | Product E + Tech A |
| **Rules mismatch** (set prompts, code-only judging) | Checked Tuesday. If judging is on code, make the repo/notebook clean and runnable; the website is a bonus. | Product E |
| **Last-minute submission problems** | Submit Friday early; keep polishing only if re-submission is allowed. | Product E |
| **API keys leaked** | `.env` in `.gitignore`; never paste keys in code or chat. | Everyone |

---

## Judge FAQ (prepared answers)

### "Why Qiskit instead of NumPy?"
> At this size a classical computer runs our model easily, since quantum cognition models are linear algebra. We used Qiskit because (1) the model is naturally quantum: beliefs are states, decisions are measurements, and order effects come from measurements that don't commute; (2) the same circuits run on real IBM hardware, and we did, so part of his stress comes from real physical decoherence; (3) richer minds scale exponentially, since many interacting beliefs need 2ⁿ amplitudes, which is where quantum hardware becomes the natural home for models like this. We don't claim a speedup today.

*Have ready:* a check that our circuit's output matches the analytic formula for a simple case.

### "Is stress = decoherence real?"
> It's a modelling choice, not a claim about the brain. In quantum cognition, the "irrational" effects come from interference terms. Decoherence destroys those terms, so as stress rises his choices drift toward classical-probability behaviour and get noisier. On hardware, the decoherence itself is real: qubits idling on the chip. Whether human stress works this way is a hypothesis our model makes, not something we claim.

*Have ready:* "What's real vs. metaphor" slide; plot of interference shrinking with delay.

### "Is quantum cognition legit? Are you saying brains are quantum?"
> No. Quantum cognition uses quantum probability as math that fits human decision data. It's an established research area (Busemeyer & Bruza), and a 2014 PNAS study found survey order effects matched a quantum probability prediction (the QQ equality). It's also debated, and we treat it as a model, not a fact.

*Have ready:* our reproduction of the order effect + QQ-equality check.

### "What does the data add?"
> His starting habits come from real time-use data, so he begins from how people actually spend their time instead of numbers we invented. The quantum layer models how he deviates from those habits under order, uncertainty, and stress.

### "How do you know the quantum mind behaves differently?"
> We ran [N] identical worlds with each mind. In scenarios with uncertainty or event-order changes they diverge by [X]; in simple situations they agree, which is expected, since quantum and classical probability only differ when interference matters.

### "Isn't the simulation itself classical?"
> Yes. The world, needs, and events are ordinary code. Only decision-making is quantum. We put quantum where it changes behaviour, not everywhere.

### "What did you build vs. use?"
> We built the mind circuits, the hardware experiments, the world and engine, the classical baseline, and the interface. We used [library] to validate our order effect against an established model, and Qiskit/IBM Runtime to run on hardware.

### "Which machine did you run on?"
> [Backend name], on [date], [N] circuits × 2,000 shots. Results and job IDs are in the repo.

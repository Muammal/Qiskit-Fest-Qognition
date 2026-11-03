# Agent Coordination & Role Directory

Welcome to the **Stranded: Quantum Cognition Survival Simulation** multi-agent coordination hub.

This repository branch (`agent-docs`) serves as the dedicated knowledge base for all autonomous and human engineering agents working on the project.

---

## Team Topology & Ownership Matrix

The project operates under a strict **3 Tech + 2 Product** division of responsibility. Each agent owns an isolated domain and codes against frozen interfaces defined in [TECH_STACK.md](../TECH_STACK.md).

```
                      +-----------------------------+
                      |   Stranded Simulation Hub   |
                      +--------------+--------------+
                                     |
         +---------------------------+---------------------------+
         |                                                       |
  [ Tech Track ]                                          [ Product Track ]
         |                                                       |
  +------+-------+-------+                                +------+-------+
  |              |       |                                |              |
Tech A        Tech B   Tech C                          Product D      Product E
Quantum Mind  Data &   World, Engine &                 Web Replay &   Narrative, Demo
& Circuits    Hardware Integration                     Visualizer     & Pitch Deck
```

| Agent | Role | Domain Ownership | Primary Deliverables | Specification |
|---|---|---|---|---|
| **Tech A** | Quantum Mind | `mind/` | 2-qubit decision circuit, order effect notebook, decoherence delay circuits | [TECH_A.md](./TECH_A.md) |
| **Tech B** | Data, Baseline & Hardware | `data/`, `baseline/`, `hardware/` | ATUS summary `priors.json`, `classical_decide()`, IBM hardware jobs & fake backend | [TECH_B.md](./TECH_B.md) |
| **Tech C** | World, Engine & Integration | `engine/`, `contracts.py`, `requirements.txt` | 40x40 procedural hydrology, survival loop, `timeline.json`, batch runner, GUI | [TECH_C.md](./TECH_C.md) |
| **Product D** | Web Replay & Visualizer | `site/` | Interactive timeline playback, island viewer, decision "Why" telemetry inspector | [PRODUCT_D.md](./PRODUCT_D.md) |
| **Product E** | Story, Demo Pack & Pitch | `pitch/`, `demo-pack/` | Curated runs, judge Q&A briefing, demo video recording, presentation deck | [PRODUCT_E.md](./PRODUCT_E.md) |

---

## The Three Frozen Hand-Off Points

To eliminate blocking dependencies between agents, collaboration is mediated exclusively through standardized data contracts:

1. **Tuesday Gate (Tech C -> Product D & E)**:
   - Hand-off: Sample `timeline.json` conforming to `contracts.py`.
   - Purpose: Allows Product D to immediately construct the web visualizer without waiting for quantum circuits.

2. **Thursday 6:00 PM Gate (Tech -> Product)**:
   - Hand-off: The `demo-pack/` directory containing 5 signature simulation runs (`run_01_heroic_survival.json` through `run_05_stress_decoherence.json`), matplotlib divergence plots, and short markdown explainers.
   - Purpose: Provides Product E with verified scientific data for video narration and deck assembly.

3. **Friday Rehearsal**:
   - Hand-off: Integrated live rehearsal answering judge defense questions prepared in [RISKS_AND_FAQ.md](../RISKS_AND_FAQ.md).

---

## Core Documentation References

- **[ROLES.md](../ROLES.md)**: Detailed individual commitments, demo ownership, and team protocols.
- **[TECH_STACK.md](../TECH_STACK.md)**: Frozen Python interfaces (`contracts.py`), environment requirements, and repository layout.
- **[PLAN.md](../PLAN.md)**: Lean hackathon milestone schedule, go/no-go gates, and feature cut priorities.
- **[RISKS_AND_FAQ.md](../RISKS_AND_FAQ.md)**: Technical risks, mitigations, and prepared answers to judge scrutiny.
- **[README.md](../README.md)**: Scientific concept, mathematical foundations of quantum cognition, and island simulation mechanics.

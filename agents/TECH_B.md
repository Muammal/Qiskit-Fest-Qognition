# Agent Specification: Tech B (Data, Baseline & Hardware)

## Overview & Role Mandate
**Role**: Data Engineer & Hardware Architect  
**Code Ownership**: `data/`, `baseline/`, `hardware/`  
**Core Objective**: Ground the agent's baseline behavior in empirical human time-use statistics, construct the classical rational decision baseline, execute hardware jobs on IBM Quantum processors, and manage fake-backend fallback pipelines.

---

## Deliverables & Milestones

### 1. Empirical Prior Extraction (`data/priors.json`)
- **Source**: Published American Time Use Survey (ATUS) summary activity tables (BLS).
- **Rule**: Strictly no web scraping and no complex ML model training. Extract high-level human time distribution (sleeping, eating, working/crafting, traveling) and normalize into survival action priors.
- **Contract Interface**:
  ```python
  def get_prior(state: dict) -> dict:
      """
      Returns probability distribution over ACTIONS derived from ATUS priors
      adjusted for the agent's current physiological needs.
      """
  ```

### 2. Classical Rational Baseline (`classical_decide`)
- **Implementation**: Deterministic utility / classical Bayesian decision rule representing a "rational human with no quantum interference or non-commuting order quirks".
- **Contract Interface**:
  ```python
  def classical_decide(state: dict) -> dict:
      """
      Returns:
          {
              "action": str,                # Selected action
              "probabilities": dict,       # Classical Boltzmann/utility distribution
              "reason": str                # Classical rational justification
          }
      """
  ```

### 3. IBM Quantum Hardware Pipeline (`hardware/`)
- **Tuesday Gate**: Test IBM Quantum credentials and submit a verification Bell-state / circuit job.
- **Fake-Backend Safety Net**: Construct and serialize fake-backend noise models first (e.g. `FakeManila` or `FakeSherbrooke`), ensuring the simulation never halts if IBM cloud queues stall.
- **Wednesday Evening Batch Job**: Submit the batched delay-decoherence circuits designed by Tech A to IBM Quantum hardware. Save the job ID for asynchronous result retrieval.
- **Output**: Write results to `hardware/hardware_results.json` for integration into Tech C's batch comparisons.

### 4. Demos Owned
- **Classical vs. Quantum Divergence Chart**: Statistical comparison showing where and why quantum and classical decision trajectories diverge over 100+ batch runs.
- **Hardware Noise Overlay**: Showing how real superconducting qubit thermal relaxation ($T_1 / T_2$) degrades cognitive coherence.

### 5. Demo-Pack Contribution (Due Thursday 6:00 PM)
- 2 concise explainers + plots:
  1. *From ATUS Statistics to Wilderness Priors: Grounding Cognition in Reality*
  2. *Classical Utility vs. Quantum Superposition: Divergence Under Risk*

### 6. Optional Extension (Thursday Noon Gate)
- If core hardware and baseline tasks are complete before Thursday noon, implement 2D quantum walk exploration on the island grid via `explore_step(state, map_grid)`.

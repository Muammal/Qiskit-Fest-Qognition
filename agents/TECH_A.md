# Agent Specification: Tech A (Quantum Mind)

## Overview & Role Mandate
**Role**: Quantum Mind Engineer  
**Code Ownership**: `mind/`  
**Core Objective**: Design, implement, and validate the 2-qubit quantum decision-making circuit modeling human cognitive bias, contextual interference, order effects, and physical decoherence under survival stress.

---

## Deliverables & Milestones

### 1. Tuesday Milestone (Go/No-Go Gate)
- **Deliverable**: Jupyter/Aer notebook demonstrating a mathematically verifiable **order effect** ($A \text{ then } B \neq B \text{ then } A$) in decision probabilities.
- **Validation**: Compare against an established quantum cognition formulation (e.g. Busemeyer & Bruza or Wang & Busemeyer QQ-equality test) using `quantum-mind` or `qcog`.
- **Contingency**: If order effect is faint or ambiguous, re-tune rotation angles on Wednesday morning; if still weak, elevate physical stress-decoherence as the headline quantum story.

### 2. Core Decision Engine (`quantum_decide`)
Implement the contract interface declared in `contracts.py`:
```python
def quantum_decide(state: dict) -> dict:
    """
    Executes 2-qubit quantum cognition decision circuit.
    Returns:
        {
            "action": str,                # Selected action from ACTIONS
            "probabilities": dict,       # Softmax or normalized measurement probabilities
            "reason": str                # Plain-language explanation for visualizer
        }
    """
```
- **Prior Encoding**: Map baseline habit prior angles from `get_prior(state)` to $R_y(\theta_1), R_y(\theta_2)$ state preparation.
- **Contextual Rotation**: Rotate belief state based on environmental hazards (`recent_events` like storms, animal encounters, injuries).
- **Projective Measurement**: Non-commuting observables project the state into action space (`forage`, `drink`, `build_shelter`, `rest`, `explore`, `craft`, `hide`).

### 3. Stress-Induced Decoherence Circuit
- **Mechanism**: Physiological stress ($0.0 \le \text{stress} \le 1.0$) mapped to qubit delay duration (`delay` gate) on real IBM Quantum backends / fake noise models.
- **Physical Consequence**: Idling qubits accumulate phase and amplitude damping errors, destroying off-diagonal quantum interference terms.
- **Observable Behavior**: At low stress, the agent leverages sharp interference; at high stress, decisions decay toward noisy classical distributions, causing panic and paralysis.

### 4. Demos & Explanations Owned
1. **Order Effect Demonstration**: Identical state subjected to $[ \text{storm} \to \text{find\_food} ]$ vs $[ \text{find\_food} \to \text{storm} ]$ yielding drastically different actions.
2. **Uncertainty Paralysis**: Superposition across survival priorities creating decision stagnation when vital needs conflict.
3. **Stress as Physical Decoherence**: Hardware noise degradation curves matching survival performance decay.

### 5. Demo-Pack Contribution (Due Thursday 6:00 PM)
- 3 concise explainers (~5 sentences each + 1 visualization figure):
  1. *The 2-Qubit Cognitive Hilbert Space*
  2. *Why Event Order Non-Commutativity Matters in Wilderness Survival*
  3. *Decoherence Under Duress: Physical Qubit Relaxation as Human Stress*

### 6. Team Support
- Lead the **20-minute Science Briefing** to Product D & E on Wednesday.
- Answer technical quantum inquiries during the judge pitch defense.

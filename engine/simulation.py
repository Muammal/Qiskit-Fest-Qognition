"""
engine/simulation.py - Core Survival Game Loop and Timeline Serializer
Owned by Tech C (Integration, Engine, Simulation).
"""

import json
import os
import sys
import random
from typing import Any, Callable, Dict, List, Optional

# Ensure contracts can be imported
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import contracts
from engine.world import IslandWorld
from engine.agent import SurvivalAgent
from engine.events import EventGenerator


class SimulationEngine:
    """
    Executes turn-based survival simulations, integrating world mechanics,
    stochastic environmental hazards, and quantum/classical decision minds.
    Outputs timeline.json for the frontend replay viewer.
    """

    def __init__(
        self,
        seed: int = 42,
        mind_type: str = "quantum",
        noise_source: str = "fake_backend",
        decide_fn: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
    ):
        self.seed = seed
        self.mind_type = mind_type.lower()
        self.noise_source = noise_source
        self.world = IslandWorld(seed=seed)
        self.agent = SurvivalAgent(start_pos=self.world.spawn_pos)
        self.event_gen = EventGenerator(seed=seed)
        
        # Select decision policy: custom callable > contracts.quantum_decide > contracts.classical_decide
        if decide_fn is not None:
            self.decide_fn = decide_fn
        elif self.mind_type == "quantum":
            self.decide_fn = contracts.quantum_decide
        else:
            self.decide_fn = contracts.classical_decide

    def run(
        self,
        max_steps: int = 24,
        step_callback: Optional[Callable[[Dict[str, Any], Any], None]] = None
    ) -> Dict[str, Any]:
        """
        Executes the game loop for up to max_steps (e.g. 24 steps = 48 game hours / 2 days).
        Returns timeline dictionary strictly matching contracts.py and timeline.json schema.
        Optionally invokes step_callback(step_record, engine) on each simulation step.
        """
        random.seed(self.seed)
        steps_log: List[Dict[str, Any]] = []

        for t in range(max_steps):
            if not self.agent.is_alive:
                break

            # 1. State snapshot before action
            current_state = self.agent.get_state()
            contracts.validate_state(current_state)

            # 2. Environmental Hazard Evaluation
            in_shelter = self.world.is_in_shelter(self.agent.pos[0], self.agent.pos[1])
            event = self.event_gen.step_event(
                day=self.agent.day,
                hour=self.agent.hour,
                current_pos=self.agent.pos,
                in_shelter=in_shelter,
                injured=self.agent.injured
            )

            # 3. Apply immediate event impact to agent
            self.agent.apply_event(event, in_shelter=in_shelter)

            # State after event impact, presented to the mind
            decision_state = self.agent.get_state()

            # 4. Invoke Decision Mind (Quantum or Classical Contract)
            decision = self.decide_fn(decision_state)
            contracts.validate_decision(decision)

            # 5. Resolve Action Effects on World and Agent
            action = decision["action"]
            narrative = self.agent.execute_action(action, self.world)

            # 6. Natural Physiological Decay
            in_shelter_after = self.world.is_in_shelter(self.agent.pos[0], self.agent.pos[1])
            self.agent.step_decay(in_shelter=in_shelter_after)

            # 7. Record Step Log
            step_record = {
                "t": t,
                "state": decision_state,
                "event": event,
                "action": action,
                "probs": decision["probs"],
                "reason": decision.get("reason", narrative)
            }
            steps_log.append(step_record)

            # 8. Interactive Step Notification
            if step_callback is not None:
                step_callback(step_record, self)

        outcome = "survived" if self.agent.is_alive else "died"
        cause = self.agent.cause_of_death

        timeline = {
            "world": {
                "width": self.world.width,
                "height": self.world.height,
                "tiles": self.world.tiles,
                "seed": self.seed,
                "mind": self.mind_type,
                "noise_source": self.noise_source
            },
            "steps": steps_log,
            "outcome": outcome,
            "cause": cause
        }
        return timeline

    def run_and_save(self, output_path: str, max_steps: int = 24) -> Dict[str, Any]:
        """Runs the simulation and persists timeline.json to disk."""
        timeline = self.run(max_steps=max_steps)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(timeline, f, indent=2)
        return timeline

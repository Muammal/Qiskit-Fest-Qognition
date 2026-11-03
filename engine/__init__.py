"""
engine - Stranded Procedural World & Survival Simulation Engine
Owned by Tech C (Integration, Engine, Contracts).
"""

from .world import IslandWorld
from .agent import SurvivalAgent
from .events import EventGenerator
from .simulation import SimulationEngine
from .batch_runner import run_batch_comparison, curate_demo_pack

__all__ = [
    "IslandWorld",
    "SurvivalAgent",
    "EventGenerator",
    "SimulationEngine",
    "run_batch_comparison",
    "curate_demo_pack"
]


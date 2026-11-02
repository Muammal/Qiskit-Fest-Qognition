"""
Shared Utilities, Quantum Telemetry HUD, and Iteration Orchestration for Real-Time Game Runners.
"""

import os
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import numpy as np

# Ensure root directory and qiskit_exploit_hunter are accessible
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PACKAGE_DIR = os.path.join(ROOT_DIR, "qiskit_exploit_hunter")
for p in [ROOT_DIR, PACKAGE_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)


@dataclass
class IterationLog:
    iteration_num: int
    game_name: str
    is_exploit: bool
    exploit_type: str
    anomaly_score: float
    detected: bool
    q_expectations: np.ndarray
    summary_text: str


class QuantumTerminalHUD:
    """Renders real-time HUD with colored status banners, quantum observables, and anomaly gauges."""

    # ANSI Colors
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

    @classmethod
    def render_iteration_header(cls, game_title: str, iter_idx: int, total_iters: int, is_exploit: bool):
        badge = f"{cls.RED}{cls.BOLD}[BACKGROUND EXPLOIT INJECTION]{cls.RESET}" if is_exploit else f"{cls.GREEN}{cls.BOLD}[REGULAR GAMEPLAY]{cls.RESET}"
        print("\n" + "=" * 80)
        print(f" {cls.CYAN}{cls.BOLD}GAME SIMULATION: {game_title.upper()}{cls.RESET} | Iteration {cls.BOLD}{iter_idx}/{total_iters}{cls.RESET} | {badge}")
        print("=" * 80)

    @classmethod
    def render_quantum_state_hud(
        cls,
        q_expectations: np.ndarray,
        anomaly_score: float,
        is_exploit_flagged: bool,
        exploit_label: str = ""
    ):
        """Draws dynamic quantum observables and anomaly score meter."""
        print(f"{cls.YELLOW}{cls.BOLD}--- REAL-TIME QUANTUM TELEMETRY HUD (Qiskit 4-Qubit Circuit & Kernel) ---{cls.RESET}")
        
        # 4 Qubit Expectation Meters
        q_meters = []
        for i, val in enumerate(q_expectations[:4]):
            val_clamped = float(np.clip(val, -1.0, 1.0))
            bar_len = 10
            pos = int(round((val_clamped + 1.0) / 2.0 * bar_len))
            pos = min(bar_len, max(0, pos))
            bar = ["-"] * (bar_len + 1)
            bar[pos] = "O"
            bar_str = "".join(bar)
            q_meters.append(f"Q{i}<Z{i}>:[{bar_str}] {val_clamped:+5.2f}")
        print("  " + " | ".join(q_meters))

        # Anomaly Meter
        norm_score = float(np.clip((anomaly_score + 0.1) * 20, 0, 20))
        bar_gauge = "#" * int(norm_score) + "-" * (20 - int(norm_score))
        
        if is_exploit_flagged and exploit_label and exploit_label != "None":
            status_tag = f"{cls.RED}{cls.BOLD}[ALERT: EXPLOIT DETECTED! - {exploit_label}]{cls.RESET}"
        else:
            status_tag = f"{cls.GREEN}[NORMAL LEGAL STATE]{cls.RESET}"

        print(f"  Anomaly Gauge : [{cls.RED if is_exploit_flagged else cls.GREEN}{bar_gauge}{cls.RESET}] Score: {anomaly_score:+6.4f} -> {status_tag}")
        print("-" * 80)

    @classmethod
    def render_summary_table(cls, logs: List[IterationLog]):
        print("\n" + "=" * 80)
        print(f"{cls.CYAN}{cls.BOLD}   FINAL ITERATION BREAKDOWN & QUANTUM INTERCEPTION REPORT{cls.RESET}")
        print("=" * 80)
        print(f" {'ITER':<5} | {'MODE':<20} | {'EXPLOIT TYPE':<22} | {'ANOMALY SCORE':<14} | {'STATUS'}")
        print("-" * 80)
        
        total_exploits = sum(1 for l in logs if l.is_exploit)
        detected_exploits = sum(1 for l in logs if l.is_exploit and l.detected)

        for l in logs:
            mode_str = f"{cls.RED}Exploit Fuzzing{cls.RESET}" if l.is_exploit else f"{cls.GREEN}Regular Play{cls.RESET}"
            verdict = f"{cls.RED}[INTERCEPTED]{cls.RESET}" if (l.is_exploit and l.detected) else (f"{cls.GREEN}[LEGAL PASS]{cls.RESET}" if not l.is_exploit else f"{cls.YELLOW}[MISSED]{cls.RESET}")
            print(f" #{l.iteration_num:<4} | {mode_str:<29} | {l.exploit_type:<22} | {l.anomaly_score:+13.4f} | {verdict}")

        print("=" * 80)
        print(f" Total Iterations Shown : {len(logs)}")
        print(f" Regular Gameplay Runs : {len(logs) - total_exploits}")
        print(f" Injected Exploits     : {total_exploits} | Intercepted by Quantum Kernel: {cls.BOLD}{detected_exploits}/{total_exploits}{cls.RESET}")
        print("=" * 80)

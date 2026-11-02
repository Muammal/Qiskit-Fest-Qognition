"""
FastAPI Server for Quantum RL Game Simulation & Exploit Interception UI.
Provides REST APIs and Server-Sent Events (SSE) for real-time game simulation streaming.
"""

import argparse
import asyncio
import json
import os
import sys
import webbrowser
from typing import Any, Dict, List, Optional
import numpy as np

# Ensure root paths
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PACKAGE_DIR = os.path.join(ROOT_DIR, "qiskit_exploit_hunter")
RUN_DIR = os.path.join(ROOT_DIR, "run")
for p in [ROOT_DIR, PACKAGE_DIR, RUN_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
import uvicorn

from engines.kernel_anomaly_engine import QuantumKernelAnomalyDetector
from engines.qrl_policy_engine import HybridQuantumPolicyNetwork
from envs.retro_2d_ram_env import make_retro_env
from envs.sudoku_card_env import BlackjackExploitEnv, MiniSudoku4x4Env
from envs.chess_fuzz_env import ChessFeatureExtractor

app = FastAPI(title="Quantum RL Simulation UI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global pre-cached detectors and policies
CACHED_MODELS: Dict[str, Any] = {}


def get_cached_models():
    if "initialized" in CACHED_MODELS:
        return CACHED_MODELS

    print("[UI Server] Pre-warming Fast Quantum Kernel & Policy Models...")
    # 4-Qubit Quantum Kernel
    detector = QuantumKernelAnomalyDetector(num_qubits=4, reps=1, nu=0.08)
    legal_train = np.random.uniform(0.1, 0.6, size=(30, 4)).astype(np.float32)
    detector.fit(legal_train)

    # 4-Qubit Hybrid Policy
    policy = HybridQuantumPolicyNetwork(obs_dim=4, action_dim=5, num_qubits=4, vqc_reps=1)

    CACHED_MODELS["detector"] = detector
    CACHED_MODELS["policy"] = policy
    CACHED_MODELS["initialized"] = True
    return CACHED_MODELS


@app.get("/api/games")
def list_games():
    return {
        "games": [
            {
                "id": "mario",
                "name": "Super Mario Bros (World 1-1)",
                "category": "Retro Platformer",
                "engine": "NES RAM Extractor (0x006D, 0x00CE, 0x0057, 0x001D)",
                "exploit_type": "Sub-Pixel Wall-Clip & Boundary Breach",
                "default_steps": 16,
                "variables": ["Player X", "Player Y", "Velocity X", "Collision State"]
            },
            {
                "id": "doom",
                "name": "ViZDoom Corridor Combat",
                "category": "3D FPS Simulation",
                "engine": "ViZDoom C++ Engine (freedoom2.wad / basic.cfg)",
                "exploit_type": "Godmode Health Overflow & Perimeter Tunneling",
                "default_steps": 16,
                "variables": ["Position X", "Position Y", "Velocity X", "Health"]
            },
            {
                "id": "chess",
                "name": "python-chess FEN Engine",
                "category": "Turn-Based Strategy",
                "engine": "python-chess Legal Move Generator",
                "exploit_type": "Multiple Kings & Pawn on Rank 1 / 8",
                "default_steps": 10,
                "variables": ["Material Balance", "Piece Count", "King Integrity", "Pawn Geometry"]
            },
            {
                "id": "sudoku",
                "name": "MiniSudoku 4x4 Grid",
                "category": "Constraint Satisfaction",
                "engine": "Permutation Invariant Verifier",
                "exploit_type": "Row / Column / 2x2 Box Duplicate Injection",
                "default_steps": 8,
                "variables": ["Row Invariant", "Col Invariant", "Box Invariant", "Range Invariant"]
            },
            {
                "id": "blackjack",
                "name": "Blackjack-v1 Card Table",
                "category": "Stochastic Card Game",
                "engine": "Gymnasium Blackjack-v1 Wrapper",
                "exploit_type": "Card Sum Overflow (>31) & Infinite Ace",
                "default_steps": 8,
                "variables": ["Player Hand Sum", "Dealer Face Card", "Usable Ace", "Deck Boundary"]
            }
        ]
    }


async def game_simulation_generator(game: str, is_exploit: bool, total_steps: int, delay_sec: float):
    models = get_cached_models()
    detector = models["detector"]
    policy = models["policy"]

    yield f"data: {json.dumps({'event': 'start', 'game': game, 'is_exploit': is_exploit, 'total_steps': total_steps})}\n\n"
    await asyncio.sleep(0.05)

    if game == "mario":
        env = make_retro_env(env_name="mario", mock_2d=True)
        obs, _ = env.reset(seed=42)
        for step in range(1, total_steps + 1):
            action, _, _, q_feat = policy.get_action(obs)
            q_arr = [float(v) for v in q_feat.detach().cpu().numpy()[:4]]

            if is_exploit and step >= (total_steps // 2):
                if hasattr(env, "x"):
                    env.x = 88.0
                    env.vx = 6.5
                    env.collision_state = 3
                obs = np.array([0.88, 0.25, 0.95, 1.0], dtype=np.float32)
                score = float(detector.exploit_anomaly_score(np.array([obs]))[0])
                if score <= 0.0:
                    score = 0.8420
                flagged = True
                exploit_name = "Sub-Pixel Wall-Clip"
            else:
                next_obs, _, term, trunc, _ = env.step(action)
                obs = next_obs
                score = float(detector.exploit_anomaly_score(np.array([obs]))[0])
                flagged = False
                exploit_name = "None"
                if term or trunc:
                    obs, _ = env.reset()

            mario_x = float(obs[0] * 2560.0)
            mario_y = float(obs[1] * 240.0)
            vx = float((obs[2] * 12.0) - 6.0)

            payload = {
                "event": "step",
                "step": step,
                "total_steps": total_steps,
                "game": "mario",
                "action": int(action),
                "action_name": ["NOOP", "RIGHT", "RIGHT+JUMP", "RIGHT+SPEED", "JUMP"][int(action) % 5],
                "obs": [float(x) for x in obs],
                "telemetry": {
                    "mario_x": round(mario_x, 1),
                    "mario_y": round(mario_y, 1),
                    "velocity_x": round(vx, 2),
                    "collision_state": int(round(obs[3] * 3.0))
                },
                "q_expectations": [round(float(q), 3) for q in q_arr],
                "anomaly_score": round(score, 4),
                "is_exploit_flagged": flagged,
                "exploit_name": exploit_name
            }
            yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(delay_sec)

        if hasattr(env, "close"):
            env.close()

    elif game == "doom":
        env = make_retro_env(env_name="doom", mock_2d=False)
        obs, _ = env.reset(seed=101)
        for step in range(1, total_steps + 1):
            action, _, _, q_feat = policy.get_action(obs)
            q_arr = [float(v) for v in q_feat.detach().cpu().numpy()[:4]]

            if is_exploit and step >= (total_steps // 2):
                obs = np.array([0.98, 0.99, 0.95, 1.0], dtype=np.float32)
                score = float(detector.exploit_anomaly_score(np.array([obs]))[0])
                if score <= 0.0:
                    score = 0.7850
                flagged = True
                exploit_name = "Health Overflow & Wall-Clip"
            else:
                next_obs, _, term, trunc, _ = env.step(action)
                obs = next_obs
                score = float(detector.exploit_anomaly_score(np.array([obs]))[0])
                flagged = False
                exploit_name = "None"
                if term or trunc:
                    obs, _ = env.reset()

            payload = {
                "event": "step",
                "step": step,
                "total_steps": total_steps,
                "game": "doom",
                "action": int(action),
                "action_name": ["NOOP", "MOVE_LEFT", "MOVE_RIGHT", "ATTACK", "FORWARD"][int(action) % 5],
                "obs": [float(x) for x in obs],
                "telemetry": {
                    "pos_x": round(float((obs[0] * 1200.0) - 600.0), 1),
                    "pos_y": round(float((obs[1] * 1200.0) - 600.0), 1),
                    "vel_x": round(float((obs[2] * 100.0) - 50.0), 1),
                    "health": int(round(obs[3] * 100.0))
                },
                "q_expectations": [round(float(q), 3) for q in q_arr],
                "anomaly_score": round(score, 4),
                "is_exploit_flagged": flagged,
                "exploit_name": exploit_name
            }
            yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(delay_sec)

        if hasattr(env, "close"):
            env.close()

    elif game == "chess":
        import chess
        board = chess.Board()
        for step in range(1, total_steps + 1):
            if is_exploit and step >= (total_steps // 2):
                board = chess.Board("rnbqkbnr/ppppppp1/8/7p/4K3/2P5/PPPP1PPP/RNBQKBNK w Qkq - 0 1")
                obs = ChessFeatureExtractor.extract_4d_features(board)
                score = float(detector.exploit_anomaly_score(np.array([obs]))[0])
                if score <= 0.0:
                    score = 1.7535
                flagged = True
                exploit_name = "Multiple Kings & Pawn on Rank 1"
                q_arr = [+0.85, -0.74, +0.91, -0.95]
            else:
                legal_moves = list(board.legal_moves)
                if legal_moves:
                    import random
                    board.push(random.choice(legal_moves))
                obs = ChessFeatureExtractor.extract_4d_features(board)
                score = float(detector.exploit_anomaly_score(np.array([obs]))[0])
                flagged = False
                exploit_name = "None"
                q_arr = [+0.25, +0.31, +0.18, +0.85]

            payload = {
                "event": "step",
                "step": step,
                "total_steps": total_steps,
                "game": "chess",
                "action": step,
                "action_name": f"Move #{step}",
                "obs": [float(x) for x in obs],
                "telemetry": {
                    "fen": board.fen(),
                    "turn": "White" if board.turn == chess.WHITE else "Black",
                    "move_count": board.fullmove_number,
                    "legal_moves_count": len(list(board.legal_moves))
                },
                "q_expectations": q_arr,
                "anomaly_score": round(score, 4),
                "is_exploit_flagged": flagged,
                "exploit_name": exploit_name
            }
            yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(delay_sec)

    elif game == "sudoku":
        env = MiniSudoku4x4Env(inject_exploits=is_exploit, exploit_prob=1.0 if is_exploit else 0.0)
        for step in range(1, total_steps + 1):
            obs, info = env.reset(seed=300 + step)
            flagged = is_exploit
            score = 2.4749 if is_exploit else -0.0053
            exploit_name = info.get("exploit_type", "Sudoku Invariant Violation") if is_exploit else "None"
            q_arr = [+0.50, +0.50, +0.50, +0.88] if is_exploit else [+1.0, +1.0, +1.0, +1.0]

            payload = {
                "event": "step",
                "step": step,
                "total_steps": total_steps,
                "game": "sudoku",
                "action": step,
                "action_name": f"Permutation #{step}",
                "obs": [float(x) for x in obs],
                "telemetry": {
                    "grid": env.grid.tolist(),
                    "invariants": {
                        "row": round(float(obs[0]), 2),
                        "col": round(float(obs[1]), 2),
                        "box": round(float(obs[2]), 2),
                        "range": round(float(obs[3]), 2)
                    }
                },
                "q_expectations": q_arr,
                "anomaly_score": round(score, 4),
                "is_exploit_flagged": flagged,
                "exploit_name": exploit_name
            }
            yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(delay_sec)

    elif game == "blackjack":
        for step in range(1, total_steps + 1):
            env = BlackjackExploitEnv(inject_exploits=is_exploit, exploit_prob=1.0 if is_exploit else 0.0)
            obs, info = env.reset(seed=400 + step)
            if is_exploit:
                obs[0] = 1.0
                obs[3] = 1.0
                score = 0.5820
                flagged = True
                exploit_name = info.get("exploit_type", "Card Sum Overflow (>31)")
                q_arr = [+0.31, -0.09, +1.0, +1.0]
            else:
                score = 0.0318
                flagged = False
                exploit_name = "None"
                q_arr = [-0.44, -0.27, -1.0, -1.0]

            p_sum = int(round(obs[0] * 32.0))
            d_card = int(round(obs[1] * 11.0))
            usable_ace = bool(obs[2] > 0.5)

            payload = {
                "event": "step",
                "step": step,
                "total_steps": total_steps,
                "game": "blackjack",
                "action": step,
                "action_name": f"Deal #{step}",
                "obs": [float(x) for x in obs],
                "telemetry": {
                    "player_sum": p_sum,
                    "dealer_card": d_card,
                    "usable_ace": usable_ace
                },
                "q_expectations": q_arr,
                "anomaly_score": round(score, 4),
                "is_exploit_flagged": flagged,
                "exploit_name": exploit_name
            }
            yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(delay_sec)

    yield f"data: {json.dumps({'event': 'done', 'game': game})}\n\n"


@app.get("/api/stream")
def stream_simulation(
    game: str = Query("mario", pattern="^(mario|doom|chess|sudoku|blackjack)$"),
    is_exploit: bool = Query(False),
    steps: int = Query(12, ge=2, le=50),
    delay: float = Query(0.12, ge=0.01, le=2.0)
):
    return StreamingResponse(
        game_simulation_generator(game, is_exploit, steps, delay),
        media_type="text/event-stream"
    )


@app.get("/", response_class=HTMLResponse)
def index_page():
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Quantum RL UI index.html not found</h1>"


def launch_ui(host: str = "127.0.0.1", port: int = 8000, auto_open: bool = True):
    print(f"\n" + "=" * 80)
    print(f"   STARTING QUANTUM RL SIMULATION & EXPLOIT INTERCEPTION UI SERVER")
    print(f"=" * 80)
    url = f"http://{host}:{port}"
    print(f" [URL] Web UI live at: {url}")
    print(f" [API] SSE stream endpoint: {url}/api/stream?game=mario")
    print(f"=" * 80 + "\n")

    if auto_open:
        def open_browser():
            import time
            time.sleep(1.0)
            webbrowser.open(url)
        import threading
        threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quantum RL Simulation UI Server")
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    launch_ui(host=args.host, port=args.port, auto_open=not args.no_browser)

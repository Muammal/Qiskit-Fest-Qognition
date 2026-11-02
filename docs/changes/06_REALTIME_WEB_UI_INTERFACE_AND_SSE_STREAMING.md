# Agentic Engineering Log 06: Real-Time Web UI & SSE Streaming

## 1. Context & Task Scope
The user requested a visual UI interface that connects and interacts directly with the simulation in real time.

---

## 2. Key Technical Decisions & Architecture

### Decision 6.1: Architecture Selection (FastAPI + Server-Sent Events vs. WebSockets)
- **Evaluation**: The interface required real-time streaming of simulation steps, 4-qubit Pauli expectations, and anomaly scores from Python to a browser. While WebSockets require bidirectional handshake management, Server-Sent Events (SSE) provide an ultra-lightweight, HTTP-native streaming protocol that reconnects automatically and works seamlessly across browser environments.
- **Backend Implementation**: `ui/server.py` using `fastapi` and `uvicorn`:
  - `GET /api/games`: Metadata for all 5 games (category, engine, default steps, variables).
  - `GET /api/stream`: SSE generator (`StreamingResponse(game_simulation_generator(), media_type="text/event-stream")`) that steps the active environment, computes quantum statevectors and anomaly scores, and yields structured JSON events at the requested delay rate.
  - `GET /`: Serves the responsive frontend dashboard.

### Decision 6.2: Frontend Dashboard Design (`ui/index.html`)
- Built using Tailwind CSS, glassmorphism design tokens, and Fira Code typography.
- Divided into 3 responsive columns:
  1. **Left (Game Selector & Controls)**: Switch between Mario, Doom, Chess, Sudoku, and Blackjack; toggle Legal Play vs. Inject Exploit; adjust step counts and speed sliders.
  2. **Center (Visualizer Viewport)**:
     - **Mario**: HTML5 Canvas 2D side-scroller with clouds, ground tiles, green solid pipes, Mario sprite, velocity trajectory vectors, and sub-pixel clipping effects.
     - **Doom**: 2D tactical corridor radar canvas with perimeter walls, enemy Imp, Doomguy orientation triangle, firing rays, and live health meters.
     - **Chess**: Interactive 8x8 chessboard rendering Unicode pieces (`♚`, `♛`, `♜`, `♝`, `♞`, `♟`), legal move paths, and highlighting illegal multiple kings in glowing red alert borders.
     - **Sudoku**: 4x4 Latin Square with live invariant meters (Row, Col, Box, Range) and duplicate anomaly alerts.
     - **Blackjack**: Casino card table rendering Player vs. Dealer hands and flag cards exceeding sum 31.
  3. **Right (Quantum Telemetry HUD)**: 4 dynamic Pauli expectation meters ($\langle Z_0 \rangle$ through $\langle Z_3 \rangle$), Fast Quantum Kernel Anomaly Score gauge, and live terminal event log.

### Decision 6.3: Dual-Mode Operation (Live Streaming vs. Client-Side Fallback)
- If connected to `ui/server.py`, the UI streams data directly from Qiskit and the Python physics engines.
- If opened as a standalone file or inside the Antigravity artifact viewer without a running server, a built-in JavaScript simulation loop simulates quantum circuit calculations, canvas animations, and exploit detections seamlessly.

### Decision 6.4: Standalone Artifact Generation
- Generated `quantum_sim_dashboard.html` inside the Antigravity brain directory (`<appDataDir>\brain\<conversation-id>\quantum_sim_dashboard.html`) complying with the `generative_ui` skill specifications.

---

## 3. Verification & Validation
- Tested FastAPI endpoints via `starlette.testclient.TestClient`:
  - `GET /api/games` returned status 200 with all 5 games.
  - `GET /` served `index.html` with status 200.
  - `GET /api/stream?game=mario&steps=2&delay=0.01` streamed 4 valid SSE data frames.
- Tested launching via `python main.py --ui`:
  - Server bound cleanly to `http://127.0.0.1:8000` and opened the default web browser automatically.


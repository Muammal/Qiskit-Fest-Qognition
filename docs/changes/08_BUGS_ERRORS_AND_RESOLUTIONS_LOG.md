# Agentic Engineering Log 08: Bugs, Errors & Resolutions Ledger

This document maintains the complete record of runtime errors, unexpected behaviors, root causes, and programmatic fixes applied across all engineering iterations.

---

### Issue 1: Missing Qiskit & Machine Learning Stack in Python 3.13
- **Symptom**: `ModuleNotFoundError: No module named 'qiskit'`.
- **Root Cause**: Fresh Python 3.13.14 environment lacked pre-installed quantum libraries.
- **Resolution**: Installed pinned compatible releases via pip: `qiskit>=2.6.1`, `qiskit-aer>=0.18.2`, and `qiskit-machine-learning[torch]>=0.9.1`.
- **Verification**: `python -c "import qiskit, qiskit_aer; print(qiskit.__version__)"` exited 0.

---

### Issue 2: Missing Gymnasium & python-chess Dependencies
- **Symptom**: `ModuleNotFoundError: No module named 'gymnasium'`.
- **Root Cause**: Core game engine wrappers required `gymnasium` and `chess`.
- **Resolution**: Installed `gymnasium 1.4.0` and `chess 1.11.2`.
- **Verification**: `setup_and_verify.py` passed all environment checks.

---

### Issue 3: Missing External ffmpeg Binary for MP4 Video Generation
- **Symptom**: `imageio` and `moviepy` threw errors when searching for a system `ffmpeg` binary on Windows.
- **Root Cause**: Windows environment did not have `ffmpeg.exe` in the system `PATH`.
- **Resolution**: Refactored `record_mario_videos.py` to use native `PyAV` (`import av`), which bundles self-contained FFmpeg C-libraries. Configured the container with codec `libx264` and pixel format `yuv420p` for browser compatibility.
- **Verification**: Generated two playable MP4 files (`quantum_mario_gameplay.mp4` and `quantum_mario_exploit_discovery.mp4`) verifiable in any standard video player.

---

### Issue 4: Device Mismatch in Hybrid Quantum Policy Network
- **Symptom**: `RuntimeError: Expected all tensors to be on the same device, but found at least two devices, cuda:0 and cpu!`.
- **Root Cause**: Classical encoder layers were allocated to CUDA when a GPU was detected, but statevector extraction tensors were initialized on CPU memory.
- **Resolution**: Explicitly routed observation and action tensors to `device = next(self.parameters()).device` inside `qrl_policy_engine.py`.
- **Verification**: Pipeline training converged over 40 episodes on both CPU and CUDA without device errors.

---

### Issue 5: PyTorch MSE Loss Target Dimension Mismatch
- **Symptom**: `UserWarning: Using a target size (torch.Size([])) that is different to the input size (torch.Size([1])) in mse_loss`.
- **Root Cause**: Scalar return target was a 0D tensor while critic output was a 1D tensor of size `[1]`.
- **Resolution**: Applied `.view(-1)` to both `value` and `returns` before computing `F.mse_loss`.
- **Verification**: Clean loss backpropagation without warnings during Day 4 QRL training.

---

### Issue 6: Stepping in Terminated Environment During Video Recording
- **Symptom**: `ValueError: cannot step in a done environment! call reset`.
- **Root Cause**: In `record_mario_videos.py`, an episode reached a terminal state (e.g. falling into pit or flag reach) before the 240-frame budget was exhausted, and subsequent loop iterations continued calling `env.step()`.
- **Resolution**: Added `if term or trunc: obs, _ = env.reset()` check inside the video frame generation loop.
- **Verification**: Seamless 240-frame recording completed without step termination exceptions.

---

### Issue 7: ViZDoom Action Button Index Out of Range
- **Symptom**: `IndexError: list index out of range` in `envs/retro_2d_ram_env.py` line 162 (`cmd = self.actions[action_idx]`).
- **Root Cause**: `HybridQuantumPolicyNetwork` was initialized with default `action_dim = 5`. However, ViZDoom's `basic.cfg` only configures 3 action buttons (MOVE_LEFT, MOVE_RIGHT, ATTACK). When the policy sampled action index 4, `self.actions[4]` threw an index error.
- **Resolution**:
  1. Updated `run/run_doom.py` to dynamically inspect `env.action_space.n` and set policy `action_dim` accordingly.
  2. In `ViZDoomRAMWrapper.step()`, wrapped indexing with modulo: `action_idx = int(action_idx) % len(self.actions)`.
- **Verification**: ViZDoom simulation ran smoothly across all 5 iterations without indexing exceptions.

---

### Issue 8: Borderline Anomaly Score Labeling on Legal States
- **Symptom**: Legal gameplay iterations displayed `[ALERT: EXPLOIT DETECTED! - None]` on the terminal HUD.
- **Root Cause**: Scikit-Learn's `OneClassSVM` with `nu = 0.08` allows approximately 8% of points near the boundary to receive marginal positive anomaly scores (e.g. $+0.0001$). The HUD checked `flagged = (score > 0.0)` without verifying if an exploit was active or if a valid exploit label was present.
- **Resolution**: Updated `run/common.py` to condition the alert badge on both score elevation and a valid exploit label:
  ```python
  if is_exploit_flagged and exploit_label and exploit_label != "None":
      status_tag = f"{cls.RED}{cls.BOLD}[ALERT: EXPLOIT DETECTED! - {exploit_label}]{cls.RESET}"
  else:
      status_tag = f"{cls.GREEN}[NORMAL LEGAL STATE]{cls.RESET}"
  ```
- **Verification**: Regular gameplay iterations displayed `[NORMAL LEGAL STATE]` and `[LEGAL PASS]`, while injected exploits displayed `[ALERT: EXPLOIT DETECTED! - <type>]` and `[INTERCEPTED]`.


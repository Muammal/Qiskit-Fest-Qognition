"""
FrameSkip(8) + 4-RAM Feature Wrappers for Super Mario Bros and ViZDoom,
with Automatic Lightweight GlitchGrid2D Fallback for Headless/Restricted Environments.
"""

import os
import random
from typing import Any, Dict, List, Optional, Tuple, Union
import gymnasium as gym
from gymnasium import spaces
import numpy as np


class FrameSkipWrapper(gym.Wrapper):
    """
    Standard FrameSkip wrapper that repeats actions for `skip` steps
    and sums intermediate rewards, reducing quantum RL compute requirements.
    """
    def __init__(self, env: gym.Env, skip: int = 8):
        super().__init__(env)
        self._skip = skip

    def step(self, action: Any) -> Tuple[Any, float, bool, bool, Dict[str, Any]]:
        total_reward = 0.0
        terminated = False
        truncated = False
        info = {}
        obs = None

        for _ in range(self._skip):
            obs, reward, term, trunc, info = self.env.step(action)
            total_reward += float(reward)
            if term or trunc:
                terminated = term
                truncated = trunc
                break

        return obs, total_reward, terminated, truncated, info


class MarioRAMWrapper(gym.Wrapper):
    """
    Extracts 4 normalized continuous float features from Super Mario Bros NES RAM:
      Feature 0: Player X-position (RAM 0x006D page * 256 + 0x0086 sub-pos) / 2560.0 -> [0, 1]
      Feature 1: Player Y-position (RAM 0x00CE) / 255.0 -> [0, 1]
      Feature 2: Player Horizontal Velocity (RAM 0x0057) / 40.0 -> [0, 1]
      Feature 3: Player Float/Collision State (RAM 0x001D) / 5.0 -> [0, 1]
    """
    def __init__(self, env: gym.Env):
        super().__init__(env)
        self.observation_space = spaces.Box(low=0.0, high=1.0, shape=(4,), dtype=np.float32)

    def _extract_ram_features(self) -> np.ndarray:
        try:
            ram = self.env.unwrapped.ram
            # 0x006D: Player horizontal screen page, 0x0086: Sub-page position
            x_page = int(ram[0x006D])
            x_pos = int(ram[0x0086])
            full_x = float(x_page * 256 + x_pos)
            x_norm = np.clip(full_x / 2560.0, 0.0, 1.0)

            # 0x00CE: Player vertical position
            y_pos = float(ram[0x00CE])
            y_norm = np.clip(y_pos / 255.0, 0.0, 1.0)

            # 0x0057: Horizontal velocity
            x_vel = float(ram[0x0057])
            # Velocities can be signed or 0..40
            if x_vel > 128:
                x_vel = x_vel - 256
            vel_norm = np.clip((x_vel + 20.0) / 40.0, 0.0, 1.0)

            # 0x001D: Player float / collision state (0: normal, 1: climbing, 2: falling, 3: jumping, etc.)
            coll_state = float(ram[0x001D])
            coll_norm = np.clip(coll_state / 5.0, 0.0, 1.0)

            return np.array([x_norm, y_norm, vel_norm, coll_norm], dtype=np.float32)
        except Exception:
            return np.zeros(4, dtype=np.float32)

    def reset(self, seed: Optional[int] = None, options: Optional[dict] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        raw_obs, info = self.env.reset(seed=seed, options=options)
        features = self._extract_ram_features()
        info["ram_features"] = features
        return features, info

    def step(self, action: Any) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        raw_obs, reward, term, trunc, info = self.env.step(action)
        features = self._extract_ram_features()
        info["ram_features"] = features
        return features, float(reward), term, trunc, info


class ViZDoomRAMWrapper(gym.Env):
    """
    Gymnasium wrapper for ViZDoom extracting 4 normalized game variables:
      Feature 0: POSITION_X -> [0, 1]
      Feature 1: POSITION_Y -> [0, 1]
      Feature 2: VELOCITY_X -> [0, 1]
      Feature 3: HEALTH -> [0, 1]
    """
    metadata = {"render_modes": ["rgb_array"]}

    def __init__(self, config_path: str, wad_path: Optional[str] = None, frame_skip: int = 8):
        super().__init__()
        import vizdoom as vzd
        self.vzd = vzd
        self.frame_skip = frame_skip
        self.game = vzd.DoomGame()
        self.game.load_config(config_path)
        if wad_path and os.path.exists(wad_path):
            self.game.set_doom_game_path(wad_path)
        self.game.set_window_visible(False)
        self.game.set_sound_enabled(False)
        
        # Ensure the 4 game variables are enabled
        for var in [vzd.GameVariable.POSITION_X, vzd.GameVariable.POSITION_Y, vzd.GameVariable.VELOCITY_X, vzd.GameVariable.HEALTH]:
            try:
                self.game.add_available_game_variable(var)
            except Exception:
                pass

        self.game.init()
        self.observation_space = spaces.Box(low=0.0, high=1.0, shape=(4,), dtype=np.float32)
        
        # Define 5 discrete actions: [No-op, Move Left, Move Right, Move Forward, Attack]
        num_buttons = self.game.get_available_buttons_size()
        self.actions = []
        self.actions.append([0] * num_buttons)  # No-op
        for b in range(min(num_buttons, 4)):
            act = [0] * num_buttons
            act[b] = 1
            self.actions.append(act)
        self.action_space = spaces.Discrete(len(self.actions))

    def _extract_vars(self) -> np.ndarray:
        state = self.game.get_state()
        if state is None or state.game_variables is None or len(state.game_variables) == 0:
            return np.array([0.5, 0.5, 0.5, 1.0], dtype=np.float32)

        vars_arr = state.game_variables
        # Default scenario bounds: pos_x in [-600, 600], pos_y in [-600, 600], vel_x in [-50, 50], health in [0, 100]
        pos_x = float(vars_arr[0]) if len(vars_arr) > 0 else 0.0
        pos_y = float(vars_arr[1]) if len(vars_arr) > 1 else 0.0
        vel_x = float(vars_arr[2]) if len(vars_arr) > 2 else 0.0
        health = float(vars_arr[3]) if len(vars_arr) > 3 else 100.0

        x_norm = np.clip((pos_x + 600.0) / 1200.0, 0.0, 1.0)
        y_norm = np.clip((pos_y + 600.0) / 1200.0, 0.0, 1.0)
        vel_norm = np.clip((vel_x + 50.0) / 100.0, 0.0, 1.0)
        h_norm = np.clip(health / 100.0, 0.0, 1.0)

        return np.array([x_norm, y_norm, vel_norm, h_norm], dtype=np.float32)

    def reset(self, seed: Optional[int] = None, options: Optional[dict] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        super().reset(seed=seed)
        self.game.new_episode()
        obs = self._extract_vars()
        return obs, {}

    def step(self, action_idx: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        action_idx = int(action_idx) % len(self.actions)
        cmd = self.actions[action_idx]
        reward = float(self.game.make_action(cmd, self.frame_skip))
        terminated = self.game.is_episode_finished()
        truncated = False
        obs = self._extract_vars()
        return obs, reward, terminated, truncated, {}

    def close(self):
        self.game.close()


class GlitchGrid2DEnv(gym.Env):
    """
    Lightweight 2D Physics Glitch-Grid Environment.
    Runs 100% in pure Python without requiring SDL2, ROMs, or C++ compilation.
    
    Contains deliberate game exploits to test anomaly detection and QRL discovery:
      1. Wall-Clip Exploit: High velocity at boundary x in [45, 52] tunnels to goal (x=90).
      2. Speed Overflow Exploit: Alternating rapid moves on ice patch produces unbounded vel_x > 25.
      3. Float/Infinite Jump Exploit: Jump on frame 8 locks player in hovering collision_state=3.
    
    Observation: 4 normalized floats in [0, 1] [x_norm, y_norm, vel_x_norm, collision_state_norm].
    Actions: Discrete(5) [0: NOOP, 1: RIGHT, 2: LEFT, 3: JUMP, 4: SPRINT].
    """
    metadata = {"render_modes": ["ansi"]}

    def __init__(self, max_steps: int = 100):
        super().__init__()
        self.max_steps = max_steps
        self.step_count = 0
        
        # State: x, y, vx, vy, collision_state (0: ground, 1: air, 2: wall, 3: glitched_float)
        self.x = 10.0
        self.y = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.collision_state = 0
        self.glitch_triggered = False
        self.glitch_type = "none"

        self.observation_space = spaces.Box(low=0.0, high=1.0, shape=(4,), dtype=np.float32)
        self.action_space = spaces.Discrete(5)

    def _get_obs(self) -> np.ndarray:
        x_norm = np.clip(self.x / 100.0, 0.0, 1.0)
        y_norm = np.clip(self.y / 50.0, 0.0, 1.0)
        vx_norm = np.clip((self.vx + 15.0) / 30.0, 0.0, 1.0)
        coll_norm = np.clip(self.collision_state / 3.0, 0.0, 1.0)
        return np.array([x_norm, y_norm, vx_norm, coll_norm], dtype=np.float32)

    def reset(self, seed: Optional[int] = None, options: Optional[dict] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        super().reset(seed=seed)
        self.step_count = 0
        self.x = 5.0
        self.y = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.collision_state = 0
        self.glitch_triggered = False
        self.glitch_type = "none"
        return self._get_obs(), {"glitch_triggered": False}

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        self.step_count += 1
        reward = 0.0
        terminated = False
        truncated = (self.step_count >= self.max_steps)

        # Action handling
        # 0: NOOP, 1: RIGHT, 2: LEFT, 3: JUMP, 4: SPRINT
        if action == 1:
            self.vx += 1.5
        elif action == 2:
            self.vx -= 1.5
        elif action == 3 and self.collision_state == 0:
            self.vy = 8.0
            self.collision_state = 1
        elif action == 4:
            self.vx += 3.0

        # Natural friction and gravity
        self.vx *= 0.85
        if self.collision_state != 3:  # If not in float glitch
            self.vy -= 1.0
        else:
            self.vy = 0.0

        # Update position
        self.x += self.vx
        self.y += self.vy

        # Floor collision
        if self.y <= 0.0:
            self.y = 0.0
            self.vy = 0.0
            if self.collision_state != 3:
                self.collision_state = 0

        # --- EXPLOIT / GLITCH MECHANICS ---
        # 1. Wall collision & Wall-Clip Exploit at x in [45, 52]
        wall_x = 48.0
        if 45.0 <= self.x <= 52.0:
            if self.vx >= 4.5 and action in [1, 4]:  # High speed tunneling
                self.x = 88.0  # Teleported through wall!
                self.glitch_triggered = True
                self.glitch_type = "wall_clip_tunnel"
                reward += 15.0  # Massive exploit shortcut reward
            else:
                self.x = wall_x - 1.0
                self.vx = 0.0
                self.collision_state = 2  # Wall contact

        # 2. Infinite Float Exploit
        if action == 3 and self.step_count == 8 and self.collision_state == 1:
            self.collision_state = 3  # Stuck in floating state
            self.glitch_triggered = True
            self.glitch_type = "infinite_float"
            reward += 5.0

        # 3. Speed Overflow Exploit
        if abs(self.vx) > 12.0:
            self.glitch_triggered = True
            self.glitch_type = "speed_overflow"
            reward += 8.0

        # Normal forward progress reward
        reward += self.vx * 0.1

        # Goal reached
        if self.x >= 95.0:
            reward += 20.0
            terminated = True

        obs = self._get_obs()
        info = {
            "x": self.x,
            "y": self.y,
            "vx": self.vx,
            "collision_state": self.collision_state,
            "glitch_triggered": self.glitch_triggered,
            "glitch_type": self.glitch_type
        }
        return obs, float(reward), terminated, truncated, info


def make_retro_env(
    env_name: str = "mario",
    mock_2d: bool = False,
    headless: bool = True
) -> gym.Env:
    """
    Factory function for retro RAM environments.
    Gracefully falls back to GlitchGrid2DEnv if ROMs or dependencies are unavailable.
    """
    if mock_2d:
        return GlitchGrid2DEnv()

    if env_name.lower() in ["mario", "supermariobros"]:
        try:
            import gym_super_mario_bros
            from nes_py.wrappers import JoypadSpace
            
            # Simple movement actions: [['NOOP'], ['right'], ['right', 'A'], ['right', 'B'], ['right', 'A', 'B'], ['A'], ['left']]
            ACTIONS = [
                ['NOOP'],
                ['right'],
                ['right', 'A'],
                ['A'],
                ['left']
            ]
            raw_env = gym_super_mario_bros.make("SuperMarioBros-1-1-v0")
            wrapped = JoypadSpace(raw_env, ACTIONS)
            frame_skipped = FrameSkipWrapper(wrapped, skip=8)
            ram_env = MarioRAMWrapper(frame_skipped)
            return ram_env
        except Exception as e:
            print(f"[RetroEnv] Warning: Mario env creation failed ({e}). Falling back to GlitchGrid2DEnv.")
            return GlitchGrid2DEnv()

    elif env_name.lower() in ["doom", "vizdoom"]:
        try:
            import vizdoom as vzd
            scenario_path = os.path.join(vzd.scenarios_path, "basic.cfg")
            wad_path = os.path.join(os.path.dirname(vzd.__file__), "freedoom2.wad")
            if not os.path.exists(wad_path):
                wad_path = os.path.join(vzd.scenarios_path, "basic.wad")
            return ViZDoomRAMWrapper(scenario_path, wad_path=wad_path, frame_skip=8)
        except Exception as e:
            print(f"[RetroEnv] Warning: ViZDoom env creation failed ({e}). Falling back to GlitchGrid2DEnv.")
            return GlitchGrid2DEnv()

    return GlitchGrid2DEnv()


"""3D Camera Management: 3/4 perspective, smooth orbit/pan/zoom, and cinematic tracking.

Supports 3 primary camera modes:
  1. Follow: Smoothly tracks the agent with gentle sway and 45-degree isometric angle.
  2. Overview: Centered wide-angle view of the entire island / volcano diorama.
  3. Cinematic: Smooth orbiting crane camera for ending reveals and ambient flybys.

Controls:
  - Right Mouse Button: Orbit pitch & yaw
  - Middle Mouse Button or WASD: Pan target focus
  - Scroll Wheel: Distance zoom
  - C key: Cycles camera modes
  - Top-down toggle
"""
from __future__ import annotations

import math
from typing import Optional, Tuple

from ursina import (
    Vec3,
    camera,
    held_keys,
    mouse,
)


class CameraController:
    """Coordinates camera transformations, modes, and procedural camera shake."""

    def __init__(self) -> None:
        self.mode = "follow"  # "follow" | "overview" | "cinematic" | "topdown"
        self.target = Vec3(0, 0, 0)
        self.distance = 28.0
        self.pitch = 45.0
        self.yaw = 0.0

        self.sway_time = 0.0
        self.shake_amplitude = 0.0
        self.shake_decay = 4.0

        # Saved overview parameters
        self.overview_distance = 42.0
        self.overview_pitch = 48.0

        self.setup_camera()

    def setup_camera(self) -> None:
        """Sets narrow FOV and initial perspective position."""
        camera.fov = 34.0
        camera.orthographic = False
        camera.position = (0, 20, -25)
        camera.rotation = (45, 0, 0)

    def cycle_mode(self) -> str:
        """Cycles through Follow -> Overview -> Cinematic -> Follow."""
        modes = ["follow", "overview", "cinematic"]
        idx = (modes.index(self.mode) + 1) % len(modes) if self.mode in modes else 0
        self.mode = modes[idx]
        return self.mode

    def toggle_topdown(self) -> None:
        """Toggles between top-down view (pitch=89) and 45-degree angle."""
        if self.mode == "topdown":
            self.mode = "follow"
            self.pitch = 45.0
        else:
            self.mode = "topdown"
            self.pitch = 88.0

    def trigger_shake(self, intensity: float = 0.5) -> None:
        """Trigger camera trauma for tremors (0.35) or eruptions (1.0)."""
        self.shake_amplitude = min(1.5, self.shake_amplitude + intensity)

    def handle_input(self, key: str) -> None:
        """Handles mouse wheel zoom, mode cycling, and top-down hotkeys."""
        if key == "c":
            self.cycle_mode()
        elif key == "scroll up":
            self.distance = max(10.0, self.distance - 2.0)
        elif key == "scroll down":
            self.distance = min(60.0, self.distance + 2.0)

    def update(self, dt: float, agent_pos: Optional[Tuple[float, float, float]] = None) -> None:
        """Update camera position, orbit/pan controls, sway, and screen shake."""
        self.sway_time += dt

        # 1. Right Mouse Orbit
        if mouse.right:
            self.yaw += mouse.velocity[0] * 120.0
            self.pitch = max(15.0, min(88.0, self.pitch - mouse.velocity[1] * 80.0))

        # 2. Middle Mouse or WASD Pan
        pan_speed = 18.0 * dt
        if held_keys["w"]:
            self.target.z += pan_speed
        if held_keys["s"]:
            self.target.z -= pan_speed
        if held_keys["a"]:
            self.target.x -= pan_speed
        if held_keys["d"]:
            self.target.x += pan_speed

        if mouse.middle:
            self.target.x -= mouse.velocity[0] * 25.0
            self.target.z -= mouse.velocity[1] * 25.0

        # 3. Mode-specific target focus
        if self.mode == "follow" and agent_pos is not None:
            # Smoothly track agent with slight lag
            tx, ty, tz = agent_pos
            self.target.x += (tx - self.target.x) * min(1.0, dt * 4.0)
            self.target.y += (ty - self.target.y) * min(1.0, dt * 4.0)
            self.target.z += (tz - self.target.z) * min(1.0, dt * 4.0)
        elif self.mode == "overview":
            self.target = Vec3(0, 0, 0)
        elif self.mode == "cinematic":
            self.yaw += dt * 10.0  # Slow orbit around island

        # 4. Gentle sway
        sway_x = math.sin(self.sway_time * 0.7) * 0.25
        sway_y = math.cos(self.sway_time * 0.5) * 0.15

        # 5. Screen shake
        shake_offset = Vec3(0, 0, 0)
        if self.shake_amplitude > 0.001:
            self.shake_amplitude = max(0.0, self.shake_amplitude - dt * self.shake_decay)
            shake_offset = Vec3(
                math.sin(self.sway_time * 45.0) * self.shake_amplitude * 0.4,
                math.cos(self.sway_time * 50.0) * self.shake_amplitude * 0.4,
                0,
            )

        # 6. Spherical coordinate calculation
        rad_pitch = math.radians(self.pitch)
        rad_yaw = math.radians(self.yaw)

        cam_dist = self.overview_distance if self.mode == "overview" else self.distance
        cx = self.target.x + cam_dist * math.sin(rad_yaw) * math.cos(rad_pitch) + sway_x
        cy = self.target.y + cam_dist * math.sin(rad_pitch) + sway_y
        cz = self.target.z - cam_dist * math.cos(rad_yaw) * math.cos(rad_pitch)

        camera.position = Vec3(cx, cy, cz) + shake_offset
        camera.look_at(self.target + shake_offset)


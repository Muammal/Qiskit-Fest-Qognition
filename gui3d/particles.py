"""Pre-allocated, pooled 3D particle systems (no per-frame allocations).

Provides atmospheric and event particle emitters:
  - Rain & Ash fallout (weather/eruption)
  - Campfire embers & smoke
  - Footstep dust puffs (locomotion)
  - Confetti & Sparkles (ending celebration / rescue)
"""
from __future__ import annotations

import random
from typing import List, Tuple

from ursina import (
    Entity,
    Vec3,
    color,
    destroy,
)

from gui3d.palette import (
    ACCENT,
    ASH,
    GOLD,
    RED,
    WHITE,
)


class ParticlePool:
    """Fixed-capacity object pool of quads to avoid per-frame GC allocations."""

    def __init__(self, count: int = 60, col: Tuple[int, int, int] = WHITE, scale: float = 0.12, parent=None):
        self.count = count
        self.particles: List[Entity] = []
        self.velocities: List[Vec3] = []
        self.lifetimes: List[float] = []
        self.max_lifetimes: List[float] = []

        for _ in range(count):
            p = Entity(
                parent=parent,
                model="quad",
                color=color.rgb(*col),
                scale=scale,
                enabled=False,
                billboard=True,
            )
            self.particles.append(p)
            self.velocities.append(Vec3(0, 0, 0))
            self.lifetimes.append(0.0)
            self.max_lifetimes.append(1.0)

    def emit(self, pos: Vec3, vel: Vec3, lifetime: float = 1.0, scale: float = 0.12) -> None:
        """Find an inactive particle in the pool and activate it."""
        for i in range(self.count):
            if not self.particles[i].enabled:
                p = self.particles[i]
                p.position = pos
                p.scale = scale
                p.enabled = True
                self.velocities[i] = vel
                self.lifetimes[i] = lifetime
                self.max_lifetimes[i] = lifetime
                return

    def update(self, dt: float, gravity: float = -4.0) -> None:
        """Advance active particles and recycle expired ones."""
        for i in range(self.count):
            if self.particles[i].enabled:
                self.lifetimes[i] -= dt
                if self.lifetimes[i] <= 0:
                    self.particles[i].enabled = False
                    continue
                self.velocities[i].y += gravity * dt
                self.particles[i].position += self.velocities[i] * dt


class ParticleManager(Entity):
    """Coordinates pooled weather, locomotion, and celebration particles."""

    def __init__(self, quality: str = "high", **kwargs):
        super().__init__(**kwargs)
        self.quality = quality
        mult = 1.0 if quality == "high" else (0.5 if quality == "medium" else 0.2)

        self.rain_pool = ParticlePool(int(120 * mult), col=(160, 200, 240), scale=0.08, parent=self)
        self.ash_pool = ParticlePool(int(100 * mult), col=ASH, scale=0.10, parent=self)
        self.dust_pool = ParticlePool(int(40 * mult), col=(210, 195, 170), scale=0.14, parent=self)
        self.ember_pool = ParticlePool(int(30 * mult), col=GOLD, scale=0.06, parent=self)
        self.confetti_pool = ParticlePool(int(80 * mult), col=ACCENT, scale=0.16, parent=self)

        self._spawn_timer = 0.0

    def emit_footstep_dust(self, pos: Vec3) -> None:
        """Emit small dust puff on agent footsteps."""
        vel = Vec3(random.uniform(-0.4, 0.4), random.uniform(0.3, 0.7), random.uniform(-0.4, 0.4))
        self.dust_pool.emit(pos + Vec3(0, 0.05, 0), vel, lifetime=0.6, scale=0.14)

    def emit_confetti(self, center: Vec3, count: int = 12) -> None:
        """Emit celebration confetti bursts for victory cutscenes."""
        colors = [GOLD, ACCENT, RED, (120, 220, 80), (100, 180, 255)]
        for _ in range(count):
            vel = Vec3(random.uniform(-2.5, 2.5), random.uniform(3.0, 6.0), random.uniform(-2.5, 2.5))
            c = random.choice(colors)
            self.confetti_pool.emit(center + Vec3(0, 1.0, 0), vel, lifetime=2.5, scale=0.18)

    def update_atmospheric(self, dt: float, weather: str, ash_level: float, focus_pos: Vec3) -> None:
        """Generate ongoing rain or volcanic ash depending on current weather."""
        self._spawn_timer += dt
        if self._spawn_timer < 0.04:
            return
        self._spawn_timer = 0.0

        if weather == "rain":
            for _ in range(3):
                sp = focus_pos + Vec3(random.uniform(-16, 16), random.uniform(10, 16), random.uniform(-16, 16))
                vel = Vec3(-1.0, -14.0, -1.0)
                self.rain_pool.emit(sp, vel, lifetime=1.2, scale=0.09)

        if ash_level > 0.05:
            n_ash = int(min(5, ash_level * 5))
            for _ in range(n_ash):
                sp = focus_pos + Vec3(random.uniform(-18, 18), random.uniform(8, 14), random.uniform(-18, 18))
                vel = Vec3(random.uniform(-0.8, 0.8), random.uniform(-2.5, -4.5), random.uniform(-0.8, 0.8))
                self.ash_pool.emit(sp, vel, lifetime=3.0, scale=0.11)

    def update(self) -> None:
        import time
        from ursina import time as utime
        dt = utime.dt
        self.rain_pool.update(dt, gravity=-8.0)
        self.ash_pool.update(dt, gravity=-1.5)
        self.dust_pool.update(dt, gravity=-1.0)
        self.ember_pool.update(dt, gravity=1.2)  # Embers float upwards
        self.confetti_pool.update(dt, gravity=-3.5)


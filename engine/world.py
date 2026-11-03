"""
engine/world.py - Procedural 40x40 Island World Generator
Owned by Tech C (Integration, Engine, World).
"""

import math
import random
from typing import Any, Dict, List, Tuple


class IslandWorld:
    """
    Procedural 40x40 Island Map generator using deterministic seeded noise.
    Tile Types:
      0: Water (Ocean border + freshwater streams)
      1: Plains (Beach, meadows, open clearings)
      2: Forest (Dense trees, wood, forageable berries)
      3: Mountain (High elevation, rock, stone)
      4: Shelter (Built or natural shelter location)
    """

    def __init__(self, width: int = 40, height: int = 40, seed: int = 42):
        self.width = width
        self.height = height
        self.seed = seed
        self.tiles = [[0 for _ in range(width)] for _ in range(height)]
        self.freshwater_tiles: List[Tuple[int, int]] = []
        self.food_tiles: List[Tuple[int, int]] = []
        self.shelter_tiles: List[Tuple[int, int]] = []
        self.spawn_pos: List[int] = [20, 20]
        self._generate()

    def _generate(self):
        rng = random.Random(self.seed)
        cx, cy = self.width / 2.0, self.height / 2.0
        max_radius = 16.0

        # 1. Base Island Shape (Radial gradient with noise perturbation)
        for y in range(self.height):
            for x in range(self.width):
                dist = math.hypot(x - cx, y - cy)
                # Multi-octave sinusoidal noise for organic coastlines
                noise = (
                    math.sin(x * 0.4 + self.seed % 10) * 1.8 +
                    math.cos(y * 0.4 + self.seed % 7) * 1.8 +
                    math.sin((x + y) * 0.3) * 1.2
                )
                effective_dist = dist + noise

                if effective_dist > max_radius:
                    self.tiles[y][x] = 0  # Ocean Water
                elif effective_dist > max_radius - 3.5:
                    self.tiles[y][x] = 1  # Plains / Beach
                elif effective_dist > max_radius - 8.5:
                    self.tiles[y][x] = 2  # Dense Forest
                else:
                    # Mountain center with rocky slopes
                    self.tiles[y][x] = 3 if rng.random() > 0.35 else 2

        # 2. Freshwater Stream carving from Mountain down to Coast
        stream_x, stream_y = int(cx), int(cy)
        stream_dir = rng.choice([(1, 1), (-1, 1), (1, -1), (-1, -1)])
        for _ in range(15):
            if 0 <= stream_x < self.width and 0 <= stream_y < self.height:
                self.tiles[stream_y][stream_x] = 0  # Water
                self.freshwater_tiles.append((stream_x, stream_y))
            stream_x += stream_dir[0] + rng.choice([0, rng.choice([-1, 1])])
            stream_y += stream_dir[1] + rng.choice([0, rng.choice([-1, 1])])

        # 3. Mark Food & Forage Locations in Forests
        for y in range(self.height):
            for x in range(self.width):
                if self.tiles[y][x] == 2 and rng.random() < 0.25:
                    self.food_tiles.append((x, y))

        # 4. Starting Spawn Point (Safe beach / clearing near forest)
        candidates = []
        for y in range(8, self.height - 8):
            for x in range(8, self.width - 8):
                if self.tiles[y][x] == 1:
                    # Near water and near forest
                    has_water = any(
                        0 <= x + dx < self.width and 0 <= y + dy < self.height and self.tiles[y + dy][x + dx] == 0
                        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                    )
                    has_forest = any(
                        0 <= x + dx < self.width and 0 <= y + dy < self.height and self.tiles[y + dy][x + dx] == 2
                        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                    )
                    if has_water or has_forest:
                        candidates.append([x, y])

        if candidates:
            self.spawn_pos = rng.choice(candidates)
        else:
            self.spawn_pos = [int(cx), int(cy)]

    def get_tile(self, x: int, y: int) -> int:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return 0  # Default water outside bounds

    def set_shelter(self, x: int, y: int):
        """Upgrades a land tile to a shelter spot."""
        if 0 <= x < self.width and 0 <= y < self.height and self.tiles[y][x] != 0:
            self.tiles[y][x] = 4
            if (x, y) not in self.shelter_tiles:
                self.shelter_tiles.append((x, y))

    def is_near_water(self, x: int, y: int, radius: int = 2) -> bool:
        """Returns True if agent is within `radius` tiles of water."""
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if 0 <= x + dx < self.width and 0 <= y + dy < self.height and self.tiles[y + dy][x + dx] == 0:
                    return True
        return False

    def is_in_shelter(self, x: int, y: int) -> bool:
        """Returns True if agent is in an established shelter tile."""
        return self.get_tile(x, y) == 4

    def export_dict(self) -> Dict[str, Any]:
        """Returns world serialization dict conforming to timeline.json schema."""
        return {
            "width": self.width,
            "height": self.height,
            "tiles": self.tiles,
            "seed": self.seed
        }

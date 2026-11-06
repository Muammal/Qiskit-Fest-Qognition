"""3D World Builder: merged terrain geometry, scenery placement, water, and lighting.

Combines the 40x40 simulation grid into single merged meshes with vertex colors,
preventing entity bloat and guaranteeing steady 60 FPS. Instantiates props, animated water,
hazard overlays, and day/night celestial lighting.
"""
from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional, Set, Tuple

from panda3d.core import (
    Geom,
    GeomNode,
    GeomTriangles,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
    NodePath,
    Vec4,
)
from ursina import (
    DirectionalLight,
    AmbientLight,
    Entity,
    Mesh,
    Vec3,
    color,
    destroy,
    scene,
)

from gui3d.models import (
    create_bush,
    create_campfire,
    create_dock,
    create_hut,
    create_rock,
    create_tree,
    create_volcano_model,
)
from gui3d.palette import (
    ASH,
    DARK_WOOD,
    DEEP_GREEN,
    GOLD,
    GRASS,
    LAVA,
    OUTLINE,
    RED,
    ROCK,
    SAND,
    TILE_COLORS,
    WATER,
    WHITE,
    WOOD,
    daynight,
)
from gui3d.shaders import toon_cel_shader, water_shader


def build_merged_terrain_mesh(tiles: List[List[int]], elevation: Optional[List[List[int]]] = None) -> Mesh:
    """Builds a single merged mesh with vertex colors for the entire 40x40 grid."""
    h = len(tiles)
    w = len(tiles[0]) if h else 0

    vertices: List[Vec3] = []
    triangles: List[Tuple[int, int, int]] = []
    colors: List[Vec4] = []
    normals: List[Vec3] = []

    def get_elev(x: int, y: int) -> float:
        if not elevation or y >= len(elevation) or x >= len(elevation[y]):
            t = tiles[y][x] if 0 <= y < h and 0 <= x < w else 0
            return 0.0 if t == 0 else (0.2 if t == 1 else (0.4 if t == 2 else 0.8))
        raw = elevation[y][x]
        return max(0.0, float(raw)) * 0.005

    for y in range(h):
        for x in range(w):
            t = tiles[y][x]
            # Tile base color with Hay Day checkerboard pattern on grass
            base_rgb = TILE_COLORS.get(t, GRASS)
            if t == 1:  # Grass checkerboard
                if (x + y) % 2 == 0:
                    base_rgb = (126, 202, 68)  # #7CC24A
                else:
                    base_rgb = (114, 190, 58)  # slightly darker
            elif t == 0:  # Water
                base_rgb = WATER

            r, g, b = [c / 255.0 for c in base_rgb]
            v_color = Vec4(r, g, b, 1.0)

            # Cell corners centered at (0, 0)
            cx, cz = x - w * 0.5, y - h * 0.5
            y00 = get_elev(x, y)
            y10 = get_elev(min(w - 1, x + 1), y)
            y01 = get_elev(x, min(h - 1, y + 1))
            y11 = get_elev(min(w - 1, x + 1), min(h - 1, y + 1))

            v_idx = len(vertices)
            p0 = Vec3(cx, y00, cz)
            p1 = Vec3(cx + 1, y10, cz)
            p2 = Vec3(cx + 1, y11, cz + 1)
            p3 = Vec3(cx, y01, cz + 1)

            # Normal calculation
            normal = Vec3(0, 1, 0)

            vertices.extend([p0, p1, p2, p3])
            colors.extend([v_color, v_color, v_color, v_color])
            normals.extend([normal, normal, normal, normal])

            triangles.append((v_idx, v_idx + 1, v_idx + 2))
            triangles.append((v_idx, v_idx + 2, v_idx + 3))

    return Mesh(vertices=vertices, triangles=triangles, colors=colors, normals=normals)


class World3D(Entity):
    """Encapsulates terrain, scenery props, water, and hazard overlays."""

    def __init__(self, world_dict: Dict[str, Any], quality: str = "high", **kwargs):
        super().__init__(**kwargs)
        self.world_dict = world_dict or {}
        self.quality = quality
        self.width = int(self.world_dict.get("width") or 40)
        self.height = int(self.world_dict.get("height") or 40)
        self.tiles = self.world_dict.get("tiles") or [[1] * self.width for _ in range(self.height)]
        self.elevation = self.world_dict.get("elevation")

        self.props: List[Entity] = []
        self.shelter_entities: Dict[Tuple[int, int], Entity] = {}
        self.hazard_overlays: List[Entity] = []

        self._build_environment()
        self._build_lighting()

    def _build_environment(self) -> None:
        # 1. Merged Terrain Mesh
        terrain_mesh = build_merged_terrain_mesh(self.tiles, self.elevation)
        self.terrain = Entity(
            parent=self,
            model=terrain_mesh,
            shader=toon_cel_shader if self.quality != "low" else None,
        )

        # 2. Animated Ocean / Water Plane
        self.water = Entity(
            parent=self,
            model="plane",
            scale=(self.width * 2.2, 1, self.height * 2.2),
            position=(0, 0.05, 0),
            color=color.rgba(*WATER, 190),
            shader=water_shader if self.quality == "high" else None,
        )

        # 3. Procedural Scenery Props (Trees, Rocks, Bushes, Volcano)
        rng = random.Random(int(self.world_dict.get("seed") or 101))
        half_w = self.width * 0.5
        half_h = self.height * 0.5

        def tile_to_world(tx: int, ty: int) -> Tuple[float, float, float]:
            raw_el = self.elevation[ty][tx] if self.elevation and ty < len(self.elevation) and tx < len(self.elevation[ty]) else 0
            wy = max(0.0, float(raw_el)) * 0.005
            return tx - half_w + 0.5, wy, ty - half_h + 0.5

        # Place Volcano at Caldera Vent if volcano scenario
        volcano_data = self.world_dict.get("volcano") or {}
        vent = volcano_data.get("vent", [20, 20])
        if self.world_dict.get("scenario") == "volcano" or volcano_data.get("erupts"):
            vx, vy, vz = tile_to_world(vent[0], vent[1])
            self.volcano_prop = create_volcano_model(parent=self, pos=(vx, vy, vz), scale=1.4)
            self.props.append(self.volcano_prop)

        # Place Campfire near spawn
        spawn = (self.world_dict.get("evacuation_map") or {}).get("route_from_spawn", [[24, 25]])[0]
        sx, sy, sz = tile_to_world(spawn[0], spawn[1])
        self.campfire = create_campfire(parent=self, pos=(sx + 0.6, sy, sz + 0.6), scale=0.8)
        self.props.append(self.campfire)

        # Populate vegetation and geology
        step_interval = 2 if self.quality == "low" else 1
        for y in range(0, self.height, step_interval):
            for x in range(0, self.width, step_interval):
                t = self.tiles[y][x]
                px, py, pz = tile_to_world(x, y)

                if t == 2:  # Forest
                    if rng.random() < 0.65:
                        tr = create_tree(parent=self, pos=(px, py, pz), scale=rng.uniform(0.7, 1.1), seed=x * 100 + y)
                        self.props.append(tr)
                elif t == 3:  # Mountain
                    if rng.random() < 0.40 and (x, y) != tuple(vent):
                        rk = create_rock(parent=self, pos=(px, py, pz), scale=rng.uniform(0.6, 1.2), seed=x * 77 + y)
                        self.props.append(rk)
                elif t == 1:  # Plain
                    if rng.random() < 0.08:
                        bs = create_bush(parent=self, pos=(px, py, pz), scale=0.7)
                        self.props.append(bs)

    def _build_lighting(self) -> None:
        """Sets up day/night sun and ambient lights with soft shadow mapping."""
        shadows_enabled = self.quality == "high"
        self.sun = DirectionalLight(
            parent=self,
            rotation=(50, 45, 0),
            color=color.rgb(255, 245, 220),
            shadows=shadows_enabled,
        )
        self.ambient = AmbientLight(parent=self, color=color.rgb(100, 110, 130))

    def update_daynight(self, hour: float) -> None:
        """Update sunlight, ambient intensity, and sky colors based on hour."""
        sky_rgb, sun_rgb, amb_rgb, intensity = daynight(hour)
        self.sun.color = color.rgb(
            int(sun_rgb[0] * intensity),
            int(sun_rgb[1] * intensity),
            int(sun_rgb[2] * intensity),
        )
        self.ambient.color = color.rgb(*amb_rgb)

    def sync_shelters(self, shelters: Set[Tuple[int, int]]) -> None:
        """Dynamically add or remove shelter hut props."""
        half_w = self.width * 0.5
        half_h = self.height * 0.5

        current = set(self.shelter_entities.keys())
        # Add new
        for tx, ty in shelters - current:
            raw_el = self.elevation[ty][tx] if self.elevation else 0
            wy = max(0.0, float(raw_el)) * 0.005
            hut = create_hut(parent=self, pos=(tx - half_w + 0.5, wy, ty - half_h + 0.5), scale=0.85)
            self.shelter_entities[(tx, ty)] = hut

        # Remove destroyed
        for tx, ty in current - shelters:
            destroy(self.shelter_entities.pop((tx, ty)))

    def update_hazards(self, hazards, show_evac: bool = False) -> None:
        """Update active flow markers and evacuation path overlay."""
        for e in self.hazard_overlays:
            destroy(e)
        self.hazard_overlays.clear()

        half_w = self.width * 0.5
        half_h = self.height * 0.5

        def tile_to_pos(tx: int, ty: int) -> Tuple[float, float, float]:
            raw_el = self.elevation[ty][tx] if self.elevation else 0
            return tx - half_w + 0.5, max(0.0, float(raw_el)) * 0.005 + 0.06, ty - half_h + 0.5

        # 1. Active PDC tiles (glowing red-orange quad)
        for tx, ty in hazards.active_pdc:
            px, py, pz = tile_to_pos(tx, ty)
            q = Entity(parent=self, model="quad", color=color.rgba(*RED, 210), scale=0.9, position=(px, py, pz), rotation=(90, 0, 0))
            self.hazard_overlays.append(q)

        # 2. Active Lahar tiles (dark mud quad)
        for tx, ty in hazards.active_lahar:
            px, py, pz = tile_to_pos(tx, ty)
            q = Entity(parent=self, model="quad", color=color.rgba(*DARK_WOOD, 200), scale=0.9, position=(px, py, pz), rotation=(90, 0, 0))
            self.hazard_overlays.append(q)

        # 3. Deposited Lava tiles
        for tx, ty in hazards.lava:
            px, py, pz = tile_to_pos(tx, ty)
            q = Entity(parent=self, model="quad", color=color.rgba(*LAVA, 220), scale=0.9, position=(px, py, pz), rotation=(90, 0, 0))
            self.hazard_overlays.append(q)

        # 4. Evacuation route overlay (E key)
        if show_evac:
            evac_map = self.world_dict.get("evacuation_map") or {}
            routes = evac_map.get("routes_from_spawn", [])
            for route in routes:
                for tx, ty in route:
                    px, py, pz = tile_to_pos(tx, ty)
                    q = Entity(parent=self, model="quad", color=color.rgba(*GOLD, 210), scale=0.65, position=(px, py, pz), rotation=(90, 0, 0))
                    self.hazard_overlays.append(q)
            # Assembly points
            for ax, ay in evac_map.get("assembly_points", []):
                px, py, pz = tile_to_pos(ax, ay)
                q = Entity(parent=self, model="quad", color=color.rgba(*DEEP_GREEN, 240), scale=1.1, position=(px, py, pz), rotation=(90, 0, 0))
                self.hazard_overlays.append(q)


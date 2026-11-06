"""Procedural low-poly 3D models and character assembly (Ursina / Panda3D).

Constructs stylized, chunky "Hay Day"-inspired 3D models from primitives in code:
trees with foliage variants, faceted boulders, berry bushes, huts, campfires, docks,
the volcano caldera, and a cute straw-hat character with pose controls.

Provides fixed model names so optional CC0 .glb files (e.g. Kenney assets) can replace
them seamlessly if dropped into assets/.
"""
from __future__ import annotations

import math
import random
from typing import Dict, List, Optional, Tuple

from ursina import (
    Entity,
    Mesh,
    Vec3,
    color,
    destroy,
)

from gui3d.palette import (
    ACCENT,
    BLUE_UI,
    CREAM,
    DARK_WOOD,
    DEEP_GREEN,
    GOLD,
    GRASS,
    LAVA,
    OUTLINE,
    PARCHMENT,
    RED,
    ROCK,
    SAND,
    WATER,
    WHITE,
    WOOD,
)

from ursina.models.procedural.cone import Cone
from ursina.models.procedural.cylinder import Cylinder

_SHARED_CONE = None
_SHARED_CYLINDER = None


def get_cone():
    global _SHARED_CONE
    if _SHARED_CONE is None:
        _SHARED_CONE = Cone(resolution=8)
    return _SHARED_CONE


def get_cylinder():
    global _SHARED_CYLINDER
    if _SHARED_CYLINDER is None:
        _SHARED_CYLINDER = Cylinder(resolution=8)
    return _SHARED_CYLINDER

#: Standard model names for drop-in CC0 .glb replacement
MODEL_FILENAMES: Dict[str, str] = {
    "tree": "models/tree.glb",
    "rock": "models/rock.glb",
    "bush": "models/bush.glb",
    "hut": "models/hut.glb",
    "campfire": "models/campfire.glb",
    "dock": "models/dock.glb",
    "volcano": "models/volcano.glb",
    "agent": "models/agent.glb",
}


def create_tree(parent=None, pos: Tuple[float, float, float] = (0, 0, 0), scale: float = 1.0, seed: int = 0) -> Entity:
    """Stylized tree with cylindrical timber trunk and stacked fluffy foliage cones."""
    rng = random.Random(seed)
    root = Entity(parent=parent, position=pos, scale=scale)

    # Trunk
    Entity(
        parent=root,
        model=get_cylinder(),
        color=color.rgb(*WOOD),
        scale=(0.35, 1.2, 0.35),
        position=(0, 0.6, 0),
    )

    # Foliage tiers (stacked cones with slight color variation)
    base_color = DEEP_GREEN if (seed % 2 == 0) else GRASS
    tiers = 3
    for i in range(tiers):
        t_y = 1.2 + i * 0.75
        t_scale = (1.5 - i * 0.35) * (0.9 + rng.random() * 0.2)
        c_shift = i * 15
        col = color.rgb(
            min(255, base_color[0] + c_shift),
            min(255, base_color[1] + c_shift),
            min(255, base_color[2] + c_shift),
        )
        Entity(
            parent=root,
            model=get_cone(),
            color=col,
            scale=(t_scale, 1.1, t_scale),
            position=(0, t_y, 0),
        )

    return root


def create_rock(parent=None, pos: Tuple[float, float, float] = (0, 0, 0), scale: float = 1.0, seed: int = 0) -> Entity:
    """Chunky faceted rock boulder with warm gray tone and subtle moss cap."""
    rng = random.Random(seed)
    root = Entity(parent=parent, position=pos, scale=scale)

    # Main boulder
    rot = (rng.uniform(-15, 15), rng.uniform(0, 360), rng.uniform(-15, 15))
    Entity(
        parent=root,
        model="sphere",
        color=color.rgb(*ROCK),
        scale=(0.9 + rng.random() * 0.3, 0.65, 0.8 + rng.random() * 0.3),
        position=(0, 0.32, 0),
        rotation=rot,
    )

    # Secondary pebble
    Entity(
        parent=root,
        model="sphere",
        color=color.rgb(ROCK[0] - 20, ROCK[1] - 20, ROCK[2] - 20),
        scale=(0.4, 0.3, 0.4),
        position=(0.45, 0.15, -0.3),
    )

    return root


def create_bush(parent=None, pos: Tuple[float, float, float] = (0, 0, 0), scale: float = 1.0, has_berries: bool = True) -> Entity:
    """Cute rounded bush cluster with optional ruby berries."""
    root = Entity(parent=parent, position=pos, scale=scale)

    # Central foliage
    Entity(
        parent=root,
        model="sphere",
        color=color.rgb(*GRASS),
        scale=(0.85, 0.7, 0.85),
        position=(0, 0.35, 0),
    )
    # Side puffs
    Entity(
        parent=root,
        model="sphere",
        color=color.rgb(*DEEP_GREEN),
        scale=(0.6, 0.5, 0.6),
        position=(0.3, 0.25, 0.2),
    )
    Entity(
        parent=root,
        model="sphere",
        color=color.rgb(*DEEP_GREEN),
        scale=(0.55, 0.45, 0.55),
        position=(-0.25, 0.22, -0.2),
    )

    if has_berries:
        for bx, by, bz in [(0.2, 0.5, 0.3), (-0.2, 0.45, 0.25), (0.0, 0.55, -0.3)]:
            Entity(
                parent=root,
                model="sphere",
                color=color.rgb(*RED),
                scale=0.14,
                position=(bx, by, bz),
            )

    return root


def create_hut(parent=None, pos: Tuple[float, float, float] = (0, 0, 0), scale: float = 1.0) -> Entity:
    """Timber survival shelter with pitched thatch roof and glowing doorway."""
    root = Entity(parent=parent, position=pos, scale=scale)

    # Walls
    Entity(
        parent=root,
        model="cube",
        color=color.rgb(*WOOD),
        scale=(1.4, 1.0, 1.4),
        position=(0, 0.5, 0),
    )

    # Pitched roof (cone/pyramid)
    Entity(
        parent=root,
        model=get_cone(),
        color=color.rgb(*DARK_WOOD),
        scale=(1.9, 0.9, 1.9),
        position=(0, 1.4, 0),
        rotation=(0, 45, 0),
    )

    # Cozy door opening
    Entity(
        parent=root,
        model="cube",
        color=color.rgb(30, 20, 15),
        scale=(0.45, 0.7, 0.1),
        position=(0, 0.35, 0.71),
    )

    return root


def create_dock(parent=None, pos: Tuple[float, float, float] = (0, 0, 0), scale: float = 1.0) -> Entity:
    """Wooden pier planks extending over shoreline water with timber stilts."""
    root = Entity(parent=parent, position=pos, scale=scale)

    # Deck planking
    Entity(
        parent=root,
        model="cube",
        color=color.rgb(*WOOD),
        scale=(1.2, 0.1, 2.4),
        position=(0, 0.35, 1.0),
    )

    # Timber pilings / stilts
    for px, pz in [(-0.5, 0.2), (0.5, 0.2), (-0.5, 1.8), (0.5, 1.8)]:
        Entity(
            parent=root,
            model=get_cylinder(),
            color=color.rgb(*DARK_WOOD),
            scale=(0.12, 0.7, 0.12),
            position=(px, 0.15, pz),
        )

    # Mooring post
    Entity(
        parent=root,
        model=get_cylinder(),
        color=color.rgb(*WOOD),
        scale=(0.14, 0.45, 0.14),
        position=(0.45, 0.55, 2.1),
    )

    return root


def create_campfire(parent=None, pos: Tuple[float, float, float] = (0, 0, 0), scale: float = 1.0) -> Entity:
    """Campfire with wood log ring, glowing charcoal base, and animated flame."""
    root = Entity(parent=parent, position=pos, scale=scale)

    # Stone ring
    for angle in range(0, 360, 60):
        rad = math.radians(angle)
        sx = math.cos(rad) * 0.45
        sz = math.sin(rad) * 0.45
        Entity(
            parent=root,
            model="sphere",
            color=color.rgb(*ROCK),
            scale=(0.2, 0.15, 0.2),
            position=(sx, 0.08, sz),
        )

    # Cross logs
    for rot in (30, 120):
        Entity(
            parent=root,
            model=get_cylinder(),
            color=color.rgb(*DARK_WOOD),
            scale=(0.14, 0.8, 0.14),
            position=(0, 0.12, 0),
            rotation=(90, rot, 0),
        )

    # Glowing ember core
    root.ember = Entity(
        parent=root,
        model="sphere",
        color=color.rgb(*GOLD),
        scale=0.3,
        position=(0, 0.2, 0),
    )

    return root


def create_volcano_model(parent=None, pos: Tuple[float, float, float] = (0, 0, 0), scale: float = 1.0) -> Entity:
    """Volcano caldera cone with glowing emissive crater and lava rim."""
    root = Entity(parent=parent, position=pos, scale=scale)

    # Main cone (inverted truncated cone)
    root.cone = Entity(
        parent=root,
        model=get_cone(),
        color=color.rgb(*ROCK),
        scale=(4.0, 3.2, 4.0),
        position=(0, 1.6, 0),
    )

    # Crater magma pool
    root.crater = Entity(
        parent=root,
        model=get_cylinder(),
        color=color.rgb(*LAVA),
        scale=(1.4, 0.1, 1.4),
        position=(0, 3.0, 0),
    )

    return root


class Agent3D(Entity):
    """Cute, stylized agent character with limbs, straw hat, and procedural animation poses."""

    def __init__(self, parent=None, pos: Tuple[float, float, float] = (0, 0, 0), **kwargs):
        super().__init__(parent=parent, position=pos, **kwargs)

        self.root_node = Entity(parent=self)

        # Soft blob shadow
        self.shadow = Entity(
            parent=self,
            model="quad",
            color=color.rgba(20, 10, 5, 130),
            scale=(0.9, 0.7, 1.0),
            position=(0, 0.03, 0),
            rotation=(90, 0, 0),
        )

        # Body (tunic)
        self.body = Entity(
            parent=self.root_node,
            model="cube",
            color=color.rgb(*BLUE_UI),
            scale=(0.5, 0.55, 0.35),
            position=(0, 0.55, 0),
        )

        # Head
        self.head = Entity(
            parent=self.root_node,
            model="sphere",
            color=color.rgb(*CREAM),
            scale=0.45,
            position=(0, 1.0, 0),
        )

        # Straw Hat (chunky Hay Day brim + cone top)
        self.hat_brim = Entity(
            parent=self.head,
            model=get_cylinder(),
            color=color.rgb(*GOLD),
            scale=(1.4, 0.08, 1.4),
            position=(0, 0.35, 0),
        )
        self.hat_crown = Entity(
            parent=self.head,
            model=get_cylinder(),
            color=color.rgb(GOLD[0] - 25, GOLD[1] - 25, GOLD[2] - 25),
            scale=(0.85, 0.35, 0.85),
            position=(0, 0.55, 0),
        )

        # Eyes
        self.eye_l = Entity(parent=self.head, model="sphere", color=color.rgb(*OUTLINE), scale=0.08, position=(-0.11, 0.05, 0.20))
        self.eye_r = Entity(parent=self.head, model="sphere", color=color.rgb(*OUTLINE), scale=0.08, position=(0.11, 0.05, 0.20))

        # Limbs
        self.leg_l = Entity(parent=self.root_node, model=get_cylinder(), color=color.rgb(*DARK_WOOD), scale=(0.14, 0.35, 0.14), position=(-0.15, 0.18, 0))
        self.leg_r = Entity(parent=self.root_node, model=get_cylinder(), color=color.rgb(*DARK_WOOD), scale=(0.14, 0.35, 0.14), position=(0.15, 0.18, 0))
        self.arm_l = Entity(parent=self.root_node, model=get_cylinder(), color=color.rgb(*CREAM), scale=(0.12, 0.35, 0.12), position=(-0.32, 0.55, 0))
        self.arm_r = Entity(parent=self.root_node, model=get_cylinder(), color=color.rgb(*CREAM), scale=(0.12, 0.35, 0.12), position=(0.32, 0.55, 0))

        self.current_pose = "idle"
        self._anim_timer = 0.0

    def set_pose(self, pose: str) -> None:
        """Set pose: 'idle', 'walk', 'hurt', 'happy', 'fallen'."""
        self.current_pose = pose
        if pose == "fallen":
            self.root_node.rotation_z = 85
            self.root_node.y = -0.2
        elif pose == "hurt":
            self.body.color = color.rgb(*RED)
            self.root_node.rotation_z = 15
        elif pose == "happy":
            self.body.color = color.rgb(*GOLD)
            self.root_node.rotation_z = 0
            self.arm_l.rotation_z = 120
            self.arm_r.rotation_z = -120
        else:
            self.body.color = color.rgb(*BLUE_UI)
            self.root_node.rotation_z = 0
            self.root_node.y = 0

    def animate(self, dt: float, is_moving: bool = False) -> None:
        """Update procedural limb animations and head bobbing."""
        self._anim_timer += dt * 6.0
        if self.current_pose == "fallen":
            return

        if is_moving:
            # Walk cycle: swinging limbs + bob
            swing = math.sin(self._anim_timer) * 35.0
            self.leg_l.rotation_x = swing
            self.leg_r.rotation_x = -swing
            self.arm_l.rotation_x = -swing
            self.arm_r.rotation_x = swing
            self.root_node.y = abs(math.sin(self._anim_timer * 2.0)) * 0.08
        else:
            # Idle gentle breath / bob
            self.leg_l.rotation_x = 0
            self.leg_r.rotation_x = 0
            self.arm_l.rotation_x = 0
            self.arm_r.rotation_x = 0
            self.root_node.y = math.sin(self._anim_timer * 0.5) * 0.03

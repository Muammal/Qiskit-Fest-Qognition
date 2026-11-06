"""gui3d - Stylized 3D front-end (Ursina / Panda3D) for the Quantum Cognition Simulation.

Pure-logic modules (no Ursina import, testable headless):
    data_source, playback, ending_stats, layout, palette

Rendering modules (import Ursina lazily):
    display, textures, models, shaders, world, particles, agent3d, cameras, ui, screens,
    cinematics, app
"""

__all__ = ["data_source", "playback", "ending_stats", "layout", "palette"]


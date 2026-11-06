"""Short diagonal-angle cutscenes for jumps, lifeboats and anything leaving the ship.

Everything is drawn from pygame primitives, like the rest of the GUI. Scenes are
display only: they pause the simulation and never change its result.
"""

import math

import pygame

from engine.crowd import ROLE_COLORS

DURATION = 3.5  # seconds
WIDTH, HEIGHT = 1600, 900
COOLDOWN_STEPS = 8  # crowd jump scenes repeat at most this often, unless it is the person being followed
MAX_PER_STEP = 2
HORIZON_Y = 150
SKY_TOP, SKY_LOW = (6, 10, 26), (34, 46, 78)
SEA_FAR, SEA_NEAR = (34, 72, 112), (8, 26, 50)
DECK_Z = 14.0
RAIL_Z = DECK_Z + 1.1
BOAT_X = 42.0
CAMERA_ANGLE = math.radians(35)  # assumption: diagonal view, hull receding to the right
CAMERA_DISTANCE, CAMERA_FOCAL, CAMERA_HEIGHT = 75.0, 2250.0, 21.4
FIGURE = 3.0  # figure height in scene units; drawn large on purpose so a jump reads clearly


def project(x, y, z, tilt=0.0):
    """Perspective from above the deck, off the ship's side. x along ship, y outward, z up."""
    dx = x - BOAT_X
    if tilt:
        z = z - dx * math.tan(math.radians(tilt))
    depth = max(6.0, CAMERA_DISTANCE + dx * math.sin(CAMERA_ANGLE) - y * math.cos(CAMERA_ANGLE))
    scale = CAMERA_FOCAL / depth
    sx = 700 + (dx * math.cos(CAMERA_ANGLE) + y * math.sin(CAMERA_ANGLE)) * scale
    sy = HORIZON_Y + (CAMERA_HEIGHT - z) * scale * 0.95
    return sx, sy, scale


def _pt(x, y, z, tilt=0.0):
    sx, sy, _ = project(x, y, z, tilt)
    return sx, sy


def _deck_z(x, tilt):
    """Rail height at x on the tilted ship, for paths drawn in sea-fixed coordinates."""
    return RAIL_Z - (x - BOAT_X) * math.tan(math.radians(tilt))


def draw_person(surface, x, y, size, pose, color):
    """Stick figure with a solid torso. pose is stand, crouch, leap, fall or swim."""
    head = max(3, int(size * 0.13))
    skin = (240, 208, 176)
    width = max(2, int(size * 0.07))
    if pose == "crouch":
        hip = (x, y - size * 0.28)
        neck = (x + size * 0.12, y - size * 0.62)
        legs = [((x - size * 0.18, y - size * 0.1), (x - size * 0.1, y)), ((x + size * 0.12, y - size * 0.12), (x + size * 0.2, y))]
        arms = [(x + size * 0.32, y - size * 0.34), (x - size * 0.1, y - size * 0.36)]
    elif pose == "leap":
        hip = (x, y - size * 0.42)
        neck = (x + size * 0.18, y - size * 0.8)
        legs = [((x - size * 0.24, y - size * 0.26), (x - size * 0.46, y - size * 0.32)), ((x + size * 0.1, y - size * 0.18), (x - size * 0.06, y))]
        arms = [(x + size * 0.5, y - size * 1.05), (x - size * 0.1, y - size * 1.0)]
    elif pose == "fall":
        hip = (x, y - size * 0.45)
        neck = (x + size * 0.04, y - size * 0.85)
        legs = [((x - size * 0.14, y - size * 0.2), (x - size * 0.1, y)), ((x + size * 0.14, y - size * 0.2), (x + size * 0.1, y))]
        arms = [(x + size * 0.36, y - size * 1.1), (x - size * 0.32, y - size * 1.1)]
    elif pose == "swim":
        pygame.draw.circle(surface, skin, (int(x), int(y - size * 0.12)), head)
        pygame.draw.line(surface, color, (x - size * 0.3, y - size * 0.25), (x + size * 0.3, y - size * 0.25), width)
        return
    else:
        hip = (x, y - size * 0.46)
        neck = (x, y - size * 0.84)
        legs = [((x - size * 0.08, y - size * 0.22), (x - size * 0.12, y)), ((x + size * 0.08, y - size * 0.22), (x + size * 0.12, y))]
        arms = [(x + size * 0.2, y - size * 0.5), (x - size * 0.2, y - size * 0.5)]
    for knee, foot in legs:
        pygame.draw.line(surface, (32, 30, 34), hip, knee, width)
        pygame.draw.line(surface, (32, 30, 34), knee, foot, width)
    pygame.draw.line(surface, color, hip, neck, width + 2)
    for hand in arms:
        pygame.draw.line(surface, color, neck, hand, width)
    pygame.draw.circle(surface, skin, (int(neck[0]), int(neck[1] - head)), head)
    pygame.draw.circle(surface, (40, 30, 26), (int(neck[0]), int(neck[1] - head)), head, 1)


def draw_boat(surface, x, y, z, rock=0.0, people=0):
    """A lifeboat lying along the hull, at scene position (x, y, z)."""
    length, beam, height = 5.2, 1.5, 1.1
    corners = [(-length, beam), (length, beam), (length, -beam), (-length, -beam)]

    def p(dx, dy, dz):
        return _pt(x + dx, y + dy, z + dz + rock * dx * 0.08)

    gunwale = [p(a, b, height) for a, b in corners]
    keel = [p(a * 0.8, b * 0.55, 0) for a, b in corners]
    pygame.draw.polygon(surface, (226, 222, 208), [keel[0], keel[1], gunwale[1], gunwale[0]])
    pygame.draw.polygon(surface, (196, 190, 172), [keel[1], keel[2], gunwale[2], gunwale[1]])
    pygame.draw.polygon(surface, (120, 86, 52), gunwale)
    pygame.draw.polygon(surface, (46, 34, 26), gunwale, 2)
    size = project(x, y, z)[2] * 2.2
    for i in range(people):
        fx = -length * 0.7 + (i + 0.5) * (length * 1.4) / people
        px, py = p(fx, (0.5 if i % 2 else -0.4), height * 0.5)
        draw_person(surface, px, py, size, "stand", ((120, 200, 255) if i % 2 else (240, 240, 245)))


def _backdrop():
    surface = pygame.Surface((WIDTH, HEIGHT))
    for y in range(HORIZON_Y):
        f = y / HORIZON_Y
        pygame.draw.line(surface, tuple(int(p + (q - p) * f) for p, q in zip(SKY_TOP, SKY_LOW)), (0, y), (WIDTH, y))
    for y in range(HORIZON_Y, HEIGHT):
        f = (y - HORIZON_Y) / (HEIGHT - HORIZON_Y)
        pygame.draw.line(surface, tuple(int(p + (q - p) * f) for p, q in zip(SEA_FAR, SEA_NEAR)), (0, y), (WIDTH, y))
    for i in range(70):
        pygame.draw.circle(surface, (210, 216, 236), ((i * 211) % WIDTH, 78 + (i * 67) % (HORIZON_Y - 78)), 1)
    for i in range(60):  # wave glints
        wx, wy = (i * 383) % WIDTH, HORIZON_Y + 14 + (i * 149) % (HEIGHT - HORIZON_Y)
        pygame.draw.line(surface, (70, 110, 150), (wx, wy), (wx + 14 + wy // 30, wy), 1)
    return surface


def _ship(surface, tilt, backdrop):
    def p(x, y, z):
        return _pt(x, y, z, tilt)

    x0, x1 = BOAT_X - 26.0, BOAT_X + 110.0
    # Far side of the boat deck: superstructure and funnels.
    pygame.draw.polygon(surface, (214, 210, 196), [p(x0, -7, DECK_Z), p(x1, -7, DECK_Z), p(x1, -7, DECK_Z + 5), p(x0, -7, DECK_Z + 5)])
    for fx in (BOAT_X - 16, BOAT_X + 16, BOAT_X + 48, BOAT_X + 80):
        pygame.draw.polygon(surface, (196, 124, 46), [p(fx, -5, DECK_Z + 5), p(fx + 8, -5, DECK_Z + 5), p(fx + 8, -5, DECK_Z + 34), p(fx, -5, DECK_Z + 34)])
    pygame.draw.polygon(surface, (150, 122, 86), [p(x0, 0, DECK_Z), p(x1, 0, DECK_Z), p(x1, -7, DECK_Z), p(x0, -7, DECK_Z)])
    for i in range(30):  # deck planks
        wx = x0 + i * 4.5
        pygame.draw.line(surface, (126, 100, 70), p(wx, 0, DECK_Z), p(wx, -7, DECK_Z), 1)
    # Hull side: a white upper band, then black, then red below the waterline.
    pygame.draw.polygon(surface, (22, 24, 30), [p(x0, 0, DECK_Z - 3.5), p(x1, 0, DECK_Z - 3.5), p(x1, 0, -6), p(x0, 0, -6)])
    pygame.draw.polygon(surface, (232, 228, 214), [p(x0, 0, DECK_Z), p(x1, 0, DECK_Z), p(x1, 0, DECK_Z - 3.5), p(x0, 0, DECK_Z - 3.5)])
    pygame.draw.polygon(surface, (120, 38, 30), [p(x0, 0, 0.8), p(x1, 0, 0.8), p(x1, 0, -6), p(x0, 0, -6)])
    for row, z in enumerate((DECK_Z - 1.7, DECK_Z - 6.0, DECK_Z - 9.0)):
        color = (40, 44, 54) if row == 0 else (250, 214, 120)
        for i in range(56):
            sx, sy, scale = project(x0 + i * 2.5 + row, 0, z, tilt)
            if -20 < sx < WIDTH + 20:
                pygame.draw.circle(surface, color, (int(sx), int(sy)), max(1, int(scale * 0.13)))
    for i in range(46):
        wx = x0 + i * 3
        pygame.draw.line(surface, (226, 220, 200), p(wx, 0, DECK_Z), p(wx, 0, RAIL_Z), 2)
    pygame.draw.line(surface, (244, 240, 222), p(x0, 0, RAIL_Z), p(x1, 0, RAIL_Z), 3)
    # The sea covers everything below the waterline along the hull.
    for sx in range(0, WIDTH, 6):
        x = _x_on_hull(sx)
        water_y = _pt(x, 0.2, 0.0)[1]
        top = int(max(HORIZON_Y, water_y))
        if top < HEIGHT:
            surface.blit(backdrop, (sx, top), (sx, top, 6, HEIGHT - top))
            pygame.draw.line(surface, (196, 222, 240), (sx, top), (sx + 6, top), 2)


def _x_on_hull(sx):
    """Ship x whose hull point appears at screen column sx, found by bisection."""
    low, high = BOAT_X - 60.0, BOAT_X + 300.0
    for _ in range(18):
        mid = (low + high) / 2
        if _pt(mid, 0, 0.0)[0] < sx:
            low = mid
        else:
            high = mid
    return (low + high) / 2


def _davits(surface, x, tilt, boat_z, y):
    """Curved davits at both ends of the boat, with the falls (ropes) running down to it."""
    for end in (-5.2, 5.2):
        top = _pt(x + end, y, DECK_Z + 5, tilt)
        base = _pt(x + end, 0, DECK_Z, tilt)
        elbow = _pt(x + end, 1.5, DECK_Z + 5.5, tilt)
        pygame.draw.line(surface, (70, 74, 84), base, elbow, 7)
        pygame.draw.line(surface, (70, 74, 84), elbow, top, 7)
        pygame.draw.line(surface, (216, 206, 170), top, _pt(x + end, y, boat_z + 1, tilt), 2)


def _splash(surface, x, y, age, size=1.0):
    """Expanding ripple rings and droplets; age runs 0..1."""
    if not 0 <= age <= 1:
        return
    sx, sy, scale = project(x, y, 0.0)
    for ring in range(3):
        grow = (age + ring * 0.12) * scale * 2.2 * size
        rect = pygame.Rect(sx - grow, sy - grow * 0.3, grow * 2, grow * 0.6)
        if rect.width > 2:
            pygame.draw.ellipse(surface, (206, 232, 248), rect, 2)
    for i in range(11):
        a = i * 0.7
        rise = math.sin(age * math.pi) * scale * 1.6 * size * (1 + i % 3 * 0.3)
        pygame.draw.circle(surface, (232, 246, 252), (int(sx + math.cos(a) * scale * 1.5 * age * size), int(sy - rise)), 3)


def _arc(start, end, peak, f):
    x = start[0] + (end[0] - start[0]) * f
    y = start[1] + (end[1] - start[1]) * f
    z = start[2] + (end[2] - start[2]) * f + peak * 4 * f * (1 - f)
    return x, y, z


def _figure(surface, position, pose, color, size=FIGURE, tilt=0.0):
    sx, sy, scale = project(*position, tilt)
    if size >= FIGURE:  # a halo marks the person the scene is about
        radius = int(scale * size * 0.62)
        halo = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(halo, (255, 232, 150, 60), (radius, radius), radius)
        surface.blit(halo, (sx - radius, sy - scale * size * 0.5 - radius))
    draw_person(surface, sx, sy, scale * size, pose, color)


def _draw_jump(surface, start, end, peak, f, color, size=FIGURE, trail=True):
    """A figure on a clear parabolic arc in sea-fixed coordinates, with a dotted trail."""
    if trail:
        for i in range(24):
            g = i / 24
            if g > f:
                break
            sx, sy = _pt(*_arc(start, end, peak, g))
            pygame.draw.circle(surface, (252, 236, 170), (int(sx), int(sy)), 3)
    _figure(surface, _arc(start, end, peak, f), "leap" if f < 0.55 else "fall", color, size)


def _scene_jump_boat(surface, f, scene, backdrop):
    tilt = min(scene["trim_deg"], 8)
    boat_y, boat_z = 6.0, DECK_Z - 5.0
    color = ROLE_COLORS.get(scene["role"], ROLE_COLORS["passenger"])
    _ship(surface, tilt, backdrop)
    for i, offset in enumerate((-9, -6.5, 7, 9.5)):
        _figure(surface, (BOAT_X + offset, -0.8, DECK_Z), "stand", (120, 200, 255) if i % 2 else (240, 240, 245), 2.4, tilt)
    _davits(surface, BOAT_X, tilt, boat_z, boat_y)
    start, land = (BOAT_X - 0.4, 0.1, _deck_z(BOAT_X - 0.4, tilt)), (BOAT_X + 0.3, boat_y, boat_z + 0.9)
    landed = f >= 0.68
    rock = math.sin((f - 0.68) * 22) * (1 - f) * 2.5 if landed else 0
    draw_boat(surface, BOAT_X, boat_y, boat_z, rock=rock, people=4)
    if f < 0.25:
        _figure(surface, start, "crouch" if f > 0.1 else "stand", color)
    elif f < 0.68:
        _draw_jump(surface, start, land, 3.2, (f - 0.25) / 0.43, color)
    else:
        _figure(surface, land, "crouch" if f < 0.78 else "stand", color)


def _scene_boat_lowered(surface, f, scene, backdrop):
    tilt = min(scene["trim_deg"], 8)
    _ship(surface, tilt, backdrop)
    lower = min(1.0, f / 0.68)
    eased = lower * lower * (3 - 2 * lower)
    start_z, water_z = DECK_Z - 2.5, 0.3
    z = start_z + (water_z - start_z) * eased
    pull = max(0.0, (f - 0.74) / 0.26)
    y = 6.0 + pull * 8
    _davits(surface, BOAT_X, tilt, z if pull == 0 else DECK_Z - 1, 6.0)
    draw_boat(surface, BOAT_X, y, z, rock=math.sin(f * 14) * 0.4, people=7)
    _splash(surface, BOAT_X, 6.0, (f - 0.62) / 0.38, 1.8)


def _scene_jump_sea(surface, f, scene, backdrop):
    tilt = max(6.0, min(scene["trim_deg"], 14))
    _ship(surface, tilt, backdrop)
    color = ROLE_COLORS.get(scene["role"], ROLE_COLORS["passenger"])
    for i in range(min(5, max(0, scene.get("count", 1) - 1))):
        x = BOAT_X + (-14, -8, 7, 13, 20)[i]
        g = (f - (0.04 + i * 0.09)) / 0.5
        start, end = (x, 0.1, _deck_z(x, tilt)), (x + 1, 8.0 + i, 0.0)
        other = (120, 200, 255) if i % 2 else (240, 240, 245)
        if g <= 0:
            _figure(surface, start, "stand", other, 2.2)
        elif g < 1:
            _draw_jump(surface, start, end, 2.2, g, other, 2.2, trail=False)
        else:
            _splash(surface, end[0], end[1], (g - 1) * 1.2)
            _figure(surface, end, "swim", other, 2.2)
    start, end = (BOAT_X, 0.1, _deck_z(BOAT_X, tilt)), (BOAT_X + 1.5, 10.0, 0.0)
    if f < 0.18:
        _figure(surface, start, "crouch", color)
    elif f < 0.72:
        _draw_jump(surface, start, end, 3.0, (f - 0.18) / 0.54, color)
    else:
        _splash(surface, end[0], end[1], (f - 0.72) / 0.28, 1.6)
        _figure(surface, end, "swim", color)


def _scene_float_off(surface, f, scene, backdrop):
    tilt = 8.0
    _ship(surface, tilt, backdrop)
    # The sea climbs over the deck and lifts the collapsible away.
    rise = min(DECK_Z + 3.0, f * 1.25 * (DECK_Z + 3.0))
    for sx in range(0, WIDTH, 6):
        top = int(max(HORIZON_Y, _pt(_x_on_hull(sx), 0.2, rise)[1]))
        if top < HEIGHT:
            surface.blit(backdrop, (sx, top), (sx, top, 6, HEIGHT - top))
            pygame.draw.line(surface, (196, 222, 240), (sx, top), (sx + 6, top), 2)
    y = 2.0 + f * 10
    z = max(rise, 0.0) * 0.15 + (1 - f) * (DECK_Z - rise) * 0.2
    draw_boat(surface, BOAT_X, y, z, rock=math.sin(f * 10), people=3)
    for i in range(4):
        wx, wy = BOAT_X - 8 + i * 6, 5.0 + i * 1.5 + f * 4
        _figure(surface, (wx, wy, 0.0), "swim", (240, 240, 245) if i % 2 else (120, 200, 255), 2.2)
        _splash(surface, wx, wy, (f * 2 + i * 0.2) % 1, 0.6)


SCENES = {"jump_boat": _scene_jump_boat, "boat_lowered": _scene_boat_lowered, "jump_sea": _scene_jump_sea, "float_off": _scene_float_off}


class CutscenePlayer:
    """Queue and play scenes. The simulation waits while `active` is true."""

    def __init__(self, font_title, font_small):
        self.font_title, self.font_small = font_title, font_small
        self.queue, self.current, self.elapsed = [], None, 0.0
        self.enabled = True
        self.last_crowd_scene = {}
        self._backdrop = None

    @property
    def active(self):
        return self.current is not None

    def reset(self):
        self.queue, self.current, self.elapsed = [], None, 0.0
        self.last_crowd_scene = {}

    def enqueue(self, scenes):
        """Keep scenes for the followed person and all lowerings; rate-limit repeated crowd jumps."""
        if not self.enabled:
            return
        kept = []
        for scene in sorted(scenes, key=lambda s: not s.get("focus")):
            kind = scene["kind"]
            if not scene.get("focus") and kind in ("jump_boat", "jump_sea"):
                last = self.last_crowd_scene.get(kind)
                if last is not None and scene["t"] - last < COOLDOWN_STEPS:
                    continue
                self.last_crowd_scene[kind] = scene["t"]
            kept.append(scene)
        self.queue.extend(kept[:MAX_PER_STEP])
        self._next_if_idle()

    def _next_if_idle(self):
        if self.current is None and self.queue:
            self.current, self.elapsed = self.queue.pop(0), 0.0

    def skip(self):
        self.current = None
        self._next_if_idle()

    def update(self, dt):
        if self.current is None:
            return
        self.elapsed += dt
        if self.elapsed >= DURATION:
            self.skip()

    def draw(self, canvas):
        if self.current is None:
            return
        if self._backdrop is None:
            self._backdrop = _backdrop()
        scene = self.current
        canvas.blit(self._backdrop, (0, 0))
        SCENES[scene["kind"]](canvas, min(1.0, self.elapsed / DURATION), scene, self._backdrop)
        self._draw_frame(canvas, scene)

    def _draw_frame(self, canvas, scene):
        bar = 76
        pygame.draw.rect(canvas, (4, 6, 12), (0, 0, WIDTH, bar))
        pygame.draw.rect(canvas, (4, 6, 12), (0, HEIGHT - bar, WIDTH, bar))
        minutes = 23 * 60 + 30 + scene["t"] * 5
        clock = self.font_small.render(f"{minutes // 60 % 24:02d}:{minutes % 60:02d} ship's time", True, (190, 198, 216))
        canvas.blit(clock, (28, 30))
        title = self.font_title.render(scene["caption"], True, (250, 244, 224))
        canvas.blit(title, ((WIDTH - title.get_width()) // 2, HEIGHT - bar + 16))
        hint = self.font_small.render("Click or press any key to skip", True, (150, 158, 176))
        canvas.blit(hint, ((WIDTH - hint.get_width()) // 2, HEIGHT - bar + 46))
        progress = min(1.0, self.elapsed / DURATION)
        pygame.draw.rect(canvas, (250, 214, 120), (0, HEIGHT - 4, int(WIDTH * progress), 4))

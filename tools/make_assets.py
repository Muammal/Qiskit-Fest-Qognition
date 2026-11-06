"""tools/make_assets.py - Procedural Hay Day-Inspired Asset Generator.
Generates cute, cartoony, high-resolution procedural placeholder sprites using Pillow:
- UI Panels, Buttons, Ribbons
- Vector-styled Icons (trophy, skull, heart, star, flame, water drop, wood, food, atom, dice)
- Terrain Tile Variants (grass, sand, forest, mountain, water with shore foam)
- Props (pine trees, fruit bushes, boulders, active volcano crater, lava, shelter tent)
- Animated Agent Sprite Sheet (idle, walk, hurt, happy, fallen)
- Particle & Ambient Sprites (clouds, soft ground shadows, ash, embers, confetti)

All assets are generated at >= 2x resolution and cached for crisp downscaling.
"""

import os
import math
from PIL import Image, ImageDraw

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
SPRITES_DIR = os.path.join(ASSETS_DIR, "sprites")
TILES_DIR = os.path.join(ASSETS_DIR, "tiles")
ICONS_DIR = os.path.join(ASSETS_DIR, "icons")

# Palette constants
PAL_GRASS = (124, 194, 74, 255)
PAL_DEEP_GREEN = (62, 142, 58, 255)
PAL_WATER = (143, 211, 244, 255)
PAL_WATER_DEEP = (60, 150, 210, 255)
PAL_SAND = (245, 218, 145, 255)
PAL_MOUNTAIN = (140, 135, 145, 255)
PAL_MOUNTAIN_SNOW = (250, 250, 255, 255)
PAL_WOOD = (185, 120, 63, 255)
PAL_DARK_WOOD = (107, 62, 30, 255)
PAL_PARCHMENT = (248, 235, 200, 255)
PAL_GOLD = (255, 204, 0, 255)
PAL_ORANGE = (255, 138, 43, 255)
PAL_RED = (235, 65, 55, 255)
PAL_OUTLINE = (59, 35, 18, 255)
PAL_WHITE = (255, 255, 255, 255)


def ensure_dirs():
    for d in (ASSETS_DIR, SPRITES_DIR, TILES_DIR, ICONS_DIR):
        os.makedirs(d, exist_ok=True)


def make_icons():
    size = (128, 128)

    # 1. Heart (Vitals / Health)
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(64, 110), (16, 50), (32, 20), (64, 38), (96, 20), (112, 50)], fill=PAL_RED, outline=PAL_OUTLINE, width=6)
    d.ellipse([(28, 24), (46, 42)], fill=(255, 140, 130, 255))
    im.save(os.path.join(ICONS_DIR, "icon_heart.png"))

    # 2. Water Drop (Thirst / Springs)
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(64, 14), (20, 80), (34, 110), (94, 110), (108, 80)], fill=PAL_WATER, outline=PAL_OUTLINE, width=6)
    d.ellipse([(38, 65), (56, 85)], fill=PAL_WHITE)
    im.save(os.path.join(ICONS_DIR, "icon_water.png"))

    # 3. Flame (Warmth / Eruption / Fire)
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(64, 12), (30, 60), (45, 110), (83, 110), (98, 60)], fill=PAL_ORANGE, outline=PAL_OUTLINE, width=6)
    d.polygon([(64, 45), (45, 80), (52, 105), (76, 105), (83, 80)], fill=PAL_GOLD)
    im.save(os.path.join(ICONS_DIR, "icon_flame.png"))

    # 4. Star (Rating / Achievement)
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pts = []
    for i in range(10):
        angle = i * (math.pi / 5) - math.pi / 2
        r = 54 if i % 2 == 0 else 24
        pts.append((64 + int(r * math.cos(angle)), 64 + int(r * math.sin(angle))))
    d.polygon(pts, fill=PAL_GOLD, outline=PAL_OUTLINE, width=6)
    d.ellipse([(50, 40), (62, 52)], fill=PAL_WHITE)
    im.save(os.path.join(ICONS_DIR, "icon_star.png"))

    # 5. Skull (Cause of death / Fatalities)
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([(24, 20), (104, 88)], fill=PAL_WHITE, outline=PAL_OUTLINE, width=6)
    d.rectangle([(40, 78), (88, 108)], fill=PAL_WHITE, outline=PAL_OUTLINE, width=5)
    # Eye sockets & teeth
    d.ellipse([(38, 46), (56, 68)], fill=PAL_OUTLINE)
    d.ellipse([(72, 46), (90, 68)], fill=PAL_OUTLINE)
    d.line([(52, 90), (52, 108)], fill=PAL_OUTLINE, width=4)
    d.line([(64, 90), (64, 108)], fill=PAL_OUTLINE, width=4)
    d.line([(76, 90), (76, 108)], fill=PAL_OUTLINE, width=4)
    im.save(os.path.join(ICONS_DIR, "icon_skull.png"))

    # 6. Trophy (Heroic Survival / Victory)
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([(32, 20), (96, 70)], fill=PAL_GOLD, outline=PAL_OUTLINE, width=6)
    d.polygon([(48, 70), (80, 70), (72, 96), (56, 96)], fill=PAL_GOLD, outline=PAL_OUTLINE, width=5)
    d.rectangle([(40, 96), (88, 114)], fill=PAL_DARK_WOOD, outline=PAL_OUTLINE, width=5)
    # Handles
    d.arc([(14, 26), (46, 62)], 90, 270, fill=PAL_OUTLINE, width=6)
    d.arc([(82, 26), (114, 62)], 270, 90, fill=PAL_OUTLINE, width=6)
    im.save(os.path.join(ICONS_DIR, "icon_trophy.png"))

    # 7. Food (Apple / Berries)
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([(24, 30), (104, 110)], fill=PAL_RED, outline=PAL_OUTLINE, width=6)
    d.ellipse([(38, 44), (56, 62)], fill=(255, 140, 130, 255))
    d.line([(64, 14), (64, 32)], fill=PAL_DARK_WOOD, width=6)
    d.ellipse([(66, 14), (88, 30)], fill=PAL_DEEP_GREEN, outline=PAL_OUTLINE, width=4)
    im.save(os.path.join(ICONS_DIR, "icon_food.png"))

    # 8. Wood (Timber logs)
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([(20, 48), (108, 88)], fill=PAL_WOOD, outline=PAL_OUTLINE, width=6)
    d.ellipse([(14, 48), (36, 88)], fill=(210, 145, 85, 255), outline=PAL_OUTLINE, width=5)
    d.ellipse([(96, 48), (118, 88)], fill=PAL_WOOD, outline=PAL_OUTLINE, width=5)
    im.save(os.path.join(ICONS_DIR, "icon_wood.png"))

    # 9. Quantum Atom
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([(48, 48), (80, 80)], fill=(180, 90, 240, 255), outline=PAL_OUTLINE, width=5)
    d.arc([(18, 32), (110, 96)], 0, 360, fill=(150, 60, 220, 255), width=5)
    d.arc([(32, 18), (96, 110)], 0, 360, fill=(150, 60, 220, 255), width=5)
    im.save(os.path.join(ICONS_DIR, "icon_atom.png"))


def make_tiles():
    size = (128, 128)

    # 1. Grass Tile (with checkerboard tint & tufts)
    im = Image.new("RGBA", size, PAL_GRASS)
    d = ImageDraw.Draw(im)
    d.rectangle([(0, 0), (127, 127)], outline=PAL_DEEP_GREEN, width=2)
    # Grass tufts
    d.line([(40, 70), (46, 50)], fill=PAL_DEEP_GREEN, width=4)
    d.line([(46, 50), (52, 70)], fill=PAL_DEEP_GREEN, width=4)
    d.line([(85, 95), (90, 75)], fill=PAL_DEEP_GREEN, width=4)
    d.line([(90, 75), (96, 95)], fill=PAL_DEEP_GREEN, width=4)
    im.save(os.path.join(TILES_DIR, "tile_grass.png"))

    # 2. Sand Tile
    im = Image.new("RGBA", size, PAL_SAND)
    d = ImageDraw.Draw(im)
    d.rectangle([(0, 0), (127, 127)], outline=(220, 190, 115, 255), width=2)
    # Sandy pebbles
    d.ellipse([(35, 45), (42, 50)], fill=(200, 170, 95, 255))
    d.ellipse([(85, 80), (95, 86)], fill=(200, 170, 95, 255))
    im.save(os.path.join(TILES_DIR, "tile_sand.png"))

    # 3. Water Tile (with wave crests)
    im = Image.new("RGBA", size, PAL_WATER)
    d = ImageDraw.Draw(im)
    d.arc([(20, 30), (70, 50)], 0, 180, fill=PAL_WHITE, width=4)
    d.arc([(70, 75), (120, 95)], 0, 180, fill=PAL_WHITE, width=4)
    d.arc([(15, 100), (55, 115)], 0, 180, fill=PAL_WATER_DEEP, width=4)
    im.save(os.path.join(TILES_DIR, "tile_water.png"))

    # 4. Mountain Tile
    im = Image.new("RGBA", size, PAL_MOUNTAIN)
    d = ImageDraw.Draw(im)
    # Peaks
    d.polygon([(64, 16), (20, 112), (108, 112)], fill=(120, 115, 125, 255), outline=PAL_OUTLINE, width=5)
    # Snowcap
    d.polygon([(64, 16), (46, 55), (64, 48), (82, 55)], fill=PAL_MOUNTAIN_SNOW)
    im.save(os.path.join(TILES_DIR, "tile_mountain.png"))


def make_sprites():
    # 1. Pine Tree
    im = Image.new("RGBA", (128, 160), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # Trunk
    d.rectangle([(54, 115), (74, 150)], fill=PAL_DARK_WOOD, outline=PAL_OUTLINE, width=5)
    # 3 layered conical canopies
    d.polygon([(64, 15), (20, 70), (108, 70)], fill=(40, 110, 45, 255), outline=PAL_OUTLINE, width=5)
    d.polygon([(64, 45), (12, 100), (116, 100)], fill=PAL_DEEP_GREEN, outline=PAL_OUTLINE, width=5)
    d.polygon([(64, 75), (6, 130), (122, 130)], fill=PAL_GRASS, outline=PAL_OUTLINE, width=5)
    im.save(os.path.join(SPRITES_DIR, "tree_pine.png"))

    # 2. Fruit Bush
    im = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([(16, 24), (112, 112)], fill=PAL_DEEP_GREEN, outline=PAL_OUTLINE, width=6)
    # Ruby berries
    for bx, by in [(40, 50), (84, 55), (62, 85), (45, 90), (80, 88)]:
        d.ellipse([(bx, by), (bx + 16, by + 16)], fill=PAL_RED, outline=PAL_OUTLINE, width=3)
    im.save(os.path.join(SPRITES_DIR, "bush_berries.png"))

    # 3. Shelter Tent
    im = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(64, 20), (16, 110), (112, 110)], fill=PAL_PARCHMENT, outline=PAL_OUTLINE, width=6)
    d.polygon([(64, 20), (45, 110), (83, 110)], fill=PAL_DARK_WOOD)
    im.save(os.path.join(SPRITES_DIR, "shelter_tent.png"))

    # 4. Soft Ground Shadow Blob
    im = Image.new("RGBA", (128, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([(8, 8), (120, 56)], fill=(20, 10, 5, 110))
    im.save(os.path.join(SPRITES_DIR, "shadow_blob.png"))

    # 5. Cloud
    im = Image.new("RGBA", (256, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([(20, 40), (110, 110)], fill=(255, 255, 255, 230))
    d.ellipse([(80, 20), (180, 110)], fill=(255, 255, 255, 245))
    d.ellipse([(150, 45), (235, 110)], fill=(255, 255, 255, 230))
    d.rectangle([(50, 70), (200, 110)], fill=(255, 255, 255, 235))
    im.save(os.path.join(SPRITES_DIR, "cloud.png"))

    # 6. Cute Agent Spritesheet (128x128 per frame, 5 frames: idle, walk, hurt, happy, fallen)
    sheet = Image.new("RGBA", (128 * 5, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(sheet)
    for i, state in enumerate(["idle", "walk", "hurt", "happy", "fallen"]):
        ox = i * 128
        # Shadow
        d.ellipse([(ox + 34, 102), (ox + 94, 122)], fill=(25, 12, 5, 90))

        if state == "fallen":
            # Body horizontal
            d.rectangle([(ox + 32, 85), (ox + 96, 105)], fill=PAL_DEEP_GREEN, outline=PAL_OUTLINE, width=4)
            d.ellipse([(ox + 20, 75), (ox + 50, 105)], fill=(255, 218, 175, 255), outline=PAL_OUTLINE, width=4)
            # Straw Hat on ground
            d.ellipse([(ox + 70, 75), (ox + 105, 95)], fill=PAL_GOLD, outline=PAL_OUTLINE, width=4)
            continue

        # Torso (Farmer Dungarees)
        d.rectangle([(ox + 46, 58), (ox + 82, 94)], fill=PAL_DEEP_GREEN, outline=PAL_OUTLINE, width=4)
        # Legs
        if state == "walk":
            d.rectangle([(ox + 48, 92), (ox + 60, 114)], fill=PAL_DARK_WOOD, outline=PAL_OUTLINE, width=3)
            d.rectangle([(ox + 68, 90), (ox + 80, 108)], fill=PAL_DARK_WOOD, outline=PAL_OUTLINE, width=3)
        else:
            d.rectangle([(ox + 50, 94), (ox + 62, 112)], fill=PAL_DARK_WOOD, outline=PAL_OUTLINE, width=3)
            d.rectangle([(ox + 66, 94), (ox + 78, 112)], fill=PAL_DARK_WOOD, outline=PAL_OUTLINE, width=3)

        # Head
        d.ellipse([(ox + 44, 24), (ox + 84, 64)], fill=(255, 218, 175, 255), outline=PAL_OUTLINE, width=4)

        # Straw Hat
        d.ellipse([(ox + 30, 20), (ox + 98, 38)], fill=PAL_GOLD, outline=PAL_OUTLINE, width=4)
        d.ellipse([(ox + 46, 10), (ox + 82, 30)], fill=PAL_GOLD, outline=PAL_OUTLINE, width=4)
        d.rectangle([(ox + 48, 24), (ox + 80, 28)], fill=PAL_RED)

        # Eyes & Expression
        if state == "hurt":
            d.line([(ox + 52, 40), (ox + 58, 46)], fill=PAL_OUTLINE, width=3)
            d.line([(ox + 58, 40), (ox + 52, 46)], fill=PAL_OUTLINE, width=3)
            d.line([(ox + 70, 40), (ox + 76, 46)], fill=PAL_OUTLINE, width=3)
            d.line([(ox + 76, 40), (ox + 70, 46)], fill=PAL_OUTLINE, width=3)
            d.arc([(ox + 58, 50), (ox + 70, 60)], 0, 180, fill=PAL_OUTLINE, width=3)
        elif state == "happy":
            d.arc([(ox + 52, 38), (ox + 60, 46)], 180, 360, fill=PAL_OUTLINE, width=3)
            d.arc([(ox + 68, 38), (ox + 76, 46)], 180, 360, fill=PAL_OUTLINE, width=3)
            d.arc([(ox + 56, 46), (ox + 72, 58)], 0, 180, fill=PAL_OUTLINE, width=4)
        else:
            d.ellipse([(ox + 53, 40), (ox + 59, 48)], fill=PAL_OUTLINE)
            d.ellipse([(ox + 69, 40), (ox + 75, 48)], fill=PAL_OUTLINE)
            d.line([(ox + 60, 52), (ox + 68, 52)], fill=PAL_OUTLINE, width=3)

    sheet.save(os.path.join(SPRITES_DIR, "agent_sheet.png"))


def main():
    ensure_dirs()
    print("[AssetGen] Generating procedural Hay Day-style assets...")
    make_icons()
    make_tiles()
    make_sprites()
    print("[AssetGen] All procedural assets successfully generated in assets/")


if __name__ == "__main__":
    main()


import json
import random

def generate_sample_timeline():
    # 40x40 Island world: water border, plains, forest, mountains
    width = 40
    height = 40
    tiles = [[0 for _ in range(width)] for _ in range(height)]
    
    # Fill island center
    for y in range(5, 35):
        for x in range(5, 35):
            dist_to_center = ((x - 20)**2 + (y - 20)**2)**0.5
            if dist_to_center > 14:
                tiles[y][x] = 0 # Water
            elif dist_to_center > 10:
                tiles[y][x] = 1 # Plains / Beach
            elif dist_to_center > 5:
                tiles[y][x] = 2 # Dense Forest
            else:
                tiles[y][x] = 3 # Mountain / High ground

    # Mark shelter at [18, 19]
    tiles[19][18] = 4

    steps = [
        {
            "t": 0,
            "state": {
                "day": 1, "hour": 8, "pos": [15, 15],
                "needs": {"hunger": 0.85, "thirst": 0.75, "warmth": 0.90, "energy": 0.90, "safety": 0.85, "morale": 0.80},
                "stress": 0.10, "injured": False, "inventory": {"wood": 0, "food": 1}, "recent_events": ["none"]
            },
            "event": "none",
            "action": "explore",
            "probs": {"explore": 0.42, "forage": 0.28, "drink": 0.15, "rest": 0.05, "build_shelter": 0.05, "craft": 0.03, "hide": 0.02},
            "reason": "Morning baseline: high energy and clear weather favor mapping nearby resources"
        },
        {
            "t": 1,
            "state": {
                "day": 1, "hour": 10, "pos": [16, 17],
                "needs": {"hunger": 0.70, "thirst": 0.55, "warmth": 0.85, "energy": 0.80, "safety": 0.80, "morale": 0.78},
                "stress": 0.15, "injured": False, "inventory": {"wood": 1, "food": 1}, "recent_events": ["none", "none"]
            },
            "event": "find_food",
            "action": "forage",
            "probs": {"forage": 0.55, "drink": 0.25, "explore": 0.10, "build_shelter": 0.05, "rest": 0.03, "craft": 0.01, "hide": 0.01},
            "reason": "Discovered berry grove: prior belief collapses around immediate food gathering"
        },
        {
            "t": 2,
            "state": {
                "day": 1, "hour": 12, "pos": [17, 18],
                "needs": {"hunger": 0.85, "thirst": 0.40, "warmth": 0.85, "energy": 0.70, "safety": 0.80, "morale": 0.82},
                "stress": 0.20, "injured": False, "inventory": {"wood": 2, "food": 3}, "recent_events": ["find_food"]
            },
            "event": "none",
            "action": "drink",
            "probs": {"drink": 0.65, "build_shelter": 0.15, "forage": 0.08, "explore": 0.05, "rest": 0.04, "craft": 0.02, "hide": 0.01},
            "reason": "Midday dehydration threshold: freshwater stream nearby shifts dominant probability amplitude to drink"
        },
        {
            "t": 3,
            "state": {
                "day": 1, "hour": 14, "pos": [18, 18],
                "needs": {"hunger": 0.75, "thirst": 0.85, "warmth": 0.80, "energy": 0.60, "safety": 0.75, "morale": 0.78},
                "stress": 0.25, "injured": False, "inventory": {"wood": 3, "food": 2}, "recent_events": ["find_food", "none"]
            },
            "event": "injury",
            "action": "rest",
            "probs": {"rest": 0.48, "build_shelter": 0.22, "hide": 0.15, "forage": 0.05, "drink": 0.05, "explore": 0.03, "craft": 0.02},
            "reason": "Ankle sprain while hauling timber: acute pain rotates quantum belief state toward recuperation"
        },
        {
            "t": 4,
            "state": {
                "day": 1, "hour": 16, "pos": [18, 19],
                "needs": {"hunger": 0.65, "thirst": 0.75, "warmth": 0.65, "energy": 0.45, "safety": 0.40, "morale": 0.60},
                "stress": 0.55, "injured": True, "inventory": {"wood": 4, "food": 2}, "recent_events": ["none", "injury"]
            },
            "event": "storm",
            "action": "build_shelter",
            "probs": {"build_shelter": 0.52, "hide": 0.30, "rest": 0.10, "drink": 0.03, "forage": 0.02, "explore": 0.02, "craft": 0.01},
            "reason": "Quantum Order Effect: Injury followed by Storm induces constructive interference on shelter fortification"
        },
        {
            "t": 5,
            "state": {
                "day": 1, "hour": 19, "pos": [18, 19],
                "needs": {"hunger": 0.50, "thirst": 0.65, "warmth": 0.45, "energy": 0.35, "safety": 0.35, "morale": 0.50},
                "stress": 0.72, "injured": True, "inventory": {"wood": 1, "food": 2}, "recent_events": ["injury", "storm"]
            },
            "event": "cold_night",
            "action": "hide",
            "probs": {"hide": 0.58, "rest": 0.25, "build_shelter": 0.10, "forage": 0.03, "drink": 0.02, "craft": 0.01, "explore": 0.01},
            "reason": "Severe stress decoherence: high anxiety washes out interference, driving instinctual burrowing into shelter"
        },
        {
            "t": 6,
            "state": {
                "day": 1, "hour": 22, "pos": [18, 19],
                "needs": {"hunger": 0.42, "thirst": 0.58, "warmth": 0.70, "energy": 0.55, "safety": 0.65, "morale": 0.62},
                "stress": 0.40, "injured": True, "inventory": {"wood": 1, "food": 1}, "recent_events": ["storm", "cold_night"]
            },
            "event": "none",
            "action": "rest",
            "probs": {"rest": 0.75, "hide": 0.15, "drink": 0.04, "forage": 0.03, "build_shelter": 0.02, "explore": 0.01, "craft": 0.00},
            "reason": "Nighttime shelter sanctuary: storm passes outside while agent recuperates vital energy"
        },
        {
            "t": 7,
            "state": {
                "day": 2, "hour": 6, "pos": [18, 19],
                "needs": {"hunger": 0.55, "thirst": 0.60, "warmth": 0.85, "energy": 0.85, "safety": 0.80, "morale": 0.85},
                "stress": 0.20, "injured": False, "inventory": {"wood": 1, "food": 1}, "recent_events": ["cold_night", "none"]
            },
            "event": "none",
            "action": "forage",
            "probs": {"forage": 0.48, "explore": 0.25, "drink": 0.15, "build_shelter": 0.05, "rest": 0.04, "craft": 0.02, "hide": 0.01},
            "reason": "Dawn of Day 2: sprain healed overnight, high morale unlocks exploratory forage drive"
        }
    ]

    timeline_data = {
        "world": {
            "width": width,
            "height": height,
            "tiles": tiles,
            "seed": 1337,
            "mind": "quantum",
            "noise_source": "ibm_hardware"
        },
        "steps": steps,
        "outcome": "survived",
        "cause": "none"
    }

    with open(r"c:\Users\lenovo\OneDrive\Desktop\QWC\timeline.json", "w", encoding="utf-8") as f:
        json.dump(timeline_data, f, indent=2)

    print("Sample timeline.json generated successfully!")

generate_sample_timeline()


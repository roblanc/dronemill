#!/usr/bin/env python3
"""
Title generator for timeless ambience channel.
Generates titles matching existing patterns: cosmic horror narrative, prehistoric/futuristic timestamp,
"You [verb]" present-tense, dream-nostalgic.

Usage:
    python3 gen-titles.py [count=30] [pattern=mixed|narrative|prehistoric|you|dream]

Output: one title per line to stdout. Pipe to file:
    python3 gen-titles.py 30 > titles.txt
"""

import random
import sys

# ── Pattern A: Cosmic Horror Narrative ──────────────────────────────────
SUBJECTS = [
    "He", "She", "They", "It", "Something", "Someone",
    "The Visitor", "The Figure", "The Watcher", "The Thing",
]

NARRATIVE_VERBS = [
    "Watched", "Waited", "Approached", "Listened", "Called Out",
    "Stepped Forward", "Whispered Back", "Was Standing", "Was Already There",
    "Came Through the Fog", "Rose From the Soil", "Hovered Above",
    "Knocked Twice", "Smiled Without Moving", "Knew My Name",
]

NARRATIVE_PLACES = [
    "Above the Road", "Beneath the Bed", "In the Parking Garage",
    "Behind the Door", "In the Laundromat", "Between the Trees",
    "Under the Stairs", "At the Lighthouse", "In the Basement",
    "On the Rooftop", "Beyond the Fence", "In the Hallway",
    "From the Attic", "Inside the Walls", "From the Lake",
    "Across the Field", "Through the Static", "From the Treeline",
]

NARRATIVE_HOOKS = [
    "{subject} {verb} {place}…",
    "{subject} {verb}, And No One Saw…",
    "{subject} {verb} While I Slept…",
    "When {subject} {verb} {place}…",
    "{subject} Was Already Waiting {place}…",
    "I Heard {subject} {verb} {place}…",
    "Something {verb} {place}, Then Stopped…",
]

HORROR_SUFFIXES = [
    "1 Hour of Cosmic Horror Ambience",
    "1 Hour of Lovecraftian Ambience",
    "Cosmic Horror Ambient Music HD",
    "1 Hour Dark Ambient",
    "Lovecraftian Ambience",
    "1 Hour of Low Altitude Cosmic Horror Ambience",
    "1 Hour of Pure Cosmic Horror",
]

# ── Pattern B: Prehistoric / Futuristic Timestamp ───────────────────────
TIMESTAMP_PLACES = [
    "Mammoth Steppe", "River of Giants", "Plesiosaur Lake",
    "Dinosaur Lake at Dusk", "The Lost Sea", "The Last Pangean Coast",
    "The Sunken Forest", "Cretaceous River Mouth", "The Tar Pits",
    "Elephants of Jupiter", "Dinosaurs of Saturn", "Last Witness of Liberty",
    "The Forgotten Spaceport", "New Eden", "The Hollow Moon",
    "Cathedral of Tomorrow", "City Beneath the Ice",
]

TIMESTAMPS = [
    "65 Million Years Ago", "150 Million Years Ago", "18,500 BC",
    "2912 BC", "200 Million Years Ago", "12,000 BC",
    "2999", "3024 AD", "4501 AD", "8800 AD",
]

# ── Pattern C: "You [verb]" Present-Tense Cozy ──────────────────────────
YOU_VERBS = [
    "Found", "Sleep In", "Drift Across", "Fall Asleep In",
    "Wander Through", "Rest Beneath", "Dream Inside", "Wake Inside",
]

YOU_PLACES = [
    "The Perfect Tomorrow", "The City of Tomorrow",
    "The Forest of the City", "The Moon's Gentle Gravity",
    "The Garden Beneath the Stars", "The Cathedral of Lost Signals",
    "The Library at the End of Time", "The Ocean That Sings",
    "A Wooden Canoe Across the Prehistoric Swamp",
    "The Quiet Side of the Galaxy",
]

# ── Pattern D: Dream-Nostalgic Futurism ─────────────────────────────────
DREAM_TEMPLATES = [
    "The {noun} That Dreamed Us Into Morning",
    "Tomorrow Waits Quietly In Your {noun}",
    "The Future We Found While {gerund}",
    "The Place Where Dreams And {plural} Meet",
    "A Future Where We All Slept on The {noun}",
    "The {adj} Night in the City Where the {noun} Never Lets Go",
    "When the {noun} Forgot Our Names",
    "We Were Always Going to End Up in This {noun}",
]

DREAM_NOUNS = ["City", "Moon", "Sky", "Sea", "Mountain", "Library", "Forest", "Garden", "Tower"]
DREAM_PLURALS = ["Futures", "Memories", "Tomorrows", "Stars", "Echoes", "Signals"]
DREAM_GERUNDS = ["Dreaming", "Sleeping", "Falling", "Listening", "Drifting", "Waiting"]
DREAM_ADJ = ["Quiet", "Endless", "Gentle", "Final", "Last", "Forgotten"]


def gen_narrative():
    template = random.choice(NARRATIVE_HOOKS)
    title = template.format(
        subject=random.choice(SUBJECTS),
        verb=random.choice(NARRATIVE_VERBS),
        place=random.choice(NARRATIVE_PLACES),
    )
    suffix = random.choice(HORROR_SUFFIXES)
    return f"{title} | {suffix}"


def gen_prehistoric():
    place = random.choice(TIMESTAMP_PLACES)
    when = random.choice(TIMESTAMPS)
    return f"{place}, {when}"


def gen_you():
    verb = random.choice(YOU_VERBS)
    place = random.choice(YOU_PLACES)
    return f"You {verb} {place}"


def gen_dream():
    template = random.choice(DREAM_TEMPLATES)
    return template.format(
        noun=random.choice(DREAM_NOUNS),
        plural=random.choice(DREAM_PLURALS),
        gerund=random.choice(DREAM_GERUNDS),
        adj=random.choice(DREAM_ADJ),
    )


GENERATORS = {
    "narrative": gen_narrative,
    "prehistoric": gen_prehistoric,
    "you": gen_you,
    "dream": gen_dream,
}

# Distribution for "mixed" mode (matches existing channel ratio approximately)
MIXED_WEIGHTS = [
    ("narrative", 50),
    ("prehistoric", 20),
    ("you", 15),
    ("dream", 15),
]


def gen_mixed():
    population = []
    for name, weight in MIXED_WEIGHTS:
        population.extend([name] * weight)
    pattern = random.choice(population)
    return GENERATORS[pattern]()


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    mode = sys.argv[2] if len(sys.argv) > 2 else "mixed"

    seen = set()
    out = []
    attempts = 0
    while len(out) < count and attempts < count * 10:
        attempts += 1
        if mode == "mixed":
            title = gen_mixed()
        elif mode in GENERATORS:
            title = GENERATORS[mode]()
        else:
            print(f"Unknown mode: {mode}. Use: mixed|narrative|prehistoric|you|dream", file=sys.stderr)
            sys.exit(1)

        if title not in seen:
            seen.add(title)
            out.append(title)

    for t in out:
        print(t)


if __name__ == "__main__":
    main()

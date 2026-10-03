#!/usr/bin/env python3
"""Prepare no-API image generation briefs for Dronemill.

This does not call an image API. It writes:
  - output/image_generation_briefs.md
  - output/image_generation_briefs.json
  - images/inbox/<slug>.json sidecars

Generate images manually in ChatGPT/Antigravity, save each image as the
suggested filename in images/inbox/, and stock-manager.py will import metadata.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
INBOX = ROOT / "images" / "inbox"

LIMINAL_THEMES = [
    {
        "title": "the aquarium tunnel after closing",
        "profile": "poolrooms",
        "description": "poolrooms.txt",
        "visual": "a realistic aquarium tunnel in bright filtered daylight, curved glass walls, pale blue water light rippling over wet floors, no fish visible, no people, serene and spacious",
    },
    {
        "title": "the data center kept breathing",
        "profile": "server",
        "description": "library.txt",
        "visual": "a realistic data center with clean white architecture and cool daylight spilling through glass, endless server racks, polished floor reflections, cold aisle perspective, no people",
    },
    {
        "title": "the ferry terminal in the fog",
        "profile": "terminal",
        "description": "airport_terminal.txt",
        "visual": "a realistic ferry terminal in soft morning light, rows of plastic seats, fogged windows, pale water outside, one vending machine glow, no people",
    },
    {
        "title": "the tv studio after broadcast",
        "profile": "mall",
        "description": "empty_mall.txt",
        "visual": "a realistic television studio after the show, bright white cyclorama, dark cameras on tripods, glossy floor, inactive light panels, silent stage, no logos, no people",
    },
    {
        "title": "the funeral home waiting room",
        "profile": "mall",
        "description": "infinite_hotel.txt",
        "visual": "a realistic funeral home waiting room in soft daylight, beige couches, silk flowers, warm lamps, patterned carpet, one hallway receding into depth, no people",
    },
    {
        "title": "the bowling alley at 4am",
        "profile": "mall",
        "description": "empty_mall.txt",
        "visual": "a realistic bowling alley in bright clean daylight, polished lanes reflecting soft light, shoes abandoned neatly, score screens glowing unreadably, no people",
    },
    {
        "title": "the greenhouse lights never turned off",
        "profile": "mall",
        "description": "suburban_street.txt",
        "visual": "a realistic municipal greenhouse in bright morning light, wet concrete path, rows of plants under translucent glass, condensation on the panes, no people",
    },
    {
        "title": "the cruise ship corridor at midnight",
        "profile": "terminal",
        "description": "infinite_hotel.txt",
        "visual": "a realistic cruise ship passenger corridor in clean daylight, patterned carpet, repeating cabin doors, ocean light from windows, slight tilt, no people",
    },
    {
        "title": "the civic archive below the city",
        "profile": "mall",
        "description": "library.txt",
        "visual": "a realistic underground civic archive room with pale concrete and skylight spill, endless file shelves, beige boxes with no readable labels, dust in the air, no people",
    },
    {
        "title": "the rest stop beyond the highway",
        "profile": "terminal",
        "description": "suburban_street.txt",
        "visual": "a realistic empty highway rest stop at sunrise, picnic shelters, vending machines, warm asphalt, black trees beyond the lamps, no people",
    },
    {
        "title": "the indoor garden under the office tower",
        "profile": "mall",
        "description": "library.txt",
        "visual": "a realistic indoor corporate atrium garden in bright daylight, glass roof, potted trees, stone benches, elevator doors glowing softly, rain streaks on windows, no people",
    },
    {
        "title": "the laser tag arena without players",
        "profile": "backrooms",
        "description": "level_0.txt",
        "visual": "a realistic empty laser tag arena after closing, blacklight maze walls with brighter cyan accents, carpeted ramps, soft red and blue glow, fog machine residue, no logos, no people",
    },
    {
        "title": "the office copier room at dawn",
        "profile": "mall",
        "description": "library.txt",
        "visual": "a realistic empty office copier room in bright dawn, stacked paper trays, clean fluorescent panel, beige cabinets, a small window with blue morning light, no people",
    },
    {
        "title": "the spa reception under green light",
        "profile": "poolrooms",
        "description": "poolrooms.txt",
        "visual": "a realistic spa reception in bright natural light, tiled floor, pale green pool light from a side corridor, folded towels, quiet water reflections, no people",
    },
    {
        "title": "the planetarium lobby after the eclipse",
        "profile": "void",
        "description": "template.txt",
        "visual": "a realistic empty planetarium lobby after hours, circular ceiling, pale blue carpet, star projector display cases with unreadable plaques, soft cosmic light, no people",
    },
    {
        "title": "the bus depot beneath the overpass",
        "profile": "terminal",
        "description": "train_station.txt",
        "visual": "a realistic empty bus depot under a concrete overpass at dawn, wet pavement, parked buses in shadow, orange lights, fog at the far entrance, no people",
    },
    {
        "title": "the church basement after bingo night",
        "profile": "mall",
        "description": "classroom.txt",
        "visual": "a realistic empty church basement after a community event, folding tables, linoleum floor, coffee urns, bright fluorescent lights, stairwell door open, no people",
    },
    {
        "title": "the observation deck above the sleeping city",
        "profile": "terminal",
        "description": "airport_terminal.txt",
        "visual": "a realistic empty observation deck at dusk, floor-to-ceiling windows, coin binoculars, city lights far below, reflections on polished floor, no people",
    },
    {
        "title": "the car wash tunnel still dripping",
        "profile": "poolrooms",
        "description": "poolrooms.txt",
        "visual": "a realistic empty automatic car wash tunnel after closing, wet tiled floor, hanging strips, bright utility lights, water dripping, no car, no people",
    },
    {
        "title": "the municipal pool locker room",
        "profile": "poolrooms",
        "description": "poolrooms.txt",
        "visual": "a realistic municipal pool locker room, damp benches, pale blue lockers, fluorescent hum, puddles reflecting ceiling lights, corridor to pool glowing softly, no people",
    },
    {
        "title": "the storage warehouse with one light on",
        "profile": "mall",
        "description": "empty_mall.txt",
        "visual": "a realistic empty storage warehouse in bright overhead light, tall metal shelves, one fluorescent bay lit, concrete floor, distant loading door, no readable labels, no people",
    },
    {
        "title": "the basement cafeteria under renovation",
        "profile": "mall",
        "description": "classroom.txt",
        "visual": "a realistic empty basement cafeteria under renovation, stacked plastic chairs, exposed ceiling pipes, sunlit serving counter, dust sheets, no people",
    },
    {
        "title": "the covered market before morning",
        "profile": "mall",
        "description": "empty_mall.txt",
        "visual": "a realistic empty covered market before morning, closed stalls, tiled floor, metal shutters, soft skylight, one hanging bulb, no logos, no people",
    },
    {
        "title": "the clinic elevator opened by itself",
        "profile": "mall",
        "description": "infinite_hotel.txt",
        "visual": "a realistic empty medical clinic hallway in bright daylight, elevator doors open to darkness, pale green walls, polished floor reflections, no people",
    },
]

LOVECRAFTIAN_THEMES = [
    {
        "title": "The Black Tide Under the Lighthouse",
        "profile": "harbor",
        "visual": "a lonely lighthouse above a black cosmic tide, impossible waves reflecting faint violet stars",
    },
    {
        "title": "The Drowned Cathedral Beneath the Moon",
        "profile": "harbor",
        "visual": "a half-submerged gothic cathedral under moonlit water, stone spires disappearing into dark fog",
    },
    {
        "title": "The Sunken Ruins That Kept Breathing",
        "profile": "void",
        "visual": "ancient underwater ruins exhaling pale light from cracks, vast darkness around them",
    },
    {
        "title": "When the Village Heard the Wave Think",
        "profile": "harbor",
        "visual": "a coastal village facing an unnatural wall of water shaped like a sleeping mind",
    },
    {
        "title": "The Antarctic Shelf Opened at Midnight",
        "profile": "arctic",
        "visual": "an Antarctic ice shelf split open at night, faint red glow rising from the abyss below",
    },
    {
        "title": "The Basalt Shore Under Three Dead Suns",
        "profile": "harbor",
        "visual": "black basalt coastline under three dim suns, tide pools reflecting alien constellations",
    },
    {
        "title": "The Ship's Wheel Turned by Itself",
        "profile": "harbor",
        "visual": "abandoned ship wheel on a ruined deck, ocean fog, unseen force turning it slowly",
    },
    {
        "title": "The Ribcage at the Bottom of the Sea",
        "profile": "void",
        "visual": "colossal rib bones on the abyssal seafloor glowing with bioluminescent blue light",
    },
    {
        "title": "The Pier Where the Fog Learned Your Name",
        "profile": "harbor",
        "visual": "an old wooden pier vanishing into thick fog, distant lights beneath the water",
    },
    {
        "title": "The Icebound Ghost of HMS Erebus",
        "profile": "arctic",
        "visual": "a frozen ghost ship trapped in pack ice under green aurora and heavy black clouds",
    },
    {
        "title": "The Fractal Cathedral in the Ice",
        "profile": "arctic",
        "visual": "ice cathedral with impossible fractal arches, blue light pulsing deep inside",
    },
    {
        "title": "The Glacier's Pulsing Vein",
        "profile": "arctic",
        "visual": "a glacier with a glowing crimson vein beneath transparent ice, prehistoric bones nearby",
    },
    {
        "title": "The Signal Above the Empty Road",
        "profile": "terminal",
        "visual": "an empty desert road at night, low hovering radio towers pulling light from the sky",
    },
    {
        "title": "The Parking Garage Below the Wrong Moon",
        "profile": "mall",
        "visual": "underground parking garage with wet concrete, fluorescent hum, a huge moon visible through the ceiling",
    },
    {
        "title": "The City Looked Up and Went Quiet",
        "profile": "mall",
        "visual": "empty city avenue at 3am, all windows reflecting the same impossible shape in the sky",
    },
    {
        "title": "The Moon That Answered Back",
        "profile": "void",
        "visual": "astronaut standing on a grey lunar plain, a dark eye-like crater opening in the distance",
    },
    {
        "title": "The Door in the Pink Wilderness",
        "profile": "void",
        "visual": "pink alien wilderness with one black rectangular doorway standing alone among strange plants",
    },
    {
        "title": "The Cathedral of the Cosmos Went Dark",
        "profile": "void",
        "visual": "vast space cathedral floating among stars, interior lights extinguished except one altar glow",
    },
    {
        "title": "The Windy Citadel at the End of Sleep",
        "profile": "arctic",
        "visual": "snow-covered cliffside citadel in violent wind, warm windows far above an endless valley",
    },
    {
        "title": "The Red Megacity with No People",
        "profile": "mall",
        "visual": "empty futuristic megacity in red fog, stacked towers, no traffic, no humans",
    },
    {
        "title": "The Alien Lake Beneath Twin Moons",
        "profile": "harbor",
        "visual": "still alien lake under two moons, black reeds, faint geometric ripples spreading outward",
    },
    {
        "title": "The Gardened Machine Kept Growing",
        "profile": "arctic",
        "visual": "overgrown biomechanical garden, huge silent machine covered in vines and pale flowers",
    },
    {
        "title": "The Last Train Never Arrived",
        "profile": "terminal",
        "visual": "empty train platform at night, fog in the tunnel, arrival sign showing impossible symbols",
    },
    {
        "title": "The Laundromat in the Wrong Dimension",
        "profile": "mall",
        "visual": "empty laundromat at midnight, spinning machines full of dark water and tiny stars",
    },
]

POSTHUMAN_THEMES = [
    {
        "title": "The City Where the Gardens Won",
        "profile": "mall",
        "description": "library.txt",
        "visual": "a clean post-human city street overtaken by curated gardens, glass towers covered in vines, soft daylight, no decay, no people",
    },
    {
        "title": "The Valley After the Machines Left",
        "profile": "arctic",
        "description": "suburban_street.txt",
        "visual": "a vast green valley with abandoned clean white machine towers slowly covered by moss, morning fog, peaceful post-human scale, no people",
    },
    {
        "title": "The Airport That Became a Forest",
        "profile": "mall",
        "description": "airport_terminal.txt",
        "visual": "an empty airport concourse transformed into an indoor forest, saplings growing between polished tiles, skylights glowing with morning sun, no people",
    },
    {
        "title": "The Apartment Blocks Under Summer Moss",
        "profile": "mall",
        "description": "suburban_street.txt",
        "visual": "quiet post-human apartment blocks covered in summer moss and balcony gardens, warm afternoon haze, empty courtyards, no people",
    },
]

PREHISTORIC_THEMES = [
    {
        "title": "The Prehistoric River at Dawn",
        "profile": "harbor",
        "description": "suburban_street.txt",
        "visual": "a wide prehistoric river at dawn, mist above warm water, giant fern banks, distant gentle silhouettes of ancient animals, no close-up creatures",
    },
    {
        "title": "The Giant Fern Lake",
        "profile": "harbor",
        "description": "poolrooms.txt",
        "visual": "a still ancient lake surrounded by giant ferns and cycads, warm mist, low sun, distant sauropod silhouettes partly hidden by haze",
    },
    {
        "title": "The Mammoth Steppe Before Snow",
        "profile": "arctic",
        "description": "suburban_street.txt",
        "visual": "a wide mammoth steppe before snowfall, pale grasses, distant woolly mammoths as small silhouettes, cold blue morning, no humans",
    },
    {
        "title": "The Jurassic Treehouse Without Builders",
        "profile": "mall",
        "description": "library.txt",
        "visual": "a strange empty wooden treehouse village woven through massive prehistoric trees, soft sunlight, ancient ferns below, no people",
    },
]

SOFT_SCIFI_THEMES = [
    {
        "title": "The Archive of Tomorrow's Weather",
        "profile": "server",
        "description": "library.txt",
        "visual": "a bright futuristic weather archive, transparent display walls without readable text, cloud chambers, pale floors, soft blue daylight, no people",
    },
    {
        "title": "The Quiet Beach on Europa",
        "profile": "arctic",
        "description": "template.txt",
        "visual": "a calm icy beach beneath Jupiter in the sky, smooth frozen waves, warm station lights far away, no people, peaceful science fiction atmosphere",
    },
    {
        "title": "The Floating Greenhouse Above Saturn",
        "profile": "poolrooms",
        "description": "poolrooms.txt",
        "visual": "a serene orbital greenhouse with glass walkways, plants growing under soft artificial sun, Saturn visible through curved windows, no people",
    },
    {
        "title": "The Moon Garden Before Morning",
        "profile": "void",
        "description": "template.txt",
        "visual": "a quiet lunar garden under a transparent dome, pale flowers, soft Earthlight, empty white paths, distant sleeping habitat modules, no people",
    },
]

WEIRD_MUNDANE_THEMES = [
    {
        "title": "The Furniture Store After the Power Flickered",
        "profile": "mall",
        "description": "empty_mall.txt",
        "visual": "a realistic empty furniture store after closing, staged living rooms in rows, one ceiling light flickering, polished floor, no brands, no people",
    },
    {
        "title": "The Hotel Breakfast Room at 5am",
        "profile": "mall",
        "description": "infinite_hotel.txt",
        "visual": "a realistic empty hotel breakfast room before sunrise, cereal dispensers, plastic chairs, coffee machines, pale window light, no readable labels, no people",
    },
    {
        "title": "The School Gym After the Dance",
        "profile": "mall",
        "description": "classroom.txt",
        "visual": "a realistic empty school gym after a dance, folded tables, balloons on the floor, basketball hoops above, fluorescent lights, no people",
    },
    {
        "title": "The DMV Waiting Room After Closing",
        "profile": "mall",
        "description": "empty_mall.txt",
        "visual": "a realistic empty DMV waiting room after closing, rows of plastic chairs, ticket counter with no readable numbers, pale fluorescent light, no people",
    },
]

MYTHIC_CALM_THEMES = [
    {
        "title": "The Temple Under the Still Water",
        "profile": "poolrooms",
        "description": "poolrooms.txt",
        "visual": "a calm submerged stone temple visible beneath perfectly still clear water, sunbeams, pale columns, no people, no creatures",
    },
    {
        "title": "The Desert Observatory Before Sunrise",
        "profile": "void",
        "description": "library.txt",
        "visual": "a quiet desert observatory before sunrise, old telescopes, pale stone terraces, stars fading above, no people",
    },
    {
        "title": "The Garden of Sleeping Statues",
        "profile": "mall",
        "description": "template.txt",
        "visual": "a peaceful abandoned garden of giant stone statues partly covered in flowers, morning mist, no people, no fantasy armor",
    },
    {
        "title": "The Museum of Extinct Sunsets",
        "profile": "mall",
        "description": "library.txt",
        "visual": "a bright empty museum hall with large window-like sunset installations, polished stone floor, soft amber light, no readable plaques, no people",
    },
]

ALIEN_TRAVEL_THEMES = [
    {
        "title": "The Orchard Under the Glass Moon",
        "profile": "harbor",
        "description": "suburban_street.txt",
        "visual": "a quiet alien orchard under a huge glass moon, pale fruit trees in geometric rows, irrigation channels reflecting sunrise, no people",
    },
    {
        "title": "The Tourist Platform on Kepler 186f",
        "profile": "terminal",
        "description": "airport_terminal.txt",
        "visual": "an empty scenic tourist platform on an alien planet, safety rails, wide valley of blue vegetation, twin shadows, no people",
    },
    {
        "title": "The Red Dunes Visitor Center",
        "profile": "terminal",
        "description": "train_station.txt",
        "visual": "a quiet visitor center on red alien dunes, panoramic windows, empty benches, distant ringed planet, soft morning light, no people",
    },
    {
        "title": "The Alien Lake Beneath Twin Moons",
        "profile": "harbor",
        "description": "poolrooms.txt",
        "visual": "a still alien lake under two moons, black reeds, faint geometric ripples spreading outward, peaceful travel documentary mood, no people",
    },
]

LOVECRAFTIAN_STYLE = (
    "cinematic cosmic horror ambience cover art, 16:9, no text, no logo, no people close-up, "
    "wide establishing shot, analog horror texture, photorealistic cinematic still, atmospheric fog, "
    "dark but readable composition, strong simple silhouette, YouTube thumbnail clarity, slightly degraded film scan"
)

LIMINAL_STYLE = (
    "photorealistic bright liminal or surreal architecture cover, 16:9, no text, no logo, no people, no visible monster, "
    "wide static architectural shot, monumental real-world location, strong one-point perspective or clean symmetry, "
    "large empty negative space, high-key daylight or soft sunrise light, pale surfaces, subtle haze or dust, analog camcorder still, "
    "natural colors, slightly eerie but believable, YouTube thumbnail clarity"
)

SPECULATIVE_STYLE = (
    "photorealistic speculative ambient cover, 16:9, no text, no logo, no people, wide quiet worldbuilding shot, "
    "calm but strange atmosphere, elegant composition, natural cinematic daylight, rich but restrained color palette, "
    "clear subject silhouette, large negative space, high-resolution YouTube thumbnail clarity, realistic materials and scale"
)

PREHISTORIC_STYLE = (
    "photorealistic prehistoric ambient cover, 16:9, no text, no logo, no people, wide natural landscape shot, "
    "ancient Earth atmosphere, soft mist, realistic animals only as distant scale silhouettes, documentary clarity, "
    "warm natural light, calm immersive composition, high-resolution YouTube thumbnail clarity"
)

WEIRD_MUNDANE_STYLE = (
    "photorealistic weird mundane ambient cover, 16:9, no text, no logo, no people, realistic empty everyday place, "
    "bright liminal lighting, clean readable composition, subtle unease, analog camcorder still, large negative space, "
    "believable real-world materials, high-resolution YouTube thumbnail clarity"
)

MYTHIC_CALM_STYLE = (
    "photorealistic calm mythic ambient cover, 16:9, no text, no logo, no people, quiet monumental place, "
    "ancient but believable materials, soft natural light, serene atmosphere, no battle, no dramatic fantasy action, "
    "wide establishing shot, large negative space, high-resolution YouTube thumbnail clarity"
)

NEGATIVE = (
    "avoid readable text, watermark, logo, gore, cartoon style, low resolution, blurry subject, "
    "oversaturated neon, cute fantasy, busy collage, dark noir look, epic fantasy concept art, dramatic creature close-up"
)


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:72].strip("-")


def prompt_for(brief: dict, style: str) -> str:
    style_text = {
        "liminal": LIMINAL_STYLE,
        "lovecraftian": LOVECRAFTIAN_STYLE,
        "posthuman": SPECULATIVE_STYLE,
        "prehistoric": PREHISTORIC_STYLE,
        "soft_scifi": SPECULATIVE_STYLE,
        "weird_mundane": WEIRD_MUNDANE_STYLE,
        "mythic_calm": MYTHIC_CALM_STYLE,
        "alien_travel": SPECULATIVE_STYLE,
    }[style]
    return f"{brief['visual']}. {style_text}. {NEGATIVE}."


def title_suffix_for(style: str) -> str:
    return {
        "liminal": "1 Hour Liminal Space Ambience",
        "lovecraftian": "Cosmic Horror Ambience",
        "posthuman": "1 Hour Post-Human Ambient World",
        "prehistoric": "1 Hour Prehistoric Ambient World",
        "soft_scifi": "1 Hour Soft Sci-Fi Ambience",
        "weird_mundane": "1 Hour Weird Liminal Ambience",
        "mythic_calm": "1 Hour Mythic Ambient World",
        "alien_travel": "1 Hour Alien World Ambience",
    }[style]


def primary_tag_for(style: str) -> str:
    return {
        "liminal": "liminal space",
        "lovecraftian": "cosmic horror",
        "posthuman": "post-human ambience",
        "prehistoric": "prehistoric ambience",
        "soft_scifi": "soft sci-fi ambience",
        "weird_mundane": "liminal space",
        "mythic_calm": "mythic ambience",
        "alien_travel": "alien world ambience",
    }[style]


def secondary_tag_for(style: str) -> str:
    return {
        "liminal": "dreamcore",
        "lovecraftian": "lovecraftian ambience",
        "posthuman": "future nature",
        "prehistoric": "ancient earth",
        "soft_scifi": "speculative ambience",
        "weird_mundane": "weirdcore",
        "mythic_calm": "ancient ambience",
        "alien_travel": "planetary ambience",
    }[style]


def themes_for(style: str) -> list[dict]:
    return {
        "liminal": LIMINAL_THEMES,
        "lovecraftian": LOVECRAFTIAN_THEMES,
        "posthuman": POSTHUMAN_THEMES,
        "prehistoric": PREHISTORIC_THEMES,
        "soft_scifi": SOFT_SCIFI_THEMES,
        "weird_mundane": WEIRD_MUNDANE_THEMES,
        "mythic_calm": MYTHIC_CALM_THEMES,
        "alien_travel": ALIEN_TRAVEL_THEMES,
    }[style]


def select_themes(style: str, count: int) -> list[tuple[str, dict]]:
    if style != "mixed":
        themes = themes_for(style)
        return [(style, item) for item in themes[: max(1, min(count, len(themes)))]]

    lanes = ["lovecraftian", "liminal", "posthuman", "prehistoric", "soft_scifi", "weird_mundane"]
    cursors = {lane: 0 for lane in lanes}
    selected: list[tuple[str, dict]] = []
    for idx in range(max(1, count)):
        lane = lanes[idx % len(lanes)]
        lane_themes = themes_for(lane)
        item = lane_themes[cursors[lane] % len(lane_themes)]
        cursors[lane] += 1
        selected.append((lane, item))
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=24)
    parser.add_argument(
        "--style",
        choices=[
            "liminal",
            "lovecraftian",
            "posthuman",
            "prehistoric",
            "soft_scifi",
            "weird_mundane",
            "mythic_calm",
            "alien_travel",
            "mixed",
        ],
        default="liminal",
    )
    parser.add_argument("--start-index", type=int, default=1)
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    INBOX.mkdir(parents=True, exist_ok=True)

    briefs = []
    for offset, (style, item) in enumerate(select_themes(args.style, args.count)):
        idx = args.start_index + offset
        slug = f"{idx:03d}_{slugify(item['title'])}"
        image_name = f"{slug}.png"
        sidecar = {
            "title": f"{item['title']} | {title_suffix_for(style)}",
            "description": item.get("description", "template.txt"),
            "audio_profile": item["profile"],
            "visual_style": style,
            "content_lane": style,
            "tags": [
                primary_tag_for(style),
                "dark ambient",
                "sleep ambient",
                secondary_tag_for(style),
                f"{item['profile']} ambience",
                "timeless ambience",
            ],
            "prompt": prompt_for(item, style),
        }
        (INBOX / f"{slug}.json").write_text(json.dumps(sidecar, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        briefs.append({
            "index": idx,
            "image_file": image_name,
            **sidecar,
        })

    (OUT / "image_generation_briefs.json").write_text(json.dumps(briefs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    prompt_lines = [
        "# Dronemill UI Image Prompts",
        "# Used by scripts/ui-image-worker.sh, antigravity-image-worker.js, and chatgpt-image-worker.js.",
        "",
    ]
    for brief in briefs:
        prompt_lines.append(f"--- Image {brief['image_file']} ---")
        prompt_lines.append(brief["prompt"])
        prompt_lines.append("")
    (OUT / "ui_image_prompts.txt").write_text("\n".join(prompt_lines), encoding="utf-8")

    lines = [
        "# Dronemill Image Generation Briefs",
        "",
        "Save each generated image into `images/inbox/` using the exact filename shown.",
        "The matching `.json` sidecar has already been written there.",
        "",
    ]
    for brief in briefs:
        lines.extend([
            f"## {brief['index']:03d}. {brief['title']}",
            "",
            f"Filename: `{brief['image_file']}`",
            f"Audio profile: `{brief['audio_profile']}`",
            "",
            "Prompt:",
            "",
            brief["prompt"],
            "",
        ])
    (OUT / "image_generation_briefs.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"wrote output/image_generation_briefs.md")
    print(f"wrote output/image_generation_briefs.json")
    print(f"wrote output/ui_image_prompts.txt")
    print(f"wrote {len(briefs)} sidecars in images/inbox/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

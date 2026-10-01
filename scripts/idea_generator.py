#!/usr/bin/env python3
"""
DroneMill Autonomous Concept & Idea Generator.
Generates unique, non-repeating titles, descriptions, image prompts, and sound design recipes
based on previous release history.
"""

import os
import sys
import json
import re
import random
import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HISTORY_FILE = os.path.join(ROOT, "output", "upload_history.json")
TRACKER_FILE = os.path.join(ROOT, ".generated_ideas_history.json")

# Thematic archetypes with rich poetic building blocks
THEMES = [
    {
        "category": "Maritime & Abyssal Horror",
        "places": ["the drowned sea wall", "the kelp cathedral", "the barnacle church", "the abyssal trench", "the salt archives", "the rusted lighthouse", "the tidal cavern", "the harbor of silent hulls"],
        "subjects": ["the keeper who never left", "the bell beneath the tide", "the cold light on the water", "the fathomless breathing", "the forgotten diving bell", "the midnight trawler"],
        "subgenres": ["maritime dread ambient", "abyssal ocean ambient", "dark coastal drone", "lovecraftian ocean horror"],
        "foley": ["27_wind_desolate.mp3", "28_aquarium.mp3", "34_cave_drip.mp3"],
        "roots": [43.65, 51.91, 58.27, 65.41], # F, G#, Bb, C
        "overlay": "fog-overlay.mp4",
        "overlay_opacity": 0.40,
        "tags": ["maritime horror", "oceanic dark", "lighthouse ambient", "abyssal", "cosmic dread"]
    },
    {
        "category": "Liminal Spaces & Night Transit",
        "places": ["the carpeted terminal lounge", "the 4 AM baggage carousel", "the flooded subway mezzanine", "the empty neon laundromat", "the hotel corridor on floor 13", "the night shift observatory"],
        "subjects": ["shoes off on the vintage carpet", "the announcement for a flight that never boarded", "the hum of the vending machine", "the flickering departures board", "the escalator that runs down forever"],
        "subgenres": ["liminal transit ambient", "empty terminal ambient", "mallsoft drone", "dreamcore soundscape"],
        "foley": ["02_airport_terminal.mp3", "07_train_station.mp3", "01_empty_mall.mp3", "22_rain_window.mp3"],
        "roots": [73.42, 77.78, 82.41, 87.31], # D, Eb, E, F
        "overlay": "dust_motes_loop.mp4",
        "overlay_opacity": 0.70,
        "tags": ["liminal space", "airport ambient", "mallsoft", "dreamcore", "empty spaces"]
    },
    {
        "category": "Cosmic Solitude & Deep Space",
        "places": ["the greenhouse on europa", "the asteroid workshop", "the lunar sleeper cabin", "the observation deck of the derelict", "the atmospheric scoop station", "the orbital ceramics kiln"],
        "subjects": ["tea steaming while jupiter rotates", "the quiet hum of hydroponic pumps", "drifting through the ring system", "listening to solar static", "the last radio beacon from earth"],
        "subgenres": ["cozy sci-fi ambient", "deep space warm ambient", "orbital drone", "cosmic solitude soundscape"],
        "foley": ["23_server_room.mp3", "13_synth_warm.mp3", "31_synth_void.mp3", "32_synth_pulse.mp3"],
        "roots": [55.00, 65.41, 73.42, 98.00], # A, C, D, G
        "overlay": "dust_motes_loop.mp4",
        "overlay_opacity": 0.65,
        "tags": ["sci-fi ambient", "deep space", "space ambient", "europa", "cosmic solitude"]
    },
    {
        "category": "Dark Academia & Ancient Repositories",
        "places": ["the flooded mahogany library", "the clocktower map room", "the botanical archive at midnight", "the stone atrium of lost manuscripts", "the fossil preparation vault"],
        "subjects": ["whispering pages in the green lamp glow", "dust motes drifting across leather bindings", "rain tapping against high arched glass", "the pendulum that changes speed", "the catalog of unwritten books"],
        "subgenres": ["dark academia ambient", "infinite library drone", "victorian study ambient", "gothic archive soundscape"],
        "foley": ["06_library.mp3", "24_museum_hall.mp3", "25_church_empty.mp3", "22_rain_window.mp3"],
        "roots": [58.27, 69.30, 82.41, 92.50], # Bb, C#, E, F#
        "overlay": "cinematic_rain_loop.mp4",
        "overlay_opacity": 0.65,
        "tags": ["dark academia", "infinite library", "study ambient", "victorian gothic", "focus music"]
    },
    {
        "category": "Prehistoric & Deep Time",
        "places": ["the hollow beneath the fossil tree", "the petrified river delta", "the jurassic fern sanctuary", "the salt flats before the ocean", "the cave of the first fire"],
        "subjects": ["warm rain over ancient moss", "resting beneath the oldest thunder", "the river that knew no humans", "shadows of giant wings across the marsh", "the wind across the pangean coast"],
        "subgenres": ["prehistoric cozy ambient", "deep time soundscape", "ancient nature drone", "earth memory ambient"],
        "foley": ["27_wind_desolate.mp3", "34_cave_drip.mp3", "28_aquarium.mp3"],
        "roots": [49.00, 55.00, 65.41, 73.42], # G, A, C, D
        "overlay": "cinematic_rain_loop.mp4",
        "overlay_opacity": 0.60,
        "tags": ["prehistoric", "deep time", "nature ambient", "ancient earth", "sleep drone"]
    },
    {
        "category": "Retro-Nostalgia & Analog Memories",
        "places": ["the video rental store at closing", "the empty 1986 diner booth", "the midnight arcade under the pier", "the roadside motel room in the rain", "the autumn car ride through fog"],
        "subjects": ["rewind tape static fading to black", "neon reflections on wet linoleum", "the muffled song from the kitchen radio", "watching headlights through the blinds", "a memory from an old cassette"],
        "subgenres": ["analog nostalgia ambient", "retro vaporwave drone", "midnight diner ambient", "nostalgic memory soundscape"],
        "foley": ["01_empty_mall.mp3", "35_night_drive.mp3", "36_synth_haze.mp3", "03_laundromat.mp3"],
        "roots": [65.41, 73.42, 82.41, 98.00], # C, D, E, G
        "overlay": "dust_motes_loop.mp4",
        "overlay_opacity": 0.75,
        "tags": ["analog nostalgia", "retro ambient", "vaporwave", "night drive", "1980s aesthetic"]
    },
    {
        # Scene-based theme: each scene pairs an image with titles that describe it.
        "category": "Eldritch Cosmic Horror",
        "preset": "lovecraft",
        "bank_prefix": "eldritch",
        "title_suffix": "... 2 Hours of Cosmic Horror Ambience",
        "scenes": [
            {"titles": ["The Keeper Never Turned the Light Off", "Something Waits Behind the Lighthouse"],
             "prompt": "a single old lighthouse with one lit window on black rocks at night, and behind it out in the sea fog a colossal dark creature silhouette taller than the lighthouse, only its outline visible, two faint pale glowing eyes"},
            {"titles": ["The Sky Opened Over the Harbor at Dusk", "Nobody in the Village Looked Up"],
             "prompt": "a small fishing village of crooked roofs seen from the end of a wooden pier at dusk, the low cloud layer above it opened into a huge slow spiral with a pale curved edge of something enormous inside"},
            {"titles": ["Something Kneels in the Salt Marsh at Dawn", "The Boardwalk Leads to Something Kneeling"],
             "prompt": "a narrow wooden boardwalk through a misty salt marsh at grey dawn, far out in the reeds a colossal kneeling figure with long branching antlers like dead trees half lost in the fog, birds circling its shoulders"},
            {"titles": ["The Observatory Saw It First", "The Stars Were Coiled Around the Hill"],
             "prompt": "a small old observatory on a bare hill at night, its dome shutter open and the door lit by a lamp, the whole sky above a faint enormous spiral of stars and dark gaps coiled around the hill"},
            {"titles": ["The Tide Went Out and Something Stayed", "It Was Standing Where the Sea Used to Be"],
             "prompt": "a wide empty tidal flat at dusk with wet sand reflecting the sky, far out where the water retreated a vast still silhouette standing in the haze, a rusted mooring post in the foreground"},
            {"titles": ["The Radio Station Kept Broadcasting to the Fog", "Someone Answered on the Coastal Frequency"],
             "prompt": "an abandoned coastal radio station with a tall lattice antenna on a cliff at night, one red warning light, thick fog rolling in from the sea and inside the fog a darker shape far larger than the antenna"},
            {"titles": ["The Church Bell Rang Under the Lake", "The Drowned Village Is Ringing Again"],
             "prompt": "a still reservoir lake at twilight with the top of a drowned church steeple rising from the water, a faint glow under the surface around it, mist on the far shore"},
            {"titles": ["The Whalers Never Came Back for It", "Something Old Sleeps at the Whaling Station"],
             "prompt": "a derelict whaling station of rusted tanks and broken jetties in a cold fjord at night, sea fog, and in the fog across the water a long pale shape too large to be a ship"},
        ],
        "foley": ["27_wind_desolate.mp3", "28_aquarium.mp3", "34_cave_drip.mp3", "30_void_deep.mp3"],
        "roots": [43.65, 46.25, 51.91, 58.27], # F, F#, G#, Bb
        "overlay": "fog-overlay.mp4",
        "overlay_opacity": 0.40,
        "image_extra": "More felt than seen. No people.",
        "description_lines": [
            "Something enormous and very old stands just outside what you can see. Low tectonic drones, distant groans and the long breath of the fog.",
        ],
        "tags": ["cosmic horror", "lovecraftian", "eldritch horror", "cosmic dread", "dark ambient", "eldritch ambience"],
    },
    {
        "category": "Weary Knight & Dark Fantasy Rest",
        "preset": "fantasy",
        "bank_prefix": "knight",
        "lowercase_titles": True,
        "scenes": [
            {"titles": ["let me sit by the gate a while", "i will rest before the last climb"],
             "prompt": "a knight in worn steel armor and a dark cloak sitting slumped in the snow against an old castle wall beside an iron-studded gate at dusk, sword across his legs, helmet on, face not visible, through the gate a pale violet sky and a distant spire"},
            {"titles": ["the fire will keep until morning", "stay with the embers a little longer"],
             "prompt": "at night, a lone knight in worn armor sitting against a stone pillar inside a dark ruined chapel with a broken roof, a small campfire burning a few steps in front of him, snow falling through the gap in the roof, helmet lowered, face not visible, embers rising"},
            {"titles": ["the tower is closer than it looks", "keep walking, the road remembers you"],
             "prompt": "a lone cloaked wanderer with a walking staff seen from behind, climbing an old worn stone road along a misty mountainside at dusk, an old stone tower with one lit window on a ridge far ahead"},
            {"titles": ["wake me when the ice sings", "the castle lights can wait"],
             "prompt": "a knight in worn armor asleep sitting against a bare old tree at the edge of a frozen lake at twilight, shield leaning beside him, his horse standing patiently nearby, a distant castle with a few faint lights across the ice, light snowfall, face not visible"},
            {"titles": ["we were the last to leave the keep", "no one will light the lanterns now"],
             "prompt": "two cloaked riders on tired horses seen from behind leaving through the open gate of an empty mountain keep at dusk, banners hanging limp, a long winding path down into a valley of mist"},
            {"titles": ["the bridge held one more night", "rest here, the river is loud enough"],
             "prompt": "a knight in worn armor sitting on an old stone bridge over a dark rushing river at night, a lantern beside him, pine forest and snow on the banks, face not visible"},
            {"titles": ["the inn was empty but the fire was lit", "someone kept a chair by the hearth"],
             "prompt": "the inside of an empty medieval roadside inn at night, a fire burning in a stone hearth, a sword and helmet left on a wooden table, snow against the small window, no one there"},
            {"titles": ["i buried my banner on the hill", "the war ended somewhere behind us"],
             "prompt": "a lone knight in worn armor standing on a windy hill at dawn beside a torn banner planted in the snow, looking down at a misty valley, seen from behind, face not visible"},
        ],
        "foley": ["27_wind_desolate.mp3", "25_church_empty.mp3", "34_cave_drip.mp3"],
        "roots": [55.00, 73.42, 82.41, 98.00], # A, D, E, G
        "overlay": "dust_motes_loop.mp4",
        "overlay_opacity": 0.45,
        "image_extra": "No other people.",
        "description_lines": [
            "a quiet place to stop for a while. wind on the stones, a small fire, voices far away and an old melody that comes and goes.",
        ],
        "tags": ["dark fantasy ambient", "medieval ambience", "fantasy music for sleep", "dungeon synth", "knight ambience", "dark souls ambience"],
    },
]

SNAPSHOT_STYLE = (
    "Simple iPhone snapshot, landscape 16:9, no deliberate composition, ordinary and slightly awkward, "
    "like a quick pocket shot. Slight motion blur, uneven lighting, mild overexposure, tilted angle, messy frame, "
    "phone sensor noise, real textures, not studio, not cinematic, no retouching. Not through a window or windshield. "
    "No text, no logos."
)


def generate_scene_concept(theme, existing_titles):
    """Concept for a scene-based theme: the title is written for the exact image prompt."""
    order = list(range(len(theme["scenes"])))
    random.shuffle(order)
    for idx in order:
        scene = theme["scenes"][idx]
        cover_key = f"{theme['bank_prefix']}_{idx + 1:02d}"  # e.g. knight_02 -> images/fresh/knight_02*.jpg
        for raw in random.sample(scene["titles"], len(scene["titles"])):
            title = raw.lower() if theme.get("lowercase_titles") else raw + theme.get("title_suffix", "")
            if title.lower() in existing_titles or is_too_similar(title, existing_titles):
                continue
            root_freq = random.choice(theme["roots"])
            dsp_freqs = [round(root_freq * mult, 2) for mult in [1.0, 1.5, 2.0, 2.667]]
            dsp_lfos = sorted(random.sample([31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 79, 83], 4))
            foley_samples = [f"{ROOT}/audio/samples/{s}" for s in random.sample(theme["foley"], min(2, len(theme["foley"])))]
            overlay_file = f"{ROOT}/assets/overlays/{theme['overlay']}"
            if not os.path.exists(overlay_file):
                overlay_file = f"{ROOT}/assets/youtube-overlays/{theme['overlay']}"
            if not os.path.exists(overlay_file):
                overlay_file = f"{ROOT}/assets/overlays/dust_motes_loop.mp4"
            image_prompt = (f"Take the phone out of your pocket and snap a quick photo of {scene['prompt']}. "
                            f"{SNAPSHOT_STYLE} {theme.get('image_extra', '')}").strip()
            hashtags = " ".join("#" + t.replace(" ", "") for t in theme["tags"][:4])
            description = (
                f"{theme['description_lines'][0]}\n\n"
                f"🌲 use this for sleep, deep work, writing, studying, reading or a quiet night.\n\n"
                f"🌲 sound design:\n"
                f"• Harmonic root: {root_freq} Hz, chords that slowly change every few minutes\n"
                f"• Layered pads, choir, distant events and foley in a large reverb\n"
                f"• Mastered to -16 LUFS (EBU R128)\n\n"
                f"🌲 subscribe for new atmospheric soundscapes: @timelessambience55\n\n"
                f"{hashtags} #ambient #sleepmusic #2hourambient #timelessambience"
            )
            return {
                "title": title,
                "category": theme["category"],
                "preset": theme.get("preset"),
                "cover_key": cover_key,
                "subgenre": theme["tags"][0],
                "description": description,
                "tags": ", ".join(["ambient", "dark ambient", "sleep ambient", "study music", "2 hours"] + theme["tags"]),
                "image_prompt": image_prompt,
                "dsp_freqs": dsp_freqs,
                "dsp_lfos": dsp_lfos,
                "foley": foley_samples,
                "overlay": overlay_file,
                "overlay_opacity": theme["overlay_opacity"],
            }
    return None


def load_previous_history():
    titles = set()
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                for item in json.load(f):
                    if item.get("title"):
                        titles.add(item["title"].lower())
        except Exception:
            pass

    if os.path.exists(TRACKER_FILE):
        try:
            with open(TRACKER_FILE, "r", encoding="utf-8") as f:
                for t in json.load(f):
                    titles.add(t.lower())
        except Exception:
            pass

    return titles


def save_used_idea(title):
    history = []
    if os.path.exists(TRACKER_FILE):
        try:
            with open(TRACKER_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []
    if title not in history:
        history.append(title)
    with open(TRACKER_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


def is_too_similar(new_title, existing_titles):
    new_words = set(re.findall(r"\b[a-z]{4,}\b", new_title.lower()))
    stopwords = {"ambient", "soundscape", "drone", "hours", "hour", "minute", "sample", "music", "sleep", "dark", "space"}
    new_keywords = new_words - stopwords

    for existing in existing_titles:
        exist_words = set(re.findall(r"\b[a-z]{4,}\b", existing.lower())) - stopwords
        if not new_keywords or not exist_words:
            continue
        overlap = len(new_keywords.intersection(exist_words))
        if overlap >= 3 or (len(new_keywords) >= 2 and overlap / len(new_keywords) > 0.6):
            return True
    return False


def generate_novel_concept():
    existing_titles = load_previous_history()
    
    # Try up to 50 randomized creative variations to guarantee novelty
    for _ in range(50):
        theme = random.choice(THEMES)
        if "scenes" in theme:
            concept = generate_scene_concept(theme, existing_titles)
            if concept:
                return concept
            continue
        place = random.choice(theme["places"])
        subject = random.choice(theme["subjects"])
        subgenre = random.choice(theme["subgenres"])
        
        # Select title formula
        templates = [
            f"{subject} | {subgenre} | 2 hours",
            f"you entered {place}, but the lights never came on | {subgenre}",
            f"{subject} at {place} | {subgenre}",
            f"{place} at 3 AM | {subgenre} | 2 hours",
            f"when {subject} across {place} | {subgenre}"
        ]
        title = random.choice(templates)
        
        if not is_too_similar(title, existing_titles):
            # Select sound design parameters
            root_freq = random.choice(theme["roots"])
            dsp_freqs = [round(root_freq * mult, 2) for mult in [1.0, 1.5, 2.0, 2.667, 3.0][:4]]
            dsp_lfos = random.sample([31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 79, 83], 4)
            dsp_lfos.sort()
            
            foley_samples = [f"{ROOT}/audio/samples/{s}" for s in random.sample(theme["foley"], min(2, len(theme["foley"])))]
            
            # Select overlay
            overlay_file = f"{ROOT}/assets/overlays/{theme['overlay']}"
            if not os.path.exists(overlay_file):
                overlay_file = f"{ROOT}/assets/youtube-overlays/{theme['overlay']}"
            if not os.path.exists(overlay_file):
                overlay_file = f"{ROOT}/assets/overlays/dust_motes_loop.mp4"
                
            image_prompt = (
                f"Photorealistic 35mm cinematic photograph of {place}, {subject}. "
                f"Atmospheric volumetric haze, deep cinematic shadows, muted color palette, vast negative space, 16:9 ratio, ultra-detailed."
            )
            
            description = (
                f"2 hours of immersive {subgenre}.\n"
                f"Step inside {place}. {subject.capitalize()}.\n\n"
                f"🌲 use this for sleep, deep work, writing, studying, or quiet nocturnal drift.\n\n"
                f"🌲 sound design specs:\n"
                f"• Harmonic Root: {root_freq} Hz modal resonance\n"
                f"• Multi-Layer Acoustic Foley & Procedural Haas 3D stereo drones\n"
                f"• Mastered to Broadcast EBU R128 (-16 LUFS)\n\n"
                f"🌲 subscribe for new liminal space, deep space, and dark atmospheric soundscapes weekly.\n\n"
                f"#ambient #liminalspace #{theme['tags'][0].replace(' ', '')} #sleepmusic #studymusic #2hourambient #timelessambience"
            )
            
            return {
                "title": title,
                "category": theme["category"],
                "subgenre": subgenre,
                "description": description,
                "tags": ", ".join(["ambient", "cosmic horror", "dark ambient", "sleep ambient", "study music", "2 hours"] + theme["tags"]),
                "image_prompt": image_prompt,
                "dsp_freqs": dsp_freqs,
                "dsp_lfos": dsp_lfos,
                "foley": foley_samples,
                "overlay": overlay_file,
                "overlay_opacity": theme["overlay_opacity"]
            }

    # Fallback if loop exhausted
    return None


if __name__ == "__main__":
    concept = generate_novel_concept()
    if concept:
        print(json.dumps(concept, indent=2))
        save_used_idea(concept["title"])

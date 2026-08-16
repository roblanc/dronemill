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
    }
]


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
                f"• Mastered to Broadcast EBU R128 (-22.0 LUFS)\n\n"
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

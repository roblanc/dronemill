#!/usr/bin/env python3
"""
AI Scene & Audio Director for DroneMill / Timeless Ambience.
Leverages local 'agy' (Antigravity CLI) or 'opencode' to dynamically analyze video titles
and compose:
1. Exact harmonic audio parameters (frequencies, scales, prime LFO cycles, noise filters).
2. Scene-aware visual motion and particle overlay settings (rain, dust motes, fog, snow, embers).
3. Channel-optimized descriptions and tags.

Usage:
    python3 scripts/ai-scene-director.py "<video_title>" [output_profile.json]
"""

import sys
import os
import json
import re
import subprocess
import shutil

SCHEMA_EXAMPLE = {
    "title": "the botanist's lantern in the conservatory | rainy greenhouse ambient",
    "mood": "reflective_vintage_rain",
    "musical_palette": {
        "scale_name": "F_lydian",
        "root_frequency": 87.31,
        "harmony_partials": [87.31, 174.61, 261.63, 349.23, 440.00, 523.25],
        "sub_frequency": 43.65,
        "noise_type": "pink",
        "noise_filter_low": 200,
        "noise_filter_high": 2800,
        "noise_volume": 0.035,
        "lfo_periods": [37, 53, 73, 97],
        "reverb_type": "damp_greenhouse_hall"
    },
    "visual_fx": {
        "overlay_type": "rain",
        "overlay_opacity": 0.75,
        "camera_drift_px": 40,
        "camera_zoom_amount": 0.018,
        "light_pulse_speed": 3.5,
        "light_pulse_intensity": 0.008
    },
    "seo_description": "Detailed 2-3 paragraph atmospheric YouTube description...",
    "tags": ["ambient", "greenhouse", "rain ambient", "botanical", "sleep music", "timeless ambience"]
}

def query_llm(prompt: str) -> str:
    """Queries agy CLI or opencode CLI without requiring API keys."""
    # 1. Try agy
    if shutil.which("agy"):
        try:
            res = subprocess.run(
                ["agy", "-p", prompt],
                capture_output=True, text=True, timeout=90
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception as e:
            sys.stderr.write(f"Warn: agy invocation error: {e}\n")

    # 2. Try opencode
    if shutil.which("opencode"):
        try:
            res = subprocess.run(
                ["opencode", "run", prompt],
                capture_output=True, text=True, timeout=90
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception as e:
            sys.stderr.write(f"Warn: opencode invocation error: {e}\n")

    raise RuntimeError("No working LLM CLI tool (agy or opencode) responded successfully.")

def clean_json_response(raw_text: str) -> dict:
    """Extracts and parses JSON from markdown or raw text."""
    text = raw_text.strip()
    # Remove markdown code blocks if present
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()
    
    # Try parsing directly
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Attempt to find first { and last }
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace != -1:
            return json.loads(text[first_brace:last_brace+1])
        raise

def direct_scene(title: str) -> dict:
    prompt = f"""You are the master Audio, Visual, and Ambient Music Director for the YouTube channel 'Timeless Ambience'.
Analyze this title and concept:
"{title}"

Determine the optimal, context-aware musical harmony and visual treatment.
Rules:
1. Partials: Provide 5-6 harmonic partial frequencies in Hz matching the mood (e.g. Dorian, Lydian, Aeolian, Pentatonic, or Deep Minor chords).
2. Partials must be musical frequencies (e.g. 55.0, 110.0, 164.81, 220.0, 261.63, 329.63, 392.0, 440.0, 523.25 Hz).
3. LFO Periods: Choose 4 distinct prime numbers in seconds (between 30 and 110) for evolving non-repeating movement.
4. Noise layer: Choose pink, brown, white, or none based on environment (rain, wind, room tone, space vacuum).
5. Visual overlay: Choose exactly one of ["rain", "dust_motes", "fog", "snow_blizzard", "embers", "none"].
   - Rain: for rainy/diner/storm/wet glass scenes (opacity ~0.75).
   - Dust motes: for libraries, antique rooms, sunlight shafts (opacity ~0.80).
   - Fog: for swamps, lakes, space dust/nebula, eerie forests (opacity ~0.35).
   - Snow blizzard: for winter, arctic, snowy fortresses (opacity ~0.70).
   - Embers: for fireplaces, hearths, ruins (opacity ~0.75).

Return ONLY a valid JSON object adhering to this schema:
{json.dumps(SCHEMA_EXAMPLE, indent=2)}
"""
    raw = query_llm(prompt)
    return clean_json_response(raw)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/ai-scene-director.py \"<video_title>\" [output_profile.json]")
        sys.exit(1)
        
    title = sys.argv[1]
    out_profile = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f">> [AI Director] Analyzing scene: '{title}' via Antigravity/AGY...")
    profile = direct_scene(title)
    
    print(f">> Mode: {profile.get('mood')} | Scale: {profile.get('musical_palette', {}).get('scale_name')}")
    print(f">> Harmonics (Hz): {profile.get('musical_palette', {}).get('harmony_partials')}")
    print(f">> Visual Overlay: {profile.get('visual_fx', {}).get('overlay_type')} (opacity: {profile.get('visual_fx', {}).get('overlay_opacity')})")
    
    if out_profile:
        os.makedirs(os.path.dirname(os.path.abspath(out_profile)), exist_ok=True)
        with open(out_profile, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2)
        print(f">> Profile saved to: {out_profile}")
    else:
        print(json.dumps(profile, indent=2))

if __name__ == "__main__":
    main()

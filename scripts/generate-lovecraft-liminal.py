#!/usr/bin/env python3
"""
Pipeline for Lovecraftian Abyss & Liminal Space Hybrid Audio & Video Generation:
1. Generates LatentScore Neural Tracks
2. Orchestrates Multi-Engine Soundscapes (LatentScore + Procedural DSP + Foley + Rubberband Sub + AI Harmonic Director)
3. Renders 1080p Videos with Living Overlays
4. Uploads to YouTube as Unlisted Review Drafts
"""

import os
import sys
import subprocess
import json

ROOT = "/home/brewuser/projects/dronemill"
sys.path.append(f"{ROOT}/scripts")

from ai_hybrid_sound_conductor import build_hybrid_soundscape, run_cmd

os.makedirs(f"{ROOT}/audio/hybrid", exist_ok=True)
os.makedirs(f"{ROOT}/output", exist_ok=True)

# =========================================================================
# 1. GENERATE LATENTSCORE NEURAL TRACKS
# =========================================================================
print("=== [1/4] Generating LatentScore Neural Audio ===")

ls_lovecraft = f"{ROOT}/audio/hybrid/latentscore_lovecraft.wav"
if not os.path.exists(ls_lovecraft):
    print(">> Generating Lovecraftian neural pad...")
    cmd_ls1 = f"\"{ROOT}/scripts/latentscore-gen.sh\" \"ancient dark ocean abyss, ominous cyclopean drone, bowed subterranean metal, sacred cosmic dread\" \"{ls_lovecraft}\" 60"
    run_cmd(cmd_ls1, "LatentScore Lovecraftian")

ls_liminal = f"{ROOT}/audio/hybrid/latentscore_liminal.wav"
if not os.path.exists(ls_liminal):
    print(">> Generating Liminal Poolroom neural pad...")
    cmd_ls2 = f"\"{ROOT}/scripts/latentscore-gen.sh\" \"haunting nostalgic electric piano and music box decaying in infinite reverb, empty tiled poolroom, dreamcore\" \"{ls_liminal}\" 60"
    run_cmd(cmd_ls2, "LatentScore Liminal Poolroom")

# =========================================================================
# 2. COMPOSE HYBRID MULTI-ENGINE SOUNDSCAPES
# =========================================================================
print("\n=== [2/4] Orchestrating Hybrid Multi-Engine Soundscapes ===")

# --- 2A. LOVECRAFTIAN ABYSS (5-Engine Dark Atmospheric Ensemble) ---
cfg_lovecraft = {
    "title": "the submerged observatory of the abyss",
    "duration": 60,
    "engines": {
        "latentscore": {
            "enabled": True,
            "wav": ls_lovecraft,
            "volume": 0.80,
            "filter": "highpass=f=70,lowpass=f=4500"
        },
        "foley": {
            "enabled": True,
            "samples": [
                f"{ROOT}/audio/samples/34_cave_drip.mp3",
                f"{ROOT}/audio/samples/27_wind_desolate.mp3"
            ],
            "volume": 0.40,
            "filter": "highpass=f=100,lowpass=f=5500"
        },
        "dsp": {
            "enabled": True,
            "frequencies": [69.30, 103.83, 138.59, 207.65], # C# Locrian / Abyssal intervals
            "lfos": [41, 59, 83, 101],
            "volume": 0.50
        },
        "rubberband": {
            "enabled": True,
            "source_wav": f"{ROOT}/audio/samples/12_cosmic_horror.mp3",
            "semitones": -12,
            "volume": 0.75
        }
    }
}
audio_lovecraft_master = f"{ROOT}/audio/hybrid/lovecraft_hybrid_master.wav"
build_hybrid_soundscape(cfg_lovecraft, audio_lovecraft_master)

# --- 2B. LIMINAL POOLROOMS (4-Engine Dreamcore Soundscape) ---
cfg_liminal = {
    "title": "echoes in the eternal poolroom",
    "duration": 60,
    "engines": {
        "latentscore": {
            "enabled": True,
            "wav": ls_liminal,
            "volume": 0.85,
            "filter": "highpass=f=120,lowpass=f=6500"
        },
        "foley": {
            "enabled": True,
            "samples": [
                f"{ROOT}/audio/samples/04_poolrooms.mp3",
                f"{ROOT}/audio/samples/29_humid_bathroom.mp3"
            ],
            "volume": 0.45,
            "filter": "highpass=f=150,lowpass=f=7500"
        },
        "dsp": {
            "enabled": True,
            "frequencies": [82.41, 164.81, 246.94, 329.63, 440.00], # E Dorian / Pentatonic suspended
            "lfos": [37, 53, 71, 89],
            "volume": 0.40
        },
        "rubberband": {
            "enabled": True,
            "source_wav": f"{ROOT}/audio/samples/04_poolrooms.mp3",
            "semitones": -12,
            "volume": 0.65
        }
    }
}
audio_liminal_master = f"{ROOT}/audio/hybrid/liminal_hybrid_master.wav"
build_hybrid_soundscape(cfg_liminal, audio_liminal_master)

# =========================================================================
# 3. RENDER 1080P VIDEOS WITH LIVING VISUALS
# =========================================================================
print("\n=== [3/4] Rendering 1080p Living Hybrid Videos ===")

def render_vid(img, audio, overlay, opacity, out_mp4):
    cmd = f"""ffmpeg -y -nostdin \
      -loop 1 -framerate 24 -t 60 -i "{img}" \
      -stream_loop -1 -i "{overlay}" \
      -i "{audio}" \
      -filter_complex "
        [0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,format=gbrp[base];
        [1:v]scale=1920:1080:flags=lanczos,curves=all='0/0 0.15/0 0.50/0.30 1/0.85',format=gbrp[fx];
        [base][fx]blend=all_mode=screen:all_opacity={opacity}[merged];
        [merged]vignette=angle=0.35,noise=alls=0.6:allf=t+u,format=yuv420p[vout]
      " -map "[vout]" -map "2:a" \
      -c:v libx264 -preset ultrafast -crf 20 -c:a aac -b:a 256k -ar 48000 -t 60 -movflags +faststart "{out_mp4}"
    """
    run_cmd(cmd, f"Rendering video -> {out_mp4}")

video_lovecraft = f"{ROOT}/output/lovecraft_hybrid_sample.mp4"
render_vid(
    f"{ROOT}/images/lovecraftian_submerged_observatory.jpg",
    audio_lovecraft_master,
    f"{ROOT}/assets/youtube-overlays/fog-overlay.mp4",
    0.40,
    video_lovecraft
)

video_liminal = f"{ROOT}/output/liminal_hybrid_sample.mp4"
render_vid(
    f"{ROOT}/images/liminal_poolrooms_sanctuary.jpg",
    audio_liminal_master,
    f"{ROOT}/assets/youtube-overlays/fog-overlay.mp4",
    0.20,
    video_liminal
)

# =========================================================================
# 4. UPLOAD TO YOUTUBE AS UNLISTED DRAFTS
# =========================================================================
print("\n=== [4/4] Uploading to YouTube ===")

def upload_vid(video, title, desc_text, thumb, tags):
    desc_file = "/tmp/yt_temp_desc.txt"
    with open(desc_file, "w", encoding="utf-8") as f:
        f.write(desc_text)
    cmd = f"\"{ROOT}/scripts/upload-yt.sh\" \"{video}\" \"{title}\" \"{desc_file}\" \"{thumb}\" \"unlisted\" \"{tags}\""
    run_cmd(cmd, f"Uploading {title}")
    if os.path.exists(desc_file):
        os.remove(desc_file)

# 4A. Upload Lovecraftian
desc_lc = """AI Hybrid Orchestration Demo (5 Engines Combined):
1. AI Harmonic Conductor: C# Locrian abyssal root harmonic frequencies (69.30Hz).
2. LatentScore Neural Music Composer: Ancient bowed subterranean metal and cosmic dread pads.
3. Multi-Layer Foley: Desolate subterranean cavern drips and abyssal ocean wind.
4. Procedural FFmpeg DSP Engine: Haas 3D stereo spatialized sub-harmonic sine oscillators.
5. Rubberband Studio Pitch-Shift Engine: Deep sub-octave phase-vocoded cosmic horror rumble (under 50Hz).
• Mastered with EBU R128 (-22 LUFS) and analog warmth.

Visual: Monolithic cyclopean submerged stone observatory at twilight + volumetric sea fog.

#ambient #lovecraftian #darkambient #cosmicdread #hybridsound #timelessambience"""

upload_vid(
    video_lovecraft,
    "[HYBRID DEMO] the submerged observatory of the abyss | lovecraftian dark ambient | 1 min sample",
    desc_lc,
    f"{ROOT}/images/lovecraftian_submerged_observatory.jpg",
    "ambient,lovecraftian,dark ambient,cosmic dread,hybrid sound,timeless ambience"
)

# 4B. Upload Liminal
desc_lm = """AI Hybrid Orchestration Demo (4 Engines Combined):
1. AI Harmonic Conductor: E Dorian / nostalgic pentatonic suspended harmonic map.
2. LatentScore Neural Music Composer: Haunting nostalgic electric piano and music box decaying in infinite reverb.
3. Multi-Layer Foley: Damp indoor poolroom water reverberations and fluorescent light hum.
4. Procedural FFmpeg DSP Engine: Haas 3D stereo harmonic shimmers with prime LFO breathing cycles.
5. Rubberband Studio Pitch-Shift Engine: Phase-vocoded sub-octave poolroom resonance drone for heavy stillness.
• Mastered with EBU R128 (-22 LUFS) loudness normalization.

Visual: Endless pale turquoise ceramic tiled poolrooms with quiet water reflections + soft humid haze.

#ambient #liminalspaces #poolrooms #dreamcore #nostalgia #hybridsound #timelessambience"""

upload_vid(
    video_liminal,
    "[HYBRID DEMO] echoes in the eternal poolroom | liminal space ambient | 1 min sample",
    desc_lm,
    f"{ROOT}/images/liminal_poolrooms_sanctuary.jpg",
    "ambient,liminal spaces,poolrooms,dreamcore,nostalgia,hybrid sound,timeless ambience"
)

print("\n✨ ALL LOVECRAFTIAN & LIMINAL SAMPLES GENERATED, RENDERED, AND UPLOADED SUCCESSFULLY!")

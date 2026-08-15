#!/usr/bin/env python3
"""
Master script to generate, orchestrate, render, and upload 3 Lovecraftian / Cosmic Horror
hybrid samples inspired by @TheLighthouseKeeper:
1. Arkham Sky Breach (1926)
2. The Madness of the Fresnel Light
3. Strange is the Night in Carcosa (King in Yellow)
"""

import os
import sys
import subprocess
import json

ROOT = "/home/brewuser/projects/dronemill"
sys.path.append(f"{ROOT}/scripts")

from ai_hybrid_sound_conductor import build_hybrid_soundscape, run_cmd

os.makedirs(f"{ROOT}/audio/lovecraft", exist_ok=True)
os.makedirs(f"{ROOT}/output", exist_ok=True)

# =========================================================================
# 1. GENERATE NEURAL LATENTSCORE STEMS
# =========================================================================
print("=== [1/4] Generating Neural LatentScore Audio Tracks ===")

ls1 = f"{ROOT}/audio/lovecraft/ls_arkham_1926.wav"
if not os.path.exists(ls1):
    print(">> Generating LatentScore: Arkham 1926...")
    cmd1 = f"\"{ROOT}/scripts/latentscore-gen.sh\" \"ominous 1920s arkham rainy street, massive celestial breach, slow low cello drone, sacred cosmic dread\" \"{ls1}\" 60"
    run_cmd(cmd1, "LatentScore Arkham 1926")

ls2 = f"{ROOT}/audio/lovecraft/ls_lighthouse_fresnel.wav"
if not os.path.exists(ls2):
    print(">> Generating LatentScore: Lighthouse Fresnel...")
    cmd2 = f"\"{ROOT}/scripts/latentscore-gen.sh\" \"madness in the lighthouse lantern room, bowed metal resonance, oceanic abyss swell, hypnotic nautical drone\" \"{ls2}\" 60"
    run_cmd(cmd2, "LatentScore Lighthouse Fresnel")

ls3 = f"{ROOT}/audio/lovecraft/ls_carcosa_yellow.wav"
if not os.path.exists(ls3):
    print(">> Generating LatentScore: Carcosa King in Yellow...")
    cmd3 = f"\"{ROOT}/scripts/latentscore-gen.sh\" \"ancient decaying music box echoing in the ruined stone halls of carcosa under black stars, king in yellow ambient\" \"{ls3}\" 60"
    run_cmd(cmd3, "LatentScore King in Yellow")

# =========================================================================
# 2. ORCHESTRATE HYBRID MULTI-ENGINE SOUNDSCAPES
# =========================================================================
print("\n=== [2/4] Orchestrating Multi-Engine Hybrid Scores ===")

# --- 2A. ARKHAM 1926 (G# Phrygian / Cosmic Void) ---
cfg1 = {
    "title": "midnight walk in arkham, 1926",
    "duration": 60,
    "engines": {
        "latentscore": {
            "enabled": True,
            "wav": ls1,
            "volume": 0.85,
            "filter": "highpass=f=80,lowpass=f=5500"
        },
        "foley": {
            "enabled": True,
            "samples": [
                f"{ROOT}/audio/samples/22_rain_window.mp3",
                f"{ROOT}/audio/samples/27_wind_desolate.mp3"
            ],
            "volume": 0.40,
            "filter": "highpass=f=120,lowpass=f=6000"
        },
        "dsp": {
            "enabled": True,
            "frequencies": [51.91, 103.83, 155.56, 207.65], # G# Phrygian / Diminished 5th
            "lfos": [43, 61, 79, 103],
            "volume": 0.45
        },
        "rubberband": {
            "enabled": True,
            "source_wav": f"{ROOT}/audio/samples/12_cosmic_horror.mp3",
            "semitones": -12,
            "volume": 0.75
        }
    }
}
master1 = f"{ROOT}/audio/lovecraft/master_arkham_1926.wav"
build_hybrid_soundscape(cfg1, master1)

# --- 2B. FRESNEL LIGHTHOUSE MADNESS (D Locrian / Abyssal Swell) ---
cfg2 = {
    "title": "the madness of the fresnel light",
    "duration": 60,
    "engines": {
        "latentscore": {
            "enabled": True,
            "wav": ls2,
            "volume": 0.80,
            "filter": "highpass=f=100,lowpass=f=5000"
        },
        "foley": {
            "enabled": True,
            "samples": [
                f"{ROOT}/audio/samples/34_cave_drip.mp3",
                f"{ROOT}/audio/samples/28_aquarium.mp3"
            ],
            "volume": 0.45,
            "filter": "highpass=f=100,lowpass=f=6500"
        },
        "dsp": {
            "enabled": True,
            "frequencies": [73.42, 110.00, 146.83, 220.00], # D Locrian / Abyssal tide
            "lfos": [37, 53, 73, 97],
            "volume": 0.45
        },
        "rubberband": {
            "enabled": True,
            "source_wav": f"{ROOT}/audio/bases/batch3/oldest-thunder.wav",
            "semitones": -12,
            "volume": 0.70
        }
    }
}
master2 = f"{ROOT}/audio/lovecraft/master_lighthouse_fresnel.wav"
build_hybrid_soundscape(cfg2, master2)

# --- 2C. KING IN YELLOW / CARCOSA (Bb Dorian / Ethereal Decay) ---
cfg3 = {
    "title": "strange is the night in carcosa",
    "duration": 60,
    "engines": {
        "latentscore": {
            "enabled": True,
            "wav": ls3,
            "volume": 0.85,
            "filter": "highpass=f=120,lowpass=f=6000"
        },
        "foley": {
            "enabled": True,
            "samples": [
                f"{ROOT}/audio/samples/24_museum_hall.mp3",
                f"{ROOT}/audio/samples/25_church_empty.mp3"
            ],
            "volume": 0.35,
            "filter": "highpass=f=150,lowpass=f=7000"
        },
        "dsp": {
            "enabled": True,
            "frequencies": [58.27, 116.54, 174.61, 233.08], # Bb Dorian / Dissonant 9ths
            "lfos": [47, 67, 83, 107],
            "volume": 0.40
        },
        "rubberband": {
            "enabled": True,
            "source_wav": f"{ROOT}/audio/samples/15_synth_dread.mp3",
            "semitones": -12,
            "volume": 0.70
        }
    }
}
master3 = f"{ROOT}/audio/lovecraft/master_king_in_yellow.wav"
build_hybrid_soundscape(cfg3, master3)

# =========================================================================
# 3. RENDER 1080P VIDEOS WITH LIVING OVERLAYS
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

vid1 = f"{ROOT}/output/lovecraft_arkham_1926.mp4"
render_vid(f"{ROOT}/images/lovecraft_arkham_1926.jpg", master1, f"{ROOT}/assets/youtube-overlays/fog-overlay.mp4", 0.35, vid1)

vid2 = f"{ROOT}/output/lovecraft_lighthouse_fresnel.mp4"
render_vid(f"{ROOT}/images/lovecraft_lighthouse_fresnel.jpg", master2, f"{ROOT}/assets/youtube-overlays/fog-overlay.mp4", 0.40, vid2)

vid3 = f"{ROOT}/output/lovecraft_king_in_yellow.mp4"
render_vid(f"{ROOT}/images/lovecraft_king_in_yellow.jpg", master3, f"{ROOT}/assets/youtube-overlays/fog-overlay.mp4", 0.30, vid3)

# =========================================================================
# 4. UPLOAD TO YOUTUBE AS UNLISTED DRAFTS
# =========================================================================
print("\n=== [4/4] Uploading 3 Lovecraftian Samples to YouTube ===")

def upload_vid(video, title, desc_text, thumb, tags):
    desc_file = "/tmp/yt_temp_desc.txt"
    with open(desc_file, "w", encoding="utf-8") as f:
        f.write(desc_text)
    cmd = f"\"{ROOT}/scripts/upload-yt.sh\" \"{video}\" \"{title}\" \"{desc_file}\" \"{thumb}\" \"unlisted\" \"{tags}\""
    run_cmd(cmd, f"Uploading {title}")
    if os.path.exists(desc_file):
        os.remove(desc_file)

# 4A. Arkham 1926
desc1 = """AI Hybrid Orchestration Demo (5 Engines Combined):
1. AI Harmonic Director: G# Phrygian / Diminished sub-harmonics (51.91Hz root).
2. LatentScore Neural Music Composer: 1920s rainy Arkham street cello drone & sacred dread chords.
3. Multi-Layer Foley: Night rain on asphalt & desolate cold wind.
4. Procedural FFmpeg DSP Engine: Haas 3D stereo sine oscillators with prime LFO breathing (43s, 61s, 79s).
5. Rubberband Studio Pitch-Shift Engine: Deep sub-octave phase-vocoded cosmic horror rumble (under 45Hz).
• Mastered with EBU R128 (-22 LUFS).

Visual: 1926 daguerreotype archival photograph of Arkham street sky breach + volumetric mist.

#ambient #lovecraftian #arkham #cosmicdread #hybridsound #timelessambience"""

upload_vid(
    vid1,
    "[LOVECRAFTIAN] midnight walk in arkham, 1926 | cosmic horror ambient | 1 min sample",
    desc1,
    f"{ROOT}/images/lovecraft_arkham_1926.jpg",
    "ambient,lovecraftian,arkham,cosmic horror,dark ambient,hybrid sound,timeless ambience"
)

# 4B. Lighthouse Fresnel
desc2 = """AI Hybrid Orchestration Demo (5 Engines Combined):
1. AI Harmonic Director: D Locrian / Abyssal tide modal root (73.42Hz).
2. LatentScore Neural Music Composer: Bowed metal lantern resonance & oceanic abyss swell.
3. Multi-Layer Foley: Cavern drips, distant aquarium water pressure & sea wall spray.
4. Procedural FFmpeg DSP Engine: Haas 3D stereo glass shimmer & binaural sea wind oscillators.
5. Rubberband Studio Pitch-Shift Engine: Sub-bass oceanic undertow drone (0.5x pitch shift).
• Mastered with EBU R128 (-22 LUFS) and true-peak protection.

Visual: 1890s archival monochrome of remote lighthouse lantern wrapped in eldritch tentacles.

#ambient #lovecraftian #lighthouse #cosmichorror #hybridsound #timelessambience"""

upload_vid(
    vid2,
    "[LOVECRAFTIAN] the madness of the fresnel light | lighthouse cosmic ambient | 1 min sample",
    desc2,
    f"{ROOT}/images/lovecraft_lighthouse_fresnel.jpg",
    "ambient,lovecraftian,lighthouse,cosmic horror,dark ambient,hybrid sound,timeless ambience"
)

# 4C. King in Yellow
desc3 = """AI Hybrid Orchestration Demo (5 Engines Combined):
1. AI Harmonic Director: Bb Dorian / Dissonant 9th modal map (58.27Hz root).
2. LatentScore Neural Music Composer: Ancient decaying music box decaying in ruined stone halls.
3. Multi-Layer Foley: Grand empty stone hall acoustic reverberation & subtle air pressure.
4. Procedural FFmpeg DSP Engine: Haas 3D stereo dissonant sine overtones on prime LFO envelopes.
5. Rubberband Studio Pitch-Shift Engine: Phase-vocoded sub-octave dread drone for crushing silence.
• Mastered with EBU R128 (-22 LUFS).

Visual: 1895 wet plate collodion photograph of the King in Yellow in the ruins of Carcosa.

#ambient #lovecraftian #kinginyellow #carcosa #cosmichorror #hybridsound #timelessambience"""

upload_vid(
    vid3,
    "[LOVECRAFTIAN] strange is the night in carcosa | king in yellow ambient | 1 min sample",
    desc3,
    f"{ROOT}/images/lovecraft_king_in_yellow.jpg",
    "ambient,lovecraftian,king in yellow,carcosa,cosmic horror,dark ambient,timeless ambience"
)

print("\n✨ ALL 3 LOVECRAFTIAN SAMPLES GENERATED, RENDERED, AND UPLOADED SUCCESSFULLY!")

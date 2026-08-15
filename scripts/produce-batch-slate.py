#!/usr/bin/env python3
"""
Automated Production and Scheduling Runner for Slate Slots #1 to #4:
Slot 1: 2026-08-31T18:00:00Z | you returned to the ferry terminal, but the tide never came
Slot 2: 2026-09-01T18:00:00Z | the tide that climbed into the sky | oceanic dark ambient
Slot 3: 2026-09-02T18:00:00Z | noonbloom | sunlit translucent meadow ambient
Slot 4: 2026-09-03T18:00:00Z | you arrive at the orbital ceramics workshop | cozy space ambient
"""

import os
import sys
import json
import datetime
import subprocess

ROOT = "/home/brewuser/projects/dronemill"
sys.path.append(f"{ROOT}/scripts")

from ai_hybrid_sound_conductor import build_hybrid_soundscape, run_cmd

os.makedirs(f"{ROOT}/audio/slate", exist_ok=True)
os.makedirs(f"{ROOT}/output", exist_ok=True)
os.makedirs(f"{ROOT}/descriptions", exist_ok=True)

# =========================================================================
# 1. GENERATE NEURAL LATENTSCORE STEMS
# =========================================================================
print("=== [1/4] Generating LatentScore Neural Audio ===")

ls1 = f"{ROOT}/audio/slate/ls_01_ferry_terminal.wav"
if not os.path.exists(ls1):
    cmd1 = f"\"{ROOT}/scripts/latentscore-gen.sh\" \"empty coastal ferry terminal at dusk, infinitely drained dry seabed, quiet nostalgic isolation, slow organ pad\" \"{ls1}\" 60"
    run_cmd(cmd1, "LatentScore Slot 1")

ls2 = f"{ROOT}/audio/slate/ls_02_tide_climbed.wav"
if not os.path.exists(ls2):
    cmd2 = f"\"{ROOT}/scripts/latentscore-gen.sh\" \"colossal vertical wall of water rising into clouds, black volcanic shore, heavy oceanic dark ambient, bowed metal cello\" \"{ls2}\" 60"
    run_cmd(cmd2, "LatentScore Slot 2")

ls3 = f"{ROOT}/audio/slate/ls_03_noonbloom.wav"
if not os.path.exists(ls3):
    cmd3 = f"\"{ROOT}/scripts/latentscore-gen.sh\" \"sunlit white meadow with giant crystal translucent flowers, serene bright ambient, warm acoustic guitar and glass bells\" \"{ls3}\" 60"
    run_cmd(cmd3, "LatentScore Slot 3")

ls4 = f"{ROOT}/audio/slate/ls_04_orbital_ceramics.wav"
if not os.path.exists(ls4):
    cmd4 = f"\"{ROOT}/scripts/latentscore-gen.sh\" \"cozy orbital ceramics workshop overlooking gas giant planet, warm kiln light, lived-in sci-fi synth reverie\" \"{ls4}\" 60"
    run_cmd(cmd4, "LatentScore Slot 4")

# =========================================================================
# 2. ORCHESTRATE MULTI-ENGINE HYBRID SOUNDSCAPES (-22 LUFS)
# =========================================================================
print("\n=== [2/4] Orchestrating Multi-Engine Hybrid Audio ===")

# --- SLOT 1: FERRY TERMINAL (D Dorian / Coastal Liminal) ---
cfg1 = {
    "title": "you returned to the ferry terminal, but the tide never came",
    "duration": 60,
    "engines": {
        "latentscore": {"enabled": True, "wav": ls1, "volume": 0.85, "filter": "highpass=f=80,lowpass=f=5500"},
        "foley": {
            "enabled": True,
            "samples": [f"{ROOT}/audio/samples/27_wind_desolate.mp3", f"{ROOT}/audio/samples/07_train_station.mp3"],
            "volume": 0.40,
            "filter": "highpass=f=120,lowpass=f=6000"
        },
        "dsp": {
            "enabled": True,
            "frequencies": [73.42, 110.00, 146.83, 220.00], # D Dorian
            "lfos": [43, 61, 79, 103],
            "volume": 0.45
        },
        "rubberband": {
            "enabled": True,
            "source_wav": f"{ROOT}/audio/samples/01_empty_mall.mp3",
            "semitones": -12,
            "volume": 0.70
        }
    }
}
master1 = f"{ROOT}/audio/slate/master_01_ferry.wav"
build_hybrid_soundscape(cfg1, master1)

# --- SLOT 2: TIDE THAT CLIMBED SKY (C# Locrian / Oceanic Dread) ---
cfg2 = {
    "title": "the tide that climbed into the sky",
    "duration": 60,
    "engines": {
        "latentscore": {"enabled": True, "wav": ls2, "volume": 0.80, "filter": "highpass=f=70,lowpass=f=4500"},
        "foley": {
            "enabled": True,
            "samples": [f"{ROOT}/audio/samples/34_cave_drip.mp3", f"{ROOT}/audio/samples/28_aquarium.mp3"],
            "volume": 0.45,
            "filter": "highpass=f=100,lowpass=f=6000"
        },
        "dsp": {
            "enabled": True,
            "frequencies": [69.30, 103.83, 138.59, 207.65], # C# Locrian
            "lfos": [41, 59, 83, 101],
            "volume": 0.50
        },
        "rubberband": {
            "enabled": True,
            "source_wav": f"{ROOT}/audio/bases/batch3/oldest-thunder.wav",
            "semitones": -12,
            "volume": 0.75
        }
    }
}
master2 = f"{ROOT}/audio/slate/master_02_tide.wav"
build_hybrid_soundscape(cfg2, master2)

# --- SLOT 3: NOONBLOOM (F Lydian / Sunlit Translucent) ---
cfg3 = {
    "title": "noonbloom",
    "duration": 60,
    "engines": {
        "latentscore": {"enabled": True, "wav": ls3, "volume": 0.85, "filter": "highpass=f=120,lowpass=f=7500"},
        "foley": {
            "enabled": True,
            "samples": [f"{ROOT}/audio/samples/06_library.mp3"],
            "volume": 0.30,
            "filter": "highpass=f=180,lowpass=f=6000"
        },
        "dsp": {
            "enabled": True,
            "frequencies": [87.31, 174.61, 261.63, 349.23, 440.00, 523.25], # F Lydian
            "lfos": [37, 53, 73, 97],
            "volume": 0.45
        },
        "rubberband": {
            "enabled": True,
            "source_wav": f"{ROOT}/audio/bases/batch3/rewind-season.wav",
            "semitones": -12,
            "volume": 0.65
        }
    }
}
master3 = f"{ROOT}/audio/slate/master_03_noonbloom.wav"
build_hybrid_soundscape(cfg3, master3)

# --- SLOT 4: ORBITAL CERAMICS (C Major Add9 / Warm Sci-Fi) ---
cfg4 = {
    "title": "you arrive at the orbital ceramics workshop",
    "duration": 60,
    "engines": {
        "latentscore": {"enabled": True, "wav": ls4, "volume": 0.85, "filter": "highpass=f=100,lowpass=f=6000"},
        "foley": {
            "enabled": True,
            "samples": [f"{ROOT}/audio/samples/23_server_room.mp3", f"{ROOT}/audio/samples/13_synth_warm.mp3"],
            "volume": 0.40,
            "filter": "highpass=f=140,lowpass=f=7000"
        },
        "dsp": {
            "enabled": True,
            "frequencies": [65.41, 130.81, 196.00, 246.94, 293.66], # C Add9
            "lfos": [43, 59, 71, 89],
            "volume": 0.45
        },
        "rubberband": {
            "enabled": True,
            "source_wav": f"{ROOT}/audio/bases/batch3/asteroid-kitchen.wav",
            "semitones": -12,
            "volume": 0.70
        }
    }
}
master4 = f"{ROOT}/audio/slate/master_04_orbital.wav"
build_hybrid_soundscape(cfg4, master4)

# =========================================================================
# 3. RENDER 1080P LIVING HYBRID VIDEOS
# =========================================================================
print("\n=== [3/4] Rendering 1080p Living Videos ===")

def render_video(img, audio, overlay, opacity, out_mp4):
    cmd = f"""ffmpeg -y -nostdin \
      -loop 1 -framerate 24 -t 60 -i "{img}" \
      -stream_loop -1 -i "{overlay}" \
      -i "{audio}" \
      -filter_complex "
        [0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,format=gbrp[base];
        [1:v]scale=1920:1080:flags=lanczos,curves=all='0/0 0.12/0 0.50/0.35 1/0.85',format=gbrp[fx];
        [base][fx]blend=all_mode=screen:all_opacity={opacity}[merged];
        [merged]vignette=angle=0.32,noise=alls=0.6:allf=t+u,format=yuv420p[vout]
      " -map "[vout]" -map "2:a" \
      -c:v libx264 -preset ultrafast -crf 20 -c:a aac -b:a 256k -ar 48000 -t 60 -movflags +faststart "{out_mp4}"
    """
    run_cmd(cmd, f"Rendering video -> {out_mp4}")

vid1 = f"{ROOT}/output/slate_01_ferry_terminal.mp4"
render_video(f"{ROOT}/images/slate/01_ferry_terminal.jpg", master1, f"{ROOT}/assets/youtube-overlays/fog-overlay.mp4", 0.35, vid1)

vid2 = f"{ROOT}/output/slate_02_tide_climbed_sky.mp4"
render_video(f"{ROOT}/images/slate/02_tide_climbed_sky.jpg", master2, f"{ROOT}/assets/youtube-overlays/fog-overlay.mp4", 0.40, vid2)

vid3 = f"{ROOT}/output/slate_03_noonbloom.mp4"
render_video(f"{ROOT}/images/slate/03_noonbloom.jpg", master3, f"{ROOT}/assets/overlays/dust_motes_loop.mp4", 0.80, vid3)

vid4 = f"{ROOT}/output/slate_04_orbital_ceramics.mp4"
render_video(f"{ROOT}/images/slate/04_orbital_ceramics.jpg", master4, f"{ROOT}/assets/youtube-overlays/fog-overlay.mp4", 0.25, vid4)

# =========================================================================
# 4. UPLOAD AND SCHEDULE SEQUENTIALLY ON YOUTUBE (Starting 2026-08-31)
# =========================================================================
print("\n=== [4/4] Uploading & Scheduling on YouTube ===")

def schedule_video(video, title, desc, thumb, tags, publish_date_iso):
    desc_file = f"/tmp/desc_{os.getpid()}.txt"
    with open(desc_file, "w", encoding="utf-8") as f:
        f.write(desc)
    cmd = f"\"{ROOT}/scripts/upload-yt.sh\" \"{video}\" \"{title}\" \"{desc_file}\" \"{thumb}\" \"private\" \"{tags}\" \"{publish_date_iso}\""
    run_cmd(cmd, f"Scheduling {title} for {publish_date_iso}")
    if os.path.exists(desc_file):
        os.remove(desc_file)

# 4A. Slot 1 (2026-08-31)
desc1 = """AI Hybrid Orchestration:
1. AI Harmonic Director: D Dorian coastal liminal modal field.
2. LatentScore: Nostalgic organ & piano reverberations across an infinite drained seabed.
3. Multi-Layer Foley: Desolate coastal wind & empty transit station hum.
4. Procedural DSP: Haas 3D stereo harmonic sine drones.
5. Rubberband Sub-Bass: Pitch-shifted deep spatial resonance.
• Mastered with EBU R128 (-22 LUFS).

Visual: Vast brutalist concrete ferry terminal overlooking drained seabed + drifting sea fog.

#ambient #liminalspaces #transit #coastalambient #hybridsound #timelessambience"""

schedule_video(
    vid1,
    "you returned to the ferry terminal, but the tide never came | liminal transit ambient",
    desc1,
    f"{ROOT}/images/slate/01_ferry_terminal.jpg",
    "ambient,liminal transit,coastal ambient,empty ferry,drained ocean,hybrid sound,timeless ambience",
    "2026-08-31T18:00:00Z"
)

# 4B. Slot 2 (2026-09-01)
desc2 = """AI Hybrid Orchestration:
1. AI Harmonic Director: C# Locrian oceanic dark ambient map.
2. LatentScore: Bowed metal cello drone & sacred atmospheric dread.
3. Multi-Layer Foley: Subterranean cavern drips & deep oceanic water pressure.
4. Procedural DSP: Haas 3D stereo spatialized sub-harmonic sine oscillators.
5. Rubberband Sub-Bass: Deep sub-octave volcanic thunder undertow.
• Mastered with EBU R128 (-22 LUFS).

Visual: 1920s archival daguerreotype of black volcanic shore with vertical ocean wall + sea mist.

#ambient #lovecraftian #darkambient #cosmicdread #hybridsound #timelessambience"""

schedule_video(
    vid2,
    "the tide that climbed into the sky | oceanic dark ambient",
    desc2,
    f"{ROOT}/images/slate/02_tide_climbed_sky.jpg",
    "ambient,oceanic dark ambient,lovecraftian,cosmic horror,daguerreotype,hybrid sound,timeless ambience",
    "2026-09-01T18:00:00Z"
)

# 4C. Slot 3 (2026-09-02)
desc3 = """AI Hybrid Orchestration:
1. AI Harmonic Director: F Lydian translucent modal matrix.
2. LatentScore: Warm acoustic guitar harmonics & crystalline glass bells.
3. Multi-Layer Foley: Quiet library air & gentle sunlight resonance.
4. Procedural DSP: Haas 3D stereo sine partials with prime-period LFO envelopes.
5. Rubberband Sub-Bass: Sub-octave warm drone foundation.
• Mastered with EBU R128 (-22 LUFS).

Visual: Sunlit white meadow with giant crystalline translucent flowers + 3D floating dust motes.

#ambient #surrealambient #noonbloom #crystalmeadow #dreamcore #timelessambience"""

schedule_video(
    vid3,
    "noonbloom | sunlit translucent meadow ambient",
    desc3,
    f"{ROOT}/images/slate/03_noonbloom.jpg",
    "ambient,noonbloom,surreal ambient,crystal meadow,dreamcore,hybrid sound,timeless ambience",
    "2026-09-02T18:00:00Z"
)

# 4D. Slot 4 (2026-09-03)
desc4 = """AI Hybrid Orchestration:
1. AI Harmonic Director: C Major Add9 cozy orbital science fiction tuning.
2. LatentScore: Warm kiln light synth reverie & acoustic warmth.
3. Multi-Layer Foley: Station ventilation airflow & subtle pottery workshop resonance.
4. Procedural DSP: Haas 3D stereo crystal sine harmonics on prime LFO cycles.
5. Rubberband Sub-Bass: Sub-octave deep space gravity rumble.
• Mastered with EBU R128 (-22 LUFS).

Visual: Cozy orbital pottery ceramics workshop overlooking a gas giant + slow cosmic haze.

#ambient #scifiambient #orbitalceramics #cozysci-fi #deepspace #timelessambience"""

schedule_video(
    vid4,
    "you arrive at the orbital ceramics workshop | cozy space ambient",
    desc4,
    f"{ROOT}/images/slate/04_orbital_ceramics.jpg",
    "ambient,cozy sci-fi,orbital ceramics,space ambient,deep space,hybrid sound,timeless ambience",
    "2026-09-03T18:00:00Z"
)

print("\n✨ ALL 4 SLATE VIDEOS PRODUCED, MASTERED, AND SCHEDULED ON YOUTUBE SUCCESSFULLY!")

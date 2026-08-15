#!/usr/bin/env python3
"""
Master script to generate and render 3 multi-engine hybrid samples:
1. Hybrid Duo (2 Engines: LatentScore + Multi-Layer Foley)
2. Hybrid Trio (3 Engines: LatentScore + Procedural DSP + Rubberband Sub)
3. Hybrid 5-Engine Ensemble (All 5 Engines: AI Director + LatentScore + Foley + DSP + Rubberband)
"""

import os
import sys
import json
import subprocess

ROOT = "/home/brewuser/projects/dronemill"
sys.path.append(f"{ROOT}/scripts")

from ai_hybrid_sound_conductor import build_hybrid_soundscape

os.makedirs(f"{ROOT}/audio/hybrid", exist_ok=True)
os.makedirs(f"{ROOT}/output", exist_ok=True)

# =========================================================================
# 1. GENERATE HYBRID AUDIO TRACKS
# =========================================================================

# Sample 1: 2-Engine Hybrid Duo
cfg_duo = {
    "title": "spinning neon in the rain",
    "duration": 60,
    "engines": {
        "latentscore": {
            "enabled": True,
            "wav": f"{ROOT}/audio/latentscore_diner.wav",
            "volume": 0.85,
            "filter": "highpass=f=100,lowpass=f=5500"
        },
        "foley": {
            "enabled": True,
            "samples": [
                f"{ROOT}/audio/samples/22_rain_window.mp3",
                f"{ROOT}/audio/samples/35_night_drive.mp3"
            ],
            "volume": 0.40,
            "filter": "highpass=f=120,lowpass=f=6500"
        }
    }
}
audio_duo = f"{ROOT}/audio/hybrid/sample_1_hybrid_duo.wav"
print("\n🎵 [1/3] Generating Hybrid Duo (LatentScore + Foley)...")
build_hybrid_soundscape(cfg_duo, audio_duo)

# Sample 2: 3-Engine Hybrid Trio
cfg_trio = {
    "title": "a kitchen drifting through the asteroid winter",
    "duration": 60,
    "engines": {
        "latentscore": {
            "enabled": True,
            "wav": f"{ROOT}/audio/latentscore_asteroid.wav",
            "volume": 0.75,
            "filter": "highpass=f=140,lowpass=f=5000"
        },
        "dsp": {
            "enabled": True,
            "frequencies": [116.54, 174.61, 233.08, 349.23], # Bb minor / F modal
            "lfos": [43, 59, 71, 89],
            "volume": 0.45
        },
        "rubberband": {
            "enabled": True,
            "source_wav": f"{ROOT}/audio/bases/batch3/asteroid-kitchen.wav",
            "semitones": -12,
            "volume": 0.80
        }
    }
}
audio_trio = f"{ROOT}/audio/hybrid/sample_2_hybrid_trio.wav"
print("\n🎵 [2/3] Generating Hybrid Trio (LatentScore + DSP + Rubberband)...")
build_hybrid_soundscape(cfg_trio, audio_trio)

# Sample 3: 5-Engine Hybrid Ensemble
cfg_ensemble = {
    "title": "the flooded palms at twilight",
    "duration": 60,
    "engines": {
        "latentscore": {
            "enabled": True,
            "wav": f"{ROOT}/audio/latentscore_conservatory.wav",
            "volume": 0.75,
            "filter": "highpass=f=120,lowpass=f=6000"
        },
        "foley": {
            "enabled": True,
            "samples": [
                f"{ROOT}/audio/samples/22_rain_window.mp3",
                f"{ROOT}/audio/samples/34_cave_drip.mp3"
            ],
            "volume": 0.35,
            "filter": "highpass=f=150,lowpass=f=7000"
        },
        "dsp": {
            "enabled": True,
            "frequencies": [87.31, 174.61, 261.63, 349.23, 440.00, 523.25], # F Lydian
            "lfos": [37, 53, 73, 97],
            "volume": 0.40
        },
        "rubberband": {
            "enabled": True,
            "source_wav": f"{ROOT}/audio/bases/batch3/mangrove-waterlines.wav",
            "semitones": -12,
            "volume": 0.70
        }
    }
}
audio_ensemble = f"{ROOT}/audio/hybrid/sample_3_hybrid_ensemble.wav"
print("\n🎵 [3/3] Generating Hybrid 5-Engine Ensemble (AI Director + LatentScore + Foley + DSP + Rubberband)...")
build_hybrid_soundscape(cfg_ensemble, audio_ensemble)

print("\n✨ ALL 3 HYBRID AUDIO TRACKS COMPILED AND MASTERED SUCCESSFULLY!")

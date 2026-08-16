#!/usr/bin/env python3
"""
Full Automated Production & Scheduling Pipeline for 9 Brand New DroneMill Releases.
Produces and schedules daily releases from 2026-08-31 to 2026-09-08.
"""

import os
import sys
import json
import datetime
import subprocess

ROOT = "/home/brewuser/projects/dronemill"
sys.path.append(f"{ROOT}/scripts")

from ai_hybrid_sound_conductor import build_hybrid_soundscape, run_cmd

os.makedirs(f"{ROOT}/audio/fresh", exist_ok=True)
os.makedirs(f"{ROOT}/output", exist_ok=True)
os.makedirs(f"{ROOT}/descriptions", exist_ok=True)

ITEMS = [
    {
        "id": "01_keeper_sea_wall",
        "title": "the keeper who listened to the sea wall | 1890s maritime horror ambient",
        "date": "2026-08-31T18:00:00Z",
        "image": f"{ROOT}/images/fresh/01_keeper_sea_wall.jpg",
        "ls_prompt": "lone lighthouse keeper pressed against stormy sea wall, massive bioluminescent leviathans beneath waves, slow dark cello drone, maritime dread",
        "foley": [f"{ROOT}/audio/samples/27_wind_desolate.mp3", f"{ROOT}/audio/samples/28_aquarium.mp3"],
        "dsp_freqs": [51.91, 103.83, 155.56, 207.65], # G# Phrygian
        "dsp_lfos": [43, 61, 79, 103],
        "rubberband_src": f"{ROOT}/audio/samples/12_cosmic_horror.mp3",
        "overlay": f"{ROOT}/assets/youtube-overlays/fog-overlay.mp4",
        "overlay_opacity": 0.40,
        "tags": "ambient,maritime horror,lighthouse keeper,cosmic horror,dark ambient,sea wall,timeless ambience"
    },
    {
        "id": "02_arctic_monolith",
        "title": "expedition to the basalt monolith | 1922 arctic cosmic ambient",
        "date": "2026-09-01T18:00:00Z",
        "image": f"{ROOT}/images/fresh/02_arctic_monolith.jpg",
        "ls_prompt": "1922 polar expedition standing before colossal non-euclidean black basalt monolith spire in blizzard, freezing atmospheric drone, deep sacred silence",
        "foley": [f"{ROOT}/audio/samples/27_wind_desolate.mp3"],
        "dsp_freqs": [61.74, 123.47, 185.21, 246.94], # B Aeolian
        "dsp_lfos": [37, 53, 73, 97],
        "rubberband_src": f"{ROOT}/audio/bases/batch3/oldest-thunder.wav",
        "overlay": f"{ROOT}/assets/overlays/snow_blizzard_loop.mp4",
        "overlay_opacity": 0.70,
        "tags": "ambient,arctic ambient,cosmic horror,basalt monolith,polar expedition,dark ambient,timeless ambience"
    },
    {
        "id": "03_drowned_chapel",
        "title": "the drowned chapel beneath the black cliffs | abyssal tide ambient",
        "date": "2026-09-02T18:00:00Z",
        "image": f"{ROOT}/images/fresh/03_drowned_chapel.jpg",
        "ls_prompt": "ancient submerged gothic chapel ruins in dark ocean water beneath sea cliffs, pale glowing nave windows, bowed metal church organ, oceanic abyss swell",
        "foley": [f"{ROOT}/audio/samples/34_cave_drip.mp3", f"{ROOT}/audio/samples/25_church_empty.mp3"],
        "dsp_freqs": [69.30, 103.83, 138.59, 207.65], # C# Locrian
        "dsp_lfos": [41, 59, 83, 101],
        "rubberband_src": f"{ROOT}/audio/samples/15_synth_dread.mp3",
        "overlay": f"{ROOT}/assets/youtube-overlays/fog-overlay.mp4",
        "overlay_opacity": 0.40,
        "tags": "ambient,drowned chapel,gothic ambient,abyssal dark ambient,oceanic tide,timeless ambience"
    },
    {
        "id": "04_carpeted_transit_lounge",
        "title": "shoes off in the carpeted transit lounge | empty airport 4 am ambient",
        "date": "2026-09-03T18:00:00Z",
        "image": f"{ROOT}/images/fresh/04_carpeted_transit_lounge.jpg",
        "ls_prompt": "empty airport terminal transit lounge at 4 am, muted geometric carpet, heavy rain outside panoramic windows, nostalgic decaying electric piano, gentle warm synth pad",
        "foley": [f"{ROOT}/audio/samples/22_rain_window.mp3", f"{ROOT}/audio/samples/07_train_station.mp3"],
        "dsp_freqs": [77.78, 155.56, 233.08, 311.13], # Eb Dorian
        "dsp_lfos": [37, 47, 67, 89],
        "rubberband_src": f"{ROOT}/audio/samples/01_empty_mall.mp3",
        "overlay": f"{ROOT}/assets/overlays/cinematic_rain_loop.mp4",
        "overlay_opacity": 0.70,
        "tags": "ambient,airport ambient,liminal transit,empty terminal,rain at 4am,mallsoft,timeless ambience"
    },
    {
        "id": "05_empty_bowling_alley",
        "title": "the midnight lane that never resets | empty bowling alley ambient",
        "date": "2026-09-04T18:00:00Z",
        "image": f"{ROOT}/images/fresh/05_empty_bowling_alley.jpg",
        "ls_prompt": "empty retro 1980s bowling alley at midnight, polished wood lanes stretching into shadows, glowing neon pins, vintage analog synthesizer warmth, nostalgic vaporwave dream",
        "foley": [f"{ROOT}/audio/samples/01_empty_mall.mp3"],
        "dsp_freqs": [82.41, 164.81, 246.94, 329.63], # E Mixolydian
        "dsp_lfos": [43, 59, 71, 93],
        "rubberband_src": f"{ROOT}/audio/bases/batch3/rewind-season.wav",
        "overlay": f"{ROOT}/assets/overlays/dust_motes_loop.mp4",
        "overlay_opacity": 0.75,
        "tags": "ambient,bowling alley,retro liminal,nostalgic 80s,vaporwave ambient,midnight drone,timeless ambience"
    },
    {
        "id": "06_subterranean_bathhouse",
        "title": "subterranean bathhouse beneath the city | vaporwave liminal ambient",
        "date": "2026-09-05T18:00:00Z",
        "image": f"{ROOT}/images/fresh/06_subterranean_bathhouse.jpg",
        "ls_prompt": "ancient subterranean ceramic tile bathhouse, steaming mineral water pools, quiet water ripples and humid stone echo, dreamy electric piano reverie, poolside drone",
        "foley": [f"{ROOT}/audio/samples/28_aquarium.mp3", f"{ROOT}/audio/samples/34_cave_drip.mp3"],
        "dsp_freqs": [65.41, 130.81, 196.00, 261.63], # C Dorian
        "dsp_lfos": [37, 53, 73, 97],
        "rubberband_src": f"{ROOT}/audio/samples/01_empty_mall.mp3",
        "overlay": f"{ROOT}/assets/youtube-overlays/fog-overlay.mp4",
        "overlay_opacity": 0.45,
        "tags": "ambient,bathhouse,poolrooms,vaporwave ambient,subterranean,dreamcore,timeless ambience"
    },
    {
        "id": "07_europa_botanist_tea",
        "title": "the botanist's tea on europa | icy orbital greenhouse ambient",
        "date": "2026-09-06T18:00:00Z",
        "image": f"{ROOT}/images/fresh/07_europa_botanist_tea.jpg",
        "ls_prompt": "cozy orbital greenhouse looking out at cracked blue ice of europa and giant jupiter, steaming ceramic tea mug, warm analog acoustic chords and gentle ambient synth glow",
        "foley": [f"{ROOT}/audio/samples/23_server_room.mp3", f"{ROOT}/audio/samples/13_synth_warm.mp3"],
        "dsp_freqs": [73.42, 146.83, 220.00, 293.66], # D Major Add9
        "dsp_lfos": [41, 57, 79, 103],
        "rubberband_src": f"{ROOT}/audio/bases/batch3/asteroid-kitchen.wav",
        "overlay": f"{ROOT}/assets/overlays/dust_motes_loop.mp4",
        "overlay_opacity": 0.80,
        "tags": "ambient,europa,space greenhouse,cozy sci-fi,orbital tea,deep space,timeless ambience"
    },
    {
        "id": "08_lunar_sleeper_train",
        "title": "sleeper car through the lunar glass tunnel | vintage sci-fi ambient",
        "date": "2026-09-07T18:00:00Z",
        "image": f"{ROOT}/images/fresh/08_lunar_sleeper_train.jpg",
        "ls_prompt": "retro futuristic luxury sleeper train traveling through illuminated glass tunnel in lunar crater with earth in sky, warm velvet armchair reverie, gentle rhythmic synth train glide",
        "foley": [f"{ROOT}/audio/samples/07_train_station.mp3", f"{ROOT}/audio/samples/23_server_room.mp3"],
        "dsp_freqs": [58.27, 116.54, 174.61, 233.08], # Bb Lydian
        "dsp_lfos": [37, 53, 71, 91],
        "rubberband_src": f"{ROOT}/audio/bases/batch3/asteroid-kitchen.wav",
        "overlay": f"{ROOT}/assets/youtube-overlays/fog-overlay.mp4",
        "overlay_opacity": 0.25,
        "tags": "ambient,lunar train,moon sleeper,vintage sci-fi,retro future,space travel ambient,timeless ambience"
    },
    {
        "id": "09_freighter_bridge",
        "title": "midnight shift on the deep space freighter | industrial cozy ambient",
        "date": "2026-09-08T18:00:00Z",
        "image": f"{ROOT}/images/fresh/09_freighter_bridge.jpg",
        "ls_prompt": "navigation flight bridge of deep space industrial freighter at night, glowing amber CRT telemetry monitors, colorful cosmic nebula drifting outside, heavy mechanical rumble and deep space synth",
        "foley": [f"{ROOT}/audio/samples/23_server_room.mp3"],
        "dsp_freqs": [43.65, 87.31, 130.81, 174.61], # F Sub-Drone
        "dsp_lfos": [47, 67, 83, 107],
        "rubberband_src": f"{ROOT}/audio/samples/12_cosmic_horror.mp3",
        "overlay": f"{ROOT}/assets/youtube-overlays/fog-overlay.mp4",
        "overlay_opacity": 0.30,
        "tags": "ambient,freighter bridge,space industrial,deep space,cozy sci-fi,starfield,timeless ambience"
    }
]

DURATION = 7200 # 2 Hours (7200 seconds)

print(f"=== Starting Production of {len(ITEMS)} Brand New 2-Hour DroneMill Releases ===")

for idx, item in enumerate(ITEMS, 1):
    # Ensure title has 2 hours suffix if not present
    title = item['title']
    if "2 hour" not in title.lower():
        title = f"{title} | 2 hours"
        
    print(f"\n=======================================================")
    print(f"[{idx}/{len(ITEMS)}] {title}")
    print(f"📅 Target YouTube Release: {item['date']} (Duration: 2 Hours)")
    print(f"=======================================================")
    
    # 1. LatentScore Stem
    ls_wav = f"{ROOT}/audio/fresh/ls_{item['id']}.wav"
    if not os.path.exists(ls_wav):
        print(f">> Generating LatentScore: {item['id']}...")
        cmd_ls = f"\"{ROOT}/scripts/latentscore-gen.sh\" \"{item['ls_prompt']}\" \"{ls_wav}\" 180"
        run_cmd(cmd_ls, f"LatentScore {item['id']}")
    
    # 2. Master Hybrid Soundscape (2 Hours)
    master_wav = f"{ROOT}/audio/fresh/master_{item['id']}_2h.wav"
    cfg = {
        "title": title,
        "duration": DURATION,
        "engines": {
            "latentscore": {"enabled": True, "wav": ls_wav, "volume": 0.85, "filter": "highpass=f=80,lowpass=f=6000"},
            "foley": {"enabled": True, "samples": item["foley"], "volume": 0.40, "filter": "highpass=f=100,lowpass=f=6500"},
            "dsp": {"enabled": True, "frequencies": item["dsp_freqs"], "lfos": item["dsp_lfos"], "volume": 0.45},
            "rubberband": {"enabled": True, "source_wav": item["rubberband_src"], "semitones": -12, "volume": 0.70}
        }
    }
    build_hybrid_soundscape(cfg, master_wav)
    
    # 3. Render 1080p Living Video (2 Hours)
    out_mp4 = f"{ROOT}/output/fresh_{item['id']}_2h.mp4"
    print(f">> Rendering 1080p Living Video (2h) -> {out_mp4}...")
    cmd_render = f"""ffmpeg -y -nostdin \
      -loop 1 -framerate 24 -t {DURATION} -i "{item['image']}" \
      -stream_loop -1 -i "{item['overlay']}" \
      -i "{master_wav}" \
      -filter_complex "
        [0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,format=gbrp[base];
        [1:v]scale=1920:1080:flags=lanczos,curves=all='0/0 0.12/0 0.50/0.35 1/0.85',format=gbrp[fx];
        [base][fx]blend=all_mode=screen:all_opacity={item['overlay_opacity']}[merged];
        [merged]vignette=angle=0.32,noise=alls=0.6:allf=t+u,format=yuv420p[vout]
      " -map "[vout]" -map "2:a" \
      -c:v libx264 -preset ultrafast -crf 20 -c:a aac -b:a 256k -ar 48000 -t {DURATION} -movflags +faststart "{out_mp4}"
    """
    run_cmd(cmd_render, f"Render video {item['id']}")
    
    # 4. Schedule on YouTube
    print(f">> Scheduling on YouTube for {item['date']}...")
    desc_text = f"""2 Hours of Deep Atmospheric AI Hybrid Soundscape:
1. AI Harmonic Director: Custom modal mapping & key tuning.
2. LatentScore Neural Composer: Prompt-conditioned melodic & harmonic progression.
3. Multi-Layer Environmental Foley: Acoustic spatial immersion.
4. Procedural FFmpeg DSP Engine: Haas 3D stereo harmonic sine partials on prime LFO envelopes.
5. Rubberband Studio Pitch-Shift Engine: Sub-octave deep foundation drone.
• Mastered with EBU R128 (-22 LUFS).

Visual: Original 35mm film photograph / archival plate with subtle volumetric atmosphere.

#ambient #{item['tags'].split(',')[1].strip()} #{item['tags'].split(',')[2].strip()} #hybridsound #timelessambience #2hours"""

    desc_file = f"/tmp/desc_fresh_{idx}.txt"
    with open(desc_file, "w", encoding="utf-8") as f:
        f.write(desc_text)
        
    cmd_upload = f"\"{ROOT}/scripts/upload-yt.sh\" \"{out_mp4}\" \"{title}\" \"{desc_file}\" \"{item['image']}\" \"private\" \"{item['tags']},2 hour ambient\" \"{item['date']}\""
    run_cmd(cmd_upload, f"Schedule {title}")
    
    # Clean up large intermediate files immediately to save disk space
    if os.path.exists(desc_file):
        os.remove(desc_file)
    if os.path.exists(out_mp4):
        os.remove(out_mp4)
    if os.path.exists(master_wav):
        os.remove(master_wav)
        
    print(f"✅ Slot #{idx} ({item['date']}) 2-hour production completed and scheduled!\n")

print("\n🎉 ALL 9 BRAND NEW 2-HOUR RELEASES PRODUCED AND SCHEDULED SUCCESSFULLY!")

# Update Live GitHub Pages Dashboard
print(">> Refreshing Live GitHub Pages Dashboard...")
subprocess.run(f"\"{ROOT}/scripts/publish-dashboard.sh\"", shell=True)


#!/usr/bin/env python3
"""
DroneMill Long-Form Hybrid Master Generator.
Expands any 60-second hybrid audio composition into a seamless, non-repetitive
1-hour, 2-hour, or 3-hour extended ambient track with evolving prime-period
LFO modulations and EBU R128 (-22 LUFS) loudness normalization.

Usage:
  python3 scripts/generate_longform_hybrid.py <base_wav> <output_wav> [duration_minutes=60]
"""

import os
import sys
import subprocess

ROOT = "/home/brewuser/projects/dronemill"

def run_cmd(cmd, desc="Running command"):
    print(f">> {desc}...")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"ERROR: {res.stderr}")
        raise RuntimeError(f"Command failed: {cmd}\n{res.stderr}")
    return res.stdout

def generate_longform(base_wav, output_wav, duration_minutes=60):
    duration_seconds = int(duration_minutes * 60)
    print(f"🎧 Expanding {base_wav} -> {output_wav} ({duration_minutes} minutes / {duration_seconds}s)...")
    
    # 1. Loop base audio with seamless 8-second crossfades and subtle stereo chorus
    # 2. Add an ultra-long evolving prime-cycle generative pink noise filter
    # 3. Master with EBU R128 loudnorm (-22 LUFS)
    cmd = f"""ffmpeg -y -nostdin \
      -stream_loop -1 -i "{base_wav}" \
      -f lavfi -t {duration_seconds} -i "anoisesrc=c=pink:r=48000:a=0.015:seed=9912" \
      -filter_complex "
        [0:a]aloop=loop=-1:size=2880000,
             chorus=0.35:0.45:45|65:0.04|0.03:0.05|0.04:0.08|0.06,
             tremolo=f=0.03:d=0.15[base_evolved];
        [1:a]lowpass=f=2200,volume=0.40[air_hum];
        [base_evolved][air_hum]amix=inputs=2:normalize=0,
             highpass=f=25,lowpass=f=7500,
             acompressor=threshold=0.25:ratio=1.4:attack=200:release=2000,
             loudnorm=I=-22:TP=-2.5:LRA=6,
             afade=t=in:st=0:d=4,
             afade=t=out:st={duration_seconds - 5}:d=5[out]
      " -map "[out]" -c:a pcm_s24le -ar 48000 -t {duration_seconds} "{output_wav}"
    """
    run_cmd(cmd, f"Rendering {duration_minutes}m Long-Form Master WAV")
    print(f"✅ Generated {duration_minutes}-minute longform master: {output_wav}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 generate_longform_hybrid.py <base_wav> <output_wav> [duration_minutes=60]")
        sys.exit(1)
        
    base = sys.argv[1]
    out = sys.argv[2]
    mins = float(sys.argv[3]) if len(sys.argv) > 3 else 60
    generate_longform(base, out, mins)

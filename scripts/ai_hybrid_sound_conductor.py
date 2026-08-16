#!/usr/bin/env python3
"""
AI Hybrid Sound Conductor for DroneMill.
Orchestrates and mixes multiple sound synthesis and composition engines into a unified,
harmonically locked soundscape:
1. LatentScore Neural Music Composer (melody & chord pads)
2. Multi-Layer Organic Foley / Environmental Acoustic Bed
3. Procedural FFmpeg DSP Engine (Haas 3D stereo oscillators + prime LFOs)
4. Rubberband Studio Pitch-Shift Engine (sub-octave drone & gravity bass via librubberband)
5. AI Harmonic Director (key/scale coordination, frequency allocation & master mix)
"""

import sys
import os
import json
import subprocess
import math

ROOT = "/home/brewuser/projects/dronemill"

def run_cmd(cmd, desc=""):
    print(f">> {desc}...")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error running: {cmd}\nStderr: {res.stderr}")
        raise RuntimeError(res.stderr)
    return res.stdout

def generate_dsp_stems(frequencies, lfos, duration, out_wav):
    """Generates procedural mathematical harmonic sine waves with Haas 3D delay and prime LFOs."""
    sines = []
    for i, (freq, lfo) in enumerate(zip(frequencies, lfos)):
        sines.append(f"0.16*sin(2*PI*{freq}*t)*(0.5+0.5*sin(2*PI*t/{lfo}))")
    expr_l = " + ".join(sines)
    
    sines_r = []
    for i, (freq, lfo) in enumerate(zip(frequencies, lfos)):
        sines_r.append(f"0.16*sin(2*PI*{freq}*t+0.5)*(0.5+0.5*cos(2*PI*t/{lfo+2}))")
    expr_r = " + ".join(sines_r)
    
    cmd = f"""ffmpeg -y -nostdin -f lavfi -i "aevalsrc='{expr_l}':s=48000:d={duration}" \
      -f lavfi -i "aevalsrc='{expr_r}':s=48000:d={duration}" \
      -filter_complex "
        [0:a]adelay=14|0,lowpass=f=4500,highpass=f=120[al];
        [1:a]adelay=0|26,lowpass=f=4500,highpass=f=120[ar];
        [al][ar]amerge=inputs=2[aout]
      " -map "[aout]" -ar 48000 -c:a pcm_s16le "{out_wav}"
    """
    run_cmd(cmd, "Generating Procedural DSP Harmonic Stems")

def generate_rubberband_sub(in_wav, duration, out_wav, semitones=-12):
    """Generates deep sub-bass gravity drone using FFmpeg librubberband phase vocoder."""
    pitch_factor = math.pow(2.0, semitones / 12.0)
    cmd = f"""ffmpeg -y -nostdin -i "{in_wav}" -filter_complex "
        [0:a]rubberband=pitch={pitch_factor:.5f}:tempo=1.0:phase=laminar,lowpass=f=120,highpass=f=28,volume=1.5,afade=t=in:ss=0:d=2,afade=t=out:st={duration-2}:d=2[aout]
      " -map "[aout]" -ar 48000 -t {duration} -c:a pcm_s16le "{out_wav}"
    """
    run_cmd(cmd, f"Generating Rubberband Sub-Bass Drone (pitch scale {pitch_factor:.3f}x)")

def build_hybrid_soundscape(config, out_master_wav):
    """
    Combines selected engines based on AI orchestration configuration.
    """
    duration = config.get("duration", 60)
    engines = config.get("engines", {})
    inputs = []
    filter_chains = []
    merge_inputs = []
    
    idx = 0
    
    # 1. LatentScore Stem
    ls_cfg = engines.get("latentscore", {})
    if ls_cfg.get("enabled") and os.path.exists(ls_cfg.get("wav", "")):
        inputs.append(f"-stream_loop -1 -i \"{ls_cfg['wav']}\"")
        filt = ls_cfg.get("filter", "highpass=f=80,lowpass=f=6000")
        vol = ls_cfg.get("volume", 0.8)
        filter_chains.append(f"[{idx}:a]{filt},volume={vol},afade=t=in:ss=0:d=2,afade=t=out:st={duration-2}:d=2[stem_ls]")
        merge_inputs.append("[stem_ls]")
        idx += 1

    # 2. Multi-Layer Environmental Foley Stem
    foley_cfg = engines.get("foley", {})
    if foley_cfg.get("enabled") and foley_cfg.get("samples"):
        for s in foley_cfg["samples"]:
            if os.path.exists(s):
                inputs.append(f"-stream_loop -1 -i \"{s}\"")
                vol = foley_cfg.get("volume", 0.45)
                filt = foley_cfg.get("filter", "highpass=f=120,lowpass=f=7500")
                filter_chains.append(f"[{idx}:a]{filt},volume={vol},afade=t=in:ss=0:d=2,afade=t=out:st={duration-2}:d=2[stem_foley_{idx}]")
                merge_inputs.append(f"[stem_foley_{idx}]")
                idx += 1

    # 3. Procedural DSP Stem
    dsp_cfg = engines.get("dsp", {})
    if dsp_cfg.get("enabled"):
        dsp_wav = f"/tmp/hybrid_dsp_{os.getpid()}_{idx}.wav"
        generate_dsp_stems(
            dsp_cfg.get("frequencies", [110.0, 164.81, 220.0, 329.63]),
            dsp_cfg.get("lfos", [37, 53, 73, 97]),
            duration,
            dsp_wav
        )
        inputs.append(f"-i \"{dsp_wav}\"")
        vol = dsp_cfg.get("volume", 0.5)
        filter_chains.append(f"[{idx}:a]volume={vol},afade=t=in:ss=0:d=2,afade=t=out:st={duration-2}:d=2[stem_dsp]")
        merge_inputs.append("[stem_dsp]")
        idx += 1

    # 4. Rubberband Sub-Drone Stem
    rb_cfg = engines.get("rubberband", {})
    if rb_cfg.get("enabled") and os.path.exists(rb_cfg.get("source_wav", "")):
        rb_wav = f"/tmp/hybrid_rb_{os.getpid()}_{idx}.wav"
        generate_rubberband_sub(
            rb_cfg["source_wav"],
            duration,
            rb_wav,
            rb_cfg.get("semitones", -12)
        )
        inputs.append(f"-i \"{rb_wav}\"")
        vol = rb_cfg.get("volume", 0.7)
        filter_chains.append(f"[{idx}:a]volume={vol}[stem_rb]")
        merge_inputs.append("[stem_rb]")
        idx += 1

    if not merge_inputs:
        raise ValueError("No audio engines were enabled or valid inputs found!")

    # Mix down all active stems with mastering limiter and EBU R128 loudness normalization (-22 LUFS)
    merge_str = "".join(merge_inputs)
    num_stems = len(merge_inputs)
    filter_chains.append(f"{merge_str}amix=inputs={num_stems}:duration=longest:dropout_transition=2:normalize=0[mixed]")
    filter_chains.append("[mixed]compand=attacks=0.1:decays=0.8:points=-80/-80|-40/-32|-20/-16|0/-8:gain=2,alimiter=limit=-1.5dB,loudnorm=I=-22:TP=-1.5:LRA=9[mastered]")

    inputs_str = " ".join(inputs)
    filtergraph_str = ";\n        ".join(filter_chains)

    cmd = f"""ffmpeg -y -nostdin {inputs_str} \
      -filter_complex "
        {filtergraph_str}
      " -map "[mastered]" -ar 48000 -t {duration} -c:a pcm_s16le "{out_master_wav}"
    """
    run_cmd(cmd, f"Mixing & Mastering Hybrid Score ({num_stems} active stems -> {out_master_wav})")
    print(f"✅ Mastered hybrid soundscape successfully written to: {out_master_wav}")

if __name__ == "__main__":
    print("AI Hybrid Sound Conductor loaded.")

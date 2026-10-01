#!/usr/bin/env python3
"""
AI Hybrid Sound Conductor for DroneMill.
Orchestrates and mixes multiple sound synthesis and composition engines into a unified,
harmonically locked soundscape:
1. LatentScore Neural Music Composer (melody & chord pads)
2. Multi-Layer Organic Foley / Environmental Acoustic Bed (decorrelated loops)
3. Procedural FFmpeg DSP Engine (Haas 3D stereo oscillators + prime LFOs)
4. Synth Sub Engine (sub drone locked to the concept root)
5. Texture Engine (brown + pink noise beds with slow crossfading and autopan)
6. Rubberband Studio Pitch-Shift Engine (legacy sub-octave drone via librubberband, looped)
7. Musical layers via ambient_layers.py: chord pad, formant choir, melodic phrases, sparse events
8. Reverb Bus (synthesized stereo impulse response, convolution via afir)

Synth layers are generated inline as lavfi sources, so no multi-gigabyte temp stems are
written to disk. Every random choice derives from config["seed"] (falls back to the output
path), so a given concept always renders the same audio and different concepts differ.

Mastering: two-pass. Pass 1 measures the raw mix (EBU R128), pass 2 applies one static
gain to hit TARGET_LUFS plus a peak limiter. No compander and no dynamic loudnorm, so the
level does not "breathe" over a 2h render.
"""

import sys
import os
import re
import json
import hashlib
import subprocess
import math

ROOT = "/home/brewuser/projects/dronemill"
TMP_DIR = os.path.join(ROOT, "tmp")
os.makedirs(TMP_DIR, exist_ok=True)

TARGET_LUFS = -16.0       # matches the channel's best-performing originals (-15..-16 LUFS)
PEAK_LIMIT = 0.75         # ~ -2.5 dBFS sample peak, headroom for AAC encoding overs
FADE_IN_SEC = 20
FADE_OUT_SEC = 30
MEASURE_SEC = 900          # the mix is stationary; 15 min measures within ~0.5 LU of the full 2h
PRIMES = [71, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151]


def run_cmd(cmd, desc=""):
    print(f">> {desc}...")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error running: {cmd}\nStderr: {res.stderr}")
        raise RuntimeError(res.stderr)
    return res.stdout


class _Seed:
    """Deterministic stream of pseudo-random values derived from a string seed."""

    def __init__(self, seed):
        self.base = str(seed)
        self.n = 0

    def _next_bytes(self):
        self.n += 1
        return hashlib.sha256(f"{self.base}:{self.n}".encode("utf-8")).digest()

    def uniform(self, lo, hi):
        v = int.from_bytes(self._next_bytes()[:4], "big") / 0xFFFFFFFF
        return lo + (hi - lo) * v

    def choice(self, items):
        return items[int.from_bytes(self._next_bytes()[:4], "big") % len(items)]

    def int(self, lo, hi):
        return lo + int.from_bytes(self._next_bytes()[:4], "big") % (hi - lo + 1)


def _dsp_exprs(frequencies, lfos):
    """Harmonic sine partials with prime-period amplitude LFOs (left/right differ in phase)."""
    left = " + ".join(f"0.16*sin(2*PI*{f}*t)*(0.5+0.5*sin(2*PI*t/{l}))" for f, l in zip(frequencies, lfos))
    right = " + ".join(f"0.16*sin(2*PI*{f}*t+0.5)*(0.5+0.5*cos(2*PI*t/{l + 2}))" for f, l in zip(frequencies, lfos))
    return left, right


def generate_dsp_stems(frequencies, lfos, duration, out_wav):
    """Renders the DSP harmonic layer to a wav (kept for scripts that want a standalone stem)."""
    expr_l, expr_r = _dsp_exprs(frequencies, lfos)
    cmd = f"""ffmpeg -y -nostdin -f lavfi -i "aevalsrc='{expr_l}|{expr_r}':s=48000:d={duration}" \
      -af "adelay=14|26,lowpass=f=4500,highpass=f=30" -ar 48000 -c:a pcm_s16le "{out_wav}"
    """
    run_cmd(cmd, "Generating Procedural DSP Harmonic Stems")


def generate_rubberband_sub(in_wav, duration, out_wav, semitones=-12):
    """Legacy sub-bass drone via librubberband. Input is looped to cover the full duration
    (sources are 90s samples; previously the stem stopped after 90s)."""
    pitch_factor = math.pow(2.0, semitones / 12.0)
    cmd = f"""ffmpeg -y -nostdin -stream_loop -1 -i "{in_wav}" -filter_complex "
        [0:a]rubberband=pitch={pitch_factor:.5f}:tempo=1.0:phase=laminar,lowpass=f=120,highpass=f=28,volume=1.5[aout]
      " -map "[aout]" -ar 48000 -t {duration} -c:a pcm_s16le "{out_wav}"
    """
    run_cmd(cmd, f"Generating Rubberband Sub-Bass Drone (pitch scale {pitch_factor:.3f}x)")


def generate_reverb_ir(out_wav, decay=2.6, length=9.0, seed="dronemill"):
    """Synthesizes a dark stereo hall impulse response: decorrelated noise with an exponential
    decay, a short predelay and high frequencies rolled off. Tiny file (a few MB)."""
    rng = _Seed(f"{seed}:ir")
    i_l, i_r = rng.int(0, 7), rng.int(0, 7)
    tau_l = decay
    tau_r = decay * rng.uniform(1.03, 1.10)
    cmd = f"""ffmpeg -y -nostdin -f lavfi -i "aevalsrc='(random({i_l})*2-1)*exp(-t/{tau_l:.3f})|(random({i_r})*2-1)*exp(-t/{tau_r:.3f})':s=48000:d={length}" \
      -af "adelay=35|47,lowpass=f=3800,lowpass=f=5200,highpass=f=90" -ar 48000 -c:a pcm_f32le "{out_wav}"
    """
    run_cmd(cmd, f"Synthesizing reverb impulse response ({length}s, decay {decay}s)")


def _render_np_stem(fn, duration, out_path, channels=2, sr=48000, chunk_sec=30):
    """Renders fn(t) -> (n, channels) float array for the full duration in chunks and pipes it
    into ffmpeg as FLAC. Pure array math, so phase is continuous across chunks (no seams) and a
    2h stem takes seconds instead of the ~0.2x realtime of aevalsrc."""
    import numpy as np
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-nostdin", "-loglevel", "error", "-f", "f32le", "-ar", str(sr),
         "-ac", str(channels), "-i", "-", "-c:a", "flac", out_path],
        stdin=subprocess.PIPE)
    total = int(duration * sr)
    step = int(chunk_sec * sr)
    clipped = 0
    try:
        for start in range(0, total, step):
            n = min(step, total - start)
            t = (np.arange(n, dtype=np.float64) + start) / sr
            y = fn(t)
            peak = float(np.max(np.abs(y))) if len(y) else 0.0
            if peak > 1.0:
                clipped += 1
            proc.stdin.write(np.ascontiguousarray(np.clip(y, -1.0, 1.0), dtype=np.float32).tobytes())
    finally:
        proc.stdin.close()
        proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed writing {out_path}")
    if clipped:
        print(f"WARN: {clipped} chunk(s) of {os.path.basename(out_path)} exceeded full scale and were clipped")


def _dsp_np(frequencies, lfos):
    import numpy as np

    def fn(t):
        tl, tr = t - 0.014, t - 0.026  # Haas offsets (14 ms / 26 ms)
        left = sum(0.16 * np.sin(2 * np.pi * f * tl) * (0.5 + 0.5 * np.sin(2 * np.pi * tl / l))
                   for f, l in zip(frequencies, lfos))
        right = sum(0.16 * np.sin(2 * np.pi * f * tr + 0.5) * (0.5 + 0.5 * np.cos(2 * np.pi * tr / (l + 2)))
                    for f, l in zip(frequencies, lfos))
        return np.stack([left, right], axis=1)
    return fn


def _sub_np(root, rng):
    """Mono sub drone locked to the concept root.

    Fundamental sits at root (or root/2 when root >= 80 Hz) so it stays in the 40-80 Hz band.
    A quiet, barely detuned twin gives slow beating (10-30 s period, not a pulse); a quiet
    2nd harmonic keeps it audible on small speakers.
    """
    import numpy as np
    f = root / 2.0 if root >= 80 else root
    beat_period = rng.uniform(10, 30)
    lfo_a = rng.choice(PRIMES)
    lfo_b = rng.choice(PRIMES) + 0.5

    def fn(t):
        y = (0.50 * np.sin(2 * np.pi * f * t) * (0.85 + 0.15 * np.sin(2 * np.pi * t / lfo_a))
             + 0.12 * np.sin(2 * np.pi * (f + 1.0 / beat_period) * t)
             + 0.10 * np.sin(2 * np.pi * 2 * f * t + 0.3) * (0.6 + 0.4 * np.sin(2 * np.pi * t / lfo_b)))
        return y[:, None]
    return fn, f


def _measure_loudness(inputs_str, filtergraph_str, duration):
    """Pass 1: integrated loudness and peak of the raw mix."""
    cmd = f"""ffmpeg -nostdin -hide_banner {inputs_str} \
      -filter_complex "
        {filtergraph_str};
        [mixed]loudnorm=I={TARGET_LUFS}:TP=-2:LRA=11:print_format=json[meas]
      " -map "[meas]" -t {min(duration, MEASURE_SEC)} -f null -
    """
    print(f">> Pass 1: measuring raw mix loudness (first {min(duration, MEASURE_SEC)}s)...")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(res.stderr)
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", res.stderr, re.S)
    if not m:
        raise RuntimeError("loudness measurement failed: no loudnorm JSON in output")
    data = json.loads(m.group(0))
    return float(data["input_i"]), float(data["input_tp"])


def _probe_duration(path):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
            capture_output=True, text=True).stdout.strip()
        return float(out)
    except Exception:
        return 0.0


def build_hybrid_soundscape(config, out_master_wav):
    """
    Combines selected engines based on AI orchestration configuration.
    """
    duration = config.get("duration", 60)
    engines = config.get("engines", {})
    rng = _Seed(config.get("seed") or engines.get("sub", {}).get("seed") or out_master_wav)
    inputs = []
    filter_chains = []
    merge_inputs = []
    temp_stems = []

    rev_cfg = engines.get("reverb", {})
    reverb_on = bool(rev_cfg.get("enabled"))
    sends = []  # (label, send_gain)

    def add_stem(label, chain, send=0.0):
        """chain ends without an output label; routes a dry copy to the mix and, when the
        reverb bus is on, a second copy to the reverb send."""
        if reverb_on and send > 0:
            filter_chains.append(f"{chain},asplit=2[{label}][{label}_s]")
            sends.append((f"{label}_s", send))
        else:
            filter_chains.append(f"{chain}[{label}]")
        merge_inputs.append(f"[{label}]")

    idx = 0
    try:
        # 1. LatentScore Stem
        ls_cfg = engines.get("latentscore", {})
        if ls_cfg.get("enabled") and os.path.exists(ls_cfg.get("wav", "")):
            inputs.append(f"-stream_loop -1 -i \"{ls_cfg['wav']}\"")
            filt = ls_cfg.get("filter", "highpass=f=80,lowpass=f=6000")
            vol = ls_cfg.get("volume", 0.8)
            add_stem("stem_ls", f"[{idx}:a]{filt},volume={vol}", ls_cfg.get("send", 0.5))
            idx += 1

        # 2. Multi-Layer Environmental Foley Stem
        # Each layer starts at a different offset and runs at a slightly different speed,
        # so loop points never line up across layers or repeat on a fixed grid.
        foley_cfg = engines.get("foley", {})
        if foley_cfg.get("enabled") and foley_cfg.get("samples"):
            for s in foley_cfg["samples"]:
                if os.path.exists(s):
                    length = _probe_duration(s)
                    offset = rng.uniform(0, max(0.0, length - 1)) if length > 2 else 0.0
                    tempo = rng.uniform(0.96, 1.04)
                    inputs.append(f"-stream_loop -1 -ss {offset:.2f} -i \"{s}\"")
                    vol = foley_cfg.get("volume", 0.45)
                    filt = foley_cfg.get("filter", "highpass=f=120,lowpass=f=7500")
                    add_stem(f"stem_foley_{idx}",
                             f"[{idx}:a]aresample=48000,atempo={tempo:.4f},{filt},volume={vol}",
                             foley_cfg.get("send", 0.6))
                    idx += 1

        # 3. Procedural DSP Stem (numpy, rendered once to FLAC)
        dsp_cfg = engines.get("dsp", {})
        if dsp_cfg.get("enabled"):
            dsp_path = f"{TMP_DIR}/hybrid_dsp_{os.getpid()}_{idx}.flac"
            temp_stems.append(dsp_path)
            print(">> Rendering procedural DSP harmonic stem...")
            _render_np_stem(_dsp_np(dsp_cfg.get("frequencies", [110.0, 164.81, 220.0, 329.63]),
                                    dsp_cfg.get("lfos", [37, 53, 73, 97])), duration, dsp_path, 2)
            inputs.append(f"-i \"{dsp_path}\"")
            vol = dsp_cfg.get("volume", 0.5)
            # highpass at 30 Hz (was 120 Hz, which removed the root and most low partials)
            add_stem("stem_dsp", f"[{idx}:a]highpass=f=30,volume={vol}", dsp_cfg.get("send", 0.5))
            idx += 1

        # 4. Synth Sub Stem (numpy mono FLAC, locked to concept root, always dry)
        sub_cfg = engines.get("sub", {})
        if sub_cfg.get("enabled") and sub_cfg.get("root"):
            sub_fn, sub_f = _sub_np(float(sub_cfg["root"]), rng)
            print(f">> Synth sub drone: root {sub_cfg['root']} Hz -> {sub_f:.2f} Hz")
            sub_path = f"{TMP_DIR}/hybrid_sub_{os.getpid()}_{idx}.flac"
            temp_stems.append(sub_path)
            _render_np_stem(sub_fn, duration, sub_path, 1)
            inputs.append(f"-i \"{sub_path}\"")
            vol = sub_cfg.get("volume", 0.28)
            add_stem("stem_sub", f"[{idx}:a]pan=stereo|c0=c0|c1=c0,lowpass=f=180,highpass=f=25,volume={vol}")
            idx += 1

        # 5. Texture Stem (inline): brown noise body + pink noise air, slowly crossfading
        tex_cfg = engines.get("texture", {})
        if tex_cfg.get("enabled"):
            seeds = [rng.int(1, 2**31 - 2) for _ in range(4)]
            for color, sd in zip(["brown", "brown", "pink", "pink"], seeds):
                inputs.append(f"-f lavfi -i \"anoisesrc=c={color}:a=0.5:r=48000:seed={sd}:d={duration}\"")
            p_body = rng.choice(PRIMES) * 2 + 1
            p_air = rng.choice(PRIMES) * 2 + 3
            pan_hz = rng.uniform(0.011, 0.02)
            body_lp = tex_cfg.get("body_lowpass", 380)
            air_bp = tex_cfg.get("air_band", [350, 1800])
            vol = tex_cfg.get("volume", 0.5)
            filter_chains.append(
                f"[{idx}:a][{idx + 1}:a]amerge=inputs=2,lowpass=f={body_lp},lowpass=f={body_lp},"
                f"volume='0.55+0.45*sin(2*PI*t/{p_body})':eval=frame[tex_body]")
            filter_chains.append(
                f"[{idx + 2}:a][{idx + 3}:a]amerge=inputs=2,highpass=f={air_bp[0]},lowpass=f={air_bp[1]},"
                f"volume='0.45+0.45*sin(2*PI*t/{p_air}+1.3)':eval=frame,volume=0.5[tex_air]")
            add_stem("stem_tex",
                     f"[tex_body][tex_air]amix=inputs=2:normalize=0,"
                     f"apulsator=hz={pan_hz:.4f}:amount=0.35,volume={vol}",
                     tex_cfg.get("send", 0.3))
            idx += 4

        # 6. Rubberband Sub-Drone Stem (legacy, pre-rendered)
        rb_cfg = engines.get("rubberband", {})
        if rb_cfg.get("enabled") and os.path.exists(rb_cfg.get("source_wav", "")):
            rb_wav = f"{TMP_DIR}/hybrid_rb_{os.getpid()}_{idx}.wav"
            temp_stems.append(rb_wav)
            generate_rubberband_sub(rb_cfg["source_wav"], duration, rb_wav, rb_cfg.get("semitones", -12))
            inputs.append(f"-i \"{rb_wav}\"")
            vol = rb_cfg.get("volume", 0.7)
            add_stem("stem_rb", f"[{idx}:a]volume={vol}")
            idx += 1

        # 7. Musical layers (numpy): chord pad, formant choir, melodic phrases, sparse events.
        # All share config["preset"] ("lovecraft" | "historical" | "fantasy") and the concept root.
        layer_defaults = {"pad": (0.8, 0.5), "choir": (0.6, 0.7), "melody": (0.6, 0.7), "events": (0.5, 0.9),
                          "fire": (0.5, 0.15)}
        layer_names = [n for n in layer_defaults if engines.get(n, {}).get("enabled")]
        if layer_names:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import ambient_layers
            root = (config.get("root") or sub_cfg.get("root")
                    or (dsp_cfg.get("frequencies") or [55.0])[0])
            preset_name = config.get("preset", "lovecraft")
            preset = ambient_layers.resolve_preset(preset_name, config.get("preset_overrides"))
            builders = ambient_layers.layer_builders(float(root), rng.base, duration, preset)
            for name in layer_names:
                layer_path = f"{TMP_DIR}/hybrid_{name}_{os.getpid()}_{idx}.flac"
                temp_stems.append(layer_path)
                print(f">> Rendering {name} layer ({preset_name}, root {root} Hz)...")
                _render_np_stem(builders[name](), duration, layer_path, 2)
                inputs.append(f"-i \"{layer_path}\"")
                l_cfg = engines[name]
                vol_default, send_default = layer_defaults[name]
                add_stem(f"stem_{name}", f"[{idx}:a]volume={l_cfg.get('volume', vol_default)}",
                         l_cfg.get("send", send_default))
                idx += 1

        if not merge_inputs:
            raise ValueError("No audio engines were enabled or valid inputs found!")

        # 8. Reverb bus: sum of sends -> convolution with synthesized IR -> wet return
        if reverb_on and sends:
            ir_wav = f"{TMP_DIR}/hybrid_ir_{os.getpid()}.wav"
            temp_stems.append(ir_wav)
            generate_reverb_ir(ir_wav, rev_cfg.get("decay", 2.6), rev_cfg.get("length", 9.0), rng.base)
            inputs.append(f"-i \"{ir_wav}\"")
            ir_idx = idx
            idx += 1
            scaled = []
            for label, gain in sends:
                filter_chains.append(f"[{label}]volume={gain}[{label}v]")
                scaled.append(f"[{label}v]")
            if len(scaled) == 1:
                filter_chains.append(f"{scaled[0]}anull[sendbus]")
            else:
                filter_chains.append(f"{''.join(scaled)}amix=inputs={len(scaled)}:normalize=0[sendbus]")
            filter_chains.append(
                f"[sendbus][{ir_idx}:a]afir=dry=0:wet=1:irnorm=2:irgain=1,"
                f"volume={rev_cfg.get('wet', 0.6)}[stem_wet]")
            merge_inputs.append("[stem_wet]")

        merge_str = "".join(merge_inputs)
        num_stems = len(merge_inputs)
        filter_chains.append(f"{merge_str}amix=inputs={num_stems}:duration=longest:dropout_transition=2:normalize=0[mixed]")

        inputs_str = " ".join(inputs)
        filtergraph_str = ";\n        ".join(filter_chains)

        # Pass 1: measure. Pass 2: static gain + peak limiter + long fades.
        measured_i, measured_tp = _measure_loudness(inputs_str, filtergraph_str, duration)
        gain_db = TARGET_LUFS - measured_i
        print(f">> Raw mix: {measured_i:.1f} LUFS, {measured_tp:.1f} dBTP -> gain {gain_db:+.1f} dB")

        fade_in = min(FADE_IN_SEC, duration / 4)
        fade_out = min(FADE_OUT_SEC, duration / 4)
        master_chain = (
            f"[mixed]volume={gain_db:.2f}dB,"
            f"alimiter=limit={PEAK_LIMIT}:attack=5:release=200:level=0,"
            f"afade=t=in:ss=0:d={fade_in},afade=t=out:st={duration - fade_out}:d={fade_out}[mastered]"
        )

        cmd = f"""ffmpeg -y -nostdin {inputs_str} \
          -filter_complex "
            {filtergraph_str};
            {master_chain}
          " -map "[mastered]" -ar 48000 -t {duration} -c:a pcm_s16le "{out_master_wav}"
        """
        run_cmd(cmd, f"Mixing & Mastering Hybrid Score ({num_stems} active stems -> {out_master_wav})")
        print(f"✅ Mastered hybrid soundscape successfully written to: {out_master_wav}")
    finally:
        # Clean up intermediate files (rubberband stem, reverb IR)
        for stem_path in temp_stems:
            if os.path.exists(stem_path):
                try:
                    os.remove(stem_path)
                except Exception:
                    pass

if __name__ == "__main__":
    print("AI Hybrid Sound Conductor loaded.")

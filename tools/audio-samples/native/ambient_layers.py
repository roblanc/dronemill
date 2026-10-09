#!/usr/bin/env python3
"""
Musical ambient layers for DroneMill, synthesized with numpy.

Layers (each returns fn(t) -> (n, 2) float array, rendered in chunks by the conductor):
- pad:    detuned additive chord pad that slowly changes chord every few minutes
- choir:  formant-filtered "oo"/"ah" voices that swell in and out
- melody: sparse phrases (felt piano, string swells, bells) in the preset's scale,
          following the current chord
- events: rare one-shots placed far away in the mix (distant booms, metallic groans,
          leviathan calls, bells)

Everything is in key with the concept root and fully determined by (seed, duration, preset),
so pass 1 and pass 2 of the mastering render identical audio, and different concepts differ.

Presets:
- lovecraft:  dark phrygian/minor chords, choir, booms/groans/calls, very sparse bells
- historical: melancholic aeolian chords, piano and string phrases, rare bells
              (in the spirit of "Place, Year" ambient-music channels)
- fantasy:    open-fifth dorian chords, choir, reed-organ and string phrases, bells,
              plus an optional campfire layer (weary-knight dark fantasy)
"""

import copy
import hashlib
import math

import numpy as np

SR = 48000

SCALES = {
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "aeolian": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
}

PRESETS = {
    "lovecraft": {
        "pad_ratios": [1.0, 6 / 5, 3 / 2, 32 / 15],
        "pad_amps": [1.0, 0.55, 0.7, 0.18],
        "pad_octave": 2.0,
        "pad_harmonics": 8,
        "pad_brightness": (0.25, 0.55),
        "progression": [0, -4, -2, 1, 0, 5, -4],
        "section_sec": (480, 900),
        "xfade_sec": 75,
        "choir_ratios": [1.0, 3 / 2],
        "choir_presence": 0.45,
        "choir_vowels": ("oo", "ah"),
        "melody": {"scale": "phrygian", "timbres": {"bell": 1.0}, "notes": (1, 3),
                   "spacing": (4.0, 9.0), "phrase_gap": 110, "low": 300},
        "events": {"mean_gap": 75, "weights": {"boom": 3, "groan": 3, "call": 2, "bell": 0}},
    },
    "historical": {
        "pad_ratios": [1.0, 6 / 5, 3 / 2, 2.0, 9 / 4],
        "pad_amps": [1.0, 0.5, 0.7, 0.4, 0.22],
        "pad_octave": 2.0,
        "pad_harmonics": 8,
        "pad_brightness": (0.35, 0.65),
        "progression": [0, -4, 3, -2, 0, 5],
        "section_sec": (360, 720),
        "xfade_sec": 60,
        "choir_ratios": [1.0, 3 / 2],
        "choir_presence": 0.2,
        "choir_vowels": ("oo", "eh"),
        "melody": {"scale": "aeolian", "timbres": {"piano": 0.6, "string": 0.4}, "notes": (3, 6),
                   "spacing": (2.5, 6.0), "phrase_gap": 35, "low": 200},
        "events": {"mean_gap": 150, "weights": {"boom": 1, "groan": 0, "call": 0, "bell": 1}},
    },
}

PRESETS["fantasy"] = {
    # open fifths and dorian colour, closer to dungeon synth than to film score
    "pad_ratios": [1.0, 3 / 2, 2.0, 3.0, 12 / 5],
    "pad_amps": [1.0, 0.8, 0.5, 0.25, 0.3],
    "pad_octave": 2.0,
    "pad_harmonics": 9,
    "pad_brightness": (0.30, 0.55),
    "progression": [0, -2, 5, 3, 0, -5, -2],
    "section_sec": (420, 840),
    "xfade_sec": 70,
    "choir_ratios": [1.0, 3 / 2],
    "choir_presence": 0.5,
    "choir_vowels": ("oo", "ah"),
    "melody": {"scale": "dorian", "timbres": {"organ": 0.5, "string": 0.3, "bell": 0.2}, "notes": (3, 5),
               "spacing": (3.0, 7.0), "phrase_gap": 45, "low": 180},
    "events": {"mean_gap": 140, "weights": {"boom": 1, "groan": 0, "call": 0, "bell": 2}},
}

VOWELS = {
    # formant centers (Hz), gains, bandwidths (Hz)
    "oo": ([320, 800, 2500], [1.0, 0.30, 0.06], [70, 90, 140]),
    "ah": ([700, 1150, 2600], [1.0, 0.55, 0.12], [90, 110, 160]),
    "eh": ([500, 1700, 2500], [1.0, 0.40, 0.12], [80, 110, 150]),
}


def _rng(seed, tag):
    h = hashlib.sha256(f"{seed}:{tag}".encode("utf-8")).digest()
    return np.random.default_rng(int.from_bytes(h[:8], "big"))


def resolve_preset(name, overrides=None):
    preset = copy.deepcopy(PRESETS.get(name, PRESETS["lovecraft"]))
    for k, v in (overrides or {}).items():
        if isinstance(v, dict) and isinstance(preset.get(k), dict):
            preset[k].update(v)
        else:
            preset[k] = v
    return preset


# ---------------------------------------------------------------- helpers

def _harmonic_sums(theta, *amp_sets):
    """sum_k a_k * sin(k * theta) for each amplitude set, via the Chebyshev recurrence
    sin(k x) = 2 cos(x) sin((k-1) x) - sin((k-2) x). One sin + one cos per call."""
    s_prev = np.zeros_like(theta)
    s = np.sin(theta)
    c2 = 2.0 * np.cos(theta)
    outs = [amps[0] * s for amps in amp_sets]
    for k in range(1, max(len(a) for a in amp_sets)):
        s_prev, s = s, c2 * s - s_prev
        for out, amps in zip(outs, amp_sets):
            if k < len(amps):
                out += amps[k] * s
    return outs


def _pan_gains(p):
    ang = (p + 1.0) * math.pi / 4.0
    return math.cos(ang), math.sin(ang)


def _fft_lowpass(x, cutoff):
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1.0 / SR)
    spec *= 1.0 / (1.0 + (f / cutoff) ** 4)
    return np.fft.irfft(spec, len(x))


def _smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def section_schedule(seed, duration, preset):
    """Chord sections: list of dicts with start/end (s) and semitone offset from the root."""
    rng = _rng(seed, "sections")
    prog = preset["progression"]
    sections, t, i = [], 0.0, 0
    while t < duration:
        length = rng.uniform(*preset["section_sec"])
        sections.append({"start": t, "end": min(duration, t + length), "semi": prog[i % len(prog)]})
        t += length
        i += 1
    return sections


def _section_weights(t, sections, xfade):
    """Equal-power crossfade weights of the sections overlapping this chunk."""
    half = xfade / 2.0
    t0, t1 = t[0], t[-1]
    result = []
    for i, s in enumerate(sections):
        a = s["start"] - half if i > 0 else -1e9
        b = s["end"] + half if i < len(sections) - 1 else 1e9
        if b < t0 or a > t1:
            continue
        w = np.ones_like(t)
        if i > 0:
            w *= np.sin(0.5 * math.pi * np.clip((t - a) / xfade, 0.0, 1.0))
        if i < len(sections) - 1:
            w *= np.cos(0.5 * math.pi * np.clip((t - (b - xfade)) / xfade, 0.0, 1.0))
        result.append((s, w))
    return result


def _section_at(sections, t):
    for s in sections:
        if s["start"] <= t < s["end"]:
            return s
    return sections[-1]


def _fold_into(f, lo, hi):
    while f < lo:
        f *= 2.0
    while f > hi:
        f /= 2.0
    return f


# ---------------------------------------------------------------- pad

def pad_fn(root, seed, duration, preset):
    sections = section_schedule(seed, duration, preset)
    rng = _rng(seed, "pad")
    ratios, tone_amps = preset["pad_ratios"], preset["pad_amps"]
    n_harm = preset["pad_harmonics"]
    lo, hi = preset["pad_brightness"]
    p_bright = rng.uniform(180, 360)
    tones = []
    for j in range(len(ratios)):
        d = rng.uniform(0.0015, 0.003)
        side = 1 if j % 2 == 0 else -1
        voices = [(1.0 - d, rng.uniform(0, 2 * math.pi), -0.5 * side),
                  (1.0 + d, rng.uniform(0, 2 * math.pi), 0.5 * side)]
        tones.append((rng.uniform(60, 160), rng.uniform(0, 2 * math.pi), voices))
    # worst-case peak normalization (all partials in phase) so the stem never clips
    peak = sum(tone_amps) * 2 * sum(hi ** (k - 1) / k ** 0.8 for k in range(1, n_harm + 1))
    scale = 0.9 / peak * 2.2  # partials are never all in phase; realistic peaks stay under full scale

    def fn(t):
        out = np.zeros((len(t), 2))
        b = lo + (hi - lo) * (0.5 + 0.5 * np.sin(2 * math.pi * t / p_bright))
        amps = [b ** (k - 1) / k ** 0.8 for k in range(1, n_harm + 1)]
        for sec, w in _section_weights(t, sections, preset["xfade_sec"]):
            base = root * preset["pad_octave"] * 2 ** (sec["semi"] / 12.0)
            for (ratio, amp), (p_env, ph_env, voices) in zip(zip(ratios, tone_amps), tones):
                env = amp * (0.65 + 0.35 * np.sin(2 * math.pi * t / p_env + ph_env)) * w
                for det, ph0, pan in voices:
                    y = _harmonic_sums(2 * math.pi * base * ratio * det * t + ph0, amps)[0] * env
                    gl, gr = _pan_gains(pan)
                    out[:, 0] += gl * y
                    out[:, 1] += gr * y
        return out * scale
    return fn


# ---------------------------------------------------------------- choir

def _formant_weights(freqs, vowel):
    centers, gains, bws = VOWELS[vowel]
    w = np.zeros_like(freqs)
    for c, g, bw in zip(centers, gains, bws):
        w += g * np.exp(-0.5 * ((freqs - c) / bw) ** 2)
    return w


def choir_fn(root, seed, duration, preset):
    sections = section_schedule(seed, duration, preset)
    rng = _rng(seed, "choir")
    presence = preset["choir_presence"]
    base0 = _fold_into(root * 2.0, 130.0, 260.0)
    vowel_a, vowel_b = preset["choir_vowels"]
    p1, p2 = rng.uniform(90, 160), rng.uniform(200, 320)
    ph_gate = rng.uniform(0, 2 * math.pi)
    p_vowel = rng.uniform(40, 90)
    voices = []
    for ratio in preset["choir_ratios"]:
        for _ in range(3):
            voices.append((ratio, 1.0 + rng.uniform(-0.004, 0.004), rng.uniform(0, 2 * math.pi),
                           rng.uniform(4.6, 5.6), rng.uniform(0, 2 * math.pi), rng.uniform(-0.6, 0.6)))
    scale = 0.9 / (len(voices) * 1.6)

    def fn(t):
        out = np.zeros((len(t), 2))
        g = 0.5 + 0.3 * np.sin(2 * math.pi * t / p1) + 0.2 * np.sin(2 * math.pi * t / p2 + ph_gate)
        gate = _smoothstep((g - (1.0 - presence)) / 0.25)
        if gate.max() < 1e-4:
            return out
        m = 0.5 + 0.5 * np.sin(2 * math.pi * t / p_vowel)
        for sec, w in _section_weights(t, sections, preset["xfade_sec"]):
            base = _fold_into(base0 * 2 ** (sec["semi"] / 12.0), 120.0, 280.0)
            for ratio, det, ph0, vr, vph, pan in voices:
                f0 = base * ratio * det
                n_harm = max(1, int(3800 / f0))
                freqs = f0 * np.arange(1, n_harm + 1)
                wa, wb = _formant_weights(freqs, vowel_a), _formant_weights(freqs, vowel_b)
                theta = 2 * math.pi * f0 * t + ph0 - (f0 * 0.004 / vr) * np.cos(2 * math.pi * vr * t + vph)
                sa, sb = _harmonic_sums(theta, wa, wb)
                y = ((1.0 - m) * sa + m * sb) * w * gate
                gl, gr = _pan_gains(pan)
                out[:, 0] += gl * y
                out[:, 1] += gr * y
        return out * scale
    return fn


# ---------------------------------------------------------------- one-shot synths
# Each returns a mono float array with peak <= 1.

def _env_t(length):
    return np.arange(int(length * SR)) / SR


def synth_boom(rng, root):
    t = _env_t(7.0)
    noise = _fft_lowpass(rng.standard_normal(len(t)), rng.uniform(90, 160))
    noise /= np.max(np.abs(noise)) + 1e-9
    env = (1 - np.exp(-t / 0.06)) * np.exp(-t / rng.uniform(1.4, 2.4))
    f0 = rng.uniform(32, 42)
    tone = np.sin(2 * math.pi * f0 * (t - 0.1 * t ** 2 / 7.0)) * (1 - np.exp(-t / 0.03)) * np.exp(-t / 2.2)
    y = 0.6 * noise * env + 0.8 * tone
    return y / (np.max(np.abs(y)) + 1e-9)


def synth_groan(rng, root):
    length = rng.uniform(5.0, 9.0)
    t = _env_t(length)
    f0 = _fold_into(root, 40.0, 80.0) * rng.uniform(0.95, 1.3)
    glide = rng.uniform(0.10, 0.20)
    phase = 2 * math.pi * f0 * (t - 0.5 * glide * t ** 2 / length)
    y = np.zeros_like(t)
    for ratio, amp in zip([1.0, 2.76, 5.40, 8.93], [1.0, 0.5, 0.3, 0.15]):
        y += amp * np.sin(ratio * phase)
    rough = 0.55 + 0.45 * np.sin(2 * math.pi * rng.uniform(8, 14) * t + 0.8 * np.sin(2 * math.pi * 0.7 * t))
    y *= rough * np.sin(math.pi * t / length) ** 0.7
    y = _fft_lowpass(y, 1800)
    return y / (np.max(np.abs(y)) + 1e-9)


def synth_call(rng, root):
    length = rng.uniform(7.0, 11.0)
    t = _env_t(length)
    f0 = _fold_into(root, 45.0, 90.0) * rng.uniform(1.0, 1.3)
    f = f0 * (1 + 0.3 * np.sin(math.pi * t / length) ** 2 - 0.1 * t / length) * (1 + 0.012 * np.sin(2 * math.pi * 3 * t))
    phase = 2 * math.pi * np.cumsum(f) / SR
    y = _harmonic_sums(phase, [k ** -1.5 for k in range(1, 7)])[0]
    y *= np.sin(math.pi * t / length) ** 1.5
    y = _fft_lowpass(y, 700)
    return y / (np.max(np.abs(y)) + 1e-9)


def synth_bell(rng, freq):
    t = _env_t(9.0)
    y = np.zeros_like(t)
    stretch = rng.uniform(0.8, 1.2)
    for ratio, amp, tau in zip([1.0, 2.0, 2.76, 4.07, 5.40], [1.0, 0.6, 0.45, 0.25, 0.15], [6.0, 4.0, 3.0, 2.0, 1.5]):
        y += amp * np.sin(2 * math.pi * freq * ratio * t + rng.uniform(0, 2 * math.pi)) * np.exp(-t / (tau * stretch))
    y *= 1 - np.exp(-t / 0.004)
    return y / (np.max(np.abs(y)) + 1e-9)


def synth_piano(rng, freq):
    """Soft felt-piano-like note: slightly inharmonic partials, faster decay up high,
    two slightly detuned strings."""
    t = _env_t(7.0)
    y = np.zeros_like(t)
    for detune, gain in [(1.0, 1.0), (1.0015, 0.5)]:
        for k in range(1, 11):
            fk = k * freq * detune * math.sqrt(1 + 0.0004 * k * k)
            if fk > 9000:
                break
            y += gain * k ** -1.3 * np.sin(2 * math.pi * fk * t) * np.exp(-t / (3.5 / k ** 0.6))
    y *= 1 - np.exp(-t / 0.006)
    return y / (np.max(np.abs(y)) + 1e-9)


def synth_organ(rng, freq):
    """Soft reed-organ / dungeon-synth lead: odd-heavy harmonics, slow attack, gentle
    tremolo, held then released."""
    length = rng.uniform(5.0, 8.0)
    t = _env_t(length)
    amps = [1.0 if k % 2 == 1 else 0.35 for k in range(1, 9)]
    amps = [a / k ** 1.2 for a, k in zip(amps, range(1, 9))]
    y = np.zeros_like(t)
    for detune in (0.999, 1.001):
        y += _harmonic_sums(2 * math.pi * freq * detune * t + rng.uniform(0, 6.28), amps)[0]
    y *= 1.0 + 0.06 * np.sin(2 * math.pi * rng.uniform(4.5, 5.5) * t)
    y *= _smoothstep(t / 0.6) * _smoothstep((length - t) / 1.8)
    return y / (np.max(np.abs(y)) + 1e-9)


def synth_string(rng, freq):
    length = rng.uniform(7.0, 10.0)
    t = _env_t(length)
    amps = [k ** -1.6 for k in range(1, 11)]
    y = np.zeros_like(t)
    for _ in range(3):
        f = freq * (1 + rng.uniform(-0.003, 0.003))
        vr = rng.uniform(4.8, 5.6)
        theta = 2 * math.pi * f * t - (f * 0.002 / vr) * np.cos(2 * math.pi * vr * t + rng.uniform(0, 6.28)) + rng.uniform(0, 6.28)
        y += _harmonic_sums(theta, amps)[0]
    env = _smoothstep(t / 2.5) * _smoothstep((length - t) / 3.0)
    y *= env
    return y / (np.max(np.abs(y)) + 1e-9)


# ---------------------------------------------------------------- timelines

def _timeline_fn(items):
    """items: list of (start_sec, pan, gain, synth_callable). Synths run lazily per chunk."""
    items = sorted(items, key=lambda x: x[0])
    cache = {}
    state = {"first": 0}

    def fn(t):
        n = len(t)
        s0 = int(round(t[0] * SR))
        out = np.zeros((n, 2))
        i = state["first"]
        while i < len(items):
            start, pan, gain, synth = items[i]
            a = int(start * SR)
            if a >= s0 + n:
                break
            if i not in cache:
                cache[i] = synth()
            buf = cache[i]
            b = a + len(buf)
            if b <= s0:
                cache.pop(i, None)
                if i == state["first"]:
                    state["first"] += 1
                i += 1
                continue
            lo, hi = max(a, s0), min(b, s0 + n)
            gl, gr = _pan_gains(pan)
            seg = buf[lo - a:hi - a] * gain
            out[lo - s0:hi - s0, 0] += gl * seg
            out[lo - s0:hi - s0, 1] += gr * seg
            i += 1
        return out * 0.5
    return fn


def melody_fn(root, seed, duration, preset):
    cfg = preset.get("melody")
    if not cfg:
        return lambda t: np.zeros((len(t), 2))
    sections = section_schedule(seed, duration, preset)
    rng = _rng(seed, "melody")
    scale = SCALES[cfg["scale"]]
    timbres = list(cfg["timbres"].keys())
    probs = np.array(list(cfg["timbres"].values()), dtype=float)
    probs /= probs.sum()
    synths = {"piano": synth_piano, "string": synth_string, "bell": synth_bell, "organ": synth_organ}
    base = _fold_into(root, cfg["low"], cfg["low"] * 2)
    items, t, n_item = [], rng.uniform(15, 40), 0
    while t < duration - 30:
        timbre = timbres[rng.choice(len(timbres), p=probs)]
        degree = int(rng.choice([0, 2, 4]))
        for _ in range(int(rng.integers(cfg["notes"][0], cfg["notes"][1] + 1))):
            if t >= duration - 30:
                break
            sec = _section_at(sections, t)
            semi = sec["semi"] + scale[degree % 7] + 12 * (degree // 7)
            freq = base * 2 ** (semi / 12.0)
            note_rng = _rng(seed, f"note{n_item}")
            items.append((t, float(rng.uniform(-0.5, 0.5)), float(10 ** (rng.uniform(-6, 0) / 20)),
                          (lambda s=synths[timbre], r=note_rng, f=freq: s(r, f))))
            n_item += 1
            degree = int(np.clip(degree + rng.choice([-2, -1, 1, 2, 0], p=[0.2, 0.3, 0.3, 0.1, 0.1]), 0, 9))
            t += rng.uniform(*cfg["spacing"])
        t += rng.exponential(cfg["phrase_gap"]) + 8.0
    return _timeline_fn(items)


def events_fn(root, seed, duration, preset):
    cfg = preset.get("events")
    if not cfg:
        return lambda t: np.zeros((len(t), 2))
    rng = _rng(seed, "events")
    kinds = [k for k, w in cfg["weights"].items() if w > 0]
    if not kinds:
        return lambda t: np.zeros((len(t), 2))
    probs = np.array([cfg["weights"][k] for k in kinds], dtype=float)
    probs /= probs.sum()
    bell_base = _fold_into(root, 350.0, 700.0)
    items, t, n_item = [], 20.0 + rng.exponential(cfg["mean_gap"] / 2), 0
    while t < duration - 40:
        kind = kinds[rng.choice(len(kinds), p=probs)]
        ev_rng = _rng(seed, f"event{n_item}")
        if kind == "bell":
            synth = (lambda r=ev_rng: synth_bell(r, bell_base * 2 ** (int(r.choice([0, 3, 7])) / 12.0)))
        else:
            fn = {"boom": synth_boom, "groan": synth_groan, "call": synth_call}[kind]
            synth = (lambda f=fn, r=ev_rng: f(r, root))
        items.append((t, float(rng.uniform(-0.75, 0.75)), float(10 ** (rng.uniform(-8, 0) / 20)), synth))
        n_item += 1
        t += max(20.0, rng.exponential(cfg["mean_gap"]))
    return _timeline_fn(items)


def fire_fn(root, seed, duration, preset):
    """A small campfire: a soft low roar that flickers in level, plus random crackles and
    the occasional bigger pop. State is carried across chunks so nothing clicks at the
    chunk boundaries."""
    rng = _rng(seed, "fire")
    box = 96  # moving-average length for the roar (lowpass around 500 Hz)
    state = {"tail": np.zeros((box, 2)), "spill": np.zeros((0, 2))}
    p1, p2 = rng.uniform(3, 7), rng.uniform(11, 23)

    def fn(t):
        n = len(t)
        white = np.concatenate([state["tail"], rng.standard_normal((n, 2))])
        state["tail"] = white[-box:]
        c = np.cumsum(white, axis=0)
        roar = (c[box:] - c[:-box]) / box
        flicker = 0.75 + 0.15 * np.sin(2 * math.pi * t / p1) + 0.1 * np.sin(2 * math.pi * t / p2)
        out = roar * flicker[:, None] * 1.4
        # crackles: short decaying noise grains, a few per second, randomly panned
        grain_max = int(0.06 * SR)
        buf = np.zeros((n + grain_max, 2))
        spill = state["spill"]
        buf[:len(spill)] += spill
        n_crackles = rng.poisson(5.0 * n / SR)
        for _ in range(n_crackles):
            pos = int(rng.integers(0, n))
            big = rng.random() < 0.06
            length = int(SR * (rng.uniform(0.02, 0.06) if big else rng.uniform(0.002, 0.012)))
            g = rng.standard_normal(length) * np.exp(-np.arange(length) / (length / 4))
            if not big:
                g = np.diff(g, prepend=0.0)  # brighter, snappier
            g /= np.max(np.abs(g)) + 1e-9
            amp = (0.8 if big else 0.4) * min(1.6, rng.lognormal(0, 0.4))
            pan = rng.uniform(-0.6, 0.6)
            gl, gr = _pan_gains(pan)
            buf[pos:pos + length, 0] += gl * amp * g
            buf[pos:pos + length, 1] += gr * amp * g
        state["spill"] = buf[n:]
        out += buf[:n]
        return out * 0.35
    return fn


def layer_builders(root, seed, duration, preset):
    return {
        "pad": lambda: pad_fn(root, seed, duration, preset),
        "choir": lambda: choir_fn(root, seed, duration, preset),
        "melody": lambda: melody_fn(root, seed, duration, preset),
        "events": lambda: events_fn(root, seed, duration, preset),
        "fire": lambda: fire_fn(root, seed, duration, preset),
    }

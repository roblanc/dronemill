"""Native layers: pure NumPy, no samples, no licences.

Ported from /mnt/media/bob/ambience/ambient.py (soundscapes) and ambience/abracat/lofi.py (spooky lo-fi),
split into stems so the renderer can mix, process and loop each one. Every function takes a Ctx and
returns a mono (n,) or stereo (n, 2) float array of exactly ctx.n samples.
"""
import numpy as np

hz = lambda m: 440 * 2 ** ((m - 69) / 12)
SCALES = {'minor': [0, 2, 3, 5, 7, 8, 10], 'major': [0, 2, 4, 5, 7, 9, 11], 'harmonic': [0, 2, 3, 5, 7, 8, 11],
          'pent': [0, 3, 5, 7, 10], 'wholetone': [0, 2, 4, 6, 8, 10], 'phrygian': [0, 1, 3, 5, 7, 8, 10]}


class Ctx:
    def __init__(self, sr, seconds, seed, tonic=2, mode='minor', bpm=80):
        self.sr, self.secs, self.n = sr, seconds, int(round(seconds * sr))
        self.t = np.arange(self.n) / sr
        self.rng = np.random.default_rng(seed)
        self.tonic, self.mode, self.bpm = tonic, mode, bpm


# ---------------- tools ----------------
def spec_filter(c, x, fn):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / c.sr); return np.fft.irfft(X * fn(f), len(x))
def lp(c, x, fc, order=2): return spec_filter(c, x, lambda f: 1 / np.sqrt(1 + (f / fc) ** (2 * order)))
def hp(c, x, fc, order=2): return spec_filter(c, x, lambda f: 1 / np.sqrt(1 + (fc / np.maximum(f, 1e-3)) ** (2 * order)))
def bp(c, x, lo, hi): return hp(c, lp(c, x, hi), lo)
def norm(x): return x / (np.abs(x).max() + 1e-9)
def pink(c, n=None): n = n or c.n; return norm(spec_filter(c, c.rng.standard_normal(n), lambda f: 1 / np.sqrt(np.maximum(f, 20))))
def brown(c, n=None): n = n or c.n; return norm(spec_filter(c, c.rng.standard_normal(n), lambda f: 1 / np.maximum(f, 15)))
def smooth_lfo(c, rate, depth=1.0):
    k = max(4, int(c.secs * rate) + 4); pts = c.rng.random(k)
    return 1 - depth + depth * np.interp(np.linspace(0, k - 3, c.n), np.arange(k), pts)
def place(buf, sig, i0, g=1.0):
    i = max(0, i0); j = min(len(buf), i0 + len(sig))
    if j > i: buf[i:j] += sig[i - i0:j - i0] * g
def at(c, buf, sig, t, g=1.0): place(buf, sig, int(t * c.sr), g)
def adsr(c, n, a, r):
    t = np.arange(n) / c.sr; return np.minimum(1, t / max(a, 1e-3)) * np.clip((n / c.sr - t) / max(r, 1e-3), 0, 1)
def reverb(c, x, secs=2.5, mix=0.35, bright=4000):
    """Seeded noise-IR convolution reverb, stereo out (the old ambient.py room)."""
    n = int(secs * c.sr); tt = np.arange(n) / c.sr; out = []
    for _ in range(2):
        h = lp(c, c.rng.standard_normal(n) * np.exp(-tt / (secs / 5)), bright); h /= np.sqrt(np.sum(h ** 2))
        L = len(x) + n; m = 1 << (L - 1).bit_length()
        out.append(np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(h, m), m)[:len(x)])
    return np.stack([x * (1 - mix) + out[0] * mix * 2.2, x * (1 - mix) + out[1] * mix * 2.2], 1)
def scale(c, name=None): return SCALES[name or c.mode]
def chord_prog(c, kind='minor'):
    """Four slow chords in the context key (MIDI note lists, octave 3–4)."""
    r = 48 + c.tonic
    if kind == 'major': return [[r, r + 7, r + 12, r + 16], [r - 3, r + 4, r + 9, r + 12], [r - 7, r, r + 5, r + 9], [r - 5, r + 2, r + 7, r + 11]]
    return [[r, r + 7, r + 12, r + 15], [r - 4, r + 3, r + 8, r + 12], [r - 7, r, r + 5, r + 8], [r - 2, r + 5, r + 10, r + 14]]


# ---------------- instruments ----------------
def pad(c, chords=None, every=10, bright=1400, detune=0.003, wow=0.0):
    chords = chords or chord_prog(c, 'major' if c.mode == 'major' else 'minor')
    out = np.zeros(c.n)
    for s in range(int(np.ceil(c.secs / every)) + 1):
        ch = chords[s % len(chords)]; t0 = s * every - every * 0.35; n = int(every * 1.7 * c.sr); t = np.arange(n) / c.sr
        sig = np.zeros(n)
        for m in ch:
            for d in (-detune, 0, detune):
                f = hz(m) * (1 + d) * (1 + wow * np.sin(2 * np.pi * 0.4 * t + c.rng.random() * 6))
                ph = 2 * np.pi * np.cumsum(f) / c.sr + c.rng.random() * 6
                sig += sum(np.sin(k * ph) / k for k in range(1, 7))
        at(c, out, sig * np.sin(np.pi * np.clip(t / (every * 1.7), 0, 1)) ** 1.5, t0)
    return lp(c, norm(out), bright)
def drone(c, note=None, beat=0.12):
    f = hz(note if note is not None else 26 + c.tonic)
    s = np.sin(2 * np.pi * f * c.t) + 0.6 * np.sin(2 * np.pi * (f * 1.5 + beat) * c.t) + 0.4 * np.sin(2 * np.pi * (f * 2 - beat) * c.t)
    return norm(s) * smooth_lfo(c, 0.08, 0.5)
def _cello(c, m, dur):
    n = int(dur * c.sr); t = np.arange(n) / c.sr; f = hz(m) * (1 + 0.004 * np.sin(2 * np.pi * 5 * t) * np.minimum(1, t / 1.5))
    ph = 2 * np.pi * np.cumsum(f) / c.sr
    return lp(c, sum(np.sin(k * ph) / k ** 1.3 for k in range(1, 10)), 900) * adsr(c, n, 1.6, 1.8)
def cello(c, every=10):
    out = np.zeros(c.n); r = 36 + c.tonic
    for i in range(int(c.secs / every) + 1): at(c, out, _cello(c, [r, r - 4, r - 2, r - 5][i % 4], every + .5), i * every)
    return norm(out)
def _piano(c, m, dur=4, vel=1.0):
    n = int((dur + 2) * c.sr); t = np.arange(n) / c.sr; f = hz(m)
    s = sum(np.sin(2 * np.pi * f * k * t * (1 + 0.0007 * k)) * (0.55 ** k) for k in range(1, 7))
    return s * np.minimum(1, t / 0.006) * np.exp(-t / 1.8) * vel
def _musicbox(c, m, vel=1.0):
    n = int(3 * c.sr); t = np.arange(n) / c.sr; f = hz(m)
    s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / 0.25) + 0.15 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t / 0.08)
    return s * np.minimum(1, t / 0.002) * np.exp(-t / 0.8) * vel
def _bell(c, m, decay=6, vel=1.0):
    n = int(decay * 1.5 * c.sr); t = np.arange(n) / c.sr; f = hz(m)
    s = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / (decay / (1 + i))) for i, (r, a) in enumerate([(1, 1), (2.76, .5), (5.4, .3), (8.93, .15)]))
    return s * np.minimum(1, t / 0.004) * vel
def melody(c, inst='piano', scale_name=None, octave=5, every=2.4, density=0.5, decay=6):
    """Sparse wandering melody. inst: piano | musicbox | bell."""
    voice = {'piano': lambda m: _piano(c, m), 'musicbox': lambda m: _musicbox(c, m), 'bell': lambda m: _bell(c, m, decay)}[inst]
    sc = scale(c, scale_name); root = 12 * octave + c.tonic
    out = np.zeros(c.n); deg = c.rng.integers(0, len(sc)); t = c.rng.random() * every
    while t < c.secs - 1:
        if c.rng.random() < density:
            deg = int(np.clip(deg + c.rng.choice([-2, -1, 1, 2, 0]), 0, len(sc) * 2 - 1))
            at(c, out, voice(root + sc[deg % len(sc)] + 12 * (deg // len(sc))), t, 0.8 * (0.6 + 0.4 * c.rng.random()))
        t += every * c.rng.choice([1, 1, 2, 0.5])
    return norm(out)
def arp_bells(c, step=0.75):
    r = 62 + c.tonic - 2; notes = [r, r + 7, r + 12, r + 14, r + 19, r + 14, r + 12, r + 7]
    out = np.zeros(c.n); t = 0
    while t < c.secs: at(c, out, _bell(c, notes[int(t / step) % 8], 3), t, 0.5 + 0.3 * c.rng.random()); t += step
    return norm(out)
def dissonant_swells(c, every=9):
    out = np.zeros(c.n)
    for i in range(int(c.secs / every) + 1):
        root = 36 + c.tonic + c.rng.choice([0, 1, 6]); ch = [root, root + 1, root + 6, root + 13, root + 18]
        n = int(14 * c.sr); t = np.arange(n) / c.sr
        at(c, out, sum(np.sin(2 * np.pi * hz(m) * t + c.rng.random() * 6) for m in ch) * np.sin(np.pi * t / 14) ** 2, i * every)
    return norm(lp(c, out, 1200))


# ---------------- sound layers (foley) ----------------
def rain(c, heavy=0.5):
    bed = bp(c, pink(c), 600, 9000) * (0.6 + 0.4 * smooth_lfo(c, 0.05))
    drops = np.zeros(c.n); idx = c.rng.integers(0, c.n, int(c.secs * (40 + 120 * heavy)))
    drops[idx] = c.rng.random(len(idx)) ** 2 * c.rng.choice([-1, 1], len(idx))
    drops = bp(c, np.convolve(drops, np.exp(-np.arange(60) / 8), 'same'), 1500, 7000)
    return norm(bed * 0.5 + norm(drops) * 0.5)
def fire(c):
    rumble = lp(c, brown(c), 250) * smooth_lfo(c, 1.5, 0.6)
    cr = np.zeros(c.n); idx = c.rng.integers(0, c.n, int(c.secs * 14)); cr[idx] = c.rng.random(len(idx)) ** 3 * c.rng.choice([-1, 1], len(idx))
    cr = hp(c, np.convolve(cr, np.exp(-np.arange(90) / 12), 'same'), 900)
    pops = np.zeros(c.n); idx = c.rng.integers(0, c.n, int(c.secs * 0.8)); pops[idx] = c.rng.choice([-1, 1], len(idx))
    pops = bp(c, np.convolve(pops, np.exp(-np.arange(400) / 40), 'same'), 300, 4000)
    return norm(norm(rumble) * 0.5 + norm(cr) * 0.4 + norm(pops) * 0.5)
def waves(c):
    env = np.zeros(c.n); t = c.rng.random() * 3
    while t < c.secs:
        n = int(9 * c.sr); tt = np.arange(n) / c.sr
        at(c, env, np.minimum(1, tt / 2.2) * np.exp(-np.maximum(tt - 2.2, 0) / 2.8), t, 0.6 + 0.4 * c.rng.random()); t += c.rng.uniform(6, 10)
    return norm(norm(lp(c, brown(c), 900) * (0.25 + env)) + 0.35 * norm(bp(c, pink(c), 1500, 7000) * env ** 2))
def wind(c):
    return norm(bp(c, pink(c), 250, 1200) * smooth_lfo(c, 0.12, 0.8) + 0.3 * bp(c, pink(c), 900, 2600) * smooth_lfo(c, 0.2, 0.9))
def foghorn(c, every=22, note=41):
    out = np.zeros(c.n); t = 5
    while t < c.secs:
        n = int(5 * c.sr); tt = np.arange(n) / c.sr
        s = sum(np.sin(2 * np.pi * hz(note) * k * tt) / k for k in range(1, 8)) + 0.7 * sum(np.sin(2 * np.pi * (hz(note) + 2.5) * k * tt) / k for k in range(1, 8))
        at(c, out, lp(c, s, 500) * adsr(c, n, 0.6, 1.5), t); t += every
    return norm(out)
def train(c):
    out = np.zeros(c.n); t = 0.3; k = int(0.08 * c.sr); kk = np.arange(k)
    thump = lambda: lp(c, c.rng.standard_normal(k) * np.exp(-kk / 300), 400) + np.sin(2 * np.pi * 55 * kk / c.sr) * np.exp(-kk / 1500)
    while t < c.secs: at(c, out, thump(), t); at(c, out, thump(), t + 0.13, 0.8); t += 1.2 + c.rng.normal(0, 0.01)
    return norm(norm(out) * 0.6 + lp(c, brown(c), 180) * 0.7)
def clock(c):
    out = np.zeros(c.n); k = int(0.03 * c.sr)
    for i in range(int(c.secs)): at(c, out, bp(c, c.rng.standard_normal(k), 1800 if i % 2 else 2600, 5000) * np.exp(-np.arange(k) / 150), i + 0.5)
    return norm(out)
def drips(c):
    out = np.zeros(c.n); t = c.rng.random()
    while t < c.secs:
        n = int(0.12 * c.sr); tt = np.arange(n) / c.sr; f = c.rng.uniform(900, 2600) * (1 + 2 * np.exp(-tt / 0.01))
        at(c, out, np.sin(2 * np.pi * np.cumsum(f) / c.sr) * np.exp(-tt / 0.03), t, c.rng.uniform(0.3, 1)); t += c.rng.exponential(1.6)
    return norm(out)
def hum(c, base=60):
    return norm(sum(np.sin(2 * np.pi * base * k * c.t) / k ** 1.5 for k in (2, 3, 4, 6, 8)) * (0.8 + 0.2 * smooth_lfo(c, 3)))
def bubbles(c):
    out = np.zeros(c.n); t = 0
    while t < c.secs:
        n = int(0.05 * c.sr); tt = np.arange(n) / c.sr; f = c.rng.uniform(150, 260) * (1 + 3 * tt / 0.05)
        at(c, out, np.sin(2 * np.pi * np.cumsum(f) / c.sr) * np.sin(np.pi * tt / 0.05), t, c.rng.uniform(0.3, 1)); t += c.rng.exponential(0.35)
    return norm(lp(c, out, 1500))
def thunder(c, every=45):
    out = np.zeros(c.n); t = c.rng.uniform(5, every)
    while t < c.secs:
        n = int(7 * c.sr); tt = np.arange(n) / c.sr
        at(c, out, lp(c, c.rng.standard_normal(n), 140) * np.minimum(1, tt / 0.6) * np.exp(-tt / 1.8), t); t += c.rng.uniform(every * .6, every * 1.4)
    return norm(out)
def water(c):
    return norm(lp(c, brown(c), 500) * smooth_lfo(c, 0.2, 0.5))


# ---------------- lo-fi stems (from lofi.py) ----------------
LOFI_PROGS = [  # (semitones from tonic, chord intervals)
    [(0, [0, 3, 7, 10, 14]), (8, [0, 4, 7, 11]), (5, [0, 3, 7, 10, 14]), (7, [0, 4, 7, 10, 13])],
    [(0, [0, 3, 7, 10]), (3, [0, 4, 7, 11]), (8, [0, 4, 7, 11, 14]), (7, [0, 4, 7, 10, 13])],
    [(0, [0, 3, 7, 11]), (5, [0, 3, 7, 10]), (10, [0, 4, 7, 10]), (8, [0, 4, 7, 11])],
]
def _lofi_grid(c, swing=0.58):
    beat = 60 / c.bpm; bar = beat * 4
    return beat, bar, (lambda b, k: b * bar + (k // 2) * beat + (k % 2) * beat * 2 * swing)
def _lofi_prog(c, prog):
    return LOFI_PROGS[prog if prog is not None else int(np.random.default_rng(c.tonic * 7 + c.bpm).integers(3))]
def _ep(c, m, dur, vel):
    n = int((dur + 1.5) * c.sr); t = np.arange(n) / c.sr; f = hz(m)
    s = sum(np.sin(2 * np.pi * f * k * t * (1 + 0.0008 * k)) * (0.6 ** k) for k in range(1, 6))
    s += 0.3 * np.sin(2 * np.pi * f * t + 1.2 * np.sin(2 * np.pi * f * t) * np.exp(-t / 0.3))
    return s * np.minimum(1, t / 0.008) * np.exp(-t / 1.2) * np.clip((dur + 0.4 - t) / 0.4, 0, 1) * vel
def lofi_keys(c, prog=None):
    """Warm electric-piano chords, one per bar, slight strum, swung re-voiced stabs."""
    beat, bar, eighth = _lofi_grid(c); pr = _lofi_prog(c, prog); root = 48 + c.tonic
    L = np.zeros(c.n); R = np.zeros(c.n)
    for b in range(int(np.ceil(c.secs / bar)) + 1):
        semi, ch = pr[b % len(pr)]; v = [root + semi + i for i in ch]
        for i, m in enumerate(v):
            pan = (i - 2) * 0.15; s = _ep(c, m, bar * 0.95, 0.75 + 0.15 * c.rng.random()); t = b * bar + i * 0.012 + c.rng.normal(0, 0.004)
            at(c, L, s * np.sqrt((1 - pan) / 2), t); at(c, R, s * np.sqrt((1 + pan) / 2), t)
        if c.rng.random() < 0.5:
            for i, m in enumerate(v[1:4]):
                s = _ep(c, m + 12, beat * 0.8, 0.35); at(c, L, s * .55, eighth(b, 3) + i * .01); at(c, R, s * .84, eighth(b, 3) + i * .01)
    return np.stack([L, R], 1) / (max(np.abs(L).max(), np.abs(R).max()) + 1e-9)
def lofi_bass(c, prog=None):
    beat, bar, _ = _lofi_grid(c); pr = _lofi_prog(c, prog); root = 48 + c.tonic; out = np.zeros(c.n)
    def note(m, dur):
        n = int((dur + 0.1) * c.sr); t = np.arange(n) / c.sr
        s = np.sin(2 * np.pi * hz(m) * t) + 0.15 * np.sin(4 * np.pi * hz(m) * t)
        return s * np.minimum(1, t / 0.02) * np.clip((dur - t) / 0.08, 0, 1) * np.exp(-t / 2.5)
    for b in range(int(np.ceil(c.secs / bar)) + 1):
        tone = root + pr[b % len(pr)][0] - 12
        at(c, out, note(tone, beat * 2.6), b * bar); at(c, out, note(tone + (7 if c.rng.random() < 0.5 else 0), beat * 1.2), b * bar + beat * 2.5)
    return norm(out)
def lofi_drums_synth(c):
    """Synthesized dusty kit (swung kick / laid-back snare / hats). No samples."""
    beat, bar, eighth = _lofi_grid(c)
    def bandnoise(n, lo, hi):
        X = np.fft.rfft(c.rng.standard_normal(n)); f = np.fft.rfftfreq(n, 1 / c.sr); X[(f < lo) | (f > hi)] = 0
        return norm(np.fft.irfft(X, n))
    SN = bandnoise(int(0.3 * c.sr), 900, 7000); HH = bandnoise(int(0.12 * c.sr), 6000, 14000)
    tS = np.arange(len(SN)) / c.sr; tH = np.arange(len(HH)) / c.sr
    def kick(v):
        n = int(0.45 * c.sr); t = np.arange(n) / c.sr; ph = 2 * np.pi * np.cumsum(45 + 75 * np.exp(-t / 0.04)) / c.sr
        return (np.sin(ph) * np.exp(-t / 0.16) + 0.05 * c.rng.standard_normal(n) * np.exp(-t / 0.005)) * v * 0.7
    snare = lambda v: (SN * np.exp(-tS / 0.07) * 0.8 + np.sin(2 * np.pi * 185 * tS) * np.exp(-tS / 0.05) * 0.5) * v * 0.55
    hat = lambda v, o=False: HH * np.exp(-tH / (0.06 if o else 0.018)) * v * 0.16
    kpat = [[0, 5], [0, 3, 5], [0, 5, 7], [0, 2, 5]][c.rng.integers(4)]
    L = np.zeros(c.n); R = np.zeros(c.n)
    for b in range(int(np.ceil(c.secs / bar)) + 1):
        for k in range(8):
            t = eighth(b, k)
            if k in kpat: s = kick(0.9 if k == 0 else 0.7); at(c, L, s, t); at(c, R, s, t)
            if k in (2, 6): s = snare(0.85 + 0.1 * c.rng.random()); at(c, L, s, t + .012); at(c, R, s, t + .012)
            elif c.rng.random() < 0.08: s = snare(0.18); at(c, L, s, t); at(c, R, s, t)
            s = hat(0.6 + 0.4 * c.rng.random() if k % 2 == 0 else 0.35 + 0.3 * c.rng.random(), k == 7 and c.rng.random() < 0.3)
            at(c, L, s * .6, t); at(c, R, s * .8, t)
    return np.stack([L, R], 1) / (max(np.abs(L).max(), np.abs(R).max()) + 1e-9)
def lofi_musicbox(c, prog=None):
    beat, bar, eighth = _lofi_grid(c); pr = _lofi_prog(c, prog); root = 48 + c.tonic; out = np.zeros(c.n)
    def box(m, v):
        n = int(2.5 * c.sr); t = np.arange(n) / c.sr; s = _musicbox(c, m, v)[:n]
        return s * (1 + 0.004 * np.sin(2 * np.pi * 5.5 * t))
    for b in range(int(np.ceil(c.secs / bar)) + 1):
        semi = pr[b % len(pr)][0]
        if b % 2 == 1 or c.rng.random() < 0.6:
            deg = c.rng.integers(0, 7)
            for k in sorted(c.rng.choice(8, size=c.rng.integers(3, 6), replace=False)):
                deg = int(np.clip(deg + c.rng.choice([-2, -1, 1, 2, 0], p=[.15, .3, .3, .15, .1]), 0, 9))
                sc = SCALES['harmonic'] if semi == 7 else SCALES['minor']
                at(c, out, box(root + 36 + sc[deg % 7] + 12 * (deg // 7), 0.6 + 0.4 * c.rng.random()), eighth(b, k))
    return norm(out)
def vinyl(c, crackle=9):
    """Vinyl crackle + tape hiss bed."""
    cr = np.zeros(c.n); idx = c.rng.integers(0, c.n, int(c.secs * crackle)); cr[idx] = c.rng.choice([-1, 1], len(idx)) * c.rng.random(len(idx)) ** 3
    cr = np.convolve(cr, np.exp(-np.arange(40) / 6), 'same')
    return norm(norm(cr) + 0.25 * norm(lp(c, c.rng.standard_normal(c.n), 5000)))


# ---------------- bus processors (native) ----------------
def tape_wow(c, st, depth=0.003, rate=0.55, flutter=0.0006):
    src = c.t + depth / (2 * np.pi * rate) * np.sin(2 * np.pi * rate * c.t) + flutter / (2 * np.pi * 3.1) * np.sin(2 * np.pi * 3.1 * c.t)
    return np.stack([np.interp(src * c.sr, np.arange(c.n), st[:, ch]) for ch in range(2)], 1)
def dust(c, st, cutoff=6500):
    return np.stack([lp(c, st[:, ch], cutoff) for ch in range(2)], 1)


LAYERS = {
    # music
    'pad': pad, 'drone': drone, 'cello': cello, 'melody': melody, 'arp_bells': arp_bells, 'dissonant_swells': dissonant_swells,
    # foley / environment
    'rain': rain, 'fire': fire, 'waves': waves, 'wind': wind, 'foghorn': foghorn, 'train': train, 'clock': clock,
    'drips': drips, 'hum': hum, 'bubbles': bubbles, 'thunder': thunder, 'water': water,
    # lo-fi
    'lofi_keys': lofi_keys, 'lofi_bass': lofi_bass, 'lofi_drums_synth': lofi_drums_synth, 'lofi_musicbox': lofi_musicbox, 'vinyl': vinyl,
}
BUS = {'tape_wow': tape_wow, 'dust': dust}

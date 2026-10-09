"""Songygen layers: Motion synth voices, Ambient Studio environments, groove drums, and the WASM FX chain.

The DSP runs in fx/host.mjs (Node). This module builds the specs, calls the host and returns NumPy arrays.
Drum kits are fetched once from songygen.com/drums into kits/<id>/ with their manifest (licence + attribution).
"""
import json, subprocess, urllib.request
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
HOST = ROOT / 'fx' / 'host.mjs'
WORK = ROOT / '.work'
KITS = ROOT / 'kits'
GROOVES = json.loads((ROOT / 'data' / 'grooves.json').read_text())
SCALE = {'major': [0, 2, 4, 5, 7, 9, 11], 'minor': [0, 2, 3, 5, 7, 8, 10]}
PROG = {'minor': [[0, 5, 2, 6], [0, 3, 5, 0], [0, 5, 3, 4], [0, 6, 5, 6]], 'major': [[0, 3, 5, 4], [0, 4, 5, 3], [0, 5, 3, 0], [0, 3, 0, 4]]}


def _host(cmd, spec, inp=None, tag='x'):
    WORK.mkdir(exist_ok=True)
    sp, out = WORK / f'{tag}.spec.json', WORK / f'{tag}.out.f32'
    sp.write_text(json.dumps(spec))
    args = ['node', str(HOST), cmd, str(sp)] + ([str(inp)] if inp else []) + [str(out)]
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode: raise RuntimeError(f'host {cmd} failed: {r.stderr[-3000:]}')
    x = np.fromfile(out, '<f4').reshape(-1, 2).astype(np.float64)
    out.unlink(); sp.unlink()
    return x


def fx(c, st, chain, tag='fx'):
    """Run a stereo buffer through a chain of Drift / Tame / Era stages."""
    if not chain: return st
    WORK.mkdir(exist_ok=True)
    inp = WORK / f'{tag}.in.f32'; st.astype('<f4').tofile(inp)
    try: return _host('fx', {'sr': c.sr, 'chain': chain}, inp, tag)
    finally: inp.unlink(missing_ok=True)


def chords(c, seed, chord_seconds=20, feel='ambient'):
    """Ambient Studio chord plan: a four-chord diatonic progression, open voicings."""
    r = np.random.default_rng(seed ^ 40503); mode = 'major' if c.mode == 'major' else 'minor'
    prog, sc = PROG[mode][int(r.integers(4))], SCALE[mode]
    step = lambda k: sc[k % 7] + 12 * (k // 7)
    out, i, t = [], 0, 0.0
    while t < c.secs:
        deg, base = prog[i % 4], 48 + c.tonic
        voicing = [0, 2, 6, 8] if feel == 'lofi' else ([0, 4, 8, 14] if r.random() < .5 else [0, 4, 7, 8])
        out.append({'at': t, 'dur': min(chord_seconds + (.25 if feel == 'lofi' else 4), c.secs - t + 4), 'notes': [base + step(deg + v) for v in voicing]})
        i += 1; t += chord_seconds
    return out


def motion(c, voice='pad', brightness=.4, chord_seconds=20, feel='ambient', preset=None, note=None, seed=1, params=None):
    """Motion synth stem. voice: drone (one long note) | pad (slow chords) | lofi_keys (jazzy chords per two bars)."""
    if voice == 'drone':
        notes = [{'at': 0, 'note': note if note is not None else 36 + c.tonic, 'vel': .8, 'dur': c.secs}]
    else:
        if voice == 'lofi_keys': chord_seconds, feel = 2 * 240 / c.bpm, 'lofi'
        vel = .5 if feel == 'lofi' else .6
        notes = [{'at': ch['at'], 'note': m, 'vel': vel, 'dur': ch['dur']} for ch in chords(c, seed, chord_seconds, feel) for m in ch['notes']]
    spec = {'sr': c.sr, 'seconds': c.secs, 'voice': voice, 'brightness': brightness, 'notes': notes, 'bpm': c.bpm, 'params': params or {}}
    if preset: spec['preset'] = preset
    return _host('motion', spec, tag=f'motion-{voice}')


def environment(c, kind='rain', seed=1, **params):
    """Ambient Studio environments: rain | sea | wind | noise (color=pink|brown|white, low, high)."""
    return _host('env', {'sr': c.sr, 'seconds': c.secs, 'kind': kind, 'seed': seed, **params}, tag=f'env-{kind}')


# ---------------- drums: Songygen grooves on sample kits ----------------
KIT_FOR = {'jazz': 'bigrusty-brushes', 'vintage': 'bigrusty-vintage', 'metal': 'crocell-metal', 'perc': 'drs-studio', 'acoustic': 'drs-studio'}
FALLBACK = {35: [36], 36: [35], 37: [40, 38], 40: [38], 39: [40, 38], 44: [42], 46: [42], 41: [43, 45], 43: [41, 45], 45: [47, 43],
            47: [45, 48], 48: [50, 47], 50: [48, 47], 49: [57, 52, 51], 57: [49], 52: [59, 49], 59: [52, 55, 49], 55: [49, 57], 51: [59, 53, 49], 53: [51]}


def kit_for(g):
    if g['kit'] in KIT_FOR: return KIT_FOR[g['kit']]
    if g['id'] in ('synthpop', 'hinrg', 'newwave', 'synthwave', 'boogie', 'industrialmetal'): return 'rx5-80s'
    if g['line'] in ('electronic', 'pop'): return 'rx5-80s' if g['year'] < 1986 else 'tr8-909'
    return 'tr8-808'


def ensure_kit(kit):
    """Download a kit once (manifest + MP3s) and decode every file to a cached float32 array."""
    d = KITS / kit; d.mkdir(parents=True, exist_ok=True); man = d / 'index.json'
    if not man.exists():
        man.write_bytes(urllib.request.urlopen(f'https://songygen.com/drums/{kit}/index.json', timeout=30).read())
    m = json.loads(man.read_text())
    for note in m['notes'].values():
        for layer in note['layers']:
            for f in layer['files']:
                mp3, npy = d / f, d / (f + '.npy')
                if npy.exists(): continue
                if not mp3.exists(): mp3.write_bytes(urllib.request.urlopen(f'https://songygen.com/drums/{kit}/{f}', timeout=30).read())
                r = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(mp3), '-f', 'f32le', '-ac', '2', '-ar', '48000', '-'], capture_output=True)
                np.save(npy, np.frombuffer(r.stdout, '<f4').reshape(-1, 2))
    return m


def drums(c, groove='lofihiphop', kit=None, bpm=None, humanize=.008, seed=1):
    """Render a Songygen groove (4-bar phrase A A A B) on a sample kit for the whole length."""
    g = next(x for x in GROOVES['grooves'] if x['id'] == groove)
    kit = kit or kit_for(g); m = ensure_kit(kit); d = KITS / kit
    bpm = bpm or c.bpm; beat = 60 / bpm; phrase = 16 * beat
    rng = np.random.default_rng(seed); rr = {}; out = np.zeros((c.n + c.sr * 3, 2))
    choke = {p: name for name, ps in (m.get('groups') or {}).items() for p in ps}
    groups = {name: np.zeros_like(out) for name in set(choke.values())}  # each choke group mixes on its own
    cut = np.exp(-np.arange(int(.08 * c.sr)) / (.012 * c.sr))[:, None]
    ends, cache = {}, {}
    hits = []
    for rep in range(int(np.ceil(c.secs / phrase)) + 1):
        for pitch, start, vel in g['hits']:
            t = (rep * 16 + start) * beat + rng.normal(0, humanize)
            if 0 <= t < c.secs + 1: hits.append((t, pitch, vel))
    hits.sort()
    for t, pitch, vel in hits:
        note = None
        for p in [pitch] + FALLBACK.get(pitch, []):
            if str(p) in m['notes']: note = m['notes'][str(p)]; break
        if note is None: continue
        v = max(1, min(127, round(vel * 127)))
        layer = next((L for L in note['layers'] if L['vel'][0] <= v <= L['vel'][1]), note['layers'][-1])
        key = (pitch, id(layer)); k = rr.get(key, 0); rr[key] = k + 1
        f = layer['files'][k % len(layer['files'])]
        smp = cache[f] if f in cache else cache.setdefault(f, np.load(d / (f + '.npy')))
        lo, hi = layer['vel']
        a = (v / 127) ** 1.6 if len(note['layers']) == 1 else .75 + .25 * (v - lo) / max(1, hi - lo)
        gain = 10 ** ((note.get('gainDb', 0) + layer['peakDb'] - note['layers'][-1]['peakDb']) / 20) * a
        i = int(t * c.sr); grp = choke.get(pitch); buf = groups[grp] if grp else out
        if grp and ends.get(grp, 0) > i:  # a new hat chokes the ringing one: fast fade, then silence
            e = ends[grp]; k = min(len(cut), e - i); buf[i:i + k] *= cut[:k]; buf[i + k:e] = 0
        seg = smp[:len(buf) - i] * gain * .9; buf[i:i + len(seg)] += seg
        if grp: ends[grp] = i + len(seg)
    for b in groups.values(): out += b
    out = out[:c.n]
    # Songygen level(): RMS to -24 dBFS, soft knee above 0.5, ceiling -1 dBFS.
    pk = np.abs(out).max()
    if pk:
        rms = np.sqrt(np.mean(out ** 2)); ceil = 10 ** (-1 / 20); gain = min(10 ** (-24 / 20) / rms, 2 * ceil / pk); knee = .5
        y = out * gain; a = np.abs(y)
        out = np.where(a <= knee, y, np.sign(y) * (knee + (ceil - knee) * np.tanh((a - knee) / (ceil - knee))))
    return out, {'groove': g['name'], 'kit': kit, 'license': m.get('license'), 'attribution': m.get('attribution'), 'source': m.get('source')}

#!/usr/bin/env python3
"""soundlab — one palette of every ambience / music tool, an idea scanner, and a seamless-loop renderer.

  soundlab.py palette                         list every tool by role (ready / manual / reference)
  soundlab.py grooves [filter]                list the 117 Songygen drum grooves
  soundlab.py scan "an idea in plain words"   score every tool against the idea; write a draft recipe
  soundlab.py render recipes/x.json [--seconds 60]
                                              render a seamless loop: WAV 48 kHz/24-bit, MP3, certificate, seam report
  soundlab.py longform out/x/loop.wav --hours 2
                                              repeat a seamless loop to full length (no re-render, no seams)
"""
import argparse, hashlib, json, re, subprocess, sys, time, zlib
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'gen'))
import native, songy  # noqa: E402

PALETTE = json.loads((ROOT / 'palette.json').read_text())['tools']
SR = 48000
NOTE = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}
ROLE_ORDER = ['bed', 'harmony', 'melody', 'rhythm', 'bass', 'environment', 'texture', 'space', 'color', 'master', 'reference']
LEVEL = {'bed': -26, 'harmony': -24, 'melody': -29, 'rhythm': -22, 'bass': -27, 'environment': -27, 'texture': -35}

# Words in an idea that imply palette tags (one word can open several doors).
SYN = {
    'halloween': ['spooky', 'witch', 'dark', 'horror', 'music box', 'thunder', 'creepy'], 'spooky': ['creepy', 'dark', 'music box', 'eerie'],
    'witch': ['cauldron', 'potion', 'music box', 'fire', 'kitchen'], 'haunted': ['eerie', 'creepy', 'dark', 'reverse', 'music box'],
    'ghost': ['eerie', 'reverse', 'distant', 'dark'], 'graveyard': ['dark', 'wind', 'eerie', 'night', 'bells'], 'cemetery': ['dark', 'wind', 'eerie', 'bells'],
    'lantern': ['night', 'fire', 'warm'], 'pumpkin': ['halloween', 'cozy', 'autumn'], 'autumn': ['melancholic', 'rain', 'wind', 'cozy', 'nostalgic'],
    'study': ['lofi', 'calm', 'library', 'rain', 'clock'], 'studying': ['study', 'lofi', 'calm', 'library'], 'focus': ['study', 'calm', 'minimal'],
    'library': ['dark academia', 'clock', 'fire', 'cello', 'piano'], 'academia': ['dark academia', 'library', 'cello', 'clock'],
    'cozy': ['fire', 'rain', 'warm', 'cozy'], 'cosy': ['cozy', 'fire', 'rain', 'warm'], 'cabin': ['fire', 'wind', 'snow', 'cozy'],
    'liminal': ['backrooms', 'fluorescent', 'hum', 'reverse', 'distant', '3am', 'mall'], 'backrooms': ['fluorescent', 'hum', 'liminal'],
    'poolrooms': ['pool', 'drip', 'water', 'flooded', 'underwater', 'liminal'], 'mall': ['mallsoft', '1980s', 'fluorescent', 'nostalgic'],
    'lighthouse': ['sea', 'foghorn', 'night', 'wind', 'lighthouse'], 'ocean': ['sea', 'waves'], 'storm': ['rain', 'thunder', 'wind'],
    'space': ['cosmic', 'void', 'vast', 'drone', 'stars'], 'cosmic': ['dread', 'lovecraft', 'void', 'space', 'drone'], 'lovecraft': ['cosmic horror', 'dread', 'eldritch', 'abyss', 'choir'],
    'lofi': ['lo-fi', 'beats', 'vinyl', 'study', 'chill', '1990s'], 'lo-fi': ['lofi'], 'beats': ['lofi', 'drums'], 'chill': ['lofi', 'calm'],
    'jazz': ['brushes', 'jazz rap', 'cafe', 'noir', 'smoky'], 'noir': ['jazz', 'rain', 'night', 'smoky', '1950s'], 'cafe': ['jazz', 'bossa', 'warm'], 'café': ['cafe'],
    'sleep': ['calm', 'slow', 'vast', 'drone', 'meditation'], 'meditation': ['drone', 'calm', 'slow', 'bells'], 'calm': ['warm', 'slow'],
    'christmas': ['bells', 'snow', 'fire', 'cozy', 'magic', 'music box'], 'winter': ['snow', 'wind', 'fire', 'ice', 'cozy'], 'snow': ['wind', 'winter', 'cozy'],
    'train': ['train', 'rain', 'night', 'journey'], 'diner': ['mallsoft', 'neon', 'hum', 'rain', '1980s'], 'vhs': ['1980s', 'tape', 'cassette', 'wow'],
    'retro': ['1980s', 'tape', 'nostalgic'], 'nostalgia': ['nostalgic', 'tape', 'vinyl', 'memory'], 'nostalgic': ['tape', 'vinyl', 'memory'],
    'underwater': ['muffled', 'water', 'distant'], 'cave': ['drip', 'dark', 'cave'], 'dungeon': ['drip', 'dark', 'crypt'], 'crypt': ['drip', 'dark', 'choir'],
    'radio': ['broken', 'signal', 'old radio'], 'analog': ['tape', 'analog horror', '1980s'], 'dream': ['dreamy', 'reverse', 'shimmer', 'floating'],
    'sad': ['melancholic', 'rain', 'piano'], 'melancholy': ['melancholic', 'rain', 'piano'], 'dark': ['dread', 'minor', 'drone'],
}
DECADE_WORDS = {'gramophone': 1950, 'shellac': 1950, 'vinyl': 1960, 'record': 1960, 'tape': 1980, 'cassette': 1980, 'vhs': 1980, 'y2k': 2000, 'ps1': 1990}


def expand(text):
    t = text.lower()
    words = re.findall(r"[a-z0-9'&-]+", t)
    direct = set(words) | {' '.join(p) for p in zip(words, words[1:])}
    via = set()
    for w in list(direct):
        for s in SYN.get(w, []): via.add(s); via.update(SYN.get(s, [])[:3])
    m = re.search(r'\b(19[5-9]0|20[0-2]0)s?\b|\b([5-9]0)s\b', t)
    decade = int(m.group(1)) if m and m.group(1) else (1900 + int(m.group(2)) if m else None)
    if decade is None: decade = next((y for w, y in DECADE_WORDS.items() if w in direct), None)
    if decade: direct.add(f'{decade}s')
    return t, direct, via - direct, decade


def score(tool, text, direct, via):
    s, hits = 0.0, []
    for tag in tool.get('tags', []):
        if tag in direct or (' ' in tag and tag in text): s += 2; hits.append(tag)
        elif tag in via: s += 1; hits.append(f'~{tag}')
    if 'default' in tool.get('tags', []): s += .3
    return s, hits


def cmd_palette(_):
    for role in ROLE_ORDER:
        tools = [t for t in PALETTE if t['role'] == role]
        print(f'\n{role.upper()} ({len(tools)})')
        for t in tools: print(f"  {t['id']:<28} {t['status']:<11} {t['name']} — {t['what']}")


def cmd_grooves(a):
    for g in songy.GROOVES['grooves']:
        line = f"{g['id']:<16} {g['name']:<22} {g['line']:<10} {g['year']} {g['bpm']:>4} bpm  swing {g['swing']:<4} {songy.kit_for(g):<17} {g['text']}"
        if not a.filter or a.filter.lower() in line.lower(): print(line)


def draft(text, direct, via, decade, ranked, seconds, seed):
    best = lambda role, minimum=0.5: next((t for s, h, t in ranked[role] if s >= minimum and t['status'].startswith('ready')), None)
    lofi = any(w in direct | via for w in ('lofi', 'lo-fi', 'beats', 'hip-hop', 'boom bap', 'jazz rap')) or 'lofi' in text
    dark = bool({'dark', 'horror', 'dread', 'halloween', 'spooky', 'cosmic', 'creepy', 'eerie', 'night'} & (direct | via))
    warm = bool({'warm', 'calm', 'morning', 'hope', 'garden', 'happy', 'cozy', 'sunset', 'summer'} & direct)
    sad = bool({'sad', 'melancholic', 'melancholy', 'lonely', 'autumn', 'rainy'} & (direct | via))
    key = {'tonic': 'D', 'mode': 'minor'} if dark or not (warm or sad) else ({'tonic': 'F', 'mode': 'major'} if warm else {'tonic': 'A', 'mode': 'minor'})
    layers, credits = [], []
    def add(tool, role, **extra):
        if not tool: return
        L = {'id': tool['id'].split('.', 1)[1].replace('.', '_'), 'tool': tool['id'], 'src': tool['src'], 'args': dict(tool.get('args', {})), 'db': LEVEL.get(role, -28), 'role': role}
        L.update(extra); layers.append(L)
    if lofi:
        groove = best('rhythm') or next(t for t in PALETTE if t['id'] == 'songy.drums.lofihiphop')
        if groove['id'] == 'songy.drums.any': groove = next(t for t in PALETTE if t['id'] == 'songy.drums.lofihiphop')
        if groove['src'] == 'songy.drums':
            g = next(x for x in songy.GROOVES['grooves'] if x['id'] == groove['args']['groove'])
            bpm = groove['args'].get('bpm', g['bpm'])
        else: bpm = 80
        add(groove, 'rhythm', fx=[{'engine': 'tame', 'preset': 'Drum bus tame'}])
        keys = best('harmony', 1) if (best('harmony', 1) or {}).get('id', '').endswith('lofi_keys') else next(t for t in PALETTE if t['id'] == 'native.lofi_keys')
        add(keys, 'harmony'); add(next(t for t in PALETTE if t['id'] == 'native.lofi_bass'), 'bass')
        mel = best('melody', 2)
        if mel: add(mel, 'melody')
        add(next(t for t in PALETTE if t['id'] == 'native.vinyl'), 'texture', db=-38)
        env = best('environment', 2)
        if env: add(env, 'environment', db=-30)
        space = {'engine': 'drift', 'preset': 'Cathedral wash', 'amount': .35}
        color = [{'engine': 'era', 'year': decade or 1990, 'authenticity': .35}, {'native': 'tape_wow'}]
        loudness = -16
    else:
        bpm = 60
        add(best('bed') or next(t for t in PALETTE if t['id'] == 'songy.motion.drone'), 'bed')
        add(best('harmony', 1) or next(t for t in PALETTE if t['id'] == 'songy.motion.pad'), 'harmony')
        mel = best('melody', 1.5)
        if mel: add(mel, 'melody')
        envs = [t for s, h, t in ranked['environment'] if s >= 2 and t['status'].startswith('ready')]
        seen = set()
        for t in envs:  # one source per kind of sound (native rain vs Ambient Studio rain)
            kind = t['name'].split(' ')[0].lower()
            if kind in seen: continue
            seen.add(kind); add(t, 'environment')
            if len(seen) == 2: break
        tex = best('texture', 2)
        if tex: add(tex, 'texture')
        sp = best('space', 1) or next(t for t in PALETTE if t['id'] == 'fx.drift.cathedral')
        space = sp['engine'] if 'engine' in sp.get('engine', {}) else {'engine': 'drift', 'preset': 'Cathedral wash', 'amount': .6}
        col = best('color', 2)
        color = [col['engine']] if col else []
        loudness = -18
    for L in layers:  # rhythm: much less reverb and no delay, the way Ambient Studio treats the beat
        if L['role'] == 'rhythm': L['space'] = {'reverb_scale': .3, 'no_delay': True}
    return {
        'title': text.strip()[:60], 'idea': text.strip(), 'profile': 'lofi' if lofi else 'ambient', 'seed': seed,
        'key': key, 'bpm': bpm, 'seconds': seconds, 'layers': layers, 'space': space, 'color': color,
        'master': [{'engine': 'tame', 'preset': 'Master smooth'}], 'loudness_lufs': loudness, 'true_peak_db': -1.5,
    }


def cmd_scan(a):
    text, direct, via, decade = expand(a.idea)
    ranked = {r: [] for r in ROLE_ORDER}
    for t in PALETTE:
        s, h = score(t, text, direct, via); ranked[t['role']].append((s, h, t))
    for r in ranked: ranked[r].sort(key=lambda x: -x[0])
    n = len(PALETTE); st = lambda k: sum(1 for t in PALETTE if t['status'].startswith(k))
    print(f'Idea: {a.idea}\nScanned {n} tools (ready {st("ready")}, manual {st("manual")}, reference {st("reference")}).')
    print(f"Matched words: {', '.join(sorted(direct & {g for t in PALETTE for g in t['tags']})) or '-'};  implied: {', '.join(sorted(via & {g for t in PALETTE for g in t['tags']}))[:300] or '-'}")
    for r in ROLE_ORDER:
        rows = [x for x in ranked[r] if x[0] > 0.3][:a.top]
        if not rows: continue
        print(f'\n{r.upper()}')
        for s, h, t in rows: print(f"  {s:4.1f}  {t['id']:<28} {t['status']:<11} {t['name']}  [{', '.join(h)}]")
    recipe = draft(text, direct, via, decade, ranked, a.seconds, a.seed)
    slug = re.sub(r'[^a-z0-9]+', '-', a.idea.lower()).strip('-')[:48] or 'idea'
    path = ROOT / 'recipes' / f'{slug}.json'
    path.write_text(json.dumps(recipe, indent=1))
    print(f"\nDraft recipe ({recipe['profile']}, {recipe['key']['tonic']} {recipe['key']['mode']}, {recipe['bpm']} bpm): {path}")
    for L in recipe['layers']: print(f"  {L['role']:<11} {L['tool']:<28} {L['db']} dB")
    print(f"  space  {recipe['space']}\n  color  {recipe['color']}\n  master {recipe['master']}")
    manual = [t for t in PALETTE if not t['status'].startswith('ready') and score(t, text, direct, via)[0] >= 1]
    for t in manual: print(f"  also consider ({t['status']}): {t['name']} — {t.get('how', '')}")


# ---------------- render ----------------
def stereo(x, pan=0.0):
    if x.ndim == 2: return x
    d = int(0.013 * SR)  # mono → stereo: short Haas delay on the right, then pan
    st = np.stack([x, np.concatenate([np.zeros(d), x[:-d]])], 1) * 0.7
    return st * np.array([np.sqrt(1 - pan), np.sqrt(1 + pan)])


def make_layer(L, recipe, secs):
    seed = (recipe['seed'] * 1000003 + zlib.crc32(L['id'].encode())) % 2 ** 31
    tonic = NOTE[recipe['key']['tonic']]; c = native.Ctx(SR, secs, seed, tonic, recipe['key']['mode'], recipe['bpm'])
    src, args, credit = L['src'], dict(L.get('args', {})), None
    if src.startswith('native.'): x = native.LAYERS[src.split('.', 1)[1]](c, **args)
    elif src == 'songy.motion': x = songy.motion(c, seed=seed, **args)
    elif src == 'songy.env': x = songy.environment(c, seed=seed, **args)
    elif src == 'songy.drums':
        args.setdefault('bpm', recipe['bpm']); x, credit = songy.drums(c, seed=seed, **args)
    else: raise SystemExit(f"Layer {L['id']}: source {src} cannot render here (manual tool).")
    return c, stereo(np.asarray(x, dtype=np.float64), L.get('pan', 0.0)), credit


def apply_chain(c, st, chain, tag):
    out = st
    i = 0
    while i < len(chain):
        stage = chain[i]
        if 'native' in stage:
            name = stage['native']
            if name == 'reverb':
                out = np.stack([native.reverb(c, out[:, ch], stage.get('secs', 3), stage.get('mix', .4), stage.get('bright', 3500))[:, ch] for ch in range(2)], 1)
            else: out = native.BUS[name](c, out, **{k: v for k, v in stage.items() if k != 'native'})
            i += 1
        else:  # group consecutive engine stages into one host call
            j = i
            while j < len(chain) and 'native' not in chain[j]: j += 1
            out = songy.fx(c, out, chain[i:j], tag); i = j
    return out


def measure(path):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostdin', '-i', str(path), '-af', 'loudnorm=print_format=json', '-f', 'null', '-'], capture_output=True, text=True)
    m = json.loads(re.search(r'\{[^{}]*"input_i"[^{}]*\}', r.stderr, re.S).group())
    return float(m['input_i']), float(m['input_tp'])


def seam_report(x, ref, head, tail):
    """Is the loop point seamless?
    error_db: loop end → loop start (10 ms each side) against the continuous render at the same moment; a click shows above -30 dB.
    sample_jump: last → first sample against the largest steps inside the loop.
    xfade_similarity: how alike the two crossfaded regions are (1 = identical; low values on a beat = doubled hits)."""
    d = np.abs(np.diff(x, axis=0)).max(1); jump = np.abs(x[0] - x[-1]).max(); w = len(ref) // 2
    played = np.concatenate([x[-w:], x[:w]])
    err = 20 * np.log10(np.sqrt(np.mean((played - ref) ** 2)) / (np.sqrt(np.mean(ref ** 2)) + 1e-12) + 1e-12)
    sim = float(np.sum(head * tail) / (np.sqrt(np.sum(head ** 2) * np.sum(tail ** 2)) + 1e-12))
    ok = err < -30 and jump <= np.percentile(d, 99.9) * 1.5
    return {'pass': bool(ok), 'error_db': round(float(err), 1), 'sample_jump': round(float(jump), 5),
            'jump_p99_9_inside': round(float(np.percentile(d, 99.9)), 5), 'xfade_similarity': round(sim, 2)}


def cmd_render(a):
    t0 = time.time(); recipe = json.loads(Path(a.recipe).read_text())
    loop = a.seconds or recipe.get('seconds', 180); xf = recipe.get('crossfade', 4.0); lead = 8.0
    if recipe['profile'] == 'lofi' or any(L['src'] == 'songy.drums' for L in recipe['layers']):
        phrase = 32 * 60 / recipe['bpm']  # loop and lead-in in whole 8-bar units: the groove (4 bars) and chord cycle (up to 8 bars) line up
        loop = max(1, round(loop / phrase)) * phrase; lead = max(1, np.ceil(8 / phrase)) * phrase
    total = lead + loop + xf + 1
    if loop > 420: print('warning: loops over 7 minutes need a lot of RAM on this server; prefer 3–5 minutes + longform.')
    slug = Path(a.recipe).stem; out_dir = ROOT / 'out' / slug; out_dir.mkdir(parents=True, exist_ok=True)
    mix, credits, a0, a1 = None, [], int(lead * SR), int((lead + loop) * SR)
    for L in recipe['layers']:
        t1 = time.time(); c, x, credit = make_layer(L, recipe, total)
        if credit: credits.append(credit)
        rms = np.sqrt(np.mean(x[a0:a1] ** 2)) + 1e-12; x *= 10 ** (L['db'] / 20) / rms   # absolute RMS level, as in ambient.py
        chain = list(L.get('fx', []))
        sp = L.get('space', True)
        if sp and recipe.get('space'):
            stage = dict(recipe['space'])
            if isinstance(sp, dict): stage.update(sp)
            chain.append(stage)
        if chain: x = apply_chain(c, x, chain, f"layer-{L['id']}")
        mix = x if mix is None else mix + x
        print(f"  layer {L['id']:<20} {L['src']:<16} {time.time() - t1:5.1f}s", flush=True)
    bus = native.Ctx(SR, total, recipe['seed'])
    mix = apply_chain(bus, mix, list(recipe.get('color', [])) + list(recipe.get('master', [])), 'bus')
    # Seamless loop (Songygen Ambient Studio method): the tail after the loop end is crossfaded, equal-power, over the start.
    n, k = a1 - a0, int(xf * SR); o = (np.arange(k) + .5) / k
    loopx = mix[a0:a1].copy()
    loopx[:k] = mix[a0:a0 + k] * np.sin(o * np.pi / 2)[:, None] + mix[a1:a1 + k] * np.cos(o * np.pi / 2)[:, None]
    raw = out_dir / 'loop.f32'; loopx.astype('<f4').tofile(raw)
    tmp = out_dir / '_measure.wav'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', str(raw), '-c:a', 'pcm_f32le', str(tmp)], check=True)
    I, TP = measure(tmp); gain = min(recipe.get('loudness_lufs', -18) - I, recipe.get('true_peak_db', -1.5) - TP)
    loopx *= 10 ** (gain / 20); loopx.astype('<f4').tofile(raw); tmp.unlink()
    wav, mp3 = out_dir / 'loop.wav', out_dir / 'loop.mp3'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', str(raw), '-c:a', 'pcm_s24le', str(wav)], check=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-stream_loop', '1', '-i', str(wav), '-c:a', 'libmp3lame', '-b:a', '256k', str(mp3)], check=True)
    raw.unlink()
    g, w = 10 ** (gain / 20), SR // 100
    seam = seam_report(loopx, mix[a1 - w:a1 + w] * g, mix[a0:a0 + k], mix[a1:a1 + k])
    I2, TP2 = measure(wav)
    lock = json.loads((ROOT / 'engines' / 'lock.json').read_text())
    used = sorted({s.get('engine') for L in recipe['layers'] for s in L.get('fx', []) + [recipe.get('space') or {}] if s.get('engine')} |
                  {s.get('engine') for s in recipe.get('color', []) + recipe.get('master', []) if s.get('engine')} |
                  {'motion' for L in recipe['layers'] if L['src'] == 'songy.motion'})
    cert = {
        'product': 'soundlab (bob, Timeless Ambience)', 'made': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'recipe': recipe, 'loop_seconds': round(loop, 3), 'sample_rate': SR,
        'loop': 'The tail after the loop end is crossfaded over the start (equal power, %.1f s): the file repeats with no seam.' % xf,
        'engines': {e: lock[e] for e in used if e in lock},
        'sources': 'Synthesized on this server. ' + ('Recorded drum samples: ' + '; '.join(f"{c['kit']} ({c['license']}): {c['attribution']}" for c in credits) if credits else 'No recordings and no third-party samples.'),
        'loudness': {'lufs': round(I2, 1), 'true_peak_db': round(TP2, 1)}, 'seam': seam,
        'wav_sha256': hashlib.sha256(wav.read_bytes()).hexdigest(),
        'note': 'Songygen engines and Ambient Studio code are used with the songygen.com owner\'s permission (confirmed 2026-10-09).' if used or any(L['src'].startswith('songy') for L in recipe['layers']) else '',
    }
    (out_dir / 'certificate.json').write_text(json.dumps(cert, indent=1))
    print(f"\n{wav}\n  {loop:.1f} s loop, {I2:.1f} LUFS, true peak {TP2:.1f} dB, seam {'PASS' if seam['pass'] else 'CHECK'} {seam}\n  preview (loop played twice): {mp3}\n  took {time.time() - t0:.0f}s")


def cmd_longform(a):
    src = Path(a.loop); secs = a.hours * 3600; out = Path(a.out) if a.out else src.with_name(f'longform-{a.hours:g}h.flac')
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(src)], capture_output=True, text=True).stdout)
    reps = int(np.ceil(secs / dur))
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-stream_loop', str(reps), '-i', str(src), '-t', str(secs), '-c:a', 'flac', str(out)], check=True)
    print(f'{out}: {a.hours:g} h = {reps} × {dur:.1f} s loop')


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter); sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('palette').set_defaults(f=cmd_palette)
    g = sub.add_parser('grooves'); g.add_argument('filter', nargs='?'); g.set_defaults(f=cmd_grooves)
    s = sub.add_parser('scan'); s.add_argument('idea'); s.add_argument('--top', type=int, default=4); s.add_argument('--seconds', type=float, default=180); s.add_argument('--seed', type=int, default=1); s.set_defaults(f=cmd_scan)
    r = sub.add_parser('render'); r.add_argument('recipe'); r.add_argument('--seconds', type=float); r.set_defaults(f=cmd_render)
    l = sub.add_parser('longform'); l.add_argument('loop'); l.add_argument('--hours', type=float, default=2); l.add_argument('--out'); l.set_defaults(f=cmd_longform)
    a = p.parse_args(); a.f(a)


if __name__ == '__main__':
    main()

// Offline host for the Songygen WASM engines (Drift, Tame, Era, Motion). No browser, no network.
//   node host.mjs fx     SPEC.json IN.f32 OUT.f32   — run a stereo f32le buffer through a chain
//   node host.mjs motion SPEC.json OUT.f32          — render notes on the Motion synth
//   node host.mjs env    SPEC.json OUT.f32          — Ambient Studio rain / sea / wind / coloured noise
//   node host.mjs info                              — list engines, presets and parameter counts
// Buffers are interleaved stereo float32. Every engine file is checked against engines/lock.json.
import {existsSync, readFileSync, writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {dirname, join} from 'node:path';
import {fileURLToPath} from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const LOCK = JSON.parse(readFileSync(join(ROOT, 'engines/lock.json'), 'utf8'));
const TAME = JSON.parse(readFileSync(join(ROOT, 'data/tame_presets.json'), 'utf8'));

async function engine(name) {
  const path = join(ROOT, 'engines', name + '.wasm');
  if (!existsSync(path)) {  // not in git: fetch once from songygen.com, keep only an exact match
    const res = await fetch(LOCK[name].url);
    if (!res.ok) throw Error(`Could not download ${name}.wasm (${res.status}).`);
    const got = Buffer.from(await res.arrayBuffer());
    if (createHash('sha256').update(got).digest('hex') !== LOCK[name].sha256) throw Error(`Downloaded ${name}.wasm differs from engines/lock.json — Songygen shipped a new build; review it, then update the lock.`);
    writeFileSync(path, got);
  }
  const bytes = readFileSync(path);
  const sha = createHash('sha256').update(bytes).digest('hex');
  if (sha !== LOCK[name].sha256) throw Error(`${name}.wasm does not match engines/lock.json — review the new build before use.`);
  return (await WebAssembly.instantiate(bytes, {})).instance.exports;
}

// ---------- Drift: delay + reverb ----------
const DRIFT = {TIME:0,REPEATS:1,TONE:2,D_MIX:3,DECAY:4,R_MIX:5,MODE:6,RATIO:7,EXP_TARGET:8,EXP:9,EXP_ON:10,ACTIVE:11,TAILS:12,ROUTING:13,HOLD:14,SPREAD:15,MOD:16,DUCK:17,LOFI:18,SWELL:19,PREDELAY:20,R_TONE:21,FREEZE:22,OUT_DB:23};
const DRIFT_DEFAULT = {TIME:420,REPEATS:.4,TONE:0,D_MIX:.35,DECAY:.5,R_MIX:.3,MODE:0,RATIO:0,EXP_TARGET:2,EXP:0,EXP_ON:0,ACTIVE:1,TAILS:2,ROUTING:0,HOLD:0,SPREAD:0,MOD:0,DUCK:0,LOFI:0,SWELL:-1,PREDELAY:12,R_TONE:0,FREEZE:0,OUT_DB:0};
// Songygen Drift presets (drift page), values as published on 2026-10-09.
export const DRIFT_PRESETS = {
  'Reverb only': {D_MIX:0,R_MIX:.45,DECAY:.55},
  'Glacier': {TIME:720,REPEATS:.72,TONE:-.45,D_MIX:.55,DECAY:.88,R_MIX:.6,MOD:.25,SPREAD:.4,PREDELAY:40},
  'Northern lights': {TIME:560,REPEATS:.62,TONE:.25,D_MIX:.5,DECAY:.8,R_MIX:.55,MOD:.4,SPREAD:.8,R_TONE:.35},
  'Cathedral wash': {TIME:900,REPEATS:.5,TONE:-.2,D_MIX:.3,DECAY:.96,R_MIX:.78,PREDELAY:60},
  'Weightless': {TIME:1200,REPEATS:.88,TONE:-.3,D_MIX:.92,DECAY:.9,R_MIX:.7,MOD:.3,SPREAD:.6},
  'Under the ice': {TIME:650,REPEATS:.7,TONE:-.85,D_MIX:.5,DECAY:.75,R_MIX:.5,MOD:.6,R_TONE:-.6},
  'Ducked pad': {TIME:600,REPEATS:.65,D_MIX:.6,DECAY:.85,R_MIX:.65,DUCK:.7,SPREAD:.5},
  'Backwards': {MODE:1,TIME:520,REPEATS:.3,D_MIX:.62,DECAY:.55,R_MIX:.35},
  'Reverse bloom': {MODE:1,TIME:1100,REPEATS:.45,TONE:-.25,D_MIX:.7,DECAY:.85,R_MIX:.6,SPREAD:.5},
  'Violin': {MODE:2,TIME:480,REPEATS:.35,D_MIX:.35,DECAY:.6,R_MIX:.45},
  'Slow tide': {MODE:2,SWELL:.85,TIME:800,REPEATS:.7,D_MIX:.55,DECAY:.85,R_MIX:.6,MOD:.25},
  'Tape echo': {TIME:340,REPEATS:.6,TONE:-.4,D_MIX:.45,MOD:.45,LOFI:.45,R_MIX:.2,DECAY:.4},
  'Broken radio': {TIME:420,REPEATS:.72,TONE:.6,D_MIX:.5,LOFI:.85,MOD:.3,R_MIX:.15},
  'Room': {TIME:140,REPEATS:.1,D_MIX:.15,DECAY:.18,R_MIX:.3,PREDELAY:5},
  'Quarter bounce': {TIME:500,REPEATS:.4,D_MIX:.45,SPREAD:.9,R_MIX:.15},
};
function driftValues(stage) {
  const v = {...DRIFT_DEFAULT, ...(DRIFT_PRESETS[stage.preset] ?? {}), ...(stage.params ?? {})};
  // "amount" scales the space the way Ambient Studio does: reverb mix × amount, delay mix × amount × 0.6.
  if (stage.amount !== undefined) { v.R_MIX *= stage.amount; v.D_MIX *= stage.amount * .6; }
  if (stage.reverb_scale !== undefined) v.R_MIX *= stage.reverb_scale;
  if (stage.no_delay) v.D_MIX = 0;
  return v;
}

// ---------- Era: decade colour ----------
const ERA = {YEAR:0,CHARACTER:1,MIX:2,OUTPUT:3,BYPASS:4,ROOM:5,ARTEFACTS:6,MATCH:7,INPUT_DB:8};
export const ERAS = {1950:'Shellac',1960:'Tungsten',1970:'Console',1980:'Neon',1990:'Dust',2000:'Digital',2010:'Teal',2020:'Ice'};

async function processStage(stage, sr, L, R) {
  const n = L.length;
  if (stage.engine === 'drift') {
    const w = await engine('drift'), d = w.drift_new(sr);
    for (const [k, v] of Object.entries(driftValues(stage))) w.drift_set(d, DRIFT[k], v);
    return block(w, n, (l, r, m) => w.drift_process(d, l, r, m), w.drift_buffer, L, R, 0);
  }
  if (stage.engine === 'tame') {
    const w = await engine('tame'), t = w.tame_new(sr), G = TAME.param_ids;
    const p = TAME.presets.find(x => x.name === (stage.preset ?? 'Master smooth'));
    if (!p) throw Error(`Unknown Tame preset: ${stage.preset}`);
    if (!p.default) for (let b = 0; b < 8; b++) w.tame_set(t, 100 + 8 * b, 0);
    p.bands.forEach(([shape, freq, gain, q], b) => {
      for (const [f, v] of [[0, 1], [1, shape], [2, freq], [3, gain], [4, q]]) w.tame_set(t, 100 + 8 * b + f, v);
    });
    for (const [k, v] of Object.entries({...p.params, ...(stage.params ?? {})})) w.tame_set(t, G[k], v);
    w.tame_set(t, G.LISTEN_BAND, -1);
    return block(w, n, (l, r, m) => w.tame_process(t, l, r, m), w.tame_buffer, L, R, w.tame_latency(t));
  }
  if (stage.engine === 'era') {
    const w = await engine('era'), e = w.era_new(sr);
    const vals = [[ERA.YEAR, stage.year ?? 1990], [ERA.CHARACTER, stage.authenticity ?? .35], [ERA.MIX, stage.mix ?? 1],
      [ERA.OUTPUT, 10 ** ((stage.output_db ?? 0) / 20)], [ERA.BYPASS, 0]];
    if (stage.artefacts !== undefined) vals.push([ERA.ARTEFACTS, stage.artefacts]);
    for (const [id, v] of vals) w.era_set(e, id, v);
    return block(w, n, (l, r, m) => w.era_process(e, l, r, m), w.era_buffer, L, R, 0);
  }
  throw Error(`Unknown engine: ${stage.engine}`);
}

// Process the whole buffer in blocks; drop `latency` samples so the output lines up with the input.
function block(w, n, proc, alloc, L, R, latency) {
  const B = 4096, bl = alloc(B), br = alloc(B), total = n + latency;
  const oL = new Float32Array(total), oR = new Float32Array(total);
  for (let at = 0; at < total; at += B) {
    const m = Math.min(B, total - at);
    const xl = new Float32Array(w.memory.buffer, bl, m), xr = new Float32Array(w.memory.buffer, br, m);
    xl.fill(0); xr.fill(0);
    if (at < n) { xl.set(L.subarray(at, Math.min(n, at + m))); xr.set(R.subarray(at, Math.min(n, at + m))); }
    proc(bl, br, m);
    oL.set(new Float32Array(w.memory.buffer, bl, m), at); oR.set(new Float32Array(w.memory.buffer, br, m), at);
  }
  return [oL.subarray(latency, latency + n), oR.subarray(latency, latency + n)];
}

// ---------- Motion: synth voice ----------
const M = {SOURCE:0,BPM:1,VOLUME_DB:2,CUTOFF:3,RESO:4,DRIVE:5,FILTER_TYPE:6,PAN:7,WIDTH:8,MIX:9,GAIN_DB:10,OSC1_LEVEL:11,OSC1_MORPH:12,OSC2_LEVEL:13,OSC2_MORPH:14,OSC2_TUNE:15,UNISON:16,DETUNE:17,SUB:18,NOISE:19,GLIDE:20,VOICES:21};
const ENV = (e, f) => 40 + 10 * e + f, ENVF = {DELAY:0,ATTACK:1,HOLD:2,DECAY:3,SUSTAIN:4,RELEASE:5};
const LFO = (l, f) => 80 + 12 * l + f, LFOF = {MODE:0,SYNC:1,RATE_HZ:2,DIVISION:3};
const SRC = {ENV1:0,ENV2:1,LFO1:3,LFO2:4,RANDOM1:7,VELOCITY:10};
const pts = (...a) => a.map(([x, y, c]) => [x, y, c ?? 0]);
const SHAPES = {
  Sine: pts([0,.5,-2.2],[.25,1,2.2],[.5,.5,-2.2],[.75,0,2.2],[1,.5]),
  Breathe: pts([0,0,3],[.5,1,-3],[1,0]),
  Triangle: pts([0,0],[.5,1],[1,0]),
};
// Motion presets used by Songygen Ambient Studio (drone, pad, lo-fi keys) plus two from the Motion page.
const MP = (vals, shapes, mods) => ({vals, shapes, mods});
const SLOW_TIDE = MP({[ENV(0,1)]:.9,[ENV(0,3)]:1.5,[ENV(0,4)]:.75,[ENV(0,5)]:2.2,[M.OSC1_MORPH]:.6,[M.OSC2_LEVEL]:.5,[M.OSC2_MORPH]:.55,[M.OSC2_TUNE]:12,[M.UNISON]:5,[M.DETUNE]:.35,[M.CUTOFF]:1400,[M.RESO]:.25,[LFO(0,1)]:0,[LFO(0,2)]:.12,[LFO(1,1)]:0,[LFO(1,2)]:.07,[LFO(0,0)]:1,[LFO(1,0)]:1},
  ['Sine','Sine'], [[SRC.LFO1, M.CUTOFF, .18, 1], [SRC.LFO2, M.PAN, .6, 1]]);
export const MOTION_PRESETS = {
  'Slow tide pad': SLOW_TIDE,
  'Breathing strings': MP({[ENV(0,1)]:1.6,[ENV(0,4)]:.85,[ENV(0,5)]:1.8,[M.OSC1_MORPH]:.62,[M.UNISON]:7,[M.DETUNE]:.25,[M.CUTOFF]:900,[LFO(0,0)]:1,[LFO(0,3)]:4}, ['Breathe'], [[SRC.LFO1, M.CUTOFF, .4, 0]]),
  'Glass keys': MP({[ENV(0,1)]:.003,[ENV(0,3)]:1.4,[ENV(0,4)]:.2,[ENV(0,5)]:.9,[M.OSC1_MORPH]:.2,[M.OSC2_LEVEL]:.4,[M.OSC2_MORPH]:.1,[M.OSC2_TUNE]:19,[M.CUTOFF]:900,[ENV(1,1)]:0,[ENV(1,3)]:.6,[ENV(1,4)]:.1}, ['Sine'], [[SRC.ENV2, M.CUTOFF, .5, 0], [SRC.VELOCITY, M.CUTOFF, .2, 0]]),
};
// Ambient Studio's derived voices: brightness 0..1 sets the cutoff exactly as on the site.
function motionVoice(spec) {
  const base = MOTION_PRESETS[spec.preset ?? 'Slow tide pad'];
  const vals = {...base.vals}, b = spec.brightness ?? .4;
  if (spec.voice === 'drone') Object.assign(vals, {[M.OSC1_MORPH]:.3,[M.OSC2_LEVEL]:.35,[M.OSC2_TUNE]:7,[M.UNISON]:3,[M.DETUNE]:.12,[M.SUB]:.6,[M.CUTOFF]:180+900*b,[M.RESO]:.15,[ENV(0,1)]:6,[ENV(0,4)]:1,[ENV(0,5)]:6,[LFO(0,2)]:.031,[LFO(1,2)]:.019});
  if (spec.voice === 'pad') Object.assign(vals, {[M.CUTOFF]:450+2600*b,[ENV(0,1)]:3.5,[ENV(0,5)]:5});
  if (spec.voice === 'lofi_keys') Object.assign(vals, {[M.CUTOFF]:400+1800*b,[M.UNISON]:3,[M.DETUNE]:.18,[ENV(0,1)]:.25,[ENV(0,5)]:1.2});
  Object.assign(vals, Object.fromEntries(Object.entries(spec.params ?? {}).map(([k, v]) => [M[k] ?? Number(k), v])));
  return {vals, shapes: base.shapes, mods: [[SRC.ENV1, M.VOLUME_DB, 1, 0], ...base.mods]};
}
async function renderMotion(spec) {
  const w = await engine('motion'), sr = spec.sr, m = w.motion_new(sr), v = motionVoice(spec);
  for (const [k, val] of Object.entries(v.vals)) w.motion_set(m, Number(k), val);
  v.shapes.forEach((name, i) => {
    const p = SHAPES[name].flat(), ptr = w.motion_buffer(p.length);
    new Float32Array(w.memory.buffer, ptr, p.length).set(p); w.motion_shape(m, i, ptr, SHAPES[name].length);
  });
  v.mods.forEach(([src, dst, amount, bip], slot) => w.motion_mod_set(m, slot, src, dst, amount, bip));
  const n = Math.round(spec.seconds * sr), B = 256, bl = w.motion_buffer(B), br = w.motion_buffer(B);
  const ev = (spec.notes ?? []).flatMap(x => [{t: Math.round(x.at * sr), on: 1, x}, {t: Math.round((x.at + x.dur) * sr), on: 0, x}]).sort((a, b) => a.t - b.t);
  const out = new Float32Array(n * 2), bpm = spec.bpm ?? 120;
  let p = 0;
  for (let at = 0; at < n; at += B) {
    const k = Math.min(B, n - at);
    while (p < ev.length && ev[p].t < at + k) { const e = ev[p++]; e.on ? w.motion_note_on(m, e.x.note, e.x.vel ?? .8) : w.motion_note_off(m, e.x.note); }
    w.motion_transport(m, 1, at / sr * bpm / 60);
    new Float32Array(w.memory.buffer, bl, k).fill(0); new Float32Array(w.memory.buffer, br, k).fill(0);
    w.motion_process(m, bl, br, k);
    const L = new Float32Array(w.memory.buffer, bl, k), R = new Float32Array(w.memory.buffer, br, k);
    for (let i = 0; i < k; i++) { out[2 * (at + i)] = L[i]; out[2 * (at + i) + 1] = R[i]; }
  }
  return out;
}

// ---------- Ambient Studio environments (rain, sea, wind, coloured noise), ported from AmbientPage ----------
function rng(seed) { let t = seed >>> 0; return () => { t = t + 1831565813 >>> 0; let e = t; e = Math.imul(e ^ e >>> 15, e | 1); e ^= e + Math.imul(e ^ e >>> 7, e | 61); return ((e ^ e >>> 14) >>> 0) / 4294967296; }; }
function noise(color, n, seed) {
  const r = rng(seed), x = new Float32Array(n); let a = 0, o = 0, s = 0, c = 0, l = 0, u = 0, d = 0, f = 0;
  for (let i = 0; i < n; i++) {
    const t = r() * 2 - 1;
    if (color === 'white') x[i] = t * .5;
    else if (color === 'pink') { a = .99886 * a + t * .0555179; o = .99332 * o + t * .0750759; s = .969 * s + t * .153852; c = .8665 * c + t * .3104856; l = .55 * l + t * .5329522; u = -.7616 * u - t * .016898; x[i] = (a + o + s + c + l + u + d + t * .5362) * .11; d = t * .115926; }
    else { f = .998 * f + t * .04; x[i] = f * 1.6; }
  }
  return x;
}
function svf(x, sr, type, cutoffAt, q = .707) {  // state-variable filter, cutoff re-read every 32 samples
  let a = 0, o = 0, g = 0, k = 1 / q, a1 = 0, a2 = 0, a3 = 0;
  for (let i = 0; i < x.length; i++) {
    if (!(i & 31)) { const fc = Math.min(sr * .45, Math.max(10, cutoffAt(i))); g = Math.tan(Math.PI * fc / sr); k = 1 / q; a1 = 1 / (1 + g * (g + k)); a2 = g * a1; a3 = g * a2; }
    const v0 = x[i], v3 = v0 - o, v1 = a1 * a + a2 * v3, v2 = o + a2 * a + a3 * v3;
    a = 2 * v1 - a; o = 2 * v2 - o;
    x[i] = type === 'lp' ? v2 : type === 'bp' ? v1 : v0 - k * v1 - v2;
  }
  return x;
}
function smoothRandom(seed, period) { const r = rng(seed), pts = []; return t => { const i = Math.floor(t / period); while (pts.length <= i + 1) pts.push(r()); const u = t / period - i, w = (1 - Math.cos(Math.PI * u)) / 2; return pts[i] * (1 - w) + pts[i + 1] * w; }; }
const ENVGEN = {
  noise({color = 'pink', low = 100, high = 4000}, n, sr, seed) {
    return [0, 1].map(ch => {
      const x = noise(color, n, seed + ch * 7919), mod = smoothRandom(seed + 31 + ch, 9);
      svf(x, sr, 'hp', () => low, .6); svf(x, sr, 'lp', i => high * (.75 + .5 * mod(i / sr)), .6);
      const amp = smoothRandom(seed + 77, 13); for (let i = 0; i < n; i++) x[i] *= .55 + .45 * amp(i / sr);
      return x;
    });
  },
  sea(_, n, sr, seed) {
    const r = rng(seed), swells = [];
    for (let t = -4; t < n / sr + 12;) { const len = 6 + r() * 5; swells.push({t, len, size: .55 + r() * .45}); t += len * (.7 + r() * .2); }
    const level = (t, off) => { let v = 0; for (const s of swells) { const u = (t - s.t - off) / s.len; if (u > 0 && u < 1) v += s.size * (u < .6 ? Math.sin(u / .6 * Math.PI / 2) ** 2 : Math.cos((u - .6) / .4 * Math.PI / 2) ** 1.5); } return Math.min(1.4, v); };
    return [0, 1].map(ch => {
      const x = noise('brown', n, seed + 101 + ch), off = ch * .35;
      svf(x, sr, 'lp', i => 250 + 2200 * level(i / sr, off) ** 2, .5);
      for (let i = 0; i < n; i++) x[i] *= .15 + 1.1 * level(i / sr, off);
      return x;
    });
  },
  rain({drops_per_sec = 26}, n, sr, seed) {
    const out = [0, 1].map(ch => { const x = noise('pink', n, seed + 211 + ch); svf(x, sr, 'hp', () => 1800, .5); svf(x, sr, 'lp', () => 9000, .5); for (let i = 0; i < n; i++) x[i] *= .35; return x; });
    const r = rng(seed + 5);
    for (let t = 0; ;) {
      t += -Math.log(1 - r()) / drops_per_sec; const i0 = Math.floor(t * sr); if (i0 >= n) break;
      const f = 1800 + r() * 3200, amp = .04 + r() * r() * .35, pan = r(), len = Math.floor(.012 * sr + r() * .02 * sr), w = 2 * Math.PI * f / sr;
      for (let j = 0; j < len && i0 + j < n; j++) { const v = amp * Math.exp(-j / (.0035 * sr)) * Math.sin(w * j); out[0][i0 + j] += v * Math.cos(pan * Math.PI / 2); out[1][i0 + j] += v * Math.sin(pan * Math.PI / 2); }
    }
    return out;
  },
  wind(_, n, sr, seed) {
    return [0, 1].map(ch => {
      const x = noise('pink', n, seed + 307 + ch), f = smoothRandom(seed + 13 + ch, 5), g = smoothRandom(seed + 17, 7);
      svf(x, sr, 'bp', i => 250 + 1150 * f(i / sr), 1.8);
      for (let i = 0; i < n; i++) x[i] *= (.3 + .9 * g(i / sr) ** 2) * 2.2;
      return x;
    });
  },
};

// ---------- I/O ----------
function readStereo(path) {
  const raw = readFileSync(path), x = new Float32Array(raw.buffer, raw.byteOffset, raw.byteLength / 4), n = x.length / 2;
  const L = new Float32Array(n), R = new Float32Array(n);
  for (let i = 0; i < n; i++) { L[i] = x[2 * i]; R[i] = x[2 * i + 1]; }
  return [L, R];
}
function writeStereo(path, L, R) {
  const out = new Float32Array(L.length * 2);
  for (let i = 0; i < L.length; i++) { out[2 * i] = L[i]; out[2 * i + 1] = R[i]; }
  check(out); writeFileSync(path, Buffer.from(out.buffer));
}
function check(x) { for (const v of x) if (!Number.isFinite(v)) throw Error('Engine produced a non-finite sample.'); }

const [cmd, ...args] = process.argv.slice(2);
if (cmd === 'fx') {
  const [specPath, inPath, outPath] = args, spec = JSON.parse(readFileSync(specPath, 'utf8'));
  let [L, R] = readStereo(inPath);
  for (const stage of spec.chain) [L, R] = await processStage(stage, spec.sr, L, R);
  writeStereo(outPath, L, R);
} else if (cmd === 'motion') {
  const [specPath, outPath] = args, out = await renderMotion(JSON.parse(readFileSync(specPath, 'utf8')));
  check(out); writeFileSync(outPath, Buffer.from(out.buffer));
} else if (cmd === 'env') {
  const [specPath, outPath] = args, s = JSON.parse(readFileSync(specPath, 'utf8'));
  const n = Math.round(s.seconds * s.sr), [L, R] = ENVGEN[s.kind](s, n, s.sr, s.seed ?? 1);
  writeStereo(outPath, L, R);
} else if (cmd === 'info') {
  console.log(JSON.stringify({drift: Object.keys(DRIFT_PRESETS), tame: TAME.presets.map(p => p.name), era: ERAS, motion: Object.keys(MOTION_PRESETS), motion_voices: ['drone', 'pad', 'lofi_keys']}, null, 1));
} else {
  console.error('usage: host.mjs fx SPEC IN OUT | motion SPEC OUT | env SPEC OUT | info'); process.exit(2);
}

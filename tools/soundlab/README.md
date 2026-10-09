# soundlab

One palette of every ambience and music tool, an idea scanner, and a seamless-loop renderer for Timeless Ambience.

## Commands

Run all commands from `/mnt/media/bob/soundlab`.

```bash
python3 soundlab.py palette                       # every tool, by role and status
python3 soundlab.py grooves jazz                  # the 117 Songygen drum grooves (optional filter)
python3 soundlab.py scan "drowned lighthouse at 3am, sea and fog"
python3 soundlab.py render recipes/<name>.json --seconds 60
python3 soundlab.py longform out/<name>/loop.wav --hours 2
```

- `scan` scores all tools in `palette.json` against the idea. It prints the best tools per role and writes a draft recipe to `recipes/`.
- `render` makes `out/<name>/loop.wav` (48 kHz, 24-bit), `loop.mp3` (the loop played twice, to check the seam), and `certificate.json`.
- `longform` repeats the loop to full length. The loop is seamless, so the repeats are seamless.

## How a loop is made

```
layers (native NumPy | Motion synth | Ambient Studio env | groove + kit)
  → level each layer to its RMS dB
  → per-layer FX (Tame / Drift / Era / native) + the recipe's "space"
  → bus: color (Era, tape wow) → master (Tame)
  → seamless loop: render 8 s lead-in + loop + 4 s tail, crossfade the tail over the start (equal power)
  → loudness to target (ambient -18 LUFS, lo-fi -16 LUFS, true peak -1.5 dB)
```

Lo-fi loops snap to whole 8-bar units, so the groove and the chord cycle meet at the loop point.

## Files

| Path | What |
| --- | --- |
| `palette.json` | Every tool: role, tags, status, licence. Add new tools here. |
| `gen/native.py` | Own NumPy layers (from `ambience/ambient.py` and `abracat/lofi.py`). |
| `gen/songy.py` | Motion voices, Ambient Studio environments, groove drums, FX calls. |
| `fx/host.mjs` | Node host for the Songygen WASM engines and environments. |
| `engines/` | `lock.json` (URL + SHA-256). The `drift`, `motion`, `era` and `tame` `.wasm` files download on first run and are not in git. |
| `data/` | Groove table and Tame presets extracted from songygen.com. |
| `kits/` | Drum kits, downloaded on first use, with licence and attribution. |

## Status values

- **ready:** renders here. Songygen tools are used with the owner's permission (confirmed 2026-10-09), monetized uploads included.
- **manual:** a person runs it (DroneMill production engine, Gemini Lyria, Acid 303).
- **reference:** listen only.

## Rules

- The engines must match `engines/lock.json`. If Songygen ships a new build, review it, then update the lock.
- The DRS studio kit is CC-BY-4.0. Put its credit in the video description. The other kits are CC0.
- The 8 GB RAM limit allows loops of about 7 minutes at most. Use 3–5 minute loops and `longform`.

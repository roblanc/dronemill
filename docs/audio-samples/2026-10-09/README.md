# Halloween audio experiments — Claude handoff

Four 30-second listening previews were created for Timeless Ambience / DroneMill.
The latest comparison is **Lanterns Beyond the Grave**, first using the installed
DroneMill procedural engine, then with Songygen effect processing.

For the new illustrated Halloween scenes, generation prompts and visual loop
prototype, start with the [rendering and audio handoff](../../halloween-assets/2026-10-09/README.md).

| Preview | Composition and rendering | Files |
| --- | --- | --- |
| Between Quiet Hours | Songygen's public rule-based Sketch engine evaluated locally; edited D-minor notes rendered with custom ambient synthesis | [MP3](between-quiet-hours.mp3), [MIDI](between-quiet-hours.mid), [notes](between-quiet-hours-notes.txt) |
| The House Keeps Humming | Original local Halloween composition; synthesized music-box tines, organ-style chords, choir and bass | [MP3](the-house-keeps-humming.mp3), [MIDI](the-house-keeps-humming.mid), [notes](the-house-keeps-humming-notes.txt) |
| Lanterns: DroneMill baseline | Actual server-side hybrid conductor and ambient layers: Lovecraft pad, formant choir, sparse Phrygian phrases, DSP harmonics, sub, quiet textures and convolution reverb | [MP3](lanterns-beyond-the-grave-dronemill.mp3), [recipe](halloween-dronemill-recipe.json), [provenance](halloween-dronemill-provenance.json) |
| Lanterns: Songygen FX | Re-rendered native DroneMill layers with per-note ADSR, processed by Songygen's actual public DSP classes locally in Node | [MP3](lanterns-beyond-the-grave-songy-fx.mp3), [processing recipe](lanterns-beyond-the-grave-songy-fx-recipe.json) |

## What changed in the latest version

The musical seed and harmony were preserved from the DroneMill baseline. Bell,
organ and string note envelopes were reshaped with explicit attack, decay,
sustain, hold and release controls. Slow LFOs modulate filter cutoff (2300–3700 Hz),
amplitude (13-second cycle), and stereo pan (17-second cycle). A separate master
ADSR gives a 2.5-second attack, 2-second decay, 0.86 sustain and 6-second release.

The chain uses these Songygen algorithms, rather than substitute FFmpeg effects:

1. **Contour EQ:** bass -1 dB, mid -2.5 dB at 900 Hz, treble -5 dB.
2. **Compressor:** -27 dB threshold, 1.65:1 ratio, 35 ms attack, 240 ms release,
   30% blend, no makeup gain.
3. **Orbit Phaser:** 0.055 Hz, depth 0.40, feedback 0.12, mix 0.16.
4. **Drift Chorus:** 0.11 Hz, depth 0.35, mix 0.26.
5. **Tape delay:** 650 ms, feedback 0.23, mix 0.17, ping-pong enabled.
6. **Dattorro-style plate reverb:** decay 0.76, damping 0.67, predelay 45 ms,
   mix 0.30.

The user referred to an EQ called "Tame". That separate name was not found in the
inspected public code; Contour EQ was used to tame harsh upper frequencies.
Songygen was used for DSP only in this latest version, not for music generation.
Neither Lanterns version used LatentScore, remote generation, or downloaded recordings.
No Songygen account or project was modified.

## Reproduce and continue

```bash
python3 -m pip install -r tools/audio-samples/requirements.txt
python3 tools/audio-samples/render.py --variant all
```

The tool includes the native engine snapshot needed to reproduce the server's
sound, since that version had not yet been committed on main. Its provenance and
source hashes are in `tools/audio-samples/native/source.json`. The public Songygen
effect source is SHA-256 pinned, fetched once, and cached locally. The source
implementation is not vendored into this repository.

WAV masters can be regenerated; MP3 previews and MIDI/recipe files are committed
here to keep the handoff small. The first two experiments are listening references;
the portable renderer covers the two latest Lanterns versions.

The baseline is seconds 30–60 of a 90-second native render. The FX version directly
renders that time range from the same musical seed, applies note ADSR, and replaces
the baseline hall return with the Songygen processing chain. They are comparable
variants, not a bit-identical before/after master-bus processing test.

The original latest FX WAV was checked at **30.000 seconds, 48 kHz stereo,
24-bit, -22.01 LUFS and -10.35 dBTP**, with a near-zero ending. Preview targets
do not change the channel's production mastering defaults.

Suggested next work for Claude: audition the two Lanterns previews, choose the
processing amount, and adapt the approved recipe to continuous long-form audio.
Do not loop this 30-second fade-in/fade-out preview as a finished two-hour track.

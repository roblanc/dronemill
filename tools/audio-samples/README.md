# Lanterns audio sample renderer

Render the 30-second DroneMill baseline and the version processed with Songygen's
public effect algorithms. Python 3.10+, NumPy, Node.js 18+, and FFmpeg/ffprobe are
required. FFmpeg needs `afir`, `anoisesrc`, `alimiter`, `loudnorm`, FLAC, and MP3 support.

From the repository root:

```bash
python3 -m pip install -r tools/audio-samples/requirements.txt
python3 tools/audio-samples/render.py --variant all
```

Outputs go into the ignored `tools/audio-samples/rendered/` directory. Each variant
produces a WAV, a 256 kbps MP3, and a validation JSON. Override this location with
`--output-dir`. Render one version with `--variant baseline` or `--variant songy-fx`.

The first FX render downloads the pinned public Songygen asset, checks its SHA-256,
and extracts its DSP module into an ignored cache. Later runs can work offline.
If that asset disappears or changes, do not silently switch implementations:
review a replacement, update `songy-source.json`, and compare a fresh render.
An already prepared module can be supplied with `--songy-dsp PATH`.

The native engine snapshot is included because the working server's conductor
and `ambient_layers.py` differ from the repository's main branch. The original
source hashes are in `native/source.json`. Only the conductor's temporary-directory
resolution was made portable. Production scripts, upload jobs, and channel
settings are not changed by this renderer.

Songygen source is fetched rather than vendored. This does not establish any
additional redistribution rights for that source. The processing recipe records
the precise parameters and provenance used for these previews.

The samples are review previews. Both target approximately -22 LUFS for comparison;
this does not change the production channel's mastering target. A 30-second sample
is not a seamless long-form loop. ADSR durations and phrase/chord timing need a
separate long-form recipe before a full upload.

See `docs/audio-samples/2026-10-09/README.md` for listening copies and the Claude handoff.

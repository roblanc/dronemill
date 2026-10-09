# Lantern keeper loop prototype

The existing 24-second native Python/OpenCV animation demonstrates layered
character and environmental motion. `preview-720p.mp4` is a silent 48-second
viewing copy showing two cycles. `drawing.png` is its frame-zero poster.
Background and transparent character/lantern PNGs are in `assets/`.

This prototype predates the simpler nighttime scene art direction. It is a
working motion reference; the new scene stills require their own layers and
character-specific geometry before they can use the same approach.

## Reproduce

Python 3.10+, FFmpeg and ffprobe are required. From the repository root:

```sh
python3 -m venv docs/halloween-assets/2026-10-09/loop-prototype/.venv
docs/halloween-assets/2026-10-09/loop-prototype/.venv/bin/pip install \
  -r docs/halloween-assets/2026-10-09/loop-prototype/requirements.txt
docs/halloween-assets/2026-10-09/loop-prototype/.venv/bin/python \
  docs/halloween-assets/2026-10-09/loop-prototype/atmosphere.py \
  --out docs/halloween-assets/2026-10-09/loop-prototype/rendered/atmosphere-1080p.mp4
```

`render.py` contains the base compositor: breathing, head tilt, blinks, lantern
swing, candlelight and soft background modulation. `atmosphere.py` adds drifting
clouds, mist ribbons, falling leaves and subtle moon shading. All motion shares
a 24-second cycle. `--width 1280` produces 720p; `--poster-only` writes only the
poster. Rendering writes `drawing.png` in this directory and a JSON report next
to the chosen MP4. FFmpeg refuses to overwrite an existing MP4.

The 1080p master is regenerated from code rather than committed alongside the
viewing copy. `validation.json` and `lanterns-beyond-the-grave-1080p.json` retain
the original 1080p checks: 576 frames at 24 fps, 24.000 seconds, silent H.264,
identical source poses across the cycle and an inspected encoded seam.
`generation.json` contains the original still-asset prompts and tool provenance.

## Finish with a full soundtrack

After generating a two-hour audio master and rendering the visual loop above:

```sh
python3 docs/halloween-assets/2026-10-09/loop-prototype/finish-two-hours.py \
  /absolute/path/to/two-hour-master.wav \
  --loop docs/halloween-assets/2026-10-09/loop-prototype/rendered/atmosphere-1080p.mp4 \
  --out docs/halloween-assets/2026-10-09/loop-prototype/rendered/two-hours.mp4
```

The helper requires a soundtrack at least as long as the requested duration
(default 7200 seconds), repeats the video, copies its stream, encodes 256 kbps AAC,
and verifies the result. A full soundtrack is supplied separately. The viewing
copy is silent and the helper does not synthesize audio. Neither this prototype
nor the new scene images have been wired into production render/upload jobs.

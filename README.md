# dronemill

Drone factory. Mass-produces 1-hour cosmic-horror ambient YouTube videos from a single audio source. Pitch-shifts, image overlays, AAC-muxes, and auto-uploads to YouTube.

Channel: [@timelessambience55](https://www.youtube.com/@timelessambience55)

## Stack
- `ffmpeg` (with librubberband)
- `yt-dlp` (optional: download source audio)
- `youtubeuploader` (YT auto-upload)
- bash

## Structure
```
audio/                raw mp3 source (gitignored)
images/queue/         drop new thumbnails here — picked oldest-first
images/used/          auto-archived after upload
output/               rendered mp4 (gitignored)
descriptions/         per-video YT descriptions
scripts/              pipeline
SETUP-YOUTUBE.md      Google Cloud OAuth (one-time)
PUSH-TO-GITHUB.md     git workflow
```

## Quickstart on a new machine

```bash
git clone https://github.com/<user>/dronemill.git
cd dronemill
brew install ffmpeg yt-dlp youtubeuploader rubberband

# populate
mkdir -p audio images/queue
# drop .mp3 in audio/, .png/.jpg in images/queue/

# YT auth (see SETUP-YOUTUBE.md)
mkdir -p ~/.youtubeuploader
# move client_secrets.json there

# run
cd scripts
./full-pipeline.sh ../audio/raw.mp3 "title here" ../descriptions/file.txt 0.93
```

## Workflows

### Image queue model
Drop multiple images in `images/queue/`. Pipeline picks the oldest (alphabetical) automatically. After successful upload, image moves to `images/used/`. You don't pass the image path — just audio + title.

### Render only (skip upload)
```bash
./scripts/render-only.sh ../audio/raw.mp3 "my title here" 0.93
```
→ output: `output/my-title-here.mp4`

### Full chain — scheduled (default)
Auto-schedules at next slot (default: 18:00 local / 15:00 UTC, 1 video/day cadence).
```bash
./scripts/full-pipeline.sh ../audio/raw.mp3 \
  "frozen 169 years | hms erebus deep ambient | dark arctic drone" \
  ../descriptions/frozen.txt 0.93
```
Each invocation advances scheduler by 1 day. State in `.schedule_state` (gitignored).

### Full chain — immediate publish
```bash
./scripts/full-pipeline.sh ../audio/raw.mp3 "title" descriptions/d.txt 0.93 now public
# or 'now unlisted' to keep private until manual review
```

### Reset scheduler
```bash
rm .schedule_state   # next call schedules for today/tomorrow at 18:00 local
```

### Custom schedule slot
```bash
./scripts/scheduler.sh 21 3   # 21:00 EEST = 18:00 UTC
```

### Generate original ambient (zero copyright)
```bash
./scripts/noise-gen.sh 3600 deep_void brown
```

### Download source from YT
```bash
./scripts/yt-grab.sh "https://youtube.com/watch?v=..." erebus
```

## Title-driven naming

Output filename = slugified title:
- title: `"frozen 169 years | hms erebus deep ambient | dark arctic drone"`
- file:  `output/frozen-169-years-hms-erebus-deep-ambient-dark-arctic-drone.mp4`

Slug rules: lowercase, non-alphanumerics → `-`, max 80 chars.

## Title pattern (channel branding)

```
[hook 3-5 words] | [main descriptor] | [tag/duration]
```

Examples:
- `frozen 169 years | hms erebus deep ambient | dark arctic drone`
- `signals from below | hms erebus abyssal ambient | 1 hour`
- `the ice remembers | franklin expedition ambient | dark drone`

Lowercase. No em dashes. Pipe `|` separator.

## Pitch values
- `0.85` — −2.7 semitones (deep doom)
- `0.93` — −1.2 semitones (default subtle)
- `1.07` — +1.2 semitones (alien high)

## Performance
- 1h source → 1h video: ~45s total on M4
- Pitch + AAC encode: ~40s
- Stream-loop mux: ~5s

## Security
**Never commit:**
- `client_secrets.json`
- `request.token`
- `.env`

`.gitignore` enforces. Always run `git status` before push.

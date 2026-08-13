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

### Maintain a rolling schedule

Check how many days remain between now and the last locally scheduled slot. The
default reports when runway falls below seven days and calculates how many items
are needed to restore a 30-day queue:

```bash
./scripts/rolling-batch-check.sh
```

The checker is dry-run by default. To let cron invoke production, configure a
bounded `DRONEMILL_BATCH_COMMAND` that reads `DRONEMILL_BATCH_COUNT`, then run
with `--run`. It uses a non-blocking lock to prevent overlapping batches:

```bash
DRONEMILL_BATCH_COMMAND='./scripts/batch-schedule.sh "$DRONEMILL_BATCH_COUNT"' \
  ./scripts/rolling-batch-check.sh 7 30 --run
```

Do not enable cron until the queue has enough reviewed images, audio recipes,
titles, descriptions, disk space, and YouTube quota. A daily check is sufficient;
the runway threshold, rather than the calendar month boundary, triggers refill.

### Run jobs after disconnecting

Use the systemd-backed job runner for renders or batches that must survive a
closed terminal, ended SSH session, exited OpenCode process, or powered-off
client laptop:

```bash
./scripts/job-runner.sh start greenhouse-render -- \
  ./scripts/greenhouse-audio.sh output/greenhouse.wav 7200

./scripts/job-runner.sh list
./scripts/job-runner.sh status greenhouse-render
./scripts/job-runner.sh logs greenhouse-render 100
./scripts/job-runner.sh stop greenhouse-render
```

The system `systemd` manager owns the process. Durable state and logs are stored
under `/var/lib/dronemill/jobs/`. Client disconnection does not stop the job.
A server shutdown or reboot does stop an active transient job; completed files,
status, and logs remain, but interrupted work must be restarted.

The detached runner executes a concrete command or batch prepared before
disconnecting. It does not keep the conversational LLM agent alive or make new
creative decisions after OpenCode exits. Define the target and approval policy
first, then start the resulting job and disconnect safely.

Successful creative combinations are recorded in `docs/creative-recipes.md` so
later batches can recombine proven visual, motion, audio, and mastering choices.

### Image handoff workflow

An image uploaded through CasaOS can start a complete production handoff. Ask
DroneMill to check the new image; it will locate and inspect the asset, assess
composition and motion options, propose a title and sound direction, render a
short review sample, and wait for approval before the long-form render and
YouTube upload. See `docs/image-handoff-workflow.md` for the review gates and
defaults.

### Generate original ambient (zero copyright)
```bash
./scripts/noise-gen.sh 3600 deep_void brown
```

### Generate title-conditioned ambient with LatentScore

LatentScore runs CPU-only in an isolated Docker image. The first run builds the
image and downloads the local retrieval model; later runs reuse both caches.

```bash
./scripts/latentscore-gen.sh \
  "isolated lighthouse in midnight ocean fog, cosmic dread" \
  audio/queue/lighthouse.wav 180
```

Arguments are prompt, output WAV, and duration in seconds. The script writes the
raw WAV, a JSON sidecar with provenance, and a stereo master at `-18 LUFS`.
LatentScore 0.1.8 does not expose deterministic seeding, so renders cannot be
recreated exactly. This is currently an experimental musical bed; layer original
environmental textures over it before using it for a full one-hour upload.

### Render a scene-aware comparison

Scene profiles in `profiles/` control both the environmental audio mix and visual
motion. The lighthouse profile adds procedural ocean, surf, wind, and sparse
foghorns to a musical bed, then renders the baseline and enhanced treatments side
by side for review.

```bash
./scripts/scene-audio.sh \
  profiles/lighthouse.json \
  audio/previews/lighthouse-latentscore-3min.mp3 \
  output/lighthouse-scene.wav 180

./scripts/scene-visual.sh \
  profiles/lighthouse.json \
  images/queue/111_lighthouse_fog.png \
  output/lighthouse-scene.wav \
  output/lighthouse-comparison.mp4 180
```

These first scene renderers support the lighthouse profile. Environmental layers
are generated locally and require no downloaded field recordings. Fog opacity,
drift speed, rain density/direction, wave strength/speed, and the feathered water
region are adjustable under `visual` in the profile JSON. If
`assets/youtube-overlays/fog-overlay.mp4` and `rain-overlay.mp4` exist, the
renderer uses those clips with adjustable playback speed; otherwise it falls back
to procedural fog and rain. Camera motion renders at double resolution before
downsampling and uses the profile's `fps` value to avoid low-frame-rate judder.
`camera_breathe_amount` and `camera_breathe_seconds` control a prolonged eased
inhale/exhale zoom; separate drift controls add only slow horizontal motion.

Render a long-form full-screen production by creating a reusable visual cycle and
looping it without re-encoding against long-form audio:

```bash
./scripts/scene-production.sh \
  profiles/lighthouse.json images/queue/111_lighthouse_fog.png \
  output/lighthouse-2h.wav output/lighthouse-2h.mp4 7200 120
```

### Midjourney liminal animation workflow

This workflow starts with a Midjourney still image, uses Midjourney's manual
animation feature, and exports the result as MP4. Keep the downloaded MP4 under
`assets/source-videos/`; source media there is intentionally excluded from Git.

The prompt used for the first glass-landscape sample was:

```text
liminal atmosphere outside a grass field with hills and trees made of sparkling glass, raw, interesting perspective, minimalistic, abstract
```

Suggested process:

1. Generate and select the still image in Midjourney.
2. Use manual animation, keeping motion restrained and the camera stable enough
   to reverse naturally.
3. Export the animation as MP4 and place it in `assets/source-videos/`.
4. Turn it into a forward/reverse loop. The script removes duplicated endpoint
   frames so the animation does not pause at either reversal:

```bash
./scripts/pingpong-loop.sh \
  assets/source-videos/liminal-glass-landscape.mp4 \
  output/liminal-glass-pingpong.mp4 31
```

5. Generate matching procedural ambience, then mux it with the animation:

```bash
./scripts/liminal-glass-audio.sh output/liminal-glass-audio.wav 32

ffmpeg -y -i output/liminal-glass-pingpong.mp4 \
  -i output/liminal-glass-audio.wav -map 0:v:0 -map 1:a:0 \
  -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart \
  output/liminal-glass-soundtracked.mp4
```

The sound design treats this as bright pastoral liminality rather than indoor
Backrooms horror. It uses silence, a quiet suspended major/Lydian harmony, and a
sparse incomplete melody without a continuous noise bed, synthetic wind, birds,
an ominous low drone, or constant glass effects. The 48 kHz, `-24 LUFS` audio is
generated locally without copyrighted recordings.
See `docs/liminal-sound-design.md` for the research-backed sound principles and
references used by this workflow.

Future browser-assisted Midjourney generation may automate the image and manual
animation steps if an authenticated browser session and browser-control tooling
are available at that time. Browser access is not assumed or stored by this
repository; confirm the prompt, account access, and generation costs before an
automated run.

### Publish a review sample to Jellyfin

Combine an image and audio preview into a lightweight 720p review video. Jellyfin
shows it under `Videos / DroneMill Previews` with local title and poster metadata.

```bash
./scripts/publish-jellyfin-preview.sh \
  images/queue/111_lighthouse_fog.png \
  audio/previews/lighthouse-latentscore-3min.mp3 \
  "lighthouse through the midnight fog"
```

Publish an animated review render without re-encoding it:

```bash
./scripts/publish-rendered-preview.sh \
  output/lighthouse-comparison.mp4 \
  "lighthouse scene-aware comparison"
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

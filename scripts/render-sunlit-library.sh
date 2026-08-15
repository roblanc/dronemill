#!/bin/bash
# Sunlit Library Living Scene Renderer
# Combines:
# 1. Floating golden dust motes with soft screen blend
# 2. Volumetric sunlight breathing
# 3. Slow eased camera drift and subpixel breathing

set -euo pipefail

IMAGE="${1:-}"
AUDIO="${2:-}"
OUTPUT="${3:-}"
DURATION="${4:-60}"
FPS=24

ROOT="/root/dronemill"
DUST_OVERLAY="$ROOT/assets/overlays/dust_motes_loop.mp4"

mkdir -p "$(dirname "$OUTPUT")"
WORK="${TMPDIR:-/tmp}/library_render_$$"
mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT

LOOP_CLIP="$WORK/loop60.mp4"

echo ">> [1/2] Rendering 60s sunlit library scene with golden dust motes..."

ffmpeg -y -nostdin \
  -loop 1 -framerate "$FPS" -t 60 -i "$IMAGE" \
  -stream_loop -1 -i "$DUST_OVERLAY" \
  -filter_complex "
    [0:v]scale=3200:1800:force_original_aspect_ratio=increase,crop=3200:1800,zoompan=z='1.02+0.016*(0.5-0.5*cos(2*PI*on/(60*${FPS})))':x='iw/2-(iw/zoom/2)+45*sin(2*PI*on/(60*${FPS}))':y='ih/2-(ih/zoom/2)+12*cos(2*PI*on/(60*${FPS}))':d=1:s=1920x1080:fps=${FPS},format=gbrp[base];
    [1:v]scale=1920:1080:flags=lanczos,curves=all='0/0 0.20/0 0.55/0.30 0.85/0.75 1/0.95',format=gbrp[dust_soft];
    [base][dust_soft]blend=all_mode=screen:all_opacity=0.35[merged];
    [merged]eq=contrast='1.02+0.008*sin(2*PI*n/(32*${FPS}))':brightness='-0.004+0.007*sin(2*PI*n/(22*${FPS}))',vignette=angle=0.32,noise=alls=0.6:allf=t+u,format=yuv420p[vout]
  " -map "[vout]" \
  -c:v libx264 -preset veryfast -crf 19 -r "$FPS" -t 60 "$LOOP_CLIP"

echo ">> [2/2] Muxing with audio to $OUTPUT..."
LOOPS=$((DURATION / 60 + 1))

ffmpeg -y -stream_loop "$LOOPS" -i "$LOOP_CLIP" -i "$AUDIO" \
  -c:v copy -c:a aac -b:a 256k -ar 48000 -t "$DURATION" -movflags +faststart "$OUTPUT"

echo "Done -> $OUTPUT"

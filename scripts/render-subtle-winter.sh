#!/bin/bash
# Subtle Winter Living Scene Renderer

set -euo pipefail

IMAGE="${1:-}"
AUDIO="${2:-}"
OUTPUT="${3:-}"
DURATION="${4:-60}"
FPS=24

ROOT="/root/dronemill"
SNOW_OVERLAY="$ROOT/assets/overlays/snow_blizzard_loop.mp4"

mkdir -p "$(dirname "$OUTPUT")"
WORK="${TMPDIR:-/tmp}/subtle_render_$$"
mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT

LOOP_CLIP="$WORK/loop60.mp4"

echo ">> [1/2] Rendering 60s subtle living winter scene..."

ffmpeg -y -nostdin \
  -loop 1 -framerate "$FPS" -t 60 -i "$IMAGE" \
  -stream_loop -1 -i "$SNOW_OVERLAY" \
  -filter_complex "
    [0:v]scale=3200:1800:force_original_aspect_ratio=increase,crop=3200:1800,zoompan=z='1.02+0.018*(0.5-0.5*cos(2*PI*on/(60*${FPS})))':x='iw/2-(iw/zoom/2)+50*sin(2*PI*on/(60*${FPS}))':y='ih/2-(ih/zoom/2)+15*cos(2*PI*on/(60*${FPS}))':d=1:s=1920x1080:fps=${FPS},format=gbrp[base];
    [1:v]scale=1920:1080:flags=lanczos,curves=all='0/0 0.15/0 0.50/0.25 0.85/0.70 1/0.90',format=gbrp[snow_soft];
    [base][snow_soft]blend=all_mode=screen:all_opacity=0.28[merged];
    [merged]eq=contrast='1.015+0.006*sin(2*PI*n/(28*${FPS}))':brightness='-0.005+0.005*sin(2*PI*n/(18*${FPS}))',vignette=angle=0.34,noise=alls=0.8:allf=t+u,format=yuv420p[vout]
  " -map "[vout]" \
  -c:v libx264 -preset veryfast -crf 19 -r "$FPS" -t 60 "$LOOP_CLIP"

echo ">> [2/2] Muxing with audio to $OUTPUT..."
LOOPS=$((DURATION / 60 + 1))

ffmpeg -y -stream_loop "$LOOPS" -i "$LOOP_CLIP" -i "$AUDIO" \
  -c:v copy -c:a aac -b:a 256k -ar 48000 -t "$DURATION" -movflags +faststart "$OUTPUT"

echo "Done -> $OUTPUT"

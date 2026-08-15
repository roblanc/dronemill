#!/bin/bash
# Contextual Scene Renderer
# Selects and blends the appropriate physical overlay based on scene type:
# - snow/winter/blizzard -> snow_blizzard_loop.mp4
# - dust/sun/library/atrium -> dust_motes_loop.mp4
# - rain/storm -> rain-overlay.mp4
# - fog/mist/ocean -> fog-overlay.mp4

set -euo pipefail

IMAGE="${1:-}"
AUDIO="${2:-}"
SCENE_TYPE="${3:-snow}"
OUTPUT="${4:-/tmp/contextual_output.mp4}"
DURATION="${5:-60}"
FPS=24

ROOT="/root/dronemill"
OVERLAYS_DIR="$ROOT/assets/overlays"
YT_OVERLAYS_DIR="$ROOT/assets/youtube-overlays"

case "$SCENE_TYPE" in
  snow*|winter*|blizzard*|arctic*|ice*)
    OVERLAY="$OVERLAYS_DIR/snow_blizzard_loop.mp4"
    OVERLAY_OPACITY="0.85"
    BLEND_MODE="screen"
    ;;
  dust*|sun*|library*|atrium*|golden*|room*)
    OVERLAY="$OVERLAYS_DIR/dust_motes_loop.mp4"
    OVERLAY_OPACITY="0.65"
    BLEND_MODE="screen"
    ;;
  rain*|storm*|greenhouse*)
    OVERLAY="$YT_OVERLAYS_DIR/rain-overlay.mp4"
    OVERLAY_OPACITY="0.45"
    BLEND_MODE="screen"
    ;;
  fog*|mist*|ocean*|coast*)
    OVERLAY="$YT_OVERLAYS_DIR/fog-overlay.mp4"
    OVERLAY_OPACITY="0.30"
    BLEND_MODE="screen"
    ;;
  *)
    OVERLAY="$OVERLAYS_DIR/snow_blizzard_loop.mp4"
    OVERLAY_OPACITY="0.80"
    BLEND_MODE="screen"
    ;;
esac

if [ ! -f "$OVERLAY" ]; then
  echo "WARN: overlay $OVERLAY not found, using procedural fallback"
fi

mkdir -p "$(dirname "$OUTPUT")"
WORK="${TMPDIR:-/tmp}/context_render_$$"
mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT

LOOP_CLIP="$WORK/loop60.mp4"

echo ">> [1/2] Rendering 60s contextual scene: type=$SCENE_TYPE, overlay=$(basename "$OVERLAY")..."

ffmpeg -y -nostdin \
  -loop 1 -framerate "$FPS" -t 60 -i "$IMAGE" \
  -stream_loop -1 -i "$OVERLAY" \
  -filter_complex "
    [0:v]scale=3200:1800:force_original_aspect_ratio=increase,crop=3200:1800,
      zoompan=z='1.03+0.025*(0.5-0.5*cos(2*PI*on/(60*${FPS})))':x='iw/2-(iw/zoom/2)+70*sin(2*PI*on/(60*${FPS}))':y='ih/2-(ih/zoom/2)+20*cos(2*PI*on/(60*${FPS}))':d=1:s=1920x1080:fps=${FPS},
      format=gbrp[base];
    [1:v]scale=1920:1080:flags=lanczos,format=gbrp[fx];
    [base][fx]blend=all_mode=${BLEND_MODE}:all_opacity=${OVERLAY_OPACITY}[merged];
    [merged]eq=contrast='1.02+0.008*sin(2*PI*n/(30*${FPS}))':brightness='-0.008+0.006*sin(2*PI*n/(20*${FPS}))':eval=frame,
      vignette=angle=0.36,
      noise=alls=1.2:allf=t+u,
      format=yuv420p[vout]
  " -map "[vout]" \
  -c:v libx264 -preset veryfast -crf 20 -r "$FPS" -t 60 "$LOOP_CLIP"

echo ">> [2/2] Muxing with audio to $OUTPUT..."
LOOPS=$((DURATION / 60 + 1))

ffmpeg -y -stream_loop "$LOOPS" -i "$LOOP_CLIP" -i "$AUDIO" \
  -c:v copy -c:a aac -b:a 256k -ar 48000 -t "$DURATION" -movflags +faststart "$OUTPUT"

echo "Done -> $OUTPUT"

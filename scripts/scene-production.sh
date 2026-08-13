#!/bin/bash
# Render a full-screen scene master, then loop it against long-form audio.
# Usage: ./scripts/scene-production.sh <profile.json> <image> <audio> <output> [duration=7200] [visual_cycle=120]

set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
PROFILE="${1:-}"
IMAGE="${2:-}"
AUDIO="${3:-}"
OUTPUT="${4:-}"
DURATION="${5:-7200}"
CYCLE="${6:-120}"
LOOP_FADE=4
RENDER_CYCLE=$((CYCLE + LOOP_FADE))

if [ ! -f "$PROFILE" ] || [ ! -f "$IMAGE" ] || [ ! -f "$AUDIO" ] || [ -z "$OUTPUT" ]; then
  echo "Usage: $0 <profile.json> <image> <audio> <output> [duration=7200] [visual_cycle=120]" >&2
  exit 1
fi

eval "$(python3 "$DIR/scene-profile.py" "$PROFILE")"
if [ "$ID" != "lighthouse" ]; then
  echo "ERROR: unsupported production profile: $ID" >&2
  exit 1
fi

FOG_OVERLAY="$ROOT/assets/youtube-overlays/fog-overlay.mp4"
RAIN_OVERLAY="$ROOT/assets/youtube-overlays/rain-overlay.mp4"
if [ ! -f "$FOG_OVERLAY" ] || [ ! -f "$RAIN_OVERLAY" ]; then
  echo "ERROR: production render requires fog-overlay.mp4 and rain-overlay.mp4" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT")"
MASTER="${OUTPUT%.mp4}.visual-master.mp4"
CYCLE_FRAMES=$((CYCLE * VISUAL_FPS))

if [ ! -f "$MASTER" ]; then
  echo "Rendering ${CYCLE}s full-screen visual master at ${VISUAL_FPS} fps"
  ffmpeg -y -nostdin \
    -loop 1 -framerate "$VISUAL_FPS" -t "$RENDER_CYCLE" -i "$IMAGE" \
    -stream_loop -1 -i "$FOG_OVERLAY" \
    -stream_loop -1 -i "$RAIN_OVERLAY" \
    -f lavfi -t "$RENDER_CYCLE" -i "perlin=s=1280x720:r=${VISUAL_FPS}:octaves=3:persistence=0.58:xscale=${VISUAL_WAVE_SCALE}:yscale=0.22:tscale=0.11:random_mode=seed:seed=73" \
    -filter_complex "
      [0:v]scale=2560:1440:force_original_aspect_ratio=increase,crop=2560:1440,
        zoompan=z='${VISUAL_CAMERA_BASE_ZOOM}+${VISUAL_CAMERA_BREATHE_AMOUNT}*(0.5-0.5*cos(2*PI*on/(${VISUAL_CAMERA_BREATHE_SECONDS}*${VISUAL_FPS})))':x='iw/2-(iw/zoom/2)+${VISUAL_CAMERA_DRIFT_PIXELS}*sin(2*PI*on/${CYCLE_FRAMES})':y='ih/2-(ih/zoom/2)':d=1:s=2560x1440:fps=${VISUAL_FPS},
        scale=1280:720:flags=lanczos,eq=contrast='1.035+0.008*sin(2*PI*n/(35*${VISUAL_FPS}))':brightness='-0.018+${VISUAL_LIGHT_BREATHE}*sin(2*PI*n/(18*${VISUAL_FPS}))',vignette=angle=0.42,format=gbrp[base];
      [1:v]setpts=PTS/${VISUAL_FOG_PLAYBACK_SPEED},fps=${VISUAL_FPS},scale=1400:720:force_original_aspect_ratio=increase,crop=1280:720:x='60+35*sin(2*PI*t/17)',eq=saturation=0:contrast=1.25:brightness=-0.02,curves=all='0/0 0.18/0 0.42/0.20 0.72/0.68 1/0.92',format=gbrp[fog];
      [2:v]setpts=PTS/${VISUAL_RAIN_PLAYBACK_SPEED},fps=${VISUAL_FPS},scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,eq=saturation=0:contrast=1.35:brightness=0.015,curves=all='0/0 0.08/0 0.28/0.16 0.62/0.72 1/1',format=gbrp[rain];
      [3:v]scroll=horizontal=${VISUAL_WAVE_SPEED},edgedetect=mode=colormix:high=0.18:low=0.04,dblur=angle=0:radius=5,curves=all='0/0 0.55/0 0.72/0.18 1/0.62',format=gbrp[waves];
      color=s=1280x720:r=${VISUAL_FPS}:c=black,geq=lum='255*gte(X,$((VISUAL_WATER_LEFT * 2)))*gte(Y,${VISUAL_WATER_HORIZON})*lte(Y,${VISUAL_WATER_BOTTOM})':cb=128:cr=128,gblur=sigma=${VISUAL_WATER_FEATHER},format=gbrp[watermask];
      [base][fog]blend=all_mode=screen:all_opacity=${VISUAL_FOG_OPACITY},split=2[fogged][wavebase];
      [wavebase][waves]blend=all_mode=screen:all_opacity=${VISUAL_WAVE_OPACITY}[waterfx];
      [fogged][waterfx][watermask]maskedmerge[withwaves];
      [withwaves][rain]blend=all_mode=screen:all_opacity=${VISUAL_RAIN_OPACITY},noise=alls=1.5:allf=t+u,format=yuv420p,split=2[scene][opening];
      [scene]trim=duration=${CYCLE},setpts=PTS-STARTPTS[main];
      [opening]trim=duration=${LOOP_FADE},setpts=PTS-STARTPTS[head];
      [main][head]xfade=transition=fade:duration=${LOOP_FADE}:offset=$((CYCLE - LOOP_FADE)),format=yuv420p[vout]
    " \
    -map "[vout]" -an -c:v libx264 -preset veryfast -crf 22 -r "$VISUAL_FPS" \
    -t "$CYCLE" -movflags +faststart "$MASTER"
fi

echo "Muxing ${DURATION}s production video"
ffmpeg -y -nostdin -stream_loop -1 -i "$MASTER" -i "$AUDIO" \
  -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k -ar 48000 -ac 2 \
  -t "$DURATION" -movflags +faststart "$OUTPUT"

echo "Done -> $OUTPUT"

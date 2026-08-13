#!/bin/bash
# Render a scene-aware comparison: baseline motion on left, enhanced profile on right.
# Usage: ./scripts/scene-visual.sh <profile.json> <image> <audio> <output> [duration=180]

set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
PROFILE="${1:-}"
IMAGE="${2:-}"
AUDIO="${3:-}"
OUTPUT="${4:-}"
DURATION="${5:-180}"

if [ ! -f "$PROFILE" ] || [ ! -f "$IMAGE" ] || [ ! -f "$AUDIO" ] || [ -z "$OUTPUT" ]; then
  echo "Usage: $0 <profile.json> <image> <audio> <output> [duration=180]" >&2
  exit 1
fi

eval "$(python3 "$DIR/scene-profile.py" "$PROFILE")"
if [ "$ID" != "lighthouse" ]; then
  echo "ERROR: unsupported visual profile: $ID" >&2
  exit 1
fi

FOG="$ROOT/assets/fog_loop.mp4"
if [ ! -f "$FOG" ]; then
  echo "ERROR: missing $FOG; run cosmic.sh once to generate it" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT")"
FRAMES=$((DURATION * 12))

ffmpeg -y -nostdin \
  -loop 1 -framerate 12 -t "$DURATION" -i "$IMAGE" \
  -stream_loop -1 -i "$FOG" \
  -f lavfi -t "$DURATION" -i "life=s=320x180:r=12:ratio=0.018:death_color=black:life_color=white:mold=2" \
  -i "$AUDIO" \
  -filter_complex "
    [0:v]split=2[leftsrc][rightsrc];
    [leftsrc]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,
      zoompan=z='1.02+0.018*on/${FRAMES}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=640x720:fps=12,
      eq=contrast=1.01:brightness=-0.01,vignette=angle=0.38[left];
    [rightsrc]scale=2560:1440:force_original_aspect_ratio=increase,crop=2560:1440,
      zoompan=z='1.04+${VISUAL_CAMERA_ZOOM}*on/${FRAMES}':x='iw/2-(iw/zoom/2)+34*sin(2*PI*on/${FRAMES})':y='ih/2-(ih/zoom/2)+18*cos(2*PI*on/${FRAMES})':d=1:s=640x720:fps=12,
      eq=contrast='1.035+0.008*sin(2*PI*n/420)':brightness='-0.018+${VISUAL_LIGHT_BREATHE}*sin(2*PI*n/216)',vignette=angle=0.42[rightbase];
    [1:v]scale=640:720,format=yuv420p,eq=brightness=-0.08[fog];
    [2:v]scale=640:720,scroll=horizontal=-0.018:vertical=0.11,tmix=frames=5:weights='1 1 1 1 1',format=yuv420p[rain];
    [rightbase][fog]blend=all_mode=screen:all_opacity=${VISUAL_FOG_OPACITY}[fogged];
    [fogged][rain]blend=all_mode=screen:all_opacity=${VISUAL_RAIN_OPACITY},noise=alls=2:allf=t+u[right];
    [left][right]hstack=inputs=2[stack];
    [stack]drawbox=x=637:y=0:w=6:h=720:color=white@0.18:t=fill,
      drawtext=text='CURRENT':x=24:y=24:fontsize=24:fontcolor=white@0.8:box=1:boxcolor=black@0.45:boxborderw=8,
      drawtext=text='SCENE-AWARE':x=664:y=24:fontsize=24:fontcolor=white@0.8:box=1:boxcolor=black@0.45:boxborderw=8,
      format=yuv420p[vout]
  " \
  -map "[vout]" -map 3:a:0 \
  -c:v libx264 -preset veryfast -crf 24 -r 12 \
  -c:a aac -b:a 192k -ar 48000 -ac 2 -t "$DURATION" -movflags +faststart "$OUTPUT"

echo "Done -> $OUTPUT"

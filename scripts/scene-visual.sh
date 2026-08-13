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

mkdir -p "$(dirname "$OUTPUT")"
FRAMES=$((DURATION * VISUAL_FPS))
FOG_OVERLAY="$ROOT/assets/youtube-overlays/fog-overlay.mp4"
RAIN_OVERLAY="$ROOT/assets/youtube-overlays/rain-overlay.mp4"

if [ -f "$FOG_OVERLAY" ] && [ -f "$RAIN_OVERLAY" ]; then
  FOG_INPUT=(-stream_loop -1 -i "$FOG_OVERLAY")
  RAIN_INPUT=(-stream_loop -1 -i "$RAIN_OVERLAY")
  FOG_FILTER="[1:v]setpts=PTS/${VISUAL_FOG_PLAYBACK_SPEED},fps=${VISUAL_FPS},scale=760:720:force_original_aspect_ratio=increase,crop=640:720:x='60+35*sin(2*PI*t/17)',eq=saturation=0:contrast=1.25:brightness=-0.02,curves=all='0/0 0.18/0 0.42/0.20 0.72/0.68 1/0.92',format=gbrp[fog]"
  RAIN_FILTER="[2:v]setpts=PTS/${VISUAL_RAIN_PLAYBACK_SPEED},fps=${VISUAL_FPS},scale=640:720:force_original_aspect_ratio=increase,crop=640:720,eq=saturation=0:contrast=1.35:brightness=0.015,curves=all='0/0 0.08/0 0.28/0.16 0.62/0.72 1/1',format=gbrp[rain]"
  echo "Using external fog and rain overlays"
else
  FOG_INPUT=(-f lavfi -t "$DURATION" -i "perlin=s=640x720:r=${VISUAL_FPS}:octaves=5:persistence=0.52:xscale=${VISUAL_FOG_SCALE}:yscale=0.007:tscale=0.025:random_mode=seed:seed=41")
  RAIN_INPUT=(-f lavfi -t "$DURATION" -i "nullsrc=s=640x720:r=${VISUAL_FPS}")
  FOG_FILTER="[1:v]scroll=horizontal=${VISUAL_FOG_SPEED},gblur=sigma=22,curves=all='0/0 0.38/0 0.56/0.35 0.75/0.72 1/0.88',format=gbrp[fog]"
  RAIN_FILTER="[2:v]geq=lum='if(gt(random(1),${VISUAL_RAIN_DENSITY}),255,0)':cb=128:cr=128,dblur=angle=${VISUAL_RAIN_ANGLE}:radius=${VISUAL_RAIN_LENGTH},tmix=frames=3:weights='1 0.55 0.25',format=gbrp[rain]"
  echo "Using procedural fog and rain overlays"
fi

ffmpeg -y -nostdin \
  -loop 1 -framerate "$VISUAL_FPS" -t "$DURATION" -i "$IMAGE" \
  "${FOG_INPUT[@]}" \
  "${RAIN_INPUT[@]}" \
  -f lavfi -t "$DURATION" -i "perlin=s=640x720:r=${VISUAL_FPS}:octaves=3:persistence=0.58:xscale=${VISUAL_WAVE_SCALE}:yscale=0.22:tscale=0.11:random_mode=seed:seed=73" \
  -i "$AUDIO" \
  -filter_complex "
    [0:v]split=2[leftsrc][rightsrc];
    [leftsrc]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,
      zoompan=z='1.02+0.018*on/${FRAMES}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1280x1440:fps=${VISUAL_FPS},
      scale=640:720:flags=lanczos,eq=contrast=1.01:brightness=-0.01,vignette=angle=0.38[left];
    [rightsrc]scale=2560:1440:force_original_aspect_ratio=increase,crop=2560:1440,
      zoompan=z='1.04+${VISUAL_CAMERA_ZOOM}*on/${FRAMES}':x='iw/2-(iw/zoom/2)+34*sin(2*PI*on/${FRAMES})':y='ih/2-(ih/zoom/2)+18*cos(2*PI*on/${FRAMES})':d=1:s=1280x1440:fps=${VISUAL_FPS},
      scale=640:720:flags=lanczos,eq=contrast='1.035+0.008*sin(2*PI*n/(35*${VISUAL_FPS}))':brightness='-0.018+${VISUAL_LIGHT_BREATHE}*sin(2*PI*n/(18*${VISUAL_FPS}))',vignette=angle=0.42,format=gbrp[rightbase];
    ${FOG_FILTER};
    ${RAIN_FILTER};
    [3:v]scroll=horizontal=${VISUAL_WAVE_SPEED},edgedetect=mode=colormix:high=0.18:low=0.04,
      dblur=angle=0:radius=5,curves=all='0/0 0.55/0 0.72/0.18 1/0.62',format=gbrp[waves];
    color=s=640x720:r=${VISUAL_FPS}:c=black,geq=lum='255*gte(X,${VISUAL_WATER_LEFT})*gte(Y,${VISUAL_WATER_HORIZON})*lte(Y,${VISUAL_WATER_BOTTOM})':cb=128:cr=128,
      gblur=sigma=${VISUAL_WATER_FEATHER},format=gbrp[watermask];
    [rightbase][fog]blend=all_mode=screen:all_opacity=${VISUAL_FOG_OPACITY},split=2[fogged][wavebase];
    [wavebase][waves]blend=all_mode=screen:all_opacity=${VISUAL_WAVE_OPACITY}[waterfx];
    [fogged][waterfx][watermask]maskedmerge[withwaves];
    [withwaves][rain]blend=all_mode=screen:all_opacity=${VISUAL_RAIN_OPACITY},noise=alls=1.5:allf=t+u[right];
    [left][right]hstack=inputs=2[stack];
    [stack]drawbox=x=637:y=0:w=6:h=720:color=white@0.18:t=fill,
      drawtext=text='CURRENT':x=24:y=24:fontsize=24:fontcolor=white@0.8:box=1:boxcolor=black@0.45:boxborderw=8,
      drawtext=text='SCENE-AWARE':x=664:y=24:fontsize=24:fontcolor=white@0.8:box=1:boxcolor=black@0.45:boxborderw=8,
      format=yuv420p[vout]
  " \
  -map "[vout]" -map 4:a:0 \
  -c:v libx264 -preset veryfast -crf 24 -r "$VISUAL_FPS" \
  -c:a aac -b:a 192k -ar 48000 -ac 2 -t "$DURATION" -movflags +faststart "$OUTPUT"

echo "Done -> $OUTPUT"

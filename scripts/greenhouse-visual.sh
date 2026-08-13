#!/bin/bash
# Animate a greenhouse still with localized, physically motivated movement.
# Usage: ./scripts/greenhouse-visual.sh <image> <audio> <output> [duration=90]

set -euo pipefail

IMAGE="${1:-}"
AUDIO="${2:-}"
OUTPUT="${3:-}"
DURATION="${4:-90}"
FPS=12

if [ ! -f "$IMAGE" ] || [ ! -f "$AUDIO" ] || [ -z "$OUTPUT" ]; then
  echo "Usage: $0 <image> <audio> <output> [duration=90]" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT")"

ffmpeg -y -nostdin \
  -loop 1 -framerate "$FPS" -t "$DURATION" -i "$IMAGE" \
  -f lavfi -t "$DURATION" -i "perlin=s=320x180:r=${FPS}:octaves=3:persistence=0.52:xscale=0.018:yscale=0.032:tscale=0.018:random_mode=seed:seed=117" \
  -f lavfi -t "$DURATION" -i "perlin=s=320x180:r=${FPS}:octaves=3:persistence=0.58:xscale=0.010:yscale=0.045:tscale=0.028:random_mode=seed:seed=211" \
  -i "$AUDIO" \
  -filter_complex "
    [0:v]scale=960:540:flags=lanczos,format=gbrp,split=3[base][plantsrc][floorsrc];
    [1:v]scale=960:540:flags=bilinear,format=gray,split=2[plantx][planty];
    [2:v]scale=960:540:flags=bilinear,format=gray[floortex];
    [plantsrc][plantx][planty]displace=edge=smear,eq=brightness='0.003*sin(2*PI*t/19)':eval=frame[plantmove];
    color=s=960x540:r=${FPS}:c=black,format=gray,
      geq=lum='255*max(0,min(1,(abs(X-480)-140)/130))*max(0,min(1,(Y-135)/160))',gblur=sigma=18[plantmask];
    [base][plantmove][plantmask]maskedmerge[withplants];
    [floorsrc][floortex]blend=all_mode=screen:all_opacity=0.025,
      eq=brightness='0.004+0.005*sin(2*PI*t/23)':contrast=1.01:eval=frame[floormove];
    color=s=960x540:r=${FPS}:c=black,format=gray,
      geq=lum='255*max(0,min(1,(Y-320)/100))*max(0,min(1,(235-abs(X-480))/95))',gblur=sigma=14[floormask];
    [withplants][floormove][floormask]maskedmerge[withfloor];
    color=s=960x540:r=${FPS}:c=0xffa7c4,format=gbrp,
      fade=t=in:st=0:d=${DURATION}:alpha=1[light];
    [withfloor][light]blend=all_mode=screen:all_opacity=0.035,
      eq=brightness='-0.012+0.010*t/${DURATION}':saturation='0.98+0.025*t/${DURATION}':eval=frame,
      vignette=angle=0.36,noise=alls=0.5:allf=t+u,
      scale=1280:720:flags=lanczos,fps=24,format=yuv420p[vout]
  " \
  -map "[vout]" -map 3:a:0 -t "$DURATION" \
  -c:v libx264 -preset veryfast -crf 20 -r 24 \
  -c:a aac -b:a 192k -ar 48000 -ac 2 -movflags +faststart "$OUTPUT"

echo "Done -> $OUTPUT"

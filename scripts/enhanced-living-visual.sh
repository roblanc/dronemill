#!/bin/bash
# Enhanced Living Scene Renderer

set -euo pipefail

IMAGE="${1:-}"
AUDIO="${2:-}"
OUTPUT="${3:-}"
DURATION="${4:-60}"
FPS=24

if [ -z "$IMAGE" ] || [ -z "$AUDIO" ] || [ -z "$OUTPUT" ]; then
  echo "Usage: $0 <image> <audio> <output.mp4> [duration=60]" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT")"
WORK="${TMPDIR:-/tmp}/living_render_$$"
mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT

LOOP_CLIP="$WORK/loop60.mp4"

echo ">> [1/2] Rendering 60s enhanced living scene..."

ffmpeg -y -nostdin \
  -loop 1 -framerate "$FPS" -t 60 -i "$IMAGE" \
  -f lavfi -t 60 -i "perlin=s=960x540:r=${FPS}:octaves=4:persistence=0.55:xscale=0.012:yscale=0.035:tscale=0.025:random_mode=seed:seed=9102" \
  -f lavfi -t 60 -i "perlin=s=960x540:r=${FPS}:octaves=5:persistence=0.50:xscale=0.008:yscale=0.006:tscale=0.018:random_mode=seed:seed=4405" \
  -f lavfi -t 60 -i "nullsrc=s=1920x1080:r=${FPS}" \
  -filter_complex "
    [0:v]scale=3200:1800:force_original_aspect_ratio=increase,crop=3200:1800,zoompan=z='1.03+0.025*(0.5-0.5*cos(2*PI*on/(60*${FPS})))':x='iw/2-(iw/zoom/2)+80*sin(2*PI*on/(60*${FPS}))':y='ih/2-(ih/zoom/2)+25*cos(2*PI*on/(60*${FPS}))':d=1:s=1920x1080:fps=${FPS},format=gbrp[base];
    [base]split=2[b_still][b_warp];
    [1:v]scale=1920:1080:flags=lanczos,format=gray,split=2[dx][dy];
    [b_warp][dx][dy]displace=edge=smear[warped];
    color=s=1920x1080:r=${FPS}:c=black,geq=lum='255*max(0,min(1,(Y-520)/200))':cb=128:cr=128,gblur=sigma=18,format=gray[watermask];
    [b_still][warped][watermask]maskedmerge[with_water];
    [2:v]scroll=horizontal=0.4:vertical=0.1,scale=1920:1080:flags=lanczos,gblur=sigma=26,curves=all='0/0 0.35/0 0.58/0.28 0.80/0.65 1/0.85',format=gbrp[fog];
    [with_water][fog]blend=all_mode=screen:all_opacity=0.075[with_fog];
    [3:v]geq=lum='if(gt(random(1),0.991),255,0)':cb=128:cr=128,dblur=angle=70:radius=7,tmix=frames=3:weights='1 0.5 0.25',format=gbrp[mist];
    [with_fog][mist]blend=all_mode=screen:all_opacity=0.06[with_mist];
    [with_mist]eq=contrast='1.025+0.010*sin(2*PI*n/(30*${FPS}))':brightness='-0.012+0.008*sin(2*PI*n/(20*${FPS}))':eval=frame,vignette=angle=0.36,noise=alls=1.2:allf=t+u,format=yuv420p[vout]
  " -map "[vout]" \
  -c:v libx264 -preset veryfast -crf 20 -r "$FPS" -t 60 "$LOOP_CLIP"

echo ">> [2/2] Muxing with audio to $OUTPUT..."
LOOPS=$((DURATION / 60 + 1))

ffmpeg -y -stream_loop "$LOOPS" -i "$LOOP_CLIP" -i "$AUDIO" \
  -c:v copy -c:a aac -b:a 256k -ar 48000 -t "$DURATION" -movflags +faststart "$OUTPUT"

echo "Done -> $OUTPUT"

#!/bin/bash
# Render detached review samples for the three approved ChatGPT concepts.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE="/DATA/Media/DroneMill ChatGPT Concepts"
DEST="/srv/media/videos/DroneMill Previews"
DURATION="${1:-60}"

render_audio() {
  local output="$1" f1="$2" f2="$3" f3="$4" f4="$5" f5="$6"
  ffmpeg -y -nostdin \
    -f lavfi -t "$DURATION" -i "sine=frequency=${f1}:sample_rate=48000" \
    -f lavfi -t "$DURATION" -i "sine=frequency=${f2}:sample_rate=48000" \
    -f lavfi -t "$DURATION" -i "sine=frequency=${f3}:sample_rate=48000" \
    -f lavfi -t "$DURATION" -i "sine=frequency=${f4}:sample_rate=48000" \
    -f lavfi -t "$DURATION" -i "sine=frequency=${f5}:sample_rate=48000" \
    -filter_complex "
      [0:a]volume='if(isnan(t),0,0.018*(0.72+0.28*sin(2*PI*t/43)))':eval=frame,aformat=channel_layouts=stereo[a0];
      [1:a]volume='if(isnan(t),0,0.011*(0.68+0.32*sin(2*PI*t/59+0.7)))':eval=frame,haas=left_delay=1.1:right_delay=6.8[a1];
      [2:a]volume='if(isnan(t),0,0.008*(0.66+0.34*sin(2*PI*t/71+1.9)))':eval=frame,haas=left_delay=7.2:right_delay=1.0[a2];
      [3:a]volume='if(isnan(t),0,0.006*(0.64+0.36*sin(2*PI*t/67+2.8)))':eval=frame,aformat=channel_layouts=stereo[a3];
      [4:a]volume='if(isnan(t),0,0.004*(0.62+0.38*sin(2*PI*t/83+4.1)))':eval=frame,haas=left_delay=1.4:right_delay=7.8[a4];
      [a0][a1][a2][a3][a4]amix=inputs=5:normalize=0,
        aecho=0.90:0.15:1270|2810:0.07|0.03,highpass=f=55,lowpass=f=6500,
        volume=125,loudnorm=I=-24:TP=-3:LRA=9,
        afade=t=in:st=0:d=4,afade=t=out:st=$((DURATION - 6)):d=6[out]
    " -map "[out]" -ar 48000 -c:a pcm_s24le "$output"
}

render_video() {
  local image="$1" audio="$2" output="$3" palette="$4" seed="$5"
  ffmpeg -y -nostdin \
    -loop 1 -framerate 12 -t "$DURATION" -i "$image" \
    -f lavfi -t "$DURATION" -i "perlin=s=320x180:r=12:octaves=3:persistence=0.54:xscale=0.012:yscale=0.026:tscale=0.018:random_mode=seed:seed=${seed}" \
    -i "$audio" \
    -filter_complex "
      [0:v]scale=960:540:flags=lanczos,format=gbrp,split=2[base][moving];
      [1:v]scale=960:540:flags=bilinear,format=gray,split=2[dx][dy];
      [moving][dx][dy]displace=edge=smear[texture];
      color=s=960x540:r=12:c=black,format=gray,
        geq=lum='255*max(0,min(1,(Y-170)/230))',gblur=sigma=22[mask];
      [base][texture][mask]maskedmerge[alive];
      color=s=960x540:r=12:c=${palette},format=gbrp,
        fade=t=in:st=0:d=${DURATION}:alpha=1[colorwash];
      [alive][colorwash]blend=all_mode=screen:all_opacity=0.028,
        eq=brightness='-0.010+0.009*t/${DURATION}':contrast=1.015:eval=frame,
        vignette=angle=0.34,scale=1280:720:flags=lanczos,fps=24,format=yuv420p[vout]
    " \
    -map "[vout]" -map 2:a:0 -t "$DURATION" \
    -c:v libx264 -preset veryfast -crf 20 -r 24 \
    -c:a aac -b:a 192k -ar 48000 -ac 2 -movflags +faststart "$output"
}

render_concept() {
  local slug="$1" image="$2" palette="$3" seed="$4"
  shift 4
  local folder="$DEST/$slug-review"
  local wav="$ROOT/output/$slug-review.wav"
  mkdir -p "$folder"
  render_audio "$wav" "$@"
  render_video "$image" "$wav" "$folder/$slug-review.mp4" "$palette" "$seed"
  ffmpeg -y -ss "$((DURATION / 2))" -i "$folder/$slug-review.mp4" \
    -frames:v 1 -q:v 2 -update 1 "$folder/poster.jpg"
  rm -f "$wav"
}

render_concept "noonbloom" "$SOURCE/01-noonbloom-chatgpt.png" 0xffd8e6 301 \
  146.83 220.00 277.18 329.63 440.00
render_concept "tide-climbed-sky" "$SOURCE/02-the-tide-that-climbed-into-the-sky-chatgpt.png" 0x5d7f9b 419 \
  73.42 110.00 138.59 164.81 220.00
render_concept "orbital-ceramics" "$SOURCE/03-orbital-ceramics-workshop-chatgpt.png" 0xff9a4d 557 \
  130.81 196.00 246.94 293.66 392.00

echo "Three-concept review batch complete: $DEST"

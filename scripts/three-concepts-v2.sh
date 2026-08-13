#!/bin/bash
# Render complex scene-authored v2 reviews for the three ChatGPT concepts.

set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
SOURCE="/DATA/Media/DroneMill ChatGPT Concepts"
DEST="/srv/media/videos/DroneMill Previews"
DURATION="${1:-120}"

render_visual() {
  local mode="$1" image="$2" audio="$3" output="$4"
  local mask palette seed
  case "$mode" in
    noonbloom)
      mask="255*max(0,min(1,(Y-150)/220))"
      palette="0xffc9dc"
      seed=6101
      ;;
    tide)
      mask="255*max(0,min(1,(430-Y)/190))"
      palette="0x577b98"
      seed=6203
      ;;
    ceramics)
      mask="255*max(0,min(1,(Y-190)/230))"
      palette="0xff8b43"
      seed=6301
      ;;
  esac

  ffmpeg -y -nostdin \
    -loop 1 -framerate 12 -t "$DURATION" -i "$image" \
    -f lavfi -t "$DURATION" -i "perlin=s=320x180:r=12:octaves=3:persistence=0.54:xscale=0.010:yscale=0.024:tscale=0.015:random_mode=seed:seed=${seed}" \
    -i "$audio" \
    -filter_complex "
      [0:v]scale=960:540:flags=lanczos,format=gbrp,split=2[base][moving];
      [1:v]scale=960:540:flags=bilinear,format=gray,split=2[dx][dy];
      [moving][dx][dy]displace=edge=smear[texture];
      color=s=960x540:r=12:c=black,format=gray,geq=lum='${mask}',gblur=sigma=20[mask];
      [base][texture][mask]maskedmerge[alive];
      color=s=960x540:r=12:c=${palette},format=gbrp,fade=t=in:st=0:d=${DURATION}:alpha=1[wash];
      [alive][wash]blend=all_mode=screen:all_opacity=0.025,
        eq=brightness='-0.012+0.010*t/${DURATION}':contrast=1.018:eval=frame,
        vignette=angle=0.34,scale=1280:720:flags=lanczos,fps=24,format=yuv420p[vout]
    " -map "[vout]" -map 2:a:0 -t "$DURATION" \
    -c:v libx264 -preset veryfast -crf 20 -r 24 \
    -c:a aac -b:a 256k -ar 48000 -ac 2 -movflags +faststart "$output"
}

render_one() {
  local mode="$1" slug="$2" image="$3"
  local folder="$DEST/$slug-v2-review"
  local wav="$ROOT/output/$slug-v2.wav"
  mkdir -p "$folder"
  "$DIR/scene-sound-v2.sh" "$mode" "$wav" "$DURATION"
  render_visual "$mode" "$image" "$wav" "$folder/$slug-v2-review.mp4"
  ffmpeg -y -ss "$((DURATION / 2))" -i "$folder/$slug-v2-review.mp4" \
    -frames:v 1 -q:v 2 -update 1 "$folder/poster.jpg"
  rm -f "$wav"
}

render_one noonbloom noonbloom "$SOURCE/01-noonbloom-chatgpt.png"
render_one tide tide-climbed-sky "$SOURCE/02-the-tide-that-climbed-into-the-sky-chatgpt.png"
render_one ceramics orbital-ceramics "$SOURCE/03-orbital-ceramics-workshop-chatgpt.png"

echo "Complex v2 review batch complete: $DEST"

#!/bin/bash
# Generate and render Lighthouse-style, music-forward v4 reviews.

set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
SOURCE="/DATA/Media/DroneMill ChatGPT Concepts"
DEST="${DRONEMILL_MEDIA_DIR:-/DATA/Media}"
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
  local mode="$1" slug="$2" image="$3" prompt="$4"
  local music="${TMPDIR:-/tmp}/$slug-v4-latentscore-$$.wav"
  local mix="${TMPDIR:-/tmp}/$slug-v4-mix-$$.wav"
  local video="$DEST/$slug-v4-review.mp4"
  mkdir -p "$DEST"
  "$DIR/latentscore-gen.sh" "$prompt" "$music" "$DURATION"
  "$DIR/lighthouse-style-scene-audio.sh" "$mode" "${music%.wav}.mastered.wav" "$mix" "$DURATION"
  render_visual "$mode" "$image" "$mix" "$video"
  rm -f "$music" "${music%.wav}.mastered.wav" "$mix"
}

render_one noonbloom noonbloom "$SOURCE/01-noonbloom-chatgpt.png" \
  "slow human-composed ethereal cosmic dark ambient, vast translucent flowers in a white alien desert, fluid evolving synthesizer pads, beautiful celestial melancholy, deep spacious harmony, no percussion, no melody notes, no chimes, no sound effects"
render_one tide tide-climbed-sky "$SOURCE/02-the-tide-that-climbed-into-the-sky-chatgpt.png" \
  "slow human-composed anti-cosmic dark ambient, impossible black ocean rising into the storm sky, abyssal evolving synthesizer drones, immense dread and negative space, fluid unresolved harmony, no percussion, no melody notes, no horns, no sound effects"
render_one ceramics orbital-ceramics "$SOURCE/03-orbital-ceramics-workshop-chatgpt.png" \
  "slow human-composed warm cosmic dark ambient, solitary ceramics workshop orbiting a ringed planet, analog synthesizer pads, ancient craft in deep space, fluid evolving harmony, intimate wonder and quiet mystery, no percussion, no melody notes, no chimes, no sound effects"

echo "Lighthouse-style v4 review batch complete: $DEST"

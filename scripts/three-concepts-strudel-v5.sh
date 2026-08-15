#!/bin/bash
# Build 2-minute Strudel-composed, Lighthouse-style review videos.

set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
STRUDEL_ROOT="${STRUDEL_MUSIC_ROOT:-/root/.claude/skills/strudel-music}"
SOURCE="/DATA/Media/DroneMill ChatGPT Concepts"
DEST="${DRONEMILL_MEDIA_DIR:-/DATA/Media}"
DURATION=120

render_visual() {
  local mode="$1" image="$2" audio="$3" output="$4"
  local mask palette seed
  case "$mode" in
    noonbloom) mask="255*max(0,min(1,(Y-150)/220))"; palette="0xffc9dc"; seed=7101 ;;
    tide) mask="255*max(0,min(1,(430-Y)/190))"; palette="0x577b98"; seed=7203 ;;
    ceramics) mask="255*max(0,min(1,(Y-190)/230))"; palette="0xff8b43"; seed=7301 ;;
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
  local mode="$1" slug="$2" title="$3" image="$4" target_i="$5" target_lra="$6" target_tp="$7"
  local comp="$ROOT/assets/compositions/$slug-v5.js"
  local work="${TMPDIR:-/tmp}/dronemill-$slug-strudel-v5-$$"
  local raw="$work/raw.wav"
  local scene="$work/scene.wav"
  local master="$work/master.wav"
  local video="$DEST/$slug-strudel-v5-review.mp4"

  mkdir -p "$work" "$DEST"
  node "$STRUDEL_ROOT/src/runtime/offline-render-v2.mjs" "$comp" "$raw" 30 60
  "$DIR/lighthouse-style-scene-audio.sh" "$mode" "$raw" "$scene" "$DURATION"
  ffmpeg -y -nostdin -i "$scene" \
    -af "loudnorm=I=${target_i}:TP=${target_tp}:LRA=${target_lra},afade=t=in:st=0:d=5,afade=t=out:st=114:d=6" \
    -ar 48000 -c:a pcm_s24le "$master"
  render_visual "$mode" "$image" "$master" "$video"
  rm -rf "$work"
}

render_one noonbloom noonbloom "Noonbloom | Strudel v5 Review" \
  "$SOURCE/01-noonbloom-chatgpt.png" -22 10 -3
render_one tide tide-climbed-sky "The Tide That Climbed Into the Sky | Strudel v5 Review" \
  "$SOURCE/02-the-tide-that-climbed-into-the-sky-chatgpt.png" -20 11 -2.5
render_one ceramics orbital-ceramics "Orbital Ceramics Workshop | Strudel v5 Review" \
  "$SOURCE/03-orbital-ceramics-workshop-chatgpt.png" -21 9 -3

echo "Published three Strudel v5 reviews -> $DEST"

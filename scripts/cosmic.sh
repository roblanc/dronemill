#!/bin/bash
# Render 1h cosmic-horror ambient video.
# Usage: ./cosmic.sh <audio> <image_or_folder> <title> [pitch=0.93]
#
# If <image_or_folder> is a single file -> fast loop-based render (current behavior).
# If <image_or_folder> is a directory   -> multi-scene render with crossfade across 1h.
#
# Visual effects: pseudo-Ken-Burns drift + zoom breathing + light eq breathing
#                 + procedural fog overlay + grain + vignette.
# Audio effects:  pitch shift + lowpass + loudnorm (YouTube target) + 10s fade-out.

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
source "$DIR/_lib.sh"

AUDIO="$1"
IMAGE="$2"
TITLE="$3"
PITCH="${4:-0.93}"

if [ -z "$AUDIO" ] || [ -z "$IMAGE" ] || [ -z "$TITLE" ]; then
  echo "Usage: $0 <audio> <image_or_folder> <title> [pitch=0.93]"
  exit 1
fi

SLUG=$(slugify "$TITLE")
SHIFTED="$ROOT/output/${SLUG}_shifted.aac"
OUT="$ROOT/output/${SLUG}.mp4"

# ──────────────────────────────────────────────────────────────────
# One-time fog overlay generation (60s seamless loop, 1920x1080)
# ──────────────────────────────────────────────────────────────────
FOG="$ROOT/assets/fog_loop.mp4"
if [ ! -f "$FOG" ]; then
  echo "[setup] Generating fog overlay loop (one-time, ~10s)..."
  mkdir -p "$ROOT/assets"
  # Low-res gray noise -> scaled up + heavy blur = animated fog.
  # geq uses periodic sin/cos so the 60s clip loops cleanly.
  ffmpeg -y -f lavfi -i "color=c=gray:s=240x135:r=24:d=60" \
    -vf "geq=lum='128+55*sin(2*PI*(X+T*30)/400+T*0.5)*cos(2*PI*(Y-T*22)/300+T*0.3)':cb=128:cr=128,scale=1920:1080:flags=fast_bilinear,boxblur=18:2,format=yuv420p" \
    -c:v libx264 -preset ultrafast -pix_fmt yuv420p "$FOG"
fi

# ──────────────────────────────────────────────────────────────────
# Sample rate detection
# ──────────────────────────────────────────────────────────────────
SR=$(ffprobe -v error -select_streams a:0 -show_entries stream=sample_rate -of default=noprint_wrappers=1:nokey=1 "$AUDIO")
if [ -z "$SR" ] || ! [[ "$SR" =~ ^[0-9]+$ ]]; then
  SR=44100
fi

echo "[1/3] Pitch shift + AAC encode + loudnorm (pitch=$PITCH, sr=$SR, 1h target)..."
ffmpeg -y -stream_loop -1 -i "$AUDIO" \
  -af "asetrate=${SR}*${PITCH},aresample=${SR},atempo=$(awk "BEGIN {print 1/${PITCH}}"),lowpass=f=8000,loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=out:st=3590:d=10" \
  -c:a aac -b:a 192k -t 3600 "$SHIFTED"

# ──────────────────────────────────────────────────────────────────
# Shared video filter components
#  zoom : 1.00 -> 1.06 over 60s (sin, seamless loop)
#  drift: x ±50px / 120s, y ±30px / 90s — desynced from zoom = floating camera
#  eq   : contrast 15s, brightness 20s — both divide 60s -> loop seam clean
# ──────────────────────────────────────────────────────────────────
VF_BASE="scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,zoompan=z='1.03+0.03*sin(2*PI*on/1440)':x='iw/2-(iw/zoom/2)+50*sin(2*PI*on/2880)':y='ih/2-(ih/zoom/2)+30*cos(2*PI*on/2160)':d=1:s=1920x1080"
VF_POST="eq=contrast='1.0+0.015*sin(2*PI*n/360)':brightness='0.005*cos(2*PI*n/480)',noise=alls=8:allf=t+u,vignette='angle=0.4+0.03*sin(2*PI*t/6)'"

# ──────────────────────────────────────────────────────────────────
# Multi-image path: <IMAGE> is a directory
# ──────────────────────────────────────────────────────────────────
if [ -d "$IMAGE" ]; then
  mapfile -t IMAGES < <(find "$IMAGE" -maxdepth 1 -type f \( -iname "*.png" -o -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.webp" \) | sort)
  N=${#IMAGES[@]}
  if [ "$N" -eq 0 ]; then
    echo "ERROR: no images in $IMAGE" >&2
    exit 1
  fi
  if [ "$N" -gt 1 ]; then
    echo "[2/3] Multi-scene render: $N images, ~$((3600 / N))s each + 8s crossfade + fog..."
    XFADE=8
    SCENE_DUR=$((3600 / N))
    LAST_PAD=$(( 3600 - SCENE_DUR * (N - 1) ))   # absorb rounding into final scene

    # Build inputs
    INPUT_ARGS=()
    for idx in "${!IMAGES[@]}"; do
      if [ "$idx" -eq $((N-1)) ]; then
        INPUT_ARGS+=( -loop 1 -framerate 24 -t "$LAST_PAD" -i "${IMAGES[$idx]}" )
      else
        INPUT_ARGS+=( -loop 1 -framerate 24 -t "$((SCENE_DUR + XFADE))" -i "${IMAGES[$idx]}" )
      fi
    done
    INPUT_ARGS+=( -stream_loop -1 -i "$FOG" )
    FOG_IDX=$N

    # Filter graph
    FC=""
    for i in $(seq 0 $((N-1))); do
      FC+="[$i:v]${VF_BASE},${VF_POST}[v$i];"
    done

    # Chain xfades
    PREV="v0"
    for i in $(seq 1 $((N-1))); do
      OFFSET=$(( SCENE_DUR * i - XFADE ))
      LABEL="x$i"
      FC+="[$PREV][v$i]xfade=transition=fade:duration=${XFADE}:offset=${OFFSET}[$LABEL];"
      PREV="$LABEL"
    done

    # Fog overlay on top
    FC+="[${FOG_IDX}:v]scale=1920:1080,format=yuv420p[fog];"
    FC+="[$PREV][fog]blend=all_mode=screen:all_opacity=0.12,format=yuv420p[vout]"

    VIDEO_TMP="$ROOT/output/${SLUG}_video.mp4"
    ffmpeg -y "${INPUT_ARGS[@]}" \
      -filter_complex "$FC" \
      -map "[vout]" \
      -c:v libx264 -preset ultrafast -tune stillimage -pix_fmt yuv420p \
      -t 3600 -r 24 "$VIDEO_TMP"

    echo "[3/3] Mux video + audio..."
    ffmpeg -y -i "$VIDEO_TMP" -i "$SHIFTED" \
      -c:v copy -c:a copy -shortest \
      -map 0:v:0 -map 1:a:0 "$OUT"
    rm -f "$VIDEO_TMP" "$SHIFTED"
    echo "Done -> $OUT"
    exit 0
  fi
  # Only 1 image in dir -> fall through to fast path
  IMAGE="${IMAGES[0]}"
fi

# ──────────────────────────────────────────────────────────────────
# Single-image fast path (current behavior + drift + fog + loudnorm)
# ──────────────────────────────────────────────────────────────────
LOOP60="$ROOT/output/${SLUG}_loop60.mp4"
LOOPS=61

echo "[2/3] Build 60s clip (drift + breathing + fog overlay)..."
ffmpeg -y -loop 1 -framerate 24 -t 60 -i "$IMAGE" -stream_loop -1 -i "$FOG" \
  -filter_complex "[0:v]${VF_BASE},${VF_POST}[base];[1:v]scale=1920:1080,format=yuv420p[fog];[base][fog]blend=all_mode=screen:all_opacity=0.12,format=yuv420p[vout]" \
  -map "[vout]" \
  -c:v libx264 -tune stillimage -preset ultrafast -pix_fmt yuv420p \
  -r 24 -t 60 "$LOOP60"

echo "[3/3] Loop x${LOOPS} + mux audio..."
ffmpeg -y -stream_loop "$LOOPS" -i "$LOOP60" -i "$SHIFTED" \
  -c:v copy -c:a copy -shortest \
  -map 0:v:0 -map 1:a:0 "$OUT"

rm -f "$LOOP60" "$SHIFTED"
echo "Done -> $OUT"

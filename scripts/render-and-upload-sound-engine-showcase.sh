#!/bin/bash
set -euo pipefail

ROOT="/home/brewuser/projects/dronemill"
FPS=24
DURATION=60

mkdir -p "$ROOT/output" "$ROOT/audio" "$ROOT/descriptions"

AUDIO1_MASTER="$ROOT/audio/demo_1_latentscore.mastered.wav"
AUDIO2_MASTER="$ROOT/audio/demo_2_scenesound.wav"
AUDIO3_MASTER="$ROOT/audio/demo_3_dsp.wav"
AUDIO4_MASTER="$ROOT/audio/demo_4_ai_director.wav"
AUDIO5_MASTER="$ROOT/audio/demo_5_rubberband.wav"

echo "======================================================="
echo "🎬 RENDERING AND UPLOADING 5 SOUND ENGINE DEMO VIDEOS"
echo "======================================================="

render_and_upload() {
  local IMAGE="$1"
  local AUDIO="$2"
  local OVERLAY="$3"
  local OPACITY="$4"
  local TITLE="$5"
  local DESC_TEXT="$6"
  local TAGS="$7"
  local OUT_VIDEO="/tmp/showcase_temp.mp4"
  local DESC_FILE="/tmp/showcase_desc.txt"

  echo "$DESC_TEXT" > "$DESC_FILE"

  if [ -n "$OVERLAY" ] && [ -f "$OVERLAY" ]; then
    echo ">> Rendering video with overlay: $OVERLAY ($OPACITY)..."
    ffmpeg -y -nostdin \
      -loop 1 -framerate "$FPS" -t "$DURATION" -i "$IMAGE" \
      -stream_loop -1 -i "$OVERLAY" \
      -i "$AUDIO" \
      -filter_complex "
        [0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,format=gbrp[base];
        [1:v]scale=1920:1080:flags=lanczos,curves=all='0/0 0.08/0 0.50/0.40 1/1',format=gbrp[fx];
        [base][fx]blend=all_mode=screen:all_opacity=${OPACITY}[merged];
        [merged]vignette=angle=0.32,noise=alls=0.6:allf=t+u,format=yuv420p[vout]
      " -map "[vout]" -map "2:a" \
      -c:v libx264 -preset ultrafast -crf 20 -c:a aac -b:a 256k -ar 48000 -t "$DURATION" -movflags +faststart "$OUT_VIDEO"
  else
    echo ">> Rendering video without overlay..."
    ffmpeg -y -nostdin \
      -loop 1 -framerate "$FPS" -t "$DURATION" -i "$IMAGE" \
      -i "$AUDIO" \
      -filter_complex "
        [0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,vignette=angle=0.32,noise=alls=0.6:allf=t+u,format=yuv420p[vout]
      " -map "[vout]" -map "1:a" \
      -c:v libx264 -preset ultrafast -crf 20 -c:a aac -b:a 256k -ar 48000 -t "$DURATION" -movflags +faststart "$OUT_VIDEO"
  fi

  echo ">> Uploading $TITLE to YouTube..."
  "$ROOT/scripts/upload-yt.sh" "$OUT_VIDEO" "$TITLE" "$DESC_FILE" "$IMAGE" "unlisted" "$TAGS"
  rm -f "$DESC_FILE"
}

# 1. LatentScore Demo
echo "=== [1/5] LatentScore Neural Music Composer ==="
render_and_upload \
  "$ROOT/images/universal_diner.jpg" \
  "$AUDIO1_MASTER" \
  "$ROOT/assets/overlays/cinematic_rain_loop.mp4" \
  "0.75" \
  "[SOUND ENGINE DEMO] LatentScore Neural Music Composer | 1 minute sample" \
  "Sound Engine Demo: LatentScore Neural Music Composer (Docker dronemill-latentscore:0.1.8). Prompt: 'nostalgic 3am diner in heavy rain, soft neon reflections, warm lonely ambient'." \
  "ambient,latentscore,sound engine demo,neural music,timeless ambience"

# 2. Multi-Layer Scene Sound Engine Demo
echo "=== [2/5] Multi-Layer Scene Sound Engine ==="
render_and_upload \
  "$ROOT/images/universal_conservatory.jpg" \
  "$AUDIO2_MASTER" \
  "$ROOT/assets/overlays/dust_motes_loop.mp4" \
  "0.80" \
  "[SOUND ENGINE DEMO] Multi-Layer Scene Sound Engine | 1 minute sample" \
  "Sound Engine Demo: Multi-Layer Scene Sound Engine (Noonbloom recipe). 6-layer acoustic composition with breathing Lydian partials and organic membrane texture." \
  "ambient,scene sound,multi layer,sound engine demo,timeless ambience"

# 3. Procedural FFmpeg DSP Engine Demo
echo "=== [3/5] Procedural FFmpeg DSP Engine ==="
render_and_upload \
  "$ROOT/images/universal_asteroid_kitchen.jpg" \
  "$AUDIO3_MASTER" \
  "$ROOT/assets/youtube-overlays/fog-overlay.mp4" \
  "0.35" \
  "[SOUND ENGINE DEMO] Procedural FFmpeg DSP Engine | 1 minute sample" \
  "Sound Engine Demo: Procedural FFmpeg DSP Synthesizer. Harmonic sine partials with Haas 3D spatializer, analog chorus, and prime-period LFO volume envelopes." \
  "ambient,ffmpeg dsp,procedural sound,sound engine demo,timeless ambience"

# 4. AI Scene Director Demo
echo "=== [4/5] AI Scene Director (AGY Composed) ==="
render_and_upload \
  "$ROOT/images/midjourney_conservatory_test.jpg" \
  "$AUDIO4_MASTER" \
  "$ROOT/assets/overlays/dust_motes_loop.mp4" \
  "0.80" \
  "[SOUND ENGINE DEMO] AI Scene Director (AGY Composed) | 1 minute sample" \
  "Sound Engine Demo: AI Scene Director. Dynamically analyzed and composed in D Aeolian via connected Antigravity CLI (agy)." \
  "ambient,ai scene director,antigravity,sound engine demo,timeless ambience"

# 5. Rubberband Studio Pitch-Shift Demo
echo "=== [5/5] Rubberband Studio Pitch-Shift Engine ==="
render_and_upload \
  "$ROOT/images/winter_gothic_observatory_1786796620223.jpg" \
  "$AUDIO5_MASTER" \
  "$ROOT/assets/overlays/snow_blizzard_loop.mp4" \
  "0.70" \
  "[SOUND ENGINE DEMO] Rubberband Studio Pitch-Shift Engine | 1 minute sample" \
  "Sound Engine Demo: Rubberband Studio Pitch-Shift Engine (librubberband phase vocoder). Deep sub-octave ambient drone transformation." \
  "ambient,rubberband,pitch shift,dark ambient,sound engine demo,timeless ambience"

echo "=== ALL 5 SOUND ENGINE DEMOS RENDERED AND UPLOADED TO YOUTUBE ==="

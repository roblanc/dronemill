#!/bin/bash
set -euo pipefail

ROOT="/home/brewuser/projects/dronemill"
FPS=24
DURATION=60

mkdir -p "$ROOT/output" "$ROOT/audio/hybrid" "$ROOT/descriptions"

AUDIO1_HYBRID="$ROOT/audio/hybrid/sample_1_hybrid_duo.wav"
AUDIO2_HYBRID="$ROOT/audio/hybrid/sample_2_hybrid_trio.wav"
AUDIO3_HYBRID="$ROOT/audio/hybrid/sample_3_hybrid_ensemble.wav"

echo "======================================================="
echo "🎬 RENDERING AND UPLOADING 3 AI HYBRID SOUND DEMOS"
echo "======================================================="

render_and_upload() {
  local IMAGE="$1"
  local AUDIO="$2"
  local OVERLAY1="$3"
  local OPACITY1="$4"
  local OVERLAY2="${5:-}"
  local OPACITY2="${6:-}"
  local TITLE="$7"
  local DESC_TEXT="$8"
  local TAGS="$9"
  local OUT_VIDEO="/tmp/hybrid_showcase_temp.mp4"
  local DESC_FILE="/tmp/hybrid_desc.txt"

  echo "$DESC_TEXT" > "$DESC_FILE"

  if [ -n "$OVERLAY1" ] && [ -f "$OVERLAY1" ] && [ -n "$OVERLAY2" ] && [ -f "$OVERLAY2" ]; then
    echo ">> Rendering video with dual overlays: $OVERLAY1 ($OPACITY1) & $OVERLAY2 ($OPACITY2)..."
    ffmpeg -y -nostdin \
      -loop 1 -framerate "$FPS" -t "$DURATION" -i "$IMAGE" \
      -stream_loop -1 -i "$OVERLAY1" \
      -stream_loop -1 -i "$OVERLAY2" \
      -i "$AUDIO" \
      -filter_complex "
        [0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,format=gbrp[base];
        [1:v]scale=1920:1080:flags=lanczos,curves=all='0/0 0.10/0 0.50/0.40 1/1',format=gbrp[fx1];
        [2:v]scale=1920:1080:flags=lanczos,curves=all='0/0 0.20/0 0.50/0.25 1/0.80',format=gbrp[fx2];
        [base][fx2]blend=all_mode=screen:all_opacity=${OPACITY2}[with_fog];
        [with_fog][fx1]blend=all_mode=screen:all_opacity=${OPACITY1}[merged];
        [merged]vignette=angle=0.32,noise=alls=0.6:allf=t+u,format=yuv420p[vout]
      " -map "[vout]" -map "3:a" \
      -c:v libx264 -preset ultrafast -crf 20 -c:a aac -b:a 256k -ar 48000 -t "$DURATION" -movflags +faststart "$OUT_VIDEO"

  elif [ -n "$OVERLAY1" ] && [ -f "$OVERLAY1" ]; then
    echo ">> Rendering video with single overlay: $OVERLAY1 ($OPACITY1)..."
    ffmpeg -y -nostdin \
      -loop 1 -framerate "$FPS" -t "$DURATION" -i "$IMAGE" \
      -stream_loop -1 -i "$OVERLAY1" \
      -i "$AUDIO" \
      -filter_complex "
        [0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,format=gbrp[base];
        [1:v]scale=1920:1080:flags=lanczos,curves=all='0/0 0.08/0 0.50/0.40 1/1',format=gbrp[fx];
        [base][fx]blend=all_mode=screen:all_opacity=${OPACITY1}[merged];
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
  rm -f "$DESC_FILE" "$OUT_VIDEO"
}

# echo "=== [1/3] Sample 1: Hybrid Duo (Already Uploaded) ==="
# render_and_upload ...

# =========================================================================
# SAMPLE 2: THE HYBRID TRIO (3 Engines: LatentScore + Procedural DSP + Rubberband Sub)
# =========================================================================
echo "=== [2/3] Sample 2: Hybrid Trio (LatentScore + Procedural DSP + Rubberband Sub) ==="
render_and_upload \
  "$ROOT/images/universal_asteroid_kitchen.jpg" \
  "$AUDIO2_HYBRID" \
  "$ROOT/assets/youtube-overlays/fog-overlay.mp4" \
  "0.35" \
  "" \
  "" \
  "[HYBRID TRIO] a kitchen drifting through the asteroid winter | cozy sci-fi ambient | 1 min sample" \
  "AI Hybrid Orchestration Demo (3 Engines Combined):
• LatentScore Neural Music Composer: Space voyager synth theme in Bb modal.
• Procedural FFmpeg DSP Engine: Haas 3D stereo harmonic sine partials with prime LFO breathing cycles.
• Rubberband Studio Pitch-Shift Engine: Deep sub-octave phase-vocoded space drone (-12 semitones, under 80Hz).
• Mastered with dynamic limiter & EBU R128 (-22 LUFS).

Visual: Universal Ambient asteroid galley kitchen + slow volumetric cosmic haze.

#ambient #scifiambient #hybridmusic #latentscore #rubberband #dsp #timelessambience" \
  "ambient,sci-fi ambient,hybrid music,latentscore,rubberband,dsp,timeless ambience"

# =========================================================================
# SAMPLE 3: THE HYBRID 5-ENGINE ENSEMBLE (All 5 Engines in Concert)
# =========================================================================
echo "=== [3/3] Sample 3: Hybrid 5-Engine Ensemble (All 5 Engines Working Together) ==="
render_and_upload \
  "$ROOT/images/universal_conservatory.jpg" \
  "$AUDIO3_HYBRID" \
  "$ROOT/assets/overlays/dust_motes_loop.mp4" \
  "0.80" \
  "$ROOT/assets/youtube-overlays/fog-overlay.mp4" \
  "0.25" \
  "[HYBRID 5-ENGINE ENSEMBLE] the flooded palms at twilight | victorian conservatory ambient | 1 min sample" \
  "AI Hybrid Orchestration Demo (Full 5-Engine Ensemble in Concert):
1. AI Harmonic Director (AGY / Antigravity): Mathematical F Lydian modal map (87.31Hz root + exact partials).
2. LatentScore Neural Music Composer: Victorian greenhouse reverie acoustic pad progression.
3. Multi-Layer Environmental Foley: Conservatory droplets, foliage whisper & room acoustics.
4. Procedural FFmpeg DSP Engine: Haas 3D stereo spatialized sine partials on prime LFO envelopes.
5. Rubberband Studio Pitch-Shift Engine: Sub-octave cathedral resonance drone for deep physical warmth.
• Full multi-bus mastering with EBU R128 (-22 LUFS) and true-peak protection.

Visual: Universal Ambient conservatory + 3D floating dust motes & gentle mist.

#ambient #conservatory #hybridorchestra #latentscore #5engines #timelessambience" \
  "ambient,conservatory,hybrid orchestra,latentscore,5 engines,timeless ambience"

echo "=== ALL 3 HYBRID DEMO SAMPLES RENDERED AND UPLOADED TO YOUTUBE ==="

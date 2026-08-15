#!/bin/bash
# AI-Directed Dynamic Audio & Video Pipeline for DroneMill
# Usage: ./scripts/ai-render-pipeline.sh <image_path> "<video_title>" [duration_seconds=60] [output_path]

set -euo pipefail

IMAGE="${1:-}"
TITLE="${2:-}"
DURATION="${3:-60}"
ROOT="/home/brewuser/projects/dronemill"

if [ -z "$IMAGE" ] || [ -z "$TITLE" ]; then
  echo "Usage: $0 <image_path> \"<video_title>\" [duration_seconds=60] [output_path]"
  exit 1
fi

SLUG=$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-//;s/-$//' | cut -c 1-80)
OUTPUT="${4:-$ROOT/output/${SLUG}.mp4}"
PROFILE="/tmp/profile_${SLUG}.json"
DESC_FILE="$ROOT/descriptions/${SLUG}.txt"
FPS=24

mkdir -p "$ROOT/output" "$ROOT/descriptions" "$ROOT/profiles"

# =================================================================
# 1. RUN AI SCENE DIRECTOR VIA ANTIGRAVITY (AGY)
# =================================================================
echo ">> [1/4] Running AI Scene Director via 'agy'..."
python3 "$ROOT/scripts/ai-scene-director.py" "$TITLE" "$PROFILE"

# Extract description and save to descriptions/
python3 -c "
import json, sys
with open('$PROFILE') as f:
    p = json.load(f)
desc = p.get('seo_description', '')
with open('$DESC_FILE', 'w', encoding='utf-8') as f:
    f.write(desc + '\n')
"

# Parse audio & visual variables
eval $(python3 -c "
import json
with open('$PROFILE') as f:
    p = json.load(f)
mp = p.get('musical_palette', {})
vfx = p.get('visual_fx', {})

partials = mp.get('harmony_partials', [55.0, 110.0, 164.81, 220.0, 261.63])
while len(partials) < 5:
    partials.append(partials[-1] * 1.5)

print(f'F0={partials[0]}')
print(f'F1={partials[1]}')
print(f'F2={partials[2]}')
print(f'F3={partials[3]}')
print(f'F4={partials[4]}')
print(f'SUB_FREQ={mp.get(\"sub_frequency\", 43.65)}')
print(f'NOISE_TYPE={mp.get(\"noise_type\", \"pink\")}')
print(f'NOISE_HIGH={mp.get(\"noise_filter_high\", 2800)}')
print(f'NOISE_VOL={mp.get(\"noise_volume\", 0.035)}')

lfos = mp.get('lfo_periods', [37, 53, 73, 97])
while len(lfos) < 4:
    lfos.append(61)
print(f'LFO0={lfos[0]}')
print(f'LFO1={lfos[1]}')
print(f'LFO2={lfos[2]}')
print(f'LFO3={lfos[3]}')

print(f'OVERLAY_TYPE={vfx.get(\"overlay_type\", \"none\")}')
print(f'OVERLAY_OPACITY={vfx.get(\"overlay_opacity\", 0.75)}')
print(f'CAMERA_DRIFT={vfx.get(\"camera_drift_px\", 40)}')
print(f'CAMERA_ZOOM={vfx.get(\"camera_zoom_amount\", 0.016)}')
")

# =================================================================
# 2. DYNAMICALLY SYNTHESIZE HARMONIC AUDIO (-22 LUFS)
# =================================================================
AUDIO_OUT="/tmp/audio_${SLUG}.wav"
echo ">> [2/4] Synthesizing AI-directed harmonic soundscape ($DURATION s)..."

ffmpeg -y -nostdin \
  -f lavfi -t "$DURATION" -i "anoisesrc=c=${NOISE_TYPE}:r=48000:a=1:seed=8812" \
  -f lavfi -t "$DURATION" -i "sine=frequency=${SUB_FREQ}:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=${F0}:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=${F1}:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=${F2}:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=${F3}:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=${F4}:sample_rate=48000" \
  -filter_complex "
    [0:a]lowpass=f=${NOISE_HIGH},volume=${NOISE_VOL}:eval=frame,aformat=channel_layouts=stereo[ambience];
    [1:a]lowpass=f=140,volume=0.045:eval=frame,aformat=channel_layouts=stereo[sub];
    [2:a]volume=0.080*(0.70+0.30*sin(2*3.14159265*t/${LFO0})):eval=frame[s1];
    [3:a]volume=0.045*(0.65+0.35*sin(2*3.14159265*t/${LFO1})):eval=frame,haas=left_delay=2.5:right_delay=6.0[s2];
    [4:a]volume=0.030*(0.60+0.40*sin(2*3.14159265*t/${LFO2})):eval=frame,haas=left_delay=6.5:right_delay=2.0[s3];
    [5:a]volume=0.020*(0.55+0.45*sin(2*3.14159265*t/${LFO3})):eval=frame,aformat=channel_layouts=stereo[s4];
    [6:a]volume=0.015:eval=frame,haas=left_delay=1.5:right_delay=8.0[s5];
    [s1][s2][s3][s4][s5]amix=inputs=5:normalize=0,chorus=0.28:0.38:35|50:0.05|0.035:0.06|0.045:0.09|0.07,aecho=0.92:0.22:1800|3800:0.08|0.04,lowpass=f=3800[music];
    [ambience][sub][music]amix=inputs=3:normalize=0:dropout_transition=0,
      highpass=f=25,lowpass=f=4400,acompressor=threshold=0.28:ratio=1.35:attack=180:release=1800,
      loudnorm=I=-22:TP=-3:LRA=4.5,afade=t=in:st=0:d=3,afade=t=out:st=$((DURATION - 4)):d=4[out]
  " -map "[out]" -ar 48000 -c:a pcm_s24le -t "$DURATION" "$AUDIO_OUT"

# =================================================================
# 3. SELECT VISUAL OVERLAY & RENDER SCENE MOTION
# =================================================================
echo ">> [3/4] Rendering video with overlay: $OVERLAY_TYPE ($OVERLAY_OPACITY)..."
TMP_CLIP="/tmp/clip_${SLUG}.mp4"

OVERLAY_FILE=""
case "$OVERLAY_TYPE" in
  rain)
    OVERLAY_FILE="$ROOT/assets/overlays/cinematic_rain_loop.mp4"
    ;;
  dust_motes|dust)
    OVERLAY_FILE="$ROOT/assets/overlays/dust_motes_loop.mp4"
    ;;
  snow_blizzard|snow)
    OVERLAY_FILE="$ROOT/assets/overlays/snow_blizzard_loop.mp4"
    ;;
  fog)
    OVERLAY_FILE="$ROOT/assets/youtube-overlays/fog-overlay.mp4"
    ;;
  *)
    OVERLAY_FILE=""
    ;;
esac

if [ -n "$OVERLAY_FILE" ] && [ -f "$OVERLAY_FILE" ]; then
  ffmpeg -y -nostdin \
    -loop 1 -framerate "$FPS" -t "$DURATION" -i "$IMAGE" \
    -stream_loop -1 -i "$OVERLAY_FILE" \
    -filter_complex "
      [0:v]scale=3200:1800:force_original_aspect_ratio=increase,crop=3200:1800,zoompan=z='1.02+${CAMERA_ZOOM}*(0.5-0.5*cos(2*3.14159265*on/(60*${FPS})))':x='iw/2-(iw/zoom/2)+${CAMERA_DRIFT}*sin(2*3.14159265*on/(60*${FPS}))':y='ih/2-(ih/zoom/2)+8*cos(2*3.14159265*on/(60*${FPS}))':d=1:s=1920x1080:fps=${FPS},format=gbrp[base];
      [1:v]scale=1920:1080:flags=lanczos,curves=all='0/0 0.08/0 0.50/0.40 1/1',format=gbrp[fx];
      [base][fx]blend=all_mode=screen:all_opacity=${OVERLAY_OPACITY}[merged];
      [merged]vignette=angle=0.32,noise=alls=0.6:allf=t+u,format=yuv420p[vout]
    " -map "[vout]" \
    -c:v libx264 -preset veryfast -crf 19 -r "$FPS" -t "$DURATION" "$TMP_CLIP"
else
  ffmpeg -y -nostdin \
    -loop 1 -framerate "$FPS" -t "$DURATION" -i "$IMAGE" \
    -filter_complex "
      [0:v]scale=3200:1800:force_original_aspect_ratio=increase,crop=3200:1800,zoompan=z='1.02+${CAMERA_ZOOM}*(0.5-0.5*cos(2*3.14159265*on/(60*${FPS})))':x='iw/2-(iw/zoom/2)+${CAMERA_DRIFT}*sin(2*3.14159265*on/(60*${FPS}))':y='ih/2-(ih/zoom/2)+8*cos(2*3.14159265*on/(60*${FPS}))':d=1:s=1920x1080:fps=${FPS},vignette=angle=0.32,noise=alls=0.6:allf=t+u,format=yuv420p[vout]
    " -map "[vout]" \
    -c:v libx264 -preset veryfast -crf 19 -r "$FPS" -t "$DURATION" "$TMP_CLIP"
fi

# =================================================================
# 4. MUX AUDIO AND VIDEO
# =================================================================
echo ">> [4/4] Muxing to $OUTPUT..."
ffmpeg -y -i "$TMP_CLIP" -i "$AUDIO_OUT" -c:v copy -c:a aac -b:a 256k -ar 48000 -t "$DURATION" -movflags +faststart "$OUTPUT"
rm -f "$TMP_CLIP" "$AUDIO_OUT"

echo ">> SUCCESS: Generated AI-Directed Video -> $OUTPUT"
echo ">> Description file created -> $DESC_FILE"

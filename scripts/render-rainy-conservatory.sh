#!/bin/bash
# Rainy Conservatory Renderer
# Integrates:
# 1. Warm rain on glass roof audio soundscape (-22 LUFS)
# 2. Diagonal cinematic rain streaks with motion blur (transparent screen blend)
# 3. Soft lantern glow pulse + subpixel eased camera zoom

set -euo pipefail

IMAGE="${1:-}"
AUDIO="${2:-}"
OUTPUT="${3:-}"
DURATION="${4:-60}"
FPS=24

ROOT="/root/dronemill"
RAIN_OVERLAY="$ROOT/assets/youtube-overlays/rain-overlay.mp4"

mkdir -p "$(dirname "$OUTPUT")"
WORK="${TMPDIR:-/tmp}/conservatory_render_$$"
mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT

# 1. Generate customized rainy greenhouse audio if not provided
if [ ! -f "$AUDIO" ]; then
  AUDIO="$WORK/rain_audio.wav"
  echo ">> Generating warm rain ambient soundscape..."
  ffmpeg -y -nostdin \
    -f lavfi -t "$DURATION" -i "anoisesrc=c=pink:r=48000:a=1:seed=8812" \
    -f lavfi -t "$DURATION" -i "anoisesrc=c=brown:r=48000:a=1:seed=8819" \
    -f lavfi -t "$DURATION" -i "sine=frequency=65.41:sample_rate=48000" \
    -f lavfi -t "$DURATION" -i "sine=frequency=130.81:sample_rate=48000" \
    -f lavfi -t "$DURATION" -i "sine=frequency=196.00:sample_rate=48000" \
    -f lavfi -t "$DURATION" -i "sine=frequency=293.66:sample_rate=48000" \
    -f lavfi -t "$DURATION" -i "sine=frequency=392.00:sample_rate=48000" \
    -filter_complex "
      [0:a]highpass=f=200,lowpass=f=2800,volume='0.022*(0.75+0.15*sin(2*PI*t/14)+0.10*sin(2*PI*t/39))':eval=frame,aformat=channel_layouts=stereo[rain_glass];
      [1:a]lowpass=f=180,volume='0.035*(0.70+0.20*sin(2*PI*t/29)+0.10*sin(2*PI*t/71))':eval=frame,aformat=channel_layouts=stereo[sub_rumble];
      [2:a]lowpass=f=120,volume='0.085*(0.72+0.28*sin(2*PI*t/41))':eval=frame,aformat=channel_layouts=stereo[c1];
      [3:a]volume='0.035*(0.65+0.35*sin(2*PI*t/53+1.2))':eval=frame,haas=left_delay=1.1:right_delay=7.2[c2];
      [4:a]volume='0.025*(0.60+0.40*sin(2*PI*t/67+2.4))':eval=frame,haas=left_delay=7.5:right_delay=1.0[c3];
      [5:a]volume='0.018*(0.55+0.45*sin(2*PI*t/79+3.1))':eval=frame,aformat=channel_layouts=stereo[c4];
      [6:a]volume='0.014*(0.52+0.48*sin(2*PI*t/91+0.8))':eval=frame,haas=left_delay=1.0:right_delay=8.5[c5];
      [c1][c2][c3][c4][c5]amix=inputs=5:normalize=0,chorus=0.25:0.38:35|50:0.05|0.035:0.06|0.045:0.09|0.07,aecho=0.92:0.18:1600|3800:0.07|0.03,lowpass=f=3500[music];
      [rain_glass][sub_rumble][music]amix=inputs=3:normalize=0:dropout_transition=0,
        highpass=f=25,lowpass=f=4200,acompressor=threshold=0.28:ratio=1.35:attack=180:release=1800,
        loudnorm=I=-22:TP=-3:LRA=4.5,afade=t=in:st=0:d=4,afade=t=out:st=$((DURATION - 5)):d=5[out]
    " -map "[out]" -ar 48000 -c:a pcm_s24le -t "$DURATION" "$AUDIO"
fi

LOOP_CLIP="$WORK/loop60.mp4"

echo ">> [1/2] Rendering 60s rainy greenhouse scene with soft rain overlay..."

ffmpeg -y -nostdin \
  -loop 1 -framerate "$FPS" -t 60 -i "$IMAGE" \
  -stream_loop -1 -i "$RAIN_OVERLAY" \
  -filter_complex "
    [0:v]scale=3200:1800:force_original_aspect_ratio=increase,crop=3200:1800,zoompan=z='1.02+0.016*(0.5-0.5*cos(2*PI*on/(60*${FPS})))':x='iw/2-(iw/zoom/2)+40*sin(2*PI*on/(60*${FPS}))':y='ih/2-(ih/zoom/2)+10*cos(2*PI*on/(60*${FPS}))':d=1:s=1920x1080:fps=${FPS},format=gbrp[base];
    [1:v]scale=1920:1080:flags=lanczos,curves=all='0/0 0.12/0 0.45/0.25 0.80/0.70 1/0.90',format=gbrp[rain_soft];
    [base][rain_soft]blend=all_mode=screen:all_opacity=0.32[merged];
    [merged]eq=contrast='1.018+0.007*sin(2*PI*n/(30*${FPS}))':brightness='-0.006+0.006*sin(2*PI*n/(20*${FPS}))',vignette=angle=0.34,noise=alls=0.7:allf=t+u,format=yuv420p[vout]
  " -map "[vout]" \
  -c:v libx264 -preset veryfast -crf 19 -r "$FPS" -t 60 "$LOOP_CLIP"

echo ">> [2/2] Muxing with audio to $OUTPUT..."
LOOPS=$((DURATION / 60 + 1))

ffmpeg -y -stream_loop "$LOOPS" -i "$LOOP_CLIP" -i "$AUDIO" \
  -c:v copy -c:a aac -b:a 256k -ar 48000 -t "$DURATION" -movflags +faststart "$OUTPUT"

echo "Done -> $OUTPUT"

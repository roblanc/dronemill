#!/bin/bash
set -euo pipefail

ROOT="/home/brewuser/projects/dronemill"
FPS=24
DURATION=60

mkdir -p "$ROOT/output"

# =========================================================================
# 1. SAMPLE 1: SPINNING NEON IN THE RAIN (HIGH VISIBILITY CINEMATIC RAIN)
# =========================================================================
echo "=== [1/3] Rendering Sample 1: Spinning Neon in the Rain (Visible Rain FX) ==="
IMAGE1="$ROOT/images/midjourney_diner_test.jpg"
RAIN_OVERLAY="$ROOT/assets/overlays/cinematic_rain_loop.mp4"
AUDIO1="/tmp/audio_diner_v2.wav"
VIDEO1="$ROOT/output/midjourney-diner-test-sample.mp4"
TMP_CLIP1="/tmp/clip_diner_v2.mp4"

echo ">> Synthesizing rain & analog pad audio..."
ffmpeg -y -nostdin \
  -f lavfi -t "$DURATION" -i "anoisesrc=c=pink:r=48000:a=1:seed=4412" \
  -f lavfi -t "$DURATION" -i "anoisesrc=c=brown:r=48000:a=1:seed=7719" \
  -f lavfi -t "$DURATION" -i "sine=frequency=55.00:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=110.00:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=164.81:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=220.00:sample_rate=48000" \
  -filter_complex "
    [0:a]highpass=f=250,lowpass=f=3200,volume=0.035:eval=frame,aformat=channel_layouts=stereo[rain];
    [1:a]lowpass=f=160,volume=0.045:eval=frame,aformat=channel_layouts=stereo[sub];
    [2:a]volume=0.075:eval=frame[s1];
    [3:a]volume=0.038:eval=frame,haas=left_delay=2.5:right_delay=5.8[s2];
    [4:a]volume=0.024:eval=frame,haas=left_delay=6.0:right_delay=1.5[s3];
    [5:a]volume=0.016:eval=frame,aformat=channel_layouts=stereo[s4];
    [s1][s2][s3][s4]amix=inputs=4:normalize=0,chorus=0.25:0.38:35|50:0.05|0.035:0.06|0.045:0.09|0.07,aecho=0.9:0.2:1800|3600:0.08|0.04,lowpass=f=3600[pads];
    [rain][sub][pads]amix=inputs=3:normalize=0:dropout_transition=0,
      highpass=f=25,lowpass=f=4500,acompressor=threshold=0.28:ratio=1.35:attack=180:release=1800,
      loudnorm=I=-22:TP=-3:LRA=4.5,afade=t=in:st=0:d=3,afade=t=out:st=56:d=4[out]
  " -map "[out]" -ar 48000 -c:a pcm_s24le -t "$DURATION" "$AUDIO1"

echo ">> Rendering video with bold cinematic rain streaks & neon pulse..."
ffmpeg -y -nostdin \
  -loop 1 -framerate "$FPS" -t "$DURATION" -i "$IMAGE1" \
  -stream_loop -1 -i "$RAIN_OVERLAY" \
  -filter_complex "
    [0:v]scale=3200:1800:force_original_aspect_ratio=increase,crop=3200:1800,zoompan=z='1.02+0.018*(0.5-0.5*cos(2*3.14159265*on/(60*${FPS})))':x='iw/2-(iw/zoom/2)+45*sin(2*3.14159265*on/(60*${FPS}))':y='ih/2-(ih/zoom/2)+10*cos(2*3.14159265*on/(60*${FPS}))':d=1:s=1920x1080:fps=${FPS},format=gbrp[base];
    [1:v]scale=1920:1080:flags=lanczos,curves=all='0/0 0.05/0 0.50/0.45 1/1',format=gbrp[rain_crisp];
    [base][rain_crisp]blend=all_mode=screen:all_opacity=0.75[merged];
    [merged]eq=contrast='1.025+0.015*sin(2*3.14159265*n/(2.8*${FPS}))':brightness='-0.005+0.008*sin(2*3.14159265*n/(1.9*${FPS}))',vignette=angle=0.32,noise=alls=0.7:allf=t+u,format=yuv420p[vout]
  " -map "[vout]" \
  -c:v libx264 -preset veryfast -crf 19 -r "$FPS" -t "$DURATION" "$TMP_CLIP1"

ffmpeg -y -i "$TMP_CLIP1" -i "$AUDIO1" -c:v copy -c:a aac -b:a 256k -ar 48000 -t "$DURATION" -movflags +faststart "$VIDEO1"
rm -f "$TMP_CLIP1" "$AUDIO1"
echo "Done Sample 1: $VIDEO1"


# =========================================================================
# 2. SAMPLE 2: THE FLOODED PALMS (VISIBLE DUST MOTES + VOLUMETRIC MIST)
# =========================================================================
echo "=== [2/3] Rendering Sample 2: The Flooded Palms (Dust Motes & Mist) ==="
IMAGE2="$ROOT/images/midjourney_conservatory_test.jpg"
DUST_OVERLAY="$ROOT/assets/overlays/dust_motes_loop.mp4"
FOG_OVERLAY="$ROOT/assets/youtube-overlays/fog-overlay.mp4"
AUDIO2="/tmp/audio_conservatory_v2.wav"
VIDEO2="$ROOT/output/midjourney-conservatory-test-sample.mp4"
TMP_CLIP2="/tmp/clip_conservatory_v2.mp4"

echo ">> Synthesizing organ & choir ambient drone..."
ffmpeg -y -nostdin \
  -f lavfi -t "$DURATION" -i "anoisesrc=c=pink:r=48000:a=1:seed=9912" \
  -f lavfi -t "$DURATION" -i "sine=frequency=65.41:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=130.81:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=196.00:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=246.94:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=329.63:sample_rate=48000" \
  -filter_complex "
    [0:a]highpass=f=200,lowpass=f=2200,volume=0.015:eval=frame,aformat=channel_layouts=stereo[air];
    [1:a]volume=0.080:eval=frame[c1];
    [2:a]volume=0.045:eval=frame,haas=left_delay=2.0:right_delay=6.5[c2];
    [3:a]volume=0.030:eval=frame,haas=left_delay=7.0:right_delay=1.5[c3];
    [4:a]volume=0.020:eval=frame,aformat=channel_layouts=stereo[c4];
    [5:a]volume=0.015:eval=frame,haas=left_delay=1.5:right_delay=8.0[c5];
    [c1][c2][c3][c4][c5]amix=inputs=5:normalize=0,chorus=0.30:0.40:40|55:0.06|0.04:0.07|0.05:0.10|0.08,aecho=0.92:0.25:2000|4000:0.10|0.05,lowpass=f=3200[organ];
    [air][organ]amix=inputs=2:normalize=0:dropout_transition=0,
      highpass=f=25,lowpass=f=3800,acompressor=threshold=0.28:ratio=1.35:attack=180:release=1800,
      loudnorm=I=-22:TP=-3:LRA=4.5,afade=t=in:st=0:d=3,afade=t=out:st=56:d=4[out]
  " -map "[out]" -ar 48000 -c:a pcm_s24le -t "$DURATION" "$AUDIO2"

echo ">> Rendering video with floating golden motes, mist, & lantern pulse..."
ffmpeg -y -nostdin \
  -loop 1 -framerate "$FPS" -t "$DURATION" -i "$IMAGE2" \
  -stream_loop -1 -i "$DUST_OVERLAY" \
  -stream_loop -1 -i "$FOG_OVERLAY" \
  -filter_complex "
    [0:v]scale=3200:1800:force_original_aspect_ratio=increase,crop=3200:1800,zoompan=z='1.02+0.016*(0.5-0.5*cos(2*3.14159265*on/(60*${FPS})))':x='iw/2-(iw/zoom/2)+42*sin(2*3.14159265*on/(60*${FPS}))':y='ih/2-(ih/zoom/2)+10*cos(2*3.14159265*on/(60*${FPS}))':d=1:s=1920x1080:fps=${FPS},format=gbrp[base];
    [1:v]scale=1920:1080:flags=lanczos,curves=all='0/0 0.10/0 0.50/0.40 1/1',format=gbrp[dust_bright];
    [2:v]scale=1920:1080:flags=lanczos,curves=all='0/0 0.20/0 0.50/0.25 1/0.80',format=gbrp[fog_soft];
    [base][fog_soft]blend=all_mode=screen:all_opacity=0.30[with_fog];
    [with_fog][dust_bright]blend=all_mode=screen:all_opacity=0.85[merged];
    [merged]eq=brightness='0.008*sin(2*3.14159265*n/(3.5*${FPS}))',vignette=angle=0.32,noise=alls=0.6:allf=t+u,format=yuv420p[vout]
  " -map "[vout]" \
  -c:v libx264 -preset veryfast -crf 19 -r "$FPS" -t "$DURATION" "$TMP_CLIP2"

ffmpeg -y -i "$TMP_CLIP2" -i "$AUDIO2" -c:v copy -c:a aac -b:a 256k -ar 48000 -t "$DURATION" -movflags +faststart "$VIDEO2"
rm -f "$TMP_CLIP2" "$AUDIO2"
echo "Done Sample 2: $VIDEO2"


# =========================================================================
# 3. SAMPLE 3: ASTEROID KITCHEN (COSMIC DUST & SHIP GLOW)
# =========================================================================
echo "=== [3/3] Rendering Sample 3: Asteroid Kitchen (Cosmic Drift & Indicator Glow) ==="
IMAGE3="$ROOT/images/midjourney_asteroid_galley_test.jpg"
FOG_OVERLAY="$ROOT/assets/youtube-overlays/fog-overlay.mp4"
AUDIO3="/tmp/audio_asteroid_v2.wav"
VIDEO3="$ROOT/output/midjourney-asteroid-galley-test-sample.mp4"
TMP_CLIP3="/tmp/clip_asteroid_v2.mp4"

echo ">> Synthesizing sub-bass space rumble & cosmic resonance..."
ffmpeg -y -nostdin \
  -f lavfi -t "$DURATION" -i "anoisesrc=c=brown:r=48000:a=1:seed=1219" \
  -f lavfi -t "$DURATION" -i "sine=frequency=43.65:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=87.31:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=130.81:sample_rate=48000" \
  -f lavfi -t "$DURATION" -i "sine=frequency=261.63:sample_rate=48000" \
  -filter_complex "
    [0:a]lowpass=f=120,volume=0.060:eval=frame,aformat=channel_layouts=stereo[sub_deep];
    [1:a]volume=0.085:eval=frame[f1];
    [2:a]volume=0.040:eval=frame,haas=left_delay=3.0:right_delay=7.0[f2];
    [3:a]volume=0.025:eval=frame,haas=left_delay=8.0:right_delay=2.0[f3];
    [4:a]volume=0.012:eval=frame,aformat=channel_layouts=stereo[f4];
    [f1][f2][f3][f4]amix=inputs=4:normalize=0,chorus=0.35:0.45:45|60:0.07|0.05:0.08|0.06:0.12|0.09,aecho=0.90:0.20:2400|4800:0.09|0.04,lowpass=f=2800[sci_drone];
    [sub_deep][sci_drone]amix=inputs=2:normalize=0:dropout_transition=0,
      highpass=f=20,lowpass=f=3500,acompressor=threshold=0.28:ratio=1.35:attack=180:release=1800,
      loudnorm=I=-22:TP=-3:LRA=4.5,afade=t=in:st=0:d=3,afade=t=out:st=56:d=4[out]
  " -map "[out]" -ar 48000 -c:a pcm_s24le -t "$DURATION" "$AUDIO3"

echo ">> Rendering video with cosmic nebula drift & instrument glow pulse..."
ffmpeg -y -nostdin \
  -loop 1 -framerate "$FPS" -t "$DURATION" -i "$IMAGE3" \
  -stream_loop -1 -i "$FOG_OVERLAY" \
  -filter_complex "
    [0:v]scale=3200:1800:force_original_aspect_ratio=increase,crop=3200:1800,zoompan=z='1.02+0.014*(0.5-0.5*cos(2*3.14159265*on/(60*${FPS})))':x='iw/2-(iw/zoom/2)+50*sin(2*3.14159265*on/(60*${FPS}))':y='ih/2-(ih/zoom/2)+6*cos(2*3.14159265*on/(60*${FPS}))':d=1:s=1920x1080:fps=${FPS},format=gbrp[base];
    [1:v]scale=1920:1080:flags=lanczos,curves=all='0/0 0.12/0 0.45/0.25 0.80/0.70 1/0.90',format=gbrp[fog_soft];
    [base][fog_soft]blend=all_mode=screen:all_opacity=0.35[merged];
    [merged]eq=contrast='1.02+0.012*sin(2*3.14159265*n/(4.2*${FPS}))':brightness='0.006*sin(2*3.14159265*n/(2.1*${FPS}))',vignette=angle=0.35,noise=alls=0.5:allf=t+u,format=yuv420p[vout]
  " -map "[vout]" \
  -c:v libx264 -preset veryfast -crf 19 -r "$FPS" -t "$DURATION" "$TMP_CLIP3"

ffmpeg -y -i "$TMP_CLIP3" -i "$AUDIO3" -c:v copy -c:a aac -b:a 256k -ar 48000 -t "$DURATION" -movflags +faststart "$VIDEO3"
rm -f "$TMP_CLIP3" "$AUDIO3"
echo "Done Sample 3: $VIDEO3"

echo "=== ALL 3 SAMPLES V2 RENDERED WITH ENHANCED EFFECTS ==="

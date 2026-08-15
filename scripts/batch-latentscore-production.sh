#!/bin/bash
set -euo pipefail

ROOT="/home/brewuser/projects/dronemill"
DURATION=60
FPS=24

mkdir -p "$ROOT/audio" "$ROOT/output"

# =========================================================================
# 1. GENERATE LATENTSCORE NEURAL AUDIO
# =========================================================================
echo "=== [1/3] Generating LatentScore Neural Audio: 3 AM Diner ==="
"$ROOT/scripts/latentscore-gen.sh" \
  "nostalgic 3am diner in heavy rain, soft neon reflections, warm lonely ambient" \
  "$ROOT/audio/latentscore_diner.wav" \
  "$DURATION"

echo "=== [2/3] Generating LatentScore Neural Audio: Conservatory ==="
"$ROOT/scripts/latentscore-gen.sh" \
  "victorian glass conservatory at twilight, quiet ancient plants, deep peaceful reverie, sacred ambient" \
  "$ROOT/audio/latentscore_conservatory.wav" \
  "$DURATION"

echo "=== [3/3] Generating LatentScore Neural Audio: Asteroid Kitchen ==="
"$ROOT/scripts/latentscore-gen.sh" \
  --preset "voyage-home-kitchen" \
  "$ROOT/audio/latentscore_asteroid.wav" \
  "$DURATION"

# =========================================================================
# 2. RENDER VIDEOS WITH LIVING OVERLAYS & LATENTSCORE SOUNDTRACKS
# =========================================================================
echo "=== Rendering LatentScore Video 1: Diner in Heavy Rain ==="
ffmpeg -y -nostdin \
  -loop 1 -framerate "$FPS" -t "$DURATION" -i "$ROOT/images/universal_diner.jpg" \
  -stream_loop -1 -i "$ROOT/assets/overlays/cinematic_rain_loop.mp4" \
  -filter_complex "
    [0:v]scale=3200:1800:force_original_aspect_ratio=increase,crop=3200:1800,zoompan=z='1.02+0.018*(0.5-0.5*cos(2*3.14159265*on/(60*${FPS})))':x='iw/2-(iw/zoom/2)+45*sin(2*3.14159265*on/(60*${FPS}))':y='ih/2-(ih/zoom/2)+10*cos(2*3.14159265*on/(60*${FPS}))':d=1:s=1920x1080:fps=${FPS},format=gbrp[base];
    [1:v]scale=1920:1080:flags=lanczos,curves=all='0/0 0.05/0 0.50/0.45 1/1',format=gbrp[rain_crisp];
    [base][rain_crisp]blend=all_mode=screen:all_opacity=0.75[merged];
    [merged]eq=contrast='1.025+0.015*sin(2*3.14159265*n/(2.8*${FPS}))':brightness='-0.005+0.008*sin(2*3.14159265*n/(1.9*${FPS}))',vignette=angle=0.32,noise=alls=0.7:allf=t+u,format=yuv420p[vout]
  " -map "[vout]" \
  -c:v libx264 -preset veryfast -crf 19 -r "$FPS" -t "$DURATION" "/tmp/clip_ls_diner.mp4"

ffmpeg -y -i "/tmp/clip_ls_diner.mp4" -i "$ROOT/audio/latentscore_diner.mastered.wav" \
  -c:v copy -c:a aac -b:a 256k -ar 48000 -t "$DURATION" -movflags +faststart \
  "$ROOT/output/latentscore-diner-sample.mp4"
rm -f "/tmp/clip_ls_diner.mp4"


echo "=== Rendering LatentScore Video 2: Conservatory ==="
ffmpeg -y -nostdin \
  -loop 1 -framerate "$FPS" -t "$DURATION" -i "$ROOT/images/universal_conservatory.jpg" \
  -stream_loop -1 -i "$ROOT/assets/overlays/dust_motes_loop.mp4" \
  -stream_loop -1 -i "$ROOT/assets/youtube-overlays/fog-overlay.mp4" \
  -filter_complex "
    [0:v]scale=3200:1800:force_original_aspect_ratio=increase,crop=3200:1800,zoompan=z='1.02+0.016*(0.5-0.5*cos(2*3.14159265*on/(60*${FPS})))':x='iw/2-(iw/zoom/2)+42*sin(2*3.14159265*on/(60*${FPS}))':y='ih/2-(ih/zoom/2)+10*cos(2*3.14159265*on/(60*${FPS}))':d=1:s=1920x1080:fps=${FPS},format=gbrp[base];
    [1:v]scale=1920:1080:flags=lanczos,curves=all='0/0 0.10/0 0.50/0.40 1/1',format=gbrp[dust_bright];
    [2:v]scale=1920:1080:flags=lanczos,curves=all='0/0 0.20/0 0.50/0.25 1/0.80',format=gbrp[fog_soft];
    [base][fog_soft]blend=all_mode=screen:all_opacity=0.30[with_fog];
    [with_fog][dust_bright]blend=all_mode=screen:all_opacity=0.85[merged];
    [merged]eq=brightness='0.008*sin(2*3.14159265*n/(3.5*${FPS}))',vignette=angle=0.32,noise=alls=0.6:allf=t+u,format=yuv420p[vout]
  " -map "[vout]" \
  -c:v libx264 -preset veryfast -crf 19 -r "$FPS" -t "$DURATION" "/tmp/clip_ls_conservatory.mp4"

ffmpeg -y -i "/tmp/clip_ls_conservatory.mp4" -i "$ROOT/audio/latentscore_conservatory.mastered.wav" \
  -c:v copy -c:a aac -b:a 256k -ar 48000 -t "$DURATION" -movflags +faststart \
  "$ROOT/output/latentscore-conservatory-sample.mp4"
rm -f "/tmp/clip_ls_conservatory.mp4"


echo "=== Rendering LatentScore Video 3: Asteroid Kitchen ==="
ffmpeg -y -nostdin \
  -loop 1 -framerate "$FPS" -t "$DURATION" -i "$ROOT/images/universal_asteroid_kitchen.jpg" \
  -stream_loop -1 -i "$ROOT/assets/youtube-overlays/fog-overlay.mp4" \
  -filter_complex "
    [0:v]scale=3200:1800:force_original_aspect_ratio=increase,crop=3200:1800,zoompan=z='1.02+0.014*(0.5-0.5*cos(2*3.14159265*on/(60*${FPS})))':x='iw/2-(iw/zoom/2)+50*sin(2*3.14159265*on/(60*${FPS}))':y='ih/2-(ih/zoom/2)+6*cos(2*3.14159265*on/(60*${FPS}))':d=1:s=1920x1080:fps=${FPS},format=gbrp[base];
    [1:v]scale=1920:1080:flags=lanczos,curves=all='0/0 0.12/0 0.45/0.25 0.80/0.70 1/0.90',format=gbrp[fog_soft];
    [base][fog_soft]blend=all_mode=screen:all_opacity=0.35[merged];
    [merged]eq=contrast='1.02+0.012*sin(2*3.14159265*n/(4.2*${FPS}))':brightness='0.006*sin(2*3.14159265*n/(2.1*${FPS}))',vignette=angle=0.35,noise=alls=0.5:allf=t+u,format=yuv420p[vout]
  " -map "[vout]" \
  -c:v libx264 -preset veryfast -crf 19 -r "$FPS" -t "$DURATION" "/tmp/clip_ls_asteroid.mp4"

ffmpeg -y -i "/tmp/clip_ls_asteroid.mp4" -i "$ROOT/audio/latentscore_asteroid.mastered.wav" \
  -c:v copy -c:a aac -b:a 256k -ar 48000 -t "$DURATION" -movflags +faststart \
  "$ROOT/output/latentscore-asteroid-kitchen-sample.mp4"
rm -f "/tmp/clip_ls_asteroid.mp4"

# =========================================================================
# 3. UPLOAD TO YOUTUBE AS UNLISTED DRAFTS
# =========================================================================
echo "=== Uploading LatentScore Sample 1: Diner ==="
"$ROOT/scripts/upload-yt.sh" \
  "$ROOT/output/latentscore-diner-sample.mp4" \
  "spinning neon in the rain | empty 3 am diner ambient | 1 minute sample" \
  "$ROOT/descriptions/midjourney-diner-sample.txt" \
  "$ROOT/images/universal_diner.jpg" \
  "unlisted" \
  "ambient,latentscore,3 am diner,rain ambient,neural music,sleep music,timeless ambience"

echo "=== Uploading LatentScore Sample 2: Conservatory ==="
"$ROOT/scripts/upload-yt.sh" \
  "$ROOT/output/latentscore-conservatory-sample.mp4" \
  "the flooded palms at twilight | victorian conservatory ambient | 1 minute sample" \
  "$ROOT/descriptions/midjourney-conservatory-sample.txt" \
  "$ROOT/images/universal_conservatory.jpg" \
  "unlisted" \
  "ambient,latentscore,conservatory,botanical,neural music,sleep music,timeless ambience"

echo "=== Uploading LatentScore Sample 3: Asteroid Kitchen ==="
"$ROOT/scripts/upload-yt.sh" \
  "$ROOT/output/latentscore-asteroid-kitchen-sample.mp4" \
  "a kitchen drifting through the asteroid winter | cozy sci-fi ambient | 1 minute sample" \
  "$ROOT/descriptions/midjourney-asteroid-galley-sample.txt" \
  "$ROOT/images/universal_asteroid_kitchen.jpg" \
  "unlisted" \
  "ambient,latentscore,sci-fi,space,cozy sci-fi,neural music,sleep music,timeless ambience"

echo "=== ALL 3 LATENTSCORE SAMPLES GENERATED, RENDERED, AND UPLOADED ==="

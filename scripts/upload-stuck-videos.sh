#!/bin/bash
# Upload the three locally rendered videos that failed previously.
# Files will be uploaded as 'private' for safety and review.

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"

echo "=== STARTING UPLOADS OF STUCK VIDEOS ==="

# 1. HMS Erebus Video
if [ -f "$ROOT/output/frozen-169-years-hms-erebus-deep-ambient-dark-arctic-drone.mp4" ]; then
  echo ""
  echo "--------------------------------------------------"
  echo "UPLOADING: HMS Erebus"
  echo "--------------------------------------------------"
  "$DIR/upload-yt.sh" \
    "$ROOT/output/frozen-169-years-hms-erebus-deep-ambient-dark-arctic-drone.mp4" \
    "frozen 169 years | hms erebus deep ambient | dark arctic drone" \
    "$ROOT/descriptions/template.txt" \
    "$ROOT/images/used/013_hms_erebus_1777731330386.png" \
    "private" \
    "arctic horror,ghost ship,pack ice,lovecraftian,ambient,cosmic horror,dark ambient,sleep ambient"
else
  echo "Skip: HMS Erebus video not found or already uploaded."
fi

# 2. Level 0 Backrooms Video
if [ -f "$ROOT/output/infinite-lobby-level-0-backrooms-ambient-yellow-wallpaper-drone.mp4" ]; then
  echo ""
  echo "--------------------------------------------------"
  echo "UPLOADING: Level 0 Backrooms"
  echo "--------------------------------------------------"
  "$DIR/upload-yt.sh" \
    "$ROOT/output/infinite-lobby-level-0-backrooms-ambient-yellow-wallpaper-drone.mp4" \
    "infinite lobby | level 0 backrooms ambient | yellow wallpaper drone" \
    "$ROOT/descriptions/level_0.txt" \
    "$ROOT/images/used/017_subglacial_cavern.png" \
    "private" \
    "subglacial,cosmic horror,crystals,lovecraftian,backrooms,level 0,liminal space,yellow rooms,fluorescent hum"
else
  echo "Skip: Level 0 Backrooms video not found or already uploaded."
fi

# 3. Poolrooms Video
if [ -f "$ROOT/output/lost-in-the-tiles-poolrooms-ambient-drone-liminal-space.mp4" ]; then
  echo ""
  echo "--------------------------------------------------"
  echo "UPLOADING: Lost in the Tiles (Poolrooms)"
  echo "--------------------------------------------------"
  "$DIR/upload-yt.sh" \
    "$ROOT/output/lost-in-the-tiles-poolrooms-ambient-drone-liminal-space.mp4" \
    "lost in the tiles | poolrooms ambient playlist | liminal space drone" \
    "$ROOT/descriptions/lost_in_the_tiles.txt" \
    "$ROOT/images/used/019_poolrooms.png" \
    "private" \
    "liminal space,poolrooms,ambient playlist,dreamcore,water soundscape,nostalgic drone"
else
  echo "Skip: Poolrooms video not found or already uploaded."
fi

echo ""
echo "=== ALL UPLOADS COMPLETED SUCCESSFULLY ==="

#!/bin/bash
set -euo pipefail

ROOT="/home/brewuser/projects/dronemill"

echo "=== Uploading Universal Ambient Sample 1: Diner ==="
"$ROOT/scripts/upload-yt.sh" \
  "$ROOT/output/universal-diner-sample.mp4" \
  "spinning neon in the rain | empty 3 am diner ambient | 1 minute sample" \
  "$ROOT/descriptions/midjourney-diner-sample.txt" \
  "$ROOT/images/universal_diner.jpg" \
  "unlisted" \
  "ambient,liminal space,3 am diner,rain ambient,diner ambient,sleep music,timeless ambience"

echo "=== Uploading Universal Ambient Sample 2: Conservatory ==="
"$ROOT/scripts/upload-yt.sh" \
  "$ROOT/output/universal-conservatory-sample.mp4" \
  "the flooded palms at twilight | victorian conservatory ambient | 1 minute sample" \
  "$ROOT/descriptions/midjourney-conservatory-sample.txt" \
  "$ROOT/images/universal_conservatory.jpg" \
  "unlisted" \
  "ambient,conservatory,dark academia,botanical,greenhouse,sleep music,timeless ambience"

echo "=== Uploading Universal Ambient Sample 3: Asteroid Kitchen ==="
"$ROOT/scripts/upload-yt.sh" \
  "$ROOT/output/universal-asteroid-kitchen-sample.mp4" \
  "a kitchen drifting through the asteroid winter | cozy sci-fi ambient | 1 minute sample" \
  "$ROOT/descriptions/midjourney-asteroid-galley-sample.txt" \
  "$ROOT/images/universal_asteroid_kitchen.jpg" \
  "unlisted" \
  "ambient,sci-fi,space,cozy sci-fi,asteroid winter,sleep music,timeless ambience"

echo "=== ALL 3 UNIVERSAL AMBIENT SAMPLES UPLOADED ==="

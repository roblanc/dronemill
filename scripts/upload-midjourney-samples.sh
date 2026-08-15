#!/bin/bash
set -euo pipefail

ROOT="/home/brewuser/projects/dronemill"

echo "=== Uploading Sample 1: Diner ==="
"$ROOT/scripts/upload-yt.sh" \
  "$ROOT/output/midjourney-diner-test-sample.mp4" \
  "spinning neon in the rain | empty 3 am diner ambient | 1 minute sample" \
  "$ROOT/descriptions/midjourney-diner-sample.txt" \
  "$ROOT/images/midjourney_diner_test.jpg" \
  "unlisted" \
  "ambient,liminal space,3 am diner,rain ambient,diner ambient,sleep music,timeless ambience"

echo "=== Uploading Sample 2: Conservatory ==="
"$ROOT/scripts/upload-yt.sh" \
  "$ROOT/output/midjourney-conservatory-test-sample.mp4" \
  "the flooded palms at twilight | victorian conservatory ambient | 1 minute sample" \
  "$ROOT/descriptions/midjourney-conservatory-sample.txt" \
  "$ROOT/images/midjourney_conservatory_test.jpg" \
  "unlisted" \
  "ambient,conservatory,dark academia,botanical,greenhouse,sleep music,timeless ambience"

echo "=== Uploading Sample 3: Asteroid Galley ==="
"$ROOT/scripts/upload-yt.sh" \
  "$ROOT/output/midjourney-asteroid-galley-test-sample.mp4" \
  "a kitchen drifting through the asteroid winter | cozy sci-fi ambient | 1 minute sample" \
  "$ROOT/descriptions/midjourney-asteroid-galley-sample.txt" \
  "$ROOT/images/midjourney_asteroid_galley_test.jpg" \
  "unlisted" \
  "ambient,sci-fi,space,cozy sci-fi,asteroid winter,sleep music,timeless ambience"

echo "=== ALL 3 SAMPLES UPLOADED AS UNLISTED DRAFTS ==="

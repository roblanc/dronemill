#!/bin/bash
set -euo pipefail
cd /home/brewuser/projects/dronemill
OUT="/DATA/Media/DroneMill ChatGPT Concepts"

node tools/chatgpt-gen.mjs "wide 16:9 aspect ratio, small cozy spacecraft kitchen with warm wood cabinets, frost-edged window overlooking a slow asteroid field, realistic practical lighting, no people, no text" "$OUT/14-asteroid-kitchen-chatgpt.png"

node tools/chatgpt-gen.mjs "wide 16:9 aspect ratio, empty early 1990s local television weather studio after broadcast, analog map panels, blank chroma wall, tungsten practical lights, realistic nostalgic photograph, no readable text, no people" "$OUT/15-rewind-season-chatgpt.png"

node tools/chatgpt-gen.mjs "wide 16:9 aspect ratio, remote desert observatory at night, blank starless sky outside, open doorway revealing constellations glowing across the interior floor, film-soft cinematic realism, no people, no text" "$OUT/16-indoor-stars-chatgpt.png"

node tools/chatgpt-gen.mjs "wide 16:9 aspect ratio, moonlit mangrove forest with several luminous tidal waterlines suspended horizontally between the roots, dark reflective water, photoreal atmosphere, no creatures, no people, no text" "$OUT/17-mangrove-waterlines-chatgpt.png"

node tools/chatgpt-gen.mjs "wide 16:9 aspect ratio, view from a warm prehistoric rock shelter across a rainy fern basin, distant ankylosaurs moving peacefully through mist, cozy fireless refuge, photoreal nature scene, no text" "$OUT/18-oldest-thunder-chatgpt.png"

echo "ALL BATCH 3 IMAGES GENERATED"
ls -la "$OUT"/*-chatgpt.png | tail -5
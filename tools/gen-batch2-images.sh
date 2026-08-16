#!/bin/bash
set -euo pipefail
cd /home/brewuser/projects/dronemill
OUT="/DATA/Media/DroneMill ChatGPT Concepts"

node tools/chatgpt-gen.mjs "wide 16:9 aspect ratio, vast windowless concrete atrium, monumental columns, impossible shafts of daylight rising from the floor, tiny empty benches for scale, photoreal architectural dread, no people, no text" "$OUT/09-atrium-chatgpt.png"

node tools/chatgpt-gen.mjs "wide 16:9 aspect ratio, extreme macro photograph of ancient compressed blue glacier ice, luminous fracture channels and trapped air bubbles, abstract geological scale, no text" "$OUT/10-blue-pressure-chatgpt.png"

node tools/chatgpt-gen.mjs "wide 16:9 aspect ratio, empty airport baggage claim, moving carousel carrying a continuous strip of sunlit summer meadow and wild grass, film-soft surreal realism, no luggage, no people, no text" "$OUT/11-baggage-claim-chatgpt.png"

node tools/chatgpt-gen.mjs "wide 16:9 aspect ratio, immense underground salt archive, pale carved shelves descending into perfectly black tidal water, dim mineral reflections, photoreal cinematic cosmic horror, no creatures, no people, no text" "$OUT/12-salt-archive-chatgpt.png"

node tools/chatgpt-gen.mjs "wide 16:9 aspect ratio, vast bright white plain under low soft clouds growing luminous roots into the earth, serene impossible landscape, pastel blue sky, no people, no text" "$OUT/13-cloud-roots-chatgpt.png"

echo "ALL BATCH 2 IMAGES GENERATED"
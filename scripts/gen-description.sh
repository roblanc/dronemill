#!/bin/bash
# Generate YouTube description via local Ollama (qwen3.5:9b).
# Takes title, outputs cosmic-horror-styled description with timestamps + hashtags.
#
# Usage: ./gen-description.sh "<title>" > descriptions/<slug>.txt
# Example: ./gen-description.sh "He Was Already Waiting Behind the Door…" > descriptions/door.txt

set -e

TITLE="$1"
MODEL="${OLLAMA_MODEL:-qwen3.5:9b}"

if [ -z "$TITLE" ]; then
  echo "Usage: $0 <title>" >&2
  exit 1
fi

if ! command -v ollama > /dev/null 2>&1; then
  echo "ERROR: ollama not installed. brew install ollama" >&2
  exit 1
fi

PROMPT="You are writing the YouTube description for a 1-hour cosmic horror ambient video. Channel: timeless ambience.

Title: \"$TITLE\"

Write a description with this exact structure:
1. Two short paragraphs (3 sentences total) painting the cosmic horror scene from the title. Lovecraftian, atmospheric, second-person where natural. No marketing fluff.
2. A 'use this for:' line listing 3-4 use cases (sleep, deep work, writing, late-night reading, etc).
3. Three timestamps in this format:
   0:00 — [evocative chapter name]
   20:00 — [evocative chapter name]
   40:00 — [evocative chapter name]
4. One short subscribe nudge line.
5. Hashtag line (8-10 lowercase hashtags relevant to title, ambient, sleep, cosmic horror, lovecraft).

Rules:
- No bullet points, no asterisks, no markdown.
- Use 🜲 (alchemy symbol) before each major section as separator.
- All hashtags lowercase, no spaces inside hashtags.
- Output description text only, no preamble, no commentary.

Begin:"

ollama run "$MODEL" "$PROMPT" 2>/dev/null

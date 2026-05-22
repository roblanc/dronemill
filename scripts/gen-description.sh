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

PROMPT="You are writing the YouTube description for a 1-hour cosmic horror / liminal space ambient video. Channel: timeless ambience.

Title: \"$TITLE\"

Write a description with this exact structure:
1. Two short paragraphs (3 sentences total) painting the scene from the title. Lovecraftian or liminal-space atmospheric, second-person where natural. No marketing fluff.
2. A 'use this for:' line listing 3-4 use cases (sleep, deep work, writing, late-night reading, study, meditation).
3. SIX timestamps in this exact format (one per line, en-dash separator), spaced every 10 minutes:
   0:00 — [evocative chapter name]
   10:00 — [evocative chapter name]
   20:00 — [evocative chapter name]
   30:00 — [evocative chapter name]
   40:00 — [evocative chapter name]
   50:00 — [evocative chapter name]
   Chapter names must be 2-5 words, sensory, escalating in unease or descent. Examples: 'Distant Hum', 'The Tiles Below', 'Submerged', 'No One Left', 'The Light Fades', 'After'. Never explain — only evoke.
4. One short subscribe nudge line (single sentence, no exclamation marks).
5. Hashtag line (8-10 lowercase hashtags relevant to title, ambient, sleep, cosmic horror, lovecraft, liminal space, dreamcore where applicable).

Rules:
- No bullet points, no asterisks, no markdown.
- Use 🜲 (alchemy symbol) before each major section as separator.
- The 0:00 chapter MUST appear and MUST be first — YouTube only parses chapters if first timestamp is 0:00.
- All hashtags lowercase, no spaces inside hashtags.
- Output description text only, no preamble, no commentary.

Begin:"

ollama run "$MODEL" "$PROMPT" 2>/dev/null

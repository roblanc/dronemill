---
name: sound-palette
description: Use whenever the user has a new sound, ambience, soundscape, lo-fi, drone, music or sound-effect idea (for Timeless Ambience / DroneMill, a video, a Short, or "a sound like X"). Scans the whole soundlab palette (own NumPy layers, Songygen Motion/Drift/Tame/Era engines, Ambient Studio rain/sea/wind, 117 drum grooves with sample kits, DroneMill, Gemini Lyria, references), proposes a recipe, and renders a seamless loop on the server.
---

# Sound palette

The tool is `/mnt/media/bob/soundlab` (read its README.md first). It runs on the server as bob.

## Every new idea

1. Scan the whole palette. Do not pick tools from memory.
   ```bash
   cd /mnt/media/bob/soundlab && python3 soundlab.py scan "<the idea in the user's words>" --seconds 60
   ```
   If the idea has an unusual word that matched nothing, also run `python3 soundlab.py palette` and `python3 soundlab.py grooves <word>`, and read them.
2. Review the draft recipe in `recipes/<slug>.json`. Edit it by hand where your judgment differs from the scorer. Look at:
   - ties between a native tool and a Songygen tool (try the other one as a variation),
   - "also consider" lines (manual tools and references),
   - key, tempo, levels (RMS dBFS), the space preset and the decade colour.
3. Show the user a table before rendering: role → chosen tool → why → the runner-up.
4. Render a 60 s preview: `python3 soundlab.py render recipes/<slug>.json --seconds 60`. Report the seam result and the loudness.
5. You cannot listen. The user judges by ear. Give the copy command with its label:

   **Run on: your Mac**
   ```bash
   scp bob@<server>:/mnt/media/bob/soundlab/out/<slug>/loop.mp3 ~/Downloads/<slug>.mp3
   ```
6. After approval, render a 3–5 minute loop (`--seconds 240`), then `longform ... --hours 2`.

## Rules

- Every Timeless Ambience loop must be seamless. Keep the seam check at PASS.
- Songygen tools (the user's friend's code) are cleared for use, monetized uploads included (`songygen_permission` in `palette.json`, 2026-10-09).
- If a kit is CC-BY (DRS studio kit), put its credit from `certificate.json` into the video description.
- When you find or build a new sound tool, add it to `palette.json` with honest tags, so the next scan sees it.
- If the shell output is lost because `/tmp` is full, redirect the output to a file under `/home/bob/.cc-out/` and read that file.

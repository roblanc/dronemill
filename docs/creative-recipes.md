# Creative Recipes

Keep successful production ideas here as modular recipes. Each recipe records
the visual source, motion method, sound engine, rejected elements, mastering, and
licensing so future batches can reuse or combine proven choices.

## Glass Hills Between Hours

- Visual concept: bright empty grassland with hills and trees made from
  translucent sparkling glass.
- Midjourney prompt: `liminal atmosphere outside a grass field with hills and trees made of sparkling glass, raw, interesting perspective, minimalistic, abstract`
- Motion source: Midjourney manual animation exported as MP4.
- Loop treatment: forward/reverse ping-pong with duplicate endpoint frames
  removed by `scripts/pingpong-loop.sh`.
- Sound engine: `musicbox` drone renderer at commit
  `8aa47f2c9083d246f4cf3232c799599f2263b75f`.
- Sound adaptation: remove Karplus-Strong plucks; retain bass, filtered mids,
  high oscillator layer, and Dattorro plate reverb; high-pass at 170 Hz.
- Rejected elements: continuous pink/white noise, synthetic wind, birds,
  literal glass effects, and wooden/plucked transients.
- Long form: render unique continuous audio for the full duration; repeat only
  the visual ping-pong cycle.
- Thumbnail: use a clean representative frame from the video with no text,
  borders, overlays, or additional design treatment.
- Master: 48 kHz stereo, target `-24 LUFS`, AAC 192 kb/s for production.
- License: musicbox Copyright 2026 Ben Askins, CC BY-SA 4.0. Attribute, link the
  source/license, identify modifications, and share the adaptation alike.

## Combination Ideas

- Reuse the no-pluck musicbox palette with empty pools, synthetic gardens, or
  impossible daylight architecture.
- Combine restrained ping-pong motion with slow scene-level camera breathing,
  but do not stack both when the source animation already moves the camera.
- Use LatentScore for prompt-conditioned harmonic variation, then compare it
  against no-pluck musicbox before choosing a production bed.
- Keep environmental layers optional. Silence and clean harmonic space are
  preferable to generic noise when the image does not imply an audible source.

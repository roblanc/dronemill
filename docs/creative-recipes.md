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
- Select title grammar and clean/analog packaging by mood using
  `docs/title-and-visual-packaging.md`; do not apply VHS treatment globally.

## The Greenhouse After Rain

- Visual concept: an empty municipal greenhouse after rain, with a centered wet
  walkway, dense plants, one weathered bench, and violet-coral dawn light.
- Visual source: user-supplied Midjourney still, 1456x816.
- Motion treatment: an extremely restrained camera breath for evaluation;
  prefer scene-level condensation and leaf motion if an animated source arrives.
- Sound engine: `scripts/greenhouse-audio.sh`, using a warm C major/add-nine
  palette with slow independent continuous partials.
- Rejected elements: continuous rain, generic noise, birds, water-drop samples,
  beeps, blips, isolated transients, dark sub-drone, and the Glass Hills
  musicbox palette.
- Master: 48 kHz stereo, target `-24 LUFS`, with generous true-peak headroom.
- Review sample: 90 seconds; render unique continuous audio for production.
- Packaging: clean or very light film-soft treatment, no VHS decay.

## Scene-Authored Continuous Sound

The renderer `scripts/scene-sound-v2.sh` builds complex environments from
continuous layers only. Each layer has its own deterministic seed, frequency
range, spatial position, and slow non-matching envelope. This creates motion and
depth without beeps, blips, chimes, isolated impacts, or random one-shot events.

### Noonbloom

- Ground layer: low wind pressure following the white terrain.
- Body layer: plant-height pink-noise wind with restrained stereo width.
- Air layer: high, diffuse movement above the flowers.
- Material layer: a continuous narrow-band membrane resonance suggesting
  translucent petals under tension, never a struck or chiming sound.
- Harmony: an uneasy F-sharp Lydian/add-nine field whose partials breathe on
  independent 61- to 97-second cycles.
- Master: target `-22 LUFS`, LRA 10, true peak below `-3 dBFS`.

### The Tide That Climbed Into the Sky

- Ground layer: submerged low pressure beneath the shoreline.
- Shore layer: ordinary horizontal surf with two overlapping swell periods.
- Vertical layer: broad upper-frequency water movement assigned to the wall.
- Mass layer: darker mid-band turbulence moving on much longer cycles.
- Harmony: unresolved A-based low architecture with no horn, creature, impact,
  crack, or discrete wave event.
- Master: target `-20 LUFS`, LRA 11, true peak below `-2.5 dBFS`.

### Orbital Ceramics Workshop

- Hull layer: low structural transfer through the habitat.
- Ventilation layer: stable room-scale airflow.
- Convection layer: continuous upper movement from kiln heat.
- Kiln layer: warm filtered combustion resonance without pops or tool sounds.
- Harmony: C major/add-nine field with gentle chorus and slow orbital-scale
  balance changes; no machinery alerts or pottery handling effects.
- Master: target `-21 LUFS`, LRA 9, true peak below `-3 dBFS`.

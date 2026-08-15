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

For every video, the primary sound must be a refined, fluid, deliberately voiced
ambient musical composition that feels human-authored. Nature noise, weather,
room tone, ventilation, machinery, and other scene-implied textures are quiet
supporting beds only; they must not overpower or substitute for the music.

Use the Lighthouse production as the preferred reference architecture: a
prompt-conditioned LatentScore dark-ambient composition carries the experience,
with restrained scene-specific texture mixed beneath it. Adapt the musical prompt
toward cosmic, anti-cosmic, ethereal, warm, or abyssal character as the image
requires. Do not replace this authored bed with bare oscillator chords.

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

## Midjourney-Aesthetic ChatGPT (DALL-E 3) Prompt Framework

When generating images via ChatGPT/CDP, adhere strictly to this formula to avoid the plastic/airbrushed CGI look and achieve Midjourney-level photographic texture:

1. **Ban AI "Quality" Buzzwords**: Never use `photorealistic`, `hyperrealistic`, `8k`, `4k`, `Unreal Engine`, or `masterpiece`.
2. **Specify Optical & Lens Specs**:
   - Film stocks: `Kodak Portra 400` (warmth/earth tones), `Cinestill 800T` (night/tungsten/neon halation), `Fujifilm Superia` (documentary cool greens/blues).
   - Lenses: `35mm f/1.4`, `Leica M6 50mm rangefinder`, `35mm anamorphic prime lens`.
3. **Demand Physical Imperfections**: `natural film grain`, `unretouched documentary still`, `dust motes catching light beams`, `weathered paint patina`, `scratched stainless steel`.
4. **Direct Lighting Physically**: Describe light sources and angles directly (`overhead single fluorescent tube`, `low-angle golden afternoon sunlight`, `tungsten pendant lamps reflecting off fogged wet glass`).
5. **Template**:
   `A 16:9 widescreen raw 35mm film photograph of [SUBJECT / SCENE]. Environment: [Atmosphere, textures, decay]. Lighting: [Light sources, shadow depth]. Optics: Shot on [Film Stock], [Lens/Camera], shallow depth of field, subtle film grain, unretouched analog photograph.`

## Living Scene Particle Overlays

1. **Cinematic Rain Overlay** (`assets/overlays/cinematic_rain_loop.mp4`):
   - Multi-depth 1,400 motion-blurred rain streaks angled at 18° across 10 depth layers.
   - Blend: `blend=all_mode=screen:all_opacity=0.75` for bold, clearly visible rain falling against dark/neon environments.
   - Accompany with cyclic neon ambient reflection breathing (`eq=contrast=...:brightness=...`).
2. **Floating Dust Motes & Twilight Mist**:
   - Golden dust motes (`assets/overlays/dust_motes_loop.mp4`) at `85%` opacity combined with rolling fog (`assets/youtube-overlays/fog-overlay.mp4`) at `30%` opacity + lantern glow pulse.
3. **Deep Space Nebula Drift**:
   - Space dust/nebula overlay at `35%` opacity with subtle instrument indicator light pulsing.

## AI Hybrid Multi-Engine Sound Orchestration Standard

All DroneMill audio productions now operate on the **AI Hybrid Orchestration Engine** (`scripts/ai_hybrid_sound_conductor.py`). Instead of relying on a single synthesizer or sample bed, the AI Conductor combines 2 to 5 specialized engines to build multi-dimensional soundscapes with dedicated frequency allocations:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   HYBRID FREQUENCY & ENGINE MAPPING                    │
├──────────────────────┬─────────────────────────────────────────────────┤
│ Sub Bass (< 80 Hz)   │ Rubberband Phase-Vocoder Sub-Octave Drone       │
│ Harmonic Mid Body    │ LatentScore Prompt-Conditioned Neural Pad       │
│ 3D Stereo Shimmer    │ Procedural FFmpeg DSP (Haas delay + prime LFOs) │
│ Environmental World  │ Multi-Layer Acoustic Foley & Room Resonance     │
│ Harmonic Conductor   │ AI Director (AGY) Key & Mode Locking (-22 LUFS) │
└──────────────────────┴─────────────────────────────────────────────────┘
```

### Supported Multi-Engine Modes:
1. **Duo (2 Engines)**: Minimalist emotional pairing (e.g., LatentScore Neural chords + Multi-layer rain/wind foley).
2. **Trio (3 Engines)**: Expansive space / isolation (e.g., LatentScore space pad + 3D Haas DSP sine shimmer + Rubberband sub-drone).
3. **Full 5-Engine Ensemble**: Cinematic world-building (AI Director harmonic map + LatentScore + Foley + DSP 3D shimmers + Sub-octave Rubberband rumble).
4. **Lovecraftian / Cosmic Dread**: C#/G#/D Locrian/Phrygian harmonic map + bowed metal LatentScore + cavern/ocean foley + sub-harmonic DSP + sub-45Hz pitch-shifted shudder.
5. **Liminal Space / Dreamcore**: E Dorian / pentatonic map + decaying electric piano LatentScore + poolroom/fluorescent foley + stereo sine shimmers + sub-octave room resonance.

## New Aesthetic Universes (Prompt & Sonic Formulas)

### 1. Deep Trench Research Station (Marianas Abyss)
* **Visual Formula:**
  `Authentic 35mm film photograph looking out the reinforced titanium viewport of a deep-sea benthic research lab at 8,000 meters depth. Floodlights illuminating jagged hydrothermal chimney vents and ghostly translucent abyssal siphonophores drifting in the pitch black water. Condensation on thick quartz glass, glowing control consoles, Kodak Portra 800, textless, no lettering.`
* **Hybrid Sound Design:**
  - *Key/Mode:* Eb Phrygian ($38.89\text{ Hz}$ fundamental).
  - *Foley:* Submerged water pressure hum, hydrothermal vent hiss, metal hull groaning.
  - *DSP:* Prime-cycle spatialized sine pings with long reverb tails ($47\text{s}, 71\text{s}, 97\text{s}$).
  - *Rubberband:* $0.45\times$ pitch-shifted tectonic trench rumble ($<35\text{ Hz}$).

### 2. Submerged Brutalist Megastructures
* **Visual Formula:**
  `Monumental architectural photograph of a massive brutalist concrete dam intake tower half-submerged in dark emerald reservoir water under an overcast gray sky. Impossibly vast concrete geometry, rusted iron floodgate mechanisms, silent mountain reflections, cold cinematic minimalism, 35mm film grain, textless.`
* **Hybrid Sound Design:**
  - *Key/Mode:* D Minor / Low 5ths ($73.42\text{ Hz}, 110.00\text{ Hz}$).
  - *Foley:* Deep water spillway suction, mountain wind howling through concrete tunnels.
  - *DSP:* Haas 3D stereo harmonic overtones on prime breathing cycles.
  - *Rubberband:* Sub-octave heavy concrete vibration drone.

### 3. Winter Alpine Solitude (The High Hearth)
* **Visual Formula:**
  `Cozy 35mm film photograph inside a heavy timber-and-granite mountain cabin during a fierce alpine snowstorm at twilight. Crackling stone fireplace casting warm amber light on a wool blanket and antique wooden bookshelves, frosted multi-pane window framing jagged snow-covered peaks, unretouched analog film warmth, textless.`
* **Hybrid Sound Design:**
  - *Key/Mode:* G Major / Lydian ($98.00\text{ Hz}, 146.83\text{ Hz}, 196.00\text{ Hz}, 246.94\text{ Hz}$).
  - *Foley:* Crackling pine fire embers, howling alpine blizzard outside.
  - *DSP:* 3D stereo acoustic warmth oscillators with soft prime-period tremolo.
  - *Rubberband:* Low hearth resonant warmth ($55\text{ Hz}$).



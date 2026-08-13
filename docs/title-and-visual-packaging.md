# Title and Visual Packaging

Choose the title family from the emotional premise of the video. Do not force
every release into the same search-oriented structure, and do not copy another
channel's exact wording, Unicode typography, symbols, or thumbnail lockups.

## Title Families

### Counterfactual Memory

Use for nostalgic places where the emotional hook is absence or lost time.

Pattern:

`you [returned/reached/remembered] [a place or time], but [contradiction]`

Examples:

- `you went back to the past, but no one was there | liminal nostalgia ambient`
- `you reached the beginning of the past, but time had moved on | dreamcore ambient`
- `you returned before the memory happened | emptycore for sleep`

The sentence is the main hook. Add only one short searchable suffix when useful.

### Impossible Memory

Use for dreamcore, surreal landscapes, and scenes that feel remembered but
could not have existed.

Pattern:

`a/the [memory/place/object] that [impossible predicate]`

Examples:

- `a summer evening that never happened | nostalgic ambient`
- `the greenhouse that remembered the rain | liminal soundscape`
- `a signal from a future we abandoned | deep ambient`

### Second-Person Scene

Use when the visual offers a clear destination or event and immersion is more
important than naming the genre.

Pattern:

`you [enter/wake/arrive/return] [impossible scene]`

Examples:

- `you wake beneath clear ice | glacial ambient for sleep`
- `you enter the last observatory | cosmic ambient`

Reserve `pov:` for scenes that genuinely present a first-person viewpoint.

### Minimal State

Use only when the thumbnail is unusually legible and distinctive. The period is
part of the found-label tone.

Examples:

- `life is good.`
- `liminal emptycore.`
- `blessmaxing.`
- `afterlight.`
- `whiteout.`

Invented `-core` terms should express a recognizable emotional idea, not act as
random decoration. Pair a minimal title with a clear description and tags.

### Functional Radio

Use for actual streams, very long compilations, or recurring programmed series.
Do not call a finite upload `24/7`.

Examples:

- `liminal space radio | dreamcore for sleep and relaxation`
- `midnight weather radio | dark ambient for sleep`

Use `24/7` only when the stream is continuously live and maintained as such.

### Searchable Environmental

Use for cinematic scenes, horror, weather, historical subjects, and releases
where search clarity matters more than an intimate narrative voice.

Pattern:

`[evocative hook] | [environment and genre] | [duration or use]`

Examples:

- `lighthouse through midnight fog | stormy ocean dark ambient | 2 hours`
- `glass hills between hours | liminal ambient | dreamcore soundscape`

## Selection Rules

- Nostalgic domestic or public space: counterfactual memory.
- Serene surreal or dreamcore scene: impossible memory.
- Strong first-person destination: second-person scene.
- Exceptional, instantly readable thumbnail: minimal state.
- Live or programmed long-form stream: functional radio.
- Historical, cinematic, environmental, or horror subject: searchable environmental.
- Keep titles primarily lowercase and ASCII for search, accessibility, automation,
  and consistent rendering.
- Use at most one decorative device: a period, one symbol pair, or one suffix.
- Avoid blank titles, mathematical Unicode alphabets, arbitrary years, and genre
  keyword chains.
- Keep most titles below roughly 85 characters. Longer sentence titles must earn
  the space through a strong narrative hook.

## Visual Packaging

Use analog treatment selectively. Clean pastoral, botanical, aquatic, and bright
surreal scenes should usually remain clean. Cassette/VHS language best supports
domestic nostalgia, old offices, malls, recorded broadcasts, and corrupted
memories.

### Clean

- One clear subject or impossible element.
- No text by default.
- Restrained motion and high small-screen legibility.
- No generic grain, scanlines, fog, or chromatic offset.

### Film Soft

- Fine luma grain and very light highlight bloom.
- Minimal vignette and sub-pixel gate weave.
- No scanlines, tearing, timestamps, or tape dropouts.
- Suitable for warm memory, botanical scenes, and gentle dreamcore.

### VHS Memory

- Mild horizontal softness and chroma blur.
- Slow chroma displacement below roughly one pixel most of the time.
- Tiny gate weave, weak exposure drift, and sparse dropout bands.
- Occasional low-opacity disturbance near the bottom edge.
- No permanent scanlines or digital block glitches.
- Suitable for period interiors, malls, offices, and home-video memory.

### VHS Decay

- Use only for corrupted memory or weirdcore.
- Start from VHS Memory, then add rare line displacement, desaturation events,
  and very occasional sync instability.
- Keep failures episodic; constant heavy degradation becomes a decorative filter.

Apply analog processing after scene motion and environmental compositing, but
before final downsampling and encoding. Use deterministic seeds, cycles of at
least five minutes, and no obvious failure event near a loop boundary.

## Reference Boundary

The useful inspiration from `aurora.heaven` is the match between emotional
premise, title grammar, thumbnail composition, and degree of image degradation.
Do not reproduce its exact Unicode title style, symbol patterns, eye motifs,
traumacore text layouts, blank titles, cassette frames, or individual wording.

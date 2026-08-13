# Liminal Sound Design

Liminal-space audio is not one fixed genre. The useful design principle is to
make a familiar place feel vacant, temporally uncertain, or causally incomplete.
The soundtrack should support ambiguity rather than automatically turning every
scene into horror.

## Pastoral Liminality

Bright outdoor scenes need a different palette from Backrooms interiors:

- Start with substantial empty space. Add environmental sound only when the
  image specifically needs it; synthetic noise beds easily become distracting.
- Use a restrained suspended major, add-nine, or Lydian harmony without a clear
  cadence.
- Keep events sparse and irregular. A constant sparkle layer stops feeling
  special and becomes decorative ambience.
- Suggest ecological absence with one remote call that receives no answer,
  rather than a complete dawn chorus.
- Introduce subtle causal errors, such as wind briefly disappearing while the
  landscape continues moving or a distant resonance sounding unnaturally clear.
- Preserve dynamics and long gaps. Do not force every moment to the foreground.

Avoid ominous sub-drones, monster cues, corridor reverbs, generic sad piano,
continuous vinyl crackle, detuned music boxes, and literal glass chimes on every
visual sparkle. Those choices explain the intended emotion too directly or imply
an indoor horror setting.

For the Midjourney glass landscape, target roughly 70 percent serene wonder, 20
percent solitude, and 10 percent beautiful impossibility. The current generator
uses clean open D Lydian/add-nine color and a sparse, incomplete melodic phrase.
It deliberately contains no continuous noise, synthetic wind, bird effects, or
low drone, and targets `-24 LUFS` so quiet material remains quiet.

## References

- [The Pleasant Head Trip of Liminal Spaces](https://www.newyorker.com/culture/rabbit-holes/the-pleasant-head-trip-of-liminal-spaces)
- [The Eerie Comfort of Liminal Spaces](https://www.theatlantic.com/culture/archive/2022/11/liminal-space-internet-aesthetic/671945/)
- [Boards of Canada's Music Has the Right to Children](https://pitchfork.com/features/article/why-boards-of-canadas-music-has-the-right-to-children-is-the-greatest-psychedelic-album-of-the-90s/)
- [Hauntology: The Past Inside the Present](https://rougesfoam.blogspot.com/2009/10/hauntology-past-inside-present.html)
- [Kankyo Ongaku: Japanese Ambient, Environmental and New Age Music 1980-1990](https://kankyongaku.bandcamp.com/album/kanky-ongaku-japanese-ambient-environmental-new-age-music-1980-1990)
- [Hiroshi Yoshimura: GREEN](https://hiroshiyoshimura.bandcamp.com/album/green)
- [Belbury Poly: The Willows](https://ghostbox.greedbag.com/buy/the-willows-0/)

## Generator Evaluation

The following projects were checked for actual export support and licensing. A
public GitHub repository is not automatically open-source or safe for monetized
video.

| Project | Status for DroneMill | Notes |
| --- | --- | --- |
| [LatentScore](https://github.com/prabal-rje/latentscore) | Primary engine | Apache-2.0, CPU-only procedural WAV generation, already integrated. Text selects a procedural configuration; it is not neural text-to-waveform synthesis. |
| [musicbox](https://github.com/benaskins/musicbox) | Candidate for A/B tests | Sample-free Rust synthesis and arbitrary-duration WAV rendering. Repository is CC BY-SA 4.0, so attribution and ShareAlike implications must be resolved before publication. |
| [ambient-gen](https://github.com/beowulf-audio/ambient-gen) | Conditional | Exports MIDI and MP3, but generation is TUI-driven and bundled soundfonts have separate licensing. Use only an independently reviewed soundfont. |
| [focusmusic](https://github.com/petrbrzek/focusmusic) | Not yet | Real-time procedural playback without an offline renderer. It claims MIT in metadata but has no license file. |
| [AmbientGarden](https://github.com/pac-dev/AmbientGarden) | Reference only | Useful procedural patch design, but no repository license. |
| [AmbientGardenAlbum](https://github.com/pac-dev/AmbientGardenAlbum) | Reference only | Rebuilds an authored album and has no repository license; it is not a general soundtrack generator. |
| [Moodist](https://github.com/remvze/moodist) | Do not integrate | Soundboard rather than music generator. Bundled recordings use asset-specific licenses and it has no mix exporter. |
| [Space](https://github.com/spitlo/space) | Do not integrate | No license, sample-based, and no implemented audio export. |
| [ambient_music_generator](https://github.com/timothymeehan/ambient_music_generator) | Do not integrate | Unlicensed, obsolete SampleRNN stack that requires training audio and introduces source-copyright risk. |
| [AudioCraft](https://github.com/facebookresearch/audiocraft) | Do not use released weights | Framework code is MIT, but Meta's released MusicGen weights are CC BY-NC 4.0 and unsuitable for monetized YouTube output. |

Preferred next experiment: render several `musicbox` samples locally and compare
their musical vocabulary with LatentScore and the current procedural generator.
Do not publish those renders until the CC BY-SA obligations have been reviewed.

The approved evaluation removes `musicbox`'s Karplus-Strong pluck layer while
retaining its bass, filtered mids, high oscillator layer, and plate reverb. Render
a continuous two-hour master and combine it with a prepared ping-pong cycle:

```bash
./scripts/musicbox-no-pluck.sh output/liminal-musicbox-2h.wav 7200
./scripts/pingpong-production.sh output/liminal-pingpong.cycle.mp4 \
  output/liminal-musicbox-2h.wav output/liminal-musicbox-2h.mp4 7200
```

`musicbox` is Copyright 2026 Ben Askins and licensed CC BY-SA 4.0. The no-pluck
adaptation and resulting evaluation output must retain attribution, link the
license and source, identify the modification, and be shared under CC BY-SA 4.0.

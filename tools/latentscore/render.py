import argparse
import json
from pathlib import Path

import latentscore as ls

PRESETS = {
    # ── Demo site presets ──
    "deep-ocean": "dark ambient underwater cave with bioluminescence",
    "frozen-memory": "nostalgic winter reverence",
    "zen-garden": "peaceful meditation in a zen garden",
    "deep-space": "floating through deep space surrounded by stars cosmic ambient",
    "midnight-rain": "The scene captures the stillness before the storm.",
    "respect-mystery": "Respect mystery.",
    "treasured-object": "Tension over a treasured object.",
    "bittersweetness": "Bittersweetness spreads.",
    "stars-and-shore": "Stars lesson and beach yearning.",
    "final-thanks": "Final thanks and optimism.",
    "healing-music": "healing music",
    "neon-city": "cyberpunk nightclub in tokyo",
    # ── DroneMill themed variations ──
    "liminal-corridor": "an endless empty corridor of the same door repeating, dim fluorescent hum, dreamlike liminal space",
    "drowned-lighthouse": "the last lighthouse on a drowned planet, cosmic loneliness, slow waves of starlight",
    "fern-valley-rain": "warm first rain in a prehistoric fern valley, a small creature sheltering, ancient comfort",
    "black-tide-circle": "something immense circling beneath black midnight water, slow horror, vast pressure",
    "voyage-home-kitchen": "a small warm spacecraft kitchen during the long voyage home, soft hum of the habitat",
}

DARK = dict(
    tempo="very_slow",
    brightness="very_dark",
    space="vast",
    density=2,
    motion="slow",
    stereo="wide",
    echo="heavy",
    depth=False,
    chord_change_bars=8192,
)

DRONE = dict(
    bass="drone",
    pad="dark_sustained",
    rhythm="none",
    texture="pad_whisper",
    melody_density=0.0,
    melody="procedural",
    accent="none",
    register_min_oct=1,
    register_max_oct=4,
)


def parse_override(kv):
    k, v = kv.split("=", 1)
    if k in ("density", "phrase_len_bars", "chord_change_bars", "register_min_oct", "register_max_oct"):
        return k, int(v)
    if k in ("melody_density", "motif_repeat_prob", "chromatic_prob", "cadence_strength", "syncopation", "swing", "step_bias"):
        return k, float(v)
    return k, v


def build_update(args, preset_name):
    parts = {}
    if not args.force_natural:
        parts.update(DARK)
    if not args.force_natural and (args.no_lead or preset_name is not None):
        parts.update(DRONE)
    for kv in args.sets:
        k, v = parse_override(kv)
        parts[k] = v
    if not parts:
        return None
    return ls.MusicConfigUpdate(**parts)


def main():
    parser = argparse.ArgumentParser(description="Render title-conditioned ambient audio.")
    parser.add_argument("prompt", nargs="?", default=None,
                        help="Free-text vibe prompt (required unless --preset is used)")
    parser.add_argument("output", help="Output WAV path")
    parser.add_argument("--duration", type=float, default=180)
    parser.add_argument("--preset", default=None,
                        help="Named preset from the demo site; uses the preset's own vibe")
    parser.add_argument("--update", dest="force_update", action="store_true",
                        help="Force the DroneMill dark-ambient config update")
    parser.add_argument("--natural", dest="force_natural", action="store_true",
                        help="Use the vibe's own derived config, no update")
    parser.add_argument("--no-lead", dest="no_lead", action="store_true",
                        help="Suppress the melodic lead voice and accents (ambient only)")
    parser.add_argument("--set", dest="sets", action="append", default=[], metavar="key=value",
                        help="Override an arbitrary MusicConfig field (repeatable)")
    args = parser.parse_args()

    preset_name = None
    if args.preset:
        if args.preset not in PRESETS:
            raise SystemExit(
                f"unknown preset '{args.preset}'. Choose from: {', '.join(PRESETS)}"
            )
        prompt = PRESETS[args.preset]
        preset_name = args.preset
    else:
        prompt = args.prompt
        if not prompt:
            parser.error("either <prompt> or --preset is required")

    update = build_update(args, preset_name)

    audio = ls.render(prompt, update=update, duration=args.duration)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    audio.save(str(output))

    metadata = {
        "prompt": prompt,
        "preset": preset_name,
        "duration_seconds": args.duration,
        "sample_rate": ls.SAMPLE_RATE,
        "generator": "latentscore 0.1.8",
        "reproducible": False,
        "update_applied": update is not None,
        "no_lead": bool(update is not None and update.melody_density == 0.0),
        "register_max_oct": getattr(update, "register_max_oct", None),
    }
    output.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata))


if __name__ == "__main__":
    main()
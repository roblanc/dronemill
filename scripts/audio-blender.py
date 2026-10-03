#!/usr/bin/env python3
"""Profile-aware ambient stem blender.

Creates one unique long-form bed from safe local stems in audio/samples/
and owned original stems in audio/owned/.
Writes:
  - audio/queue/<name>.mp3
  - audio/recipes/<name>.json
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "audio" / "samples"
OWNED = ROOT / "audio" / "owned"
MANIFEST = SAMPLES / "samples_manifest.json"
OWNED_SOURCES = ROOT / "owned_sources.json"
QUEUE = ROOT / "audio" / "queue"
RECIPES = ROOT / "audio" / "recipes"

PROFILE_KEYWORDS = {
    "backrooms": ["backrooms", "escalator", "parking", "server", "synth_cold", "hospital"],
    "mall": ["mall", "supermarket", "hotel", "lobby", "laundromat", "office", "synth_warm"],
    "terminal": ["airport", "train", "metro", "station", "night_drive", "rain"],
    "poolrooms": ["pool", "aquarium", "bathroom", "cave", "ethereal", "rain"],
    "server": ["server", "machine", "escalator", "elevator", "synth_pulse", "office"],
    "arctic": ["wind", "cave", "rain", "void", "synth_cold", "ethereal"],
    "harbor": ["cosmic", "wind", "rain", "cave", "void", "ethereal"],
    "void": ["void", "cosmic", "dread", "church", "cave", "synth_void"],
}


def slug_text(item: dict) -> str:
    return f"{item.get('file', '')} {item.get('slug', '')} {item.get('theme', '')}".lower()


def load_manifest() -> list[dict]:
    items: list[dict] = []
    if MANIFEST.exists():
        with MANIFEST.open("r", encoding="utf-8") as f:
            data = json.load(f)
        items = [
            {**x, "path": str(SAMPLES / x.get("file", ""))}
            for x in data
            if (SAMPLES / x.get("file", "")).exists()
        ]
        if items:
            return items

    return [
        {"file": p.name, "path": str(p), "slug": p.stem, "theme": p.stem, "source": "local"}
        for p in sorted(SAMPLES.glob("*.mp3"))
    ]


def load_owned_sources() -> dict[str, dict]:
    if not OWNED_SOURCES.exists():
        return {}
    with OWNED_SOURCES.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        return {}
    return {str(item.get("id", "")): item for item in data if item.get("id")}


def load_owned_stems() -> list[dict]:
    source_meta = load_owned_sources()
    items = []
    for p in sorted(OWNED.glob("*.mp3")):
        video_id = next(
            (source_id for source_id in source_meta if p.name.startswith(f"{source_id}_")),
            p.name.split("_", 1)[0],
        )
        meta = source_meta.get(video_id, {})
        profile = meta.get("profile", "")
        title = meta.get("title", p.stem)
        items.append({
            "file": p.name,
            "path": str(p),
            "slug": p.stem,
            "theme": f"{profile} {title}".strip(),
            "source": meta.get("rights", "owned-original"),
            "owned_id": video_id,
            "owned_profile": profile,
            "title": title,
        })
    return items


def load_items(include_owned: bool = True) -> list[dict]:
    items = load_manifest()
    if include_owned:
        items.extend(load_owned_stems())
    return items


def score_item(item: dict, profile: str) -> int:
    text = slug_text(item)
    keywords = PROFILE_KEYWORDS.get(profile, PROFILE_KEYWORDS["void"])
    score = sum(1 for k in keywords if k in text)
    if item.get("owned_profile") == profile:
        score += 3
    if item.get("source") == "owned-original":
        score += 1
    return score


def choose_stems(items: list[dict], profile: str, rng: random.Random, count: int) -> list[dict]:
    buckets: dict[int, list[dict]] = {}
    for item in items:
        buckets.setdefault(score_item(item, profile), []).append(item)

    picked: list[dict] = []
    for score in sorted(buckets, reverse=True):
        pool = buckets[score]
        rng.shuffle(pool)
        for item in pool:
            if item not in picked:
                picked.append(item)
            if len(picked) >= count:
                return picked
    return picked


def layer_settings(profile: str, idx: int, rng: random.Random) -> dict:
    # idx 0 = dominant bed. Others are quieter supports.
    if idx == 0:
        vol = rng.uniform(0.62, 0.82)
        hp = rng.randint(20, 45)
        lp = rng.randint(4500, 9000)
    else:
        vol = rng.uniform(0.08, 0.34) / idx
        hp = rng.choice([30, 45, 70, 110, 180])
        lp = rng.choice([900, 1400, 2200, 3200, 4800, 7200])

    if profile in {"void", "arctic"}:
        hp = min(hp, 70)
        lp = min(lp, 4800)
    elif profile in {"poolrooms", "terminal"}:
        lp = max(lp, 3000)
    elif profile == "server":
        hp = max(hp, 45)
        lp = min(max(lp, 1400), 4200)

    return {
        "volume": round(vol, 3),
        "highpass": hp,
        "lowpass": lp,
        "delay_ms": rng.choice([0, 1500, 3000, 5000, 8000, 13000]) if idx else 0,
    }


def build_ffmpeg(stems: list[dict], settings: list[dict], out: Path, duration: int, profile: str) -> list[str]:
    cmd = ["ffmpeg", "-y", "-nostdin"]
    for stem in stems:
        cmd.extend(["-stream_loop", "-1", "-i", stem["path"]])

    parts = []
    labels = []
    fade_out_start = max(0, duration - 12)
    for idx, layer in enumerate(settings):
        label = f"a{idx}"
        labels.append(f"[{label}]")
        delay = layer["delay_ms"]
        parts.append(
            f"[{idx}:a]"
            "aformat=sample_rates=44100:channel_layouts=stereo,"
            f"volume={layer['volume']},"
            f"highpass=f={layer['highpass']},"
            f"lowpass=f={layer['lowpass']},"
            f"adelay={delay}|{delay},"
            "afade=t=in:st=0:d=10,"
            f"afade=t=out:st={fade_out_start}:d=12,"
            f"apad=pad_dur={duration}"
            f"[{label}]"
        )

    if profile in {"void", "arctic", "harbor"}:
        echo = "aecho=0.8:0.55:2200|5200:0.28|0.16,"
        master_lp = "lowpass=f=5200,"
    elif profile == "poolrooms":
        echo = "aecho=0.8:0.6:1100|2700|5300:0.45|0.25|0.12,"
        master_lp = "lowpass=f=7600,"
    else:
        echo = "aecho=0.8:0.45:1300|3400:0.30|0.14,"
        master_lp = "lowpass=f=6400,"

    parts.append(
        "".join(labels)
        + f"amix=inputs={len(stems)}:duration=longest:dropout_transition=0:normalize=0,"
        f"{echo}{master_lp}"
        "acompressor=threshold=0.22:ratio=3:attack=200:release=900,"
        "loudnorm=I=-18:TP=-2.0:LRA=11"
        "[out]"
    )

    cmd.extend([
        "-filter_complex",
        ";".join(parts),
        "-map",
        "[out]",
        "-t",
        str(duration),
        "-c:a",
        "libmp3lame",
        "-b:a",
        "192k",
        str(out),
    ])
    return cmd


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", nargs="?", default="auto")
    parser.add_argument("name", nargs="?", default=None)
    parser.add_argument("--duration", type=int, default=3600)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--stems", type=int, default=4)
    parser.add_argument("--no-owned", action="store_true", help="ignore audio/owned stems")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    seed = args.seed if args.seed is not None else int(time.time()) ^ random.randint(0, 999999)
    rng = random.Random(seed)
    profile = args.profile if args.profile != "auto" else rng.choice(sorted(PROFILE_KEYWORDS))
    name = args.name or f"blend_{profile}_{seed}"

    items = load_items(include_owned=not args.no_owned)
    if not items:
        raise SystemExit("No audio stems found in audio/samples or audio/owned")
    count = min(max(args.stems, 2), 6, len(items))
    stems = choose_stems(items, profile, rng, count)
    settings = [layer_settings(profile, i, rng) for i in range(len(stems))]

    QUEUE.mkdir(parents=True, exist_ok=True)
    RECIPES.mkdir(parents=True, exist_ok=True)
    out = QUEUE / f"{name}.mp3"
    recipe = RECIPES / f"{name}.json"

    recipe_data = {
        "name": name,
        "profile": profile,
        "seed": seed,
        "duration": args.duration,
        "output": str(out.relative_to(ROOT)),
        "stems": [
            {
                "file": stem["file"],
                "path": str(Path(stem["path"]).relative_to(ROOT)),
                "theme": stem.get("theme", ""),
                "source": stem.get("source", ""),
                "owned_id": stem.get("owned_id", ""),
                **settings[idx],
            }
            for idx, stem in enumerate(stems)
        ],
    }

    if args.dry_run:
        print(json.dumps(recipe_data, indent=2))
        return 0

    cmd = build_ffmpeg(stems, settings, out, args.duration, profile)
    print(f">> Blending {len(stems)} stems -> {out.relative_to(ROOT)} (profile={profile}, seed={seed})")
    for stem, layer in zip(stems, settings):
        print(
            f"   - {Path(stem['path']).relative_to(ROOT)} vol={layer['volume']} "
            f"hp={layer['highpass']} lp={layer['lowpass']} delay={layer['delay_ms']}ms"
        )
    subprocess.run(cmd, check=True)

    with recipe.open("w", encoding="utf-8") as f:
        json.dump(recipe_data, f, indent=2)
    print(f"Done -> {out.relative_to(ROOT)}")
    print(f"Recipe -> {recipe.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

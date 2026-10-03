#!/usr/bin/env python3
"""Keep Dronemill runnable without manual file moving.

Ensures active thumbnail stock and unprocessed queue rows exist. It promotes
backup images first; if none exist, it creates a simple procedural thumbnail.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMAGES_QUEUE = ROOT / "images" / "queue"
IMAGES_INBOX = ROOT / "images" / "inbox"
IMAGES_BACKUP = IMAGES_QUEUE / "backup"
METADATA = ROOT / "images" / "metadata.json"
QUEUE = ROOT / "queue.csv"
BATCH_STATE = ROOT / ".batch_state"
DESCRIPTIONS = ROOT / "descriptions"
YOUTUBE_INVENTORY = ROOT / "output" / "youtube_all_videos.json"
UPLOAD_HISTORY = ROOT / "output" / "upload_history.json"
PENDING_METADATA: dict[str, dict] = {}

IMAGE_EXTS = {".png", ".jpg", ".jpeg"}
DEFAULT_DESCRIPTIONS = [
    "level_0.txt",
    "empty_mall.txt",
    "airport_terminal.txt",
    "infinite_hotel.txt",
    "laundromat.txt",
    "classroom.txt",
    "playplace.txt",
    "suburban_street.txt",
    "library.txt",
    "poolrooms.txt",
    "train_station.txt",
    "template.txt",
]


def image_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(
        p for p in path.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS and not p.name.startswith(".")
    )


def load_metadata() -> dict:
    if not METADATA.exists():
        return {}
    try:
        with METADATA.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_metadata(data: dict, dry_run: bool) -> None:
    if dry_run:
        return
    METADATA.parent.mkdir(parents=True, exist_ok=True)
    with METADATA.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def metadata_entry_for(image_name: str) -> dict:
    if image_name in PENDING_METADATA:
        return PENDING_METADATA[image_name]
    metadata = load_metadata()
    entry = metadata.get(image_name)
    return entry if isinstance(entry, dict) else {}


def read_sidecar(image_path: Path) -> dict:
    sidecar = image_path.with_suffix(".json")
    if not sidecar.exists():
        return {}
    try:
        data = json.loads(sidecar.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def norm_title(title: str) -> str:
    return " ".join(title.lower().split())


def posted_titles() -> set[str]:
    titles: set[str] = set()
    for path in (YOUTUBE_INVENTORY, UPLOAD_HISTORY):
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        items = data.get("all_videos", []) if isinstance(data, dict) else data
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict) and item.get("title"):
                titles.add(norm_title(str(item["title"])))
    return titles


def normalize_metadata(image_name: str, sidecar: dict) -> dict:
    base = metadata_for(image_name)
    out = dict(base)
    for key in ("title", "description", "audio_profile", "visual_style"):
        if sidecar.get(key):
            out[key] = str(sidecar[key])
    if isinstance(sidecar.get("tags"), list) and sidecar["tags"]:
        out["tags"] = [str(x) for x in sidecar["tags"] if str(x).strip()][:10]
    if sidecar.get("prompt"):
        out["prompt"] = str(sidecar["prompt"])
    return out


def unique_destination(src: Path) -> Path:
    dst = IMAGES_QUEUE / src.name
    if not dst.exists():
        return dst
    stem, suffix = src.stem, src.suffix
    for idx in range(2, 1000):
        candidate = IMAGES_QUEUE / f"{stem}_{idx}{suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not find unique destination for {src.name}")


def clean_words(filename: str) -> list[str]:
    stem = Path(filename).stem.lower()
    parts = []
    for token in stem.replace("-", "_").split("_"):
        if token.isdigit() or len(token) > 10 and token.isnumeric():
            continue
        if token in {"media", "image", "cover", "python", "code", "openrouter", "gen"}:
            continue
        parts.append(token)
    return parts or ["liminal", "void"]


def metadata_for(filename: str) -> dict:
    words = clean_words(filename)
    phrase = " ".join(words[:3])
    tags = ["ambient", "dark ambient", "cosmic horror", "sleep ambient", "1 hour ambient"]
    tags.extend(w.replace("-", " ") for w in words[:4])

    if "poolrooms" in words:
        title = "lost in the tiles | poolrooms ambient playlist | liminal space drone"
        desc = "poolrooms.txt"
        audio_profile = "poolrooms"
    elif "airport" in words:
        title = "silent terminal | empty airport lobby ambient | sunset liminal space"
        desc = "airport_terminal.txt"
        audio_profile = "terminal"
    elif "library" in words:
        title = "whispering shelves | infinite library ambient | dark academia drone"
        desc = "library.txt"
        audio_profile = "mall"
    elif "mall" in words:
        title = "mallsoft echoes | empty shopping mall ambient | retro liminal space"
        desc = "empty_mall.txt"
        audio_profile = "mall"
    elif "erebus" in words or "ice" in words or "antarctic" in words:
        title = "the ice remembers | arctic cosmic horror ambient | dark drone"
        desc = "template.txt"
        audio_profile = "arctic"
    elif "lighthouse" in words:
        title = "the lighthouse watched | coastal cosmic horror ambient | dark drone"
        desc = "template.txt"
        audio_profile = "harbor"
    elif "cathedral" in words:
        title = "drowned cathedral | cosmic horror ambience | deep drone"
        desc = "template.txt"
        audio_profile = "void"
    elif "harbor" in words or "cthulhu" in words:
        title = "harbor shadow | cosmic horror ambient | dark ocean drone"
        desc = "template.txt"
        audio_profile = "harbor"
    else:
        title = f"{phrase} | cosmic horror ambient | dark drone"
        desc = "template.txt"
        audio_profile = "void"

    return {
        "title": title[:100],
        "tags": list(dict.fromkeys(tags))[:10],
        "description": desc,
        "audio_profile": audio_profile,
    }


def promote_image_from(source_dir: Path, dry_run: bool) -> str | None:
    sources = image_files(source_dir)
    if not sources:
        return None
    seen = posted_titles()
    src = None
    sidecar = {}
    for candidate in sources:
        sidecar = read_sidecar(candidate)
        title = str(sidecar.get("title") or metadata_for(candidate.name).get("title") or "")
        if title and norm_title(title) in seen:
            print(f"skip posted image: {candidate.relative_to(ROOT)}")
            continue
        src = candidate
        break
    if src is None:
        return None
    dst = unique_destination(src)
    if dry_run:
        print(f"would promote image: {src.relative_to(ROOT)} -> {dst.relative_to(ROOT)}")
        if sidecar:
            PENDING_METADATA[dst.name] = normalize_metadata(dst.name, sidecar)
    else:
        IMAGES_QUEUE.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        print(f"promoted image: {dst.relative_to(ROOT)}")
        if sidecar:
            metadata = load_metadata()
            metadata[dst.name] = normalize_metadata(dst.name, sidecar)
            save_metadata(metadata, dry_run=False)
            print(f"metadata imported: images/metadata.json[{dst.name}]")
    return dst.name


def promote_image(dry_run: bool) -> str | None:
    image_name = promote_image_from(IMAGES_INBOX, dry_run)
    if image_name:
        return image_name
    return promote_image_from(IMAGES_BACKUP, dry_run)


def generate_image(dry_run: bool) -> str:
    name = f"procedural_void_{int(time.time())}.png"
    dst = IMAGES_QUEUE / name
    if dry_run:
        print(f"would generate procedural image: {dst.relative_to(ROOT)}")
        return name
    IMAGES_QUEUE.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", "color=c=0x070912:s=1280x720",
        "-vf", "noise=alls=18:allf=t+u,boxblur=2:1,vignette=PI/4,format=rgb24",
        "-frames:v", "1", str(dst),
    ]
    subprocess.run(cmd, check=True)
    print(f"generated procedural image: {dst.relative_to(ROOT)}")
    return name


def queue_rows() -> list[list[str]]:
    if not QUEUE.exists():
        return []
    with QUEUE.open("r", encoding="utf-8", newline="") as f:
        return [r for r in csv.reader(f) if r and any(x.strip() for x in r)]


def processed_count() -> int:
    if not BATCH_STATE.exists():
        return 0
    try:
        return int(BATCH_STATE.read_text(encoding="utf-8").strip() or "0")
    except Exception:
        return 0


def choose_description(image_name: str | None, row_index: int) -> str:
    if image_name:
        meta_desc = metadata_entry_for(image_name).get("description") or metadata_for(image_name).get("description")
        if meta_desc and (DESCRIPTIONS / meta_desc).exists():
            return meta_desc
    available = [d for d in DEFAULT_DESCRIPTIONS if (DESCRIPTIONS / d).exists()]
    if not available:
        return "template.txt"
    return available[row_index % len(available)]


def choose_audio_profile(image_name: str | None, desc: str) -> str:
    if image_name:
        meta_profile = metadata_entry_for(image_name).get("audio_profile") or metadata_for(image_name).get("audio_profile")
        if meta_profile:
            return meta_profile
    text = desc.lower()
    if "pool" in text or "tile" in text:
        return "poolrooms"
    if "airport" in text or "train" in text or "station" in text:
        return "terminal"
    if any(x in text for x in ["mall", "hotel", "laundromat", "classroom", "playplace", "suburban", "library"]):
        return "mall"
    if "template" in text:
        return "void"
    return "auto"


def append_queue_rows(count: int, image_name: str | None, dry_run: bool) -> int:
    rows = queue_rows()
    done = processed_count()
    remaining = max(0, len(rows) - done)
    needed = max(0, count - remaining)
    if needed == 0:
        print(f"queue rows remaining: {remaining}")
        return 0

    new_rows = []
    for i in range(needed):
        desc = choose_description(image_name, len(rows) + i)
        profile = choose_audio_profile(image_name, desc)
        new_rows.append(["blend", "auto", desc, "0.93", profile])

    if dry_run:
        for row in new_rows:
            print("would append queue row:", ",".join(row))
    else:
        with QUEUE.open("a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, lineterminator="\n")
            for row in new_rows:
                writer.writerow(row)
        print(f"appended queue rows: {needed}")
    return needed


def ensure_image_metadata(image_name: str, dry_run: bool) -> None:
    if image_name in PENDING_METADATA:
        return
    metadata = load_metadata()
    if image_name in metadata and metadata[image_name].get("title"):
        return
    metadata[image_name] = metadata_for(image_name)
    save_metadata(metadata, dry_run)
    print(f"metadata ensured: images/metadata.json[{image_name}]")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-images", type=int, default=1)
    parser.add_argument("--min-queue", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-procedural", action="store_true", default=os.environ.get("DRONEMILL_ALLOW_PROCEDURAL_IMAGE") == "1")
    args = parser.parse_args()

    IMAGES_QUEUE.mkdir(parents=True, exist_ok=True)
    IMAGES_INBOX.mkdir(parents=True, exist_ok=True)
    (ROOT / "state").mkdir(exist_ok=True)

    active_images = image_files(IMAGES_QUEUE)
    image_name = active_images[0].name if active_images else None

    while len(active_images) < args.min_images:
        image_name = promote_image(args.dry_run)
        if image_name is None:
            if not args.allow_procedural:
                print("ERROR: no real images available in images/inbox, images/queue, or images/queue/backup; refusing procedural fallback", file=sys.stderr)
                print("Generate fresh images with scripts/ui-image-worker.sh, or pass --allow-procedural / DRONEMILL_ALLOW_PROCEDURAL_IMAGE=1.", file=sys.stderr)
                return 2
            image_name = generate_image(args.dry_run)
        if args.dry_run:
            active_images.append(IMAGES_QUEUE / image_name)
        else:
            active_images = image_files(IMAGES_QUEUE)

    if image_name:
        ensure_image_metadata(image_name, args.dry_run)

    append_queue_rows(args.min_queue, image_name, args.dry_run)

    print(f"stock ok: images={len(active_images)} queue_remaining={max(0, len(queue_rows()) - processed_count())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

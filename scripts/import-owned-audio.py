#!/usr/bin/env python3
"""Import owned YouTube uploads as local reusable stems.

Default behavior downloads only an initial segment, so a 10h source does not
fill the disk. Use --full to import entire videos.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "owned_sources.json"
OWNED = ROOT / "audio" / "owned"


def slugify(text: str, max_len: int = 64) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:max_len].strip("-") or "owned-audio"


def load_sources() -> list[dict]:
    with SOURCES.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def pick_sources(sources: list[dict], wanted: str) -> list[dict]:
    if wanted == "all":
        return sources
    picked = [
        s for s in sources
        if wanted in {s.get("id"), s.get("profile"), slugify(s.get("title", ""))}
    ]
    if not picked:
        raise SystemExit(f"No owned source matched: {wanted}")
    return picked


def pick_offset_seconds(src: dict, minutes: int | None, spread: bool, offset_minutes: int | None) -> int:
    if minutes is None:
        return 0
    if offset_minutes is not None:
        return max(0, offset_minutes * 60)
    if not spread:
        return 0

    duration = int(src.get("duration_seconds") or 0)
    max_offset = max(0, duration - (minutes * 60))
    if max_offset <= 0:
        return 0

    digest = hashlib.sha1(src["id"].encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % max_offset


def output_name(src: dict, minutes: int | None, offset_seconds: int) -> str:
    suffix = "full" if minutes is None else f"{minutes}m"
    if offset_seconds:
        suffix += f"_from{offset_seconds // 60}m"
    return f"{src['id']}_{slugify(src['title'])}_{suffix}.mp3"


def import_source(
    src: dict,
    minutes: int | None,
    offset_seconds: int,
    dry_run: bool,
) -> Path:
    OWNED.mkdir(parents=True, exist_ok=True)
    out = OWNED / output_name(src, minutes, offset_seconds)
    if out.exists():
        print(f"exists: {out.relative_to(ROOT)}")
        return out

    section = None
    if minutes is not None:
        section = f"*{offset_seconds}-{offset_seconds + (minutes * 60)}"

    cmd = [
        "yt-dlp",
        "--no-playlist",
        "--no-update",
        "-f",
        "bestaudio/best",
        "-x",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "0",
        "-o",
        str(out.with_suffix(".%(ext)s")),
    ]
    if section:
        cmd.extend(["--download-sections", section, "--force-keyframes-at-cuts"])
    cmd.append(src["url"])

    start_label = f" start={offset_seconds // 60}m" if offset_seconds else ""
    print(f"import: {src['id']} profile={src.get('profile')}{start_label} -> {out.relative_to(ROOT)}")
    if dry_run:
        print(" ".join(cmd))
        return out

    subprocess.run(cmd, check=True)
    if not out.exists():
        candidates = sorted(OWNED.glob(f"{out.stem}.*"))
        if candidates:
            candidates[0].rename(out)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", nargs="?", default="all", help="all, video id, profile, or title slug")
    parser.add_argument("--minutes", type=int, default=90, help="segment length to import; default 90")
    parser.add_argument("--offset-minutes", type=int, default=None, help="fixed segment start offset")
    parser.add_argument("--spread", action="store_true", help="pick a deterministic different offset per source")
    parser.add_argument("--full", action="store_true", help="download full video audio")
    parser.add_argument("--stop-on-error", action="store_true", help="abort on first failed source")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    sources = load_sources()
    if args.list:
        for s in sources:
            duration = s.get("duration_seconds")
            duration_label = f"{duration}s" if duration else "unknown"
            print(f"{s['id']}\t{s.get('profile')}\t{duration_label}\t{s['title']}")
        return 0

    minutes = None if args.full else args.minutes
    failures: list[tuple[str, str]] = []
    for src in pick_sources(sources, args.source):
        offset_seconds = pick_offset_seconds(src, minutes, args.spread, args.offset_minutes)
        try:
            import_source(src, minutes, offset_seconds, args.dry_run)
        except subprocess.CalledProcessError as exc:
            failures.append((src["id"], str(exc)))
            print(f"ERROR: failed {src['id']}: {exc}", file=sys.stderr)
            if args.stop_on_error:
                return exc.returncode

    if failures:
        print("\nFailed sources:", file=sys.stderr)
        for video_id, error in failures:
            print(f"- {video_id}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

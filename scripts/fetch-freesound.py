#!/usr/bin/env python3
"""Download CC-licensed ambient beds from Freesound into audio/queue/.

Requires FREESOUND_API_KEY (Token) from https://freesound.org/apiv2/apply
Set in environment or dronemill/.env

Uses preview HQ MP3 when OAuth full download is unavailable (fine after cosmic.sh processing).
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_BASE = "https://freesound.org/apiv2/search/"

DEFAULT_QUERIES = [
    "drone ambient dark",
    "liminal space hum",
    "room tone empty",
    "cosmic horror drone",
    "atmospheric pad sleep",
    "industrial hum loop",
]

LICENSE_FILTERS = {
    "cc0": 'license:"Creative Commons 0"',
    "by": 'license:"Attribution"',
}


def load_env(root: Path) -> None:
    env_file = root / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = val


def slugify(name: str, max_len: int = 60) -> str:
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return (s or "sound")[:max_len]


def api_get(url: str, token: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Token {token}", "User-Agent": "dronemill/1.0"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def search_sounds(
    token: str,
    query: str,
    license_key: str,
    min_duration: float,
    max_duration: float | None,
    page_size: int,
    sort: str,
    page: int,
) -> list[dict]:
    lic = LICENSE_FILTERS.get(license_key, LICENSE_FILTERS["cc0"])
    dur_hi = "*" if max_duration is None else str(max_duration)
    filt = f"{lic} duration:[{min_duration} TO {dur_hi}]"
    params = {
        "query": query,
        "filter": filt,
        "sort": sort,
        "fields": "id,name,duration,username,license,previews,download,tags",
        "page_size": str(page_size),
        "page": str(page),
    }
    url = API_BASE + "?" + urllib.parse.urlencode(params)
    data = api_get(url, token)
    return data.get("results", [])


def download_url(url: str, dest: Path, token: str | None) -> None:
    headers = {"User-Agent": "dronemill/1.0"}
    if token:
        headers["Authorization"] = f"Token {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as resp:
        dest.write_bytes(resp.read())


def pick_download_url(sound: dict, prefer_full: bool, token: str) -> tuple[str, str]:
    previews = sound.get("previews") or {}
    preview = previews.get("preview-hq-mp3") or previews.get("preview-lq-mp3")
    if prefer_full and sound.get("download"):
        try:
            # API returns redirect target for original file (needs token).
            req = urllib.request.Request(
                sound["download"],
                headers={"Authorization": f"Token {token}", "User-Agent": "dronemill/1.0"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.url, "full"
        except urllib.error.HTTPError:
            pass
    if preview:
        return preview, "preview"
    raise RuntimeError("no preview or download URL")


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    root = script_dir.parent
    load_env(root)

    parser = argparse.ArgumentParser(description="Fetch CC ambient beds from Freesound")
    parser.add_argument("-n", "--count", type=int, default=1, help="Number of sounds to download")
    parser.add_argument("-q", "--query", action="append", help="Search query (repeatable)")
    parser.add_argument(
        "--license",
        choices=("cc0", "by"),
        default="cc0",
        help="cc0 = no attribution required; by = credit uploader in YT description",
    )
    parser.add_argument("--min-duration", type=float, default=30.0, help="Minimum seconds")
    parser.add_argument("--max-duration", type=float, default=None, help="Maximum seconds (optional)")
    parser.add_argument("--sort", default="duration_desc", help="Freesound sort (duration_desc, rating_desc, ...)")
    parser.add_argument("--page-size", type=int, default=50)
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Take first N search results (default: random sample)",
    )
    parser.add_argument("--full", action="store_true", help="Try original file via API (falls back to preview)")
    parser.add_argument("-o", "--output-dir", type=Path, default=root / "audio" / "queue")
    args = parser.parse_args()

    token = os.environ.get("FREESOUND_API_KEY", "").strip()
    if not token:
        print(
            "ERROR: FREESOUND_API_KEY not set.\n"
            "  1) Apply at https://freesound.org/apiv2/apply\n"
            "  2) Add to dronemill/.env:  FREESOUND_API_KEY=your_token",
            file=sys.stderr,
        )
        return 1

    queries = args.query or DEFAULT_QUERIES
    args.output_dir.mkdir(parents=True, exist_ok=True)

    pool: list[dict] = []
    for q in queries:
        try:
            hits = search_sounds(
                token,
                q,
                args.license,
                args.min_duration,
                args.max_duration,
                args.page_size,
                args.sort,
                args.page,
            )
            pool.extend(hits)
            print(f"query={q!r} -> {len(hits)} hits")
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:300]
            print(f"WARN: search failed for {q!r}: HTTP {e.code} {body}", file=sys.stderr)

    # Dedupe by id
    seen: set[int] = set()
    unique: list[dict] = []
    for s in pool:
        sid = s.get("id")
        if sid in seen:
            continue
        seen.add(sid)
        unique.append(s)

    if not unique:
        print("No sounds matched. Try --min-duration 10 or a broader --query.", file=sys.stderr)
        return 1

    if args.sequential:
        picks = unique[: args.count]
    else:
        picks = random.sample(unique, k=min(args.count, len(unique)))

    manifest = []
    for sound in picks:
        sid = sound["id"]
        name = sound.get("name", f"sound-{sid}")
        user = sound.get("username", "unknown")
        lic = sound.get("license", "?")
        dur = sound.get("duration", 0)
        slug = slugify(name)
        out = args.output_dir / f"fs{sid}-{slug}.mp3"

        if out.exists():
            print(f"skip (exists): {out.name}")
            manifest.append({"file": str(out), "id": sid, "skipped": True})
            continue

        try:
            url, kind = pick_download_url(sound, args.full, token)
            print(f"downloading [{kind}] id={sid} ({dur:.0f}s) {name} by {user} ({lic})")
            download_url(url, out, token if kind == "full" else None)
            print(f"  -> {out}")
            manifest.append(
                {
                    "file": str(out),
                    "id": sid,
                    "name": name,
                    "username": user,
                    "license": lic,
                    "duration": dur,
                    "tags": sound.get("tags", []),
                    "attribution": f"{name} by {user} — Freesound.org (sound {sid})",
                    "kind": kind,
                }
            )
        except Exception as exc:
            print(f"FAIL id={sid}: {exc}", file=sys.stderr)

    meta_path = args.output_dir / "freesound_manifest.json"
    existing = []
    if meta_path.exists():
        try:
            existing = json.loads(meta_path.read_text())
        except json.JSONDecodeError:
            existing = []
    existing.extend(manifest)
    meta_path.write_text(json.dumps(existing, indent=2) + "\n")
    print(f"manifest -> {meta_path} ({len(manifest)} new entries)")
    return 0 if manifest else 1


if __name__ == "__main__":
    raise SystemExit(main())
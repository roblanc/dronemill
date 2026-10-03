#!/usr/bin/env python3
"""
split-ui-image-prompts.py — split a UI image prompt file into disjoint provider batches.

This enables Antigravity/Gemini and ChatGPT UI workers to run in parallel without
fighting over the same filenames.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_prompt_entries(prompts_path: Path) -> list[dict]:
    text = prompts_path.read_text(encoding="utf-8")

    image_matches = list(
        re.finditer(r"--- Image ([^\s]+) ---\n([\s\S]*?)(?=\n--- Image [^\s]+ ---|$)", text)
    )
    if image_matches:
        return [
            {
                "filename": m.group(1).strip(),
                "prompt": m.group(2).strip(),
            }
            for m in image_matches
        ]

    beat_matches = list(
        re.finditer(r"--- Beat (\d+)\/(\d+) \(words [^)]+\) ---\n([\s\S]*?)(?=\n--- Beat \d+\/\d+|$)", text)
    )
    if beat_matches:
        return [
            {
                "filename": f"scene-{int(m.group(1)):02d}.png",
                "prompt": m.group(3).strip(),
            }
            for m in beat_matches
        ]

    raise SystemExit(f"no prompt entries found in {prompts_path}")


def ensure_unique_filenames(entries: list[dict], prompts_path: Path) -> None:
    seen: set[str] = set()
    dupes: list[str] = []
    for entry in entries:
        filename = entry["filename"]
        if filename in seen:
            dupes.append(filename)
        seen.add(filename)
    if dupes:
        dupe_text = ", ".join(sorted(set(dupes)))
        raise SystemExit(f"duplicate filenames in {prompts_path}: {dupe_text}")


def provider_assignments(entries: list[dict], providers: list[str], mode: str) -> dict[str, list[dict]]:
    assigned = {provider: [] for provider in providers}
    if mode == "alternate":
        for idx, entry in enumerate(entries):
            provider = providers[idx % len(providers)]
            assigned[provider].append(entry)
        return assigned

    if mode == "first-half":
        chunk = (len(entries) + len(providers) - 1) // len(providers)
        for idx, provider in enumerate(providers):
            start = idx * chunk
            end = start + chunk
            assigned[provider].extend(entries[start:end])
        return assigned

    raise SystemExit(f"unsupported split mode: {mode}")


def sanitize_provider(provider: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", provider.lower()).strip("-")


def write_prompt_file(out_path: Path, slug: str, provider: str, entries: list[dict]) -> None:
    rows = [
        f"# Parallel UI Image Prompts: {slug}",
        f"# Provider batch: {provider}",
        "",
        "Generate via the assigned UI provider only. Save approved outputs to the exact filenames.",
        "",
    ]
    for entry in entries:
        rows.append(f"--- Image {entry['filename']} ---")
        rows.append(entry["prompt"])
        rows.append("")
    out_path.write_text("\n".join(rows), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Split UI image prompts into provider-safe batches.")
    parser.add_argument("slug", nargs="?", default="dronemill")
    parser.add_argument("--prompts", help="Source prompt file; defaults to output/ui_image_prompts.txt")
    parser.add_argument(
        "--providers",
        default="antigravity,chatgpt",
        help="Comma-separated provider names. Default: antigravity,chatgpt",
    )
    parser.add_argument(
        "--mode",
        default="alternate",
        choices=["alternate", "first-half"],
        help="How to split prompts across providers. Default: alternate",
    )
    parser.add_argument(
        "--out-dir",
        help="Output directory for split prompt files; defaults to output/parallel-ui-prompts",
    )
    args = parser.parse_args()

    providers = [p.strip() for p in args.providers.split(",") if p.strip()]
    if not providers:
        raise SystemExit("at least one provider is required")

    prompts_path = Path(args.prompts) if args.prompts else ROOT / "output" / "ui_image_prompts.txt"
    if not prompts_path.exists():
        raise SystemExit(f"missing prompts file: {prompts_path}")

    entries = parse_prompt_entries(prompts_path)
    ensure_unique_filenames(entries, prompts_path)
    split = provider_assignments(entries, providers, args.mode)

    out_dir = Path(args.out_dir) if args.out_dir else ROOT / "output" / "parallel-ui-prompts"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"source={prompts_path}")
    print(f"mode={args.mode}")
    print(f"total_entries={len(entries)}")

    stem = prompts_path.stem
    for provider in providers:
        batch = split[provider]
        provider_slug = sanitize_provider(provider)
        out_path = out_dir / f"{stem}.{provider_slug}.txt"
        write_prompt_file(out_path, args.slug, provider, batch)
        print(f"{provider} prompts={len(batch)} file={out_path}")


if __name__ == "__main__":
    main()

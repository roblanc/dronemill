#!/usr/bin/env python3
"""Export all videos from the authenticated YouTube channel."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import googleapiclient.discovery


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
TOKEN_PATH = Path.home() / ".youtubeuploader" / "request.token"
SECRETS_PATH = Path.home() / ".youtubeuploader" / "client_secrets.json"
def load_credentials() -> Credentials:
    if not TOKEN_PATH.exists() or not SECRETS_PATH.exists():
        raise SystemExit("Missing ~/.youtubeuploader/request.token or client_secrets.json")

    token_data = json.loads(TOKEN_PATH.read_text(encoding="utf-8"))
    secrets_data = json.loads(SECRETS_PATH.read_text(encoding="utf-8"))
    cfg = secrets_data.get("installed", secrets_data.get("web", {}))
    creds = Credentials(
        token=token_data.get("access_token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=cfg.get("client_id"),
        client_secret=cfg.get("client_secret"),
        scopes=token_data.get("scope", "").split() or None,
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


def chunks(items: list[str], size: int) -> list[list[str]]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def fetch_uploads(youtube) -> tuple[dict, list[dict]]:
    chans = youtube.channels().list(mine=True, part="snippet,contentDetails").execute()
    if not chans.get("items"):
        raise SystemExit("No YouTube channel found for these credentials")

    channel = chans["items"][0]
    uploads_id = channel["contentDetails"]["relatedPlaylists"]["uploads"]
    videos: list[dict] = []
    page_token = None

    while True:
        resp = youtube.playlistItems().list(
            playlistId=uploads_id,
            part="snippet,contentDetails",
            maxResults=50,
            pageToken=page_token,
        ).execute()
        for item in resp.get("items", []):
            snippet = item["snippet"]
            content = item["contentDetails"]
            video_id = content["videoId"]
            published = content.get("videoPublishedAt") or snippet.get("publishedAt", "")
            videos.append({
                "id": video_id,
                "title": snippet.get("title", ""),
                "published_at": published,
                "date": published[:10] if published else "",
                "url": f"https://www.youtube.com/watch?v={video_id}",
            })

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return channel, videos


def add_status(youtube, videos: list[dict]) -> None:
    by_id = {v["id"]: v for v in videos}
    for chunk in chunks(list(by_id), 50):
        resp = youtube.videos().list(
            id=",".join(chunk),
            part="status,contentDetails",
            maxResults=50,
        ).execute()
        for item in resp.get("items", []):
            target = by_id[item["id"]]
            status = item.get("status", {})
            content = item.get("contentDetails", {})
            target["privacy"] = status.get("privacyStatus", "unknown")
            target["publish_at"] = status.get("publishAt", "")
            target["duration"] = content.get("duration", "")

    for video in videos:
        video.setdefault("privacy", "unknown")
        video.setdefault("publish_at", "")
        video.setdefault("duration", "")


def write_outputs(channel: dict, videos: list[dict], prefix: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    videos.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    for idx, video in enumerate(videos, 1):
        video["index"] = idx

    breakdown: dict[str, int] = {}
    for video in videos:
        breakdown[video["privacy"]] = breakdown.get(video["privacy"], 0) + 1

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "channel": channel["snippet"].get("title", ""),
        "channel_id": channel.get("id", ""),
        "channel_url": f"https://www.youtube.com/channel/{channel.get('id', '')}",
        "total": len(videos),
        "privacy_breakdown": breakdown,
        "all_videos": videos,
    }

    json_path = OUT / f"{prefix}.json"
    csv_path = OUT / f"{prefix}.csv"
    md_path = OUT / f"{prefix}.md"

    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["index", "date", "published_at", "privacy", "publish_at", "duration", "id", "title", "url"],
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(videos)

    lines = [
        f"# {payload['channel']} — All YouTube Videos",
        "",
        f"Generated: {payload['generated_at']}",
        f"Channel: https://www.youtube.com/channel/{payload['channel_id']}",
        f"Total: **{payload['total']}** ({', '.join(f'{k}: {v}' for k, v in sorted(breakdown.items()))})",
        "",
        "| # | Date | Privacy | Title | Link |",
        "|---|------|---------|-------|------|",
    ]
    for video in videos:
        title = video["title"].replace("|", "\\|")
        lines.append(
            f"| {video['index']} | {video['date']} | {video['privacy']} | "
            f"{title} | [watch]({video['url']}) |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {json_path.relative_to(ROOT)}")
    print(f"Wrote {csv_path.relative_to(ROOT)}")
    print(f"Wrote {md_path.relative_to(ROOT)}")
    print(f"Total: {payload['total']} {breakdown}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", default="youtube_all_videos")
    args = parser.parse_args()

    os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
    creds = load_credentials()
    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
    channel, videos = fetch_uploads(youtube)
    add_status(youtube, videos)
    write_outputs(channel, videos, args.prefix)
    return 0


if __name__ == "__main__":
    sys.exit(main())

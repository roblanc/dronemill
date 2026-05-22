#!/usr/bin/env python3
"""
Pull YouTube Analytics for the last N uploads → performance.csv.

Joins with images/metadata.json (pillar tags, title) so you can see which
thematic pillars actually drive retention/CTR.

Output columns:
  video_id, published, title, image_file, pillar_tags,
  views, watch_time_min, avg_view_duration_s, avg_view_pct, ctr_pct

Usage:
  ./analytics-pull.py                  # last 50 videos
  ./analytics-pull.py --limit 100
  ./analytics-pull.py --days 60        # only videos published in last 60d

NOTE: Requires the `yt-analytics.readonly` scope. If you previously authed
only with the upload scope, re-run the youtubeuploader auth flow with the
extended scope set OR run this script — it will surface the auth error
and you can re-authorize via the printed URL.
"""

import os
import sys
import csv
import json
import argparse
from datetime import datetime, timedelta, timezone
from google.oauth2.credentials import Credentials
import googleapiclient.discovery
import googleapiclient.errors

HOME = os.path.expanduser("~")
TOKEN_PATH = os.path.join(HOME, ".youtubeuploader", "request.token")
SECRETS_PATH = os.path.join(HOME, ".youtubeuploader", "client_secrets.json")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
META_PATH = os.path.join(ROOT, "images", "metadata.json")
UPLOAD_HISTORY = os.path.join(ROOT, "output", "upload_history.json")
OUT_CSV = os.path.join(ROOT, "output", "performance.csv")


def load_credentials():
    if not os.path.exists(TOKEN_PATH) or not os.path.exists(SECRETS_PATH):
        print("ERROR: missing credentials. Need request.token + client_secrets.json in ~/.youtubeuploader/", file=sys.stderr)
        sys.exit(1)
    with open(TOKEN_PATH) as f:
        token_data = json.load(f)
    with open(SECRETS_PATH) as f:
        secrets_data = json.load(f)
    cfg = secrets_data.get("installed", secrets_data.get("web", {}))
    return Credentials(
        token=token_data.get("access_token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=cfg.get("client_id"),
        client_secret=cfg.get("client_secret"),
        scopes=[
            "https://www.googleapis.com/auth/youtube.readonly",
            "https://www.googleapis.com/auth/yt-analytics.readonly",
        ],
    )


def load_metadata_index():
    """Returns dict: title (lower, stripped) -> {image_file, tags}"""
    if not os.path.exists(META_PATH):
        return {}
    with open(META_PATH) as f:
        meta = json.load(f)
    index = {}
    for img_file, entry in meta.items():
        title = (entry.get("title") or "").strip().lower()
        if not title:
            continue
        index[title] = {
            "image_file": img_file,
            "tags": entry.get("tags", []),
        }
    return index


def load_upload_history_index():
    """Returns dict: title (lower) -> upload_history entry"""
    if not os.path.exists(UPLOAD_HISTORY):
        return {}
    try:
        with open(UPLOAD_HISTORY) as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, list):
        return {}
    return {(item.get("title") or "").strip().lower(): item for item in data}


def get_recent_videos(youtube, limit, days_cutoff):
    chans = youtube.channels().list(mine=True, part="contentDetails,snippet").execute()
    if not chans.get("items"):
        print("ERROR: no channels for these credentials.", file=sys.stderr)
        sys.exit(1)
    uploads_pid = chans["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    channel_id = chans["items"][0]["id"]

    cutoff_dt = None
    if days_cutoff:
        cutoff_dt = datetime.now(timezone.utc) - timedelta(days=days_cutoff)

    videos = []
    page_token = None
    while len(videos) < limit:
        resp = youtube.playlistItems().list(
            playlistId=uploads_pid, part="snippet,contentDetails",
            maxResults=min(50, limit - len(videos)), pageToken=page_token,
        ).execute()
        for item in resp.get("items", []):
            published = item["contentDetails"].get("videoPublishedAt") or item["snippet"]["publishedAt"]
            if cutoff_dt:
                try:
                    pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                    if pub_dt < cutoff_dt:
                        continue
                except Exception:
                    pass
            videos.append({
                "video_id": item["snippet"]["resourceId"]["videoId"],
                "published": published,
                "title": item["snippet"]["title"],
            })
            if len(videos) >= limit:
                break
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return channel_id, videos


def fetch_analytics(analytics, channel_id, video_ids, start_date, end_date):
    """Returns dict: video_id -> metrics row"""
    out = {}
    # YouTube Analytics API: split into chunks of ~50 IDs
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i + 50]
        filt = f"video=={','.join(chunk)}"
        try:
            resp = analytics.reports().query(
                ids=f"channel=={channel_id}",
                startDate=start_date,
                endDate=end_date,
                metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage",
                dimensions="video",
                filters=filt,
                maxResults=200,
            ).execute()
        except googleapiclient.errors.HttpError as e:
            print(f"WARN: analytics fetch failed for chunk {i}: {e}", file=sys.stderr)
            continue
        for row in resp.get("rows", []):
            vid = row[0]
            out[vid] = {
                "views": int(row[1]) if row[1] is not None else 0,
                "watch_time_min": float(row[2]) if row[2] is not None else 0.0,
                "avg_view_duration_s": float(row[3]) if row[3] is not None else 0.0,
                "avg_view_pct": float(row[4]) if row[4] is not None else 0.0,
            }
    return out


def fetch_ctr(analytics, channel_id, video_ids, start_date, end_date):
    """Fetch CTR (impressions click-through rate) per video. Requires content owner OR channel owner scope."""
    out = {}
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i + 50]
        filt = f"video=={','.join(chunk)}"
        try:
            resp = analytics.reports().query(
                ids=f"channel=={channel_id}",
                startDate=start_date,
                endDate=end_date,
                metrics="cardImpressionsClickThroughRate",
                dimensions="video",
                filters=filt,
                maxResults=200,
            ).execute()
            for row in resp.get("rows", []):
                out[row[0]] = float(row[1]) if row[1] is not None else 0.0
        except googleapiclient.errors.HttpError:
            # CTR endpoint can be flaky / scope-restricted; skip silently.
            pass
    return out


def main():
    parser = argparse.ArgumentParser(description="Pull YT Analytics for recent uploads")
    parser.add_argument("--limit", type=int, default=50, help="Max videos to pull (default 50)")
    parser.add_argument("--days", type=int, default=90, help="Only pull videos from last N days (default 90)")
    parser.add_argument("--out", default=OUT_CSV, help="Output CSV path")
    args = parser.parse_args()

    creds = load_credentials()
    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
    analytics = googleapiclient.discovery.build("youtubeAnalytics", "v2", credentials=creds)

    meta_index = load_metadata_index()
    upload_idx = load_upload_history_index()

    print(f"[1/4] Fetching last {args.limit} videos (cutoff: {args.days}d)...")
    channel_id, videos = get_recent_videos(youtube, args.limit, args.days)
    if not videos:
        print("No videos found in window.")
        return

    video_ids = [v["video_id"] for v in videos]
    start_date = (datetime.now(timezone.utc) - timedelta(days=max(args.days, 30))).strftime("%Y-%m-%d")
    end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print(f"[2/4] Fetching analytics ({start_date} -> {end_date}) for {len(video_ids)} videos...")
    metrics = fetch_analytics(analytics, channel_id, video_ids, start_date, end_date)

    print(f"[3/4] Fetching CTR (best-effort)...")
    ctr_map = fetch_ctr(analytics, channel_id, video_ids, start_date, end_date)

    print(f"[4/4] Joining with metadata.json + writing CSV...")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "video_id", "published", "title", "image_file", "pillar_tags",
            "views", "watch_time_min", "avg_view_duration_s", "avg_view_pct", "ctr_pct",
        ])
        for v in videos:
            vid = v["video_id"]
            title = v["title"]
            key = title.strip().lower()
            meta_hit = meta_index.get(key, {})
            # Fallback: try matching via upload_history's title -> image
            if not meta_hit and key in upload_idx:
                hist = upload_idx[key]
                local = (hist.get("local_path") or "").replace(".mp4", "")
                for mk, mv in meta_index.items():
                    if mk and (mk in key or key in mk):
                        meta_hit = mv
                        break
            m = metrics.get(vid, {})
            w.writerow([
                vid,
                v["published"],
                title,
                meta_hit.get("image_file", ""),
                "|".join(meta_hit.get("tags", [])),
                m.get("views", 0),
                round(m.get("watch_time_min", 0.0), 2),
                round(m.get("avg_view_duration_s", 0.0), 1),
                round(m.get("avg_view_pct", 0.0), 2),
                round(ctr_map.get(vid, 0.0), 3),
            ])
    print(f"Wrote -> {args.out}")
    print(f"Rows: {len(videos)}")


if __name__ == "__main__":
    main()

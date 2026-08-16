#!/usr/bin/env python3
"""
Syncs YouTube video IDs and URLs from the YouTube Channel Uploads API
into output/upload_history.json and output/curated_playlists.json.
"""

import os
import sys
import json
import re
from datetime import datetime, timezone
from google.oauth2.credentials import Credentials
import googleapiclient.discovery
import googleapiclient.errors

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HOME = os.path.expanduser("~")
TOKEN_PATH = os.path.join(HOME, ".youtubeuploader", "request.token")
SECRETS_PATH = os.path.join(HOME, ".youtubeuploader", "client_secrets.json")
HISTORY_FILE = os.path.join(ROOT, "output", "upload_history.json")
PLAYLISTS_FILE = os.path.join(ROOT, "output", "curated_playlists.json")
CACHE_FILE = os.path.join(ROOT, "output", "youtube_videos_cache.json")


def load_credentials():
    if not os.path.exists(TOKEN_PATH) or not os.path.exists(SECRETS_PATH):
        print("WARN: YouTube credentials not found in ~/.youtubeuploader/")
        return None
    try:
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
            client_secret=cfg.get("client_secret")
        )
    except Exception as e:
        print(f"WARN: Error loading credentials: {e}")
        return None


def clean_str(t):
    if not t:
        return ""
    # Strip special chars, lowercase
    return re.sub(r"[^a-z0-9]", "", t.lower())


def fetch_all_youtube_videos(youtube):
    print("Fetching channel uploads playlist...")
    try:
        chans = youtube.channels().list(mine=True, part="contentDetails,snippet").execute()
    except googleapiclient.errors.HttpError as e:
        print(f"API Error fetching channel: {e}")
        return []

    if not chans.get("items"):
        print("ERROR: No channels found for credentials.")
        return []

    uploads_pid = chans["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    channel_name = chans["items"][0]["snippet"]["title"]
    print(f"Channel: {channel_name} | Uploads Playlist: {uploads_pid}")

    all_videos = []
    page_token = None
    while True:
        resp = youtube.playlistItems().list(
            playlistId=uploads_pid,
            part="snippet,status,contentDetails",
            maxResults=50,
            pageToken=page_token
        ).execute()

        items = resp.get("items", [])
        for item in items:
            vid = item["snippet"]["resourceId"]["videoId"]
            title = item["snippet"]["title"]
            published_at = item["snippet"].get("publishedAt")
            privacy = item["status"].get("privacyStatus", "unknown")
            all_videos.append({
                "video_id": vid,
                "title": title,
                "published_at": published_at,
                "privacy": privacy,
                "youtube_url": f"https://www.youtube.com/watch?v={vid}",
                "short_url": f"https://youtu.be/{vid}"
            })

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    print(f"Fetched {len(all_videos)} total videos from YouTube.")
    return all_videos


def find_matching_video(title, yt_videos):
    if not title:
        return None
    c_title = clean_str(title)
    main_part = clean_str(title.split("|")[0])
    
    # 1. Exact match cleaned
    for v in yt_videos:
        if clean_str(v["title"]) == c_title:
            return v

    # 2. Main title part exact match
    if main_part and len(main_part) >= 6:
        for v in yt_videos:
            v_main = clean_str(v["title"].split("|")[0])
            if v_main == main_part:
                return v

    # 3. Main title part substring match
    if main_part and len(main_part) >= 10:
        for v in yt_videos:
            v_clean = clean_str(v["title"])
            if main_part in v_clean or v_clean in main_part:
                return v

    # 4. Partial token intersection
    tokens = set(re.findall(r"\b\w{4,}\b", title.lower()))
    if tokens:
        best_v = None
        best_overlap = 0
        for v in yt_videos:
            v_tokens = set(re.findall(r"\b\w{4,}\b", v["title"].lower()))
            overlap = len(tokens.intersection(v_tokens))
            if overlap > best_overlap and overlap >= min(3, len(tokens)):
                best_overlap = overlap
                best_v = v
        if best_v and best_overlap >= 3:
            return best_v

    return None


def sync():
    creds = load_credentials()
    yt_videos = []
    if creds:
        try:
            yt = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
            yt_videos = fetch_all_youtube_videos(yt)
            if yt_videos:
                with open(CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump(yt_videos, f, indent=2)
        except Exception as e:
            print(f"Error fetching from YouTube API: {e}")

    if not yt_videos and os.path.exists(CACHE_FILE):
        print("Using cached YouTube videos list...")
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            yt_videos = json.load(f)

    if not yt_videos:
        print("No YouTube videos available to sync.")
        return

    # Sync upload_history.json
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)

        updated_history_count = 0
        for item in history:
            title = item.get("title", "")
            match = find_matching_video(title, yt_videos)
            if match:
                item["video_id"] = match["video_id"]
                item["youtube_url"] = match["youtube_url"]
                item["short_url"] = match["short_url"]
                updated_history_count += 1
            else:
                if "video_id" not in item:
                    item["video_id"] = None
                    item["youtube_url"] = None
                    item["short_url"] = None

        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

        print(f"Synced {updated_history_count}/{len(history)} items in {HISTORY_FILE}")

    # Sync curated_playlists.json
    if os.path.exists(PLAYLISTS_FILE):
        with open(PLAYLISTS_FILE, "r", encoding="utf-8") as f:
            playlists = json.load(f)

        updated_pl_count = 0
        total_pl_vids = 0
        for pl_name, pl_data in playlists.items():
            for v in pl_data.get("videos", []):
                total_pl_vids += 1
                match = find_matching_video(v.get("title"), yt_videos)
                if match:
                    v["video_id"] = match["video_id"]
                    v["youtube_url"] = match["youtube_url"]
                    v["short_url"] = match["short_url"]
                    updated_pl_count += 1
                else:
                    if "video_id" not in v:
                        v["video_id"] = None
                        v["youtube_url"] = None
                        v["short_url"] = None

        with open(PLAYLISTS_FILE, "w", encoding="utf-8") as f:
            json.dump(playlists, f, indent=2)

        print(f"Synced {updated_pl_count}/{total_pl_vids} videos in {PLAYLISTS_FILE}")


if __name__ == "__main__":
    sync()

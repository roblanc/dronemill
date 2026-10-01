#!/usr/bin/env python3
"""
What is already scheduled on the YouTube channel, and the next free release slots.

The cron used to schedule each new video one day after the last entry in the local
upload_history.json. That misses videos scheduled any other way (by hand in Studio, by
another script) and never fills gaps. This reads the scheduled publish times straight
from YouTube and hands out the earliest free daily slots.

Usage:
  python3 scripts/youtube_schedule.py        # list scheduled days and the next free slots
"""

import datetime
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HOME = os.environ.get("HOME", "/home/brewuser")
TOKEN_PATH = os.path.join(HOME, ".youtubeuploader", "request.token")
SECRETS_PATH = os.path.join(HOME, ".youtubeuploader", "client_secrets.json")
SLOT_HOUR_UTC = 18
MIN_LEAD_HOURS = 6     # never schedule a slot that starts sooner than this
SCAN_LIMIT = 400       # newest uploads to inspect; scheduled videos are recent uploads


def _youtube():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    import googleapiclient.discovery
    with open(TOKEN_PATH) as f:
        token = json.load(f)
    with open(SECRETS_PATH) as f:
        secrets = json.load(f)
    cfg = secrets.get("installed", secrets.get("web", {}))
    creds = Credentials(token=token.get("access_token"), refresh_token=token.get("refresh_token"),
                        token_uri="https://oauth2.googleapis.com/token",
                        client_id=cfg.get("client_id"), client_secret=cfg.get("client_secret"))
    if creds.refresh_token:
        creds.refresh(Request())
    return googleapiclient.discovery.build("youtube", "v3", credentials=creds, cache_discovery=False)


def scheduled_on_youtube(log=print):
    """Future publish times of scheduled (private + publishAt) videos, as UTC datetimes.
    Returns None if YouTube cannot be read, so the caller can fall back to local history."""
    try:
        yt = _youtube()
        chans = yt.channels().list(mine=True, part="contentDetails").execute()
        uploads = chans["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        ids, page = [], None
        while len(ids) < SCAN_LIMIT:
            resp = yt.playlistItems().list(playlistId=uploads, part="contentDetails", maxResults=50,
                                           pageToken=page).execute()
            ids += [it["contentDetails"]["videoId"] for it in resp.get("items", [])]
            page = resp.get("nextPageToken")
            if not page:
                break
        now = datetime.datetime.now(datetime.timezone.utc)
        times = []
        for i in range(0, len(ids), 50):
            resp = yt.videos().list(id=",".join(ids[i:i + 50]), part="status").execute()
            for v in resp.get("items", []):
                publish_at = v.get("status", {}).get("publishAt")
                if publish_at:
                    dt = datetime.datetime.fromisoformat(publish_at.replace("Z", "+00:00"))
                    if dt > now:
                        times.append(dt)
        return sorted(times)
    except Exception as e:
        log(f"WARN: could not read the schedule from YouTube ({str(e)[:160]}); using local history only")
        return None


def next_free_slots(occupied_days, count, now=None):
    """The earliest `count` daily slots (SLOT_HOUR_UTC) on days not in occupied_days, starting
    at least MIN_LEAD_HOURS from now."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    day = now.date()
    slots = []
    while len(slots) < count:
        slot = datetime.datetime(day.year, day.month, day.day, SLOT_HOUR_UTC, tzinfo=datetime.timezone.utc)
        if day not in occupied_days and slot - now >= datetime.timedelta(hours=MIN_LEAD_HOURS):
            slots.append(slot)
        day += datetime.timedelta(days=1)
    return slots


if __name__ == "__main__":
    times = scheduled_on_youtube()
    if times is None:
        raise SystemExit(1)
    days = sorted({t.date() for t in times})
    print(f"{len(times)} videos scheduled on YouTube across {len(days)} days")
    if days:
        print(f"first {days[0]}, last {days[-1]}")
        span = (days[-1] - days[0]).days + 1
        gaps = [days[0] + datetime.timedelta(days=i) for i in range(span)
                if days[0] + datetime.timedelta(days=i) not in set(days)]
        print("empty days inside the schedule:", ", ".join(map(str, gaps)) or "none")
    print("next free slots:", ", ".join(s.strftime("%Y-%m-%d %H:%M UTC") for s in next_free_slots(set(days), 3)))

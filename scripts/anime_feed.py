#!/usr/bin/env python3
"""
anime_feed.py: the NofaceChan (@NofaceChan55) list for the dashboard's channel switch.

Reads the anime-whatif ledger (published.json): scheduled videos first (soonest on top), then the
latest published ones. Published videos use YouTube's public thumbnail; scheduled ones are still
private on YouTube, so their thumbnail is copied from anime-whatif/thumbnails/<slug>-thumb1.* when
images_dir is given (the static GitHub Pages build). Shorts have no such file, so theirs is
downloaded through the channel's API token, which can see private videos.
"""

import datetime as dt
import glob
import json
import os
import shutil

ANIME_ROOT = os.environ.get("ANIME_ROOT", "/home/brewuser/projects/anime-whatif")
PUBLISHED_LIMIT = 40
# The publish cron sets HOME=/home/brewuser, but the NofaceChan token lives in root's home.
NOFACE_TOKEN = "/root/.youtubeuploader-anime/python_token.json"


def _api_thumbs(items, images_dir, images_url):
    """Point scheduled items that have no local thumbnail at YouTube's own copy, saved to images_dir."""
    # Always fetched again (a few small images): the thumbnail can change before the video goes out.
    todo = list(items)
    if not todo:
        return
    try:
        import sys
        import urllib.request
        if os.path.exists(NOFACE_TOKEN):
            os.environ.setdefault("NOFACE_TOKEN", NOFACE_TOKEN)
        sys.path.insert(0, os.path.join(ANIME_ROOT, "scripts"))
        import noface_youtube
        res = noface_youtube.service().videos().list(part="snippet", id=",".join(i["_id"] for i in todo)).execute()
        urls = {v["id"]: (v["snippet"]["thumbnails"].get("medium") or v["snippet"]["thumbnails"].get("high") or {}).get("url")
                for v in res.get("items", [])}
        os.makedirs(images_dir, exist_ok=True)
        for i in todo:
            if urls.get(i["_id"]):
                name = f"yt_{i['_id']}.jpg"
                with open(os.path.join(images_dir, name), "wb") as fh:
                    fh.write(urllib.request.urlopen(urls[i["_id"]], timeout=20).read())
                i["thumb"] = f"{images_url}/{name}"
    except Exception as e:
        print(f"WARN: could not fetch NofaceChan thumbnails ({e})")


def _when(entry):
    try:
        return dt.datetime.fromisoformat(entry.get("publishedAt", "").replace("Z", "+00:00"))
    except ValueError:
        return None


def anime_feed(images_dir=None, images_url=None):
    path = os.path.join(ANIME_ROOT, "published.json")
    entries = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else []
    now = dt.datetime.now(dt.timezone.utc)
    future, past = [], []
    for e in entries:
        when = _when(e)
        if not when or not e.get("id"):
            continue
        privacy = (e.get("privacy") or "").lower()
        is_future = when > now
        if privacy == "private" and not is_future:
            continue  # private uploads that never went public
        item = {
            "title": e.get("title", ""),
            "url": f"https://youtu.be/{e['id']}",
            "is_future": is_future,
            "publish_at": when.isoformat(),
            "date": when.strftime("%b %-d, %Y · %H:%M UTC") if is_future else when.strftime("%b %-d, %Y"),
            "thumb": f"https://i.ytimg.com/vi/{e['id']}/mqdefault.jpg",
            "_when": when,
            "_id": e["id"],
        }
        if is_future and images_dir and e.get("slug"):
            local = sorted(glob.glob(os.path.join(ANIME_ROOT, "thumbnails", f"{e['slug']}-thumb1.*")))
            if local:
                os.makedirs(images_dir, exist_ok=True)
                name = os.path.basename(local[0])
                shutil.copyfile(local[0], os.path.join(images_dir, name))
                item["thumb"] = f"{images_url}/{name}"
        (future if is_future else past).append(item)
    if images_dir:
        _api_thumbs([i for i in future if i["thumb"].startswith("https://i.ytimg.com/")], images_dir, images_url)
    future.sort(key=lambda i: i["_when"])
    past.sort(key=lambda i: i["_when"], reverse=True)
    out = future + past[:PUBLISHED_LIMIT]
    for i in out:
        del i["_when"], i["_id"]
    return out


if __name__ == "__main__":
    print(json.dumps(anime_feed()[:5], indent=2))

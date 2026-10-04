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


def _short_frames(out, images_dir, images_url):
    """A vertical frame from each Short's own video for the feed's Shorts shelf (its 16:9 thumbnail
    would lose the text when cropped to 9:16). The run's state.json lists the Short ids in the same
    order as output/shorts/<slug>-shorts.json lists the files."""
    import subprocess
    for i in out:
        if i["kind"] != "short" or not i["_slug"]:
            continue
        slug = i["_slug"][:-len("-short")] if i["_slug"].endswith("-short") else i["_slug"]
        try:
            ids = [m["id"] for m in json.load(open(os.path.join(ANIME_ROOT, "output", "autopilot", slug, "state.json"))).get("shorts", [])]
            files = [m["file"] for m in json.load(open(os.path.join(ANIME_ROOT, "output", "shorts", f"{slug}-shorts.json")))]
            src = files[ids.index(i["_id"])]
            dst = os.path.join(images_dir, f"short_{i['_id']}.jpg")
            if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(src):
                os.makedirs(images_dir, exist_ok=True)
                subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", "4", "-i", src, "-frames:v", "1",
                                "-vf", "scale=360:-2", "-q:v", "4", dst], check=True, timeout=60)
            i["short_thumb"] = f"{images_url}/short_{i['_id']}.jpg"
        except Exception as e:
            print(f"WARN: no Shorts frame for {i['_id']} ({e})")


def _api_enrich(out, images_dir, images_url):
    """Through the channel's API token: length and views for every item, the channel avatar, and
    YouTube's own thumbnail for scheduled items with no local one (always fetched again: it can change
    before the video goes out)."""
    todo = [i for i in out if i["is_future"] and i["thumb"].startswith("https://i.ytimg.com/")]
    try:
        import sys
        import urllib.request
        if os.path.exists(NOFACE_TOKEN):
            os.environ.setdefault("NOFACE_TOKEN", NOFACE_TOKEN)
        sys.path.insert(0, os.path.join(ANIME_ROOT, "scripts"))
        import noface_youtube
        yt = noface_youtube.service()
        res = {"items": []}
        for k in range(0, len(out), 50):
            res["items"] += yt.videos().list(part="snippet,contentDetails,statistics",
                                             id=",".join(i["_id"] for i in out[k:k + 50])).execute().get("items", [])
        info = {v["id"]: v for v in res["items"]}
        for i in out:
            v = info.get(i["_id"])
            if v:
                i["duration"] = v["contentDetails"].get("duration")
                views = v.get("statistics", {}).get("viewCount")
                i["views"] = int(views) if views is not None and not i["is_future"] else None
        urls = {vid: (v["snippet"]["thumbnails"].get("medium") or v["snippet"]["thumbnails"].get("high") or {}).get("url")
                for vid, v in info.items()}
        os.makedirs(images_dir, exist_ok=True)
        ch = yt.channels().list(mine=True, part="snippet").execute()["items"][0]["snippet"]["thumbnails"]
        avatar = (ch.get("medium") or ch.get("default") or {}).get("url")
        if avatar:
            with open(os.path.join(images_dir, "avatar.jpg"), "wb") as fh:
                fh.write(urllib.request.urlopen(avatar, timeout=20).read())
        for i in todo:
            if urls.get(i["_id"]):
                name = f"yt_{i['_id']}.jpg"
                with open(os.path.join(images_dir, name), "wb") as fh:
                    fh.write(urllib.request.urlopen(urls[i["_id"]], timeout=20).read())
                i["thumb"] = f"{images_url}/{name}"
    except Exception as e:
        print(f"WARN: could not read NofaceChan details from YouTube ({e})")


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
            "kind": "short" if e.get("kind") == "short" or (e.get("slug") or "").endswith("-short") else "video",
            "_when": when,
            "_id": e["id"],
            "_slug": e.get("slug"),
        }
        if is_future and images_dir and e.get("slug"):
            local = sorted(glob.glob(os.path.join(ANIME_ROOT, "thumbnails", f"{e['slug']}-thumb1.*")))
            if local:
                os.makedirs(images_dir, exist_ok=True)
                name = os.path.basename(local[0])
                shutil.copyfile(local[0], os.path.join(images_dir, name))
                item["thumb"] = f"{images_url}/{name}"
        (future if is_future else past).append(item)
    future.sort(key=lambda i: i["_when"])
    past.sort(key=lambda i: i["_when"], reverse=True)
    out = future + past[:PUBLISHED_LIMIT]
    if images_dir:
        _api_enrich(out, images_dir, images_url)
        _short_frames(out, images_dir, images_url)
    for i in out:
        del i["_when"], i["_id"], i["_slug"]
    return out


if __name__ == "__main__":
    print(json.dumps(anime_feed()[:5], indent=2))

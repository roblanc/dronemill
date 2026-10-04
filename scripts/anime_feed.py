#!/usr/bin/env python3
"""
anime_feed.py: the NofaceChan (@NofaceChan55) list for the dashboard's channel switch.

Reads the anime-whatif ledger (published.json): scheduled videos first (soonest on top), then the
latest published ones. Published videos use YouTube's public thumbnail; scheduled ones are still
private on YouTube, so their thumbnail is copied from anime-whatif/thumbnails/<slug>-thumb1.* when
images_dir is given (the static GitHub Pages build).
"""

import datetime as dt
import glob
import json
import os
import shutil

ANIME_ROOT = os.environ.get("ANIME_ROOT", "/home/brewuser/projects/anime-whatif")
PUBLISHED_LIMIT = 40


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
    for i in out:
        del i["_when"]
    return out


if __name__ == "__main__":
    print(json.dumps(anime_feed()[:5], indent=2))

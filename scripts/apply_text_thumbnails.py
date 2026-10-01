#!/usr/bin/env python3
"""
Applies the captioned thumbnails prepared on 2026-10-01, a limited number per run so the
YouTube API quota (thumbnails.set = 50 units) never starves the nightly uploads.

Files: images/thumb_text/out/*.jpg, manifest images/thumb_text/manifest.json,
originals of public videos in images/thumb_text/backup/, progress in images/thumb_text/applied.json.

Usage:
  python3 scripts/apply_text_thumbnails.py --max 20      # apply the next 20 not yet applied
  python3 scripts/apply_text_thumbnails.py --status
  python3 scripts/apply_text_thumbnails.py --restore 26 37   # put originals back (by number)
"""
import argparse, datetime, json, os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
BASE = os.path.join(ROOT, "images", "thumb_text")
manifest = json.load(open(os.path.join(BASE, "manifest.json")))
done_path = os.path.join(BASE, "applied.json")
done = json.load(open(done_path)) if os.path.exists(done_path) else {}

ap = argparse.ArgumentParser()
ap.add_argument("--max", type=int, default=0)
ap.add_argument("--status", action="store_true")
ap.add_argument("--restore", nargs="*", type=int)
a = ap.parse_args()

# public videos first (people see them now), newest first; scheduled ones after
order = sorted(manifest, key=lambda e: (e["privacy"] != "public", e["n"]))
if a.status:
    print(f"{len(done)}/{len(manifest)} applied; next: {[e['n'] for e in order if e['id'] not in done][:10]}")
    raise SystemExit(0)

import youtube_schedule as ys
from googleapiclient.http import MediaFileUpload
yt = ys._youtube()

def set_thumb(vid, path):
    yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(path, mimetype="image/jpeg")).execute()

if a.restore:
    for e in manifest:
        if e["n"] in a.restore:
            src = os.path.join(BASE, "backup", e["backup"]) if e.get("backup") else None
            if src and os.path.exists(src):
                set_thumb(e["id"], src); done.pop(e["id"], None); print(e["n"], "original restored")
            else:
                print(e["n"], "no original in this backup (scheduled video: see images/thumb_backup)")
    json.dump(done, open(done_path, "w"), indent=1)
    raise SystemExit(0)

count = 0
for e in order:
    if e["id"] in done or count >= a.max:
        continue
    try:
        set_thumb(e["id"], os.path.join(BASE, "out", e["file"]))
    except Exception as ex:
        msg = str(ex)
        print(f"{e['n']:03d} FAILED: {msg[:160]}", flush=True)
        if "quota" in msg.lower():
            break
        continue
    done[e["id"]] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    json.dump(done, open(done_path, "w"), indent=1)
    count += 1
    print(f"{e['n']:03d} {e['caption'][0]} applied", flush=True)
print(f"applied {count} this run; {len(done)}/{len(manifest)} total")

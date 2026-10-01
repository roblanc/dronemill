#!/usr/bin/env python3
"""
Put the original thumbnails back on videos whose thumbnail was replaced on 2026-10-01.

The originals are in images/thumb_backup/, and images/thumb_new/applied.json lists which
video got which file.

Usage:
  python3 scripts/restore_thumbnails.py              # list the replaced videos
  python3 scripts/restore_thumbnails.py all          # restore every original
  python3 scripts/restore_thumbnails.py 05 19 22     # restore some, by number from the list
"""
import json, os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
applied = json.load(open(os.path.join(ROOT, "images", "thumb_new", "applied.json")))
if len(sys.argv) == 1:
    for e in applied:
        print(f"{e['n']:02d} {e['id']} {e['title'][:70]}")
    raise SystemExit(0)
wanted = None if sys.argv[1] == "all" else {int(a) for a in sys.argv[1:]}
import youtube_schedule as ys
from googleapiclient.http import MediaFileUpload
yt = ys._youtube()
for e in applied:
    if wanted is None or e["n"] in wanted:
        yt.thumbnails().set(videoId=e["id"], media_body=MediaFileUpload(os.path.join(ROOT, e["backup"]),
                                                                        mimetype="image/jpeg")).execute()
        print(f"{e['n']:02d} {e['id']} original restored")

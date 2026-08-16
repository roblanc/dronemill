#!/usr/bin/env python3
"""
DroneMill Static Site Builder for GitHub Pages.
Exports dashboard files, schedules, playlists, and thumbnails into docs/
ready for zero-config GitHub Pages hosting.
"""

import os
import sys
import json
import shutil
import datetime
import re

ROOT = "/home/brewuser/projects/dronemill"
DOCS = f"{ROOT}/docs"

os.makedirs(f"{DOCS}/data", exist_ok=True)
os.makedirs(f"{DOCS}/images", exist_ok=True)

# 1. Export Data Endpoints
history_file = f"{ROOT}/output/upload_history.json"
now_utc = datetime.datetime.now(datetime.timezone.utc)

schedule_list = []
total_uploads = 0
future_scheduled = 0
next_release = "None"

if os.path.exists(history_file):
    with open(history_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        total_uploads = len(data)
        sched = []
        for idx, item in enumerate(data):
            p = item.get("publish_at")
            is_future = False
            release_dt_str = "Published / Instant"
            if p:
                try:
                    dt = datetime.datetime.fromisoformat(p.replace("Z", "+00:00"))
                    release_dt_str = dt.strftime("%A, %b %d, %Y — %H:%M UTC")
                    is_future = dt > now_utc
                    if is_future:
                        sched.append((dt, item.get("title")))
                except Exception:
                    release_dt_str = p

            vid_id = item.get("video_id")
            yt_url = item.get("youtube_url")
            if vid_id and not yt_url:
                yt_url = f"https://www.youtube.com/watch?v={vid_id}"

            schedule_list.append({
                "id": idx + 1,
                "title": item.get("title"),
                "publish_at": p,
                "release_formatted": release_dt_str,
                "is_future": is_future,
                "privacy": item.get("privacy", "unlisted"),
                "thumbnail": item.get("thumbnail"),
                "tags": item.get("tags", []),
                "description": item.get("description", ""),
                "video_id": vid_id,
                "youtube_url": yt_url,
                "short_url": item.get("short_url") or (f"https://youtu.be/{vid_id}" if vid_id else None)
            })
            
        sched.sort()
        future_scheduled = len(sched)
        if sched:
            next_release = f"{sched[0][1]} ({sched[0][0].strftime('%b %d, %H:%M UTC')})"

    # Separate future scheduled releases (chronological soonest first) and published releases (newest first)
    future_list = [x for x in schedule_list if x["is_future"]]
    def get_dt(x):
        p = x.get("publish_at")
        try:
            return datetime.datetime.fromisoformat(p.replace("Z", "+00:00"))
        except Exception:
            return datetime.datetime.max.replace(tzinfo=datetime.timezone.utc)
    future_list.sort(key=get_dt)

    past_list = [x for x in schedule_list if not x["is_future"]]
    past_list.reverse()

    schedule_list = future_list + past_list

status_obj = {
    "server_time_utc": now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
    "total_disk_gb": 37.2,
    "used_disk_gb": 23.9,
    "free_disk_gb": 11.8,
    "disk_percent": 64.1,
    "total_uploads": total_uploads,
    "future_scheduled_count": future_scheduled,
    "next_release": next_release,
    "master_lufs": -22.0,
    "audio_engine": "AI Hybrid 5-Engine Conductor (Active)"
}

with open(f"{DOCS}/data/status.json", "w", encoding="utf-8") as f:
    json.dump(status_obj, f, indent=2)

with open(f"{DOCS}/data/schedule.json", "w", encoding="utf-8") as f:
    json.dump(schedule_list, f, indent=2)

# Copy Playlists
pl_file = f"{ROOT}/output/curated_playlists.json"
if os.path.exists(pl_file):
    shutil.copyfile(pl_file, f"{DOCS}/data/playlists.json")
else:
    with open(f"{DOCS}/data/playlists.json", "w", encoding="utf-8") as f:
        json.dump({}, f)

# Copy Community Posts
community_posts = [
    {
        "type": "Lore Teaser",
        "title": "The Keeper of the Sea Wall",
        "content": "Deep into the 1890s archives, old logbooks spoke of nights when the tide did not ebb, but pulsed with cold light. What do you listen for when the ocean goes quiet?\n\nNew atmospheric piece premiering Monday at 18:00 UTC. 🌊🎧",
        "poll_options": ["The tide retreating", "The hull groaning", "The silence beneath", "Distant bells"]
    },
    {
        "type": "Upcoming Spotlight",
        "title": "Subterranean Bathhouse at 4 AM",
        "content": "Steam hanging between pale mint tiles, distant water ripples echoing through empty stone archways. Where does your mind drift when you are the only one awake?\n\nJoin us Saturday for the next Liminal Soundscape premiere. 🌿🛁",
        "poll_options": ["Total tranquility", "Quiet nostalgia", "Uncanny isolation", "Deep focus / study"]
    },
    {
        "type": "Sci-Fi Atmosphere",
        "title": "The Botanist's Tea on Europa",
        "content": "Watching the cracked azure ice plains of Europa while Jupiter slowly rotates in the cosmic dark. What is your go-to soundtrack for deep space reading? ☕🪐",
        "poll_options": ["Analog warm synths", "Sub-bass room drones", "Soft acoustic rain", "Pure cosmic silence"]
    }
]
with open(f"{DOCS}/data/community.json", "w", encoding="utf-8") as f:
    json.dump(community_posts, f, indent=2)

# 2. Copy Images to docs/images/
image_dirs = [f"{ROOT}/images/fresh", f"{ROOT}/images/slate", f"{ROOT}/images"]
for d in image_dirs:
    if os.path.exists(d):
        for fname in os.listdir(d):
            if fname.lower().endswith(('.jpg', '.png', '.jpeg')):
                src = os.path.join(d, fname)
                dst = os.path.join(f"{DOCS}/images", fname)
                if not os.path.exists(dst):
                    shutil.copyfile(src, dst)

# 3. Copy Web App Frontend assets to docs/ with cache busting
v_tag = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

with open(f"{ROOT}/dashboard/index.html", "r", encoding="utf-8") as f:
    html_content = f.read()

# Replace any css/js cache tags with latest timestamp
html_content = re.sub(r'href="app\.css(\?v=[^"]*)?"', f'href="app.css?v={v_tag}"', html_content)
html_content = re.sub(r'src="app\.js(\?v=[^"]*)?"', f'src="app.js?v={v_tag}"', html_content)

with open(f"{DOCS}/index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

shutil.copyfile(f"{ROOT}/dashboard/app.css", f"{DOCS}/app.css")

# Adapt app.js to fetch from static data files when on GitHub Pages or static host
with open(f"{ROOT}/dashboard/app.js", "r", encoding="utf-8") as f:
    js_content = f.read()

# Replace API endpoints with relative data files for GitHub Pages compatibility
js_static = js_content.replace("'/api/status'", f"'data/status.json?v={v_tag}'")
js_static = js_static.replace("'/api/schedule'", f"'data/schedule.json?v={v_tag}'")
js_static = js_static.replace("'/api/playlists'", f"'data/playlists.json?v={v_tag}'")
js_static = js_static.replace("'/api/community-posts'", f"'data/community.json?v={v_tag}'")
js_static = js_static.replace("`/media/image/${encodeURIComponent(item.thumbnail)}`", "`images/${encodeURIComponent(item.thumbnail)}`")

with open(f"{DOCS}/app.js", "w", encoding="utf-8") as f:
    f.write(js_static)

# Add .nojekyll so GitHub Pages doesn't ignore anything
with open(f"{DOCS}/.nojekyll", "w") as f:
    f.write("")

print("✨ Successfully built static GitHub Pages distribution in docs/")

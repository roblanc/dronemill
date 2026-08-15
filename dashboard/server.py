#!/usr/bin/env python3
"""
DroneMill Command Center Backend Server.
Provides REST APIs for release schedule, media streaming, playlists,
community posts, and channel health telemetry.
"""

import os
import sys
import json
import datetime
import shutil
import http.server
import socketserver
import urllib.parse

PORT = 8888
ROOT = "/home/brewuser/projects/dronemill"

class DroneMillHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=f"{ROOT}/dashboard", **kwargs)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/status":
            self.send_json(self.get_status())
        elif path == "/api/schedule":
            self.send_json(self.get_schedule())
        elif path == "/api/playlists":
            self.send_json(self.get_playlists())
        elif path == "/api/community-posts":
            self.send_json(self.get_community_posts())
        elif path.startswith("/media/image/"):
            img_name = urllib.parse.unquote(path.replace("/media/image/", ""))
            self.serve_file_from_dirs(img_name, [
                f"{ROOT}/images/fresh",
                f"{ROOT}/images/slate",
                f"{ROOT}/images",
                f"{ROOT}/images/queue"
            ], "image/jpeg")
        elif path.startswith("/media/audio/"):
            audio_name = urllib.parse.unquote(path.replace("/media/audio/", ""))
            self.serve_file_from_dirs(audio_name, [
                f"{ROOT}/audio/fresh",
                f"{ROOT}/audio/slate",
                f"{ROOT}/audio/lovecraft",
                f"{ROOT}/audio/samples",
                f"{ROOT}/audio"
            ], "audio/wav")
        else:
            super().do_GET()

    def send_json(self, data, status=200):
        body = json.dumps(data, indent=2).encode('utf-8')
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_file_from_dirs(self, filename, dirs, content_type):
        for d in dirs:
            target = os.path.join(d, filename)
            if os.path.isfile(target):
                size = os.path.getsize(target)
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(size))
                self.end_headers()
                with open(target, 'rb') as f:
                    shutil.copyfileobj(f, self.wfile)
                return
        self.send_error(404, f"File {filename} not found")

    def get_status(self):
        total, used, free = shutil.disk_usage(ROOT)
        gb = 1024 ** 3
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        
        history_file = f"{ROOT}/output/upload_history.json"
        total_uploads = 0
        future_scheduled = 0
        next_release = "None"
        
        if os.path.exists(history_file):
            with open(history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                total_uploads = len(data)
                sched = []
                for item in data:
                    p = item.get("publish_at")
                    if p:
                        try:
                            dt = datetime.datetime.fromisoformat(p.replace("Z", "+00:00"))
                            if dt > now_utc:
                                sched.append((dt, item.get("title")))
                        except Exception:
                            pass
                sched.sort()
                future_scheduled = len(sched)
                if sched:
                    next_release = f"{sched[0][1]} ({sched[0][0].strftime('%b %d, %H:%M UTC')})"

        return {
            "server_time_utc": now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "total_disk_gb": round(total / gb, 1),
            "used_disk_gb": round(used / gb, 1),
            "free_disk_gb": round(free / gb, 1),
            "disk_percent": round((used / total) * 100, 1),
            "total_uploads": total_uploads,
            "future_scheduled_count": future_scheduled,
            "next_release": next_release,
            "master_lufs": -22.0,
            "audio_engine": "AI Hybrid 5-Engine Conductor (Active)"
        }

    def get_schedule(self):
        history_file = f"{ROOT}/output/upload_history.json"
        if not os.path.exists(history_file):
            return []
            
        with open(history_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        now_utc = datetime.datetime.now(datetime.timezone.utc)
        results = []
        for idx, item in enumerate(data):
            p = item.get("publish_at")
            is_future = False
            release_dt_str = "Published / Instant"
            if p:
                try:
                    dt = datetime.datetime.fromisoformat(p.replace("Z", "+00:00"))
                    release_dt_str = dt.strftime("%A, %b %d, %Y — %H:%M UTC")
                    is_future = dt > now_utc
                except Exception:
                    release_dt_str = p

            results.append({
                "id": idx + 1,
                "title": item.get("title"),
                "publish_at": p,
                "release_formatted": release_dt_str,
                "is_future": is_future,
                "privacy": item.get("privacy", "unlisted"),
                "thumbnail": item.get("thumbnail"),
                "tags": item.get("tags", []),
                "description": item.get("description", "")
            })

        # Return latest scheduled first or sorted
        results.reverse()
        return results

    def get_playlists(self):
        pl_file = f"{ROOT}/output/curated_playlists.json"
        if os.path.exists(pl_file):
            with open(pl_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def get_community_posts(self):
        return [
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

if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), DroneMillHandler) as httpd:
        print(f"🚀 DroneMill Dashboard Server running on http://0.0.0.0:{PORT}")
        httpd.serve_forever()

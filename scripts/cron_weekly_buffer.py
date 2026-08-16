#!/usr/bin/env python3
"""
DroneMill Full Autonomous Cron Engine & Buffer Refiller.
Runs periodically via cron:
1. Checks how many future scheduled days remain in the release calendar.
2. If runway < 10 days, automatically generates novel unrepeated concepts, audio, and videos.
3. Uploads and schedules them on YouTube for uninterrupted daily releases at 18:00 UTC.
4. Updates GitHub Pages dashboard and pushes live to main.
"""

import os
import sys
import json
import datetime
import subprocess
import time

ROOT = "/home/brewuser/projects/dronemill"
sys.path.append(f"{ROOT}/scripts")

import idea_generator
from ai_hybrid_sound_conductor import build_hybrid_soundscape, run_cmd

LOCK_FILE = "/tmp/dronemill_cron.lock"
LOG_FILE = f"{ROOT}/output/cron_buffer.log"


def log(msg):
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{timestamp}] {msg}"
    print(line)
    try:
        os.makedirs(f"{ROOT}/output", exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def get_schedule_status():
    history_file = f"{ROOT}/output/upload_history.json"
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    future_scheduled = []

    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                for item in json.load(f):
                    p = item.get("publish_at")
                    if p:
                        try:
                            dt = datetime.datetime.fromisoformat(p.replace("Z", "+00:00"))
                            if dt > now_utc:
                                future_scheduled.append(dt)
                        except Exception:
                            pass
        except Exception as e:
            log(f"Error reading history file: {e}")

    future_scheduled.sort()
    last_dt = future_scheduled[-1] if future_scheduled else now_utc
    return len(future_scheduled), last_dt


def produce_and_schedule_single(concept, slot_dt):
    pub_iso = slot_dt.strftime("%Y-%m-%dT18:00:00Z")
    slug = re_slug(concept["title"])
    log(f"🎬 Producing release: {concept['title']} for {pub_iso}")

    # 1. Image preparation
    image_path = None
    # Check if any unused images in images/fresh or images/queue
    fresh_dir = f"{ROOT}/images/fresh"
    if os.path.exists(fresh_dir):
        fresh_files = sorted([os.path.join(fresh_dir, f) for f in os.listdir(fresh_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))])
        if fresh_files:
            image_path = fresh_files[0]
            # Move to used once scheduled
    
    if not image_path:
        # Check images/queue
        queue_dir = f"{ROOT}/images/queue"
        if os.path.exists(queue_dir):
            q_files = sorted([os.path.join(queue_dir, f) for f in os.listdir(queue_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))])
            if q_files:
                image_path = q_files[0]

    if not image_path:
        # Fallback to rich themed artwork in images
        image_path = f"{ROOT}/images/liminal_poolrooms_sanctuary.jpg"

    # 2. Audio generation via AI Hybrid 5-Engine
    master_audio = f"{ROOT}/output/{slug}_master.wav"
    build_hybrid_soundscape(
        ls_prompt=concept["image_prompt"],
        foley_samples=concept["foley"],
        dsp_freqs=concept["dsp_freqs"],
        dsp_lfos=concept["dsp_lfos"],
        out_wav=master_audio,
        duration_sec=7200 # 2 hours
    )

    # 3. Video Render with FFmpeg
    out_mp4 = f"{ROOT}/output/{slug}.mp4"
    overlay = concept["overlay"]
    opacity = concept["overlay_opacity"]
    
    cmd_render = f"""
    ffmpeg -y \
      -loop 1 -framerate 24 -i "{image_path}" \
      -stream_loop -1 -i "{overlay}" \
      -i "{master_audio}" \
      -filter_complex "
        [0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,format=gbrp[base];
        [1:v]scale=1920:1080:flags=lanczos,curves=all='0/0 0.12/0 0.50/0.35 1/0.85',format=gbrp[fx];
        [base][fx]blend=all_mode=screen:all_opacity={opacity}[merged];
        [merged]vignette=angle=0.32,noise=alls=0.6:allf=t+u,format=yuv420p[vout]
      " -map "[vout]" -map "2:a" \
      -c:v libx264 -preset ultrafast -crf 20 -c:a aac -b:a 256k -ar 48000 -t 7200 -movflags +faststart "{out_mp4}"
    """
    run_cmd(cmd_render, f"Rendering 2h video -> {out_mp4}")

    # 4. Write description file
    desc_file = f"/tmp/desc_{os.getpid()}_{int(time.time())}.txt"
    with open(desc_file, "w", encoding="utf-8") as f:
        f.write(concept["description"])

    # 5. Upload & Schedule via upload-yt.sh
    cmd_upload = f"\"{ROOT}/scripts/upload-yt.sh\" \"{out_mp4}\" \"{concept['title']}\" \"{desc_file}\" \"{image_path}\" \"private\" \"{concept['tags']}\" \"{pub_iso}\""
    run_cmd(cmd_upload, f"Uploading and scheduling on YouTube for {pub_iso}")

    if os.path.exists(desc_file):
        os.remove(desc_file)
    if os.path.exists(master_audio):
        os.remove(master_audio)

    # Save idea to history
    idea_generator.save_used_idea(concept["title"])
    log(f"✅ Successfully scheduled: {concept['title']} ({pub_iso})")


def re_slug(t):
    s = t.split("|")[0].lower()
    return "".join(c if c.isalnum() else "-" for c in s).strip("-")


def run_cron_cycle():
    # Lockfile check
    if os.path.exists(LOCK_FILE):
        log("WARN: Another cron process is active. Skipping cycle.")
        return

    try:
        with open(LOCK_FILE, "w") as f:
            f.write(str(os.getpid()))

        log("🚀 Checking DroneMill release runway status...")
        days_left, last_dt = get_schedule_status()
        log(f"Current Buffer: {days_left} future scheduled days on YouTube (Last slot: {last_dt.strftime('%Y-%m-%d %H:%M UTC')}).")

        MIN_THRESHOLD = 10
        TARGET_BUFFER = 14

        if days_left < MIN_THRESHOLD:
            needed = TARGET_BUFFER - days_left
            log(f"⚠️ Buffer ({days_left} days) is below threshold ({MIN_THRESHOLD} days). Refilling {needed} new releases...")
            
            curr_slot = last_dt
            for i in range(needed):
                curr_slot += datetime.timedelta(days=1)
                concept = idea_generator.generate_novel_concept()
                if not concept:
                    log("ERROR: Could not generate novel concept. Aborting.")
                    break
                produce_and_schedule_single(concept, curr_slot)

            # Sync IDs and rebuild GitHub Pages
            log("🔄 Syncing YouTube video IDs and updating GitHub Pages dashboard...")
            subprocess.run(["python3", f"{ROOT}/scripts/sync-youtube-ids.py"])
            subprocess.run(["python3", f"{ROOT}/scripts/build_github_pages.py"])
            subprocess.run([f"{ROOT}/scripts/publish-dashboard.sh"])
            log("✨ Buffer refill cycle completed successfully!")
        else:
            log(f"✅ Buffer is healthy ({days_left} days remaining, target is {TARGET_BUFFER}). Re-checking sync & status.")
            # Light telemetry sync and build
            subprocess.run(["python3", f"{ROOT}/scripts/build_github_pages.py"])
            subprocess.run(["bash", f"{ROOT}/scripts/publish-dashboard.sh"])

    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)


if __name__ == "__main__":
    run_cron_cycle()

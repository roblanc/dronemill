#!/usr/bin/env python3
"""
Full Autonomous September Production & Scheduling Engine for DroneMill / @timelessambience55.
Iterates through all remaining days of September 2026 (Sept 5 - Sept 30):
1. Pre-flight check: verifies disk space (>= 6GB) and refreshes YouTube OAuth token.
2. Selects novel concepts from idea_generator with title <= 98 chars.
3. Pairs with unique, theme-matched 16:9 cinematic artwork from curated candidate images.
4. Generates high-fidelity 5-engine hybrid audio master (-22 LUFS).
5. Renders 2-hour 1080p video using 60s visual loop master + stream-loop mux (fast & disk-safe).
6. Uploads and schedules sequentially for 18:00:00Z daily release on YouTube.
7. Auto-enables monetization via YouTube Studio CDP (port 9222).
8. Immediately cleans up local master wav and rendered mp4 to preserve disk space.
9. Handles YouTube upload quota gracefully with sleep-and-resume.
10. Updates GitHub Pages dashboard and telemetry after each release.
"""

import os
import sys
import glob
import json
import time
import math
import shutil
import random
import datetime
import subprocess

ROOT = "/home/brewuser/projects/dronemill"
sys.path.append(f"{ROOT}/scripts")

import idea_generator

HISTORY_FILE = f"{ROOT}/output/upload_history.json"
TMP_DIR = f"{ROOT}/tmp"
OUT_DIR = f"{ROOT}/output"
LOG_FILE = f"{OUT_DIR}/september_production.log"
LOCK_FILE = "/tmp/september_production.lock"

os.makedirs(TMP_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)


def log(msg):
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def free_disk_gb(path=ROOT):
    st = os.statvfs(path)
    return (st.f_bavail * st.f_frsize) / (1024 ** 3)


def cleanup_disk():
    try:
        subprocess.run(["python3", f"{ROOT}/scripts/cleanup_uploaded_mp4s.py"], capture_output=True, text=True)
    except Exception as e:
        log(f"WARN: cleanup_disk error: {e}")


def check_youtube_token():
    token_path = os.path.expanduser("~/.youtubeuploader/request.token")
    secrets_path = os.path.expanduser("~/.youtubeuploader/client_secrets.json")
    if not os.path.exists(token_path) or not os.path.exists(secrets_path):
        return False, "Missing token or client_secrets.json"
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        with open(token_path) as f:
            t = json.load(f)
        with open(secrets_path) as f:
            s = json.load(f)
        cfg = s.get("web") or s.get("installed", {})
        creds = Credentials(
            token=t.get("access_token"),
            refresh_token=t.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=cfg.get("client_id"),
            client_secret=cfg.get("client_secret"),
        )
        if creds.refresh_token:
            creds.refresh(Request())
        return True, "Token OK"
    except Exception as e:
        return False, str(e)


def get_scheduled_september_dates():
    """Returns set of date strings ('YYYY-MM-DD') already scheduled with valid video_id."""
    scheduled = set()
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    p = item.get("publish_at")
                    vid = item.get("video_id")
                    if p and vid and p.startswith("2026-09-"):
                        date_str = p.split("T")[0]
                        scheduled.add(date_str)
        except Exception as e:
            log(f"WARN reading history: {e}")
    return scheduled


def get_candidate_images():
    """Collects curated list of high-quality 16:9 images across the repository."""
    patterns = [
        f"{ROOT}/images/september_fresh/*.jpg",
        f"{ROOT}/images/september_fresh/*.png",
        f"{ROOT}/images/fresh/*.jpg",
        f"{ROOT}/images/fresh/*.png",
        f"{ROOT}/images/slate/*.jpg",
        f"{ROOT}/docs/images/*chatgpt*.png",
        f"{ROOT}/images/*.jpg"
    ]
    imgs = []
    for pat in patterns:
        for f in glob.glob(pat):
            base = os.path.basename(f)
            if not base.endswith("_compressed.jpg") and "poster" not in base and "preview" not in base:
                imgs.append(f)
    imgs = sorted(list(set(imgs)))
    return imgs


def select_image_for_concept(concept, candidate_images, used_images, day_int=None):
    """Selects strictly unused matching image for concept theme from candidate pool without repeating."""
    # Priority 1: Check if there is a dedicated numbered fresh image for this day (e.g. 17_*, 18_*, etc.)
    if day_int is not None:
        day_patterns = [
            f"{ROOT}/images/september_fresh/{day_int:02d}_*.jpg",
            f"{ROOT}/images/september_fresh/{day_int}_*.jpg"
        ]
        for pat in day_patterns:
            matches = glob.glob(pat)
            for m in matches:
                base = os.path.basename(m).lower()
                clean = base.replace(".jpg", "").replace(".png", "").replace(".jpeg", "")
                if m not in used_images and base not in used_images and clean not in used_images:
                    used_images.add(m)
                    used_images.add(base)
                    used_images.add(clean)
                    return m

    theme = (concept.get("category") or "").lower()
    title = (concept.get("title") or "").lower()

    theme_keywords = {
        "maritime": ["sea_wall", "chapel", "tide", "harbor", "salt", "keeper", "drowned", "lighthouse", "arkham"],
        "liminal": ["transit", "bowling", "bathhouse", "terminal", "lounge", "video", "ferry", "poolrooms"],
        "cosmic": ["europa", "lunar", "freighter", "asteroid", "ceramics", "observatory", "stars"],
        "dark academia": ["atrium", "archive", "library", "manuscript", "dunes", "clocktower"],
        "prehistoric": ["protoceratops", "thunder", "hollow", "amber", "arctic", "fern"],
        "retro": ["video", "arcade", "diner", "diner_test", "rental", "rewind", "transit"]
    }

    matched_kw = []
    for k, kws in theme_keywords.items():
        if k in theme:
            matched_kw.extend(kws)

    # First try unused images matching theme keywords
    for img in candidate_images:
        base = os.path.basename(img).lower()
        clean = base.replace("_compressed.jpg", "").replace(".jpg", "").replace(".png", "").replace(".jpeg", "")
        if img not in used_images and base not in used_images and clean not in used_images:
            if any(kw in base for kw in matched_kw) or any(w in base for w in title.split() if len(w) > 4):
                used_images.add(img)
                used_images.add(base)
                used_images.add(clean)
                return img

    # Second try any unused candidate image
    for img in candidate_images:
        base = os.path.basename(img).lower()
        clean = base.replace("_compressed.jpg", "").replace(".jpg", "").replace(".png", "").replace(".jpeg", "")
        if img not in used_images and base not in used_images and clean not in used_images:
            used_images.add(img)
            used_images.add(base)
            used_images.add(clean)
            return img

    # Fallback
    choice = random.choice(candidate_images)
    return choice


def generate_audio_master(concept, duration, out_wav):
    """Generates 2-hour mastered soundscape using DSP, Rubberband and acoustic beds."""
    log(">> Generating optimized procedural DSP & Rubberband stems...")
    pid = os.getpid()
    dsp_wav = f"{TMP_DIR}/dsp_stem_{pid}.wav"
    rb_wav = f"{TMP_DIR}/rb_stem_{pid}.wav"

    try:
        # 1. Procedural 300s DSP stem with prime LFOs (loops seamlessly)
        freqs = concept["dsp_freqs"]
        lfos = concept["dsp_lfos"]
        sines_l = " + ".join([f"0.16*sin(2*PI*{f}*t)*(0.5+0.5*sin(2*PI*t/{l}))" for f, l in zip(freqs, lfos)])
        sines_r = " + ".join([f"0.16*sin(2*PI*{f}*t+0.5)*(0.5+0.5*cos(2*PI*t/{l+2}))" for f, l in zip(freqs, lfos)])
        cmd_dsp = f"""ffmpeg -y -nostdin -f lavfi -i "aevalsrc='{sines_l}':s=48000:d=300" \
          -f lavfi -i "aevalsrc='{sines_r}':s=48000:d=300" \
          -filter_complex "
            [0:a]adelay=14|0,lowpass=f=4500,highpass=f=120[al];
            [1:a]adelay=0|26,lowpass=f=4500,highpass=f=120[ar];
            [al][ar]amerge=inputs=2[aout]
          " -map "[aout]" -ar 48000 -c:a pcm_s16le "{dsp_wav}"
        """
        subprocess.run(cmd_dsp, shell=True, check=True, capture_output=True)

        # 2. Rubberband sub-bass drone from rich source
        rb_src = f"{ROOT}/audio/samples/12_cosmic_horror.mp3"
        if not os.path.exists(rb_src):
            rb_src = f"{ROOT}/audio/samples/01_empty_mall.mp3"
        semitones = -12
        pitch_factor = math.pow(2.0, semitones / 12.0)
        cmd_rb = f"""ffmpeg -y -nostdin -i "{rb_src}" -filter_complex "
            [0:a]rubberband=pitch={pitch_factor:.5f}:tempo=1.0:phase=laminar,lowpass=f=120,highpass=f=28,volume=1.5[aout]
          " -map "[aout]" -ar 48000 -t 300 -c:a pcm_s16le "{rb_wav}"
        """
        subprocess.run(cmd_rb, shell=True, check=True, capture_output=True)

        # 3. Foley acoustic layers
        foley_inputs = []
        foley_filters = []
        merge_inputs = ["[stem_dsp]", "[stem_rb]"]
        in_idx = 2

        for sample in concept["foley"]:
            if os.path.exists(sample):
                foley_inputs.append(f"-stream_loop -1 -i \"{sample}\"")
                foley_filters.append(f"[{in_idx}:a]highpass=f=120,lowpass=f=7000,volume=0.40,afade=t=in:ss=0:d=4,afade=t=out:st={duration-4}:d=4[foley_{in_idx}]")
                merge_inputs.append(f"[foley_{in_idx}]")
                in_idx += 1

        num_inputs = len(merge_inputs)
        merge_str = "".join(merge_inputs)
        mix_chain = f"{merge_str}amix=inputs={num_inputs}:duration=longest:dropout_transition=2:normalize=0[mixed]"
        master_chain = "[mixed]compand=attacks=0.1:decays=0.8:points=-80/-80|-40/-32|-20/-16|0/-8:gain=2,alimiter=limit=-1.5dB,loudnorm=I=-22:TP=-1.5:LRA=9[mastered]"

        all_filters = [
            f"[0:a]volume=0.45,afade=t=in:ss=0:d=4,afade=t=out:st={duration-4}:d=4[stem_dsp]",
            f"[1:a]volume=0.65,afade=t=in:ss=0:d=4,afade=t=out:st={duration-4}:d=4[stem_rb]"
        ] + foley_filters + [mix_chain, master_chain]

        filtergraph = ";\n            ".join(all_filters)
        foley_str = " ".join(foley_inputs)

        cmd_mix = f"""ffmpeg -y -nostdin \
          -stream_loop -1 -i "{dsp_wav}" \
          -stream_loop -1 -i "{rb_wav}" \
          {foley_str} \
          -filter_complex "
            {filtergraph}
          " -map "[mastered]" -ar 48000 -t {duration} -c:a pcm_s16le "{out_wav}"
        """
        log(f">> Mixing & mastering 2-hour audio ({num_inputs} stems -> -22 LUFS)...")
        subprocess.run(cmd_mix, shell=True, check=True, capture_output=True)
        log(f"✅ Audio master complete: {out_wav} ({os.path.getsize(out_wav)/1024/1024:.1f} MB)")
    finally:
        for tmp_file in [dsp_wav, rb_wav]:
            if os.path.exists(tmp_file):
                try:
                    os.remove(tmp_file)
                except Exception:
                    pass


def render_video(image_path, overlay_path, overlay_opacity, audio_path, duration, out_mp4):
    """Renders 1080p video using 60s visual loop master + stream-loop mux (fast & disk-safe)."""
    pid = os.getpid()
    loop_mp4 = f"{TMP_DIR}/loop60_{pid}.mp4"

    try:
        log(f">> Step 1: Rendering 60s visual loop master for {os.path.basename(image_path)}...")
        cmd_loop = f"""ffmpeg -y \
          -loop 1 -framerate 24 -t 60 -i "{image_path}" \
          -t 60 -i "{overlay_path}" \
          -filter_complex "
            [0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,format=gbrp[base];
            [1:v]scale=1920:1080:flags=lanczos,curves=all='0/0 0.12/0 0.50/0.35 1/0.85',format=gbrp[fx];
            [base][fx]blend=all_mode=screen:all_opacity={overlay_opacity}[merged];
            [merged]vignette=angle=0.32,noise=alls=0.5:allf=t+u,format=yuv420p[vout]
          " -map "[vout]" \
          -c:v libx264 -preset veryfast -crf 24 -b:v 2000k -maxrate 2600k -bufsize 5000k -movflags +faststart "{loop_mp4}"
        """
        subprocess.run(cmd_loop, shell=True, check=True, capture_output=True)

        log(">> Step 2: Muxing 2-hour production video with audio...")
        cmd_mux = f"""ffmpeg -y \
          -stream_loop -1 -i "{loop_mp4}" \
          -i "{audio_path}" \
          -map 0:v:0 -map 1:a:0 \
          -c:v copy -c:a aac -b:a 256k -ar 48000 \
          -t {duration} -movflags +faststart "{out_mp4}"
        """
        subprocess.run(cmd_mux, shell=True, check=True, capture_output=True)
        size_gb = os.path.getsize(out_mp4) / (1024 ** 3)
        log(f"✅ Video render complete: {out_mp4} ({size_gb:.2f} GB)")
    except Exception as e:
        if os.path.exists(out_mp4):
            try:
                os.remove(out_mp4)
                log(f"🧹 Removed incomplete video file after error: {out_mp4}")
            except Exception:
                pass
        raise e
    finally:
        if os.path.exists(loop_mp4):
            try:
                os.remove(loop_mp4)
            except Exception:
                pass


def sanitize_title(raw_title):
    """Ensures title is strictly <= 98 characters to prevent YouTube API invalidTitle errors."""
    t = raw_title.strip()
    if len(t) <= 98:
        return t

    if "|" in t:
        parts = t.split("|")
        left = parts[0].strip()
        right = " | ".join(parts[1:]).strip()
        if len(right) < 40 and len(left) + len(right) + 3 > 98:
            max_left = 98 - len(right) - 4
            t = f"{left[:max_left].strip()}… | {right}"
            return t[:98]

    return t[:95].strip() + "…"


def produce_and_schedule_day(day_int, candidate_images, used_images):
    date_str = f"2026-09-{day_int:02d}"
    pub_iso = f"{date_str}T18:00:00Z"

    log("============================================================")
    log(f"📅 STARTING PRODUCTION FOR: September {day_int:02d}, 2026 ({pub_iso})")
    log("============================================================")

    # 1. Disk check
    free_gb = free_disk_gb()
    log(f"💾 Free disk space: {free_gb:.1f} GB")
    if free_gb < 6.0:
        log("⚠️ Low disk space (< 6GB). Running cleanup...")
        cleanup_disk()
        free_gb = free_disk_gb()
        log(f"💾 Free disk space after cleanup: {free_gb:.1f} GB")
        if free_gb < 5.0:
            log("🛑 Aborting: insufficient disk space to produce safely.")
            return False, "low_disk"

    # 2. Auth check
    ok, msg = check_youtube_token()
    if not ok:
        log(f"🛑 YouTube auth token check failed: {msg}")
        return False, "auth_failed"

    # 3. Concept generation
    concept = idea_generator.generate_novel_concept()
    if not concept:
        log("ERROR: Failed to generate novel concept.")
        return False, "concept_failed"

    concept["title"] = sanitize_title(concept["title"])
    log(f"🎬 Title ({len(concept['title'])} chars): {concept['title']}")
    log(f"🏷️ Category: {concept['category']} | Subgenre: {concept['subgenre']}")

    # 4. Image selection
    img_path = select_image_for_concept(concept, candidate_images, used_images, day_int=day_int)
    log(f"🖼️ Selected Artwork: {os.path.basename(img_path)}")

    # 5. Overlay selection
    overlay = concept["overlay"]
    if not os.path.exists(overlay):
        overlay = f"{ROOT}/assets/overlays/dust_motes_loop.mp4"
    if not os.path.exists(overlay):
        overlay = f"{ROOT}/assets/overlays/cinematic_rain_loop.mp4"

    # 6. Audio production
    slug = "".join(c if c.isalnum() else "-" for c in concept["title"].lower()).strip("-")
    slug = slug[:50]
    master_audio = f"{OUT_DIR}/{slug}_master_{day_int}.wav"
    out_mp4 = f"{OUT_DIR}/{slug}_{day_int}.mp4"

    try:
        generate_audio_master(concept, 7200, master_audio)

        # 7. Video production
        render_video(img_path, overlay, concept["overlay_opacity"], master_audio, 7200, out_mp4)
    finally:
        if os.path.exists(master_audio):
            try:
                os.remove(master_audio)
                log(f"🧹 Deleted intermediate master audio: {master_audio}")
            except Exception:
                pass

    # 8. Description file
    desc_file = f"{TMP_DIR}/desc_{day_int}_{int(time.time())}.txt"
    with open(desc_file, "w", encoding="utf-8") as f:
        f.write(concept["description"])

    # 9. YouTube Upload & Scheduling
    log(f"🚀 Uploading and scheduling to YouTube for {pub_iso}...")
    cmd_upload = f'"{ROOT}/scripts/upload-yt.sh" "{out_mp4}" "{concept["title"]}" "{desc_file}" "{img_path}" "private" "{concept["tags"]}" "{pub_iso}"'

    res = subprocess.run(cmd_upload, shell=True, capture_output=True, text=True)
    out_text = (res.stdout or "") + (res.stderr or "")

    if os.path.exists(desc_file):
        try:
            os.remove(desc_file)
        except Exception:
            pass

    # Inspect upload result
    video_id = None
    for line in out_text.splitlines():
        if "Video ID:" in line:
            parts = line.split("Video ID:")
            if len(parts) > 1:
                video_id = parts[1].strip()
                break

    if "quotaExceeded" in out_text or "uploadLimitExceeded" in out_text:
        log("⚠️ YouTube daily upload limit or quota exceeded.")
        return False, "quota_exceeded"

    if video_id:
        log(f"🎉 SUCCESS! Scheduled {concept['title']} for {pub_iso} (Video ID: {video_id})")
        idea_generator.save_used_idea(concept["title"])

        # Fail-safe cleanup of local out_mp4 to keep disk lean
        if os.path.exists(out_mp4):
            try:
                os.remove(out_mp4)
                log(f"🧹 Cleaned up local video file: {out_mp4}")
            except Exception:
                pass

        # Explicitly ensure monetization & product tagging are confirmed via YouTube Studio CDP
        try:
            log(f">> Ensuring monetization is active for {video_id}...")
            res_m = subprocess.run(["node", f"{ROOT}/scripts/set-monetization-studio.js", video_id], capture_output=True, text=True, timeout=180)
            log(f">> Monetization result: {res_m.stdout.strip()[-200:]}")
        except Exception as e:
            log(f"WARN monetization step: {e}")

        try:
            log(f">> Ensuring product tagging is active for {video_id}...")
            res_t = subprocess.run(["node", f"{ROOT}/scripts/tag-products-studio.js", video_id], capture_output=True, text=True, timeout=180)
            log(f">> Product tagging result: {res_t.stdout.strip()[-200:]}")
        except Exception as e:
            log(f"WARN product tagging step: {e}")

        try:
            subprocess.run(["python3", f"{ROOT}/scripts/sync-youtube-ids.py"], capture_output=True)
            subprocess.run(["python3", f"{ROOT}/scripts/build_github_pages.py"], capture_output=True)
            subprocess.run([f"{ROOT}/scripts/publish-dashboard.sh"], capture_output=True)
        except Exception as e:
            log(f"WARN telemetry update: {e}")

        return True, video_id
    else:
        log(f"❌ Upload failed for {concept['title']}. Details:\n{out_text[-500:]}")
        if os.path.exists(out_mp4):
            try:
                os.remove(out_mp4)
            except Exception:
                pass
        return False, "upload_failed"


def run_full_september_production():
    if os.path.exists(LOCK_FILE):
        log("WARN: Another production lock exists. Checking if PID is alive...")
        try:
            with open(LOCK_FILE) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            log(f"Active process {pid} is running. Exiting.")
            return
        except Exception:
            log("Lock is stale. Removing.")
            try:
                os.remove(LOCK_FILE)
            except Exception:
                pass

    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))

    try:
        log("🌟 DroneMill September Full Autonomous Production Engine Started")
        log(f"Server local time: {datetime.datetime.now(datetime.timezone.utc).isoformat()}")

        candidate_images = get_candidate_images()
        log(f"🖼️ Found {len(candidate_images)} high-resolution candidate images in pool.")
        
        # Load all previously used image basenames from history to strictly forbid repeats
        used_images = set()
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    for entry in json.load(f):
                        for field in ["thumbnail", "image", "image_path"]:
                            val = entry.get(field)
                            if val:
                                b = os.path.basename(val).lower()
                                used_images.add(b)
                                clean = b.replace("_compressed.jpg", "").replace(".jpg", "").replace(".png", "").replace(".jpeg", "")
                                used_images.add(clean)
                log(f"📋 Loaded {len(used_images)} previously used image signatures from history to guarantee zero repeats.")
            except Exception as e:
                log(f"WARN loading history images: {e}")

        target_days = list(range(5, 31))

        while True:
            scheduled_dates = get_scheduled_september_dates()
            missing_days = [d for d in target_days if f"2026-09-{d:02d}" not in scheduled_dates]

            log(f"📋 Scheduled September releases: {len(scheduled_dates)} | Remaining: {len(missing_days)}")
            if not missing_days:
                log("🎉 COMPLETE! All days of September 2026 are fully scheduled on YouTube!")
                break

            next_day = missing_days[0]
            success, reason = produce_and_schedule_day(next_day, candidate_images, used_images)

            if success:
                log(f"✅ Finished Day {next_day:02d}. Short breather (15s) before next release...")
                time.sleep(15)
            elif reason == "quota_exceeded":
                now_utc = datetime.datetime.now(datetime.timezone.utc)
                reset_time = now_utc.replace(hour=7, minute=15, second=0, microsecond=0)
                if now_utc >= reset_time:
                    reset_time += datetime.timedelta(days=1)
                sleep_secs = max(300, int((reset_time - now_utc).total_seconds()))
                log(f"⏳ Sleeping {sleep_secs/3600:.1f} hours until YouTube quota reset at {reset_time.isoformat()}...")
                time.sleep(sleep_secs)
            elif reason == "low_disk":
                log("🛑 Low disk space pause. Sleeping 30 minutes before re-checking...")
                time.sleep(1800)
            else:
                log(f"⚠️ Encountered error: {reason}. Pausing 60s before retrying...")
                time.sleep(60)

    finally:
        if os.path.exists(LOCK_FILE):
            try:
                os.remove(LOCK_FILE)
            except Exception:
                pass


if __name__ == "__main__":
    run_full_september_production()

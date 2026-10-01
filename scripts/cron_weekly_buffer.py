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

# Auto-load .env from project root if present
_env_file = os.path.join(ROOT, ".env")
if os.path.exists(_env_file):
    try:
        with open(_env_file, "r", encoding="utf-8") as _ef:
            for _line in _ef:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _v = _line.split("=", 1)
                    _k = _k.strip()
                    _v = _v.strip().strip('"').strip("'")
                    if _k and _k not in os.environ:
                        os.environ[_k] = _v
    except Exception:
        pass

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


def check_youtube_token():
    """Pre-flight check: verify OAuth token can refresh. Returns (ok, msg)."""
    token_path = os.path.expanduser("~/.youtubeuploader/request.token")
    secrets_path = os.path.expanduser("~/.youtubeuploader/client_secrets.json")
    if not os.path.exists(token_path) or not os.path.exists(secrets_path):
        return False, "Missing ~/.youtubeuploader/request.token or client_secrets.json (see SETUP-YOUTUBE.md)"
    try:
        import json as _js
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        with open(token_path) as f:
            t = _js.load(f)
        with open(secrets_path) as f:
            s = _js.load(f)
        cfg = s.get("web") or s.get("installed", {})
        creds = Credentials(
            token=t.get("access_token"),
            refresh_token=t.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=cfg.get("client_id"),
            client_secret=cfg.get("client_secret"),
        )
        # Always try refresh if we have a refresh_token — expiry may be None but token still revoked
        if creds.refresh_token:
            creds.refresh(Request())
        return True, "Token OK"
    except Exception as e:
        msg = str(e)
        if "invalid_grant" in msg or "expired or revoked" in msg:
            return False, f"Token invalid_grant (expired/revoked): {msg}. Re-auth required: run on server /home/brewuser/projects/dronemill/scripts/reauth-youtube.sh (direct via Chromium :9222, no tunnel) or see SETUP-YOUTUBE.md #7."
        return False, f"Token check failed: {msg}"


def free_disk_gb(path=ROOT):
    st = os.statvfs(path)
    return (st.f_bavail * st.f_frsize) / (1024 ** 3)


def run_disk_cleanup():
    result = subprocess.run(["python3", f"{ROOT}/scripts/cleanup_uploaded_mp4s.py"], capture_output=True, text=True)
    for line in (result.stdout or "").splitlines():
        if line.strip():
            log(f"🧹 {line.strip()}")


def get_schedule_status():
    history_file = f"{ROOT}/output/upload_history.json"
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    future_scheduled = []

    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                for item in json.load(f):
                    p = item.get("publish_at")
                    vid = item.get("video_id")
                    # Only count verified uploads (with video_id) toward buffer
                    # Failed pending uploads (video_id None) must NOT inflate runway
                    if p and vid:
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

    # 1. Image preparation - THEME-MATCHED, no longer alphabetical FIFO
    # concept contains category, image_prompt, title - pick fresh image that matches theme
    # Mapping fresh images -> theme keywords (keeps title<->image coherent, fixes escalator vs sea_wall mismatch)
    image_path = None
    fresh_dir = f"{ROOT}/images/fresh"
    # First choice: generate a cover for this exact concept through the OpenRouter model chain
    # (cover_generator.py skips delisted models and stops early when credit runs out).
    if concept.get("image_prompt"):
        import cover_generator
        gen_dir = f"{ROOT}/images/generated"
        os.makedirs(gen_dir, exist_ok=True)
        gen_path, _model = cover_generator.generate_cover(
            concept["image_prompt"], f"{gen_dir}/{slug}_{int(time.time())}.png", log=log)
        if gen_path:
            image_path = gen_path
    # Try to generate fresh image via DALL-E/OpenRouter using concept["image_prompt"] if API key present
    if not image_path and concept.get("image_prompt") and os.getenv("OPENAI_API_KEY"):
        try:
            import autopilot
            img_filename = f"{slug}_{int(time.time())}.png"
            gen_path = autopilot.generate_image_ai(concept["image_prompt"], img_filename)
            if isinstance(gen_path, str) and os.path.exists(gen_path):
                image_path = gen_path
                log(f"🖼️ Generated fresh image via AI for '{concept['title']}' -> {gen_path}")
            elif gen_path:
                candidate = os.path.join(ROOT, "images", "queue", img_filename)
                if os.path.exists(candidate):
                    image_path = candidate
                    log(f"🖼️ Generated fresh image via AI for '{concept['title']}' -> {candidate}")
        except Exception as e:
            log(f"WARN: AI image generation failed ({e}), falling back to fresh queue")
    # Scene themes: the bank holds covers named after the scene (e.g. knight_02a.jpg), so the
    # cover always shows what the title describes. No match means no video for this slot.
    if not image_path and concept.get("cover_key"):
        key = concept["cover_key"].lower()
        bank = sorted(f for f in (os.listdir(fresh_dir) if os.path.exists(fresh_dir) else [])
                      if f.lower().startswith(key) and f.lower().endswith((".jpg", ".jpeg", ".png")))
        if bank:
            image_path = os.path.join(fresh_dir, bank[0])
            log(f"🖼️ Using bank cover {bank[0]} for scene {key}")
        else:
            log(f"🛑 No cover for '{concept['title']}': generation failed and images/fresh has no {key}* file. "
                f"Skipping this slot instead of using a mismatched image.")
            return False

    if not image_path:
        if os.path.exists(fresh_dir):
            fresh_files = sorted([os.path.join(fresh_dir, f) for f in os.listdir(fresh_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))])
            if fresh_files:
                # Theme-aware pick: first file whose name contains theme keywords, else first
                theme = concept.get("category","").lower()
                # simple keyword map fresh -> theme
                theme_keywords = {
                    "maritime": ["keeper", "sea_wall", "drowned", "chapel"],
                    "liminal": ["carpeted", "transit", "bowling", "bathhouse", "lounge"],
                    "cosmic": ["europa", "lunar", "freighter", "monolith"],
                    "dark academia": ["library", "archive"],
                    "prehistoric": ["arctic", "monolith"],
                    "eldritch": ["eldritch_"],
                    "knight": ["knight_"],
                }
                picked = None
                # theme-aware: handle "Maritime & Abyssal Horror" -> maritime, etc.
                tl = theme.lower() if theme else ""
                kws = []
                if "eldritch" in tl: kws = theme_keywords["eldritch"]
                elif "knight" in tl: kws = theme_keywords["knight"]
                elif "maritime" in tl: kws = theme_keywords["maritime"]
                elif "liminal" in tl: kws = theme_keywords["liminal"]
                elif "cosmic" in tl: kws = theme_keywords["cosmic"]
                elif "dark academia" in tl: kws = theme_keywords["dark academia"]
                elif "prehistoric" in tl: kws = theme_keywords["prehistoric"]
                elif "retro" in tl: kws = theme_keywords.get("liminal", [])

                for kw in kws:
                    for f in fresh_files:
                        if kw in os.path.basename(f).lower():
                            picked = f
                            break
                    if picked:
                        break
                # fallback: try match any word from title (not for scene themes, whose covers must be exact)
                if not picked and not concept.get("preset"):
                    title_words = [w.lower() for w in concept["title"].split() if len(w)>4]
                    for f in fresh_files:
                        if any(w in os.path.basename(f).lower() for w in title_words):
                            picked = f
                            break
                if concept.get("preset") and not picked:
                    log(f"🛑 No cover for '{concept['title']}': generation failed and images/fresh has no "
                        f"'{(kws or ['?'])[0]}*' file. Skipping this slot instead of using a mismatched image.")
                    return False
                image_path = picked or fresh_files[0]
                log(f"🖼️ Picked theme-matched image for '{theme}' -> {os.path.basename(image_path)} (was FIFO 01_keeper...)")
    
    if not image_path and concept.get("preset"):
        log(f"🛑 No cover for '{concept['title']}' and no images/fresh bank. Skipping this slot.")
        return False

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

    # 2. Audio generation via AI Hybrid 5-Engine (config dict API)
    master_audio = f"{ROOT}/output/{slug}_master.wav"
    rb_src = f"{ROOT}/audio/samples/12_cosmic_horror.mp3"
    if not os.path.exists(rb_src):
        rb_src = f"{ROOT}/audio/samples/01_empty_mall.mp3"
    # Category -> sound preset. lovecraft: dark chords, choir, booms/groans/calls.
    # historical: melancholic chords with piano/string phrases ("Place, Year" ambient-music style).
    category = concept.get("category", "").lower()
    preset = concept.get("preset") or (
        "historical" if any(k in category for k in ("academia", "prehistoric", "retro")) else "lovecraft")
    root = concept["dsp_freqs"][0]
    if preset == "lovecraft":
        engines = {
            "foley": {"enabled": True, "samples": concept["foley"], "volume": 0.22, "filter": "highpass=f=100,lowpass=f=6500", "send": 0.7},
            "dsp": {"enabled": True, "frequencies": concept["dsp_freqs"], "lfos": concept["dsp_lfos"], "volume": 0.25, "send": 0.5},
            "sub": {"enabled": True, "root": root, "volume": 0.26},
            "texture": {"enabled": True, "volume": 0.5, "send": 0.3},
            "pad": {"enabled": True, "volume": 0.8, "send": 0.5},
            "choir": {"enabled": True, "volume": 0.6, "send": 0.7},
            "melody": {"enabled": True, "volume": 0.4, "send": 0.8},
            "events": {"enabled": True, "volume": 0.7, "send": 0.9},
            "reverb": {"enabled": True, "decay": 3.6, "length": 12, "wet": 0.65},
        }
    elif preset == "fantasy":
        engines = {
            "foley": {"enabled": True, "samples": concept["foley"], "volume": 0.22, "filter": "highpass=f=100,lowpass=f=7000", "send": 0.6},
            "sub": {"enabled": True, "root": root, "volume": 0.20},
            "texture": {"enabled": True, "volume": 0.3, "send": 0.3},
            "pad": {"enabled": True, "volume": 0.75, "send": 0.5},
            "choir": {"enabled": True, "volume": 0.55, "send": 0.7},
            "melody": {"enabled": True, "volume": 0.6, "send": 0.7},
            "events": {"enabled": True, "volume": 0.35, "send": 0.9},
            "fire": {"enabled": True, "volume": 0.5, "send": 0.15},
            "reverb": {"enabled": True, "decay": 3.4, "length": 12, "wet": 0.6},
        }
    else:
        engines = {
            "foley": {"enabled": True, "samples": concept["foley"], "volume": 0.25, "filter": "highpass=f=100,lowpass=f=7000", "send": 0.6},
            "sub": {"enabled": True, "root": root, "volume": 0.20},
            "texture": {"enabled": True, "volume": 0.35, "send": 0.3},
            "pad": {"enabled": True, "volume": 0.7, "send": 0.5},
            "choir": {"enabled": True, "volume": 0.4, "send": 0.7},
            "melody": {"enabled": True, "volume": 0.75, "send": 0.65},
            "events": {"enabled": True, "volume": 0.4, "send": 0.9},
            "reverb": {"enabled": True, "decay": 3.2, "length": 11, "wet": 0.65},
        }
    log(f"🎚️ Sound preset: {preset} (category: {concept.get('category', '?')}, root {root} Hz)")
    cfg = {"duration": 7200, "seed": concept["title"], "preset": preset, "root": root, "engines": engines}
    build_hybrid_soundscape(cfg, master_audio)

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
    # Preferred: a seamless 60 s "living still" loop of the cover (lamps flicker, fog drifts,
    # snow falls, the phone sways slightly), repeated under the 2 h soundtrack by stream copy.
    # Falls back to the static-image render above if anything goes wrong.
    living = f"{ROOT}/tmp/{slug}_living.mp4"
    venv_py = f"{ROOT}/.venv-visual/bin/python"
    used_living = False
    if os.path.exists(venv_py):
        try:
            res = subprocess.run([venv_py, f"{ROOT}/scripts/living_still.py", image_path,
                                  f"auto:{preset}:{concept.get('category', '')}", living, "60", "1920"],
                                 capture_output=True, text=True, timeout=2700)
            if res.returncode == 0 and os.path.exists(living) and os.path.getsize(living) > 1_000_000:
                run_cmd(f'ffmpeg -y -nostdin -stream_loop -1 -i "{living}" -i "{master_audio}" -map 0:v -map 1:a '
                        f'-c:v copy -c:a aac -b:a 256k -ar 48000 -t 7200 -movflags +faststart "{out_mp4}"',
                        f"Muxing living-still loop with 2h audio -> {out_mp4}")
                used_living = True
                log("🎞️ Rendered with a living-still loop of the cover")
            else:
                tail = (res.stderr or res.stdout or "").strip().splitlines()[-1:] or ["no output"]
                log(f"WARN: living still failed ({tail[0][:160]}), using static render")
        except Exception as e:
            log(f"WARN: living still error ({e}), using static render")
        finally:
            if os.path.exists(living):
                os.remove(living)
    if not used_living:
        run_cmd(cmd_render, f"Rendering 2h video -> {out_mp4}")

    # 4. Write description file
    tmp_dir = f"{ROOT}/tmp"
    os.makedirs(tmp_dir, exist_ok=True)
    desc_file = f"{tmp_dir}/desc_{os.getpid()}_{int(time.time())}.txt"
    with open(desc_file, "w", encoding="utf-8") as f:
        f.write(concept["description"])

    # 5. Upload & Schedule via upload-yt.sh
    # Thumbnail = the cover plus a short place name in wide-spaced capitals (the video itself
    # uses the clean cover). Falls back to the plain cover if anything goes wrong.
    thumb_path = image_path
    if concept.get("caption"):
        try:
            from PIL import Image as _Image
            from thumb_text import caption as _caption
            _main, _sub = (list(concept["caption"]) + [None])[:2]
            _thumb = _caption(_Image.open(image_path).convert("RGB").resize((1280, 720)), _main, _sub)
            thumb_path = f"{tmp_dir}/{slug}_thumb.jpg"
            _thumb.save(thumb_path, quality=90)
            log(f"🔤 Thumbnail text: {_main}" + (f" / {_sub}" if _sub else ""))
        except Exception as e:
            log(f"WARN: thumbnail text failed ({e}); uploading the plain cover")
            thumb_path = image_path
    cmd_upload = f"\"{ROOT}/scripts/upload-yt.sh\" \"{out_mp4}\" \"{concept['title']}\" \"{desc_file}\" \"{thumb_path}\" \"private\" \"{concept['tags']}\" \"{pub_iso}\""
    try:
        upload_out = run_cmd(cmd_upload, f"Uploading and scheduling on YouTube for {pub_iso}") or ""
        # Surface the monetization and product-tagging results; upload-yt.sh only prints them.
        for line in upload_out.splitlines():
            if any(k in line for k in ("Monetization", "MONETIZATION", "products", "Products", "WARN", "VIDEO_ID", "Video ID")):
                log(f"   ↳ {line.strip()[:200]}")
    finally:
        # Always clean up desc file and master wav (master wav no longer needed after render, even if upload fails)
        if thumb_path != image_path and os.path.exists(thumb_path):
            try:
                os.remove(thumb_path)
            except Exception:
                pass
        if os.path.exists(desc_file):
            try:
                os.remove(desc_file)
            except Exception:
                pass
        if os.path.exists(master_audio):
            try:
                os.remove(master_audio)
                log(f"🧹 Deleted master wav to save space: {master_audio}")
            except Exception as e:
                log(f"WARN: Could not delete master wav: {e}")
        # Clean up tmp hybrid stems for this PID to avoid disk bloat (DSP/RB wavs)
        for tmp_pat in [
            f"{tmp_dir}/hybrid_dsp_{os.getpid()}_",
            f"{tmp_dir}/hybrid_rb_{os.getpid()}_",
            f"{tmp_dir}/hybrid_sub_{os.getpid()}_",
            f"{tmp_dir}/hybrid_ir_{os.getpid()}",
            f"{tmp_dir}/hybrid_pad_{os.getpid()}_",
            f"{tmp_dir}/hybrid_choir_{os.getpid()}_",
            f"{tmp_dir}/hybrid_melody_{os.getpid()}_",
            f"{tmp_dir}/hybrid_events_{os.getpid()}_",
            f"{tmp_dir}/hybrid_fire_{os.getpid()}_",
            f"/tmp/hybrid_dsp_{os.getpid()}_",
            f"/tmp/hybrid_rb_{os.getpid()}_"
        ]:
            try:
                import glob as _glob
                for _f in _glob.glob(tmp_pat + "*.wav") + _glob.glob(tmp_pat + "*.flac"):
                    try:
                        os.remove(_f)
                    except Exception:
                        pass
            except Exception:
                pass
        # If upload succeeded, out_mp4 is already deleted by upload-yt.sh (only on VIDEO_ID).
        # If we are here and mp4 still exists but history says video_id exists, delete it (safety net).
        # If upload failed, keep mp4 for retry (do not delete).
        if os.path.exists(out_mp4):
            # Check last history entry for this title has video_id
            try:
                import json as _json
                hist_path = f"{ROOT}/output/upload_history.json"
                if os.path.exists(hist_path):
                    with open(hist_path, "r", encoding="utf-8") as _hf:
                        _hist = _json.load(_hf)
                        # Find most recent entry matching title
                        for _e in reversed(_hist):
                            if _e.get("title") == concept["title"]:
                                if _e.get("video_id"):
                                    # archive the cover so the bank never reuses it
                                    if image_path and ("/images/fresh/" in image_path or "/images/generated/" in image_path):
                                        try:
                                            os.makedirs(f"{ROOT}/images/used", exist_ok=True)
                                            os.replace(image_path, f"{ROOT}/images/used/{os.path.basename(image_path)}")
                                        except Exception as _mv:
                                            log(f"WARN: could not archive cover: {_mv}")
                                    try:
                                        os.remove(out_mp4)
                                        log(f"🧹 Deleted local mp4 after verified upload: {out_mp4}")
                                    except Exception as _ex:
                                        log(f"WARN: Could not delete mp4: {_ex}")
                                else:
                                    log(f"⚠️ Upload failed for {concept['title']}, keeping mp4 for retry: {out_mp4}")
                                break
            except Exception:
                pass

    # Save idea to history only if upload succeeded (avoid marking failed ideas as used)
    try:
        import json as _json2
        _hist_path2 = f"{ROOT}/output/upload_history.json"
        _success = False
        if os.path.exists(_hist_path2):
            with open(_hist_path2, "r", encoding="utf-8") as _hf2:
                _h2 = _json2.load(_hf2)
                for _e2 in reversed(_h2):
                    if _e2.get("title") == concept["title"]:
                        _success = bool(_e2.get("video_id"))
                        break
        if _success:
            # archive the cover so the bank never reuses it (upload-yt.sh already removed the mp4)
            if image_path and os.path.exists(image_path) and (
                    "/images/fresh/" in image_path or "/images/generated/" in image_path):
                try:
                    os.makedirs(f"{ROOT}/images/used", exist_ok=True)
                    os.replace(image_path, f"{ROOT}/images/used/{os.path.basename(image_path)}")
                except Exception as _mv:
                    log(f"WARN: could not archive cover: {_mv}")
            idea_generator.save_used_idea(concept["title"])
            log(f"✅ Successfully scheduled: {concept['title']} ({pub_iso})")
        else:
            log(f"⚠️ Not marking idea as used (upload failed, will retry): {concept['title']}")
    except Exception as _e:
        # Fallback: mark as used to avoid infinite loop, but log
        log(f"WARN: Could not verify upload success for history: {_e}")
        idea_generator.save_used_idea(concept["title"])


def re_slug(t):
    s = t.split("|")[0].lower()
    return "".join(c if c.isalnum() else "-" for c in s).strip("-")


def run_cron_cycle():
    # Lockfile check
    if os.path.exists(LOCK_FILE) or os.path.exists("/tmp/september_production.lock"):
        log("WARN: Another cron or September production process is active. Skipping cycle.")
        return

    try:
        with open(LOCK_FILE, "w") as f:
            f.write(str(os.getpid()))

        # Free up space from already-uploaded mp4s / orphan wavs before doing anything else
        run_disk_cleanup()
        log(f"💾 Free disk space: {free_disk_gb():.1f} GB")

        # Pre-flight token check — fail fast before expensive render
        ok, token_msg = check_youtube_token()
        if not ok:
            log(f"🛑 YouTube auth broken: {token_msg}")
            log("   Fix: run on server /home/brewuser/projects/dronemill/scripts/reauth-youtube.sh (direct via Chromium :9222, no SSH tunnel)")
            log("   or: /home/brewuser/projects/dronemill/scripts/upload-yt.sh <video> ... (triggers browser at http://localhost:8080/oauth2callback via server Chromium)")
            log("   Keeping existing local mp4s for retry after re-auth. Cron will resume next cycle.")
            return

        try:
            import cover_generator
            cover_generator.health(log=log)
        except Exception as e:
            log(f"WARN: cover health check failed ({e})")

        log("🚀 Checking DroneMill release runway status...")
        # What is actually scheduled: YouTube itself plus verified uploads in local history.
        import youtube_schedule
        days_left, last_dt = get_schedule_status()
        occupied = set()
        history_file = f"{ROOT}/output/upload_history.json"
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        if os.path.exists(history_file):
            try:
                for item in json.load(open(history_file, encoding="utf-8")):
                    if item.get("publish_at") and item.get("video_id"):
                        dt = datetime.datetime.fromisoformat(item["publish_at"].replace("Z", "+00:00"))
                        if dt > now_utc:
                            occupied.add(dt.date())
            except Exception as e:
                log(f"WARN: could not read upload history: {e}")
        yt_times = youtube_schedule.scheduled_on_youtube(log=log)
        if yt_times is not None:
            occupied |= {t.date() for t in yt_times}
            log(f"📺 YouTube has {len(yt_times)} scheduled videos; local history adds "
                f"{len(occupied) - len({t.date() for t in yt_times})} more days.")

        TARGET_RUNWAY_DAYS = 5   # keep at least this many consecutive days covered from tomorrow
        MAX_PER_RUN = 3          # catch up faster after a gap; each video renders in about an hour
        free_slots = youtube_schedule.next_free_slots(occupied, MAX_PER_RUN, now=now_utc)
        runway = (free_slots[0].date() - now_utc.date()).days - 1  # covered days before the first gap
        log(f"Current Buffer: {len(occupied)} future scheduled days; next free slot "
            f"{free_slots[0].strftime('%Y-%m-%d %H:%M UTC')} ({max(runway, 0)} consecutive days covered).")

        if runway < TARGET_RUNWAY_DAYS:
            log(f"⚠️ Gap in the schedule. Filling the next free slots: "
                f"{', '.join(s.strftime('%Y-%m-%d') for s in free_slots)}")
            MIN_FREE_GB_FOR_RENDER = 6
            for slot in free_slots:
                free_gb = free_disk_gb()
                if free_gb < MIN_FREE_GB_FOR_RENDER:
                    log(f"🛑 Only {free_gb:.1f} GB free (need {MIN_FREE_GB_FOR_RENDER} GB for a safe render). Skipping production this cycle — free up disk space manually.")
                    break
                concept = idea_generator.generate_novel_concept()
                if not concept:
                    log("ERROR: Could not generate novel concept. Aborting.")
                    break
                if produce_and_schedule_single(concept, slot) is False:
                    break  # the slot stays free for the next cycle

            # Sync IDs and rebuild GitHub Pages
            log("🔄 Syncing YouTube video IDs and updating GitHub Pages dashboard...")
            subprocess.run(["python3", f"{ROOT}/scripts/sync-youtube-ids.py"])
            subprocess.run(["python3", f"{ROOT}/scripts/build_github_pages.py"])
            subprocess.run([f"{ROOT}/scripts/publish-dashboard.sh"])
            log("✨ Buffer refill cycle completed successfully!")
        else:
            log(f"✅ Schedule is covered for the next {runway} days (target {TARGET_RUNWAY_DAYS}). Re-checking sync & status.")
            # Light telemetry sync and build
            subprocess.run(["python3", f"{ROOT}/scripts/build_github_pages.py"])
            subprocess.run(["bash", f"{ROOT}/scripts/publish-dashboard.sh"])

    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)


if __name__ == "__main__":
    run_cron_cycle()

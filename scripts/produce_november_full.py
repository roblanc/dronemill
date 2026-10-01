#!/usr/bin/env python3
"""
Full Autonomous November Production & Scheduling Engine for DroneMill / @timelessambience55.
Iterates through all days of November 2026 (November 1 - November 30):
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
import hashlib

ROOT = "/home/brewuser/projects/dronemill"
sys.path.append(f"{ROOT}/scripts")

import idea_generator

HISTORY_FILE = f"{ROOT}/output/upload_history.json"
TMP_DIR = f"{ROOT}/tmp"
OUT_DIR = f"{ROOT}/output"
LOG_FILE = f"{OUT_DIR}/november_production.log"
LOCK_FILE = "/tmp/november_production.lock"
YOUTUBE_AUTH_DIR = "/home/brewuser/.youtubeuploader"

# One original editorial concept for each freshly generated November artwork.
NOVEMBER_SCENES = {
    1: ("ferns sleeping beside abandoned rails | nocturne for glass and rain | 2 hours", "a forgotten railway conservatory breathing softly beneath midnight rain", "glasshouse rain ambient"),
    2: ("steam beneath the basalt bathhouse | volcanic spa ambience | 2 hours", "warm mineral steam moving through a bathhouse carved into black basalt", "volcanic spa ambient"),
    3: ("the seed vault orbiting saturn | deep space sanctuary | 2 hours", "a silent seed vault watching Saturn turn beyond the glass", "deep space sanctuary ambient"),
    4: ("storm watch at the cliff weather station | coastal isolation | 2 hours", "an isolated weather station listening to a storm cross the cliffs", "coastal isolation ambient"),
    5: ("green lamps over the unwritten catalogue | archival hush | 2 hours", "a midnight archive of old paper, green lamps, and distant rain", "dark academia ambient"),
    6: ("neon tides through the flooded arcade | liminal dream ambience | 2 hours", "an abandoned arcade glowing beneath a thin sheet of tidal water", "liminal dream ambient"),
    7: ("the mountain control room above the clouds | analog focus drone | 2 hours", "an analog control room keeping watch above a sleeping mountain range", "analog focus drone"),
    8: ("aurora signals from the arctic radio cabin | polar night ambience | 2 hours", "a small radio cabin receiving quiet signals beneath the aurora", "polar night ambient"),
    9: ("candles in the flooded crypt | subterranean sacred ambience | 2 hours", "a candlelit crypt where dark water reflects ancient stone arches", "subterranean sacred ambient"),
    10: ("the last night ferry lounge | ocean transit ambience | 2 hours", "an empty ferry lounge crossing black water long after midnight", "ocean transit ambient"),
    11: ("before the continents learned their names | primordial valley ambience | 2 hours", "a fern valley breathing in warm rain before human memory", "deep time nature ambient"),
    12: ("maps of silence in the lunar cartography room | moon base ambience | 2 hours", "a lunar cartography room charting silent craters beneath cold light", "moon base ambient"),
    13: ("signals below the lightless sea | deep ocean listening station | 2 hours", "a deep-sea station listening for distant movement beyond the windows", "deep ocean ambient"),
    14: ("snowfall beyond the alpine winter garden | cozy glasshouse ambience | 2 hours", "a warm winter garden sheltered from a silent alpine snowfall", "cozy glasshouse ambient"),
    15: ("reading through the lighthouse storm | maritime library ambience | 2 hours", "a lighthouse library glowing while the storm circles outside", "maritime library ambient"),
    16: ("the abandoned tram depot on mars | red planet ambience | 2 hours", "a silent tram depot waiting beneath the dust-red Martian sky", "red planet ambient"),
    17: ("redwood observatory under starlight | forest nocturne drone | 2 hours", "a hidden observatory opening toward the stars among ancient redwoods", "forest nocturne drone"),
    18: ("the final screening underground | empty cinema ambience | 2 hours", "an underground cinema holding the glow of its final screening", "empty cinema ambient"),
    19: ("mist through the cloud forest station | rainforest research ambience | 2 hours", "a remote research station disappearing into the cloud forest", "rainforest research ambient"),
    20: ("fluorescent silence below avenue zero | subterranean waiting room | 2 hours", "an underground platform humming after the last train has gone", "liminal transit drone"),
    21: ("coffee break in the asteroid canteen | cozy orbital ambience | 2 hours", "a quiet asteroid canteen drifting beneath a field of distant stars", "cozy orbital ambient"),
    22: ("winter ink in the monastery scriptorium | medieval study ambience | 2 hours", "a monastery scriptorium warmed by candles during a long winter night", "medieval study ambient"),
    23: ("after closing in the submerged museum | underwater liminal ambience | 2 hours", "a submerged museum where blue water moves beyond empty galleries", "underwater liminal ambient"),
    24: ("the final cable car above the storm | mountain terminal ambience | 2 hours", "a mountain cable terminal waiting above a slow-moving storm", "mountain terminal ambient"),
    25: ("a thousand clocks after midnight | antique workshop ambience | 2 hours", "an antique clock workshop ticking softly after midnight", "antique workshop ambient"),
    26: ("dinner aboard the submerged sleeper train | underwater travel ambience | 2 hours", "a submerged dining car gliding through a dark and endless sea", "underwater travel ambient"),
    27: ("city rain on the rooftop greenhouse | urban botanical ambience | 2 hours", "a rooftop greenhouse glowing quietly above a rain-soaked city", "urban botanical ambient"),
    28: ("embers beside the volcanic lake cabin | remote wilderness ambience | 2 hours", "a solitary cabin watching embers fade beside a volcanic lake", "remote wilderness ambient"),
    29: ("the chapel aboard the sleeper ship | interstellar sacred ambience | 2 hours", "a small chapel holding silence aboard a centuries-long voyage", "interstellar sacred ambient"),
    30: ("snowbound garden past last station | winter terminus nocturne | 2 hours", "a forgotten winter garden waiting beyond the final railway terminus", "snowy terminus ambient"),
}

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
    token_path = f"{YOUTUBE_AUTH_DIR}/request.token"
    secrets_path = f"{YOUTUBE_AUTH_DIR}/client_secrets.json"
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


def get_scheduled_november_dates():
    """Returns set of date strings ('YYYY-MM-DD') already scheduled with valid video_id."""
    scheduled = set()
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    p = item.get("publish_at")
                    vid = item.get("video_id")
                    if p and vid and p.startswith("2026-11-"):
                        date_str = p.split("T")[0]
                        scheduled.add(date_str)
        except Exception as e:
            log(f"WARN reading history: {e}")
    return scheduled


def get_candidate_images():
    """Collect only artwork generated specifically for November 2026."""
    patterns = [
        f"{ROOT}/images/november_fresh/*.jpg",
        f"{ROOT}/images/november_fresh/*.png",
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
    """Require the dedicated, unused November image for this exact release day."""
    if day_int is not None:
        day_patterns = [
            f"{ROOT}/images/november_fresh/{day_int:02d}_*.jpg",
            f"{ROOT}/images/november_fresh/{day_int:02d}_*.png",
            f"{ROOT}/images/november_fresh/{day_int}_*.jpg",
            f"{ROOT}/images/november_fresh/{day_int}_*.png"
        ]
        for pat in day_patterns:
            matches = glob.glob(pat)
            for m in matches:
                base = os.path.basename(m).lower()
                clean = base.replace(".jpg", "").replace(".png", "").replace(".jpeg", "")
                if m not in used_images and base not in used_images and clean not in used_images:
                    return m
    return None


def generate_audio_master(concept, duration, out_wav):
    """Generates 2-hour mastered soundscape using DSP, Rubberband and acoustic beds."""
    log(">> Generating optimized procedural DSP & Rubberband stems...")
    pid = os.getpid()
    dsp_wav = f"{TMP_DIR}/dsp_stem_{pid}.wav"
    rb_wav = f"{TMP_DIR}/rb_stem_{pid}.wav"

    try:
        # 1. Procedural 300s DSP stem with prime LFOs (loops seamlessly)
        # Title-derived micro-variation makes every finished soundscape's harmonic
        # recipe distinct, even if two concepts share the same thematic root.
        digest = hashlib.sha256(concept["title"].encode("utf-8")).digest()
        detunes = [0.992 + (digest[i] / 255.0) * 0.016 for i in range(4)]
        freqs = [round(f * detunes[i], 4) for i, f in enumerate(concept["dsp_freqs"])]
        lfos = [l + (digest[i + 4] % 7) / 10.0 for i, l in enumerate(concept["dsp_lfos"])]
        log(f">> Fresh audio recipe: {hashlib.sha256((str(freqs)+str(lfos)).encode()).hexdigest()[:16]}")
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
            raise FileNotFoundError(f"Required source texture missing: {rb_src}; refusing fallback")
        semitones = -12 - (digest[8] % 5)
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
    date_str = f"2026-11-{day_int:02d}"
    pub_iso = f"{date_str}T18:00:00Z"

    log("============================================================")
    log(f"📅 STARTING PRODUCTION FOR: November {day_int:02d}, 2026 ({pub_iso})")
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

    scene_title, scene_blurb, scene_subgenre = NOVEMBER_SCENES[day_int]
    concept["title"] = sanitize_title(scene_title)
    concept["subgenre"] = scene_subgenre
    concept["category"] = "November Fresh Collection"
    concept["description"] = (
        f"2 hours of immersive {scene_subgenre}.\n"
        f"Step inside {scene_blurb}.\n\n"
        "Created as an original Timeless Ambience soundscape for November 2026. "
        "Use it for sleep, deep work, reading, writing, or quiet nocturnal drift.\n\n"
        "#ambient #sleepmusic #studymusic #2hourambient #timelessambience"
    )
    existing_titles = idea_generator.load_previous_history()
    if concept["title"].lower() in existing_titles or idea_generator.is_too_similar(concept["title"], existing_titles):
        log("🛑 Sanitized title is not sufficiently fresh; refusing to reuse it.")
        return False, "fresh_title_failed"
    log(f"🎬 Title ({len(concept['title'])} chars): {concept['title']}")
    log(f"🏷️ Category: {concept['category']} | Subgenre: {concept['subgenre']}")

    # 4. Image selection
    img_path = select_image_for_concept(concept, candidate_images, used_images, day_int=day_int)
    if not img_path:
        log(f"🛑 No unused November-specific artwork exists for day {day_int:02d}; refusing historical fallback.")
        return False, "fresh_image_missing"
    log(f"🖼️ Selected Artwork: {os.path.basename(img_path)}")

    # 5. Overlay selection
    overlay = concept["overlay"]
    if not os.path.exists(overlay):
        log(f"🛑 Required concept overlay missing: {overlay}; refusing fallback.")
        return False, "fresh_overlay_missing"

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
        used_images.add(img_path)
        used_images.add(os.path.basename(img_path).lower())

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


def run_full_november_production():
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
        log("🌟 DroneMill November Full Autonomous Production Engine Started")
        log(f"Server local time: {datetime.datetime.now(datetime.timezone.utc).isoformat()}")

        candidate_images = get_candidate_images()
        log(f"🖼️ Found {len(candidate_images)} high-resolution candidate images in pool.")
        if len(candidate_images) != 30:
            log(f"🛑 Fresh-art preflight failed: expected exactly 30 November images, found {len(candidate_images)}.")
            return
        resolved = [select_image_for_concept({}, candidate_images, set(), day_int=d) for d in range(1, 31)]
        if any(not p for p in resolved) or len(set(resolved)) != 30:
            log("🛑 Fresh-art preflight failed: every November day must map to one unique dedicated image.")
            return
        
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

        target_days = list(range(1, 31))

        while True:
            scheduled_dates = get_scheduled_november_dates()
            missing_days = [d for d in target_days if f"2026-11-{d:02d}" not in scheduled_dates]

            log(f"📋 Scheduled November releases: {len(scheduled_dates)} | Remaining: {len(missing_days)}")
            if not missing_days:
                log("🎉 COMPLETE! All days of November 2026 are fully scheduled on YouTube!")
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
    run_full_november_production()

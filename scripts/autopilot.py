#!/usr/bin/env python3
import os
import sys
import json
import re
import subprocess
import requests
import base64
import argparse
from openai import OpenAI

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "search_configs.json")
HISTORY_PATH = os.path.join(ROOT_DIR, ".download_history")
METADATA_PATH = os.path.join(ROOT_DIR, "images", "metadata.json")
AUDIO_QUEUE_DIR = os.path.join(ROOT_DIR, "audio", "queue")
IMAGES_QUEUE_DIR = os.path.join(ROOT_DIR, "images", "queue")
IMAGES_USED_DIR = os.path.join(ROOT_DIR, "images", "used")

# API Keys
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

def load_configs():
    if not os.path.exists(CONFIG_PATH):
        print(f"WARN: search_configs.json not found at {CONFIG_PATH}. Using defaults.")
        return {
            "search_queries": [
                "liminal space ambient",
                "backrooms ambient sleep",
                "dreamcore ambient focus",
                "poolrooms ambient water sounds"
            ],
            "duration_min_seconds": 1800,
            "duration_max_seconds": 10800,
            "max_search_results_per_query": 5,
            "stock_threshold": 3
        }
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def load_history():
    if not os.path.exists(HISTORY_PATH):
        return set()
    with open(HISTORY_PATH, "r") as f:
        return set(line.strip() for line in f if line.strip())

def save_history(history):
    with open(HISTORY_PATH, "w") as f:
        for vid in sorted(history):
            f.write(f"{vid}\n")

def get_queue_files():
    audio_files = []
    if os.path.exists(AUDIO_QUEUE_DIR):
        audio_files = [f for f in os.listdir(AUDIO_QUEUE_DIR) if f.lower().endswith(('.mp3', '.wav', '.flac', '.m4a'))]
    
    image_files = []
    if os.path.exists(IMAGES_QUEUE_DIR):
        image_files = [f for f in os.listdir(IMAGES_QUEUE_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
    return len(audio_files), len(image_files)

def get_next_image_filename():
    all_files = []
    for d in [IMAGES_QUEUE_DIR, IMAGES_USED_DIR]:
        if os.path.exists(d):
            all_files.extend(os.listdir(d))
            
    numbers = []
    for f in all_files:
        match = re.match(r"^(\d+)\.(png|jpg|jpeg)$", f, re.IGNORECASE)
        if match:
            numbers.append(int(match.group(1)))
            
    next_num = max(numbers) + 1 if numbers else 1
    return f"{str(next_num).zfill(3)}.png"

def search_videos(query, duration_min, duration_max, max_results):
    print(f">> Searching YouTube for: '{query}'...")
    cmd = [
        "yt-dlp",
        f"ytsearch{max_results}:{query}",
        "--flat-playlist",
        "--dump-json"
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        videos = []
        for line in res.stdout.splitlines():
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                duration = data.get("duration")
                if duration and duration_min <= duration <= duration_max:
                    videos.append({
                        "id": data.get("id"),
                        "title": data.get("title"),
                        "duration": duration,
                        "url": data.get("url") or f"https://www.youtube.com/watch?v={data.get('id')}"
                    })
            except Exception as e:
                pass
        return videos
    except Exception as e:
        print(f"ERROR executing search: {e}")
        return []

def download_audio(video_url, dry_run=False):
    if dry_run:
        print(f"[DRY-RUN] Would download audio from: {video_url}")
        return "mock_audio_download.mp3"
        
    # Keep track of files in queue before download
    before_files = set(os.listdir(AUDIO_QUEUE_DIR)) if os.path.exists(AUDIO_QUEUE_DIR) else set()
    
    print(f">> Downloading audio from {video_url}...")
    os.makedirs(AUDIO_QUEUE_DIR, exist_ok=True)
    cmd = [
        "yt-dlp",
        "-x",
        "--audio-format",
        "mp3",
        "-o",
        os.path.join(AUDIO_QUEUE_DIR, "%(title)s.%(ext)s"),
        video_url
    ]
    try:
        subprocess.run(cmd, check=True)
        # Find which file was added
        after_files = set(os.listdir(AUDIO_QUEUE_DIR))
        new_files = after_files - before_files
        if new_files:
            downloaded = list(new_files)[0]
            print(f">> Downloaded: {downloaded}")
            return downloaded
        else:
            # Fallback scan
            mp3s = [f for f in os.listdir(AUDIO_QUEUE_DIR) if f.endswith(".mp3")]
            if mp3s:
                return sorted(mp3s, key=lambda x: os.path.getmtime(os.path.join(AUDIO_QUEUE_DIR, x)), reverse=True)[0]
    except Exception as e:
        print(f"ERROR downloading audio: {e}")
    return None

def generate_creative_assets(source_title):
    system_prompt = (
        "You are a creative content producer and YouTube SEO expert for a cosmic horror and liminal space ambient channel.\n"
        "You are given the title of a source audio track.\n"
        "Generate:\n"
        "1. A compelling, poetic, and mysterious title for our version (maximum 60 characters).\n"
        "   The title must strictly follow the format: 'hook in 3-5 words | main descriptor | tag or duration'\n"
        "   Example: 'lost in the tiles | poolrooms ambient playlist | liminal space drone'\n"
        "2. A list of 4-6 tags for search optimization.\n"
        "3. A detailed visual prompt for an image generator (like Midjourney or DALL-E 3) that captures a liminal space, dreamcore, or cosmic horror theme matching the soundscape.\n"
        "   Example: 'Liminal space poolrooms, infinite indoor swimming pools, turquoise ceramic tiles, clean glowing water, soft yellow fluorescent lighting, shot on 35mm film, nostalgic, empty, silent, eerie'\n\n"
        "Respond ONLY with a JSON object containing keys: 'title', 'tags' (list of strings), and 'image_prompt' (string)."
    )
    
    # 1. Try OpenRouter
    if OPENROUTER_API_KEY:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "google/gemini-2.0-flash-001",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Source video title: {source_title}"}
            ],
            "response_format": { "type": "json_object" }
        }
        try:
            print(">> Querying OpenRouter for titles & prompts...")
            response = requests.post(url, headers=headers, json=data, timeout=20)
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"].strip()
                if content.startswith("```"):
                    content = re.sub(r"^```(?:json)?\n", "", content)
                    content = re.sub(r"\n```$", "", content).strip()
                return json.loads(content)
        except Exception as e:
            print(f"OpenRouter failed: {e}")
            
    # 2. Try OpenAI
    if OPENAI_API_KEY:
        try:
            print(">> Querying OpenAI for titles & prompts...")
            client = OpenAI(api_key=OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Source video title: {source_title}"}
                ],
                response_format={ "type": "json_object" }
            )
            content = response.choices[0].message.content.strip()
            return json.loads(content)
        except Exception as e:
            print(f"OpenAI failed: {e}")

    # 3. Try local Ollama
    print(">> Querying local Ollama (phi3:latest)...")
    url_ollama = "http://localhost:11434/v1/chat/completions"
    data_ollama = {
        "model": "phi3:latest",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Source video title: {source_title}"}
        ],
        "response_format": { "type": "json_object" }
    }
    try:
        response = requests.post(url_ollama, json=data_ollama, timeout=90)
        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\n", "", content)
                content = re.sub(r"\n```$", "", content).strip()
            return json.loads(content)
    except Exception as e:
        print(f"Ollama failed: {e}")
        
    # Static Fallback
    print(">> Using static fallback creative assets...")
    return {
        "title": "lost in the tiles | poolrooms ambient playlist | liminal space drone",
        "tags": ["liminal space", "poolrooms", "ambient", "sleep music"],
        "image_prompt": "Liminal space poolrooms, infinite indoor swimming pools, turquoise ceramic tiles, clean glowing water, soft yellow fluorescent lighting, shot on 35mm film, nostalgic, empty, silent, eerie"
    }

def generate_image_ai(image_prompt, filename, dry_run=False):
    if dry_run:
        print(f"[DRY-RUN] Would generate cover image using prompt: '{image_prompt}'")
        return True
        
    os.makedirs(IMAGES_QUEUE_DIR, exist_ok=True)
    out_path = os.path.join(IMAGES_QUEUE_DIR, filename)
    
    # 1. Try OpenRouter Gemini Image
    if OPENROUTER_API_KEY:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "google/gemini-3.1-flash-image-preview",
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": image_prompt}]
                }
            ],
            "modalities": ["image"],
            "max_tokens": 3000,
            "image_config": {
                "aspect_ratio": "16:9"
            }
        }
        try:
            print(">> Generating image via OpenRouter...")
            res = requests.post(url, headers=headers, json=data, timeout=60)
            res.raise_for_status()
            result = res.json()
            if "choices" in result:
                message = result["choices"][0]["message"]
                if "images" in message:
                    img_url = message["images"][0]["image_url"]["url"]
                    if img_url.startswith("data:"):
                        header, encoded = img_url.split(",", 1)
                        img_data = base64.b64decode(encoded)
                    else:
                        img_data = requests.get(img_url).content
                    with open(out_path, "wb") as f:
                        f.write(img_data)
                    print(f">> Saved image to {out_path}")
                    return True
        except Exception as e:
            print(f"OpenRouter image generation failed: {e}")
            
    # 2. Try OpenAI DALL-E 3
    if OPENAI_API_KEY:
        try:
            print(">> Generating image via OpenAI DALL-E 3...")
            client = OpenAI(api_key=OPENAI_API_KEY)
            response = client.images.generate(
                model="dall-e-3",
                prompt=image_prompt,
                size="1792x1024",
                quality="standard",
                n=1
            )
            img_url = response.data[0].url
            img_data = requests.get(img_url).content
            with open(out_path, "wb") as f:
                f.write(img_data)
            print(f">> Saved image to {out_path}")
            return True
        except Exception as e:
            print(f"OpenAI DALL-E 3 image generation failed: {e}")
            
    print("ERROR: Image generation failed (no API keys or request error). Please manually add a cover to images/queue/.")
    return False

def update_metadata(filename, title, tags):
    metadata = {}
    if os.path.exists(METADATA_PATH):
        try:
            with open(METADATA_PATH, "r") as f:
                metadata = json.load(f)
        except Exception as e:
            pass
            
    metadata[filename] = {
        "title": title,
        "tags": tags
    }
    
    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f">> Updated images/metadata.json for {filename}")

def run_pipeline(dry_run=False):
    if dry_run:
        print("[DRY-RUN] Would run full-pipeline.sh in schedule mode.")
        return
        
    print(">> Launching full-pipeline.sh in schedule mode...")
    pipeline_script = os.path.join(SCRIPT_DIR, "full-pipeline.sh")
    cmd = [
        "/bin/bash",
        pipeline_script,
        "auto",
        "auto",
        os.path.join(ROOT_DIR, "descriptions", "template.txt"),
        "0.93",
        "schedule"
    ]
    try:
        subprocess.run(cmd, check=True)
        print(">> Autopilot run completed successfully!")
    except Exception as e:
        print(f"ERROR running full-pipeline: {e}")

def main():
    parser = argparse.ArgumentParser(description="Dronemill Autopilot - Automated Sourcing & Schedulers")
    parser.add_argument("--dry-run", action="store_true", help="Perform search and LLM mocks without writing files or calling paid APIs")
    parser.add_argument("--test-generation", action="store_true", help="Test LLM and image generator endpoints using a mock prompt")
    args = parser.parse_args()
    
    configs = load_configs()
    history = load_history()
    
    if args.test_generation:
        print("=== Test Generation Mode ===")
        assets = generate_creative_assets("Test Deep Water Poolrooms Ambient 1 Hour")
        print(f"LLM Result: {json.dumps(assets, indent=2)}")
        next_img = get_next_image_filename()
        print(f"Next image filename: {next_img}")
        generate_image_ai(assets["image_prompt"], next_img, dry_run=args.dry_run)
        return
        
    print("=== Dronemill Autopilot Start ===")
    aud_stock, img_stock = get_queue_files()
    print(f"Current Stock: {aud_stock} audio, {img_stock} images in queue.")
    
    if aud_stock >= configs.get("stock_threshold", 3) and img_stock >= configs.get("stock_threshold", 3):
        print(f">> Stock is sufficient (threshold is {configs.get('stock_threshold')}). No sourcing needed.")
        run_pipeline(dry_run=args.dry_run)
        return
        
    print(">> Sourcing new content...")
    downloaded_audio = None
    selected_video = None
    
    for query in configs.get("search_queries", []):
        videos = search_videos(
            query,
            configs.get("duration_min_seconds", 1800),
            configs.get("duration_max_seconds", 10800),
            configs.get("max_search_results_per_query", 5)
        )
        
        for vid in videos:
            if vid["id"] not in history:
                print(f">> Found new target: '{vid['title']}' ({vid['duration']}s)")
                selected_video = vid
                downloaded_audio = download_audio(vid["url"], dry_run=args.dry_run)
                if downloaded_audio or args.dry_run:
                    break
        if downloaded_audio or args.dry_run:
            break
            
    if not selected_video:
        print(">> No new videos found matching criteria and not in history.")
        # Fallback to run pipeline with whatever is in stock, if any
        if aud_stock > 0 and img_stock > 0:
            print(">> Running pipeline with existing stock...")
            run_pipeline(dry_run=args.dry_run)
        return
        
    # Generate creative assets for the downloaded audio
    assets = generate_creative_assets(selected_video["title"])
    print(f">> Creative Titles generated: '{assets.get('title')}'")
    
    # Generate cover art
    next_img = get_next_image_filename()
    print(f">> Generating cover art '{next_img}'...")
    success = generate_image_ai(assets["image_prompt"], next_img, dry_run=args.dry_run)
    
    if success and not args.dry_run:
        update_metadata(next_img, assets["title"], assets["tags"])
        history.add(selected_video["id"])
        save_history(history)
        
    # Run the rendering and upload pipeline
    run_pipeline(dry_run=args.dry_run)

if __name__ == "__main__":
    main()

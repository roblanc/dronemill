import os
import re
import json
import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPTS_FILE = os.path.join(SCRIPT_DIR, "../prompts.md")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "../images/metadata.json")
API_KEY = os.environ.get("OPENROUTER_API_KEY")

def get_prompts():
    with open(PROMPTS_FILE, "r") as f:
        content = f.read()
    prompts = re.findall(r"(\d+)\.\s+(.*)", content)
    return prompts

def generate_seo_metadata(prompt_text):
    system_prompt = (
        "You are a YouTube SEO expert for a cosmic horror ambience channel. "
        "Create a compelling, mysterious, and clickable title (max 60 chars) and 3-5 tags for the given scene. "
        "The title should reflect the scene but sound like a dark mystery or narrative hook. "
        "Do not use generic 'Ambient Music' titles, make them sound like stories. "
        "Respond with a JSON object containing keys: 'title' (string) and 'tags' (list of strings)."
    )
    
    # 1. Try OpenRouter if API key is present
    if API_KEY:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "google/gemini-2.0-flash-001",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Scene description: {prompt_text}"}
            ],
            "response_format": { "type": "json_object" }
        }
        try:
            print("  Trying OpenRouter...")
            response = requests.post(url, headers=headers, json=data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"].strip()
                if content.startswith("```"):
                    content = re.sub(r"^```(?:json)?\n", "", content)
                    content = re.sub(r"\n```$", "", content).strip()
                return json.loads(content)
            else:
                print(f"  OpenRouter error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"  OpenRouter failed: {e}")
            
    # 2. Try local Ollama fallback
    print("  Trying local Ollama (phi3:latest)...")
    url_ollama = "http://localhost:11434/v1/chat/completions"
    headers_ollama = {
        "Content-Type": "application/json"
    }
    data_ollama = {
        "model": "phi3:latest",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Scene description: {prompt_text}"}
        ],
        "response_format": { "type": "json_object" }
    }
    try:
        response = requests.post(url_ollama, headers=headers_ollama, json=data_ollama, timeout=90)
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\n", "", content)
                content = re.sub(r"\n```$", "", content).strip()
            return json.loads(content)
        else:
            print(f"  Ollama error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"  Ollama failed: {e}")
        
    # 3. Simple fallback
    print("  Using static template fallback...")
    return {
        "title": f"The Mystery of {prompt_text[:30]}...",
        "tags": ["cosmic horror", "ambient", "mystery"]
    }

def main():
    prompts = get_prompts()
    metadata = {}
    
    # Load existing if any
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            metadata = json.load(f)

    print(f"Generating metadata for {len(prompts)} prompts...")
    
    for num, text in prompts:
        filename = f"{num.zfill(3)}.png"
        if filename in metadata:
            continue
            
        print(f"  Processing {filename}...")
        meta = generate_seo_metadata(text)
        metadata[filename] = {
            "prompt": text,
            "title": meta.get("title", f"Untitled {num}"),
            "tags": meta.get("tags", ["cosmic horror", "ambient"])
        }
        # Small delay to be safe
        import time
        time.sleep(0.5)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(metadata, f, indent=2)
    print("Done! Metadata saved to ../images/metadata.json")

if __name__ == "__main__":
    main()

import os
import re
import json
import requests

PROMPTS_FILE = "../prompts.md"
OUTPUT_FILE = "../images/metadata.json"
API_KEY = os.environ.get("OPENROUTER_API_KEY")

def get_prompts():
    with open(PROMPTS_FILE, "r") as f:
        content = f.read()
    prompts = re.findall(r"(\d+)\.\s+(.*)", content)
    return prompts

def generate_seo_metadata(prompt_text):
    # Use OpenRouter for just a tiny bit of text (should be cheap/free or very low tokens)
    # If the user is COMPLETELY out of credits, this might fail too.
    # But for 100 titles, it's like 5k tokens total.
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    system_prompt = "You are a YouTube SEO expert for a cosmic horror ambience channel. Create a compelling, mysterious, and clickable title (max 60 chars) and 3-5 tags for the given scene. The title should reflect the scene but sound like a dark mystery or narrative hook. Do not use generic 'Ambient Music' titles, make them sound like stories."
    
    data = {
        "model": "google/gemini-2.0-flash-001", # Very cheap model
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Scene description: {prompt_text}"}
        ],
        "response_format": { "type": "json_object" }
    }
    
    try:
        # If no credits, fallback to template
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            return json.loads(content)
    except:
        pass
    
    # Simple fallback
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

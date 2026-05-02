import os
import re
import requests
import time
import sys
import json
import base64

# Configuration
PROMPTS_FILE = "../prompts.md"
OUTPUT_DIR = "../images/queue"
API_KEY = os.environ.get("OPENROUTER_API_KEY")

if not API_KEY:
    print("ERROR: OPENROUTER_API_KEY not found in environment.")
    sys.exit(1)

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def get_prompts():
    with open(PROMPTS_FILE, "r") as f:
        content = f.read()
    
    # Extract master prefix
    prefix_match = re.search(r"## Master prompt prefix.*?```(.*?)```", content, re.DOTALL)
    prefix = prefix_match.group(1).strip() if prefix_match else ""
    
    # Extract suffix
    suffix_match = re.search(r"## Suffix to append.*?```(.*?)```", content, re.DOTALL)
    suffix = suffix_match.group(1).strip() if suffix_match else ""
    
    # Extract individual prompts (numbered lines)
    prompts = re.findall(r"(\d+)\.\s+(.*)", content)
    
    return prefix, suffix, prompts

def generate_image(full_prompt, filename):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "google/gemini-3.1-flash-image-preview",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": full_prompt}
                ]
            }
        ],
        "modalities": ["image"],
        "max_tokens": 3000,
        "image_config": {
            "aspect_ratio": "16:9"
        }
    }
    
    print(f"Generating: {filename}...")
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        
        if "choices" in result:
            message = result["choices"][0]["message"]
            if "images" in message:
                img_url = message["images"][0]["image_url"]["url"]
                
                # Handle data URIs
                if img_url.startswith("data:"):
                    header, encoded = img_url.split(",", 1)
                    img_data = base64.b64decode(encoded)
                else:
                    # Download image from URL
                    img_data = requests.get(img_url).content
                
                with open(os.path.join(OUTPUT_DIR, filename), "wb") as f:
                    f.write(img_data)
                print(f"  Done: {filename}")
                return True
            else:
                print(f"  FAILED: No images in response. Result: {json.dumps(result)}")
        else:
            print(f"  FAILED: No choices in response. Result: {json.dumps(result)}")
        return False
    except Exception as e:
        print(f"  FAILED: {filename} - {str(e)}")
        try:
            print(f"  Response: {response.text}")
        except:
            pass
        return False

def main():
    prefix, suffix, prompts = get_prompts()
    
    # Process all prompts if they don't exist
    count = 0
    
    for num, text in prompts:
        filename = f"{num.zfill(3)}.png"
        
        # Check if already exists
        if os.path.exists(os.path.join(OUTPUT_DIR, filename)):
            # print(f"Skipping {filename} (already exists)")
            continue
            
        full_prompt = f"{prefix} {text} {suffix}"
        success = generate_image(full_prompt, filename)
        
        if success:
            count += 1
            # Rate limiting / polite wait
            time.sleep(1)
        else:
            # If we hit an error, stop to avoid burning credits or looping on errors
            print("Stopping due to error.")
            break

if __name__ == "__main__":
    main()

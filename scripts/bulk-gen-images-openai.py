import os
import re
import time
import sys
import requests
from openai import OpenAI

# Configuration
PROMPTS_FILE = "../prompts.md"
OUTPUT_DIR = "../images/queue"
API_KEY = os.environ.get("OPENAI_API_KEY")

if not API_KEY:
    print("ERROR: OPENAI_API_KEY not found in environment.")
    print("Please set it by running: export OPENAI_API_KEY='your-key'")
    sys.exit(1)

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

client = OpenAI(api_key=API_KEY)

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
    print(f"Generating: {filename}...")
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=full_prompt,
            size="1792x1024", # Widescreen for YouTube
            quality="standard",
            n=1,
        )
        img_url = response.data[0].url
        img_data = requests.get(img_url).content
        with open(os.path.join(OUTPUT_DIR, filename), "wb") as f:
            f.write(img_data)
        print(f"  Done: {filename}")
        return True
    except Exception as e:
        print(f"  FAILED: {filename} - {str(e)}")
        return False

def main():
    prefix, suffix, prompts = get_prompts()
    
    print(f"Loaded {len(prompts)} prompts. Starting DALL-E 3 generation...")
    
    count = 0
    for num, text in prompts:
        filename = f"{num.zfill(3)}.png"
        
        # Skip if already exists
        if os.path.exists(os.path.join(OUTPUT_DIR, filename)):
            continue
            
        full_prompt = f"{prefix} {text} {suffix}"
        success = generate_image(full_prompt, filename)
        
        if success:
            count += 1
            time.sleep(2) # rate limiting
        else:
            print("Stopping due to error. Check your OpenAI API limits.")
            break

if __name__ == "__main__":
    main()

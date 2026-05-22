import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
METADATA_PATH = os.path.join(SCRIPT_DIR, '../images/metadata.json')

def get_suffix(index):
    if 1 <= index <= 17:
        return " | Pure Cosmic Horror Ambience"
    elif 18 <= index <= 22:
        return " | [No AI] Arctic Cosmic Horror"
    elif 23 <= index <= 34:
        return " | Cosmic Academia Ambience"
    elif 35 <= index <= 46:
        return " | Deep Space Horror Ambience"
    elif 47 <= index <= 56:
        return " | Eldritch Forest Ambience"
    elif 57 <= index <= 66:
        return " | Pure Cosmic Horror Ambience"
    elif 67 <= index <= 78:
        return " | Prehistoric Cozy Ambience"
    elif 79 <= index <= 90:
        return " | Cozy Sci-Fi Ambience"
    elif 91 <= index <= 100:
        return " | Dreamcore / Liminal Ambience"
    elif 101 <= index <= 110:
        return " | Pure Cosmic Horror Ambience"
    elif 111 <= index <= 117:
        return " | Lighthouse Cosmic Horror Ambience"
    return " | Pure Cosmic Horror Ambience"

ALL_SUFFIXES = [
    " | Pure Cosmic Horror Ambience",
    " | [No AI] Arctic Cosmic Horror",
    " | Cosmic Academia Ambience",
    " | Deep Space Horror Ambience",
    " | Eldritch Forest Ambience",
    " | Prehistoric Cozy Ambience",
    " | Cozy Sci-Fi Ambience",
    " | Dreamcore / Liminal Ambience",
    " | Lighthouse Cosmic Horror Ambience"
]

def update_metadata():
    if not os.path.exists(METADATA_PATH):
        print(f"Error: {METADATA_PATH} not found")
        return

    with open(METADATA_PATH, 'r') as f:
        data = json.load(f)

    updated_count = 0
    for filename, meta in data.items():
        if filename.endswith('.png'):
            try:
                index = int(filename.split('.')[0])
                suffix = get_suffix(index)
                title = meta.get('title', '')
                
                # Strip any existing suffix if present
                base_title = title
                for s in ALL_SUFFIXES:
                    if base_title.endswith(s):
                        base_title = base_title[:-len(s)].strip()
                        break
                
                new_title = f"{base_title}{suffix}"
                if title != new_title:
                    meta['title'] = new_title
                    print(f"Updated {filename}: {title} -> {new_title}")
                    updated_count += 1
            except ValueError:
                continue

    if updated_count > 0:
        with open(METADATA_PATH, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Local metadata.json updated successfully with {updated_count} changes.")
    else:
        print("No metadata updates needed.")

if __name__ == "__main__":
    update_metadata()

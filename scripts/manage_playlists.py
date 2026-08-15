#!/usr/bin/env python3
"""
DroneMill Themed Playlist Curator & SEO Architecture.
Categorizes all channel uploads from output/upload_history.json into
high-retention algorithmic playlists.

Usage:
  python3 scripts/manage_playlists.py
"""

import os
import json

ROOT = "/home/brewuser/projects/dronemill"

PLAYLISTS = {
    "The Lighthouse Archive | Lovecraftian & Cosmic Horror Ambience": {
        "description": "Archival 1890s-1920s daguerreotype soundscapes, abyssal ocean depths, colossal monoliths, and cosmic dread. Mastered at -22 LUFS for deep immersion.",
        "keywords": ["lovecraftian", "lighthouse", "keeper", "cosmic", "abyss", "carcosa", "arkham", "dread", "oceanic dark", "chapel", "monolith", "salt archive"],
        "videos": []
    },
    "Liminal Dreamcore & Nostalgic Spaces": {
        "description": "Eerie, nostalgic, and comforting liminal ambient drone. Empty 4 AM airport lounges, deserted bowling alleys, infinite tile bathhouses, and quiet night streets.",
        "keywords": ["liminal", "transit", "poolroom", "bathhouse", "airport", "lounge", "bowling", "ferry", "diner", "video store", "rewind", "carpet", "mallsoft"],
        "videos": []
    },
    "Lived-In Sci-Fi & Deep Space Havens": {
        "description": "Warm, analog, and realistic science fiction ambient soundscapes. Orbital greenhouses, lunar sleeper cabins, asteroid asteroid galleys, and deep-space freighters.",
        "keywords": ["sci-fi", "orbital", "europa", "ceramics", "lunar", "train", "freighter", "asteroid", "deep space", "spacecraft", "station"],
        "videos": []
    },
    "Glacial Silence & Ancient Earth": {
        "description": "Pure macro acoustics of compressed blue glacier ice, prehistoric rain hollows, and vast untouched natural solitude.",
        "keywords": ["glacial", "ice", "protoceratops", "prehistoric", "thunder", "dunes", "gypsum", "forest", "mangrove", "amber", "noonbloom"],
        "videos": []
    }
}

def curate_playlists():
    history_file = f"{ROOT}/output/upload_history.json"
    if not os.path.exists(history_file):
        print(f"ERROR: {history_file} not found.")
        return
        
    with open(history_file, "r", encoding="utf-8") as f:
        history = json.load(f)
        
    # Group videos into playlists
    for item in history:
        title = item.get("title", "")
        title_lower = title.lower()
        
        assigned = False
        for pl_name, pl_data in PLAYLISTS.items():
            if any(k in title_lower for k in pl_data["keywords"]):
                pl_data["videos"].append({
                    "title": title,
                    "published_at": item.get("publish_at") or item.get("timestamp"),
                    "thumbnail": item.get("thumbnail")
                })
                assigned = True
                break
                
        if not assigned:
            # Fallback to Liminal Dreamcore
            PLAYLISTS["Liminal Dreamcore & Nostalgic Spaces"]["videos"].append({
                "title": title,
                "published_at": item.get("publish_at") or item.get("timestamp"),
                "thumbnail": item.get("thumbnail")
            })

    out_file = f"{ROOT}/output/curated_playlists.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(PLAYLISTS, f, indent=2)
        
    print("===================================================================")
    print("✨ DRONEMILL THEMED PLAYLIST CURATION REPORT")
    print("===================================================================")
    for pl_name, pl_data in PLAYLISTS.items():
        print(f"\n📂 Playlist: {pl_name}")
        print(f"   Description: {pl_data['description']}")
        print(f"   Total Videos: {len(pl_data['videos'])}")
        for vid in pl_data["videos"][:3]:
            print(f"   • {vid['title']}")
        if len(pl_data["videos"]) > 3:
            print(f"   • ... and {len(pl_data['videos']) - 3} more videos")
            
    print(f"\nSaved structured playlist architecture to: {out_file}")

if __name__ == "__main__":
    curate_playlists()

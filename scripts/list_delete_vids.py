#!/usr/bin/env python3
import os
import sys
import json
import datetime
from google.oauth2.credentials import Credentials
import googleapiclient.discovery
import googleapiclient.errors

# Paths
HOME = os.path.expanduser("~")
TOKEN_PATH = os.path.join(HOME, ".youtubeuploader", "request.token")
SECRETS_PATH = os.path.join(HOME, ".youtubeuploader", "client_secrets.json")

def load_credentials():
    if not os.path.exists(TOKEN_PATH) or not os.path.exists(SECRETS_PATH):
        print("ERROR: Credentials not found. Make sure request.token and client_secrets.json exist.")
        sys.exit(1)
        
    with open(TOKEN_PATH, "r") as f:
        token_data = json.load(f)
        
    with open(SECRETS_PATH, "r") as f:
        secrets_data = json.load(f)
        
    client_config = secrets_data.get("installed", secrets_data.get("web", {}))
    client_id = client_config.get("client_id")
    client_secret = client_config.get("client_secret")
    
    if not client_id or not client_secret:
        print("ERROR: Could not parse client_id and client_secret.")
        sys.exit(1)
        
    return Credentials(
        token=token_data.get("access_token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret
    )

def main():
    import argparse
    parser = argparse.ArgumentParser(description="List and delete YouTube videos")
    parser.add_argument("--delete", help="Comma-separated list of video IDs to delete")
    args = parser.parse_args()

    creds = load_credentials()
    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
    
    # If delete argument is provided
    if args.delete:
        video_ids = [vid.strip() for vid in args.delete.split(",") if vid.strip()]
        print(f"Requested deletion of {len(video_ids)} videos: {video_ids}")
        for vid in video_ids:
            print(f"Deleting video {vid}...")
            try:
                youtube.videos().delete(id=vid).execute()
                print(f"Successfully deleted {vid}")
            except googleapiclient.errors.HttpError as e:
                print(f"Error deleting {vid}: {e}")
        return

    # 1. Get uploads playlist
    print("Fetching channel uploads playlist...")
    try:
        channels_response = youtube.channels().list(
            mine=True,
            part="contentDetails,snippet"
        ).execute()
    except googleapiclient.errors.HttpError as e:
        print(f"API Error fetching channel: {e}")
        sys.exit(1)
        
    if not channels_response.get("items"):
        print("ERROR: No channels found for credentials.")
        sys.exit(1)
        
    channel = channels_response["items"][0]
    channel_title = channel["snippet"]["title"]
    uploads_playlist_id = channel["contentDetails"]["relatedPlaylists"]["uploads"]
    print(f"Authenticated as Channel: {channel_title} ({channel['id']})")
    print(f"Uploads playlist ID: {uploads_playlist_id}")
    print("--------------------------------------------------")
    
    # 2. List items in uploads playlist
    print("Fetching uploaded/scheduled videos...")
    videos = []
    next_page_token = None
    
    while True:
        playlist_response = youtube.playlistItems().list(
            playlistId=uploads_playlist_id,
            part="snippet,status",
            maxResults=50,
            pageToken=next_page_token
        ).execute()
        
        # To get publishAt, we will collect video IDs from this page and request video details
        page_video_ids = []
        for item in playlist_response.get("items", []):
            page_video_ids.append(item["snippet"]["resourceId"]["videoId"])
            
        if page_video_ids:
            # Fetch details in batches of 50
            vid_response = youtube.videos().list(
                id=",".join(page_video_ids),
                part="snippet,status"
            ).execute()
            
            for item in vid_response.get("items", []):
                video_id = item["id"]
                title = item["snippet"]["title"]
                privacy = item["status"].get("privacyStatus", "unknown")
                publish_at = item["status"].get("publishAt", "N/A")
                
                # We are interested in private/unlisted/scheduled videos for cleanup
                if privacy in ["private", "unlisted"]:
                    videos.append({
                        "id": video_id,
                        "title": title,
                        "privacy": privacy,
                        "publish_at": publish_at
                    })
            
        next_page_token = playlist_response.get("nextPageToken")
        if not next_page_token:
            break
            
    print(f"Found {len(videos)} private/unlisted/scheduled videos.")
    for idx, v in enumerate(videos):
        print(f"[{idx+1}] ID: {v['id']} | Privacy: {v['privacy']} | Scheduled: {v['publish_at']} | Title: {v['title']}")
        
if __name__ == "__main__":
    main()

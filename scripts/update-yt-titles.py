import json
import os
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# Paths
TOKEN_PATH = os.path.expanduser('~/.youtubeuploader/request.token')
SECRETS_PATH = os.path.expanduser('~/.youtubeuploader/client_secrets.json')
METADATA_PATH = '/Users/romica/Developer/GitHub/dronemill/images/metadata.json'

def get_credentials():
    with open(TOKEN_PATH, 'r') as f:
        token_data = json.load(f)
    with open(SECRETS_PATH, 'r') as f:
        secrets_data = json.load(f)
    
    creds = Credentials(
        token=token_data['access_token'],
        refresh_token=token_data.get('refresh_token'),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=secrets_data['installed']['client_id'],
        client_secret=secrets_data['installed']['client_secret'],
        scopes=["https://www.googleapis.com/auth/youtube"]
    )
    
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Update token file
        token_data['access_token'] = creds.token
        with open(TOKEN_PATH, 'w') as f:
            json.dump(token_data, f)
            
    return creds

def update_titles():
    creds = get_credentials()
    youtube = build('youtube', 'v3', credentials=creds)

    # Load local metadata for reference
    with open(METADATA_PATH, 'r') as f:
        metadata = json.load(f)

    # Fetch last 50 videos from the channel
    print("Fetching last 50 videos...")
    request = youtube.search().list(
        part="snippet",
        forMine=True,
        maxResults=50,
        type="video",
        order="date"
    )
    response = request.execute()

    for item in response.get('items', []):
        video_id = item['id']['videoId']
        current_title = item['snippet']['title']
        
        # Check if this title is one of ours but without the suffix
        # Or if it's one of the ones we just uploaded
        match_found = False
        new_title = None

        for filename, meta in metadata.items():
            base_title = meta['title'].split(' | ')[0]
            if current_title == base_title:
                new_title = meta['title']
                match_found = True
                break
        
        if match_found and new_title != current_title:
            print(f"Updating Video {video_id}: '{current_title}' -> '{new_title}'")
            update_request = youtube.videos().update(
                part="snippet",
                body={
                    "id": video_id,
                    "snippet": {
                        "title": new_title,
                        "categoryId": item['snippet'].get('categoryId', '10'), # Default to Music
                        "description": item['snippet'].get('description', '')
                    }
                }
            )
            update_request.execute()
            print(f"Successfully updated {video_id}")
        else:
            print(f"Skipping {video_id}: '{current_title}' (No update needed or no match)")

if __name__ == "__main__":
    update_titles()

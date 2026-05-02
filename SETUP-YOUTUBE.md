# YouTube Auto-Upload Setup

Channel: `@timelessambience55`

## One-time setup (~10 min)

### 1. Install youtubeuploader
```bash
brew install youtubeuploader
```

### 2. Google Cloud Console
1. Go to https://console.cloud.google.com/
2. Create new project: `timeless-ambience-uploader`
3. Sidebar → "APIs & Services" → "Library" → search "YouTube Data API v3" → Enable
4. Sidebar → "APIs & Services" → "OAuth consent screen":
   - User Type: External
   - App name: `timeless-ambience-uploader`
   - User support email: dumitriurobert0@gmail.com
   - Developer email: dumitriurobert0@gmail.com
   - Skip scopes
   - Add yourself as test user (dumitriurobert0@gmail.com)
5. Sidebar → "Credentials" → "+ Create Credentials" → "OAuth client ID":
   - Type: **Desktop app**
   - Name: `youtubeuploader-cli`
   - Download JSON

### 3. Place credentials
```bash
mkdir -p ~/.youtubeuploader
mv ~/Downloads/client_secret_*.json ~/.youtubeuploader/client_secrets.json
```

### 4. First auth (browser flow)
Run any upload command — youtubeuploader opens browser:
```bash
cd ~/Desktop/cosmic-video/scripts
./upload-yt.sh ../output/erebus_v1.mp4 "test upload" ../descriptions/test.txt ../images/erebus_cover.png private
```
Browser opens → choose Google account that owns `@timelessambience55`. If brand account: select it from "Choose an account" screen. Token saved to `~/.youtubeuploader/request.token`. Future runs are headless.

## Constraints

- **Privacy lock:** Unverified Google apps can only upload as `private` or `unlisted`. To make public: open YT Studio, flip toggle. One-click.
- **Quota:** 10,000 units/day. Upload = 1600. Max ~6 videos/day. Plenty.
- **Token expiry:** Refresh token doesn't expire as long as app stays "Testing" mode in OAuth consent screen + you log in once every ~7 days.
- **Brand account:** If `@timelessambience55` is a Brand Account, the Google account auth screen will show a sub-selector. Pick the brand channel, not personal.

## Daily workflow

```bash
cd ~/Desktop/cosmic-video/scripts

./full-pipeline.sh \
  ../audio/erebus_raw.mp3 \
  ../images/erebus_v3_cover.png \
  erebus_v3 \
  "signals from below | hms erebus abyssal ambient | 1 hour" \
  ../descriptions/erebus_v3.txt \
  0.91
```

## Description template

`descriptions/template.txt`:
```
1 hour of dark ambient soundscape inspired by HMS Erebus, the British Royal Navy ship that vanished into the Arctic ice during the Franklin Expedition of 1845.

frozen for sleep, deep work, writing, and atmospheric reading.

🜲 timestamps:
0:00 - drift begins
20:00 - deeper into the ice
40:00 - signals from below

🜲 if you enjoyed this, subscribe for more cosmic horror ambient soundscapes uploaded weekly.

#ambient #cosmichorror #darkambient #sleepmusic #studymusic
```

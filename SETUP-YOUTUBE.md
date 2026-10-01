# YouTube Auto-Upload Setup

Channel: `@timelessambience55`

## One-time setup (~10 min)

### 1. Install youtubeuploader
```bash
brew install youtubeuploader
```

### 2. Google Cloud Console — create project + enable API
1. Go to https://console.cloud.google.com/
2. Create new project: `timeless-ambience-uploader`
3. Sidebar → "APIs & Services" → "Library" → search "YouTube Data API v3" → Enable

### 3. Google Auth Platform — configure OAuth
**Note:** Google renamed "OAuth consent screen" to "Google Auth Platform" (2025+ UI).

1. Sidebar → "APIs & Services" → "OAuth consent screen" (redirects to Google Auth Platform Overview)
2. Click **Get started**
3. **App information:**
   - App name: `timeless-ambience-uploader`
   - User support email: `avisualtheory@gmail.com`
4. **Audience:** select **External**
5. **Contact info:** `avisualtheory@gmail.com`
6. Agree to API Services User Data Policy → **Create**

### 4. Add test user
After creation:
1. Sidebar → **Audience** → "Test users" → **+ Add users**
2. Add: `avisualtheory@gmail.com` (sau email-ul care deține `@timelessambience55`)

### 5. Create OAuth client
1. Sidebar → **Clients** → **+ Create client**
2. Application type: **Desktop app**
3. Name: `youtubeuploader-cli`
4. **Create** → click **Download JSON**

### 6. Place credentials
```bash
mkdir -p ~/.youtubeuploader
mv ~/Downloads/client_secret_*.json ~/.youtubeuploader/client_secrets.json
```

### 7. First auth (browser flow) - direct on server
Run any upload command — youtubeuploader opens Chromium directly on server (no SSH tunnel needed):
```bash
cd ~/projects/dronemill/scripts
./upload-yt.sh ../output/test.mp4 "test upload" ../descriptions/template.txt ../images/used/erebus_cover.png private
# or wizard: ./reauth-youtube.sh  -> choose [1] Direct on server via Chromium
```
Chromium runs headless on server at `http://localhost:9222` (CDP) and handles `http://localhost:8080/oauth2callback` automatically. Browser opens → choose Google account that owns `@timelessambience55`. If brand account: select it from "Choose an account" screen. Token saved to `~/.youtubeuploader/request.token`. Future runs are headless, no tunnel.

## Constraints & Permanent Token Setup

- **Privacy lock:** Unverified Google apps can only upload as `private` or `unlisted`. To schedule a public release: pass a future timestamp (`publishAt`), which sets the video private until the scheduled release time, when YouTube automatically makes it public.
- **Quota:** 10,000 units/day. Upload = 1,600 units. Max ~6 videos/day.
- **Permanent Token (Fixing the 7-day expiration):**
  - By default, Google Cloud OAuth apps in **"Testing"** mode expire their refresh tokens after **7 days**.
  - **To make the token permanent**:
    1. Go to https://console.cloud.google.com/
    2. APIs & Services → OAuth consent screen (Google Auth Platform).
    3. Under **Publishing status**, click **"Publish App"** to switch from *Testing* to *In production*.
    4. Ignore the Google verification prompt (verification is only needed for public multi-user apps, not private channel tools).
    5. Re-authenticate once with `./scripts/reauth-youtube.sh` (or `upload-yt.sh`).
    6. Once in Production, Google **never expires the refresh token**, enabling 100% autonomous unattended cron execution.
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

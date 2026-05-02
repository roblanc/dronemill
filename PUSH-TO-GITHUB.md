# Push to GitHub — when ready

## Pre-flight check (CRITICAL)

```bash
cd ~/Desktop/cosmic-video
git status        # should NOT list any .mp3/.mp4/.png/secrets
cat .gitignore    # verifica blocheaza credentialele
```

Dacă vezi `client_secrets.json` sau `*.token` în `git status` — STOP. Verifică `.gitignore`.

## Steps

```bash
# 1. init
cd ~/Desktop/cosmic-video
git init
git branch -M main

# 2. first commit
git add .
git status   # ULTIMA verificare
git commit -m "initial commit: cosmic-video pipeline"

# 3. create GitHub repo (private recommended)
# Via web: github.com/new → "cosmic-video" → Private → Create
# Sau via gh CLI: gh repo create cosmic-video --private --source=. --remote=origin

# 4. push
git remote add origin git@github.com:<USERNAME>/cosmic-video.git
git push -u origin main
```

## Pe mașină nouă (restore)

```bash
# 1. clone
git clone git@github.com:<USERNAME>/cosmic-video.git
cd cosmic-video

# 2. install tools
brew install ffmpeg yt-dlp youtubeuploader rubberband

# 3. transfer credentials manual (NU prin git)
# - copiezi client_secrets.json din 1Password / iCloud Drive
# - mv ~/Downloads/client_secrets.json ~/.youtubeuploader/
# - first run = browser OAuth (~30s)

# 4. populate audio/images
# Sync din iCloud / external drive / Drive — orice in afara de git
```

## Recommended: store secrets in iCloud Drive

Path: `~/Library/Mobile Documents/com~apple~CloudDocs/Secrets/cosmic-video/client_secrets.json`

Pe maşina nouă, simbolic-link:
```bash
ln -s ~/Library/Mobile\ Documents/com~apple~CloudDocs/Secrets/cosmic-video/client_secrets.json \
      ~/.youtubeuploader/client_secrets.json
```

## Repo recommendation: PRIVATE

Chiar cu `.gitignore` curat — repo privat = zero risc. Public dacă vrei sa-l demonstrezi în portofoliu, dar atunci adaugă .env.example în loc de orice referințe la credentiale reale.

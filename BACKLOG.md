# dronemill — Agent Backlog

## Loop Protocol
dronemill mass-produces 1-hour ambient YouTube videos.
Each task = one video: pick audio source → render → upload → archive thumbnail.

Pipeline command:
```bash
bash scripts/produce.sh <audio_file> <thumbnail_file> <title> <description_file>
```

## Queue

- [ ] Check `images/queue/` for any new thumbnails — render + upload a video for each one found
- [ ] Add a `scripts/batch.sh` that auto-processes the entire `images/queue/` folder end-to-end without manual input
- [ ] Write a cron-ready wrapper: `scripts/daily-produce.sh` that runs batch.sh daily at 3am and logs output to `logs/`
- [ ] Add a `descriptions/template.txt` with auto-fill placeholders for title, mood, and duration

## Notes
- Stack: ffmpeg, yt-dlp, youtubeuploader, bash, rubberband
- Videos go to @timelessambience55
- After upload, move thumbnail from `images/queue/` → `images/used/`

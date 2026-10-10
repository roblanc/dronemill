"""Read-only YouTube feed for the two dashboard channels. Never changes ledgers/videos."""
import datetime as dt
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path('/home/brewuser/projects/dronemill')
ANIME_ROOT = Path('/home/brewuser/projects/anime-whatif')
PUBLIC = 'https://roblanc.github.io/dronemill/'
CHANNEL_IDS = {'anime': 'UCPe5cgqBy0d2D2RgBD707gA', 'dronemill': 'UCjQ4h6BGkjEY6hB0M9fDGIg'}

def read_json(path):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def seconds(iso):
    m = re.fullmatch(r'P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso or '')
    return sum(int(v or 0) * n for v, n in zip(m.groups(), [86400,3600,60,1])) if m else 0

def absolute(url):
    return url if not url or url.startswith('https://') else PUBLIC + url.lstrip('/')

def feed_item(video, channel, known, now):
    status, snippet = video['status'], video['snippet']
    when = status.get('publishAt') if status.get('privacyStatus') == 'private' else snippet.get('publishedAt')
    if status.get('uploadStatus') in ('deleted', 'rejected', 'failed'):
        return None
    # Unscheduled private/unlisted uploads are deliberately absent from this public dashboard.
    if status.get('privacyStatus') != 'public' and not (status.get('privacyStatus') == 'private' and when):
        return None
    try:
        date = dt.datetime.fromisoformat(when.replace('Z', '+00:00'))
    except (AttributeError, ValueError):
        return None
    if status.get('privacyStatus') == 'private' and date <= now:
        return None
    duration = video.get('contentDetails', {}).get('duration')
    streams = video.get('fileDetails', {}).get('videoStreams', [])
    portrait = any(s.get('heightPixels', 0) >= s.get('widthPixels', 1) for s in streams)
    is_short = known.get('kind') == 'short' or (0 < seconds(duration) <= 180 and portrait)
    thumbs = snippet.get('thumbnails', {})
    thumb = (thumbs.get('medium') or thumbs.get('high') or thumbs.get('default') or {}).get('url')
    item = dict(title=snippet['title'], url=f"https://youtu.be/{video['id']}",
                publish_at=when, is_future=date > now, privacy=status.get('privacyStatus'),
                thumb=thumb or absolute(known.get('thumb')), duration=duration,
                views=None if date > now else int(video.get('statistics', {}).get('viewCount', 0)),
                kind='short' if is_short else 'video', on_youtube=True)
    if is_short and known.get('short_thumb'):
        item['short_thumb'] = absolute(known['short_thumb'])
    if channel == 'dronemill':
        item.update(id=video['id'], video_id=video['id'], youtube_url=item['url'], short_url=item['url'],
                    release_formatted=when, thumbnail=known.get('thumbnail'),
                    description=snippet.get('description',''), tags=snippet.get('tags',[]))
    return item

def snapshot(channel, yt=None, recent=False):
    if channel not in CHANNEL_IDS:
        raise ValueError('Unknown channel')
    if yt is None:
        if channel == 'anime':
            os.environ.setdefault('NOFACE_TOKEN', '/root/.youtubeuploader-anime/python_token.json')
            sys.path.insert(0, str(ANIME_ROOT / 'scripts'))
            import noface_youtube
            yt = noface_youtube.service()
        else:
            sys.path.insert(0, str(ROOT / 'scripts'))
            import youtube_schedule
            youtube_schedule.TOKEN_PATH = '/home/brewuser/.youtubeuploader/request.token'
            youtube_schedule.SECRETS_PATH = '/home/brewuser/.youtubeuploader/client_secrets.json'
            yt = youtube_schedule._youtube()
    ch = yt.channels().list(mine=True, part='snippet,contentDetails').execute()['items'][0]
    if ch['id'] != CHANNEL_IDS[channel]:
        raise RuntimeError('Configured YouTube account does not match requested channel')
    known = {}
    for row in read_json(ROOT / 'docs/data' / ('anime.json' if channel == 'anime' else 'schedule.json')):
        vid = row.get('video_id') or row.get('url', '').rsplit('/', 1)[-1] or f"plan-{row.get('id')}"
        known[vid] = row
    history_ids = set(known)
    saved = read_json(Path('/var/lib/dronemill-live') / f'{channel}.json')
    if isinstance(saved, dict):
        recent_past = sorted((i for i in saved.get('items', []) if not i.get('is_future') and i.get('on_youtube') is not False),
                             key=lambda i:i.get('publish_at',''),reverse=True)[:40]
        for row in [i for i in saved.get('items', []) if i.get('is_future') or i.get('on_youtube') is False] + recent_past:
            vid = row.get('video_id') or row.get('url', '').rsplit('/', 1)[-1] or f"plan-{row.get('id')}"
            known[vid] = {**known.get(vid, {}), **row}
    ids, page = [], None
    while True:
        response = yt.playlistItems().list(playlistId=ch['contentDetails']['relatedPlaylists']['uploads'],
                    part='contentDetails', maxResults=50, pageToken=page).execute()
        ids.extend(v['contentDetails']['videoId'] for v in response.get('items', []))
        page = response.get('nextPageToken')
        if recent or not page:
            break
    if recent:
        ids = list(dict.fromkeys(ids + [vid for vid in known if re.fullmatch(r'[\w-]{11}', vid)]))
    now = dt.datetime.now(dt.timezone.utc)
    items = []
    for k in range(0, len(ids), 50):
        response = yt.videos().list(id=','.join(ids[k:k+50]),
                    part='snippet,status,contentDetails,statistics,fileDetails').execute()
        for v in response.get('items', []):
            item = feed_item(v, channel, known.get(v['id'], {}), now)
            if item:
                items.append(item)
    future = sorted((i for i in items if i['is_future']), key=lambda i:i['publish_at'])
    past = sorted((i for i in items if not i['is_future']), key=lambda i:i['publish_at'], reverse=True)
    shown = future + (past[:40] if channel == 'anime' else [i for n,i in enumerate(past) if n < 40 or i['video_id'] in history_ids])
    if channel == 'dronemill':
        # Retain the existing local plans in All; they still do not count as YouTube schedules.
        actual = {i['video_id'] for i in shown}
        for previous in known.values():
            if previous.get('on_youtube') is False and previous.get('video_id') not in actual:
                shown.append(previous)
    avatar = ch['snippet'].get('thumbnails', {})
    return dict(channel=channel, channel_id=ch['id'], items=shown, stale=False,
                updated_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                avatar=(avatar.get('medium') or avatar.get('default') or {}).get('url'))

if __name__ == '__main__':
    print(json.dumps(snapshot(sys.argv[1],recent='--recent' in sys.argv)))

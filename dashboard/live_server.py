"""Loopback-only read-only feed API, exposed by a dedicated HTTPS tunnel."""
import datetime as dt
import http.server
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parents[1]
STATE = Path(os.environ.get('DRONEMILL_LIVE_STATE', '/var/lib/dronemill-live'))
STATE.mkdir(parents=True, exist_ok=True)
TTL = 55
CACHE = {}
LAST_FULL = {}
LOCKS = {c:threading.Lock() for c in ['anime','dronemill']}

def get_feed(channel, force=False):
    with LOCKS[channel]:
        cached = CACHE.get(channel)
        age = time.monotonic() - cached[0] if cached else float('inf')
        if cached and age < (5 if force else TTL):
            return cached[1]
        env = os.environ.copy()
        full = force or not cached or time.monotonic() - LAST_FULL.get(channel,0) > 600
        command = [sys.executable, str(ROOT/'scripts/live_youtube_feed.py'),channel]
        if not full:
            command.append('--recent')
        try:
            result = subprocess.run(command,
                        env=env, capture_output=True, text=True, check=True, timeout=45)
            data = json.loads(result.stdout)
            CACHE[channel] = (time.monotonic(),data)
            if full:
                LAST_FULL[channel] = time.monotonic()
            tmp = STATE/f'{channel}.tmp'
            tmp.write_text(json.dumps(data))
            tmp.replace(STATE/f'{channel}.json')
            return data
        except (subprocess.SubprocessError, ValueError):
            print(f'Live YouTube lookup failed for {channel}', flush=True)
            if not cached:
                try:
                    cached=(0,json.loads((STATE/f'{channel}.json').read_text()))
                except (OSError,ValueError):
                    raise RuntimeError('YouTube is temporarily unavailable') from None
            # Never replace a good snapshot with an empty feed or claim stale data is live.
            return {**cached[1], 'stale':True}

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        channel = {'/api/anime':'anime','/api/schedule':'dronemill'}.get(parsed.path)
        if parsed.path == '/health':
            return self.send_json({'status':'ok'})
        if not channel:
            return self.send_json({'error':'Not found'},404)
        origin = self.headers.get('Origin')
        if origin and origin != 'https://roblanc.github.io':
            return self.send_json({'error':'Origin not allowed'},403)
        try:
            data = get_feed(channel,parse_qs(parsed.query).get('refresh') == ['1'])
            self.send_json(data)
        except RuntimeError:
            self.send_json({'error':'YouTube is temporarily unavailable'},503)

    def send_json(self, data, status=200):
        body=json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Access-Control-Allow-Origin','https://roblanc.github.io')
        self.send_header('Vary','Origin')
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers()
        self.wfile.write(body)

if __name__ == '__main__':
    http.server.ThreadingHTTPServer(('127.0.0.1',8890),Handler).serve_forever()

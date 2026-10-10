"""Publish live snapshots to a dedicated data branch of the existing dashboard repo."""
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT=Path('/home/brewuser/projects/dronemill')
REPO=Path('/home/brewuser/.local/share/dronemill-live-feed.git')
BRANCH='dashboard-feed'
CONSENT=ROOT/'dashboard/live-publish-consent.json'
SOURCES=[Path('/home/brewuser/projects/anime-whatif/published.json'), ROOT/'output/upload_history.json',
         Path('/var/lib/dronemill-live/refresh-request')]
FIELDS={'title','url','publish_at','is_future','thumb','short_thumb','duration','views','kind','on_youtube',
        'id','video_id','youtube_url','short_url','privacy','release_formatted'}

def versions():
    result=[]
    for path in SOURCES:
        try:
            stat=path.stat();result.append((stat.st_ino,stat.st_mtime_ns,stat.st_size))
        except FileNotFoundError:result.append(None)
    return result

def public_snapshot(data):
    return {'channel':data['channel'],'updated_at':data['updated_at'],'stale':False,'avatar':data.get('avatar'),
            'items':[{k:v for k,v in i.items() if k in FIELDS} for i in data['items'] if i.get('on_youtube') is not False]}

def git(*args,input=None,check=True,bare=True):
    prefix=['sudo','-u','brewuser','git']
    prefix += ['--git-dir='+str(REPO)] if bare else ['-C',str(ROOT)]
    result=subprocess.run(prefix+list(args),input=input,capture_output=True,text=True,check=check,timeout=40)
    return result

def initialize():
    consent=json.loads(CONSENT.read_text())
    if consent.get('channels') != ['anime','dronemill']:
        raise RuntimeError('Explicit approval for these public schedule fields is required')
    if REPO.exists():
        if not (REPO/'dronemill-managed').exists():
            raise RuntimeError('Existing repository is not marked as this dashboard feed')
        return
    remote=git('remote','get-url','origin',bare=False).stdout.strip()
    found=git('ls-remote','--heads','origin','refs/heads/'+BRANCH,bare=False).stdout.strip()
    if found:
        raise RuntimeError('Data branch already exists; inspect before using it')
    subprocess.run(['sudo','-u','brewuser','git','init','--bare',str(REPO)],check=True,capture_output=True)
    git('remote','add','origin',remote)
    git('config','user.name','DroneMill Feed')
    git('config','user.email','dronemill-feed@users.noreply.github.com')
    subprocess.run(['sudo','-u','brewuser','python3','-c',
                    'from pathlib import Path; import sys; Path(sys.argv[1]).write_text("DroneMill live feed\\n")',
                    str(REPO/'dronemill-managed')],check=True)

def publish(force=False):
    channels={}
    for channel,endpoint in [('anime','anime'),('dronemill','schedule')]:
        with urllib.request.urlopen('http://127.0.0.1:8890/api/'+endpoint+('?refresh=1' if force else ''),timeout=50) as response:
            data=json.load(response)
        if data.get('stale'):
            raise RuntimeError('Keeping the last good published snapshot while YouTube is unavailable')
        channels[channel]=public_snapshot(data)
    body=json.dumps({'channels':channels},separators=(',',':'))+'\n'
    parent=git('rev-parse','--verify','refs/heads/'+BRANCH,check=False)
    blob=git('hash-object','-w','--stdin',input=body).stdout.strip()
    if parent.returncode==0:
        previous=git('rev-parse','refs/heads/'+BRANCH+':feed.json').stdout.strip()
        if blob==previous:
            return
    tree=git('mktree',input=f'100644 blob {blob}\tfeed.json\n').stdout.strip()
    args=['commit-tree',tree,'-m','chore(dashboard): refresh YouTube feed']
    if parent.returncode==0:args+=['-p',parent.stdout.strip()]
    commit=git(*args).stdout.strip()
    # A normal fast-forward push keeps this separate from main and from other people's edits.
    git('push','origin',commit+':refs/heads/'+BRANCH)
    git('update-ref','refs/heads/'+BRANCH,commit)
    print('Dashboard YouTube feed updated',flush=True)

if __name__=='__main__':
    initialize()
    last_versions=versions()
    pending=None
    last_check=-float('inf')
    while True:
        started=time.monotonic()
        current=versions()
        if current != last_versions:
            last_versions=current
            pending=started+5  # Wait for the finished upload/scheduling record to settle.
        if (pending is not None and started>=pending) or started-last_check>=900 or '--once' in sys.argv:
            try:
                publish(force=pending is not None)
                pending=None
                last_check=time.monotonic()
            except (RuntimeError,subprocess.SubprocessError,OSError,ValueError):
                print('YouTube feed update unavailable; retaining last good snapshot',flush=True)
                pending=time.monotonic()+30
        if '--once' in sys.argv:break
        time.sleep(3)

"""Prepare the pinned Songygen effect source for local, offline processing."""
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parent

def prepare_module():
    lock = json.loads((ROOT/'songy-source.json').read_text())
    cache = ROOT/'.cache'
    cache.mkdir(exist_ok=True)
    source = cache/'rig-source.js'
    if not source.exists():
        request = urllib.request.Request(lock['url'], headers={'User-Agent': 'DroneMill audio sample renderer'})
        with urllib.request.urlopen(request, timeout=30) as response:
            content = response.read()
        if hashlib.sha256(content).hexdigest() != lock['sha256']:
            raise RuntimeError('Songygen source changed; review it and update songy-source.json before using it.')
        source.write_bytes(content)
    content = source.read_bytes()
    if hashlib.sha256(content).hexdigest() != lock['sha256']:
        raise RuntimeError('Cached Songygen source does not match the pinned SHA-256.')
    text = content.decode('utf-8')
    start = text.index('var s=`') + len('var s=`')
    end = text.index('\n`,c=', start)
    # The inspected template contains no interpolation, only DSP code and comments.
    dsp = text[start:end]
    if '${' in dsp:
        raise RuntimeError('Unexpected interpolation in the pinned DSP template.')
    module = cache/'rig-dsp.mjs'
    module.write_text(dsp + '\nexport { RigStage, Svf };\n')
    return module

if __name__ == '__main__':
    print(prepare_module())

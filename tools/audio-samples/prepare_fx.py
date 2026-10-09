import json
import sys
from pathlib import Path
import numpy as np

import argparse
parser=argparse.ArgumentParser()
parser.add_argument('--work-dir', type=Path, required=True)
args=parser.parse_args()
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'native'))
WORK=args.work_dir.resolve()
WORK.mkdir(parents=True,exist_ok=True)
import ambient_layers as layers
import ai_hybrid_sound_conductor as conductor

SR=48000
N=SR*30
recipe=json.loads((ROOT/'lanterns-recipe.json').read_text())
preset=layers.resolve_preset(recipe['preset'],recipe['preset_overrides'])
# Keep the original Lanterns composition, but soften individual note attacks.
adsr_params={
 'bell':{'attack':.12,'decay':1.2,'sustain':.23,'hold':1.1,'release':3.6},
 'organ':{'attack':.8,'decay':1.0,'sustain':.80,'hold':1.0,'release':3.0},
 'string':{'attack':1.6,'decay':1.0,'sustain':.82,'hold':1.3,'release':3.4}
}
def adsr(t,p):
    a,d,s,h,r=(p[k] for k in ['attack','decay','sustain','hold','release'])
    env=np.zeros(len(t))
    m=t<a;env[m]=np.sin(np.clip(t[m]/a,0,1)*np.pi/2)**2
    m=(t>=a)&(t<a+d);u=(t[m]-a)/d;env[m]=s+(1-s)*np.cos(u*np.pi/2)**2
    m=(t>=a+d)&(t<a+d+h);env[m]=s
    m=(t>=a+d+h)&(t<a+d+h+r);u=(t[m]-a-d-h)/r;env[m]=s*np.cos(u*np.pi/2)**2
    return env

for name,params in adsr_params.items():
    fn=getattr(layers,'synth_'+name)
    def wrapped(*args,_fn=fn,_params=params):
        y=_fn(*args)
        return y*adsr(np.arange(len(y))/SR,_params)
    setattr(layers,'synth_'+name,wrapped)

builders=layers.layer_builders(recipe['root'],recipe['seed'],90,preset)
mix=np.zeros((N,2))
t=30+np.arange(N)/SR
for name in ['pad','choir','melody','events']:
    gain=recipe['engines'][name]['volume']
    print('Rendering native DroneMill layer:',name,flush=True)
    y=builders[name]()(t)
    mix+=y*gain

dsp=recipe['engines']['dsp']
mix+=conductor._dsp_np(dsp['frequencies'],dsp['lfos'])(t)*dsp['volume']
sub_fn,_=conductor._sub_np(recipe['root'],conductor._Seed(recipe['seed']))
mix+=np.repeat(sub_fn(t),2,axis=1)*recipe['engines']['sub']['volume']

# Quiet filtered air, using the channel's brown/pink texture approach.
rng=np.random.default_rng(31102026)
freqs=np.fft.rfftfreq(N,1/SR)
shape=(freqs>160)*np.exp(-.5*((freqs-650)/480)**2)
for ch in range(2):
    air=np.fft.irfft(np.fft.rfft(rng.standard_normal(N))*shape,N)
    air/=max(float(np.std(air)),1e-9)
    mix[:,ch]+=air*.0013*(.6+.4*np.sin(2*np.pi*t/29+ch*.7)**2)

# Moderate input level lets the Songygen compressor work gently.
mix*=.42/max(float(np.max(np.abs(mix))),1e-9)
(WORK/'input.f32').write_bytes(mix.astype('<f4').tobytes())
(WORK/'adsr.json').write_text(json.dumps(adsr_params,indent=2))
print(json.dumps({'frames':N,'sample_rate':SR,'source_excerpt':[30,60],'input_peak':float(np.max(np.abs(mix)))}))

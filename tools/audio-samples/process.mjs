import {readFileSync,writeFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
import {resolve,join} from 'node:path';
const [workArg,dspArg]=process.argv.slice(2);
if(!workArg||!dspArg)throw Error('Usage: node process.mjs WORK_DIR DSP_MODULE');
const work=resolve(workArg);
const {RigStage,Svf}=await import(pathToFileURL(resolve(dspArg)).href);

const sr=48000;
const raw=readFileSync(join(work,'input.f32'));
const input=new Float32Array(raw.buffer,raw.byteOffset,raw.byteLength/4);
const count=input.length/2;
const output=new Float32Array(input.length);
const block=128;
const stages=[
 {id:'contour-tame',type:'eq',on:true,params:{bass:-1,middle:-2.5,freq:900,treble:-5,level:0}},
 {id:'velvet',type:'comp',on:true,params:{threshold:-27,ratio:1.65,attack:35,release:240,makeup:0,blend:.30}},
 {id:'orbit',type:'phaser',on:true,params:{rate:.055,depth:.40,feedback:.12,mix:.16,stages:0}},
 {id:'drift',type:'chorus',on:true,params:{rate:.11,depth:.35,mix:.26}},
 {id:'tape',type:'delay',on:true,params:{time:650,feedback:.23,mix:.17,mode:1,pingpong:1}},
 {id:'plate',type:'reverb',on:true,params:{decay:.76,damping:.67,predelay:45,mix:.30}}
];
const rig=new RigStage(sr,block);
rig.setBlocks(stages);
const filters=[new Svf(sr),new Svf(sr)];
const L=new Float32Array(block),R=new Float32Array(block);
const oL=new Float32Array(block),oR=new Float32Array(block);
function smooth(u){u=Math.max(0,Math.min(1,u));return u*u*(3-2*u);}
function amplitudeAdsr(t){
 if(t<2.5)return smooth(t/2.5);
 if(t<4.5)return 1-.14*smooth((t-2.5)/2);
 if(t<24)return .86;
 return .86*(1-smooth((t-24)/6));
}
for(let at=0;at<count;at+=block){
 const n=Math.min(block,count-at);
 for(let i=0;i<n;i++){
  const t=(at+i)/sr;
  const lfo=.5+.5*Math.sin(2*Math.PI*t/19+.4);
  const cutoff=2300+1400*lfo;
  const amp=(.93+.07*Math.sin(2*Math.PI*t/13+.2))*amplitudeAdsr(t);
  const pan=.13*Math.sin(2*Math.PI*t/17);
  for(let ch=0;ch<2;ch++){
   filters[ch].tick(input[2*(at+i)+ch],cutoff,1.41421356);
   const y=filters[ch].lp*amp*Math.sqrt(1+(ch?pan:-pan));
   (ch?R:L)[i]=y;
  }
 }
 rig.process(L,R,oL,oR,n);
 for(let i=0;i<n;i++){
  const t=(at+i)/sr;
  // Final fade includes the effect tails, avoiding a cut-off at 30 seconds.
  const tail=t>28?1-smooth((t-28)/2):1;
  output[2*(at+i)]=oL[i]*tail;
  output[2*(at+i)+1]=oR[i]*tail;
 }
}
let peak=0,sum=0;
for(const x of output){if(!Number.isFinite(x))throw Error('Nonfinite DSP output');peak=Math.max(peak,Math.abs(x));sum+=x*x;}
if(peak<=0)throw Error('Silent DSP output');
writeFileSync(join(work,'processed.f32'),Buffer.from(output.buffer));
writeFileSync(join(work,'songy-fx-recipe.json'),JSON.stringify({
 title:'Lanterns Beyond the Grave — Songygen FX',duration_seconds:30,sample_rate:sr,
 composition_source:'Installed DroneMill procedural layers; original Lanterns seed and harmony',
 songygen_fx_source:'https://songygen.com/assets/rig-Bu9oYniG.js',
 effects_implementation:'Songygen public RigStage DSP evaluated locally in Node; no browser session or account mutation',
 eq_note:'Contour EQ used to tame harsh frequencies. A separate effect named Tame was not found in the inspected code.',
 stages,adsr_per_note:JSON.parse(readFileSync(join(work,'adsr.json'),'utf8')),
 master_adsr:{attack:2.5,decay:2,sustain:.86,release:6,note_off_seconds:24},
 additional_lfo:{filter_period_seconds:19,filter_cutoff_hz:[2300,3700],amplitude_period_seconds:13,amplitude_depth:.07,pan_period_seconds:17,pan_depth:.13},
 target_lufs:-22
},null,2));
console.log(JSON.stringify({frames:count,duration:count/sr,peak,rms:Math.sqrt(sum/output.length),effects:stages.map(s=>s.type)}));

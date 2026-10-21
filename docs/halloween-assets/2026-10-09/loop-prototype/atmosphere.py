#!/usr/bin/env python3
"""Animate low drifting mist, cloud wisps, and autumn leaves behind the keeper."""
import argparse
import json
import math
from pathlib import Path
import subprocess
import time

import cv2
import numpy as np
from PIL import Image

from render import IllustrationLoop, over, smoothstep

ROOT=Path(__file__).resolve().parent


def wisp(width,height,color,opacity,seed):
    rng=np.random.default_rng(seed)
    y,x=np.mgrid[:height,:width].astype(np.float32)
    u=x/max(1,width-1)
    center=height*(.50+.085*np.sin(2*math.pi*u+rng.uniform(0,6))+.055*np.sin(6*math.pi*u))
    vertical=np.exp(-((y-center)/(height*.21))**2)
    edges=np.sin(math.pi*u)**2
    strokes=.88+.12*np.sin(y*.32+x*.009+seed)
    alpha=(vertical*edges*strokes*opacity).astype(np.float32)
    out=np.empty((height,width,4),np.float32)
    out[:,:,:3]=np.array(color,np.float32)*alpha[:,:,None]
    out[:,:,3]=alpha
    return out


def leaf_sprite(scale,seed):
    rng=np.random.default_rng(seed)
    size=max(12,round(26*scale))
    im=np.zeros((size,size,4),np.float32)
    pts=np.array([[.13,.53],[.26,.29],[.37,.32],[.45,.14],[.60,.29],
                  [.76,.25],[.71,.44],[.89,.51],[.73,.62],[.77,.79],
                  [.57,.71],[.48,.88],[.39,.71],[.24,.74],[.28,.60]])
    pts=np.rint(pts*size).astype(np.int32)
    rust=(.45+rng.uniform(0,.12),.27+rng.uniform(0,.07),.14,1.)
    cv2.fillPoly(im,[pts],rust,lineType=cv2.LINE_AA)
    cv2.polylines(im,[pts],True,(.10,.105,.085,1.),1,cv2.LINE_AA)
    cv2.line(im,(round(size*.23),round(size*.78)),(round(size*.72),round(size*.34)),(.12,.12,.09,1.),1,cv2.LINE_AA)
    im[:,:,:3]*=im[:,:,3:4]
    return im


class AtmosphereLoop(IllustrationLoop):
    def __init__(self,width=1920):
        super().__init__(width)
        self.wisps=[]
        # Every wisp fades to zero before wrapping to its next drifting pass.
        configs=[
            (.35,.15,.70,.15,.42,.18,1,'cloud'),
            (.66,.23,.55,.13,.34,.67,1,'cloud'),
            (.30,.47,.70,.12,.25,.07,1,'mist'),
            (.61,.54,.58,.10,.23,.43,1,'mist'),
            (.76,.61,.57,.13,.27,.81,1,'mist'),
            (.35,.72,.72,.15,.32,.30,1,'mist'),
            (.67,.77,.58,.12,.27,.64,1,'mist'),
        ]
        for i,(cx,cy,ww,hh,travel,offset,cycles,kind) in enumerate(configs):
            sprite=wisp(round(self.width*ww),round(self.height*hh),
                        (.49,.48,.42) if kind=='cloud' else (.66,.64,.54),
                        .19 if kind=='cloud' else .23,seed=700+i)
            self.wisps.append((sprite,cx,cy,travel,offset,cycles,kind))
        luma=self.base.mean(axis=2)
        # Cloud coloration sits beneath dark ink strokes and tree silhouettes.
        self.sky_visibility=smoothstep(.08,.24,luma)
        yy,xx=np.mgrid[:self.height,:self.width].astype(np.float32)
        self.moon_mask=np.exp(-(((xx/self.width-.786)*16/9)**2+(yy/self.height-.104)**2)/(2*.035**2))
        rng=np.random.default_rng(101024)
        self.leaves=[]
        for i in range(8):
            self.leaves.append(dict(sprite=leaf_sprite(self.s*rng.uniform(.75,1.15),900+i),
                                    x=float(rng.uniform(.20,.93)),offset=float(rng.uniform(0,1)),
                                    cycles=int(rng.choice([2,3])),angle=float(rng.uniform(-150,150)),
                                    drift=float(rng.uniform(.035,.075))))

    def background_frame(self,p,flame):
        frame=super().background_frame(p,flame)
        phase=p/(2*math.pi)
        for sprite,cx,cy,travel,offset,cycles,kind in self.wisps:
            age=(phase*cycles+offset)%1
            fade=math.sin(math.pi*age)**2
            x=(cx+travel*(age-.5))*self.width-sprite.shape[1]/2
            y=cy*self.height-sprite.shape[0]/2+5*self.s*math.sin(2*math.pi*age)
            if kind=='cloud':
                self.cloud_over(frame,sprite*fade,x,y)
            else:
                over(frame,sprite*fade,x,y)
        # A passing cloud changes the moon's brightness gently, without a glow effect.
        frame*=1-self.moon_mask[:,:,None]*(.045*(.5+.5*math.sin(p+.9)))
        for leaf in self.leaves:
            age=(phase*leaf['cycles']+leaf['offset'])%1
            fade=math.sin(math.pi*age)**2*.84
            x=(leaf['x']+leaf['drift']*math.sin(2*math.pi*age+leaf['angle']))*self.width
            y=(.16+.72*age)*self.height
            sprite=leaf['sprite']
            h,w=sprite.shape[:2]
            angle=leaf['angle']+55*math.sin(4*math.pi*age)
            matrix=cv2.getRotationMatrix2D((w/2,h/2),angle,1)
            rotated=cv2.warpAffine(sprite,matrix,(w,h),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
            over(frame,rotated*fade,x-w/2,y-h/2)
        return frame

    def cloud_over(self,frame,sprite,left,top):
        left,top=round(left),round(top)
        h,w=sprite.shape[:2]
        x0,y0=max(0,left),max(0,top)
        x1,y1=min(self.width,left+w),min(self.height,top+h)
        if x1<=x0 or y1<=y0:
            return
        part=sprite[y0-top:y1-top,x0-left:x1-left]
        visibility=self.sky_visibility[y0:y1,x0:x1,None]
        region=frame[y0:y1,x0:x1]
        region*=1-part[:,:,3:4]*visibility
        region+=part[:,:,:3]*visibility


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--width',type=int,default=1920)
    parser.add_argument('--out',type=Path,default=ROOT/'lanterns-beyond-the-grave-1080p.mp4')
    parser.add_argument('--poster-only',action='store_true')
    args=parser.parse_args()
    if args.width<=0 or args.width%32:
        parser.error('Width must be a positive multiple of 32')
    cv2.setNumThreads(2)
    loop=AtmosphereLoop(args.width)
    first=loop.frame(0)
    Image.fromarray(first).save(ROOT/'drawing.png')
    if args.poster_only:
        return
    for point in (0,.125,7.2,18.7):
        if not np.array_equal(loop.frame(point),loop.frame(point+loop.duration)):
            raise RuntimeError(f'Loop continuity failed at {point}')
    frames=loop.duration*loop.fps
    args.out.parent.mkdir(parents=True,exist_ok=True)
    proc=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-n','-f','rawvideo','-pix_fmt','rgb24',
                           '-s',f'{loop.width}x{loop.height}','-r',str(loop.fps),'-i','pipe:0','-an',
                           '-c:v','libx264','-preset','medium','-tune','animation','-crf','16',
                           '-pix_fmt','yuv420p','-g','48','-movflags','+faststart',str(args.out)],stdin=subprocess.PIPE)
    started=time.monotonic()
    try:
        for i in range(frames):
            proc.stdin.write(loop.frame(i/loop.fps).tobytes())
            if i%96==0:
                print(f'{i/loop.fps:.0f}/{loop.duration}s; elapsed {time.monotonic()-started:.0f}s',flush=True)
        proc.stdin.close()
        if proc.wait():
            raise RuntimeError('FFmpeg encoding failed')
    except BaseException:
        proc.kill();proc.wait();raise
    delta=lambda a,b:float(np.abs(a.astype(float)-b.astype(float)).mean())
    report=dict(width=loop.width,height=loop.height,duration=loop.duration,fps=loop.fps,frames=frames,
                silent=True,repetitions_for_two_hours=300,exact_endpoint=True,
                seam_mean_pixel_difference=delta(first,loop.frame(loop.duration-1/loop.fps)),
                first_step_mean_pixel_difference=delta(first,loop.frame(1/loop.fps)),
                effects=['breathing','head tilt','blinks','lantern swing','candlelight',
                         'moving cloud wisps','layered drifting ground mist','falling autumn leaves','moon shading'])
    args.out.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':
    main()

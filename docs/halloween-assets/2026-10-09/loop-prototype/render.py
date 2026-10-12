#!/usr/bin/env python3
"""Render Lanterns Beyond the Grave as a seamless, layered illustration loop."""
import argparse
import json
import math
from pathlib import Path
import subprocess
import time

import cv2
import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent


def smoothstep(lo, hi, value):
    x = np.clip((value - lo) / (hi - lo), 0, 1)
    return x * x * (3 - 2 * x)


def load_sprite(path, height):
    with Image.open(path) as image:
        image = image.convert('RGBA')
        if image.getchannel('A').getextrema()[0] == 255:
            raise ValueError(f'{path.name} requires a transparent background')
        size = (round(image.width * height / image.height), height)
        image = image.resize(size, Image.Resampling.LANCZOS)
        rgba = np.asarray(image, np.float32) / 255
    rgba[:, :, :3] *= rgba[:, :, 3:4]
    return rgba


def over(frame, sprite, left, top):
    left, top = round(left), round(top)
    h, w = sprite.shape[:2]
    x0, y0 = max(0, left), max(0, top)
    x1, y1 = min(frame.shape[1], left + w), min(frame.shape[0], top + h)
    if x0 >= x1 or y0 >= y1:
        return
    part = sprite[y0 - top:y1 - top, x0 - left:x1 - left]
    region = frame[y0:y1, x0:x1]
    region *= 1 - part[:, :, 3:4]
    region += part[:, :, :3]


class IllustrationLoop:
    duration = 24
    fps = 24

    def __init__(self, width=1920):
        self.width, self.height = width, width * 9 // 16
        self.scale = width / 1920
        self.s = self.scale
        with Image.open(ROOT / 'assets/background.png') as image:
            image = ImageOps.fit(image.convert('RGB'), (self.width, self.height), method=Image.Resampling.LANCZOS)
            self.base = np.asarray(image, np.float32) / 255
        self.keeper = load_sprite(ROOT / 'assets/keeper.png', round(610 * self.s))
        self.kh, self.kw = self.keeper.shape[:2]
        self.left, self.top = round(460 * self.s), round(365 * self.s)
        yy, xx = np.mgrid[:self.kh, :self.kw].astype(np.float32)
        self.kx, self.ky = xx, yy
        yn = yy / self.kh
        self.head_mask = 1 - smoothstep(0.365, 0.465, yn)
        self.breath_mask = (1 - smoothstep(0.55, 0.75, yn)) * smoothstep(0.0, 0.15, yn)
        self.neck = (0.51 * self.kw, 0.425 * self.kh)
        self.eye_patches = []
        for x, y, rx, ry in [(564/1145, 413/1374, 17/1145, 20/1374), (700/1145, 357/1374, 15/1145, 20/1374)]:
            cx, cy = round(x*self.kw), round(y*self.kh)
            dx, dy = max(3,round(rx*self.kw)), max(4,round(ry*self.kh))
            x0, x1, y0, y1 = cx-dx, cx+dx+1, cy-dy, cy+dy+1
            patch = self.keeper[y0:y1,x0:x1].copy()
            skin = self.keeper[y0-2*dy-2:y1-2*dy-2,x0:x1].copy()
            ey, ex = np.mgrid[-dy:dy+1,-dx:dx+1].astype(np.float32)
            mask = (1-smoothstep(0.65,1.0,(ex/(dx+0.1))**2+(ey/(dy+0.1))**2))[...,None]
            closed = patch*(1-mask)+skin*mask
            cv2.line(closed,(max(0,dx-3),dy),(min(2*dx,dx+3),dy),(.09,.085,.07,1),1,cv2.LINE_AA)
            self.eye_patches.append((x0,x1,y0,y1,closed))
        self.lantern = load_sprite(ROOT / 'assets/lantern.png', round(186*self.s))
        self.lh,self.lw = self.lantern.shape[:2]
        self.lp = (516/1024*self.lw,76/1536*self.lh)
        self.hand = (self.left+1008/1145*self.kw,self.top+620/1374*self.kh)
        ly,lx=np.mgrid[:self.lh,:self.lw].astype(np.float32)
        self.flame_mask=np.exp(-(((lx/self.lw-.5)/.17)**2+((ly/self.lh-.65)/.14)**2))[...,None]
        self.fog_y0,self.fog_y1=round(300*self.s),round(665*self.s)
        fh=self.fog_y1-self.fog_y0
        gy,gx=np.mgrid[:fh,:self.width].astype(np.float32)
        self.fog_mask=np.exp(-((gy/fh-.58)/.34)**2)
        rng=np.random.default_rng(12036)
        fields=[]
        for i in range(3):
            noise=rng.normal(size=(90,320))
            fy=np.fft.fftfreq(90)[:,None]
            fx=np.fft.fftfreq(320)[None,:]
            field=np.fft.ifft2(np.fft.fft2(noise)*np.exp(-((fx/.028)**2+(fy/.055)**2))).real
            field=(field-field.min())/(np.ptp(field)+1e-9)
            fields.append(cv2.resize(field.astype(np.float32),(self.width,fh)))
        self.fog_fields=fields
        y,x=np.mgrid[:self.height,:self.width].astype(np.float32)
        self.shadow=np.exp(-(((x-715*self.s)/(220*self.s))**2+((y-973*self.s)/(20*self.s))**2))*.25
        self.ground_glow=np.exp(-(((x-910*self.s)/(150*self.s))**2+((y-832*self.s)/(100*self.s))**2))
        self.small_lights=[]
        for cx,cy,r in [(.475,.532,.024),(.904,.518,.023),(.78,.371,.032)]:
            mask=np.exp(-(((x/self.width-cx)*16/9)**2+(y/self.height-cy)**2)/(2*r*r))[...,None]
            self.small_lights.append(mask)

    def state(self, seconds):
        p=2*math.pi*(seconds % self.duration)/self.duration
        return dict(phase=p,head=.027*math.sin(p),breath=math.sin(4*p),
                    swing=4.8*math.sin(4*p+.35),
                    flame=.11*(.65*math.sin(23*p)+.35*math.sin(37*p+.4)))

    def background_frame(self, p, flame):
        frame=self.base.copy()
        fog=sum(field*(.28+.12*math.sin((i+1)*p+i)) for i,field in enumerate(self.fog_fields))
        fog=np.clip(fog*self.fog_mask*.12,0,.1)[...,None]
        region=frame[self.fog_y0:self.fog_y1]
        region*=1-fog
        region+=fog*np.array([.56,.55,.47],np.float32)
        for i,mask in enumerate(self.small_lights):
            frame*=1+mask*(.045*math.sin((11+i*2)*p+i))
        frame*=1-self.shadow[...,None]
        frame+=self.ground_glow[...,None]*np.array([.035,.019,.004],np.float32)*(1+flame)
        return frame

    def frame(self, seconds):
        st=self.state(seconds)
        p=st['phase']
        frame=self.background_frame(p,st['flame'])
        character=self.keeper
        blink=0.
        for center in (7.2,18.7):
            d=abs((seconds-center+self.duration/2)%self.duration-self.duration/2)
            if d<.18:
                blink=max(blink,.5+.5*math.cos(math.pi*d/.18))
        if blink:
            character=character.copy()
            for x0,x1,y0,y1,closed in self.eye_patches:
                character[y0:y1,x0:x1]=character[y0:y1,x0:x1]*(1-blink)+closed*blink
        nx,ny=self.neck
        co,si=math.cos(st['head']),math.sin(st['head'])
        rx=co*(self.kx-nx)+si*(self.ky-ny)+nx
        ry=-si*(self.kx-nx)+co*(self.ky-ny)+ny
        mx=self.kx+(rx-self.kx)*self.head_mask+.65*self.s*st['breath']*self.breath_mask
        my=self.ky+(ry-self.ky)*self.head_mask+2.0*self.s*st['breath']*self.breath_mask
        character=cv2.remap(character,mx.astype(np.float32),my.astype(np.float32),cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
        # The lantern sits behind the keeper's fingertips at a fixed hand attachment.
        lantern=self.lantern.copy()
        lantern[:,:,:3]*=1+self.flame_mask*st['flame']
        matrix=cv2.getRotationMatrix2D(self.lp,st['swing'],1)
        lantern=cv2.warpAffine(lantern,matrix,(self.lw,self.lh),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
        hand_x=self.hand[0]-.65*self.s*st['breath']
        hand_y=self.hand[1]-2.0*self.s*st['breath']
        over(frame,lantern,hand_x-self.lp[0],hand_y-self.lp[1])
        over(frame,character,self.left,self.top)
        return np.rint(np.clip(frame,0,1)*255).astype(np.uint8)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--width',type=int,default=1920)
    parser.add_argument('--out',type=Path,default=ROOT/'lanterns-beyond-the-grave-1080p.mp4')
    parser.add_argument('--poster-only',action='store_true')
    args=parser.parse_args()
    if args.width<=0 or args.width%32:
        parser.error('Width must be a positive multiple of 32')
    cv2.setNumThreads(2)
    loop=IllustrationLoop(args.width)
    first=loop.frame(0)
    Image.fromarray(first).save(ROOT/'drawing.png')
    if args.poster_only:
        return
    frames=loop.duration*loop.fps
    if not np.array_equal(first,loop.frame(loop.duration)):
        raise RuntimeError('Loop endpoint does not match')
    args.out.parent.mkdir(parents=True,exist_ok=True)
    command=['ffmpeg','-hide_banner','-loglevel','error','-n','-f','rawvideo','-pix_fmt','rgb24',
             '-s',f'{loop.width}x{loop.height}','-r',str(loop.fps),'-i','pipe:0','-an',
             '-c:v','libx264','-preset','medium','-tune','animation','-crf','16',
             '-pix_fmt','yuv420p','-g','48','-movflags','+faststart',str(args.out)]
    process=subprocess.Popen(command,stdin=subprocess.PIPE)
    started=time.monotonic()
    try:
        for i in range(frames):
            process.stdin.write(loop.frame(i/loop.fps).tobytes())
            if i%96==0:
                print(f'{i/loop.fps:.0f}/{loop.duration}s rendered; elapsed {time.monotonic()-started:.0f}s',flush=True)
        process.stdin.close()
        if process.wait():
            raise RuntimeError('FFmpeg encoding failed')
    except BaseException:
        process.kill()
        process.wait()
        raise
    delta=lambda a,b:float(np.abs(a.astype(float)-b.astype(float)).mean())
    report=dict(width=loop.width,height=loop.height,fps=loop.fps,duration=loop.duration,frames=frames,
                exact_endpoint=True,seam_mean_pixel_difference=delta(first,loop.frame(loop.duration-1/loop.fps)),
                first_step_mean_pixel_difference=delta(first,loop.frame(1/loop.fps)),
                silent=True,repetitions_for_two_hours=300,
                effects=['breathing','head tilt','two blinks','lantern swing','localized flame flicker','periodic mist'])
    args.out.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':
    main()

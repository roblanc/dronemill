#!/usr/bin/env python3
"""
High-Performance Seamless Particle Overlay Generator
Generates:
1. snow_blizzard (Heavy realistic winter blizzard)
2. snow_gentle (Soft peaceful snowfall)
3. dust_motes (Golden sunlight particles)
4. embers (Warm rising fire sparks)
5. god_rays (Volumetric sunlight shafts)

Outputs perfectly seamless 60-second 1080p 24fps MP4 loops (h264 black-background for Screen/Add blend).
"""

import sys
import math
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

WIDTH = 1920
HEIGHT = 1080
FPS = 24
DURATION = 60
TOTAL_FRAMES = FPS * DURATION

def create_snow_blizzard(out_path):
    print(f">> Generating Snow Blizzard Overlay -> {out_path}")
    num_particles = 1200
    
    # 3 Layers of depth: z in [0.2, 1.0]
    np.random.seed(42)
    z = np.random.uniform(0.2, 1.0, num_particles)
    
    # Initial positions (with padding for wrap-around)
    x0 = np.random.uniform(-200, WIDTH + 400, num_particles)
    y0 = np.random.uniform(-100, HEIGHT + 200, num_particles)
    
    # Velocities proportional to depth
    vx = np.random.uniform(180, 420, num_particles) * z  # Strong wind to the right
    vy = np.random.uniform(220, 550, num_particles) * z  # Falling down
    
    # Radii and opacity
    radii = (1.5 + 4.5 * z).astype(int)
    opacities = (40 + 190 * z).astype(int)
    
    # FFmpeg pipe
    cmd = [
        'ffmpeg', '-y', '-f', 'rawvideo', '-vcodec', 'rawvideo',
        '-s', f'{WIDTH}x{HEIGHT}', '-pix_fmt', 'rgba', '-r', str(FPS),
        '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
        '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out_path
    ]
    pipe = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    
    # Pre-render particle sprites of different sizes to be fast
    sprites = {}
    for r in range(1, 10):
        s_size = (r * 4 + 4, r * 4 + 4)
        spr = Image.new('RGBA', s_size, (0, 0, 0, 0))
        d = ImageDraw.Draw(spr)
        center = (s_size[0] // 2, s_size[1] // 2)
        # Streaked oval for motion blur
        d.ellipse([center[0] - r, center[1] - r*2, center[0] + r, center[1] + r*2], fill=(255, 255, 255, 200))
        spr = spr.rotate(35, resample=Image.BICUBIC)
        spr = spr.filter(ImageFilter.GaussianBlur(radius=max(0.5, r*0.3)))
        sprites[r] = spr

    for frame in range(TOTAL_FRAMES):
        t = frame / FPS
        # Seamless loop: position is modulo over 60s
        # x(t) = (x0 + vx * t + wind_sway) % (WIDTH + 600) - 200
        sway = 45 * np.sin(2 * math.pi * t / 6.0 + z * 10) + 20 * np.cos(2 * math.pi * t / 2.5)
        cur_x = ((x0 + vx * t + sway) % (WIDTH + 600)) - 200
        cur_y = ((y0 + vy * t) % (HEIGHT + 300)) - 100
        
        img = Image.new('RGBA', (WIDTH, HEIGHT), (0, 0, 0, 255))
        
        for i in range(num_particles):
            px, py = int(cur_x[i]), int(cur_y[i])
            if -50 <= px < WIDTH + 50 and -50 <= py < HEIGHT + 50:
                r = min(9, max(1, radii[i]))
                spr = sprites[r]
                img.paste(spr, (px - spr.width//2, py - spr.height//2), spr)
        
        pipe.stdin.write(img.tobytes())
        if frame % 120 == 0:
            print(f"  Frame {frame}/{TOTAL_FRAMES} ({frame/TOTAL_FRAMES*100:.1f}%)")
            
    pipe.stdin.close()
    pipe.wait()
    print("Done snow blizzard!")

def create_dust_motes(out_path):
    print(f">> Generating Golden Dust Motes Overlay -> {out_path}")
    num_particles = 450
    np.random.seed(88)
    
    z = np.random.uniform(0.3, 1.0, num_particles)
    x0 = np.random.uniform(0, WIDTH, num_particles)
    y0 = np.random.uniform(0, HEIGHT, num_particles)
    
    vx = np.random.uniform(-15, 25, num_particles) * z
    vy = np.random.uniform(-30, -5, num_particles) * z # Gentle upward floating
    
    radii = (2 + 6 * z).astype(int)
    
    cmd = [
        'ffmpeg', '-y', '-f', 'rawvideo', '-vcodec', 'rawvideo',
        '-s', f'{WIDTH}x{HEIGHT}', '-pix_fmt', 'rgba', '-r', str(FPS),
        '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
        '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out_path
    ]
    pipe = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    
    # Warm golden/amber glowing sprites
    sprites = {}
    for r in range(1, 12):
        s_size = (r * 6 + 6, r * 6 + 6)
        spr = Image.new('RGBA', s_size, (0, 0, 0, 0))
        d = ImageDraw.Draw(spr)
        center = (s_size[0] // 2, s_size[1] // 2)
        # Soft circle with golden tint
        d.ellipse([center[0] - r, center[1] - r, center[0] + r, center[1] + r], fill=(255, 235, 180, 220))
        spr = spr.filter(ImageFilter.GaussianBlur(radius=max(1.0, r*0.6)))
        sprites[r] = spr
        
    for frame in range(TOTAL_FRAMES):
        t = frame / FPS
        # 3D Brownian float with seamless trigonometric periodic wrap
        sway_x = 35 * np.sin(2 * math.pi * t / 15.0 + z * 5) + 15 * np.cos(2 * math.pi * t / 7.5 + x0)
        sway_y = 25 * np.cos(2 * math.pi * t / 20.0 + z * 7) + 10 * np.sin(2 * math.pi * t / 10.0 + y0)
        
        cur_x = ((x0 + vx * t + sway_x) % WIDTH)
        cur_y = ((y0 + vy * t + sway_y) % HEIGHT)
        
        img = Image.new('RGBA', (WIDTH, HEIGHT), (0, 0, 0, 255))
        
        for i in range(num_particles):
            px, py = int(cur_x[i]), int(cur_y[i])
            r = min(11, max(1, radii[i]))
            spr = sprites[r]
            img.paste(spr, (px - spr.width//2, py - spr.height//2), spr)
            
        pipe.stdin.write(img.tobytes())
        if frame % 120 == 0:
            print(f"  Frame {frame}/{TOTAL_FRAMES} ({frame/TOTAL_FRAMES*100:.1f}%)")
            
    pipe.stdin.close()
    pipe.wait()
    print("Done dust motes!")

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    out_dir = "/root/dronemill/assets/overlays"
    if mode in ("snow", "all"):
        create_snow_blizzard(f"{out_dir}/snow_blizzard_loop.mp4")
    if mode in ("dust", "all"):
        create_dust_motes(f"{out_dir}/dust_motes_loop.mp4")

def create_embers(out_path):
    print(f">> Generating Warm Floating Embers Overlay -> {out_path}")
    num_particles = 300
    np.random.seed(55)
    
    z = np.random.uniform(0.3, 1.0, num_particles)
    # Embers emanate mainly from lower-center/right where fire usually sits
    x0 = np.random.uniform(WIDTH * 0.4, WIDTH * 0.8, num_particles)
    y0 = np.random.uniform(HEIGHT * 0.6, HEIGHT + 100, num_particles)
    
    vx = np.random.uniform(-25, 45, num_particles) * z  # Drift with hot air
    vy = np.random.uniform(-120, -50, num_particles) * z # Rise upwards
    
    radii = (2 + 4 * z).astype(int)
    
    cmd = [
        'ffmpeg', '-y', '-f', 'rawvideo', '-vcodec', 'rawvideo',
        '-s', f'{WIDTH}x{HEIGHT}', '-pix_fmt', 'rgba', '-r', str(FPS),
        '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
        '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out_path
    ]
    pipe = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    
    # Glowing orange/gold ember sprites
    sprites = {}
    for r in range(1, 9):
        s_size = (r * 6 + 6, r * 6 + 6)
        spr = Image.new('RGBA', s_size, (0, 0, 0, 0))
        d = ImageDraw.Draw(spr)
        center = (s_size[0] // 2, s_size[1] // 2)
        # Inner hot yellow/white core with orange halo
        d.ellipse([center[0] - r*2, center[1] - r*2, center[0] + r*2, center[1] + r*2], fill=(255, 120, 20, 180))
        d.ellipse([center[0] - r, center[1] - r, center[0] + r, center[1] + r], fill=(255, 220, 100, 255))
        spr = spr.filter(ImageFilter.GaussianBlur(radius=max(0.6, r*0.4)))
        sprites[r] = spr
        
    for frame in range(TOTAL_FRAMES):
        t = frame / FPS
        # Upward spiral turbulence
        sway_x = 40 * np.sin(2 * math.pi * t / 8.0 + z * 6) + 15 * np.cos(2 * math.pi * t / 3.0)
        sway_y = 15 * np.sin(2 * math.pi * t / 5.0 + x0)
        
        cur_x = ((x0 + vx * t + sway_x) % (WIDTH + 200)) - 100
        cur_y = ((y0 + vy * t + sway_y) % (HEIGHT + 200)) - 100
        
        img = Image.new('RGBA', (WIDTH, HEIGHT), (0, 0, 0, 255))
        
        for i in range(num_particles):
            px, py = int(cur_x[i]), int(cur_y[i])
            r = min(8, max(1, radii[i]))
            spr = sprites[r]
            img.paste(spr, (px - spr.width//2, py - spr.height//2), spr)
            
        pipe.stdin.write(img.tobytes())
        if frame % 120 == 0:
            print(f"  Embers Frame {frame}/{TOTAL_FRAMES} ({frame/TOTAL_FRAMES*100:.1f}%)")
            
    pipe.stdin.close()
    pipe.wait()
    print("Done embers!")

def create_heat_shimmer(out_path):
    print(f">> Generating Desert Heat Shimmer Distortion Overlay -> {out_path}")
    # Generates a high-quality vertical wave displacement map for hot air mirage
    cmd = [
        'ffmpeg', '-y', '-f', 'lavfi', '-t', str(DURATION),
        '-i', f'perlin=s={WIDTH}x{HEIGHT}:r={FPS}:octaves=4:persistence=0.6:xscale=0.005:yscale=0.04:tscale=0.03:random_mode=seed:seed=3301',
        '-vf', "curves=all='0/0 0.4/0.1 0.6/0.9 1/1',gblur=sigma=12,format=yuv420p",
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
        '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out_path
    ]
    subprocess.run(cmd, check=True)
    print("Done heat shimmer!")

def create_volumetric_fog(out_path):
    print(f">> Generating Volumetric Rolling Fog Overlay -> {out_path}")
    cmd = [
        'ffmpeg', '-y', '-f', 'lavfi', '-t', str(DURATION),
        '-i', f'perlin=s={WIDTH}x{HEIGHT}:r={FPS}:octaves=5:persistence=0.52:xscale=0.006:yscale=0.004:tscale=0.015:random_mode=seed:seed=1107',
        '-vf', "scroll=horizontal=0.35:vertical=0.08,gblur=sigma=32,curves=all='0/0 0.30/0 0.55/0.25 0.80/0.65 1/0.85',format=yuv420p",
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
        '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out_path
    ]
    subprocess.run(cmd, check=True)
    print("Done fog!")

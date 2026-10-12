#!/usr/bin/env python3
"""Repeat the silent illustration loop beneath a separately rendered full soundtrack."""
import argparse
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parent


def inspect(path):
    return json.loads(subprocess.check_output([
        'ffprobe','-v','error','-show_entries','format=duration:stream=codec_type',
        '-of','json',str(path)],text=True))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('audio',type=Path,help='Full two-hour soundtrack WAV/FLAC/MP3')
    parser.add_argument('--loop',type=Path,default=ROOT/'lanterns-beyond-the-grave-1080p.mp4')
    parser.add_argument('--out',type=Path,default=ROOT/'lanterns-beyond-the-grave-two-hours.mp4')
    parser.add_argument('--duration',type=float,default=7200,help='Seconds; default 7200 (two hours)')
    args=parser.parse_args()
    if args.duration<=0:
        parser.error('Duration must be positive')
    for path in [args.audio,args.loop]:
        if not path.is_file():
            parser.error(f'File does not exist: {path}')
    if args.out.exists():
        parser.error(f'Output already exists: {args.out}')
    audio=inspect(args.audio)
    video=inspect(args.loop)
    if not any(s['codec_type']=='audio' for s in audio['streams']):
        parser.error('The soundtrack has no audio stream')
    if not any(s['codec_type']=='video' for s in video['streams']):
        parser.error('The loop has no video stream')
    if float(audio['format']['duration'])+0.05<args.duration:
        parser.error('Soundtrack is shorter than the requested video; render the full audio first')
    args.out.parent.mkdir(parents=True,exist_ok=True)
    command=['ffmpeg','-hide_banner','-n','-stream_loop','-1','-i',str(args.loop),
             '-i',str(args.audio),'-map','0:v:0','-map','1:a:0','-c:v','copy',
             '-c:a','aac','-b:a','256k','-t',str(args.duration),'-shortest',
             '-movflags','+faststart',str(args.out)]
    subprocess.run(command,check=True)
    result=inspect(args.out)
    if abs(float(result['format']['duration'])-args.duration)>0.15:
        raise RuntimeError('Finished video duration differs from the requested duration')
    print(f'Saved {args.out}')


if __name__=='__main__':
    main()

"""Render the two Lanterns previews without changing production DroneMill scripts."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'native'))

def run(command):
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-8000:] or result.stdout[-8000:])
    return result

def loudness(input_args, filters='anull'):
    result = run(['ffmpeg', '-hide_banner', '-nostdin', *input_args, '-af',
                  filters+',loudnorm=I=-22:TP=-3:LRA=10:print_format=json', '-f', 'null', '-'])
    match = re.search(r'\{[^{}]*"input_i"[^{}]*\}', result.stderr, re.S)
    if not match:
        raise RuntimeError('ffmpeg returned no loudness measurements.')
    return json.loads(match.group())

def master(input_args, filters, destination, sample_format):
    stats = loudness(input_args, filters)
    gain = min(-22-float(stats['input_i']), -3-float(stats['input_tp']))
    run(['ffmpeg', '-hide_banner', '-nostdin', '-y', *input_args, '-af',
         filters+f',volume={gain:.4f}dB', '-t', '30', '-ar', '48000', '-c:a', sample_format,
         '-metadata', 'title=Lanterns Beyond the Grave', str(destination)])
    run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', '-y', '-i', str(destination),
         '-c:a', 'libmp3lame', '-b:a', '256k', str(destination.with_suffix('.mp3'))])
    measured = loudness(['-i', str(destination)])
    probe = json.loads(run(['ffprobe', '-v', 'error', '-show_entries',
        'format=duration:stream=sample_rate,channels', '-of', 'json', str(destination)]).stdout)
    report = {'duration_seconds':float(probe['format']['duration']),
              'integrated_lufs':float(measured['input_i']), 'true_peak_dbtp':float(measured['input_tp']),
              'sample_rate':int(probe['streams'][0]['sample_rate']), 'channels':probe['streams'][0]['channels']}
    if report['duration_seconds'] != 30 or report['channels'] != 2 or report['sample_rate'] != 48000:
        raise RuntimeError(f'Unexpected audio format: {report}')
    if abs(report['integrated_lufs']+22) > .5 or report['true_peak_dbtp'] > -3:
        raise RuntimeError(f'Master outside preview limits: {report}')
    destination.with_suffix('.validation.json').write_text(json.dumps(report, indent=2)+'\n')
    print(f'{destination.name}: {report}', flush=True)

def baseline(work, output):
    import ai_hybrid_sound_conductor as conductor
    conductor.TMP_DIR = str(work)
    conductor.TARGET_LUFS = -22.0
    conductor.FADE_IN_SEC = 3
    conductor.FADE_OUT_SEC = 5
    recipe = json.loads((ROOT/'lanterns-recipe.json').read_text())
    source = work/'full-90s.wav'
    conductor.build_hybrid_soundscape(recipe, str(source))
    master(['-ss', '30', '-i', str(source), '-t', '30'],
           'afade=t=in:st=0:d=2,afade=t=out:st=26:d=4',
           output/'lanterns-beyond-the-grave-dronemill.wav', 'pcm_s16le')

def songy_fx(work, output, module):
    run([sys.executable, str(ROOT/'prepare_fx.py'), '--work-dir', str(work)])
    result = run(['node', str(ROOT/'process.mjs'), str(work), str(module)])
    print(result.stdout.strip(), flush=True)
    master(['-f', 'f32le', '-ar', '48000', '-ac', '2', '-i', str(work/'processed.f32')],
           'anull', output/'lanterns-beyond-the-grave-songy-fx.wav', 'pcm_s24le')
    shutil.copy2(work/'songy-fx-recipe.json', output/'lanterns-beyond-the-grave-songy-fx-recipe.json')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant', choices=['baseline', 'songy-fx', 'all'], default='all')
    parser.add_argument('--output-dir', type=Path, default=ROOT/'rendered')
    parser.add_argument('--songy-dsp', type=Path, help='Use a previously prepared DSP module instead of fetching it.')
    args = parser.parse_args()
    for command in ['ffmpeg', 'ffprobe'] + (['node'] if args.variant != 'baseline' else []):
        if not shutil.which(command):
            parser.error(f'Required executable is missing: {command}')
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    work_root = ROOT/'work'
    work_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='lanterns-', dir=work_root) as folder:
        work = Path(folder)
        if args.variant in ['baseline', 'all']:
            baseline(work, output)
        if args.variant in ['songy-fx', 'all']:
            if args.songy_dsp:
                module = args.songy_dsp.resolve()
            else:
                from fetch_songy_dsp import prepare_module
                module = prepare_module()
            songy_fx(work, output, module)

if __name__ == '__main__':
    main()

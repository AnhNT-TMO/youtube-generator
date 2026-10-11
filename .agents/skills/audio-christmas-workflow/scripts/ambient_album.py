import argparse
import json
import subprocess
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('order')
ap.add_argument('root')
ap.add_argument('out')
ap.add_argument('--xf', type=float, default=2.0, help='crossfade seconds (ignored with --target)')
ap.add_argument('--target', type=float, help='exact master length in seconds; crossfade is solved to match')
ap.add_argument('--min-xf', type=float, default=1.0)
ap.add_argument('--max-xf', type=float, default=4.0)
ap.add_argument('--intro-fade', type=float, default=12.0, help='album fade-in seconds, hsin curve (0 = off)')
ap.add_argument('--wav', action='store_true', help='also write 48 kHz 24-bit WAV')
a = ap.parse_args()
ROOT, OUT = Path(a.root), a.out
rows = json.load(open(a.order))
files = []
for r in rows:
    f = ROOT / r['vibe'] / r['slug'] / f"{r['slug']}.mp3"
    if not f.exists():
        raise SystemExit(f'missing {f}')
    files.append(f)


def duration(f):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(f)],
                                capture_output=True, text=True, check=True).stdout)


durs = [duration(f) for f in files]
xf = a.xf
if a.target:
    xf = round((sum(durs) - a.target) / (len(files) - 1), 3)
    if not a.min_xf <= xf <= a.max_xf:
        raise SystemExit(f'crossfade {xf} s outside [{a.min_xf}, {a.max_xf}] for target {a.target} s '
                         f'(sum {sum(durs):.1f} s, {len(files)} tracks): add or remove tracks')
cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y']
for f in files:
    cmd += ['-i', str(f)]
parts = [f'[{i}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo[a{i}]' for i in range(len(files))]
prev = 'a0'
for i in range(1, len(files)):
    parts.append(f'[{prev}][a{i}]acrossfade=d={xf}:c1=qsin:c2=qsin[x{i}]')
    prev = f'x{i}'
if a.intro_fade > 0:
    parts.append(f'[{prev}]afade=t=in:st=0:d={a.intro_fade:g}:curve=hsin[faded]')
    prev = 'faded'
if a.target:
    n = int(round(a.target * 48000))
    parts.append(f'[{prev}]apad=whole_len={n},atrim=end_sample={n}[final]')
    prev = 'final'
wav = OUT + '.wav'
cmd += ['-filter_complex', ';'.join(parts), '-map', f'[{prev}]', '-c:a', 'pcm_s24le', wav]
subprocess.run(cmd, check=True)
subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', wav, '-c:a', 'libmp3lame', '-b:a', '320k',
                OUT + '.mp3'], check=True)
t = 0.0
for r, d in zip(rows, durs):
    r['start_s'] = round(t, 2)
    r['duration_s'] = round(d, 2)
    t += d - xf
master = duration(wav)
meas = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', wav, '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                      capture_output=True, text=True).stderr
summary = meas[meas.rfind('Summary:'):]
if not a.wav:
    Path(wav).unlink()
json.dump({'crossfade_s': xf, 'intro_fade_s': a.intro_fade, 'target_seconds': a.target, 'master_seconds': round(master, 3), 'tracks': rows,
           'ebur128': summary}, open(OUT + '.json', 'w'), indent=1, ensure_ascii=False)
print('DONE', len(files), 'tracks', 'xf', xf, 'master', round(master, 3), 's')
print(summary)

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = os.path.expanduser('~/music-tools/venv/bin/python')


def melody_rate(plan):
    mel = [e for e in plan['note_plan']['events'] if e['part'] == 'melody']
    span = max(e['beat'] + e['duration'] for e in mel) - min(e['beat'] for e in mel)
    return len(mel) / (span * 60 / plan['meta']['tempo'])


def loudness(path):
    out = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', path, '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    return float(re.findall(r'^\s+I:\s+(-?[\d.]+)', out, re.M)[-1]), float(re.findall(r'^\s+Peak:\s+(-?[\d.]+)', out, re.M)[-1])


def render_finish(plan, vibe, out, cfg):
    json.dump(plan, open(f'{out}.plan.json', 'w'))
    env = {k: v for k, v in os.environ.items() if k != 'DISPLAY'}
    res = subprocess.run([PY, f'{HERE}/ambient_render.py', f'{out}.plan.json', vibe, out], capture_output=True, text=True, env=env)
    stats = [l for l in res.stdout.splitlines() if l.startswith('{')]
    if res.returncode or not stats:
        print(f'FAIL {vibe}/{os.path.basename(out)}:', res.stderr[-800:])
        return None
    i, tp = loudness(f'{out}_mix.wav')
    if (cfg['lufs'] - i) - (cfg['true_peak'] - tp) > 0.3:
        ceiling = 10 ** ((cfg['true_peak'] - 0.6) / 20)
        subprocess.run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', f'{out}_mix.wav', '-af',
                        f'volume={cfg["lufs"] - i:.2f}dB,aresample=192000,'
                        f'alimiter=limit={ceiling:.4f}:attack=1:release=80:level=disabled,aresample=48000',
                        '-c:a', 'pcm_f32le', f'{out}_lim.wav'], check=True)
        os.replace(f'{out}_lim.wav', f'{out}_mix.wav')
        i, tp = loudness(f'{out}_mix.wav')
    gain = round(min(cfg['lufs'] - i, cfg['true_peak'] - tp), 2)
    subprocess.run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', f'{out}_mix.wav', '-af', f'volume={gain}dB',
                    '-c:a', 'libmp3lame', '-b:a', '320k', f'{out}.mp3'], check=True)
    os.remove(f'{out}_mix.wav')
    i, tp = loudness(f'{out}.mp3')
    info = json.loads(stats[-1])
    json.dump(info, open(f'{out}.json', 'w'), indent=1)
    return dict(info, lufs=i, true_peak=tp)


def fit_tempo(plan, spec, cfg):
    target = spec['notes_per_s']
    rate = melody_rate(plan)
    new_rate = min(max(rate, target * (1 - cfg['band'])), target * (1 + cfg['band']))
    ratio = new_rate / rate
    tempo = round(plan['meta']['tempo'] * ratio, 1)
    problems = []
    if abs(ratio - 1) > cfg['max_change'] + 1e-9:
        problems.append(f'tempo change {ratio:.2f}x beyond ±{cfg["max_change"]:.0%}')
    if 'meters' in spec and plan['meta']['meter'] not in spec['meters']:
        problems.append(f'meter {plan["meta"]["meter"]} not in {spec["meters"]}')
    if 'pulse_bpm' in spec and not spec['pulse_bpm'][0] <= tempo <= spec['pulse_bpm'][1]:
        problems.append(f'tempo {tempo} outside {spec["pulse_bpm"]}')
    return tempo, ratio, new_rate, problems


def main(CFG, ONLY):
    for vibe, spec in CFG['vibes'].items():
        if ONLY and vibe not in ONLY:
            continue
        root = os.path.join(CFG['out'], vibe)
        os.makedirs(root, exist_ok=True)
        index = f'{root}/fit-index.json'
        rows = json.load(open(index)) if os.path.exists(index) else {}
        for slug in spec['songs']:
            plan = json.load(open(CFG['plans'].format(slug=slug)))
            tempo, ratio, new_rate, problems = fit_tempo(plan, spec, CFG)
            if problems:
                print(f'SKIP {vibe}/{slug}: {"; ".join(problems)}')
                continue
            plan['meta']['tempo'] = tempo
            os.makedirs(f'{root}/{slug}', exist_ok=True)
            out = f'{root}/{slug}/{slug}-fit'
            info = render_finish(plan, vibe, out, CFG)
            if info is None:
                continue
            rows[slug] = {'meter': plan['meta']['meter'], 'tempo': tempo, 'tempo_change': round(ratio, 3),
                          'notes_per_s': round(new_rate, 3), 'seconds': info['seconds'], 'lufs': info['lufs'],
                          'true_peak': info['true_peak'], 'pass_rms': info['pass_rms_after'], 'corr_lr': info['corr_lr']}
            print(f'{vibe}/{slug} tempo {tempo} ({ratio:.2f}x) {new_rate:.2f} n/s {info["seconds"]} s {info["lufs"]} LUFS {info["true_peak"]} dBTP')
            json.dump(rows, open(index, 'w'), indent=1)


if __name__ == '__main__':
    main(json.load(open(sys.argv[1])), sys.argv[2:])

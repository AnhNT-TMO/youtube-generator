#!/usr/bin/env python3
import argparse
import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
SOURCE_ROOT = Path('research/christmas-carols/mureka')
OUT_ROOT = Path('audio/christmas/mureka')
REMOTE_REPO = 'youtube-qc'
REMOTE_PY = f'~/{REMOTE_REPO}/.claude/skills/audio-song-naming/.venv/bin/python'
GUARD = REPO / '.claude/skills/pm-production/scripts/server_guard/guard.sh'
WINDOW_S = 0.5
ACTIVE_DB = -12.0
PRESENT_PCT = 10.0
PERCUSSION_MAX_PCT = 1.0
GUITAR_WARN_PCT = 1.0
SSH_KEY = os.path.expanduser('~/.ssh/id_rsa')


def remote_host():
    env = REPO / '.claude/skills/video-generator/remote.env'
    for line in env.read_text().splitlines() if env.exists() else []:
        if line.startswith('VG_REMOTE='):
            return line.split('=', 1)[1].strip().strip('"\'')
    sys.exit(f'no VG_REMOTE in {env}')


def take_entry(slug, name):
    ledger = REPO / OUT_ROOT / 'manifest.json'
    for g in json.loads(ledger.read_text()).get('generations', []) if ledger.exists() else []:
        for t in g.get('takes', []) if g['slug'] == slug else []:
            if t.get('file') == name:
                return g, t
    return None, None


def take_style(slug, name):
    g, _ = take_entry(slug, name)
    return g['style'] if g else None


def pass_bounds(out_dir, name):
    report = out_dir / 'fidelity.json'
    takes = json.loads(report.read_text())['takes'] if report.exists() else []
    bounds = next((t.get('pass_bounds_s') for t in takes if t['file'] == name), None)
    if not bounds:
        sys.exit(f'{name}: fidelity.json chưa có pass_bounds_s, chạy mureka_fidelity.py cho bản này trước')
    return bounds


def measure(stems, bounds):
    import numpy as np
    import soundfile as sf
    audio = {name: sf.read(stems / f'{name}.wav') for name in ('vocals', 'drums', 'bass', 'other')}
    sr = audio['vocals'][1]
    v, d = audio['vocals'][0].mean(1), audio['drums'][0].mean(1)
    rest = sum(a[0].mean(1) for name, a in audio.items() if name != 'vocals')
    mix = v + rest
    w = int(sr * WINDOW_S)

    def window_db(x, ref):
        k = len(x) // w
        rx = np.sqrt((x[:k * w].reshape(k, w) ** 2).mean(1))
        rr = np.sqrt((ref[:k * w].reshape(k, w) ** 2).mean(1)) + 1e-9
        return 20 * np.log10(rx / rr + 1e-9)

    rows = []
    for i, (start, end) in enumerate(bounds):
        a, b = int(start * sr), int(end * sr)
        voice_db = window_db(v[a:b], rest[a:b])
        drum_db = window_db(d[a:b], mix[a:b])
        rows.append({'pass': i + 1, 'start_s': start, 'end_s': end,
                     'voice_active_pct': round(100 * float((voice_db > ACTIVE_DB).mean()), 1),
                     'voice_vs_rest_median_db': round(float(np.median(voice_db)), 1),
                     'percussion_active_pct': round(100 * float((drum_db > ACTIVE_DB).mean()), 1),
                     'percussion_energy_pct': round(100 * float((d[a:b] ** 2).sum() / ((mix[a:b] ** 2).sum() + 1e-12)), 2)})
    whole = round(100 * float((d ** 2).sum() / ((mix ** 2).sum() + 1e-12)), 2)
    return rows, whole


def guitar_share(stems):
    import soundfile as sf
    audio = {name: sf.read(stems / f'{name}.wav')[0].mean(1)
             for name in ('vocals', 'drums', 'bass', 'guitar', 'piano', 'other')}
    mix = sum(audio.values())
    return round(100 * float((audio['guitar'] ** 2).sum() / ((mix ** 2).sum() + 1e-12)), 2)


def run_here(slug, takes):
    out_dir = REPO / OUT_ROOT / slug
    files = [out_dir / t for t in takes] if takes else sorted(out_dir.glob(f'{slug}_*.wav'))
    bounds = {path.name: pass_bounds(out_dir, path.name) for path in files}
    report = {'slug': slug, 'window_s': WINDOW_S, 'active_db': ACTIVE_DB,
              'present_pct': PRESENT_PCT, 'percussion_max_pct': PERCUSSION_MAX_PCT,
              'guitar_warn_pct': GUITAR_WARN_PCT, 'takes': []}
    with tempfile.TemporaryDirectory() as tmp:
        for model in ('htdemucs', 'htdemucs_6s'):
            subprocess.run([sys.executable, '-m', 'demucs', '-n', model, '-o', tmp,
                            *map(str, files)], check=True, stdout=subprocess.DEVNULL)
        for path in files:
            sep = Path(tmp) / 'htdemucs' / path.stem
            rows, percussion = measure(sep, bounds[path.name])
            guitar = guitar_share(Path(tmp) / 'htdemucs_6s' / path.stem)
            style = take_style(slug, path.name)
            heard = [r['pass'] for r in rows if r['voice_active_pct'] >= PRESENT_PCT]
            report['takes'].append({'file': path.name, 'style': style, 'passes': rows, 'voice_in_passes': heard,
                                    'ok': not heard,
                                    'percussion_energy_pct': percussion,
                                    'percussion': percussion >= PERCUSSION_MAX_PCT,
                                    'guitar_energy_pct': guitar,
                                    'guitar': guitar >= GUITAR_WARN_PCT})
    (out_dir / 'stems.json').write_text(json.dumps(report, indent=1))
    return report


def run_remote(slug, takes):
    host = remote_host()
    ssh = ['ssh', '-i', SSH_KEY, '-o', 'BatchMode=yes', host]
    out = OUT_ROOT / slug
    files = [out / t for t in takes] if takes else sorted(p.relative_to(REPO) for p in (REPO / out).glob(f'{slug}_*.wav'))
    send = [Path(__file__).relative_to(REPO), SOURCE_ROOT / slug / 'metadata.json', OUT_ROOT / 'manifest.json',
            out / 'fidelity.json', *files]
    subprocess.run(ssh + [f'mkdir -p {" ".join(sorted({shlex.quote(f"{REMOTE_REPO}/{p.parent}") for p in send}))}'], check=True)
    for path in send:
        subprocess.run(['rsync', '-a', '-e', f'ssh -i {SSH_KEY} -o BatchMode=yes',
                        str(REPO / path), f'{host}:{REMOTE_REPO}/{path}'], check=True)
    script = f'~/{REMOTE_REPO}/{Path(__file__).relative_to(REPO)}'
    names = ' '.join(shlex.quote(Path(f).name) for f in files)
    subprocess.run([str(GUARD), 'run', f'cd ~/{REMOTE_REPO} && {REMOTE_PY} {script} --here {slug} {names}'], check=True)
    subprocess.run(['rsync', '-a', '-e', f'ssh -i {SSH_KEY} -o BatchMode=yes',
                    f'{host}:{REMOTE_REPO}/{out}/stems.json', str(REPO / out / 'stems.json')], check=True)
    return json.loads((REPO / out / 'stems.json').read_text())


def show(report):
    print(f"{report['slug']}: mọi bản là instrumental; giọng có mặt khi ≥ {report['present_pct']} % "
          f"cửa sổ {report['window_s']} s có vocal > {report['active_db']} dB so với nhạc cụ; "
          f"có bộ gõ khi stem drums ≥ {report['percussion_max_pct']} % năng lượng cả bản; "
          f"stem guitar (htdemucs_6s) chỉ để tham khảo, không phải cờ")
    for t in report['takes']:
        cells = '  '.join(f"lượt {r['pass']}: {r['voice_active_pct']:>5}%" for r in t['passes'])
        verdict = 'không giọng' if t['ok'] else 'CÓ GIỌNG'
        drums = f"bộ gõ {t['percussion_energy_pct']}%{' CÓ' if t['percussion'] else ''}"
        drums += f"  guitar {t.get('guitar_energy_pct', '-')}%"
        print(f"{t['file']:48} style {t['style']}  {cells}  giọng ở lượt {t['voice_in_passes'] or '-'}  {verdict}  {drums}")


def main():
    ap = argparse.ArgumentParser(description='Đo giọng (vocal stem) theo từng lượt giai điệu, guitar (htdemucs_6s) và bộ gõ trong các bản Mureka (Demucs 4 stem trên GPU server).')
    ap.add_argument('slug')
    ap.add_argument('takes', nargs='*', help='tên file trong audio/christmas/mureka/<slug>/ (mặc định: mọi <slug>_*.wav)')
    ap.add_argument('--here', action='store_true', help='chạy tại máy này (dùng trên server)')
    args = ap.parse_args()
    os.chdir(REPO)
    report = run_here(args.slug, args.takes) if args.here else run_remote(args.slug, args.takes)
    if not args.here:
        show(report)


if __name__ == '__main__':
    main()

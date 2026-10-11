#!/usr/bin/env python3
import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
SKILL = Path(__file__).resolve().parents[1]
SOURCE_ROOT = Path('research/christmas-carols/mureka')
OUT_ROOT = Path('audio/christmas/mureka')
REMOTE_REPO = 'youtube-qc'
REMOTE_PY = f'~/{REMOTE_REPO}/.claude/skills/audio-christmas-workflow/.venv/bin/python'
CHECKPOINT = os.path.expanduser('~/piano_transcription_inference_data/note_F1=0.9677_pedal_F1=0.9186.pth')
GUARD = REPO / '.claude/skills/pm-production/scripts/server_guard/guard.sh'
SR_CHROMA = 22050
HOP = 512
ONSET_TOL_S = 0.20
CONTROL_SHIFT_BEATS = 0.5
SEQUENCE_WINDOW_S = 1.5
SKYLINE_GROUP_S = 0.08
REGISTER_MARGIN = 7
SHUFFLES = 30
OPENING_MARGIN = 10.0


def remote_host():
    env = REPO / '.claude/skills/video-generator/remote.env'
    for line in env.read_text().splitlines() if env.exists() else []:
        if line.startswith('VG_REMOTE='):
            return line.split('=', 1)[1].strip().strip('"\'')
    sys.exit(f'no VG_REMOTE in {env}')


def reference_notes(mid_path):
    import mido
    mid = mido.MidiFile(mid_path)
    tempo, ticks, seconds, open_notes, notes = 500000, 0, 0.0, {}, []
    for msg in mido.merge_tracks(mid.tracks):
        seconds += mido.tick2second(msg.time, mid.ticks_per_beat, tempo)
        if msg.type == 'set_tempo':
            tempo = msg.tempo
        elif msg.type == 'note_on' and msg.velocity > 0:
            open_notes[msg.note] = seconds
        elif msg.type in ('note_off', 'note_on') and msg.note in open_notes:
            notes.append({'onset': open_notes.pop(msg.note), 'offset': seconds, 'pitch': msg.note})
    notes.sort(key=lambda n: n['onset'])
    return notes, 60_000_000 / tempo


def transcribe(path, model):
    import librosa
    from piano_transcription_inference import sample_rate
    audio, _ = librosa.load(str(path), sr=sample_rate, mono=True)
    events = model.transcribe(audio, None)['est_note_events']
    return [{'onset': float(e['onset_time']), 'offset': float(e['offset_time']), 'pitch': int(e['midi_note']),
             'velocity': int(e['velocity'])} for e in events]


def chroma(path):
    import librosa
    y, _ = librosa.load(str(path), sr=SR_CHROMA, mono=True)
    return librosa.feature.chroma_cqt(y=y, sr=SR_CHROMA, hop_length=HOP)


def align(ref_chroma, take_chroma):
    import librosa
    import numpy as np
    frame_s = HOP / SR_CHROMA
    candidates = []
    for shift in range(-6, 6):
        cost, path = librosa.sequence.dtw(X=ref_chroma, Y=np.roll(take_chroma, -shift, axis=0), metric='cosine')
        path = path[::-1]
        candidates.append((float(cost[-1, -1] / len(path)), shift, path[:, 0] * frame_s, path[:, 1] * frame_s))
    return candidates


def best_shift(ref, est, candidates):
    def found(candidate):
        rows, _ = match(ref, est, candidate[1], candidate[2], candidate[3])
        return sum(r['kind'] != 'missing' for r in rows)
    cost, shift, ref_t, take_t = max(candidates, key=lambda c: (found(c), -c[0]))
    return shift, cost, ref_t, take_t


def warp(times, ref_t, take_t):
    import numpy as np
    return np.interp(times, ref_t, take_t)


def match(ref, est, shift, ref_t, take_t, time_offset=0.0):
    used = set()
    rows = []
    for note in ref:
        at = float(warp(note['onset'] + time_offset, ref_t, take_t))
        want = note['pitch'] + shift
        near = [(abs(e['onset'] - at), i, e) for i, e in enumerate(est)
                if i not in used and abs(e['onset'] - at) <= ONSET_TOL_S]
        exact = sorted((d, i, e) for d, i, e in near if e['pitch'] == want)
        octave = sorted((d, i, e) for d, i, e in near if (e['pitch'] - want) % 12 == 0)
        hit = exact[0] if exact else octave[0] if octave else None
        if hit:
            used.add(hit[1])
        rows.append({'ref_onset': round(note['onset'], 3), 'take_onset_expected': round(at, 3), 'pitch': want,
                     'kind': 'exact' if exact else 'octave' if octave else 'missing',
                     'got': hit[2]['pitch'] if hit else None})
    return rows, used


def onset_groups(est, low, high):
    notes = sorted((e for e in est if low <= e['pitch'] <= high), key=lambda e: e['onset'])
    groups = []
    for e in notes:
        if groups and e['onset'] - groups[-1][0] <= SKYLINE_GROUP_S:
            groups[-1][1].add(e['pitch'])
        else:
            groups.append((e['onset'], {e['pitch']}))
    return groups


def banded_lcs(ref_pitch, ref_time, group_pitches, group_time):
    n, m = len(ref_pitch), len(group_pitches)
    prev = [0] * (m + 1)
    for i in range(1, n + 1):
        cur = [0] * (m + 1)
        for j in range(1, m + 1):
            if ref_pitch[i - 1] in group_pitches[j - 1] and abs(ref_time[i - 1] - group_time[j - 1]) <= SEQUENCE_WINDOW_S:
                cur[j] = prev[j - 1] + 1
            else:
                cur[j] = max(prev[j], cur[j - 1])
        prev = cur
    return prev[m]


def sequence_match(ref, est, shift, ref_t, take_t):
    import random
    low = min(n['pitch'] for n in ref) + shift - REGISTER_MARGIN
    high = max(n['pitch'] for n in ref) + shift + REGISTER_MARGIN
    groups = onset_groups(est, low, high)
    ref_pitch = [n['pitch'] + shift for n in ref]
    ref_time = [float(warp(n['onset'], ref_t, take_t)) for n in ref]
    group_time = [g[0] for g in groups]
    hit = banded_lcs(ref_pitch, ref_time, [g[1] for g in groups], group_time)
    rng = random.Random(0)
    chance = []
    for _ in range(SHUFFLES):
        pitches = [g[1] for g in groups]
        rng.shuffle(pitches)
        chance.append(banded_lcs(ref_pitch, ref_time, pitches, group_time))
    return {'onset_groups': len(groups), 'in_order_pct': round(100 * hit / len(ref), 1),
            'shuffled_pct': round(100 * sum(chance) / len(chance) / len(ref), 1)}


def summarize(rows, passes):
    n = len(rows)
    exact = sum(r['kind'] == 'exact' for r in rows)
    octave = sum(r['kind'] == 'octave' for r in rows)
    per = len(rows) // passes if passes else n
    by_pass = []
    for p in range(passes):
        part = rows[p * per:(p + 1) * per] if p < passes - 1 else rows[p * per:]
        by_pass.append(round(100 * sum(r['kind'] != 'missing' for r in part) / max(1, len(part)), 1))
    return {'notes': n, 'exact': exact, 'octave': octave, 'missing': n - exact - octave,
            'exact_pct': round(100 * exact / n, 1), 'pitch_class_pct': round(100 * (exact + octave) / n, 1),
            'by_pass_pct': by_pass}


def analyse_take(path, ref, ref_chroma, model, bpm, passes, melody_low):
    est = transcribe(path, model)
    shift, cost, ref_t, take_t = best_shift(ref, est, align(ref_chroma, chroma(path)))
    rows, used = match(ref, est, shift, ref_t, take_t)
    control_rows, _ = match(ref, est, shift, ref_t, take_t, CONTROL_SHIFT_BEATS * 60 / bpm)
    span = (float(take_t[-1]) - float(take_t[0])) / max(1e-6, float(ref_t[-1]) - float(ref_t[0]))
    first = float(warp(ref[0]['onset'], ref_t, take_t))
    last = float(warp(ref[-1]['offset'], ref_t, take_t))
    melody_band = [e for i, e in enumerate(est) if e['pitch'] >= melody_low + shift and first - 0.5 <= e['onset'] <= last + 0.5]
    extra = [e for i, e in enumerate(est) if i not in used and e['pitch'] >= melody_low + shift
             and first - 0.5 <= e['onset'] <= last + 0.5]
    low = [e for e in est if e['pitch'] < melody_low + shift and first - 0.5 <= e['onset'] <= last + 0.5]
    bars = max(1.0, (last - first) / (4 * 60 / bpm * span))
    import soundfile
    info = soundfile.info(str(path))
    per = len(ref) // passes
    starts = [float(warp(ref[p * per]['onset'], ref_t, take_t)) for p in range(1, passes)]
    bounds = [0.0, *starts, info.duration]
    found, control = summarize(rows, passes), summarize(control_rows, passes)
    margin = found['by_pass_pct'][0] - control['by_pass_pct'][0]
    return {
        'file': path.name, 'duration_s': round(info.duration, 2),
        'transpose_semitones': shift, 'chroma_cost': round(cost, 4), 'time_ratio': round(span, 3),
        'melody_window_s': [round(first, 2), round(last, 2)],
        'pass_bounds_s': [[round(a, 2), round(b, 2)] for a, b in zip(bounds, bounds[1:])],
        'opening': {'pass_1_pct': found['by_pass_pct'][0], 'control_pct': control['by_pass_pct'][0],
                    'margin': round(margin, 1), 'min_margin': OPENING_MARGIN,
                    'recognizable': margin >= OPENING_MARGIN},
        'match': found,
        'sequence': sequence_match(ref, est, shift, ref_t, take_t),
        'control': {k: v for k, v in control.items() if k.endswith('_pct')},
        'octave_offsets': {str(o): sum(1 for r in rows if r['kind'] == 'octave' and r['got'] - r['pitch'] == o)
                           for o in sorted({r['got'] - r['pitch'] for r in rows if r['kind'] == 'octave'})},
        'transcribed_notes': len(est),
        'extra_notes_in_melody_band': len(extra),
        'extra_per_ref_note': round(len(extra) / len(ref), 2),
        'melody_band_notes': len(melody_band),
        'low_notes_per_bar': round(len(low) / bars, 2),
        'missing': [r for r in rows if r['kind'] == 'missing'],
    }


def run_here(slug, takes):
    import torch
    from piano_transcription_inference import PianoTranscription
    src = REPO / SOURCE_ROOT / slug
    meta = json.loads((src / 'metadata.json').read_text())
    ref, bpm = reference_notes(src / f'{slug}.mid')
    passes = int(meta.get('pass_count', 1))
    melody_low = min(n['pitch'] for n in ref)
    model = PianoTranscription(device='cuda' if torch.cuda.is_available() else 'cpu', checkpoint_path=CHECKPOINT)
    ref_chroma = chroma(src / f'{slug}.wav')
    out_dir = REPO / OUT_ROOT / slug
    files = [out_dir / t for t in takes] if takes else sorted(out_dir.glob(f'{slug}_*.wav'))
    report = {'slug': slug, 'reference': {'notes': len(ref), 'bpm': round(bpm, 2), 'passes': passes,
                                          'pitch_range': [melody_low, max(n['pitch'] for n in ref)],
                                          'onset_tolerance_s': ONSET_TOL_S},
              'calibration': analyse_take(src / f'{slug}.wav', ref, ref_chroma, model, bpm, passes, melody_low),
              'takes': []}
    for path in files:
        report['takes'].append(analyse_take(path, ref, ref_chroma, model, bpm, passes, melody_low))
        print(f'  {path.name}: {report["takes"][-1]["match"]["pitch_class_pct"]} %', flush=True)
    (out_dir / 'fidelity.json').write_text(json.dumps(report, indent=1))
    return report


def run_remote(slug, takes):
    host = remote_host()
    ssh = ['ssh', '-i', os.path.expanduser('~/.ssh/id_rsa'), '-o', 'BatchMode=yes', host]
    src = SOURCE_ROOT / slug
    out = OUT_ROOT / slug
    files = [out / t for t in takes] if takes else sorted(p.relative_to(REPO) for p in (REPO / out).glob(f'{slug}_*.wav'))
    send = [Path(__file__).relative_to(REPO), src / 'metadata.json', src / f'{slug}.mid', src / f'{slug}.wav', *files]
    subprocess.run(ssh + [f'mkdir -p {" ".join(sorted({shlex.quote(f"{REMOTE_REPO}/{p.parent}") for p in send}))}'], check=True)
    for path in send:
        subprocess.run(['rsync', '-a', '-e', f'ssh -i {os.path.expanduser("~/.ssh/id_rsa")} -o BatchMode=yes',
                        str(REPO / path), f'{host}:{REMOTE_REPO}/{path}'], check=True)
    script = f'~/{REMOTE_REPO}/{Path(__file__).relative_to(REPO)}'
    names = ' '.join(shlex.quote(Path(f).name) for f in files)
    subprocess.run([str(GUARD), 'run', f'cd ~/{REMOTE_REPO} && {REMOTE_PY} {script} --here {slug} {names}'], check=True)
    subprocess.run(['rsync', '-a', '-e', f'ssh -i {os.path.expanduser("~/.ssh/id_rsa")} -o BatchMode=yes',
                    f'{host}:{REMOTE_REPO}/{out}/fidelity.json', str(REPO / out / 'fidelity.json')], check=True)
    return json.loads((REPO / out / 'fidelity.json').read_text())


def show(report):
    ref = report['reference']
    print(f"{report['slug']}: {ref['notes']} nốt MIDI, {ref['passes']} lượt, {ref['bpm']} BPM, lệch onset ≤ {ref['onset_tolerance_s']} s")
    print(f"mở đầu nhận ra bài = lượt 1 khớp tên nốt cao hơn đối chứng ≥ {OPENING_MARGIN:g} điểm")
    print(f"{'file':48} {'mở đầu':>14} {'đúng nốt':>8} {'đúng tên nốt':>12} {'theo lượt':>18} {'đối chứng đúng/tên':>18} {'dịch giọng':>10} {'tốc độ':>6} {'nốt thêm/nốt':>12} {'bass/ô nhịp':>11} {'trình tự/xáo':>13}")
    for take in [dict(report['calibration'], file='(nguồn piano, hiệu chuẩn)')] + report['takes']:
        m = take['match']
        o = take['opening']
        gate = f"{o['margin']:+.0f} {'ĐẠT' if o['recognizable'] else 'TRƯỢT'}"
        print(f"{take['file']:48} {gate:>14} {m['exact_pct']:>7}% {m['pitch_class_pct']:>11}% {str(m['by_pass_pct']):>18} "
              f"{take['control']['exact_pct']:>4}/{take['control']['pitch_class_pct']}% {take['transpose_semitones']:>+10} {take['time_ratio']:>6} "
              f"{take['extra_per_ref_note']:>12} {take['low_notes_per_bar']:>11} {take['sequence']['in_order_pct']:>6}/{take['sequence']['shuffled_pct']}%")


def main():
    ap = argparse.ArgumentParser(description='Đo độ bám giai điệu MIDI gốc của các bản Mureka (chép nốt piano trên GPU server).')
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

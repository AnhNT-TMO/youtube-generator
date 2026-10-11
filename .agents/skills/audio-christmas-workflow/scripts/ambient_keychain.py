import argparse
import difflib
import hashlib
import io
import json
import os
import re
import subprocess

import numpy as np
import soundfile as sf

from ambient_vibes import fit_tempo, render_finish

PC = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8,
      'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}
FLAT = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
SHARP = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'Bb', 'B']
NOTE_RE = re.compile(r'(?<![A-Za-z#])([A-G][#b]?)')
KEY_RE = re.compile(r'([A-G][#b]?) (major|minor|aeolian|dorian)')
SHORT_RE = re.compile(r'^([A-G][#b]?)(m?)$')


def key_of(text):
    m = KEY_RE.search(text)
    return PC[m.group(1)], 'major' if m.group(2) == 'major' else 'minor'


def short_key(text):
    m = SHORT_RE.match(text)
    if not m:
        raise SystemExit(f'bad key {text!r}: use F, Bb, Em')
    return PC[m.group(1)], 'minor' if m.group(2) else 'major'


def key_name(k):
    return (FLAT if k[1] == 'major' else SHARP)[k[0]] + ('m' if k[1] == 'minor' else '')


def fifths_step(a, b):
    ca = (a[0] + (3 if a[1] == 'minor' else 0)) * 7 % 12
    cb = (b[0] + (3 if b[1] == 'minor' else 0)) * 7 % 12
    d = min((ca - cb) % 12, (cb - ca) % 12)
    return d


def shift_name(name, t, mode='major'):
    return NOTE_RE.sub(lambda m: (FLAT if mode == 'major' else SHARP)[(PC[m.group(1)] + t) % 12], name)


def lift_at(plan):
    table = plan['key_plan']['transpose_semitones_by_beat']
    base = table[0][2]

    def lift(beat):
        for row in table:
            if row[0] <= beat < row[1]:
                return row[2] - base
        return table[-1][2] - base
    return lift, base


def melody_lift_at(plan, lift, base):
    pickups = [r for r in plan['key_plan']['transpose_semitones_by_beat'] if len(r) > 3]
    statements = [s for s in plan['form']['sections'] if s['kind'] == 'statement' and 'transpose_semitones' in s]

    def melody_lift(beat):
        for r in pickups:
            if r[0] <= beat < r[1]:
                return r[2] - base
        for s in statements:
            if s['start_beat'] <= beat < s['end_beat']:
                return s['transpose_semitones'] - base
        return lift(beat)
    return melody_lift


def flatten(plan):
    lift, base = lift_at(plan)
    melody_lift = melody_lift_at(plan, lift, base)
    for e in plan['note_plan']['events']:
        e['pitch'] -= melody_lift(e['beat']) if e['part'] == 'melody' else lift(e['beat'])
    for h in plan['phrase_harmony']:
        h['chord'] = shift_name(h['chord'], -lift(h['start_beat']))
        h['transpose_semitones'] = base
    for k in plan['key_plan']['sections']:
        k['key'] = shift_name(k['key'], base - k['transpose_semitones'], key_of(k['key'])[1])
        k['transpose_semitones'] = base
    plan['key_plan']['transpose_semitones_by_beat'] = [[r[0], r[1], base] + r[3:] for r in plan['key_plan']['transpose_semitones_by_beat']]
    return plan


def transpose(plan, t):
    for e in plan['note_plan']['events']:
        e['pitch'] += t
    for h in plan['phrase_harmony']:
        h['chord'] = shift_name(h['chord'], t)
    for k in plan['key_plan']['sections']:
        k['key'] = shift_name(k['key'], t, key_of(k['key'])[1])
    plan['meta']['key'] = shift_name(plan['meta']['key'], t, key_of(plan['meta']['key'])[1])
    return plan


def home(plan):
    return key_of(plan['key_plan']['sections'][0]['key'])


def shift_to(plan, target):
    start = home(plan)
    if start[1] != target[1]:
        raise SystemExit(f"{plan['meta']['slug']}: mode {start[1]} cannot become {target[1]}")
    t = (target[0] - start[0]) % 12
    return t - 12 if t > 6 else t


def mono(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-f', 'wav', '-'], capture_output=True).stdout
    return sf.read(io.BytesIO(raw))


def centroids(x, sr):
    out = []
    for a in range(0, len(x) - sr, sr):
        seg = x[a:a + sr] * np.hanning(sr)
        e = np.abs(np.fft.rfft(seg)) ** 2
        out.append((np.fft.rfftfreq(sr, 1 / sr) * e).sum() / e.sum() if e.sum() > 1e-9 else np.nan)
    return np.array(out)


def short_term(path):
    err = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', path, '-af', 'ebur128', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    vals = [float(v) for v in re.findall(r'\bS:\s*(-?[\d.]+)', err)]
    return np.array(vals[::10])


def flow_check(path, bounds, rules):
    x, sr = mono(path)
    cen = centroids(x, sr)
    lu = short_term(path)
    w = rules['window_s']
    rises = np.array([lu[t] - lu[t - w:t].min() for t in range(w + 15, len(lu))])
    near = np.zeros(len(rises), bool)
    for b in bounds:
        near[max(0, int(b) - 10 - w - 15):int(b) + 10 - w - 15] = True
    inside = float(np.percentile(rises[~near], 99)) if (~near).any() else 0.0
    rise = float(rises[near].max()) if near.any() else 0.0
    edges = []
    for b in bounds:
        b = int(round(b))
        gap, span = rules['edge_gap_s'], rules['edge_s']
        before, after = slice(max(0, b - gap - span), b - gap), slice(b + gap, b + gap + span)
        edges.append({'at_s': b,
                      'loudness_db': round(float(np.median(lu[after]) - np.median(lu[before])), 2),
                      'brightness_pct': round(float(np.nanmedian(cen[after]) / np.nanmedian(cen[before]) - 1) * 100, 1)})
    worst_l = max((abs(e['loudness_db']) for e in edges), default=0.0)
    worst_c = max((abs(e['brightness_pct']) for e in edges), default=0.0)
    return {'edge_rise_db': round(rise, 2), 'inside_rise_p99_db': round(inside, 2), 'worst_edge_loudness_db': worst_l, 'worst_edge_brightness_pct': worst_c,
            'pass': bool(rise <= max(inside, rules['max_rise_db']) and worst_l <= rules['max_edge_db'] and worst_c <= rules['max_edge_brightness_pct']),
            'edges': edges}


def join(files, out, crossfade, fade_in, curve_out='qsin', curve_in='qsin', entry_db=0.0, entry_s=0.0):
    inputs = sum((['-i', f] for f in files), [])
    graph, last = [], '[0:a]'
    for k in range(1, len(files)):
        src = f'[{k}:a]'
        if entry_db and entry_s:
            graph.append(f"{src}volume='if(lt(t,{entry_s}),pow(10,({entry_db}*(1-t/{entry_s}))/20),1)':eval=frame[e{k}]")
            src = f'[e{k}]'
        graph.append(f'{last}{src}acrossfade=d={crossfade}:c1={curve_out}:c2={curve_in}[x{k}]')
        last = f'[x{k}]'
    graph.append(f'{last}afade=t=in:d={fade_in}:curve=hsin[out]')
    subprocess.run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', *inputs, '-filter_complex', ';'.join(graph),
                    '-map', '[out]', '-c:a', 'libmp3lame', '-b:a', '320k', out], check=True)


def duration(path):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                                capture_output=True, text=True, check=True).stdout)


def bounds_of(files, crossfade):
    t, out = 0.0, []
    for f in files[:-1]:
        t += duration(f) - crossfade
        out.append(t + crossfade / 2)
    return out


def song_out(cfg, vibe, slug, key):
    return f"{cfg['out']}/{vibe}/{slug}/{slug}-{key_name(key)}"


def note_name(p):
    return f'{SHARP[p % 12]}{p // 12 - 1}'


def find_run(src, got):
    n = len(got)
    for off in sorted({q - s for q in got[:1] for s in src}, key=abs):
        for i in range(len(src) - n + 1):
            if all(src[i + k] + off == got[k] for k in range(n)):
                return i, off
    return None


def melody_problems(plan):
    path = plan['notation_reference']['path']
    if not os.path.exists(path):
        raise SystemExit(f'{path} missing: copy research/christmas-carols/melodies here before rendering')
    src = [p for p, _ in json.load(open(path))['melody'] if p]
    events = sorted((e for e in plan['note_plan']['events'] if e['part'] == 'melody'), key=lambda e: e['beat'])
    problems, last_end = [], None
    statements = [s for s in plan['form']['sections'] if s['kind'] == 'statement']
    for n, s in enumerate(statements):
        start = s.get('pickup_start', s['start_beat'])
        end = s['end_beat']
        if n + 1 < len(statements):
            end = min(end, statements[n + 1].get('pickup_start', end))
        got = [e for e in events if start - 1e-6 <= e['beat'] < end - 1e-6]
        if not got:
            problems.append(f"{s['section']}: no melody notes")
            continue
        pitches = [e['pitch'] for e in got]
        run = find_run(src, pitches)
        if run:
            last_end = run[0] + len(pitches)
            continue
        off = max(set(q - s0 for q, s0 in zip(pitches, src)), key=[q - s0 for q, s0 in zip(pitches, src)].count)
        for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, [p + off for p in src], pitches, autojunk=False).get_opcodes():
            if op != 'equal' and j1 < len(got):
                want = ' '.join(note_name(p + off) for p in src[i1:i2]) or '-'
                have = ' '.join(note_name(p) for p in pitches[j1:j2]) or '-'
                problems.append(f"{s['section']} beat {got[j1]['beat']}: source {want}, plan {have}")
            elif op == 'delete':
                problems.append(f"{s['section']}: {i2 - i1} source notes missing at the end")
        last_end = None
    if last_end is not None and last_end != len(src):
        problems.append(f'last statement stops {len(src) - last_end} notes before the end of the source melody')
    return problems


def gate_melody(slug, plan):
    problems = melody_problems(plan)
    if problems:
        raise SystemExit(f'{slug}: melody differs from the source:\n  ' + '\n  '.join(problems[:8]))


def plan_sha(slug, cfg):
    return hashlib.sha1(open(cfg['plans'].format(slug=slug), 'rb').read()).hexdigest()[:12]


def render_song(slug, key_text, cfg, spec, allowed, force=False):
    target = short_key(key_text)
    ok = allowed.get(slug, {}).get('allowed')
    if ok is not None and key_name(target) not in ok:
        raise SystemExit(f"{slug}: key {key_text} not in allowed {ok}")
    out = song_out(cfg, spec['name'], slug, target)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sha = plan_sha(slug, cfg)
    if not force and os.path.exists(f'{out}.row.json'):
        row = json.load(open(f'{out}.row.json'))
        if row.get('plan_sha') == sha:
            gate_melody(slug, json.load(open(f'{out}.plan.json')))
            return row, f'{out}.mp3'
    plan = flatten(json.load(open(cfg['plans'].format(slug=slug))))
    t = shift_to(plan, target)
    transpose(plan, t)
    tempo, ratio, rate, problems = fit_tempo(plan, spec, cfg)
    if problems:
        raise SystemExit(f"{slug} does not fit: {'; '.join(problems)}")
    plan['meta']['tempo'] = tempo
    gate_melody(slug, plan)
    info = render_finish(plan, spec['name'], out, cfg)
    if info is None:
        raise SystemExit(f"render failed: {slug}")
    row = {'slug': slug, 'key': key_name(target), 'shift': t, 'tempo': tempo, 'notes_per_s': round(rate, 3),
           'seconds': round(duration(f'{out}.mp3'), 3), 'lufs': info['lufs'], 'true_peak': info['true_peak'],
           'pass_rms': info['pass_rms_after'], 'plan_sha': sha}
    row.update(edge_stats(f'{out}.mp3', cfg['flow']))
    json.dump(row, open(f'{out}.row.json', 'w'))
    print(json.dumps(row), flush=True)
    return row, f'{out}.mp3'


def edge_stats(path, rules, crossfade=2.0):
    x, sr = mono(path)
    cen = centroids(x, sr)
    lu = short_term(path)
    gap, span, half = rules['edge_gap_s'], rules['edge_s'], crossfade / 2
    n = min(len(cen), len(lu))
    head = slice(int(half + gap), int(half + gap + span))
    tail = slice(max(0, int(n - half - gap - span)), max(1, int(n - half - gap)))
    return {'head_brightness_hz': round(float(np.nanmedian(cen[head])), 1), 'tail_brightness_hz': round(float(np.nanmedian(cen[tail])), 1),
            'head_lufs_s': round(float(np.median(lu[head])), 2), 'tail_lufs_s': round(float(np.median(lu[tail])), 2)}


def vibe_spec(cfg, vibe):
    return dict(cfg['vibes'][vibe], name=vibe)


def allowed_of(cfg):
    return json.load(open(cfg['allowed_keys'])) if os.path.exists(cfg.get('allowed_keys', '')) else {}


def not_clean(slugs, cfg):
    folder = cfg.get('pd_audit')
    if not folder:
        return []
    if not os.path.isdir(folder):
        raise SystemExit(f'{folder} missing: copy the pd-audit folder here before rendering an album pool')
    bad = []
    for slug in slugs:
        path = f'{folder}/{slug}.json'
        verdict = json.load(open(path))['verdict'] if os.path.exists(path) else 'not audited'
        if verdict != 'clean':
            bad.append(f'{slug}: {verdict}')
    return bad


def not_familiar(slugs, cfg):
    folder = cfg.get('pd_audit')
    if not folder:
        return []
    odd = []
    for slug in slugs:
        path = f'{folder}/{slug}.json'
        fam = (json.load(open(path)).get('familiar') or {}) if os.path.exists(path) else {}
        status = fam.get('status', 'unchecked')
        if status != 'familiar' and not fam.get('approved'):
            odd.append(f'{slug}: {status}')
    return odd


def gate_familiar(slugs, cfg):
    odd = not_familiar(slugs, cfg)
    cap = cfg['rounds'].get('max_unfamiliar', 0)
    if len(odd) > cap:
        raise SystemExit(f'{len(odd)} songs not marked familiar, the album allows {cap} (unchecked counts as unfamiliar):\n  ' + '\n  '.join(odd))


def render(a, cfg):
    spec, allowed = vibe_spec(cfg, a.vibe), allowed_of(cfg)
    pool = json.load(open(a.pool))
    slugs = list(dict.fromkeys(r['slug'] for r in pool))
    bad = not_clean(slugs, cfg)
    if bad:
        raise SystemExit('songs without a clean public-domain audit (pd_audit.py summary):\n  ' + '\n  '.join(bad))
    gate_familiar(slugs, cfg)
    rows = {}
    for r in pool:
        row, _ = render_song(r['slug'], r['key'], cfg, spec, allowed, a.force)
        rows[r['slug']] = dict(row, tier=r.get('tier'))
    os.makedirs(f'{a.out}/songs', exist_ok=True)
    json.dump(rows, open(f'{a.out}/songs/index.json', 'w'), indent=1)
    print(f'{len(rows)} songs, {sum(r["seconds"] for r in rows.values()) / 60:.1f} min -> {a.out}/songs/index.json')


def edge_cost(x, y):
    bright = abs(y['head_brightness_hz'] / x['tail_brightness_hz'] - 1) * 100
    loud = abs(y['head_lufs_s'] - x['tail_lufs_s'])
    return bright, loud


def rounds(a, cfg):
    import random
    rules = cfg['rounds']
    songs = json.load(open(f'{a.out}/songs/index.json'))
    names = list(songs)
    key = {s: short_key(songs[s]['key']) for s in names}
    cf = a.crossfade
    first_s = rules['first_tier_minutes'] * 60
    random.seed(a.seed)

    def fits(seq):
        n, total = len(seq), sum(songs[s]['seconds'] for s in seq)
        return total - (n - 1) * 4.0 <= a.target <= total - (n - 1) * 1.0

    def long_enough(seq):
        return sum(songs[s]['seconds'] for s in seq) - (len(seq) - 1) * 1.0 >= a.target

    def extend(seq, used, starts, last_round):
        for _ in range(2000 if last_round else 300):
            out, pairs = list(seq), set(used)
            left = set(names)
            round_start = len(out)
            while left:
                last = out[-1] if out else None
                elapsed = sum(songs[s]['seconds'] - cf for s in out)
                cand = [s for s in left if last is None or (fifths_step(key[last], key[s]) <= rules['max_step']
                        and (last, s) not in pairs and (s, last) not in pairs)]
                cand = [s for s in cand if s not in out[-rules['min_repeat_gap']:]]
                if not out:
                    cand = [s for s in cand if s in rules['openers']]
                if len(left) == len(names):
                    cand = [s for s in cand if s not in starts and s != (out[round_start] if len(out) > round_start else None)]
                if elapsed < first_s:
                    cand = [s for s in cand if songs[s].get('tier') in rules['first_tiers']]
                if not cand:
                    break
                s = random.choice(cand)
                if last:
                    pairs.add((last, s))
                out.append(s)
                left.discard(s)
                if last_round and a.target and long_enough(out):
                    break
                if last_round and a.target and not left:
                    left = set(names)
            done = not left if not (last_round and a.target) else long_enough(out)
            if not done:
                continue
            if last_round and (out[-1] not in rules['endings'] or (a.target and not fits(out))):
                continue
            return out, pairs
        return None

    best = None
    count = rules['count'] if not a.target else max(1, int(a.target // (sum(songs[s]['seconds'] for s in names) - len(names) * cf)))
    for _ in range(a.trials):
        seq, used, starts = [], set(), set()
        for k in range(count):
            got = extend(seq, used, starts, k == count - 1)
            if got is None:
                break
            starts.add(got[0][len(seq)])
            seq, used = got
        else:
            costs = [edge_cost(songs[x], songs[y]) for x, y in zip(seq, seq[1:])]
            score = (round(max(c[0] for c in costs), 1), round(max(c[1] for c in costs), 2), sum(c[0] for c in costs))
            if best is None or score < best[0]:
                best = (score, seq, costs)
    if best is None:
        raise SystemExit('no order satisfies the rounds rules; raise --trials or relax VIBES.json rounds')
    score, seq, costs = best
    order = [{'slug': s, 'key': songs[s]['key']} for s in seq]
    json.dump(order, open(a.order_out, 'w'), indent=1)
    total = sum(songs[s]['seconds'] for s in seq) - (len(seq) - 1) * cf
    print(json.dumps({'tracks': len(seq), 'minutes_at_crossfade': round(total / 60, 2), 'worst_edge_brightness_pct': score[0],
                      'worst_edge_loudness_db': score[1], 'mean_edge_brightness_pct': round(score[2] / len(costs), 1)}))


def album(a, cfg):
    rows = json.load(open(a.order))
    slugs = list(dict.fromkeys(r['slug'] for r in rows))
    bad = not_clean(slugs, cfg)
    if bad:
        raise SystemExit('songs without a clean public-domain audit (pd_audit.py summary):\n  ' + '\n  '.join(bad))
    gate_familiar(slugs, cfg)
    spec, allowed = vibe_spec(cfg, a.vibe), allowed_of(cfg)
    os.makedirs(a.out, exist_ok=True)
    report, files, prev = [], [], None
    for n, r in enumerate(rows, 1):
        row, path = render_song(r['slug'], r['key'], cfg, spec, allowed, a.force and r['slug'] not in {x['slug'] for x in report})
        target = short_key(row['key'])
        report.append(dict(row, n=n, step_from_prev=fifths_step(prev, target) if prev else 0))
        files.append(path)
        prev = target
    crossfade = a.crossfade
    if a.target:
        crossfade = (sum(r['seconds'] for r in report) - a.target) / (len(files) - 1)
        if not 1.0 <= crossfade <= 4.0:
            raise SystemExit(f'crossfade {crossfade:.2f} s needed for {a.target} s is outside 1-4 s: add or remove tracks')
    master = f'{a.out}/album.mp3'
    join(files, master, crossfade, a.fade_in, a.curve_out, a.curve_in, a.entry_db, a.entry_s)
    flow = flow_check(master, bounds_of(files, crossfade), cfg['flow'])
    t = 0.0
    for r in report:
        r['start_s'] = round(t, 2)
        t += r['seconds'] - crossfade
    json.dump({'vibe': a.vibe, 'crossfade_s': round(crossfade, 3), 'seconds': round(duration(master), 2), 'tracks': report,
               'key_steps_over_1': sum(r['step_from_prev'] > 1 for r in report), 'flow': flow}, open(f'{a.out}/album.json', 'w'), indent=1)
    print(json.dumps({k: v for k, v in flow.items() if k != 'edges'}))


def check(a, cfg):
    rows = json.load(open(a.tracks))
    bounds, t = [], 0.0
    for r in rows[:-1]:
        t += r['seconds'] - a.crossfade
        bounds.append(t + a.crossfade / 2)
    flow = flow_check(a.audio, bounds, cfg['flow'])
    print(json.dumps(flow, indent=1))


def main():
    ap = argparse.ArgumentParser(description='render an album section in allowed keys with no key lift, join it, and run the flow check')
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('render', help='render each song of a pool once in its key; pool json = [{"slug", "key", "tier"}]; writes OUT/songs/index.json with edge stats')
    r.add_argument('vibes_json')
    r.add_argument('pool')
    r.add_argument('--vibe', default='snowglobe')
    r.add_argument('--out', required=True)
    r.add_argument('--force', action='store_true', help='re-render songs that already exist')
    o = sub.add_parser('rounds', help='order the rendered pool into reshuffled rounds (VIBES.json rounds) with the smallest edge changes')
    o.add_argument('vibes_json')
    o.add_argument('order_out')
    o.add_argument('--out', required=True, help='folder holding songs/index.json')
    o.add_argument('--target', type=float, help='keep adding tracks until the album reaches this many seconds (rounds count ignored)')
    o.add_argument('--crossfade', type=float, default=2.0)
    o.add_argument('--trials', type=int, default=300)
    o.add_argument('--seed', type=int, default=1)
    p = sub.add_parser('album', help='order json = [{"slug": ..., "key": "G"}, ...]; a song repeated in the order is rendered once')
    p.add_argument('vibes_json')
    p.add_argument('order')
    p.add_argument('--vibe', default='snowglobe')
    p.add_argument('--out', required=True)
    p.add_argument('--crossfade', type=float, default=2.0)
    p.add_argument('--target', type=float, help='solve the crossfade (1-4 s) so the master lasts exactly this many seconds')
    p.add_argument('--fade-in', type=float, default=12.0)
    p.add_argument('--curve-out', default='qsin', help='ffmpeg acrossfade curve of the ending track')
    p.add_argument('--curve-in', default='qsin', help='ffmpeg acrossfade curve of the starting track')
    p.add_argument('--entry-db', type=float, default=-6.0, help='each later track starts this many dB down')
    p.add_argument('--entry-s', type=float, default=12.0, help='seconds for that entry ramp to reach full level')
    p.add_argument('--force', action='store_true', help='re-render tracks that already exist')
    c = sub.add_parser('check', help='flow check an already joined file; tracks json = [{"seconds": ...}, ...]')
    c.add_argument('vibes_json')
    c.add_argument('audio')
    c.add_argument('tracks')
    c.add_argument('--crossfade', type=float, default=2.0)
    a = ap.parse_args()
    cfg = json.load(open(a.vibes_json))
    {'album': album, 'check': check, 'render': render, 'rounds': rounds}[a.cmd](a, cfg)


if __name__ == '__main__':
    main()

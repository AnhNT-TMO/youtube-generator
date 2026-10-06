import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import plan_io

REPO = plan_io.repo_root()
CAROLS = REPO / 'research' / 'christmas-carols'
STD = plan_io.PIPELINE['plan_standard']
WORKDIR = REPO / plan_io.PIPELINE['workdirs']
PC = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11, 'E#': 5, 'B#': 0, 'Cb': 11, 'Fb': 4}
QUALITY = plan_io.CHORD_QUALITY
MAJOR = [0, 2, 4, 5, 7, 9, 11]
MINOR = [0, 2, 3, 5, 7, 8, 10]
MODAL = {
    'dorian': [0, 2, 3, 5, 7, 9, 10],
    'aeolian': MINOR,
    'mixolydian': [0, 2, 4, 5, 7, 9, 10],
}
EPS = 1e-6


def parse(name):
    head = name.split('/')[0]
    root = head[:2] if len(head) > 1 and head[1] in '#b' else head[:1]
    return PC[root], head[len(root):]


def tones(name):
    r, q = parse(name)
    return {(r + i) % 12 for i in QUALITY[q]}


def colors(name):
    r, q = parse(name)
    out = set()
    if not q.startswith('m') and q != 'dim':
        out.add((r + 2) % 12)
    if q == '':
        out.add((r + 9) % 12)
    return out


def sounding(events, a, b):
    return [m for m in events if m['beat'] < b - EPS and m['beat'] + m['duration'] > a + EPS]


def statement_mode(song, statement):
    return statement.get('mode', song.get('mode', 'major'))


def key_shift(song, statement):
    explicit = statement.get('transpose_semitones')
    if explicit is not None:
        return int(explicit)
    tr = (PC[statement['key']] - PC[song['file_tonic']]) % 12
    return tr - 12 if tr > 6 else tr


rows = []


def add(slug, style, check, ok, detail):
    rows.append((slug, style, check, 'PASS' if ok is True else ('FAIL' if ok is False else ok), detail))


def check_song(song, revision):
    slug = song['slug']
    root = WORKDIR / slug
    plan = json.loads((root / f'{revision}-pm/arrangement-plan.json').read_text())
    tracks = {s: json.loads((root / s / revision / 'track-plan.json').read_text()) for s in plan_io.styles_for(root, revision)}
    fix = plan.get('source_fix')
    mel = json.loads((CAROLS / song['melody']).read_text())
    notes, t = [], 0.0
    for p, d in mel['melody']:
        notes.append((t, p, d))
        t += d
    sections = {s['section']: s for s in plan['sections']}
    harmony = plan['phrase_harmony']
    bpm = song['bpm']
    spb = 60.0 / bpm

    def chord_at(beat):
        for h in harmony:
            if h['start_beat'] - EPS <= beat < h['end_beat'] - EPS:
                return h
        return None

    base = [e for e in next(iter(tracks.values()))['note_plan']['events'] if e['part'] in ('melody', 'left_hand', 'pad')]
    same = all([e for e in tracks[s]['note_plan']['events'] if e['part'] in ('melody', 'left_hand', 'pad')] == base for s in tracks) and base == plan['non_support_events']
    add(slug, 'all', f'piano + pad identical in {len(tracks)} style(s) and the PM plan', same, f'{len(base)} non-support notes')

    melody = [e for e in base if e['part'] == 'melody']
    pivot_spans = [(h['start_beat'], h['end_beat']) for h in harmony if h.get('pivot')]
    acc_clash, piv_clash = [], []
    for e in base:
        if e['part'] not in ('pad', 'left_hand') or e.get('voice') == 'bass':
            continue
        a, b = e['beat'], e['beat'] + e['duration']
        for m in sounding(melody, a, b):
            ov = min(b, m['beat'] + m['duration']) - max(a, m['beat'])
            if ov >= min(1.5, 0.5 * e['duration']) - EPS and (e['pitch'] - m['pitch']) % 12 in (1, 11):
                where = piv_clash if any(pa - EPS <= max(a, m['beat']) < pb - EPS for pa, pb in pivot_spans) else acc_clash
                where.append(f'{e["note_id"]}@{e["beat"]} {e["pitch"]} vs {m["note_id"]} {m["pitch"]}')
                break
    add(slug, 'all', 'pad/LH dyad no semitone vs held melody (outside pivot)', not acc_clash, '; '.join(acc_clash[:4]) + (f' (+{len(acc_clash) - 4})' if len(acc_clash) > 4 else ''))
    add(slug, 'all', 'pivot leading-tone vs held old tonic (Deck beat 63 model)', 'INFO', '; '.join(piv_clash) or 'none')
    stmt_ids = [s['id'] for s in song['statements']]
    sub_of = {s['id']: s['statement'] for s in song.get('subsections', [])}
    missing_total, detail = 0, []
    for st in song['statements']:
        row = sections[st['id']]
        offset = row['pickup_start'] - st['file'][0]
        tr = key_shift(song, st)
        expected = Counter((round(ft + offset, 3), p + tr, d) for ft, p, d in notes if st['file'][0] - EPS <= ft < st['file'][1] - EPS and p != 0)
        onsets = {e['beat'] for e in melody}
        file_durations = {(round(ft + offset, 3), p + tr): d for ft, p, d in notes if st['file'][0] - EPS <= ft < st['file'][1] - EPS and p != 0}
        got = Counter((e['beat'], e['pitch'], file_durations.get((e['beat'], e['pitch']), e['duration'])
                       if e['duration'] < file_durations.get((e['beat'], e['pitch']), 0) and round(e['beat'] + e['duration'], 3) in onsets else e['duration'])
                      for e in melody if e['section'] == st['id'] or sub_of.get(e['section']) == st['id'])
        miss = sum((expected - got).values())
        extra = sum((got - expected).values())
        missing_total += miss + extra
        detail.append(f'{st["id"]} {sum(got.values())}/{sum(expected.values())}')
    add(slug, 'all', 'every melody note in every statement', missing_total == 0, ', '.join(detail))

    kd = []
    ok = True
    chromatic = False
    for st in song['statements']:
        tr = key_shift(song, st)
        planned = plan['keys'][st['id']]
        evs = [e for e in melody if e['section'] == st['id'] or sub_of.get(e['section']) == st['id']]
        mode = statement_mode(song, st)
        scale = MODAL.get(mode, MAJOR if mode == 'major' else MINOR)
        if mode == 'minor':
            scale = sorted(set(scale) | {9, 11})
        inside = sum((e['pitch'] - PC[st['key']]) % 12 in scale for e in evs) / len(evs)
        row_t = sections[st['id']]['transpose_semitones']
        good = planned == f'{st["key"]} {mode}' and row_t == tr and inside >= 0.8
        ok &= good
        chromatic = chromatic or inside < 0.9
        kd.append(f'{st["id"]} {planned} ({row_t:+d}, {inside:.0%} in scale)')
    add(slug, 'all', 'key of each statement = brief', 'WARN' if ok and chromatic else ok, ('chromatic melody 80-90% in scale; ' if ok and chromatic else '') + ', '.join(kd))

    last = stmt_ids[-1]
    top = max(e['pitch'] for e in melody if e['section'] == last or sub_of.get(e['section']) == last)
    add(slug, 'all', 'final statement melody top <= 83', top <= STD['max_final_melody_pitch'], f'top {top}')

    pv = []
    ok = True
    for st in song['statements'][1:]:
        row = sections[st['id']]
        edge = row['start_beat'] if row['pickup_start'] < row['start_beat'] - EPS else row['pickup_start']
        prior = song['statements'][song['statements'].index(st) - 1]
        if prior.get('key') == st.get('key') and statement_mode(song, prior) == statement_mode(song, st):
            good = True
            h = None
        else:
            h = chord_at(edge - 0.01)
            r, q = parse(h['chord'])
            mode = statement_mode(song, st)
            expected_roots = {(PC[st['key']] + 7) % 12}
            if mode in ('dorian', 'aeolian'):
                expected_roots.add((PC[st['key']] + 11) % 12)
            good = r in expected_roots and q in ('7', '')
        ok &= good
        detail = 'same key' if h is None else f'{h["start_beat"]}-{h["end_beat"]}: {h["chord"]}'
        pv.append(f'before {st["id"]}: {detail}')
    add(slug, 'all', 'dominant pivot of the new key before each lift', ok, '; '.join(pv))

    align = []
    ok = True
    first = sections[stmt_ids[0]]['downbeat']
    for sid in stmt_ids:
        off = (sections[sid]['downbeat'] - first) / song['bar']
        good = abs(off - round(off)) < EPS
        ok &= good
        align.append(f'{sid} downbeat {sections[sid]["downbeat"]} = bar {off:g}')
    add(slug, 'all', 'statement downbeats on the bar grid (meter kept)', ok, '; '.join(align))

    length_s = plan['length']['seconds']
    frac = plan['chime']['fraction']
    lo, hi = STD['chime_fraction_window']
    add(slug, 'all', 'length + chime fraction in window', lo <= frac <= hi, f'{plan["length"]["beats"]} beats = {length_s:.1f} s ({int(length_s // 60)}:{length_s % 60:04.1f}); chime beat {plan["chime"]["beat"]} = {plan["chime"]["seconds"]:.2f} s, fraction {frac:.3f}')

    if 'plain' in tracks:
        plain_cap = tracks['plain']['render']['ace_step']['caption'].lower()
        add(slug, 'plain', 'caption without decorative instrument', not any(w in plain_cap for w in ('celesta', 'vibraphone', 'glockenspiel', 'bell ')), f'{len(plain_cap.split())} words')
        add(slug, 'plain', 'no support notes', not [e for e in tracks['plain']['note_plan']['events'] if e['part'] not in ('melody', 'left_hand', 'pad')], 'base_parts ' + '+'.join(tracks['plain']['base_parts']))
    for style, track in tracks.items():
        words = len(track['render']['ace_step']['caption'].split())
        add(slug, style, 'caption <= 256 tokens (word count x 1.4)', words * 1.4 <= 256, f'{words} words')

    phrase_windows = []
    for st in song['statements']:
        offset = sections[st['id']]['pickup_start'] - st['file'][0]
        for a, b in zip(song['phrases'][:-1], song['phrases'][1:]):
            a2, b2 = max(a, st['file'][0]), min(b, st['file'][1])
            if b2 - a2 > EPS:
                phrase_windows.append((a2 + offset, b2 + offset))

    def phrase_top(beat):
        for a, b in phrase_windows:
            if a - EPS <= beat < b - EPS:
                return max((m['pitch'] for m in melody if m['section'] in stmt_ids + list(sub_of) and m['beat'] < b - EPS and m['beat'] + m['duration'] > a + EPS), default=0)
        return max((m['pitch'] for m in sounding(melody, beat - 4, beat + 4)), default=0)

    chime = plan['chime']['beat']
    for style in [style for style in tracks if style != 'plain']:
        tp = tracks[style]
        sup = [e for e in tp['note_plan']['events'] if e['part'] == style]
        ceiling = STD['ceiling'][style]
        bad_tone, color, bad_reg, bad_clash, bad_chime, bad_hold, bad_ceil, off_grid = [], 0, [], [], [], [], [], []
        for e in sup:
            h = chord_at(e['beat'])
            pc = e['pitch'] % 12
            if pc not in tones(h['chord']):
                if pc in colors(h['chord']):
                    color += 1
                else:
                    bad_tone.append(e['note_id'])
            need = max(phrase_top(e['beat']), max((m['pitch'] for m in sounding(melody, e['beat'], e['beat'] + e['duration'])), default=0)) + STD['support_margin']
            if e['pitch'] < need:
                bad_reg.append(f'{e["note_id"]}@{e["beat"]} {e["pitch"]}<{need}')
            if any((e['pitch'] - m['pitch']) % 12 in (1, 11) for m in sounding(melody, e['beat'], e['beat'] + e['duration'])):
                bad_clash.append(e['note_id'])
            if abs(e['beat'] - chime) < EPS:
                bad_chime.append(e['note_id'])
            for k in harmony:
                if k['start_beat'] > e['beat'] + EPS and k['start_beat'] < e['beat'] + e['duration'] - EPS and pc not in tones(k['chord']):
                    bad_hold.append(f'{e["note_id"]} into {k["chord"]}@{k["start_beat"]}')
            if e['pitch'] > ceiling:
                bad_ceil.append(e['note_id'])
            sec = next(s for s in plan['sections'] if s['start_beat'] - EPS <= e['beat'] < s['end_beat'] - EPS)
            pos = (e['beat'] - sec['downbeat']) / song['slot']
            if abs(pos - round(pos)) > EPS:
                off_grid.append(e['note_id'])
        add(slug, style, 'support chord tones only', not bad_tone, f'{len(sup)} notes; {color} pattern color tones (add9 / added 6th) ' + (f'non-chord {bad_tone[:6]}' if bad_tone else ''))
        add(slug, style, 'support >= phrase top + 3', not bad_reg, '; '.join(bad_reg[:5]) or f'min margin ok')
        add(slug, style, 'no semitone against melody', not bad_clash, ', '.join(bad_clash[:6]))
        add(slug, style, 'no onset on chime beat', not bad_chime, f'chime beat {chime}')
        add(slug, style, 'held note not carried into chord lacking it', not bad_hold, '; '.join(bad_hold[:5]))
        add(slug, style, f'ceiling {ceiling}', not bad_ceil, f'max {max(e["pitch"] for e in sup)}')
        add(slug, style, 'onsets on the slot grid', not off_grid, f'slot {song["slot"]} quarter')
        rule = STD['support'][style].get('min_note')
        if rule:
            min_dur = rule['compound_slots'] * song['slot'] if song['slot'] > 1 + EPS else rule['simple_beats']
            short = [f'{e["note_id"]}@{e["beat"]} {e["duration"]}' for e in sup if e['duration'] < min_dur - EPS]
            onsets = sorted({e['beat'] for e in sup})
            tight = [f'{a}->{b}' for a, b in zip(onsets, onsets[1:]) if b - a < min_dur - EPS]
            few = 0 < len(short) + len(tight) <= 3
            add(slug, style, f'every note >= {min_dur} quarter beats, onsets >= {min_dur} apart', 'WARN' if few else (not short and not tight), ('at most 3 short spots; ' if few else '') + ('; '.join(short[:4] + tight[:4]) or f'min duration {min(e["duration"] for e in sup)}'))
        dens = tp['support_pattern']['per_verse']
        parts = []
        ok = True
        near_miss = False
        ranges = dict(song['density'])
        for section_id, section_cfg in song.get('sections', {}).items():
            if section_cfg.get('tier') == 'third':
                ranges[section_id] = STD['support'][style].get('climax_density', ranges.get(section_id, [60, 80])) if style == 'vibraphone' else ranges.get(section_id, [60, 80])
        for sid, rng in ranges.items():
            pct = dens[sid]['density']['percent']
            good = rng[0] <= pct <= rng[1]
            excused = bool(not good and fix and fix['style'] == style and sid == song['statements'][0]['id'])
            near = not good and rng[0] - 10 <= pct <= rng[1] + 10
            near_miss = near_miss or (near and not excused)
            ok &= good or excused or near
            parts.append(f'{sid} {pct}% [{rng[0]}-{rng[1]}]' + ('' if good else (' OUT (source fix)' if excused else ' NEAR' if near else ' OUT')))
        o_pct = dens['O']['density']['percent']
        c_pct = dens[song['climax']]['density']['percent']
        ok &= o_pct < c_pct
        parts.append(f'O {o_pct}% < {song["climax"]} {c_pct}%')
        add(slug, style, 'density per statement in brief range', 'WARN' if ok and near_miss else ok, ('within 10 points of the range; ' if ok and near_miss else '') + '; '.join(parts))
        dropped = Counter(c['reason'].split(' (')[0].split(' rh-')[0] for c in tp['support_pattern']['dropped_by_PM'])
        changed = Counter(c['reason'].split(';')[0].split(' (')[0].split(' rh-')[0] for c in tp['support_pattern']['changed_by_PM'])
        add(slug, style, 'support notes dropped / changed', 'INFO', f'dropped {sum(dropped.values())} {dict(dropped)}; changed {sum(changed.values())} {dict(changed)}')


def main():
    global WORKDIR
    parser = argparse.ArgumentParser(description='Check plans written by make_plan.py against the standard; exit 1 on any FAIL')
    parser.add_argument('batch')
    parser.add_argument('slugs', nargs='*')
    parser.add_argument('--revision', default=plan_io.PIPELINE['default_revision'])
    parser.add_argument('--workdir')
    args = parser.parse_args()
    if args.workdir:
        WORKDIR = Path(args.workdir).resolve()
    config = json.loads((REPO / plan_io.PIPELINE['batches'] / args.batch / 'songs.json').read_text())
    for song in config['songs']:
        if (not args.slugs or song['slug'] in args.slugs) and (WORKDIR / song['slug'] / f'{args.revision}-pm').is_dir():
            check_song(song, args.revision)
    if not rows:
        print(f'no {args.revision}-pm plans found for {args.batch}')
        return 1
    w = [max(len(str(r[i])) for r in rows) for i in range(4)]
    for r in rows:
        print(f'{r[0]:<{w[0]}}  {r[1]:<{w[1]}}  {r[2]:<{w[2]}}  {r[3]:<4}  {r[4]}')
    fails = [r for r in rows if r[3] == 'FAIL']
    print(f'\n{len(rows)} checks, {len(fails)} FAIL')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())

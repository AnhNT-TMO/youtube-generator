import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

import plan_io

HERE = Path(__file__).resolve().parent
REPO = plan_io.repo_root()
CAROLS = REPO / 'research' / 'christmas-carols'
STD = plan_io.PIPELINE['plan_standard']
TEMPO = json.loads((REPO / plan_io.CONFIG['paths']['tempo_overrides']).read_text())
CONFIG = None
BATCH_FILE = None

PC = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11, 'E#': 5, 'B#': 0, 'Cb': 11, 'Fb': 4}
SHARP_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
FLAT_NAMES = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
FLAT_KEYS = {'F', 'Bb', 'Eb', 'Ab', 'Db', 'Gb'}
QUALITY = plan_io.CHORD_QUALITY
STYLES = plan_io.STYLE_ORDER
SUPPORT_STYLES = [style for style in STYLES if plan_io.CONFIG['arrangement_contract']['styles'][style]['support']]
EPS = 1e-6


def parse_chord(name):
    head, _, bass = name.partition('/')
    root = head[:2] if len(head) > 1 and head[1] in '#b' else head[:1]
    quality = head[len(root):]
    if quality not in QUALITY:
        raise SystemExit(f'unknown chord quality in {name}')
    return PC[root], quality, (PC[bass] if bass else None)


def chord_name(root, quality, bass, key):
    names = FLAT_NAMES if key in FLAT_KEYS else SHARP_NAMES
    text = names[root % 12] + quality
    if bass is not None and bass % 12 != root % 12:
        text += '/' + names[bass % 12]
    return text


def transpose_chord(name, semis, key):
    root, quality, bass = parse_chord(name)
    return chord_name(root + semis, quality, None if bass is None else bass + semis, key)


def chord_pcs(name):
    root, quality, _ = parse_chord(name)
    return {(root + i) % 12 for i in QUALITY[quality]}


def is_minor(name):
    return parse_chord(name)[1] in plan_io.MINOR_QUALITIES


def is_seventh(name):
    return '7' in parse_chord(name)[1]


def degree_offset(degree, name):
    root, quality, _ = parse_chord(name)
    third = QUALITY[quality][1]
    fifth = QUALITY[quality][2]
    seventh = 11 if quality == 'maj7' or '7' not in quality else 10
    table = {1: 0, 2: 2, 3: third, 5: fifth, 6: 9, 7: seventh, 8: 12, 9: 14, 10: 12 + third}
    return table[degree]


def substitute_degree(degree, name):
    if degree in (2, 9) and is_minor(name):
        return 5, f'add{degree} on minor chord {name} -> degree 5'
    if degree == 6 and (is_minor(name) or is_seventh(name)):
        return 8, f'added 6th on {name} -> degree 8'
    if degree == 7 and not is_seventh(name):
        return 8, f'degree 7 on triad {name} -> degree 8'
    return degree, None


def key_transpose(file_tonic, key):
    t = (PC[key] - PC[file_tonic]) % 12
    return t - 12 if t > 6 else t


def statement_mode(song, statement):
    return statement.get('mode', song.get('mode', 'major'))


def key_text(key, mode):
    return f'{key} {mode}'


def key_shift(song, statement):
    explicit = statement.get('transpose_semitones')
    return int(explicit) if explicit is not None else key_transpose(song['file_tonic'], statement['key'])


def tonic_chord(key, mode):
    return chord_name(PC[key], 'm' if mode in ('minor', 'aeolian', 'dorian') else '', None, key)


def interlude_chord(func, key, mode):
    if func == 'I':
        return tonic_chord(key, mode)
    if func in ('V', 'V7'):
        return chord_name(PC[key] + 7, '7', None, key)
    if func in ('VII', 'VII7'):
        return chord_name(PC[key] + 11, '7' if func.endswith('7') else '', None, key)
    raise SystemExit(f'unknown interlude function {func}')


def r3(x):
    return round(x + 0.0, 3)


def resolve_same_pitch(events):
    kept = []
    last = {}
    for e in sorted(events, key=lambda e: (e['beat'], -e['duration'], e['channel'], e['pitch'])):
        key = (e['channel'], e['pitch'])
        prev = last.get(key)
        if prev is not None and abs(prev['beat'] - e['beat']) < EPS:
            continue
        if prev is not None and prev['beat'] + prev['duration'] > e['beat'] + EPS:
            prev['duration'] = r3(e['beat'] - prev['beat'])
        kept.append(e)
        last[key] = e
    kept.sort(key=lambda e: (e['beat'], e['channel'], e['pitch']))
    return kept


def build_song(song, fix=None):
    melody_path = CAROLS / song['melody']
    mel = json.loads(melody_path.read_text())
    bpm = song['bpm']
    bar = song['bar']
    slot = song['slot']
    sec_per_beat = 60.0 / bpm
    statements = {s['id']: s for s in song['statements']}
    def group_id(sid):
        st = statements.get(sid, {})
        return st.get('group') or st.get('group_id') or st.get('base') or sid

    def section_config(sid):
        return song['sections'].get(sid) or song['sections'].get(group_id(sid))

    def pattern_config(style, sid):
        patterns = song['patterns'][style]
        return patterns.get(sid) or patterns.get(group_id(sid))
    trans = {sid: key_shift(song, s) for sid, s in statements.items()}
    base_t = trans[song['statements'][0]['id']]
    shift = {sid: t - base_t for sid, t in trans.items()}

    notes, t = [], 0.0
    for p, d in mel['melody']:
        notes.append((t, p, d))
        t += d
    chords, t = [], 0.0
    for c, d in mel['chords']:
        chords.append((t, t + d, c))
        t += d

    sections = []
    cursor = 0.0
    offsets = {}
    for item in song['form']:
        if item in statements:
            st = statements[item]
            fs, fe = st['file']
            overlap = (st['downbeat'] - fs) if st.get('pickup_in_previous') else 0
            place_start = cursor - overlap
            offset = place_start - fs
            offsets[item] = offset
            start = cursor
            end = place_start + (fe - fs)
            anchor = st['downbeat'] + offset
            subs = [s for s in song.get('subsections', []) if s['statement'] == item]
            cuts = [start] + [s['file_start'] + offset for s in subs] + [end]
            ids = [item] + [s['id'] for s in subs]
            for k, sid in enumerate(ids):
                sections.append({'id': sid, 'kind': 'statement', 'statement': item, 'start': cuts[k], 'end': cuts[k + 1], 'anchor': anchor, 'key': st['key'], 'transpose': trans[item], 'shift': shift[item], 'pickup_start': place_start if k == 0 else cuts[k]})
            cursor = end
        elif item == 'R':
            sections.append({'id': 'R', 'kind': 'interlude', 'start': cursor, 'end': cursor + song['interlude']['beats'], 'anchor': cursor})
            cursor += song['interlude']['beats']
        elif item == 'O':
            sections.append({'id': 'O', 'kind': 'outro', 'start': cursor, 'end': cursor + song['outro']['beats'], 'anchor': cursor})
            cursor += song['outro']['beats']
    total = cursor
    last_stmt = song['statements'][-1]['id']

    def section_at(beat):
        for s in sections:
            if s['start'] - EPS <= beat < s['end'] - EPS:
                return s
        return sections[-1]

    melody = []
    for sid, st in statements.items():
        fs, fe = st['file']
        offset = offsets[sid]
        subs = sorted([s for s in song.get('subsections', []) if s['statement'] == sid], key=lambda s: s['file_start'])
        sec_cfg = song['sections']
        for (ft, p, d) in notes:
            if not (fs - EPS <= ft < fe - EPS) or p == 0:
                continue
            beat = ft + offset
            label = sid
            for s in subs:
                if ft >= s['file_start'] - EPS:
                    label = s['id']
            anchor = st['downbeat'] + offset
            bar_idx = math.floor((beat - anchor) / bar + EPS)
            vel = STD['rh']['base_vel'] + STD['rh']['bar_contour'][bar_idx % 4] + (section_config(label) or {'vel': 0})['vel']
            melody.append({'beat': r3(beat), 'pitch': p + trans[sid], 'duration': d, 'velocity': vel, 'channel': STD['channel']['melody'], 'part': 'melody', 'section': label, 'file_beat': ft})
    melody.sort(key=lambda e: e['beat'])
    for prev_note, next_note in zip(melody, melody[1:]):
        if prev_note['beat'] + prev_note['duration'] > next_note['beat'] + EPS:
            prev_note['duration'] = r3(next_note['beat'] - prev_note['beat'])

    harmony = []
    for s in sections:
        if s['kind'] != 'statement' or s['id'] != s['statement']:
            continue
        sid = s['id']
        st = statements[sid]
        fs, fe = st['file']
        offset = offsets[sid]
        lo = s['start'] - offset
        for (a, b, c) in chords:
            a2, b2 = max(a, lo, fs), min(b, fe)
            if b2 - a2 <= EPS:
                continue
            harmony.append({'start_beat': r3(a2 + offset), 'end_beat': r3(b2 + offset), 'chord': transpose_chord(c, trans[sid], st['key']), 'section': section_at(a2 + offset)['id'], 'transpose_semitones': trans[sid], 'shift': shift[sid]})
    pivots = []
    pivot_specs = song.get('pivots')
    if pivot_specs is None and song.get('pivot'):
        pivot_specs = [song['pivot']]
    for pivot_spec in pivot_specs or []:
        target = pivot_spec['before']
        target_index = next((i for i, item in enumerate(song['form']) if item == target), None)
        previous_ids = [item for item in song['form'][:target_index] if item in statements] if target_index is not None else []
        previous = statements[previous_ids[-1]] if previous_ids else None
        target_statement = statements[target]
        if previous and previous.get('key') == target_statement.get('key') and statement_mode(song, previous) == statement_mode(song, target_statement):
            continue
        tsec = next(s for s in sections if s['id'] == target)
        p_end = tsec['start']
        p_start = tsec['pickup_start'] - pivot_spec['beats']
        target_stmt = statements[target]
        tkey = target_stmt['key']
        tmode = statement_mode(song, target_stmt)
        if statements[target].get('transpose_semitones') is not None:
            target_shift = statements[target]['transpose_semitones']
        else:
            target_shift = trans[target]
        pivot_func = pivot_spec.get('function')
        if pivot_func is None:
            pivot_func = 'V7' if tmode not in ('dorian', 'aeolian', 'mixolydian') else ('V7' if tmode == 'mixolydian' else 'VII')
        v7 = interlude_chord(pivot_func, tkey, tmode)
        new = []
        for h in harmony:
            if h['end_beat'] <= p_start + EPS or h['start_beat'] >= p_end - EPS:
                new.append(h)
                continue
            if h['start_beat'] < p_start - EPS:
                left = dict(h)
                left['end_beat'] = r3(p_start)
                new.append(left)
            if h['end_beat'] > p_end + EPS:
                right = dict(h)
                right['start_beat'] = r3(p_end)
                new.append(right)
            replaced = h['chord']
        prev = next(h for h in harmony if h['start_beat'] < p_end - EPS and h['end_beat'] > p_start + EPS)
        new.append({'start_beat': r3(p_start), 'end_beat': r3(p_end), 'chord': v7, 'section': prev['section'], 'transpose_semitones': trans[target], 'shift': shift[target], 'pivot': True})
        harmony = sorted(new, key=lambda h: h['start_beat'])
        pivots.append({'beat': r3(p_start), 'end_beat': r3(p_end), 'chord': f'{v7} ({pivot_func} of {key_text(tkey, tmode)})', 'replaces': replaced, 'note': 'pivot on the last beat before the key change'})
    for s in sections:
        if s['kind'] == 'interlude':
            b = s['start']
            for func, ref, beats in song['interlude']['chords']:
                key = statements[ref]['key']
                mode = statement_mode(song, statements[ref])
                c = interlude_chord(func, key, mode)
                harmony.append({'start_beat': r3(b), 'end_beat': r3(b + beats), 'chord': c, 'section': 'R', 'transpose_semitones': trans[ref], 'shift': shift[ref], 'function': f'{func} of {key_text(key, mode)}'})
                if func in ('V', 'V7', 'VII', 'VII7'):
                    pivots.append({'beat': r3(b), 'end_beat': r3(b + beats), 'chord': f'{c} ({func} of {key_text(key, mode)})', 'note': 'interlude dominant before the lifted statement'})
                b += beats
        if s['kind'] == 'outro':
            key = statements[last_stmt]['key']
            mode = statement_mode(song, statements[last_stmt])
            harmony.append({'start_beat': r3(s['start']), 'end_beat': r3(s['end']), 'chord': tonic_chord(key, mode), 'section': 'O', 'transpose_semitones': trans[last_stmt], 'shift': shift[last_stmt], 'function': f'I of {key_text(key, mode)}'})
    harmony.sort(key=lambda h: h['start_beat'])

    def chord_span_at(beat):
        for h in harmony:
            if h['start_beat'] - EPS <= beat < h['end_beat'] - EPS:
                return h
        raise SystemExit(f'{song["slug"]}: no harmony at beat {beat}')

    rh_extra = []
    for s in sections:
        if s['kind'] == 'interlude':
            prev_stmt = [m for m in melody if m['beat'] < s['start'] - EPS]
            next_stmt = [m for m in melody if m['beat'] >= s['start'] - EPS]
            for h in [h for h in harmony if h['section'] == 'R']:
                if any(m['beat'] < h['end_beat'] - EPS and m['beat'] + m['duration'] > h['start_beat'] + EPS for m in melody):
                    continue
                if h['function'].startswith('I '):
                    pitch = prev_stmt[-1]['pitch']
                else:
                    target = next_stmt[0]['pitch']
                    pcs = chord_pcs(h['chord'])
                    pitch = min((p for p in range(target - 12, target + 13) if p % 12 in pcs), key=lambda p: (abs(p - target), p))
                rh_extra.append({'beat': h['start_beat'], 'pitch': pitch, 'duration': r3(STD['rh']['interlude_ratio'] * (h['end_beat'] - h['start_beat'])), 'velocity': STD['rh']['interlude_vel'], 'channel': STD['channel']['melody'], 'part': 'melody', 'section': 'R'})
        if s['kind'] == 'outro':
            last = [m for m in melody if m['beat'] < s['start'] - EPS][-1]
            rh_extra.append({'beat': r3(s['start']), 'pitch': last['pitch'], 'duration': r3(s['end'] - s['start'] - STD['rh']['outro_release']), 'velocity': STD['rh']['outro_vel'], 'channel': STD['channel']['melody'], 'part': 'melody', 'section': 'O'})
    piano_rh = sorted(melody + rh_extra, key=lambda e: e['beat'])

    def sounding(start, end, events=None):
        return [m for m in (events or piano_rh) if m['beat'] < end - EPS and m['beat'] + m['duration'] > start + EPS]

    def long_melody(a, b):
        span = b - a
        return [m['pitch'] for m in sounding(a, b) if min(b, m['beat'] + m['duration']) - max(a, m['beat']) >= min(1.5, 0.5 * span) - EPS]

    texture = {sid: cfg['texture'] for sid, cfg in song['sections'].items()}
    for sid in statements:
        if sid not in texture and group_id(sid) in texture:
            texture[sid] = texture[group_id(sid)]
    texture['R'] = 'interlude'
    texture['O'] = 'outro'
    lh_cfg = STD['lh']
    lh = []
    for s in sections:
        spans = [dict(h) for h in harmony if s['start'] - EPS <= h['start_beat'] < s['end'] - EPS]
        merged = []
        for h in spans:
            if merged and merged[-1]['chord'] == h['chord'] and abs(merged[-1]['end_beat'] - h['start_beat']) < EPS:
                merged[-1]['end_beat'] = h['end_beat']
            else:
                merged.append(h)
        pieces = []
        for h in merged:
            parts = [(h['start_beat'], h['end_beat'])]
            for unit in (bar, bar / 2):
                nxt = []
                for a, b in parts:
                    if b - a <= lh_cfg['split_over'] + EPS:
                        nxt.append((a, b))
                        continue
                    k = math.floor((a - s['anchor']) / unit + EPS) + 1
                    cut = s['anchor'] + k * unit
                    marks = [a]
                    while cut < b - EPS:
                        marks.append(cut)
                        cut += unit
                    marks.append(b)
                    nxt += list(zip(marks[:-1], marks[1:]))
                parts = nxt
            for a, b in parts:
                pieces.append({'start_beat': a, 'end_beat': b, 'chord': h['chord'], 'shift': h['shift'], 'length': h['end_beat'] - h['start_beat'], 'pivot': h.get('pivot', False)})
        tex = texture[s['id']]
        cfg = lh_cfg['bass_led'] if tex == 'bass_led' else lh_cfg[tex]
        for i, pc_ in enumerate(pieces):
            if tex == 'outro' and i > 0:
                break
            a, b = pc_['start_beat'], pc_['end_beat']
            if tex == 'outro':
                b = s['end']
            L = b - a
            root, quality, bass_pc = parse_chord(pc_['chord'])
            bpc = (bass_pc if bass_pc is not None else root) % 12
            sh = pc_['shift']
            blo, bhi = lh_cfg['bass_range']
            bass_pitch = next(p for p in range(blo + sh, bhi + sh) if p % 12 == bpc)
            third = (root + QUALITY[quality][1]) % 12
            fifth = (root + 7) % 12
            dlo, dhi = lh_cfg['dyad_range']
            low_mel = min((m['pitch'] for m in sounding(a, b)), default=999)
            held_mel = [] if pc_.get('pivot') else long_melody(a, b)
            dyad = []
            for pcx in (third, fifth):
                d = next(p for p in range(dlo + sh, dhi + sh) if p % 12 == pcx)
                if d >= low_mel:
                    d -= 12
                    if d <= bass_pitch + 3:
                        continue
                if any((d - m) % 12 in (1, 11) for m in held_mel):
                    continue
                dyad.append(d)
            bass_dur = min(lh_cfg['bass_ratio'] * L, lh_cfg['bass_cap'])
            lh.append({'beat': r3(a), 'pitch': bass_pitch, 'duration': r3(bass_dur), 'velocity': cfg['vel'][0], 'channel': STD['channel']['left_hand'], 'part': 'left_hand', 'section': section_at(a)['id'], 'chord': pc_['chord'], 'voice': 'bass'})
            if L < lh_cfg['dyad_min_chord'] - EPS:
                continue
            if tex == 'bass_led':
                bar_idx = math.floor((a - s['anchor']) / bar + EPS)
                first_of_phrase = abs((a - s['anchor']) - bar_idx * bar) < EPS and bar_idx % cfg['phrase_bars'] == 0
                if not (first_of_phrase or pc_['length'] >= cfg['long'] - EPS):
                    continue
            for d, off in zip(dyad, cfg['offsets'] if len(dyad) == 2 else cfg['offsets'][:len(dyad)]):
                lh.append({'beat': r3(a + off), 'pitch': d, 'duration': r3(min(L - off, lh_cfg['dyad_cap'])), 'velocity': cfg['vel'][1], 'channel': STD['channel']['left_hand'], 'part': 'left_hand', 'section': section_at(a)['id'], 'chord': pc_['chord'], 'voice': 'dyad'})

    pad = []
    accompaniment_changes = []
    pad_cfg = STD['pad']
    prev_pitches = [None, None, None]
    for s in sections:
        spans = [h for h in harmony if s['start'] - EPS <= h['start_beat'] < s['end'] - EPS]
        open_ev = [None, None, None]
        for h in spans:
            root, quality, _ = parse_chord(h['chord'])
            pcs = [(root + i) % 12 for i in QUALITY[quality]]
            prefer = [pcs[0], pcs[1], pcs[2]]
            used = set()
            chosen = [None, None, None]
            for v, (lo, hi) in enumerate(pad_cfg['ranges']):
                lo, hi = lo + h['shift'], hi + h['shift']
                cur = open_ev[v]['pitch'] if open_ev[v] else prev_pitches[v]
                held_mel = [] if h.get('pivot') else [m['pitch'] for m in sounding(h['start_beat'], h['end_beat'], melody)]
                in_range = [p for p in range(lo, hi) if p % 12 in pcs and not any((p - m) % 12 in (1, 11) for m in held_mel)]
                if not in_range:
                    pad_lo = min(r[0] for r in pad_cfg['ranges']) + h['shift']
                    pad_hi = max(r[1] for r in pad_cfg['ranges']) + h['shift']
                    in_range = [p for p in range(pad_lo, pad_hi) if p % 12 in pcs and not any((p - m) % 12 in (1, 11) for m in held_mel)]
                    if not in_range:
                        raise SystemExit(f'{song["slug"]}: no safe pad chord tone at beat {h["start_beat"]} on {h["chord"]}')
                    accompaniment_changes.append({'part': 'pad', 'beat': h['start_beat'], 'voice': v, 'chord': h['chord'], 'reason': f'no safe chord tone in voice range {lo}-{hi - 1}; revoice within pad register {pad_lo}-{pad_hi - 1}'})
                allowed = [p for p in in_range if v == 0 or p % 12 not in used] or in_range
                if cur is not None and cur in allowed:
                    pick = cur
                elif cur is not None:
                    pick = min(allowed, key=lambda p: (abs(p - cur), p))
                else:
                    pref = [p for p in allowed if p % 12 == prefer[v]]
                    pick = (pref or allowed)[0]
                chosen[v] = pick
                if accompaniment_changes and accompaniment_changes[-1]['beat'] == h['start_beat'] and accompaniment_changes[-1]['voice'] == v:
                    accompaniment_changes[-1]['pitch'] = pick
                used.add(pick % 12)
            for v in range(3):
                ev = open_ev[v]
                if ev and ev['pitch'] == chosen[v]:
                    ev['end'] = h['end_beat']
                    continue
                if ev:
                    pad.append(ev)
                open_ev[v] = {'beat': h['start_beat'], 'pitch': chosen[v], 'end': h['end_beat'], 'section': s['id']}
        for v in range(3):
            if open_ev[v]:
                pad.append(open_ev[v])
                prev_pitches[v] = open_ev[v]['pitch']
    pad = [{'beat': r3(e['beat']), 'pitch': e['pitch'], 'duration': r3(e['end'] - e['beat']), 'velocity': pad_cfg['vel'], 'channel': STD['channel']['pad'], 'part': 'pad', 'section': e['section']} for e in sorted(pad, key=lambda e: (e['beat'], e['pitch']))]
    for e in pad:
        conflicts = [m for m in sounding(e['beat'], e['beat'] + e['duration']) if (e['pitch'] - m['pitch']) % 12 in (1, 11)]
        if not conflicts:
            continue
        h = chord_span_at(e['beat'])
        root, quality, _ = parse_chord(h['chord'])
        safe = []
        for degree in (1, 3, 5, 8):
            pitch_class = (root + degree_offset(degree, h['chord'])) % 12
            for pitch in range(50 + h['shift'], 72 + h['shift']):
                if pitch % 12 == pitch_class and not any((pitch - m['pitch']) % 12 in (1, 11) for m in sounding(e['beat'], e['beat'] + e['duration'])):
                    safe.append(pitch)
        if safe:
            old = e['pitch']
            e['pitch'] = min(safe, key=lambda p: abs(p - old))
            accompaniment_changes.append({'part': 'pad', 'beat': e['beat'], 'pitch': e['pitch'], 'reason': f'revoiced after melody semitone at {old}'})
        else:
            cut = min(m['beat'] for m in conflicts)
            if cut - e['beat'] >= 0.25:
                e['duration'] = r3(cut - e['beat'])
                accompaniment_changes.append({'part': 'pad', 'beat': e['beat'], 'reason': 'shortened before melody semitone'})
            else:
                e['duration'] = 0
                accompaniment_changes.append({'part': 'pad', 'beat': e['beat'], 'reason': 'dropped for melody semitone'})
    pad = [e for e in pad if e['duration'] > EPS]

    phrase_bounds = song['phrases']
    phrase_windows = []
    for sid, st in statements.items():
        offset = offsets[sid]
        for a, b in zip(phrase_bounds[:-1], phrase_bounds[1:]):
            lo, hi = max(a, st['file'][0]), min(b, st['file'][1])
            if hi - lo > EPS:
                phrase_windows.append((lo + offset, hi + offset, sid))

    def phrase_top(beat):
        for a, b, sid in phrase_windows:
            if a - EPS <= beat < b - EPS:
                return max((m['pitch'] for m in sounding(a, b, melody)), default=0)
        return max((m['pitch'] for m in sounding(beat - 4, beat + 4)), default=0)

    def floor_at(beat, dur):
        return max(phrase_top(beat), max((m['pitch'] for m in sounding(beat, beat + dur)), default=0)) + STD['support_margin']

    chime_sec = next(s for s in sections if s['id'] == song['chime_statement'])
    chime_beat = chime_sec['start']

    def grid_points(s):
        pts = []
        k = math.ceil((s['start'] - s['anchor']) / slot - EPS)
        g = s['anchor'] + k * slot
        while g < s['end'] - EPS:
            pts.append(r3(g))
            g += slot
        return pts

    def hold_end(beat, pitch):
        h = chord_span_at(beat)
        end = h['end_beat']
        while end < total - EPS:
            nxt = chord_span_at(end)
            if pitch % 12 in chord_pcs(nxt['chord']):
                end = nxt['end_beat']
            else:
                break
        return end

    def clash(pitch, beat, dur):
        for m in sounding(beat, beat + dur):
            if (pitch - m['pitch']) % 12 in (1, 11):
                return m
        return None

    def min_note_beats(style):
        rule = STD['support'][style].get('min_note')
        if not rule:
            return 0
        return rule['compound_slots'] * slot if slot > 1 + EPS else rule['simple_beats']

    def density_bounds(style, sid):
        cfg = section_config(sid) or {}
        if cfg.get('tier') == 'third' and style == 'vibraphone':
            return tuple(STD['support'][style].get('climax_density', (45, 65)))
        return tuple(song.get('density', {}).get(sid, (0, 100)))

    def adapt_density(style, events, changes):
        min_dur = min_note_beats(style)
        cfg = STD['support'][style]
        ceiling = STD['ceiling'][style]
        for sec in sections:
            if sec['kind'] not in ('statement', 'outro'):
                continue
            if sec['kind'] == 'outro':
                climax_sid = song['climax']
                climax_points = grid_points(next(x for x in sections if x['id'] == climax_sid))
                climax_events = {e['beat'] for e in events if e['section'] == climax_sid}
                lo, hi = 0, max(0, 100.0 * len(climax_events) / max(1, len(climax_points)) - 0.1)
                outro_onsets = sorted({e['beat'] for e in events if e['section'] == sec['id']}, reverse=True)
                while 100.0 * len(outro_onsets) / max(1, len(grid_points(sec))) >= hi and outro_onsets:
                    onset = outro_onsets.pop(0)
                    removed = [e for e in events if e['section'] == sec['id'] and abs(e['beat'] - onset) < EPS]
                    events[:] = [e for e in events if e not in removed]
                    changes.append({'beat': onset, 'kind': 'dropped', 'reason': f'density swap {style} O: outro onset removed to stay below {climax_sid}'})
            else:
                lo, hi = density_bounds(style, sec['id'])
            points = grid_points(sec)
            if not points:
                continue
            in_events = [e for e in events if sec['start'] - EPS <= e['beat'] < sec['end'] - EPS]
            onsets = {e['beat'] for e in in_events}
            target_low = math.ceil(len(points) * lo / 100.0 - EPS)
            target_high = math.floor(len(points) * hi / 100.0 + EPS)
            if len(onsets) > target_high:
                for onset in sorted(onsets, reverse=True):
                    if len(onsets) <= target_high:
                        break
                    removed = [e for e in in_events if abs(e['beat'] - onset) < EPS]
                    events[:] = [e for e in events if e not in removed]
                    in_events = [e for e in in_events if e not in removed]
                    onsets.remove(onset)
                    changes.append({'beat': onset, 'kind': 'dropped', 'reason': f'density swap {style} {sec["id"]}: {len(onsets) + 1}/{len(points)} -> <= {hi}%; removed pattern onset'})
            if len(onsets) >= target_low:
                continue
            existing = set(onsets)
            for beat in points:
                if len(onsets) >= target_low:
                    break
                if beat in existing or abs(beat - chime_beat) < EPS:
                    continue
                if min_dur and any(abs(beat - old) < min_dur - EPS for old in existing):
                    continue
                h = chord_span_at(beat)
                root = parse_chord(h['chord'])[0]
                candidates = []
                for degree in (5, 3, 1, 8):
                    raw = root + degree_offset(degree, h['chord'])
                    floor = floor_at(beat, min_dur or slot)
                    for octave in range(2, 10):
                        pitch = raw + 12 * octave
                        if floor <= pitch <= ceiling and not clash(pitch, beat, min_dur or slot):
                            hold = hold_end(beat, pitch)
                            dur = min(cfg['cap'], hold - beat)
                            if min_dur and dur < min_dur - EPS:
                                continue
                            if clash(pitch, beat, dur):
                                continue
                            candidates.append((pitch, dur, degree))
                if not candidates:
                    continue
                pitch, dur, degree = min(candidates, key=lambda x: x[0])
                events.append({'beat': r3(beat), 'pitch': pitch, 'duration': r3(dur), 'velocity': cfg['vel'][tier_of(sec['id'])], 'channel': STD['channel'][style], 'part': style, 'section': sec['id'], 'chord': h['chord'], 'degree': degree, 'figure': f'density-swap {sec["id"]}'})
                existing.add(beat)
                onsets.add(beat)
                changes.append({'beat': beat, 'kind': 'changed', 'to_degree': degree, 'pitch': pitch, 'reason': f'density swap {style} {sec["id"]}: added same-tier support onset to reach {lo}-{hi}%'})

    def tokens_for(style, s, spec):
        out = []
        per_bar = int(round(bar / slot))
        if spec['mode'] == 'bars':
            k0 = math.ceil((s['start'] - s['anchor']) / bar - EPS)
            tie = STD['support'][style].get('tie_across_bars', False)
            n = 0
            while True:
                bstart = s['anchor'] + (k0 + n) * bar
                if bstart >= s['end'] - EPS:
                    break
                pat = spec['cycle'][n % len(spec['cycle'])]
                if len(pat) != per_bar:
                    if len(pat) < per_bar:
                        repeats = (per_bar + len(pat) - 1) // len(pat)
                        pat = (pat * repeats)[:per_bar]
                    else:
                        pat = pat[:per_bar]
                ahead = pat
                if tie:
                    m = 1
                    while bstart + m * bar < s['end'] - EPS and m <= len(spec['cycle']):
                        ahead += spec['cycle'][(n + m) % len(spec['cycle'])]
                        m += 1
                    ahead += '-' * per_bar
                group = []
                for i, ch in enumerate(pat):
                    if ch == '-':
                        continue
                    span = 1
                    while i + span < len(ahead) and ahead[i + span] == '-':
                        span += 1
                    beat = bstart + i * slot
                    if beat >= s['end'] - EPS:
                        continue
                    span = min(span, (s['end'] - beat) / slot)
                    group.append({'beat': r3(beat), 'degree': int(ch), 'span': span, 'first': i == 0, 'label': f'{spec["id"]} {s["id"]} {pat}'})
                if group:
                    out.append(group)
                n += 1
        elif spec['mode'] == 'fill':
            sec_mel = [m for m in melody if s['start'] - EPS <= m['beat'] < s['end'] - EPS]
            ends = set()
            if spec.get('only_phrase_end'):
                for a, b, sid in phrase_windows:
                    inside = [m for m in sec_mel if a - EPS <= m['beat'] < b - EPS]
                    if inside:
                        ends.add(inside[-1]['beat'])
            w = 0
            for i, m in enumerate(sec_mel):
                nxt = next((x['beat'] for x in melody if x['beat'] > m['beat'] + EPS), s['end'])
                nxt = min(nxt, s['end'])
                if nxt - m['beat'] < spec['min_hold'] - EPS:
                    continue
                if spec.get('only_phrase_end') and m['beat'] not in ends:
                    continue
                start = m['beat'] + spec['offset_slots'] * slot
                k = math.ceil((start - s['anchor']) / slot - EPS)
                g = s['anchor'] + k * slot
                pts = []
                while g < nxt - EPS:
                    pts.append(g)
                    g += slot
                if not pts:
                    continue
                fig = spec['figures'][w % len(spec['figures'])]
                w += 1
                marks = [(j, ch) for j, ch in enumerate(fig) if ch != '-' and j < len(pts)][:spec['max_tokens']]
                while marks and (nxt - pts[marks[-1][0]]) < min_note_beats(style) - EPS:
                    marks.pop()
                if not marks:
                    continue
                group = []
                for q, (j, ch) in enumerate(marks):
                    span = (marks[q + 1][0] - j) if q < len(marks) - 1 else (nxt - pts[j]) / slot
                    group.append({'beat': r3(pts[j]), 'degree': int(ch), 'span': span, 'first': q == 0, 'label': f'{spec["id"]} {s["id"]} answer {fig}'})
                out.append(group)
        elif spec['mode'] == 'per_chord':
            spans = [h for h in harmony if s['start'] - EPS <= h['start_beat'] < s['end'] - EPS]
            spans = [h for h in spans if h['end_beat'] - h['start_beat'] >= min_note_beats(style) - EPS]
            for j, h in enumerate(spans):
                d = spec['degrees'][j % len(spec['degrees'])]
                out.append([{'beat': h['start_beat'], 'degree': d, 'span': (h['end_beat'] - h['start_beat']) / slot, 'first': True, 'label': f'{spec["id"]} {s["id"]} {d} per chord'}])
        elif spec['mode'] == 'held_tones':
            for g in grid_points(s):
                out.append([{'beat': g, 'degree': spec['degrees'][0], 'span': min(spec['step'], (s['end'] - g) / slot), 'first': False, 'candidate': True, 'label': f'{spec["id"]} {s["id"]} held tones every {spec["step"]} slots'}])
        elif spec['mode'] == 'per_bar':
            b = s['start']
            j = 0
            while b < s['end'] - EPS:
                d = spec['degrees'][j % len(spec['degrees'])]
                out.append([{'beat': r3(b), 'degree': d, 'span': min(bar, s['end'] - b) / slot, 'first': True, 'label': f'{spec["id"]} {s["id"]} {d} per bar'}])
                b += bar
                j += 1
        return out

    def tier_of(sid):
        if sid in ('R', 'O'):
            return sid
        cfg = section_config(sid)
        return cfg['tier'] if cfg else 'first'

    def style_plan(style):
        cfg = STD['support'][style]
        ceiling = STD['ceiling'][style]
        min_dur = min_note_beats(style)
        events, changes = [], []
        for s in sections:
            spec = pattern_config(style, s['id'])
            if not spec:
                continue
            next_free, placed_count = -1e9, 0
            for group in tokens_for(style, s, spec):
                candidate = group[0].get('candidate', False)
                if candidate:
                    if group[0]['beat'] < next_free - EPS:
                        continue
                    group = [dict(group[0], degree=spec['degrees'][placed_count % len(spec['degrees'])])]
                    mark_changes, mark_events = len(changes), len(events)
                placed = []
                for tok in group:
                    h = chord_span_at(tok['beat'])
                    deg, why = substitute_degree(tok['degree'], h['chord'])
                    chord_tones = chord_pcs(h['chord'])
                    try:
                        requested_pc = (parse_chord(h['chord'])[0] + degree_offset(deg, h['chord'])) % 12
                    except KeyError:
                        requested_pc = None
                    if requested_pc is not None and requested_pc not in chord_tones:
                        candidates = [d for d in (1, 3, 5, 7, 8, 9, 6, 2) if (parse_chord(h['chord'])[0] + degree_offset(d, h['chord'])) % 12 in chord_tones]
                        if candidates:
                            old = deg
                            deg = min(candidates, key=lambda d: abs(degree_offset(d, h['chord']) - degree_offset(old, h['chord'])))
                            why = f'degree {old} is not a chord tone on {h["chord"]} -> degree {deg}'
                    if why:
                        changes.append({'beat': tok['beat'], 'kind': 'changed', 'from_degree': tok['degree'], 'to_degree': deg, 'reason': why, 'label': tok['label']})
                    span_beats = tok['span'] * slot
                    if span_beats > slot + EPS:
                        dur = min(span_beats - cfg['release'], cfg['cap'])
                    else:
                        dur = cfg['single_ratio'] * slot
                    if min_dur and span_beats < min_dur - EPS:
                        if tok['beat'] + span_beats < s['end'] - EPS:
                            raise SystemExit(f'{song["slug"]} {style} {s["id"]}: {tok["label"]} at beat {tok["beat"]} spans {span_beats} beats, below the {min_dur}-beat minimum')
                        if not tok.get('candidate'):
                            changes.append({'beat': tok['beat'], 'kind': 'dropped', 'degree': tok['degree'], 'reason': f'section {s["id"]} ends {r3(span_beats)} beats later, below the {min_dur}-beat minimum', 'label': tok['label']})
                        continue
                    dur = max(dur, min_dur)
                    root = parse_chord(h['chord'])[0] % 12
                    placed.append(dict(tok, degree=deg, chord=h['chord'], root=root, off=degree_offset(deg, h['chord']), dur=dur, floor=floor_at(tok['beat'], dur)))
                if not placed:
                    continue
                octave = max(math.ceil((p['floor'] - p['root'] - p['off']) / 12) for p in placed)
                for p in placed:
                    pitch = 12 * octave + p['root'] + p['off']
                    beat, dur = p['beat'], p['dur']
                    if abs(beat - chime_beat) < EPS:
                        changes.append({'beat': beat, 'kind': 'dropped', 'degree': p['degree'], 'reason': 'chime beat', 'label': p['label']})
                        continue
                    if pitch > ceiling:
                        if pitch - 12 >= p['floor']:
                            changes.append({'beat': beat, 'kind': 'changed', 'degree': p['degree'], 'pitch': pitch, 'reason': f'above ceiling {ceiling}; octave down', 'label': p['label']})
                            pitch -= 12
                        else:
                            changes.append({'beat': beat, 'kind': 'dropped', 'degree': p['degree'], 'pitch': pitch, 'reason': f'above ceiling {ceiling}', 'label': p['label']})
                            continue
                    held = hold_end(beat, pitch) if pitch % 12 in chord_pcs(p['chord']) else chord_span_at(beat)['end_beat']
                    dur = r3(max(min(dur, held - beat), 0.25))
                    hit = clash(pitch, beat, dur)
                    short = min_dur and dur < min_dur - EPS
                    if short and not hit:
                        hit = {'note_id': 'chord change', 'pitch': f'{p["chord"]} -> {chord_span_at(held)["chord"]} at beat {r3(held)}'}
                    if hit:
                        fixed = False
                        for alt in spec.get('alternatives', STD['alternatives']):
                            if alt == p['degree'] or substitute_degree(alt, p['chord'])[1]:
                                continue
                            ap = 12 * octave + p['root'] + degree_offset(alt, p['chord'])
                            while ap > ceiling and ap - 12 >= p['floor']:
                                ap -= 12
                            if ap < p['floor'] or ap > ceiling:
                                continue
                            ad = r3(max(min(p['dur'], hold_end(beat, ap) - beat), 0.25))
                            if (min_dur and ad < min_dur - EPS) or clash(ap, beat, ad) or (events and events[-1]['pitch'] == ap and abs(events[-1]['beat'] - beat) < 2 * slot):
                                continue
                            why = f'held only {dur} beats before {hit["pitch"]}' if hit['note_id'] == 'chord change' else f'semitone against melody {hit["note_id"]} (pitch {hit["pitch"]})'
                            changes.append({'beat': beat, 'kind': 'changed', 'from_degree': p['degree'], 'to_degree': alt, 'pitch': pitch, 'reason': f'{why}; replaced by degree {alt}', 'label': p['label']})
                            pitch, dur, fixed = ap, ad, True
                            p = dict(p, degree=alt)
                            break
                        if not fixed:
                            why = f'held only {dur} beats before {hit["pitch"]}, no chord tone lasts {min_dur} beats' if hit['note_id'] == 'chord change' else f'semitone against melody {hit["note_id"]} (pitch {hit["pitch"]})'
                            changes.append({'beat': beat, 'kind': 'dropped', 'degree': p['degree'], 'pitch': pitch, 'reason': why, 'label': p['label']})
                            continue
                    vel = cfg['vel'][tier_of(section_at(beat)['id'])] + (cfg['first_token_bonus'] if p['first'] and section_at(beat)['id'] not in ('R', 'O') else 0)
                    if min_dur and any(abs(beat - prior['beat']) < min_dur - EPS for prior in events[-4:]):
                        changes.append({'beat': beat, 'kind': 'dropped', 'degree': p['degree'], 'pitch': pitch, 'reason': f'density swap {style} {section_at(beat)["id"]}: onset spacing below {min_dur} beats', 'label': p['label']})
                        continue
                    events.append({'beat': beat, 'pitch': pitch, 'duration': dur, 'velocity': vel, 'channel': STD['channel'][style], 'part': style, 'section': section_at(beat)['id'], 'chord': p['chord'], 'degree': p['degree'], 'figure': p['label']})
                if candidate:
                    if len(events) > mark_events:
                        placed_count += 1
                        next_free = group[0]['beat'] + spec['step'] * slot
                    else:
                        del changes[mark_changes:]
        events.sort(key=lambda e: e['beat'])
        adapt_density(style, events, changes)
        events.sort(key=lambda e: e['beat'])
        if fix and fix['style'] == style:
            first = sections[0]['anchor']
            cut = first + fix['drop_support_bars'] * bar
            for e in [e for e in events if e['beat'] < cut - EPS]:
                changes.append({'beat': e['beat'], 'kind': 'dropped', 'degree': e['degree'], 'pitch': e['pitch'], 'reason': f'source fix: no {style} note in the first {fix["drop_support_bars"]} bars ({fix["reason"]})', 'label': e['figure']})
            events = [e for e in events if e['beat'] >= cut - EPS]
        for i, e in enumerate(events, 1):
            e['note_id'] = f'{style[:3]}-{i:03d}'
        return events, changes

    for i, e in enumerate(piano_rh, 1):
        e['note_id'] = f'rh-{i:03d}'
    for i, e in enumerate(sorted(lh, key=lambda e: (e['beat'], e['pitch'])), 1):
        e['note_id'] = f'lh-{i:03d}'
    lh.sort(key=lambda e: e['beat'])
    for i, e in enumerate(pad, 1):
        e['note_id'] = f'pad-{i:03d}'

    support, changes = {}, {}
    for style in SUPPORT_STYLES:
        support[style], changes[style] = style_plan(style)

    density = {}
    for style in SUPPORT_STYLES:
        density[style] = {}
        for s in sections:
            pts = grid_points(s)
            onsets = {e['beat'] for e in support[style] if s['start'] - EPS <= e['beat'] < s['end'] - EPS}
            density[style][s['id']] = {'onsets': len(onsets), 'slots': len(pts), 'percent': round(100 * len(onsets) / len(pts), 1) if pts else 0}

    for e in piano_rh:
        e.pop('file_beat', None)
    for e in lh:
        e.pop('chord', None)
    non_support = resolve_same_pitch(piano_rh + lh + pad)
    kept_ids = {id(e) for e in non_support}
    piano_rh, lh, pad = ([e for e in group if id(e) in kept_ids] for group in (piano_rh, lh, pad))
    support = {style: resolve_same_pitch(evs) for style, evs in support.items()}
    for h in harmony:
        h.pop('shift', None)

    statement_rows = []
    for s in sections:
        row = {'section': s['id'], 'kind': s['kind'], 'start_beat': r3(s['start']), 'end_beat': r3(s['end']), 'start_seconds': round(s['start'] * sec_per_beat, 3), 'end_seconds': round(s['end'] * sec_per_beat, 3), 'downbeat': r3(s['anchor'])}
        if s['kind'] == 'statement':
            parent_id = s.get('statement', s['id'])
            row.update({'key': key_text(s['key'], statement_mode(song, statements[parent_id])), 'transpose_semitones': s['transpose'], 'pickup_start': r3(s['pickup_start'])})
        statement_rows.append(row)
    key_sections = []
    for s in sections:
        if s['kind'] == 'statement':
            parent_id = s.get('statement', s['id'])
            key_sections.append({'section_id': s['id'], 'start_beat': r3(s['start']), 'end_beat': r3(s['end']), 'key': key_text(s['key'], statement_mode(song, statements[parent_id])), 'transpose_semitones': s['transpose']})
        else:
            for h in [h for h in harmony if h['section'] == s['id']]:
                key_sections.append({'section_id': s['id'], 'start_beat': h['start_beat'], 'end_beat': h['end_beat'], 'key': h.get('function', ''), 'transpose_semitones': h['transpose_semitones']})
    by_beat = []
    for h in harmony:
        if by_beat and by_beat[-1][2] == h['transpose_semitones'] and abs(by_beat[-1][1] - h['start_beat']) < EPS:
            by_beat[-1][1] = h['end_beat']
        else:
            by_beat.append([h['start_beat'], h['end_beat'], h['transpose_semitones']])
    for s in sections:
        if s['kind'] == 'statement' and s['pickup_start'] < s['start'] - EPS:
            by_beat.append([r3(s['pickup_start']), r3(s['start']), s['transpose'], 'melody pickup inside the previous section'])

    return {
        'song': song, 'mel': mel, 'melody_path': melody_path, 'sections': sections, 'statement_rows': statement_rows,
        'harmony': harmony, 'pivots': pivots, 'non_support': non_support, 'support': support, 'changes': changes,
        'density': density, 'total': total, 'chime_beat': chime_beat, 'sec_per_beat': sec_per_beat,
        'accompaniment_changes': accompaniment_changes,
        'key_sections': key_sections, 'by_beat': by_beat, 'trans': trans, 'melody_count': len(melody),
        'counts': {'melody': len(melody), 'rh_total': len(piano_rh), 'left_hand': len(lh), 'pad': len(pad), 'non_support': len(non_support)},
    }


def rel(path):
    path = Path(path).resolve()
    return str(path.relative_to(REPO)) if path.is_relative_to(REPO) else str(path)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def caption_for(song, style, keys_text):
    cap = song['caption']
    bar_word = song['meter']
    head = f'Instrumental {song["title"]} Christmas carol, {bar_word}, quarter-note BPM {song["bpm"]}. Soft connected Salamander grand piano carries the complete melody and spacious left hand; {cap["form"]}. Warm nonvocal pad with common-tone ties and gentle envelopes.'
    if style == 'plain':
        body = ' Exactly two base instruments: piano and warm pad.'
    else:
        body = f' {cap[style]} Exactly three base instruments: piano, warm pad and {style}.'
    return f'{head}{body} {cap["tail"]} {STD["caption_tail"]}'


def write_song(song, revision):
    extra = song.get('revisions', {}).get(revision, {})
    fix = extra.get('source_fix')
    styles = extra.get('styles', STYLES)
    slug = song['slug']
    root = WORKDIR / slug
    if fix and fix.get('from_revision') and (root / f'{fix["from_revision"]}-pm/arrangement-plan.json').exists():
        parent = fix['from_revision']
        parent_plan = json.loads((root / f'{parent}-pm/arrangement-plan.json').read_text())
        parent_plan['revision'] = revision
        parent_plan['styles'] = styles
        parent_plan['source_fix'] = fix
        parent_plan['generator'] = {'path': rel(HERE / 'make_plan.py'), 'sha256': sha(HERE / 'make_plan.py'), 'songs_json': rel(BATCH_FILE), 'songs_json_sha256': sha(BATCH_FILE), 'workflow_sha256': sha(plan_io.CONFIG_PATH), 'parent_revision': parent}
        out_pm = root / f'{revision}-pm'
        out_pm.mkdir(parents=True, exist_ok=True)
        (out_pm / 'arrangement-plan.json').write_text(json.dumps(parent_plan, indent=1))
        cut = parent_plan['sections'][0]['downbeat'] + fix['drop_support_bars'] * song['bar']
        for style in styles:
            src = root / style / parent / 'track-plan.json'
            if not src.exists():
                continue
            track = json.loads(src.read_text())
            track['revision'] = revision
            track['source_fix'] = fix
            if style == fix['style']:
                events = track['note_plan']['events']
                dropped = [e for e in events if e.get('part') == style and e['beat'] < cut - EPS]
                track['note_plan']['events'] = [e for e in events if e not in dropped]
                for i, e in enumerate([e for e in track['note_plan']['events'] if e.get('part') == style], 1):
                    e['note_id'] = f'{style[:3]}-{i:03d}'
                track['support_pattern']['dropped_by_PM'] = track['support_pattern'].get('dropped_by_PM', []) + [{'beat': e['beat'], 'kind': 'dropped', 'reason': f'source fix: no {style} note in first {fix["drop_support_bars"]} bars ({fix["reason"]})'} for e in dropped]
                track['support_pattern']['note_count'] = sum(1 for e in track['note_plan']['events'] if e.get('part') == style)
                for sid, row in track['support_pattern'].get('per_verse', {}).items():
                    sec = next((x for x in parent_plan.get('sections', []) if x.get('section') == sid), None)
                    if not sec:
                        continue
                    points = max(1, round((sec['end_beat'] - sec['start_beat']) / song['slot']))
                    evs = [e for e in track['note_plan']['events'] if e.get('part') == style and sec['start_beat'] - EPS <= e['beat'] < sec['end_beat'] - EPS]
                    row['notes'] = len(evs)
                    row['density'] = {'onsets': len({e['beat'] for e in evs}), 'slots': points, 'percent': round(100 * len({e['beat'] for e in evs}) / points, 1)}
            out = root / style / revision
            out.mkdir(parents=True, exist_ok=True)
            (out / 'track-plan.json').write_text(json.dumps(track, indent=1))
        if style == fix['style']:
            parent_plan['support_events_by_style'][style] = [e for e in parent_plan.get('support_events_by_style', {}).get(style, []) if e['beat'] >= cut - EPS]
            for i, event in enumerate(parent_plan['support_events_by_style'][style], 1):
                event['note_id'] = f'{style[:3]}-{i:03d}'
            parent_plan['support_changes_by_style'][style] = parent_plan.get('support_changes_by_style', {}).get(style, []) + [{'beat': e['beat'], 'kind': 'dropped', 'reason': f'source fix: no {style} note in first {fix["drop_support_bars"]} bars'} for e in dropped]
            parent_plan['counts'][f'support_{style}'] = len(parent_plan['support_events_by_style'][style])
            for sid, row in parent_plan.get('support_pattern', {}).get('density_reached', {}).get(style, {}).items():
                sec = next((x for x in parent_plan.get('sections', []) if x.get('section') == sid), None)
                if not sec:
                    continue
                points = max(1, round((sec['end_beat'] - sec['start_beat']) / song['slot']))
                onsets = {e['beat'] for e in parent_plan['support_events_by_style'][style] if sec['start_beat'] - EPS <= e['beat'] < sec['end_beat'] - EPS}
                row['onsets'] = len(onsets)
                row['slots'] = points
                row['percent'] = round(100 * len(onsets) / points, 1)
        plan_path = out_pm / 'arrangement-plan.json'
        plan_path.write_text(json.dumps(parent_plan, indent=1))
        plan_hash = sha(plan_path)
        for style in styles:
            track_path = root / style / revision / 'track-plan.json'
            if not track_path.exists():
                continue
            track = json.loads(track_path.read_text())
            track['key_plan']['authority'] = f'{revision}-pm/arrangement-plan.json sha256 {plan_hash}'
            track['source_revision']['PM_plan_authority'] = {'path': rel(plan_path), 'sha256': plan_hash}
            track_path.write_text(json.dumps(track, indent=1))
        return parent_plan
    res = build_song(song, fix)
    sections = res['sections']
    statements = {s['id']: s for s in song['statements']}
    def group_id(sid):
        st = statements.get(sid, {})
        return st.get('group') or st.get('group_id') or st.get('base') or sid
    def pattern_config(style, sid):
        patterns = song['patterns'][style]
        return patterns.get(sid) or patterns.get(group_id(sid))
    def section_config(sid):
        return song['sections'].get(sid) or song['sections'].get(group_id(sid))
    tempo = TEMPO[slug]
    mel = res['mel']
    chime_s = round(res['chime_beat'] * res['sec_per_beat'], 3)
    total_s = round(res['total'] * res['sec_per_beat'], 3)
    sec_ids = [s['id'] for s in sections]
    support_set = {}
    for style in SUPPORT_STYLES:
        support_set[style] = {sid: pattern_config(style, sid)['name'] for sid in sec_ids if pattern_config(style, sid)}
    plan = {
        'date': CONFIG['date'],
        'batch': CONFIG['batch'],
        'revision': revision,
        'styles': styles,
        'source_fix': fix,
        'accompaniment_changes': res['accompaniment_changes'],
        'parent': plan_io.RENDER['standard'],
        'authority': CONFIG['brief'],
        'generator': {'path': rel(HERE / 'make_plan.py'), 'sha256': sha(HERE / 'make_plan.py'), 'songs_json': rel(BATCH_FILE), 'songs_json_sha256': sha(BATCH_FILE), 'workflow_sha256': sha(plan_io.CONFIG_PATH)},
        'meta': {'slug': slug, 'title': song['title'], 'meter': song['meter'], 'quarter_note_bpm': song['bpm'], 'slot_quarters': song['slot'], 'bar_quarters': song['bar']},
        'notation_reference': {'path': rel(res['melody_path']), 'sha256': sha(res['melody_path'])},
        'tempo_evidence': {'path': plan_io.CONFIG['paths']['tempo_overrides'], 'quarter_note_bpm': tempo['quarter_note_bpm'], 'status': tempo.get('status'), 'decision_basis': tempo.get('decision_basis'), 'rationale': tempo.get('rationale')},
        'form': song['form'],
        'sections': res['statement_rows'],
        'length': {'beats': r3(res['total']), 'seconds': total_s},
        'chime': {'section': song['chime_statement'], 'beat': r3(res['chime_beat']), 'seconds': chime_s, 'fraction': round(chime_s / total_s, 4)},
        'keys': {s['id']: key_text(s['key'], statement_mode(song, statements[s.get('statement', s['id'])])) for s in sections if s['kind'] == 'statement'},
        'transpose_semitones_by_beat': res['by_beat'],
        'pivots': res['pivots'],
        'piano_gain': STD['baseline_mix']['piano_linear_gain'],
        'phrase_harmony': res['harmony'],
        'support_pattern': {
            'set': support_set,
            'density_percent_targets': song['density'],
            'density_reached': res['density'],
        },
        'non_support_events': res['non_support'],
        'support_events_by_style': res['support'],
        'support_changes_by_style': res['changes'],
        'counts': {**res['counts'], **{f'support_{s}': len(v) for s, v in res['support'].items()}},
    }
    pm_dir = root / f'{revision}-pm'
    pm_dir.mkdir(parents=True, exist_ok=True)
    plan_path = pm_dir / 'arrangement-plan.json'
    plan_path.write_text(json.dumps(plan, indent=1))
    plan_sha = sha(plan_path)

    phrase_plan = []
    for s in sections:
        mel_ev = [e for e in res['non_support'] if e['part'] == 'melody' and s['start'] - 1e-6 <= e['beat'] < s['end'] - 1e-6]
        spans = [h for h in res['harmony'] if s['start'] - 1e-6 <= h['start_beat'] < s['end'] - 1e-6]
        names = ['', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        entry = {'id': s['id'], 'kind': s['kind'], 'start_beat': r3(s['start']), 'end_beat': r3(s['end']), 'bars': round((s['end'] - s['start']) / song['bar'], 3),
                 'harmony_letters': ' '.join(f'{h["chord"]}({r3(h["end_beat"] - h["start_beat"])})' for h in spans)}
        if mel_ev:
            lo, hi = min(e['pitch'] for e in mel_ev), max(e['pitch'] for e in mel_ev)
            entry['melody_range_midi'] = [lo, hi]
        if s['kind'] == 'statement':
            entry['key'] = key_text(s['key'], statement_mode(song, statements[s.get('statement', s['id'])]))
            cfg = section_config(s['id']) or {'texture': 'block', 'tier': 'first'}
            entry['texture'] = cfg['texture']
            entry['development'] = {'first': 'sparse', 'second': 'developed', 'third': 'fullest'}[cfg['tier']]
        phrase_plan.append(entry)

    keys_text = ' then '.join(plan['keys'].values())
    for style in styles:
        base_parts = ['piano', 'pad'] if style == 'plain' else ['piano', 'pad', style]
        events = copy.deepcopy(res['non_support']) + (copy.deepcopy(res['support'][style]) if style != 'plain' else [])
        events.sort(key=lambda e: (e['beat'], e['channel'], e['pitch']))
        if style == 'plain':
            sp = {'set': {sid: 'none' for sid in sec_ids}, 'per_verse': {sid: {'pattern_id': 'none', 'notes': 0} for sid in sec_ids}, 'note_count': 0,
                  'note': 'plain = Piano + Pad only; no decorative support instrument'}
        else:
            per = {}
            for sid in sec_ids:
                spec = pattern_config(style, sid)
                evs = [e for e in res['support'][style] if e['section'] == sid]
                figs = {}
                for e in evs:
                    figs[e['figure']] = figs.get(e['figure'], 0) + 1
                per[sid] = {'pattern_id': spec['id'] if spec else 'none', 'pattern_name': spec['name'] if spec else 'none', 'notes': len(evs), 'figures': figs, 'density': res['density'][style][sid], 'density_target': song['density'].get(sid)}
            dropped = [c for c in res['changes'][style] if c['kind'] == 'dropped']
            changed = [c for c in res['changes'][style] if c['kind'] == 'changed']
            sp = {'set': support_set[style],
                  'roles': {sid: ('role 3 fill (answers in melodic gaps)' if pattern_config(style, sid)['id'] in ('P8', 'P4') else 'role 1 background') for sid in sec_ids if pattern_config(style, sid)},
                  'grid': f'one pattern symbol = one slot of {song["slot"]} quarter notes ({int(round(song["bar"] / song["slot"]))} symbols per {song["meter"]} bar); no support onset off the slot grid',
                  'register': f'every support note >= highest melody note of its phrase and of the melody sounding during it + {STD["support_margin"]} semitones; top limit {STD["ceiling"][style]}',
                  'chime_space': f'no support onset on beat {r3(res["chime_beat"])} (chime onset, start of {song["chime_statement"]})',
                  'instrument_treatment': 'broken-chord figures and bell answers, rounded attacks' if style == 'celesta' else 'long sustained chord tones, notes held to the next onset (capped 3.5 quarters, cut at a chord lacking the tone)',
                  'per_verse': per, 'note_count': len(res['support'][style]),
                  'dropped_by_PM': dropped, 'changed_by_PM': changed}
        track = {
            'meta': {'slug': slug, 'title': song['title'], 'key': plan['keys'][song['statements'][0]['id']], 'meter': song['meter'], 'tempo': song['bpm']},
            'style': style,
            'revision': revision,
            'base_parts': base_parts,
            'accents_in_source': 0,
            'render': {'ace_step': {'caption': caption_for(song, style, keys_text)}},
            'notation_reference': {'path': plan['notation_reference']['path'], 'sha256': plan['notation_reference']['sha256'], 'authority': f'Melody + chords file ({mel.get("pd_basis", "")}); verified: {mel.get("confidence", "")}'},
            'tempo_evidence': {'quarter_note_bpm': song['bpm'], 'authority': plan_io.CONFIG['paths']['tempo_overrides'], 'status': tempo.get('status'), 'decision_basis': tempo.get('decision_basis')},
            'note_plan': {'events': events},
            'phrase_plan': phrase_plan,
            'baseline_mix': {'gains_db': {'piano': STD['baseline_mix']['gains_db']['piano'], 'pad': STD['baseline_mix']['gains_db']['pad'], **({} if style == 'plain' else {style: STD['baseline_mix']['gains_db']['support']})},
                             'pans': {'piano': 0, 'pad': 0, **({} if style == 'plain' else {style: STD['baseline_mix']['pans']['support']})},
                             'pad_section_gain_db': STD['baseline_mix']['pad_section_gain_db'], 'shared_reverb': STD['baseline_mix']['shared_reverb'],
                             'scale_policy': STD['baseline_mix']['scale_policy'], 'piano_linear_gain': STD['baseline_mix']['piano_linear_gain']},
            'listener_accepted': False,
            'release_approved': False,
            'source_revision': {'parent': plan_io.RENDER['standard'], 'authority': CONFIG['brief'], 'axis': fix['reason'] if fix else f'plan of batch {CONFIG["batch"]}',
                                'fixed_common_scale': STD['baseline_mix']['fixed_common_scale'], 'piano_linear_gain': STD['baseline_mix']['piano_linear_gain'],
                                'source_support_high_shelf_db': STD['baseline_mix']['support_high_shelf_db'].get(style, 0), 'source_support_balance_gain_db': STD['baseline_mix']['support_balance_gain_db'].get(style, 0),
                                'bell_applied': False, 'PM_plan_authority': {'path': rel(plan_path), 'sha256': plan_sha}},
            'phrase_harmony': res['harmony'],
            'key_plan': {'opening_key_for_ACE_keyscale': plan['keys'][song['statements'][0]['id']], 'sections': res['key_sections'], 'transpose_semitones_by_beat': res['by_beat'], 'pivots': res['pivots'], 'authority': f'{revision}-pm/arrangement-plan.json sha256 {plan_sha}'},
            'form': {'sections': res['statement_rows'], 'length_beats': r3(res['total']), 'length_seconds': plan['length']['seconds'], 'chime': plan['chime']},
            'support_pattern': sp,
        }
        out = root / style / revision
        out.mkdir(parents=True, exist_ok=True)
        (out / 'track-plan.json').write_text(json.dumps(track, indent=1))
    return plan


def load_batch(batch):
    global CONFIG, BATCH_FILE
    BATCH_FILE = REPO / plan_io.PIPELINE['batches'] / batch / 'songs.json'
    CONFIG = json.loads(BATCH_FILE.read_text())
    assert CONFIG['batch'] == batch, f'{BATCH_FILE}: batch field {CONFIG["batch"]} != {batch}'
    return CONFIG


def main():
    parser = argparse.ArgumentParser(description='Write <rev>-pm/arrangement-plan.json and <style>/<rev>/track-plan.json for songs of a batch')
    parser.add_argument('batch')
    parser.add_argument('slugs', nargs='*')
    parser.add_argument('--revision', default=plan_io.PIPELINE['default_revision'])
    parser.add_argument('--workdir', help='write under this directory instead of the configured workdirs (proof runs)')
    args = parser.parse_args()
    load_batch(args.batch)
    global WORKDIR
    WORKDIR = Path(args.workdir).resolve() if args.workdir else REPO / plan_io.PIPELINE['workdirs']
    for song in CONFIG['songs']:
        if args.slugs and song['slug'] not in args.slugs:
            continue
        plan = write_song(song, args.revision)
        d = plan['support_pattern']['density_reached']
        print(song['slug'], json.dumps(plan['counts']), plan['length'], plan['chime'])
        for style in [style for style in SUPPORT_STYLES if style in plan['styles']]:
            ch = plan['support_changes_by_style'][style]
            print(' ', style, {k: v['percent'] for k, v in d[style].items()}, 'dropped', sum(c['kind'] == 'dropped' for c in ch), 'changed', sum(c['kind'] == 'changed' for c in ch))


if __name__ == '__main__':
    main()

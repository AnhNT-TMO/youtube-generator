import argparse
import copy
import datetime
import json
import math
import statistics
import sys
from pathlib import Path

import plan_io

REPO = plan_io.repo_root()
CAROLS = REPO / 'research' / 'christmas-carols'
STD = plan_io.PIPELINE['plan_standard']
LIB = plan_io.PIPELINE['pattern_library']
TEMPO_PATH = REPO / plan_io.CONFIG['paths']['tempo_overrides']
REFS = sorted((CAROLS / 'tempo_refs').glob('t*.json'))
PC = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}
KEY_NAMES = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
SPOKEN = {'C#': 'C-sharp', 'Eb': 'E-flat', 'F#': 'F-sharp', 'Ab': 'A-flat', 'Bb': 'B-flat'}
WORDS = {2: 'two', 3: 'three'}
TIERS = {3: {'A1': 'first', 'A2': 'second', 'A3': 'third'}, 2: {'A1': 'first', 'A2': 'second', 'A2F': 'third'}}
DENSITY = {'first': [20, 30], 'second': [40, 60], 'third': [60, 80]}
TEXTURE = {'first': ('block', 0), 'second': ('broken', 3), 'third': ('bass_led', 1)}
MIN_S, MAX_S = 120, 240
TEMPO_TOLERANCE = 0.10
EPS = 1e-6


class Blocked(Exception):
    pass


def melody_file(slug, explicit):
    if explicit:
        return Path(explicit).resolve()
    hits = sorted((CAROLS / 'melodies').glob(f'b*/{slug}.json'))
    if not hits:
        raise Blocked(f'{slug}: no melodies/b*/{slug}.json')
    if len(hits) > 1:
        raise Blocked(f'{slug}: several melody files {[str(h.relative_to(CAROLS)) for h in hits]}; pass --melody')
    return hits[0]


def tempo_refs():
    refs = {}
    for path in REFS:
        refs.update(json.loads(path.read_text()))
    return refs


def calm_median(record):
    points = [p['bpm_quarter'] for p in record.get('data_points', []) if p.get('category') == 1 and p.get('bpm_quarter')]
    if not points:
        return None, []
    base = statistics.median(points)
    folded = [b / 2 if b > 1.6 * base and b / 2 >= 0.6 * base else b for b in points]
    return statistics.median(folded), folded


def melody_density(mel):
    active = sum(d for p, d in mel.get('melody', []) if p not in (0, None))
    total = sum(d for _, d in mel.get('melody', []))
    return (active / total if total else 0.0), active, total


def choose_tempo(slug, decisions, refs, mel=None):
    record = refs.get(slug, {})
    median, folded = calm_median(record)
    curated = record.get('relaxing_piano_bpm_quarter')
    reference = curated if curated else median
    decision = decisions.get(slug)
    if decision:
        bpm = decision['quarter_note_bpm']
        basis = 'tempo decision record'
    elif reference:
        bpm = round(reference)
        basis = 'relaxing_piano_bpm_quarter' if curated else 'category 1 median (double-time points halved)'
    else:
        active_density = melody_density(mel or {})[0]
        bpm = max(1, round((1.2 / active_density) * 60)) if active_density else 60
        basis = 'density_default'
        reference = None
    drift = abs(bpm - reference) / reference if reference else None
    density_basis = None
    if mel:
        density, active, total = melody_density(mel)
        density_at_bpm = density * bpm / 60.0
        if density_at_bpm > 1.5 and bpm > 0:
            capped = max(bpm * 0.6, bpm * 1.3 / density_at_bpm)
            if capped < bpm - EPS:
                bpm = max(1, round(capped))
                basis = 'density_cap'
                density_basis = {'notes': active, 'melody_beats': total, 'notes_per_second_at_bpm': density_at_bpm, 'target': 1.3, 'original_bpm': decision['quarter_note_bpm'] if decision else (round(reference) if reference else None)}
    if drift is not None and drift > TEMPO_TOLERANCE + EPS and basis != 'density_cap' and not decision:
        raise Blocked(f'{slug}: tempo {bpm} differs {drift:.0%} from the calm-piano reference {reference}; tempo changes over 10 % are PM decisions')
    return bpm, {'basis': basis, 'calm_reference': reference, 'category1_median': median, 'category1_points_quarter': folded, 'drift': round(drift, 3) if drift is not None else None, 'density': density_basis}, record


def meter_info(meter):
    num, den = (int(x) for x in meter.split('/'))
    bar = num * 4 / den
    compound = den == 8 and num % 3 == 0
    slot = 1.5 if compound else 1.0
    return bar, slot, compound


def melody_notes(mel):
    notes, t = [], 0.0
    for p, d in mel['melody']:
        notes.append((t, p, d))
        t += d
    return notes, t


def top_in(notes, a, b):
    return max((p for t, p, d in notes if p > 0 and t < b - EPS and t + d > a + EPS), default=0)


def key_name(pc):
    return KEY_NAMES[pc % 12]


def choose_key(mel, notes, spans, decision):
    tonic = PC[mel['tonic']]
    lift = STD['lift_semitones']
    top_final = top_in(notes, *spans[-1])
    lifts = lift * (len(spans) - 1)
    if decision and decision.get('start_key'):
        name = decision['start_key'].split()[0]
        t = (PC[name] - tonic) % 12
        t = t - 12 if t > 6 else t
        if top_final + t + lifts <= STD['max_final_melody_pitch']:
            return t, f'decision start_key {decision["start_key"]}'
    options = sorted(range(-6, 6), key=lambda t: (abs(t), t > 0))
    for t in options:
        if top_final + t + lifts <= STD['max_final_melody_pitch']:
            return t, 'nearest transposition of the file key with final-statement top <= {}'.format(STD['max_final_melody_pitch'])
    raise Blocked('no start key keeps the final statement top <= 83')


def phrase_bounds(fs, fe, downbeat, bar, compound):
    length = bar * (2 if compound else 4)
    bounds = [fs]
    b = downbeat + length
    while b < fe - EPS:
        if b > fs + EPS:
            bounds.append(b)
        b += length
    bounds.append(fe)
    return bounds


def barline_near(target, downbeat, bar, lo, hi):
    best = None
    k = 0
    while downbeat + k * bar < hi - EPS:
        b = downbeat + k * bar
        if b > lo + EPS and (best is None or abs(b - target) < abs(best - target)):
            best = b
        k += 1
    return best


def layouts(mel, total, bar, bpm):
    pickup = mel.get('pickup_beats', 0) or 0
    stmt_s = total * 60.0 / bpm
    out = [{'name': 'three full statements', 'count': 3, 'spans': [(0, total, pickup)] * 3}]
    half = barline_near(total / 2, pickup, bar, pickup, total)
    if half:
        if stmt_s <= 70:
            out.append({'name': 'three statements of the second half (chorus or refrain)', 'count': 3, 'spans': [(half, total, half)] * 3})
        else:
            out.append({'name': 'first half, then the full verse a whole step higher', 'count': 2, 'spans': [(0, half, pickup), (0, total, pickup)], 'cut': half})
    return out


def statement_form(layout, slot, interlude_beats, outro_beats, interlude_split):
    if layout['count'] == 3:
        return ['A1', 'A2', 'R', 'A3', 'O'], {'before': 'A2', 'beats': slot}, [['I', 'A2', interlude_split], ['V7', 'A3', interlude_beats - interlude_split]]
    return ['A1', 'R', 'A2', 'O'], None, [['I', 'A1', interlude_split], ['V7', 'A2', interlude_beats - interlude_split]]


def occurrence_id(base, index):
    return base if index == 1 else f'{base}_{index}'


def pattern_sets(meter):
    key = LIB['aliases'].get(meter, meter)
    sets = LIB['sets'].get(key)
    if not sets and meter in ('3/2', '5/4'):
        source_meter = '3/4' if meter == '3/2' else '4/4'
        sets = copy.deepcopy(LIB['sets'][source_meter])
        slots = int(meter_info(meter)[0] / meter_info(meter)[1])
        for pset in sets:
            pset['id'] = pset['id'].replace(source_meter, meter)
            for style in ('celesta', 'vibraphone'):
                for pattern in pset[style].values():
                    if pattern.get('mode') == 'bars':
                        flat = ''.join(pattern['cycle'])
                        length = math.lcm(len(flat), slots)
                        stream = flat * (length // len(flat))
                        pattern['cycle'] = [stream[i:i + slots] for i in range(0, length, slots)]
                        pattern['name'] += f' ({meter}: library pulse kept on the quarter-note grid)'
    if not sets:
        raise Blocked(f'no pattern set for meter {meter} in WORKFLOW.json pipeline.pattern_library; PM adds one')
    return sets


def set_order(meter, previous_set, used_before):
    sets = pattern_sets(meter)
    start = used_before % len(sets)
    order = [sets[(start + k) % len(sets)] for k in range(len(sets))]
    order = [s for s in order if s['id'] != previous_set]
    if not order:
        raise Blocked(f'meter {meter} has a single pattern set {sets[0]["id"]} and the previous song used it; swap one library pattern by hand')
    return order


def apply_set(entry, pset):
    tiers = {sid: cfg['tier'] for sid, cfg in entry['sections'].items()}
    entry['pattern_set'] = pset['id']
    entry['patterns'] = {style: {**{sid: copy.deepcopy(pset[style][tier]) for sid, tier in tiers.items()}, 'R': copy.deepcopy(pset[style]['R']), 'O': copy.deepcopy(pset[style]['O'])} for style in ('celesta', 'vibraphone')}
    entry['caption']['celesta'] = pset['caption']['celesta']
    entry['caption']['vibraphone'] = pset['caption']['vibraphone']


def density_misses(entry):
    import make_plan
    try:
        res = make_plan.build_song(entry)
    except (SystemExit, KeyError, ValueError) as exc:
        raise Blocked(f'{entry["slug"]}: plan cannot place support/harmony ({exc})')
    misses = []
    for style in ('celesta', 'vibraphone'):
        ranges = dict(entry['density'])
        for section_id, section_cfg in entry.get('sections', {}).items():
            if section_cfg.get('tier') == 'third':
                ranges[section_id] = STD['support'][style].get('climax_density', ranges.get(section_id, [60, 80])) if style == 'vibraphone' else ranges.get(section_id, [60, 80])
        got = res['density'][style]
        for sid, (lo, hi) in ranges.items():
            pct = got[sid]['percent']
            if not lo <= pct <= hi:
                misses.append(f'{style} {sid} {pct}% [{lo}-{hi}]')
        if got['O']['percent'] >= got[entry['climax']]['percent']:
            misses.append(f'{style} outro density not below the climax')
    return misses


def choose_set(entry, order):
    report = []
    for pset in order:
        apply_set(entry, pset)
        misses = density_misses(entry)
        if not misses:
            return report
        report.append(f'{pset["id"]}: ' + ', '.join(misses))
    apply_set(entry, order[0])
    return report


def keys_text(keys, mode='major'):
    words = [f'{SPOKEN.get(k, k)} {mode}' for k in keys]
    return ' then '.join(words)


def build_entry(slug, melody_path, bpm, mel, previous_set, used_before):
    mode = mel.get('mode', 'major')
    bar, slot, compound = meter_info(mel['meter'])
    notes, total = melody_notes(mel)
    pulses = round(bar / slot)
    interlude_bars = 1
    while interlude_bars * pulses < 3:
        interlude_bars += 1
    interlude_beats = interlude_bars * bar
    interlude_split = (interlude_bars * pulses // 2) * slot
    outro_beats = 2 * bar
    order = set_order(mel['meter'], previous_set, used_before)
    pset = order[0]
    tried = []
    for layout in layouts(mel, total, bar, bpm):
        spans = [(a, b) for a, b, _ in layout['spans']]
        decision = json.loads(TEMPO_PATH.read_text()).get(slug)
        t, key_reason = choose_key(mel, notes, spans, decision)
        start = PC[mel['tonic']] + t
        keys = [key_name(start + STD['lift_semitones'] * i) for i in range(layout['count'])]
        ids = ['A1', 'A2', 'A3'][:layout['count']]
        statements = [{'id': sid, 'file': [a, b], 'key': k, 'downbeat': db} for sid, (a, b, db), k in zip(ids, layout['spans'], keys)]
        form, pivot, chords = statement_form(layout, slot, interlude_beats, outro_beats, interlude_split)
        repeats = 1
        if layout['count'] == 3:
            span_beats = layout['spans'][0][1] - layout['spans'][0][0]
            while 3 * repeats * span_beats * 60.0 / bpm < MIN_S:
                repeats += 1
        if repeats > 1:
            expanded = []
            expanded_form = []
            for base in ids:
                st = next(s for s in statements if s['id'] == base)
                for index in range(1, repeats + 1):
                    sid = occurrence_id(base, index)
                    expanded.append({**st, 'id': sid, 'group': base, 'repeat_index': index})
                    expanded_form.append(sid)
                if base == 'A2':
                    expanded_form.append('R')
            expanded_form.append('O')
            statements = expanded
            form = expanded_form
            pivot = {'before': occurrence_id('A2', 1), 'beats': slot}
        tiers = TIERS[layout['count']]
        section_tiers = (tiers if layout['count'] == 2 else {s['id']: tiers.get(s.get('group', s['id']), tiers.get(s['id'])) for s in statements})
        entry = {
            'slug': slug, 'title': mel['title'], 'melody': str(melody_path.relative_to(CAROLS)), 'meter': mel['meter'], 'bpm': bpm,
            'bar': bar, 'slot': slot, 'file_tonic': mel['tonic'], 'mode': mode, 'statements': statements,
            'form': form, 'pivot': pivot, 'interlude': {'beats': interlude_beats, 'chords': chords}, 'outro': {'beats': outro_beats},
            'chime_statement': 'A2',
            'phrases': phrase_bounds(statements[-1]['file'][0], statements[-1]['file'][1], statements[-1]['downbeat'], bar, compound),
            'sections': {sid: {'texture': TEXTURE[tier][0], 'vel': TEXTURE[tier][1], 'tier': tier} for sid, tier in section_tiers.items()},
            'density': {sid: DENSITY[tier] for sid, tier in section_tiers.items()},
            'climax': next(sid for sid, tier in reversed(list(section_tiers.items())) if tier == 'third'),
            'pattern_set': pset['id'],
            'patterns': {style: {**{sid: copy.deepcopy(pset[style][tier]) for sid, tier in tiers.items()}, 'R': copy.deepcopy(pset[style]['R']), 'O': copy.deepcopy(pset[style]['O'])} for style in ('celesta', 'vibraphone')},
            'caption': {
                'form': (f'the three melody statements rise a whole step each, {keys_text(keys, mode)}, with a soft pivot chord before each lift' if layout['count'] == 3 else f'the first half of the verse in {keys_text(keys[:1], mode)}, then the full verse a whole step higher in {keys_text(keys[1:], mode)} after a soft dominant interlude'),
                'celesta': pset['caption']['celesta'], 'vibraphone': pset['caption']['vibraphone'],
                'tail': 'Short dominant interlude and tonic outro with natural decay.',
            },
            'spec': {'layout': layout['name'], 'key_reason': key_reason, 'mode': mode, 'repeats_per_group': repeats, 'generated_by': 'spec.py', 'date': datetime.date.today().isoformat()},
        }
        if layout['count'] == 2:
            entry['subsections'] = [{'id': 'A2F', 'statement': 'A2', 'file_start': layout['cut'], 'name': 'second half'}]
        fixed, why = fit_grid(entry)
        if not fixed:
            tried.append(f'{layout["name"]}: {why}')
            continue
        length_s, frac = measure(fixed)
        lo, hi = STD['chime_fraction_window']
        if MIN_S <= length_s <= MAX_S and lo <= frac <= hi:
            fixed['spec'].update({'length_seconds': round(length_s, 1), 'chime_fraction': round(frac, 3)})
            report = choose_set(fixed, order)
            fixed['spec']['pattern_set_report'] = report
            if len(report) == len(order):
                fixed['spec']['density_warning'] = 'no library set meets every density target; swap a pattern and log it in PLAN_REVIEW.md'
            return fixed
        tried.append(f'{layout["name"]}: {length_s:.0f} s, chime fraction {frac:.3f}')
    raise Blocked(f'{slug}: no default layout fits 2-4 min with chime {STD["chime_fraction_window"]}: ' + '; '.join(tried))


def placements(entry):
    statements = {s['id']: s for s in entry['statements']}
    cursor, anchors = 0.0, []
    for item in entry['form']:
        if item in statements:
            st = statements[item]
            fs, fe = st['file']
            overlap = (st['downbeat'] - fs) if st.get('pickup_in_previous') else 0
            place_start = cursor - overlap
            anchors.append((item, place_start - fs + st['downbeat']))
            cursor = place_start + (fe - fs)
        elif item == 'R':
            cursor += entry['interlude']['beats']
        elif item == 'O':
            cursor += entry['outro']['beats']
    return anchors, cursor


def fit_grid(entry):
    for sid in [s['id'] for s in entry['statements']][1:]:
        anchors, _ = placements(entry)
        first = anchors[0][1]
        pos = dict(anchors)[sid]
        if abs(((pos - first) / entry['bar']) - round((pos - first) / entry['bar'])) < EPS:
            continue
        st = next(s for s in entry['statements'] if s['id'] == sid)
        st['pickup_in_previous'] = True
        anchors, _ = placements(entry)
        pos = dict(anchors)[sid]
        if abs(((pos - first) / entry['bar']) - round((pos - first) / entry['bar'])) > EPS:
            return None, f'{sid} downbeat off the bar grid'
    return entry, ''


def measure(entry):
    anchors, total = placements(entry)
    statements = {s['id']: s for s in entry['statements']}
    cursor = 0.0
    chime = None
    for item in entry['form']:
        if item in statements:
            st = statements[item]
            if item == entry['chime_statement']:
                chime = cursor
            cursor = cursor - ((st['downbeat'] - st['file'][0]) if st.get('pickup_in_previous') else 0) + st['file'][1] - st['file'][0]
        elif item == 'R':
            cursor += entry['interlude']['beats']
        elif item == 'O':
            cursor += entry['outro']['beats']
    sec = 60.0 / entry['bpm']
    return total * sec, chime / total


def tempo_record(slug, bpm, info, record):
    points = [p for p in record.get('data_points', []) if p.get('category') == 1]
    return {
        'quarter_note_bpm': bpm,
        'reference_urls': [p['url'] for p in points if p.get('url')],
        'raw_marking': '; '.join(p.get('raw', '') for p in points),
        'beat_unit': 'quarter note of the melody file; category 1 points converted with their unit field, double-time points halved',
        'unit_verified': all(p.get('unit') for p in points),
        'popularity_evidence': 'research/christmas-carols/popularity/tiers.json',
        'decision_basis': f'spec.py default: {info["basis"]} {info["calm_reference"]} (category 1 median {info["category1_median"]})',
        'status': 'spec_default',
        'rationale': 'calm-piano reference from tempo_refs category 1; density cap or default applied when required',
        'density': info.get('density'),
        'decision_date': datetime.date.today().isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(description='Build default songs.json entries for a batch from melodies/b*/<slug>.json and tempo_refs')
    parser.add_argument('batch')
    parser.add_argument('slugs', nargs='+')
    parser.add_argument('--melody', help='melody file when the slug exists in several melody folders (one slug only)')
    parser.add_argument('--brief', help='brief path recorded in a new songs.json')
    parser.add_argument('--write', action='store_true', help='add or replace the entries in batches/<batch>/songs.json and add missing tempo decisions')
    args = parser.parse_args()
    batch_file = REPO / plan_io.PIPELINE['batches'] / args.batch / 'songs.json'
    if batch_file.exists():
        data = json.loads(batch_file.read_text())
    else:
        data = {'batch': args.batch, 'brief': args.brief or str(batch_file.parent.relative_to(REPO) / 'BRIEF.md'), 'date': datetime.date.today().isoformat(), 'songs': []}
    decisions = json.loads(TEMPO_PATH.read_text())
    refs = tempo_refs()
    songs = [s for s in data['songs'] if s['slug'] not in args.slugs]
    previous = songs[-1].get('pattern_set') if songs else None
    new_records = {}
    blocked = []
    built = []
    for slug in args.slugs:
        try:
            path = melody_file(slug, args.melody)
            mel = json.loads(path.read_text())
            bpm, info, record = choose_tempo(slug, decisions, refs, mel)
            meter_key = LIB['aliases'].get(mel['meter'], mel['meter'])
            used_before = sum(1 for s in songs + built if LIB['aliases'].get(s['meter'], s['meter']) == meter_key)
            entry = build_entry(slug, path, bpm, mel, previous, used_before)
            entry['spec']['tempo'] = info
            if slug not in decisions:
                new_records[slug] = tempo_record(slug, bpm, info, record)
            previous = entry['pattern_set']
            built.append(entry)
            print(f'{slug}: {entry["meter"]} bpm {bpm} ({info["basis"]}), keys {[s["key"] for s in entry["statements"]]}, {entry["spec"]["layout"]}, {entry["spec"]["length_seconds"]} s, chime {entry["spec"]["chime_fraction"]}, set {entry["pattern_set"]}' + (f' WARN {entry["spec"]["density_warning"]}: {entry["spec"]["pattern_set_report"]}' if entry['spec'].get('density_warning') else ''))
        except Blocked as exc:
            blocked.append(str(exc))
            print(f'BLOCKED {exc}')
    if not args.write:
        print(json.dumps(built, indent=1, ensure_ascii=False))
    else:
        data['songs'] = songs + built
        batch_file.parent.mkdir(parents=True, exist_ok=True)
        batch_file.write_text(json.dumps(data, indent=1, ensure_ascii=False) + '\n')
        if new_records:
            decisions.update(new_records)
            TEMPO_PATH.write_text(json.dumps(decisions, indent=2, ensure_ascii=False) + '\n')
        review = batch_file.parent / 'PLAN_REVIEW.md'
        review_lines = []
        for entry in built:
            tempo = entry.get('spec', {}).get('tempo', {})
            if tempo.get('basis') == 'density_default':
                review_lines.append(f'- {datetime.date.today().isoformat()} {entry["slug"]}: no category-1 tempo reference; default density tempo used.')
        if review_lines:
            with review.open('a') as fh:
                fh.write(('\n' if review.exists() and review.stat().st_size else '') + '\n'.join(review_lines) + '\n')
        if blocked:
            with review.open('a') as fh:
                fh.write(('\n' if review.exists() and review.stat().st_size else '') + '\n'.join(f'- BLOCKED {item}' for item in blocked) + '\n')
        print(f'wrote {batch_file.relative_to(REPO)} ({len(built)} entries); new tempo decisions: {sorted(new_records)}')
    sys.exit(2 if blocked else 0)


if __name__ == '__main__':
    main()

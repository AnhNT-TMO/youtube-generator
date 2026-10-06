import json
import math
import random
import re
import sys

from source_audio import parse_chord

PLAN = sys.argv[1]
plan = json.load(open(PLAN))


def role(name):
    return 'A3' if name == 'A2F' else re.sub(r'_\d+$', '', name)


for row in plan['note_plan']['events'] + plan['phrase_harmony']:
    row['section'] = role(row['section'])
merged = []
for sec in plan['form']['sections']:
    name = role(sec['section'])
    if merged and merged[-1]['section'] == name:
        merged[-1]['end_beat'] = sec['end_beat']
    else:
        merged.append(dict(sec, section=name))
plan['form']['sections'] = merged
BPM = plan['meta']['tempo']
METER = [int(x) for x in plan['meta']['meter'].split('/')]
BAR = METER[0] * 4 / METER[1]
rng = random.Random(7)

QUAL = {'maj': (0, 4, 7), 'add9': (0, 4, 7, 14), '6': (0, 4, 7, 9), '69': (0, 4, 7, 9, 14), 'maj7': (0, 4, 7, 11),
        'm7': (0, 3, 7, 10), '7': (0, 4, 7, 10), '9': (0, 4, 7, 10, 14), 'sus7': (0, 5, 7, 10), 'm6': (0, 3, 7, 9),
        'm': (0, 3, 7)}
TENSION = {'maj': {2, 9}, 'add9': {9}, '6': {2}, '69': set(), 'maj7': {2, 9}, 'm7': {2, 5}, '7': {2, 9}, '9': {9},
           'sus7': {2, 9}, 'm6': {2}, 'm': {2, 5}}
LEVEL = {'A1': 2, 'A2': 2, 'A3': 3, 'R': 1, 'O': 1}
SECTION_VEL = {'A1': 50, 'A2': 49, 'R': 44, 'A3': 46, 'O': 40}

sections = {s['section']: s for s in plan['form']['sections']}
melody = sorted((e for e in plan['note_plan']['events'] if e['part'] == 'melody'), key=lambda e: e['beat'])
PITCH = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8,
         'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}
tonic_at = [(k['start_beat'], k['end_beat'], PITCH[re.findall(r'\b([A-G][#b]?)(?![\w#])', k['key'].split(' of ')[-1])[0]])
            for k in plan['key_plan']['sections']]


def tonic(beat):
    for a, b, t in tonic_at:
        if a <= beat < b:
            return t
    return tonic_at[-1][2]


def quality_of(root, tones):
    rel = tuple(sorted((t - root) % 12 for t in tones))
    for name in ('7', 'maj7', 'm7', 'maj', 'm'):
        if tuple(sorted(i % 12 for i in QUAL[name])) == rel:
            return name
    return 'maj'


def fits(a, b, root, qual):
    tones = {i % 12 for i in QUAL[qual]}
    bad = 0.0
    for e in melody:
        s, t = e['beat'], e['beat'] + e['duration']
        ov = min(b, t) - max(a, s)
        if ov <= 0:
            continue
        rel = (e['pitch'] - root) % 12
        if rel in tones or rel in TENSION[qual]:
            if rel == 0 and 11 in tones:
                bad += ov
            continue
        if (rel - 1) % 12 in tones or (rel + 1) % 12 in tones and ov >= 0.5:
            bad += ov if (s >= a and (s - a) % 1.5 == 0) or ov >= 0.5 else 0.2 * ov
        else:
            bad += 0.5 * ov
    return bad <= 0.3


def options(deg, qual, length, next_deg, level, seen):
    opts = []
    half = length / 2 if length >= 3 else None
    if qual == 'maj' and deg == 0:
        if level >= 3 and next_deg == 5 and length >= 3:
            opts.append([(0, 'add9', length - 1.5), (0, '7', 1.5)])
        if level >= 2 and length >= 6:
            opts.append([(0, 'add9', half), (9, 'm7', half)])
        if level >= 3 and length == 3:
            opts.append([(0, 'add9', 1.5), (4, 'm7', 1.5)])
        opts += [[(0, 'add9', length)], [(0, '6', length)], [(0, 'maj7', length)]]
    elif qual == 'maj' and deg == 5:
        if level >= 3 and length >= 3:
            opts.append([(5, 'maj7', half), (5, 'm6', half)])
        if level >= 2 and seen % 2 == 1:
            opts.append([(2, 'm7', length)])
        opts += [[(5, 'maj7', length)], [(5, 'add9', length)], [(5, '6', length)]]
    elif qual == '7' and deg == 7:
        if level >= 2 and length >= 3:
            opts.append([(2, 'm7', half), (7, '7', half)])
            opts.append([(7, 'sus7', half), (7, '7', half)])
        opts += [[(7, '9', length)], [(7, '7', length)]]
    elif qual == '7':
        opts += [[(deg, '9', length)], [(deg, '7', length)], [(deg, 'sus7', length)]]
    elif qual == 'maj':
        opts += [[(deg, 'add9', length)], [(deg, 'maj', length)]]
    return opts


raw = [(h['start_beat'], h['end_beat'], parse_chord(h['chord']), h['section']) for h in plan['phrase_harmony']]
harmony = []
seen_iv = {}
for i, (a, b, (root, tones, bass), sec) in enumerate(raw):
    t = tonic(a)
    deg = (root - t) % 12
    qual = quality_of(root, tones)
    nxt = raw[i + 1] if i + 1 < len(raw) else None
    next_deg = (nxt[2][0] - tonic(nxt[0])) % 12 if nxt else None
    chosen = None
    seen = seen_iv.get(sec, 0)
    if deg == 5 and qual == 'maj':
        seen_iv[sec] = seen + 1
    if sec == 'O':
        chosen = [(deg, '69' if qual == 'maj' else 'm7' if qual in ('m', 'm7') else qual, b - a)]
    elif bass == root:
        for opt in options(deg, qual, b - a, next_deg, LEVEL.get(sec, 1), seen):
            x, ok = a, True
            for d, q, ln in opt:
                if not fits(x, x + ln, (t + d) % 12, q):
                    ok = False
                    break
                x += ln
            if ok:
                chosen = opt
                break
    if chosen is None:
        harmony.append((a, b, root, QUAL[qual] if fits(a, b, root, qual) or qual != '7' else QUAL['sus7'], bass, sec))
        continue
    x = a
    for d, q, ln in chosen:
        r = (t + d) % 12
        harmony.append((x, x + ln, r, QUAL[q], r, sec))
        x += ln

slow = []
for name, sec in sections.items():
    a, b = sec['start_beat'], sec['end_beat']
    if sec['kind'] == 'statement':
        for end in [x * 4 * BAR + a for x in range(1, int((b - a) // (4 * BAR)))]:
            slow.append((end - 1.0, end, 0.85))
        slow.append((b - 1.5, b, 0.75))
    elif sec['kind'] == 'outro':
        slow.append((a, a + 3, 0.85))
        slow.append((a + 3, b, 0.65))
    else:
        slow.append((b - 1.0, b, 0.8))


def factor(beat):
    for a, b, f in slow:
        if a <= beat < b:
            return f
    return 1.0


edges = sorted({0.0, *[x for a, b, _ in slow for x in (a, b)]})
END_BEAT = max(h[1] for h in harmony)


def seconds(beat):
    t, prev = 0.0, 0.0
    for e in edges + [beat]:
        e = min(e, beat)
        if e > prev:
            t += (e - prev) * 60 / (BPM * factor(prev))
            prev = e
        if prev >= beat:
            break
    return t


def chord_at(beat):
    for h in harmony:
        if h[0] <= beat < h[1]:
            return h
    return harmony[-1]


def place(pc, low):
    return low + (pc - low) % 12


import json
import math
import os
import random
import re
import sys

import dawdreamer as daw
import mido
import numpy as np
import soundfile as sf
import tinysoundfont
from scipy.signal import butter, fftconvolve, sosfilt, sosfiltfilt

from ambient_harmony import BAR, METER, END_BEAT, SECTION_VEL, chord_at, edges, factor, harmony, melody, place, plan, sections, seconds, BPM

VIBE, OUT = sys.argv[2], sys.argv[3]
HOME = os.path.expanduser('~/music-tools')
SALAMANDER = f'{HOME}/sf2/SalamanderGrandPiano-V3+20200602.sf2'
GM = f'{HOME}/sf2/MuseScore_General.sf2'
HALL = f'{HOME}/src/dragonfly/dragonfly-reverb-3.2.10/DragonflyHallReverb.vst3'
VSCO = f'{HOME}/sfz/VSCO-2-CE'
REAL = f'{HOME}/sfz/real'
SR = 48000
rng = random.Random(11)
PASSES = ['A1', 'A2', 'A3']
PASS_DB = {'A1': 0.0, 'A2': 0.5, 'A3': 1.0}

LAYERS = {
    'snowglobe': {
        'A1': ['melody:piano', 'arp:harp', 'bed:strings', 'answer:celesta', 'bells:sleigh'],
        'A2': ['melody:piano', 'arp:harp', 'bed:strings', 'answer:celesta', 'bells:sleigh'],
        'A3': ['melody:piano', 'double:octave', 'arp:harp+', 'bed:strings', 'answer:celesta', 'bells:sleigh'],
        'reverb': (3.0, 30),
    },
    'snowglobe_layer': {
        'A1': ['melody:piano', 'layer:celesta', 'arp:harp', 'bed:strings', 'bells:sleigh'],
        'A2': ['melody:piano', 'layer:celesta', 'arp:harp', 'bed:strings', 'bells:sleigh'],
        'A3': ['melody:piano', 'double:octave', 'layer:celesta', 'arp:harp+', 'bed:strings', 'bells:sleigh'],
        'reverb': (3.0, 30),
    },
    'snowglobe_clear': {
        'A1': ['melody:piano', 'left:sparse', 'grace:fifth', 'layer:celesta_short', 'bed:pad', 'bells:sleigh'],
        'A2': ['melody:piano', 'left:sparse', 'grace:fifth', 'layer:celesta_short', 'bed:pad', 'bells:sleigh'],
        'A3': ['melody:piano', 'left:sparse', 'grace:fifth', 'layer:celesta_short', 'bed:pad', 'bells:sleigh'],
        'reverb': ('static', 0.35),
    },
    'snowglobe_felt': {
        'A1': ['melody:felt', 'layer:celesta', 'arp:harp', 'bed:strings', 'bells:sleigh'],
        'A2': ['melody:felt', 'layer:celesta', 'arp:harp', 'bed:strings', 'bells:sleigh'],
        'A3': ['melody:felt', 'double:octave', 'layer:celesta', 'arp:harp+', 'bed:strings', 'bells:sleigh'],
        'reverb': (3.0, 30),
    },
    'snowglobe_felt_grace': {
        'A1': ['melody:felt', 'grace:melody', 'layer:celesta', 'arp:harp', 'bed:strings', 'bells:sleigh'],
        'A2': ['melody:felt', 'grace:melody', 'layer:celesta', 'arp:harp', 'bed:strings', 'bells:sleigh'],
        'A3': ['melody:felt', 'grace:melody', 'double:octave', 'layer:celesta', 'arp:harp+', 'bed:strings', 'bells:sleigh'],
        'reverb': (3.0, 30),
    },
    'snowglobe_felt_nocel': {
        'A1': ['melody:felt', 'arp:harp', 'bed:strings', 'bells:sleigh'],
        'A2': ['melody:felt', 'arp:harp', 'bed:strings', 'bells:sleigh'],
        'A3': ['melody:felt', 'double:octave', 'arp:harp+', 'bed:strings', 'bells:sleigh'],
        'reverb': (3.0, 30),
    },
    'felt_solo': {
        'A1': ['melody:felt'],
        'A2': ['melody:felt'],
        'A3': ['melody:felt'],
        'reverb': (3.0, 30),
    },
    'piano_solo': {
        'A1': ['melody:piano'],
        'A2': ['melody:piano'],
        'A3': ['melody:piano'],
        'reverb': (3.0, 30),
    },
    'church': {
        'A1': ['melody:piano', 'bed:organ', 'bed:choir', 'bell:tubular'],
        'A2': ['melody:piano', 'bed:organ', 'bed:choir', 'bell:tubular', 'arp:piano'],
        'A3': ['melody:piano', 'bed:organ', 'bed:choir', 'bell:tubular', 'arp:piano', 'high:choir'],
        'reverb': (4.2, 45),
    },
    'jazz': {
        'A1': ['melody:piano', 'comp:piano', 'bass:pizz', 'kit:hat'],
        'A2': ['melody:piano', 'comp:piano', 'bass:pizz', 'kit:hat', 'kit:brush'],
        'A3': ['melody:piano', 'comp:piano', 'bass:walk', 'kit:hat', 'kit:brush'],
        'reverb': (1.8, 20),
    },
    'lofi': {
        'A1': ['melody:upright', 'chords:upright', 'bass:pizz', 'kit:lofi', 'amb:vinyl'],
        'A2': ['melody:upright', 'chords:upright', 'bass:pizz', 'kit:lofi', 'kit:hat8', 'amb:vinyl'],
        'A3': ['melody:upright', 'chords:upright', 'bass:pizz', 'kit:lofi', 'kit:hat8', 'arp:upright', 'amb:vinyl'],
        'reverb': (1.4, 15),
    },
    'fireside': {
        'A1': ['melody:piano', 'arp:piano', 'amb:fire', 'amb:wind'],
        'A2': ['melody:piano', 'arp:piano', 'bed:strings', 'amb:fire', 'amb:wind'],
        'A3': ['melody:piano', 'arp:piano', 'bed:strings', 'amb:fire', 'amb:wind'],
        'reverb': (2.6, 25),
    },
    'rain': {
        'A1': ['melody:piano', 'arp:piano', 'amb:rain'],
        'A2': ['melody:piano', 'arp:piano', 'bed:strings', 'amb:rain'],
        'A3': ['melody:piano', 'arp:piano', 'bed:strings', 'amb:rain'],
        'reverb': (2.6, 25),
    },
}[VIBE]
MEL = 'up_mel' if 'melody:upright' in LAYERS['A1'] else 'felt_mel' if 'melody:felt' in LAYERS['A1'] else 'piano_mel'
OCT = 'felt_oct' if MEL == 'felt_mel' else 'piano_oct'
PULSE = 1.5 if METER[1] == 8 and METER[0] % 3 == 0 else 1.0

parts = {}


def add(part, a, b, pitch, vel):
    parts.setdefault(part, []).append([a, max(b, a + 0.2), int(pitch), int(max(8, min(110, vel + rng.randint(-3, 3))))])


def layers_at(beat):
    sec = chord_at(beat)[5]
    if sec == 'R':
        return LAYERS['A2']
    if sec == 'O':
        return LAYERS['A3']
    return LAYERS.get(sec, LAYERS['A1'])


def has(beat, layer):
    return layer in layers_at(beat)


for i, e in enumerate(melody):
    a, b, root, ivs, bass, sec = chord_at(e['beat'])
    pcs = {(root + iv) % 12 for iv in ivs}
    pos = ((e['beat'] - sections[e['section']]['start_beat']) % 12) / 12
    vel = 52 + 6 * math.sin(math.pi * pos)
    nxt = melody[i + 1]['beat'] if i + 1 < len(melody) else END_BEAT
    end = max(e['beat'] + e['duration'], b - 0.05) if e['pitch'] % 12 in pcs else min(max(e['beat'] + e['duration'], nxt + 0.25), b - 0.05)
    add(MEL, e['beat'], end, e['pitch'], vel)
    if has(e['beat'], 'double:octave'):
        add(OCT, e['beat'], end, e['pitch'] + 12, vel - 14)

CELESTA_BREATH_BARS = 2
CELESTA_BREATH_HOLD = 1.5


def breath_notes():
    groups = {}
    for e in melody:
        start = sections[e['section']]['start_beat']
        groups.setdefault((e['section'], int((e['beat'] - start + 1e-6) // (CELESTA_BREATH_BARS * BAR))), []).append(e)
    return {id(g[-1]) for g in groups.values() if g[-1]['duration'] >= CELESTA_BREATH_HOLD}


breaths = breath_notes()
CELESTA_SHORT_HOLD = 1.0
for e in melody:
    if has(e['beat'], 'layer:celesta') and id(e) not in breaths:
        pos = ((e['beat'] - sections[e['section']]['start_beat']) % 12) / 12
        add('celesta_layer', e['beat'], e['beat'] + max(e['duration'], 0.5), e['pitch'] + 12, 44 + 6 * math.sin(math.pi * pos))
    if has(e['beat'], 'layer:celesta_short') and id(e) not in breaths:
        add('celesta_short', e['beat'], e['beat'] + min(max(e['duration'], 0.5), CELESTA_SHORT_HOLD), e['pitch'] + 12, 44)

GRACE_S = 0.07
GRACE_EVERY_BARS = 2
scale_pcs = {}
for e in melody:
    scale_pcs.setdefault(e['section'], set()).add(e['pitch'] % 12)


def neighbour(pitch, up, section):
    steps = range(1, 3) if up else range(-1, -3, -1)
    return next((pitch + d for d in steps if (pitch + d) % 12 in scale_pcs[section]), None)


last_grace = -1e9
for i, e in enumerate(melody):
    if i == 0 or id(e) in breaths or not has(e['beat'], 'grace:melody') or e['duration'] < 1.0:
        continue
    start = sections[e['section']]['start_beat']
    if abs((e['beat'] - start) / BAR - round((e['beat'] - start) / BAR)) > 1e-6:
        continue
    if e['beat'] - last_grace < GRACE_EVERY_BARS * BAR - 1e-6:
        continue
    g = neighbour(e['pitch'], melody[i - 1]['pitch'] > e['pitch'], e['section'])
    if g is None:
        continue
    lead = GRACE_S * BPM * factor(e['beat']) / 60
    parts.setdefault(MEL, []).append([e['beat'] - lead, e['beat'] + 0.02, g, 40])
    last_grace = e['beat']

FIFTH_GRACE_S = 0.035
FIFTH_GRACE_EVERY_BARS = 4
FIFTH_GRACE_MIN_LEAP = 5
last_grace = -1e9
for i, e in enumerate(melody):
    if i == 0 or not has(e['beat'], 'grace:fifth') or e['duration'] < 0.9:
        continue
    if e['pitch'] - melody[i - 1]['pitch'] < FIFTH_GRACE_MIN_LEAP or e['beat'] - last_grace < FIFTH_GRACE_EVERY_BARS * BAR - 1e-6:
        continue
    lead = FIFTH_GRACE_S * BPM * factor(e['beat']) / 60
    parts.setdefault(MEL, []).append([e['beat'] - lead, e['beat'] + e['duration'], e['pitch'] - 7, 54])
    last_grace = e['beat']

END_BEAT_H = max(h[1] for h in harmony)
long_notes = [e for e in melody if e['duration'] >= 1.5 and e['section'] in PASSES]
for k, e in enumerate(long_notes):
    if k % 2 or not has(e['beat'], 'answer:celesta'):
        continue
    a, b, root, ivs, bass, sec = chord_at(e['beat'])
    tones = sorted({place((root + iv) % 12, e['pitch'] + 8 + j * 12) for iv in ivs if iv % 12 != 0 for j in (0,)})
    tones = [p for p in tones if p > e['pitch'] + 4][:3]
    for j, p in enumerate(reversed(tones)):
        t = e['beat'] + 0.5 + 0.5 * j
        if t < e['beat'] + e['duration']:
            add('celesta', t, t + 1.2, p, 40 - 3 * j)

for a, b, root, ivs, bass, sec in harmony:
    lay = layers_at(a)
    lo = place(bass, 43)
    chord_tones = [place((root + iv) % 12, lo + 1) for iv in ivs if (root + iv) % 12 != bass % 12]
    upper = sorted(set(chord_tones))
    if 'arp:harp' in lay or 'arp:harp+' in lay or 'arp:piano' in lay:
        inst = 'harp' if 'arp:piano' not in lay else 'piano_arp'
        seq = [lo] + upper[:2] + [lo + 12] + upper[:2][::-1]
        if 'arp:harp+' in lay:
            seq = [lo] + upper[:2] + [lo + 12, upper[-1] + 12 if upper else lo + 16] + upper[1:2]
        base = 40 if inst == 'harp' else 30
        t, j = a, 0
        while t < b - 1e-6:
            add(inst, t, b, seq[j % len(seq)], base + (5 if j % 3 == 0 else 0) - 2 * (j % 3 == 2))
            t += 0.5
            j += 1
    if 'left:sparse' in lay:
        t = a
        while t < b - 1e-6:
            if t + BAR / 2 < b - 1e-6:
                add('piano_left', t + BAR / 2, min(b, t + BAR), place((root + ivs[1]) % 12, 60), 30)
            t += BAR
    bed = sorted({place((root + iv) % 12, 52) for iv in ivs[:4]})
    if 'bed:pad' in lay:
        for p in bed[1:3] if len(bed) > 2 else bed:
            add('vla', a, b + 0.1, p, 48)
    if 'bed:strings' in lay:
        add('vc', a, b + 0.1, place(bass, 45), 54)
        for p in bed[1:3] if len(bed) > 2 else bed:
            add('vla', a, b + 0.1, p, 50)
    if 'bed:organ' in lay:
        add('organ', a, b + 0.05, place(bass, 41), 64)
        for p in bed[:3]:
            add('organ', a, b + 0.05, p, 64)
    if 'bed:choir' in lay:
        for p in bed[:3]:
            add('choir', a, b + 0.1, p, 46)
    if 'high:choir' in lay:
        add('choir', a, b + 0.1, place((root + ivs[2 if len(ivs) > 2 else 1]) % 12, 67), 40)
    voicing = sorted({place((root + iv) % 12, 52) for iv in ivs if (root + iv) % 12 != root % 12 or len(ivs) <= 3})[:4]
    hits = [a] + ([a + BAR / 2] if b - a >= BAR and BAR >= 3 else []) + [x for x in (a + BAR * k for k in range(1, 8)) if x < b - 0.5]
    if 'comp:piano' in lay:
        for k, t in enumerate(sorted(set(hits))):
            for p in voicing:
                add('piano_comp', t + (0.5 if k % 2 else 0), min(b, t + BAR) - 0.1, p, 30)
    if 'chords:upright' in lay:
        for t in sorted({a} | {x for x in (a + BAR * k for k in range(1, 8)) if x < b - 0.5}):
            for p in sorted({place((root + iv) % 12, 55) for iv in ivs}):
                add('up_chord', t, min(b, t + BAR) - 0.05, p, 34)
    if 'arp:upright' in lay:
        up = sorted({place((root + iv) % 12, 67) for iv in ivs})
        t, j = a + PULSE, 0
        while t < b - 1e-6:
            add('up_arp', t, t + PULSE, up[j % len(up)], 26)
            t += PULSE * 2
            j += 1
    lob = place(bass, 33)
    if 'bass:pizz' in lay:
        for t in sorted({a} | {x for x in (a + BAR * k for k in range(1, 8)) if x < b - 0.5}):
            add('pizz', t, t + PULSE * 1.5, lob, 66)
            if BAR >= 3 and t + BAR / 2 < b - 0.4:
                add('pizz', t + BAR / 2, t + BAR / 2 + PULSE, place((root + 7) % 12, 33), 58)
    if 'bass:walk' in lay:
        nxt_root = chord_at(b + 0.01)[4] if b < END_BEAT_H else bass
        steps = [lob, place((root + ivs[1]) % 12, 33), place((root + 7) % 12, 33), place(nxt_root, 33) - 1]
        t, j = a, 0
        while t < b - 1e-6:
            add('pizz', t, t + PULSE * 0.9, steps[j % 4] if t + PULSE < b - 1e-6 or j == 0 else steps[3], 62)
            t += PULSE
            j += 1

grid = 0.0
while grid < END_BEAT_H - 1e-6:
    lay = layers_at(grid)
    k = round(grid / PULSE)
    in_bar = round((grid % BAR) / PULSE)
    if 'kit:hat' in lay and in_bar % 2 == 1:
        add('hat', grid, grid + 0.2, 42, 40)
    if 'kit:brush' in lay:
        add('brush', grid, grid + PULSE, 38, 44 if in_bar % 2 else 34)
    if 'kit:lofi' in lay:
        if in_bar == 0 or (BAR / PULSE >= 4 and in_bar == 2):
            add('kick', grid, grid + 0.3, 36, 70)
        if BAR / PULSE >= 4 and in_bar == 2:
            add('kick', grid + 0.5 * PULSE, grid + PULSE, 36, 52)
        if in_bar % 2 == 1:
            add('rim', grid + 0.03, grid + 0.3, 37, 58)
    if 'kit:hat8' in lay:
        for h in (0, 1):
            add('hat', grid + h * PULSE / 2 + (0.1 * PULSE if h else 0), grid + h * PULSE / 2 + 0.2, 42, 34 if h else 40)
    grid += PULSE
for amb in ('fire', 'wind', 'rain', 'vinyl'):
    if f'amb:{amb}' in LAYERS['A1']:
        add(amb, 0, END_BEAT_H, 60, 64)

for name in PASSES + ['O']:
    s = sections.get(name)
    if not s:
        continue
    if has(s['start_beat'], 'bell:tubular'):
        add('tubular', s['start_beat'], s['start_beat'] + 6, place(chord_at(s['start_beat'])[2], 60), 34)


SLEIGH_PER_MIN = 3.3
SLEIGH_RANGE = (8, 12)
celesta_on = [n[0] for n in parts.get('celesta', [])]


def sleigh_time(e):
    return e['beat'] + e['duration'] / 2


sleigh_spots = [e for e in melody if e['section'] in PASSES and e['duration'] >= 1.0 and has(e['beat'], 'bells:sleigh')
                and all(abs(sleigh_time(e) - c) >= 0.4 for c in celesta_on)]
if sleigh_spots:
    first, last = sleigh_spots[0]['beat'], sleigh_spots[-1]['beat']
    minutes = (seconds(last) - seconds(first)) / 60
    count = min(SLEIGH_RANGE[1], max(SLEIGH_RANGE[0], round(minutes * SLEIGH_PER_MIN)), len(sleigh_spots))
    step = (last - first) / count
    taken = []
    for k in range(count):
        target = first + step * (k + 0.5)
        free = [e for e in sleigh_spots if all(abs(e['beat'] - t) >= 0.6 * step for t in taken)]
        if not free:
            break
        e = min(free, key=lambda e: abs(e['beat'] - target))
        taken.append(e['beat'])
        add('sleigh', sleigh_time(e), sleigh_time(e) + 1.0, 60, rng.randint(32, 40))


def merge(notes):
    notes.sort(key=lambda n: (n[2], n[0]))
    out = []
    for n in notes:
        if out and out[-1][2] == n[2] and out[-1][1] >= n[0] - 0.05 and out[-1][1] - n[0] < 0.15:
            out[-1][1] = max(out[-1][1], n[1])
        elif out and out[-1][2] == n[2] and out[-1][1] > n[0] - 0.02:
            out[-1][1] = n[0] - 0.02
            out.append(n)
        else:
            out.append(n)
    return sorted([n for n in out if n[1] - n[0] >= 0.1], key=lambda n: n[0])


for k in list(parts):
    if k in ('vc', 'vla', 'organ', 'choir', 'horn', 'vln', 'piano_comp', 'up_chord'):
        parts[k] = merge(parts[k])
    else:
        parts[k].sort(key=lambda n: n[0])

TOTAL = seconds(END_BEAT) + 8.0
N = int(TOTAL * SR)


def timed(notes, lag=0.0, jitter=0.006):
    return [(seconds(a) + lag + rng.uniform(-jitter, jitter), seconds(b), p, v) for a, b, p, v in notes]


def render_sf2(path, preset, notes, gain=-6.0):
    synth = tinysoundfont.Synth(samplerate=SR, gain=gain)
    synth.program_select(0, synth.sfload(path), 0, preset)
    ev = sorted([(t0, 1, p, v) for t0, t1, p, v in notes] + [(t1, 0, p, 0) for t0, t1, p, v in notes], key=lambda x: (x[0], x[1]))
    out, now = [], 0
    for when, on, p, v in ev + [(TOTAL, 0, 0, 0)]:
        target = int(max(when, 0) * SR)
        if target > now:
            out.append(np.frombuffer(synth.generate(target - now), dtype=np.float32).reshape(-1, 2).copy())
            now = target
        if p:
            synth.noteon(0, p, v) if on else synth.noteoff(0, p)
    return np.concatenate(out)[:N]


NOTE = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
index = json.load(open(f'{VSCO}/index.json'))
real = json.load(open(f'{REAL}/index.json'))
cache = {}


def sample_midi(inst, row):
    base = os.path.basename(row['file'])
    if inst == 'organ':
        return int(re.search(r'_(\d{3})_', base).group(1)) - 86
    m = re.search(r'_([A-G]#?)(\d)(?:_|\.)', base)
    return 12 * (int(m.group(2)) + (1 if inst == 'harp' else 2)) + NOTE[m.group(1)]


def load(path, offset=0.0):
    key = (path, offset)
    if key not in cache:
        x, sr = sf.read(path, dtype='float32', always_2d=True)
        if x.shape[1] == 1:
            x = np.repeat(x, 2, 1)
        x = x[int(offset * sr):]
        seg = x[int(0.05 * sr):int(1.5 * sr)]
        cache[key] = (x / (np.sqrt((seg ** 2).mean()) + 1e-9), sr)
    return cache[key]


def extend(x, need, sr, fade=0.6):
    if len(x) >= need:
        return x
    nf = int(fade * sr)
    body = x[int(0.3 * len(x)):]
    ramp = np.linspace(0, 1, nf)[:, None]
    out = x
    while len(out) < need:
        out = np.concatenate([out[:-nf], out[-nf:] * (1 - ramp) + body[:nf] * ramp, body[nf:]])
    return out


def place_audio(out, y, t0):
    start = int(max(t0, 0) * SR)
    if start < len(out):
        out[start:start + len(y)] += y[:len(out) - start]


def render_samples(inst, notes, attack, release, offset=0.0, round_robin=False):
    if inst in real:
        rows = [(r['midi'] + r['tune'] / 100, r['layer'], f"{REAL}/{r['file']}") for r in real[inst]]
    else:
        rows = [(sample_midi(inst, r), r['layer'], f"{VSCO}/{r['file']}") for r in index[inst]]
    layers = sorted({r[1] for r in rows})
    out = np.zeros((N, 2), dtype=np.float32)
    turn = {}
    for t0, t1, p, v in notes:
        layer = layers[0] if v < 72 or len(layers) == 1 else layers[-1]
        best = min([r for r in rows if r[1] == layer], key=lambda r: (abs(r[0] - p), r[0] < p))
        same = sorted(r for r in rows if r[1] == layer and abs(r[0] - best[0]) < 0.5)
        k = (round(best[0]), layer)
        turn[k] = turn.get(k, -1) + 1
        m, _, path = same[turn[k] % len(same)] if round_robin else best
        x, sr = load(path, offset)
        ratio = 2 ** ((p - m) / 12) * sr / SR
        need = int((t1 - t0 + release) * SR)
        x = extend(x, int(need * ratio) + 2, sr)
        pos = np.arange(need) * ratio
        pos = pos[pos < len(x) - 1]
        y = np.stack([np.interp(pos, np.arange(len(x)), x[:, c]) for c in range(2)], 1)
        env = np.ones(len(y))
        na = min(len(y), max(1, int(attack * SR)))
        env[:na] = np.linspace(0, 1, na) ** 1.5
        rs = int((t1 - t0) * SR)
        if rs < len(y):
            env[rs:] = np.linspace(1, 0, len(y) - rs) ** 2
        place_audio(out, y * env[:, None] * (v / 100) ** 1.6, t0)
    return out


def render_sleigh(notes):
    files = sorted(f for f in os.listdir(f'{VSCO}/Percussion') if f.startswith('Sleighbells'))
    out = np.zeros((N, 2), dtype=np.float32)
    for k, (t0, t1, p, v) in enumerate(notes):
        x, sr = load(f'{VSCO}/Percussion/{files[k % len(files)]}')
        pos = np.arange(0, len(x) - 1, sr / SR)
        y = np.stack([np.interp(pos, np.arange(len(x)), x[:, c]) for c in range(2)], 1)
        place_audio(out, y * (v / 100) ** 1.6, t0)
    return out


ONE = os.path.expanduser('~/music-tools/sfz/real/vcsl')
noise_rng = np.random.default_rng(5)


def render_hits(files, notes):
    out = np.zeros((N, 2), dtype=np.float32)
    for k, (t0, t1, p, v) in enumerate(notes):
        x, sr = load(files[k % len(files)])
        pos = np.arange(0, len(x) - 1, sr / SR)
        y = np.stack([np.interp(pos, np.arange(len(x)), x[:, c]) for c in range(2)], 1)
        place_audio(out, y * (v / 100) ** 1.6, t0)
    return out


def kit(name, pick):
    return sorted(f'{ONE}/{name}/{f}' for f in os.listdir(f'{ONE}/{name}') if pick in f)


AMBI = os.path.expanduser('~/music-tools/sfz/real/ambience')


def render_bed(name):
    x, sr = sf.read(sorted(f'{AMBI}/{name}/{f}' for f in os.listdir(f'{AMBI}/{name}') if f.endswith('.wav'))[0],
                    dtype='float32', always_2d=True)
    if x.shape[1] == 1:
        x = np.repeat(x, 2, 1)
    if sr != SR:
        pos = np.arange(0, len(x) - 1, sr / SR)
        x = np.stack([np.interp(pos, np.arange(len(x)), x[:, c]) for c in range(2)], 1)
    fade = int(3 * SR)
    start = int(noise_rng.integers(0, max(1, len(x) // 3)))
    out = x[start:]
    ramp = np.linspace(0, 1, fade)[:, None]
    while len(out) < N:
        out = np.concatenate([out[:-fade], out[-fade:] * np.sqrt(1 - ramp) + x[:fade] * np.sqrt(ramp), x[fade:]])
    return ramp_in(out[:N].astype(np.float64))


def ramp_in(x, s=3.0, crest=3.5):
    ceiling = crest * np.sqrt((x ** 2).mean())
    x = np.tanh(x / ceiling) * ceiling
    n = int(s * SR)
    x[:n] *= np.linspace(0, 1, n)[:, None] ** 2
    return x


RENDER = {
    'piano_mel': lambda n: render_sf2(SALAMANDER, 0, timed(n, lag=0.012)),
    'piano_arp': lambda n: render_sf2(SALAMANDER, 0, timed(n)),
    'piano_oct': lambda n: render_sf2(SALAMANDER, 0, timed(n, lag=0.012)),
    'felt_mel': lambda n: render_samples('felt', timed(n, lag=0.012), 0.002, 0.6, round_robin=True),
    'felt_oct': lambda n: render_samples('felt', timed(n, lag=0.012), 0.002, 0.6, round_robin=True),
    'flute': lambda n: render_samples('flute', timed(n, jitter=0.004), 0.08, 0.35),
    'harp': lambda n: render_samples('harp', timed(n), 0.003, 0.9),
    'celesta': lambda n: render_samples('celeste', timed(n), 0.002, 1.6),
    'celesta_layer': lambda n: render_samples('celeste', timed(n, lag=0.012), 0.002, 1.2),
    'celesta_short': lambda n: render_samples('celeste', timed(n, lag=0.012), 0.002, 0.4),
    'piano_left': lambda n: render_sf2(SALAMANDER, 0, timed(n, lag=0.02, jitter=0.01)),
    'vc': lambda n: render_samples('vc', timed(n, jitter=0), 0.5, 0.8),
    'vla': lambda n: render_samples('vla', timed(n, jitter=0), 0.5, 0.8),
    'vln': lambda n: render_samples('vln', timed(n, jitter=0), 0.6, 0.8),
    'horn': lambda n: render_samples('horn', timed(n, jitter=0), 0.4, 0.7),
    'organ': lambda n: render_samples('organ', timed(n, jitter=0), 0.25, 0.5),
    'choir': lambda n: render_samples('chorus', timed(n, jitter=0), 0.8, 1.2, offset=0.9),
    'tubular': lambda n: render_samples('tubular', timed(n, jitter=0), 0.002, 5.0),
    'sleigh': render_sleigh,
    'piano_comp': lambda n: render_sf2(SALAMANDER, 0, timed(n, lag=0.02, jitter=0.01)),
    'up_mel': lambda n: render_samples('upright', timed(n, lag=0.03, jitter=0.012), 0.002, 0.5),
    'up_chord': lambda n: render_samples('upright', timed(n, lag=0.01, jitter=0.015), 0.002, 0.5),
    'up_arp': lambda n: render_samples('upright', timed(n, jitter=0.01), 0.002, 0.8),
    'pizz': lambda n: render_samples('pizz', timed(n, jitter=0.008), 0.002, 0.35),
    'hat': lambda n: render_hits(kit('hihat', 'Close'), timed(n, jitter=0.006)),
    'kick': lambda n: render_hits(kit('kick', 'v3'), timed(n, jitter=0.004)),
    'rim': lambda n: render_hits(kit('snare', 'Xstick'), timed(n, jitter=0.008)),
    'brush': lambda n: render_hits(kit('brush', ''), timed(n, jitter=0.006)),
    'fire': lambda n: render_bed('fire'),
    'wind': lambda n: render_bed('wind'),
    'rain': lambda n: render_bed('rain'),
    'vinyl': lambda n: render_bed('vinyl'),
}
LEVEL = {'celesta_short': -16, 'piano_left': -12, 'piano_comp': -10, 'up_mel': 0, 'up_chord': -9, 'up_arp': -15, 'pizz': -13, 'hat': -25, 'kick': -19, 'rim': -21,
         'brush': -27, 'fire': -21, 'wind': -27, 'rain': -20, 'vinyl': -33, 'piano_mel': 0, 'piano_oct': -11, 'felt_mel': 0, 'felt_oct': -11, 'flute': 0, 'piano_arp': -9, 'harp': -7, 'celesta': -12, 'celesta_layer': -11, 'vc': -13, 'vla': -14, 'vln': -16,
         'horn': -16, 'organ': -12, 'choir': -12, 'tubular': -16, 'sleigh': -24}
HP = {'celesta_short': 300, 'piano_left': 80, 'piano_comp': 110, 'up_mel': 80, 'up_chord': 110, 'up_arp': 150, 'pizz': 50, 'hat': 500, 'kick': 45, 'rim': 200,
      'brush': 1500, 'fire': 40, 'wind': 150, 'rain': 300, 'vinyl': 500, 'piano_mel': 80, 'piano_oct': 300, 'felt_mel': 70, 'felt_oct': 300, 'flute': 200, 'piano_arp': 90, 'harp': 80, 'celesta': 300, 'celesta_layer': 300, 'vc': 80, 'vla': 140, 'vln': 200,
      'horn': 120, 'organ': 120, 'choir': 150, 'tubular': 150, 'sleigh': 400}
WIDTH = {k: 0.7 for k in LEVEL}
WIDTH.update({'fire': 1.0, 'wind': 1.0, 'rain': 1.0, 'vinyl': 0.3, 'pizz': 0.0, 'kick': 0.0, 'rim': 0.2, 'hat': 0.4, 'brush': 0.5,
              'up_mel': 0.35, 'up_chord': 0.4, 'up_arp': 0.5, 'piano_comp': 0.5})
if not VIBE.startswith('snowglobe') and VIBE != 'church':
    WIDTH.update({'piano_mel': 0.4, 'piano_arp': 0.45})
SEND = {'celesta_short': 0.6, 'piano_left': 0.5, 'piano_comp': 0.45, 'up_mel': 0.35, 'up_chord': 0.35, 'up_arp': 0.5, 'pizz': 0.2, 'hat': 0.25, 'kick': 0.1,
        'rim': 0.3, 'brush': 0.3, 'fire': 0.02, 'wind': 0.05, 'rain': 0.03, 'vinyl': 0.0, 'piano_mel': 0.5, 'piano_oct': 0.65, 'felt_mel': 0.45, 'felt_oct': 0.6, 'flute': 0.55, 'piano_arp': 0.5, 'harp': 0.6, 'celesta': 0.7, 'celesta_layer': 0.6, 'vc': 0.45, 'vla': 0.55, 'vln': 0.6,
        'horn': 0.6, 'organ': 0.6, 'choir': 0.65, 'tubular': 0.7, 'sleigh': 0.5}


def norm(x):
    act = x[np.abs(x).max(1) > 1e-4]
    return x / (np.sqrt((act ** 2).mean()) + 1e-9) if len(act) else x


dry = np.zeros((N, 2))
send = np.zeros((N, 2))
for k, notes in parts.items():
    x = norm(RENDER[k](notes).astype(np.float64))
    y = sosfiltfilt(butter(2, HP[k], 'highpass', fs=SR, output='sos'), x, axis=0)
    mid_, side = (y[:, 0] + y[:, 1]) / 2, (y[:, 0] - y[:, 1]) / 2 * WIDTH[k]
    y = np.stack([mid_ + side, mid_ - side], 1) * 10 ** (LEVEL[k] / 20)
    dry += y
    send += y * SEND[k]

STATIC_T60 = {(20, 250): 1.0, (250, 1000): 1.6, (1000, 4000): 1.5, (4000, SR / 2 - 1): 1.1}
STATIC_PREDELAY_S = 0.02
STATIC_LOW_CUT = 200
STATIC_SEND_HP = 250
STATIC_WET_WIDTH = 0.6


def static_ir(length_s=3.5):
    r = np.random.default_rng(3)
    n = int(length_s * SR)
    t = np.arange(n) / SR
    ir = np.zeros((n, 2))
    for c in range(2):
        noise = r.standard_normal(n)
        for (lo, hi), t60 in STATIC_T60.items():
            ir[:, c] += sosfilt(butter(4, [lo, hi], 'bandpass', fs=SR, output='sos'), noise) * 10 ** (-3 * t / t60)
    ir *= np.minimum(1, t / 0.03)[:, None]
    ir = sosfilt(butter(2, STATIC_LOW_CUT, 'highpass', fs=SR, output='sos'), ir, axis=0)
    return np.concatenate([np.zeros((int(STATIC_PREDELAY_S * SR), 2)), ir]) / np.sqrt((ir ** 2).sum())


if LAYERS['reverb'][0] == 'static':
    src = sosfiltfilt(butter(2, STATIC_SEND_HP, 'highpass', fs=SR, output='sos'), send, axis=0)
    ir = static_ir()
    wet = np.stack([fftconvolve(src[:, c], ir[:, c])[:N] for c in range(2)], 1)
    wm, ws = (wet[:, 0] + wet[:, 1]) / 2, (wet[:, 0] - wet[:, 1]) / 2 * STATIC_WET_WIDTH
    wet = np.stack([wm + ws, wm - ws], 1)
    wet *= LAYERS['reverb'][1] * np.sqrt((dry ** 2).mean()) / (np.sqrt((wet ** 2).mean()) + 1e-12)
else:
    eng = daw.RenderEngine(SR, 512)
    pb = eng.make_playback_processor('src', send.T.astype(np.float32))
    hall = eng.make_plugin_processor('hall', HALL)
    decay, size = LAYERS['reverb']
    SETTINGS = {2: (0, 0, 100), 3: (0, 0, 100), 4: (100, 0, 100), 5: (size, 10, 60), 6: (80, 50, 150), 7: (18, 0, 100),
                8: (85, 0, 100), 9: (120, 0, 200), 11: (0.8, 0.5, 2.5), 12: (7000, 1000, 16000), 17: (decay, 0.1, 10), 19: (20, 0, 100)}
    for i, (v, lo, hi) in SETTINGS.items():
        hall.set_parameter(i, (v - lo) / (hi - lo))
    eng.load_graph([(pb, []), (hall, ['src'])])
    eng.render(TOTAL)
    wet = eng.get_audio().T[:N].astype(np.float64)
    wet *= 0.6 * np.sqrt((dry ** 2).mean()) / (np.sqrt((wet ** 2).mean()) + 1e-12)
mix = dry + wet
if VIBE == 'lofi':
    mix = sosfiltfilt(butter(2, 5500, 'lowpass', fs=SR, output='sos'), mix, axis=0)
    tt = np.arange(len(mix)) / SR
    pos = np.arange(len(mix)) + 0.0015 * SR / (2 * np.pi * 0.35) * np.sin(2 * np.pi * 0.35 * tt)
    pos = np.clip(pos, 0, len(mix) - 1)
    mix = np.stack([np.interp(pos, np.arange(len(mix)), mix[:, c]) for c in range(2)], 1)

bounds = [(seconds(sections[s]['start_beat']), seconds(sections[s]['end_beat'])) for s in PASSES]
rms = {s: 20 * np.log10(np.sqrt((mix[int(a * SR):int(b * SR)] ** 2).mean())) for s, (a, b) in zip(PASSES, bounds)}
corr_db = {s: PASS_DB[s] - (rms[s] - rms['A1']) for s in PASSES}
pts_t = [0.0]
pts_g = [corr_db['A1']]
for s, (a, b) in zip(PASSES, bounds):
    pts_t += [a + 0.5, b - 0.5]
    pts_g += [corr_db[s], corr_db[s]]
pts_t.append(TOTAL)
pts_g.append(corr_db['A3'])
g = 10 ** (np.interp(np.arange(N) / SR, pts_t, pts_g) / 20)
mix *= g[:, None]

hop = SR // 20
music_end = int(seconds(END_BEAT) * SR)
frames = np.sqrt((mix[:len(mix) // hop * hop, :].reshape(-1, hop, 2) ** 2).mean((1, 2)))
floor = frames.max() * 10 ** (-60 / 20)
quiet = [i for i in range(music_end // hop, len(frames)) if frames[i] < floor]
last = (quiet[0] if quiet else len(frames)) * hop
mix = mix[:last]
fade = int(SR * 1.5)
mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
mix = mix / (np.abs(mix).max() + 1e-9) * 0.7
sf.write(OUT + '_mix.wav', mix.astype(np.float32), SR, subtype='FLOAT')
after = {s: round(20 * np.log10(np.sqrt((mix[int(a * SR):int(b * SR)] ** 2).mean())), 2) for s, (a, b) in zip(PASSES, bounds)}

TPQ = 480
mid = mido.MidiFile(ticks_per_beat=TPQ)
meta = mido.MidiTrack()
meta.append(mido.MetaMessage('time_signature', numerator=METER[0], denominator=METER[1], time=0))
lt = 0
for e in edges:
    tick = int(round(e * TPQ))
    meta.append(mido.MetaMessage('set_tempo', tempo=int(60_000_000 / (BPM * factor(e))), time=tick - lt))
    lt = tick
mid.tracks.append(meta)
PROGRAM = {'celesta_short': 8, 'piano_left': 0, 'piano_comp': 0, 'up_mel': 0, 'up_chord': 0, 'up_arp': 0, 'pizz': 45, 'hat': 0, 'kick': 0, 'rim': 0, 'piano_mel': 0, 'piano_oct': 0, 'felt_mel': 0, 'felt_oct': 0, 'piano_arp': 0, 'flute': 73, 'harp': 46, 'celesta': 8, 'celesta_layer': 8, 'vc': 42, 'vla': 41, 'vln': 40, 'horn': 60,
           'organ': 19, 'choir': 53, 'tubular': 14, 'sleigh': 0}
DRUM_NOTE = {'sleigh': 83, 'hat': 42, 'kick': 36, 'rim': 37}
for ch, (k, notes) in enumerate([(k, n) for k, n in parts.items() if k in PROGRAM]):
    ch = 9 if k in DRUM_NOTE else ch if ch < 9 else ch + 1
    tr = mido.MidiTrack()
    tr.append(mido.MetaMessage('track_name', name=k, time=0))
    tr.append(mido.Message('program_change', program=PROGRAM[k], channel=ch, time=0))
    msgs = sorted([(int(round(a * TPQ)), 1, DRUM_NOTE.get(k, p), v) for a, b, p, v in notes]
                  + [(int(round(b * TPQ)), 0, DRUM_NOTE.get(k, p), 0) for a, b, p, v in notes], key=lambda m: (m[0], m[1]))
    t = 0
    for tick, on, p, v in msgs:
        tr.append(mido.Message('note_on' if on else 'note_off', note=p, velocity=v, channel=ch, time=tick - t))
        t = tick
    mid.tracks.append(tr)
mid.save(OUT + '.mid')
print(json.dumps({'vibe': VIBE, 'seconds': round(len(mix) / SR, 1), 'notes': {k: len(v) for k, v in parts.items()},
                  'pass_rms_before': {s: round(v - rms['A1'], 2) for s, v in rms.items()},
                  'pass_rms_after': {s: round(v - after['A1'], 2) for s, v in after.items()},
                  'pass_bounds_s': [[round(a, 1), round(b, 1)] for a, b in bounds],
                  'corr_lr': round(float(np.corrcoef(mix[:, 0], mix[:, 1])[0, 1]), 2)}))

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
from scipy.signal import butter, sosfiltfilt

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
        'A1': ['melody:piano', 'arp:harp', 'bed:strings', 'answer:celesta'],
        'A2': ['melody:piano', 'arp:harp', 'bed:strings', 'answer:celesta', 'bells:sleigh'],
        'A3': ['melody:piano', 'arp:harp+', 'bed:strings', 'answer:celesta', 'bells:sleigh'],
        'reverb': (3.0, 30),
    },
    'church': {
        'A1': ['melody:piano', 'bed:organ', 'bed:choir', 'bell:tubular'],
        'A2': ['melody:piano', 'bed:organ', 'bed:choir', 'bell:tubular', 'arp:piano'],
        'A3': ['melody:piano', 'bed:organ', 'bed:choir', 'bell:tubular', 'arp:piano', 'high:choir'],
        'reverb': (4.2, 45),
    },
}[VIBE]

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
    add('piano_mel', e['beat'], end, e['pitch'], vel)

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
    bed = sorted({place((root + iv) % 12, 52) for iv in ivs[:4]})
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

for name in PASSES + ['O']:
    s = sections.get(name)
    if not s:
        continue
    if has(s['start_beat'], 'bell:tubular'):
        add('tubular', s['start_beat'], s['start_beat'] + 6, place(chord_at(s['start_beat'])[2], 60), 34)
    if has(s['start_beat'], 'bells:sleigh') and name in PASSES:
        t = s['start_beat']
        while t < s['end_beat'] - 1e-6:
            add('sleigh', t, t + 1.0, 60, 30 if (t - s['start_beat']) % 6 else 38)
            t += BAR


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
    if k in ('vc', 'vla', 'organ', 'choir', 'horn', 'vln'):
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


def render_samples(inst, notes, attack, release, offset=0.0):
    if inst in real:
        rows = [(r['midi'] + r['tune'] / 100, r['layer'], f"{REAL}/{r['file']}") for r in real[inst]]
    else:
        rows = [(sample_midi(inst, r), r['layer'], f"{VSCO}/{r['file']}") for r in index[inst]]
    layers = sorted({r[1] for r in rows})
    out = np.zeros((N, 2), dtype=np.float32)
    for t0, t1, p, v in notes:
        layer = layers[0] if v < 72 or len(layers) == 1 else layers[-1]
        m, _, path = min([r for r in rows if r[1] == layer], key=lambda r: (abs(r[0] - p), r[0] < p))
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


RENDER = {
    'piano_mel': lambda n: render_sf2(SALAMANDER, 0, timed(n, lag=0.012)),
    'piano_arp': lambda n: render_sf2(SALAMANDER, 0, timed(n)),
    'flute': lambda n: render_samples('flute', timed(n, jitter=0.004), 0.08, 0.35),
    'harp': lambda n: render_samples('harp', timed(n), 0.003, 0.9),
    'celesta': lambda n: render_samples('celeste', timed(n), 0.002, 1.6),
    'vc': lambda n: render_samples('vc', timed(n, jitter=0), 0.5, 0.8),
    'vla': lambda n: render_samples('vla', timed(n, jitter=0), 0.5, 0.8),
    'vln': lambda n: render_samples('vln', timed(n, jitter=0), 0.6, 0.8),
    'horn': lambda n: render_samples('horn', timed(n, jitter=0), 0.4, 0.7),
    'organ': lambda n: render_samples('organ', timed(n, jitter=0), 0.25, 0.5),
    'choir': lambda n: render_samples('chorus', timed(n, jitter=0), 0.8, 1.2, offset=0.9),
    'tubular': lambda n: render_samples('tubular', timed(n, jitter=0), 0.002, 5.0),
    'sleigh': render_sleigh,
}
LEVEL = {'piano_mel': 0, 'flute': 0, 'piano_arp': -9, 'harp': -7, 'celesta': -12, 'vc': -13, 'vla': -14, 'vln': -16,
         'horn': -16, 'organ': -12, 'choir': -12, 'tubular': -16, 'sleigh': -24}
HP = {'piano_mel': 80, 'flute': 200, 'piano_arp': 90, 'harp': 80, 'celesta': 300, 'vc': 80, 'vla': 140, 'vln': 200,
      'horn': 120, 'organ': 120, 'choir': 150, 'tubular': 150, 'sleigh': 400}
WIDTH = {k: 0.7 for k in LEVEL}
SEND = {'piano_mel': 0.5, 'flute': 0.55, 'piano_arp': 0.5, 'harp': 0.6, 'celesta': 0.7, 'vc': 0.45, 'vla': 0.55, 'vln': 0.6,
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
PROGRAM = {'piano_mel': 0, 'piano_arp': 0, 'flute': 73, 'harp': 46, 'celesta': 8, 'vc': 42, 'vla': 41, 'vln': 40, 'horn': 60,
           'organ': 19, 'choir': 53, 'tubular': 14, 'sleigh': 0}
for ch, (k, notes) in enumerate(parts.items()):
    ch = 9 if k == 'sleigh' else ch if ch < 9 else ch + 1
    tr = mido.MidiTrack()
    tr.append(mido.MetaMessage('track_name', name=k, time=0))
    tr.append(mido.Message('program_change', program=PROGRAM[k], channel=ch, time=0))
    msgs = sorted([(int(round(a * TPQ)), 1, p if k != 'sleigh' else 83, v) for a, b, p, v in notes]
                  + [(int(round(b * TPQ)), 0, p if k != 'sleigh' else 83, 0) for a, b, p, v in notes], key=lambda m: (m[0], m[1]))
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

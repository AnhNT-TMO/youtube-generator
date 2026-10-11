import glob, json, os, re, sys

D = sys.argv[1]
NOTE = {'c': 0, 'c#': 1, 'd': 2, 'd#': 3, 'e': 4, 'f': 5, 'f#': 6, 'g': 7, 'g#': 8, 'a': 9, 'a#': 10, 'b': 11}


def midi(name, octave):
    return 12 * (int(octave) + 1) + NOTE[name.lower()]


def sfz_regions(path):
    rows = {}
    for block in open(path).read().split('<region>')[1:]:
        kv = dict(re.findall(r'^(\w+)=(.+?)\s*$', block, re.M))
        if 'sample' in kv:
            rows[os.path.basename(kv['sample'])] = (int(kv.get('tune', 0)), float(kv.get('volume', 0)))
    return rows


index = {'celeste': [], 'chorus': [], 'tubular': [], 'handchimes': []}
cel = sfz_regions(f'{D}/sso/Celeste.sfz')
for f in sorted(os.listdir(f'{D}/sso/Celeste')):
    m = re.match(r'celeste-([a-g]#?)(\d)-(soft|hard)\.flac', f)
    tune = cel.get(f, cel.get(f.replace('soft', 'hard'), (0, 0)))[0]
    index['celeste'].append({'file': f'sso/Celeste/{f}', 'midi': midi(m[1], m[2]), 'tune': tune, 'layer': 0 if m[3] == 'soft' else 1})
cho = sfz_regions(f'{D}/sso/mixed-chorus.sfz')
for f in sorted(os.listdir(f'{D}/sso/Chorus')):
    m = re.match(r'chorus-(female|male)-([a-g]#?)(\d)\.wav', f)
    tune, vol = cho.get(f, (0, 0))
    index['chorus'].append({'file': f'sso/Chorus/{f}', 'midi': midi(m[2], m[3]), 'tune': tune, 'layer': 0, 'volume': vol})
for f in sorted(os.listdir(f'{D}/vcsl/tubular')):
    m = re.match(r'chimes_([A-G]#?)(\d)_', f)
    index['tubular'].append({'file': f'vcsl/tubular/{f}', 'midi': midi(m[1], m[2]) + 12, 'tune': 0, 'layer': 0})
for f in sorted(os.listdir(f'{D}/vcsl/handchimes')):
    m = re.match(r'sus_([A-G]#?)(\d)_', f)
    index['handchimes'].append({'file': f'vcsl/handchimes/{f}', 'midi': midi(m[1], m[2]) + 12, 'tune': 0, 'layer': 0})
PITCHED = {'upright': ('vcsl/upright/*.wav', r'_vl(\d)_'), 'folkharp': ('vcsl/folkharp/*.wav', r'_v(\d)_'),
           'kalimba': ('vcsl/kalimba/*.wav', None), 'felt': ('pianobook/pleyel_felt/Pleyel Felt-rr*.wav', r'-rr\d-([pf])-')}
LAYER_NAME = {'p': 0, 'f': 1}
NAME = {'felt': r'-([a-g]#?)(\d)\.wav$'}
NAMED_OCTAVE_TRUSTED = {'felt'}
if any(glob.glob(f'{D}/{pat}') for pat, _ in PITCHED.values()):
    import librosa
    import numpy as np
    for name, (pat, lay) in PITCHED.items():
        rows = []
        for f in sorted(glob.glob(f'{D}/{pat}')):
            y, sr = librosa.load(f, sr=44100, mono=True, duration=3.0)
            f0, ok, _ = librosa.pyin(y[int(0.05 * sr):], fmin=25, fmax=3000, sr=sr, frame_length=4096)
            f0 = f0[ok & np.isfinite(f0)]
            m = re.search(NAME.get(name, r'_([A-G]#?)(\d)_'), os.path.basename(f))
            named = midi(m[1], m[2]) + 12
            if len(f0) < 5 and name not in NAMED_OCTAVE_TRUSTED:
                print('no pitch', f)
                continue
            est = float(np.median(librosa.hz_to_midi(f0))) if len(f0) >= 5 else float(named)
            octv = 0 if name in NAMED_OCTAVE_TRUSTED else round((est - named) / 12) * 12
            tag = re.search(lay, f).group(1) if lay else '0'
            layer = LAYER_NAME[tag] if tag in LAYER_NAME else int(tag)
            cents = round((est - named - octv) * 100)
            rows.append({'file': os.path.relpath(f, D), 'midi': named + octv, 'tune': cents if abs(cents) <= 40 else 0, 'layer': layer})
        index[name] = rows
json.dump(index, open(f'{D}/index.json', 'w'), indent=1)
print({k: (len(v), min(r['midi'] for r in v), max(r['midi'] for r in v)) for k, v in index.items()})

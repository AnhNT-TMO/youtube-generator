import glob
import json
import os
import re
import sys

import librosa
import numpy as np

V = os.path.expanduser('~/music-tools/sfz/VSCO-2-CE')
SETS = {
    'harp': 'Strings/Harp/*.wav',
    'horn': 'Brass/F Horn/sus/*.wav',
    'glock': 'Percussion/Glock/*.wav',
    'vln': 'Strings/Violin Section/susVib/*.wav',
    'vla': 'Strings/Viola Section/susvib/*.wav',
    'vc': 'Strings/Cello Section/susvib/*.wav',
    'cb': 'Strings/Solo Contrabass/SusNV/*.wav',
    'pizz': 'Strings/Solo Contrabass/Pizz/*.wav',
    'organ': 'Keys/Organ/Quiet/NT5_Man3*.wav',
    'pedal': 'Keys/Organ/Quiet/NT5_Pedal*.wav',
    'flute': 'Woodwinds/Flute/susNV/*.wav',
}
index = json.load(open(f'{V}/index.json')) if os.path.exists(f'{V}/index.json') else {}
ONLY = sys.argv[1].split(',') if len(sys.argv) > 1 else list(SETS)
for name, pat in SETS.items():
    if name not in ONLY:
        continue
    rows = []
    for f in sorted(glob.glob(f'{V}/{pat}')):
        y, sr = librosa.load(f, sr=44100, mono=True, duration=4.0)
        f0, vflag, _ = librosa.pyin(y[int((0.05 if name in ('harp', 'glock', 'pizz') else 0.4) * sr):], fmin=30, fmax=4500 if name == 'glock' else 2100, sr=sr, frame_length=4096)
        f0 = f0[vflag & np.isfinite(f0)]
        if len(f0) < 5:
            print('no pitch', f)
            continue
        midi = float(np.median(librosa.hz_to_midi(f0)))
        layer = re.search(r'_v(\d)', os.path.basename(f))
        rms = float(np.sqrt((y[int(0.5 * sr):int(3 * sr)] ** 2).mean()))
        rows.append({'file': os.path.relpath(f, V), 'midi': round(midi, 2), 'layer': int(layer.group(1)) if layer else 1, 'rms': round(rms, 4)})
    index[name] = rows
    print(name, len(rows), [(os.path.basename(r['file'])[-24:], r['midi']) for r in rows])
json.dump(index, open(f'{V}/index.json', 'w'), indent=1)

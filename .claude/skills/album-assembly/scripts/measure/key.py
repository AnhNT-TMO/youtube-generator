from __future__ import annotations

import librosa
import numpy as np

from . import stems
from .common import load_cached, save_cached

MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
CAMELOT_MAJOR = {0: 8, 7: 9, 2: 10, 9: 11, 4: 12, 11: 1, 6: 2, 1: 3, 8: 4, 3: 5, 10: 6, 5: 7}
CAMELOT_MINOR = {9: 8, 4: 9, 11: 10, 6: 11, 1: 12, 8: 1, 3: 2, 10: 3, 5: 4, 0: 5, 7: 6, 2: 7}


def estimate(chroma_mean: np.ndarray) -> tuple[str, str, float]:
    best = (-2, None, None)
    for tonic in range(12):
        for mode, prof in (("major", MAJOR), ("minor", MINOR)):
            r = np.corrcoef(chroma_mean, np.roll(prof, tonic))[0, 1]
            if r > best[0]:
                best = (r, tonic, mode)
    r, tonic, mode = best
    cam = f"{CAMELOT_MAJOR[tonic]}B" if mode == "major" else f"{CAMELOT_MINOR[tonic]}A"
    return f"{NAMES[tonic]} {mode}", cam, float(r)


def analyze(path, force=False) -> dict:
    if not force and (c := load_cached(path, "key")):
        return c
    b, sr = stems.load_stem(path, "bass", sr=22050)
    o, _ = stems.load_stem(path, "other", sr=22050)
    y = b + o
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=2048)
    key, cam, conf = estimate(chroma.mean(axis=1))
    tail = chroma[:, -int(20 * sr / 2048):]
    key_end, cam_end, _ = estimate(tail.mean(axis=1))
    return save_cached(path, "key", {"key": key, "camelot": cam, "key_conf": conf,
                                     "ending_key": key_end, "ending_camelot": cam_end})

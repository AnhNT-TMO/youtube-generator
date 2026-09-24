from __future__ import annotations

import librosa
import numpy as np

from . import stems
from .common import frame_rms_db, load_cached, save_cached

HOP = 0.05


def vocal_activity(v: np.ndarray, sr: int) -> np.ndarray:
    rms, _ = frame_rms_db(v, sr, hop_s=HOP, win_s=0.1)
    loud = np.percentile(rms, 95)
    act = (rms > loud - 22) & (rms > -50)
    act = _close(act, int(0.4 / HOP))
    act = _open(act, int(0.4 / HOP))
    return act


def _runs(mask):
    runs, start = [], None
    for i, m in enumerate(np.append(mask, False)):
        if m and start is None:
            start = i
        elif not m and start is not None:
            runs.append((start, i))
            start = None
    return runs


def _close(mask, n):
    m = mask.copy()
    runs = _runs(~mask)
    for a, b in runs:
        if a > 0 and b < len(mask) and b - a < n:
            m[a:b] = True
    return m


def _open(mask, n):
    m = mask.copy()
    for a, b in _runs(mask):
        if b - a < n:
            m[a:b] = False
    return m


def analyze(path, force=False) -> dict:
    if not force and (c := load_cached(path, "vocal")):
        return c
    v, sr = stems.load_stem(path, "vocals", sr=16000)
    act = vocal_activity(v, sr)
    runs = [(a * HOP, b * HOP) for a, b in _runs(act)]
    dur = len(v) / sr
    out = {"vocal_ratio": float(act.mean()), "n_vocal_runs": len(runs)}
    real = [r for r in runs if r[1] - r[0] >= 1.5]
    out["vocal_start"] = float(real[0][0]) if real else None
    out["vocal_end"] = float(real[-1][1]) if real else None
    out["vocal_tail_free"] = float(dur - real[-1][1]) if real else None
    gaps = [b[0] - a[1] for a, b in zip(real[:-1], real[1:])]
    out["longest_vocal_gap"] = float(max(gaps)) if gaps else 0.0

    win = int(3 * sr)
    starts = []
    for a, b in runs:
        s = int(a * sr)
        while s + win <= int(b * sr):
            starts.append(s)
            s += win
    if len(starts) > 40:
        starts = [starts[i] for i in np.linspace(0, len(starts) - 1, 40).astype(int)]
    out["n_vocal_windows"] = len(starts)
    if starts:
        sel = starts[:: max(1, len(starts) // 30)][:30]
        f0s = []
        for s in sel:
            f0, vflag, _ = librosa.pyin(v[s:s + win], fmin=70, fmax=800, sr=sr, frame_length=1024, hop_length=320)
            f0s.append(f0[vflag & ~np.isnan(f0)])
        f0 = np.concatenate(f0s) if f0s else np.array([])
        if len(f0) > 50:
            out["f0_median_hz"] = float(np.median(f0))
            out["f0_median_midi"] = float(np.median(librosa.hz_to_midi(f0)))
    return save_cached(path, "vocal", out)

"""Nhóm B — beat/downbeat bằng beat_this, BPM, số phách/ô nhịp, độ ổn định tempo."""
from __future__ import annotations

import numpy as np

from .common import device, load_audio, load_cached, save_cached

_model = None


def _get_model():
    global _model
    if _model is None:
        from beat_this.inference import Audio2Beats
        _model = Audio2Beats(checkpoint_path="final0", device="cuda" if device() == "cuda" else "cpu", dbn=False)
    return _model


def _bpm(beats: np.ndarray) -> float | None:
    if len(beats) < 4:
        return None
    return float(60.0 / np.median(np.diff(beats)))


def analyze(path, force=False) -> dict:
    if not force and (c := load_cached(path, "rhythm")):
        return c
    y, sr = load_audio(path, sr=22050)
    beats, downbeats = _get_model()(y, sr)
    beats, downbeats = np.asarray(beats), np.asarray(downbeats)
    out = {"n_beats": int(len(beats)), "bpm": _bpm(beats)}
    if len(beats) >= 8:
        ibi = np.diff(beats)
        med = np.median(ibi)
        good = ibi[(ibi > 0.6 * med) & (ibi < 1.6 * med)]
        out["ibi_cv"] = float(np.std(good) / np.mean(good))
        # BPM phút đầu vs phút cuối (trong vùng có beat)
        first = beats[beats < beats[0] + 60]
        last = beats[beats > beats[-1] - 60]
        out["bpm_first_min"] = _bpm(first)
        out["bpm_last_min"] = _bpm(last)
        # BPM cục bộ mỗi 20s để thấy tempo có trôi không
        local = []
        for t0 in np.arange(beats[0], beats[-1] - 20, 20):
            seg = beats[(beats >= t0) & (beats < t0 + 20)]
            if (b := _bpm(seg)):
                local.append(b)
        out["bpm_local"] = local
    if len(downbeats) >= 3:
        counts = [int(((beats >= a) & (beats < b)).sum()) for a, b in zip(downbeats[:-1], downbeats[1:])]
        out["beats_per_bar"] = int(np.median(counts))
        out["bar_bpm"] = float(60.0 / np.median(np.diff(downbeats)))
    out["first_beat"] = float(beats[0]) if len(beats) else None
    return save_cached(path, "rhythm", out)

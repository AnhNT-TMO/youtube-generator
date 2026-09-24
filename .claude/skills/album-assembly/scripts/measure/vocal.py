from __future__ import annotations

import numpy as np

from .common import frame_rms_db

HOP = 0.05


def vocal_activity(v: np.ndarray, sr: int) -> np.ndarray:
    rms, _ = frame_rms_db(v, sr, hop_s=HOP, win_s=0.1)
    loud = np.percentile(rms, 95)
    act = (rms > loud - 22) & (rms > -50)
    act = _close(act, int(0.4 / HOP))
    act = _open(act, int(0.4 / HOP))
    return act


def runs(mask) -> list[tuple[int, int]]:
    out, start = [], None
    for i, m in enumerate(np.append(mask, False)):
        if m and start is None:
            start = i
        elif not m and start is not None:
            out.append((start, i))
            start = None
    return out


def _close(mask, n):
    m = mask.copy()
    for a, b in runs(~mask):
        if a > 0 and b < len(mask) and b - a < n:
            m[a:b] = True
    return m


def _open(mask, n):
    m = mask.copy()
    for a, b in runs(mask):
        if b - a < n:
            m[a:b] = False
    return m

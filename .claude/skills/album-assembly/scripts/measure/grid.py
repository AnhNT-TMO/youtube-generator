from __future__ import annotations

import numpy as np

from .common import device, load_array, load_audio, load_cached, save_array, save_cached

_model = None


def _get_model():
    global _model
    if _model is None:
        from beat_this.inference import Audio2Beats
        _model = Audio2Beats(checkpoint_path="final0", device="cuda" if device() == "cuda" else "cpu", dbn=False)
    return _model


def analyze(path, force=False) -> dict:
    if not force and load_cached(path, "grid") and (b := load_array(path, "beats")) is not None:
        return {"beats": b.astype(float), "downbeats": load_array(path, "downbeats").astype(float)}
    y, sr = load_audio(path, sr=22050)
    beats, downbeats = _get_model()(y, sr)
    beats, downbeats = np.asarray(beats, dtype=float), np.asarray(downbeats, dtype=float)
    save_array(path, "beats", beats)
    save_array(path, "downbeats", downbeats)
    bar = float(np.median(np.diff(downbeats))) if len(downbeats) > 2 else None
    save_cached(path, "grid", {"n_beats": len(beats), "n_downbeats": len(downbeats), "bar_seconds": bar})
    return {"beats": beats, "downbeats": downbeats}

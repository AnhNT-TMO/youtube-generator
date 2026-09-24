from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

from .common import cache_dir_for, device, load_audio, load_cached, save_cached

STEMS = ("vocals", "drums", "bass", "other")
_sep = None


def _get_separator():
    global _sep
    if _sep is None:
        from demucs.api import Separator
        _sep = Separator(model="htdemucs", device=device(), progress=False)
    return _sep


def stem_path(path, name: str) -> Path:
    return cache_dir_for(path) / f"stem_{name}.flac"


def ensure(path, force=False) -> dict:
    if not force and (c := load_cached(path, "stems")) and all(stem_path(path, s).exists() for s in STEMS):
        return c
    import torch
    y, sr = load_audio(path, sr=44100, mono=False)
    sep = _get_separator()
    try:
        _, stems = sep.separate_tensor(torch.from_numpy(y), sr)
    except Exception:
        sep.update_parameter(device="cpu")
        _, stems = sep.separate_tensor(torch.from_numpy(y), sr)
    out = {}
    mix_rms = float(np.sqrt(np.mean(y ** 2)) + 1e-12)
    for name in STEMS:
        s = stems[name].mean(0).cpu().numpy()
        sf.write(stem_path(path, name), s, sr, subtype="PCM_16")
        out[f"{name}_rel_db"] = float(20 * np.log10(np.sqrt(np.mean(s ** 2)) / mix_rms + 1e-12))
    return save_cached(path, "stems", out)


def load_stem(path, name: str, sr: int = 16000) -> tuple[np.ndarray, int]:
    ensure(path)
    return load_audio(stem_path(path, name), sr=sr)

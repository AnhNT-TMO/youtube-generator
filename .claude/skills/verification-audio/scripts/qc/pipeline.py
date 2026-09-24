"""Chạy các module đo, trả về dict features (có cache).

`analyze_many` chạy THEO MODULE (một model cho mọi file rồi giải phóng) thay vì theo file,
để máy 16GB không phải giữ cùng lúc Demucs + Whisper + beat_this trong RAM. Dùng bởi youtube-music-analyzer (measure.py).
"""
from __future__ import annotations

import gc
import os
import time
from concurrent.futures import ProcessPoolExecutor

from . import basic, lyrics, rhythm, stems, tempo, vocal

# Module chỉ dùng CPU (librosa/ffmpeg) → chạy song song nhiều file bằng process pool
CPU_MODULES = {"basic", "tempo"}
ORDER = ("basic", "rhythm", "stems", "tempo", "vocal", "lyrics")


def _run(m, path, force):
    if m == "basic":
        return basic.analyze(path, force)
    if m == "rhythm":
        return rhythm.analyze(path, force)
    if m == "stems":
        return stems.ensure(path, force)
    if m == "tempo":
        return tempo.analyze(path, force)
    if m == "vocal":
        return vocal.analyze(path, force)
    if m == "lyrics":
        return lyrics.analyze(path, force)
    raise ValueError(m)


def free_models():
    rhythm._model = None
    stems._sep = None
    lyrics._torch_model = None
    try:
        from mlx_whisper.transcribe import ModelHolder
        ModelHolder.model = None
        import mlx.core as mx
        mx.clear_cache()
    except Exception:
        pass
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        elif torch.backends.mps.is_available():
            torch.mps.empty_cache()
    except Exception:
        pass


def analyze(path, modules=ORDER, force=False, verbose=False) -> dict:
    return analyze_many([path], modules, force, verbose)[str(path)]


def analyze_many(paths, modules=ORDER, force=False, verbose=False) -> dict[str, dict]:
    out = {str(p): {} for p in paths}
    for m in modules:
        t0 = time.time()
        todo = [p for p in paths if force or not _is_cached(m, p)]
        ran = bool(todo)
        workers = min(len(todo), max(1, (os.cpu_count() or 2) // 2), 16)
        if m in CPU_MODULES and workers > 1:
            with ProcessPoolExecutor(workers) as ex:
                list(ex.map(_run, [m] * len(todo), todo, [force] * len(todo)))
            force_m = False  # đã tính xong, lượt dưới chỉ đọc cache
        else:
            force_m = force
        for p in paths:
            if m == "stems" and p not in todo:
                from .common import load_cached
                out[str(p)][m] = load_cached(p, "stems")
                continue
            out[str(p)][m] = _run(m, p, force_m and p in todo)
        if ran:
            free_models() if m in ("rhythm", "stems", "lyrics") else None
            if verbose:
                print(f"  {m:<11} {time.time() - t0:6.1f}s", flush=True)
    return out


# Module cần file stem FLAC. Khi tất cả đã có cache (vd. features kéo từ server về, không kèm FLAC) thì bỏ qua Demucs.
STEM_DEPENDENTS = ("tempo", "vocal", "lyrics")


def _is_cached(m, p) -> bool:
    from .common import load_cached
    if m == "stems":
        if load_cached(p, "stems") is None:
            return False
        return stems.stem_path(p, "vocals").exists() or all(load_cached(p, d) is not None for d in STEM_DEPENDENTS)
    return load_cached(p, m) is not None

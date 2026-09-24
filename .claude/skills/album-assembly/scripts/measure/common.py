"""Tiện ích chung: đường dẫn, cache theo hash file, load audio, gọi ffmpeg.

Các module trong measure/ là bản gọn của verification-audio/scripts/qc (chỉ phần album-assembly cần)."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import numpy as np

# <repo>/.claude/skills/album-assembly/scripts/measure/common.py
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
SKILL_DIR = SCRIPTS_DIR.parent
REPO_DIR = SKILL_DIR.parents[2]
CACHE_DIR = SKILL_DIR / ".cache"

# Tăng khi thay đổi cách tính của một module để cache cũ tự bị bỏ qua.
# Cùng định dạng + version với verification-audio (bản gốc của các module này) nên cache hai bên đổi cho nhau được.
MODULE_VERSIONS = {
    "basic": 2,
    "stems": 1,
    "key": 1,
    "tempo": 1,
    "grid": 1,
}


def find_album(name: str) -> Path:
    """Tìm thư mục album theo tên (vd. '001-when-the-night-is-long') ở bất kỳ đâu trong repo (albums/ hoặc channel/*/albums/)."""
    hits = sorted(p for p in REPO_DIR.glob(f"**/albums/{name}") if ".cache" not in p.parts)
    if not hits:
        raise FileNotFoundError(f"không tìm thấy album {name} trong {REPO_DIR}")
    return hits[0]


def file_key(path: str | Path) -> str:
    """Hash nhanh: kích thước + 1MB đầu + 1MB cuối. Đổi tên file không làm mất cache."""
    p = Path(path)
    size = p.stat().st_size
    h = hashlib.sha1(str(size).encode())
    with open(p, "rb") as f:
        h.update(f.read(1 << 20))
        if size > (2 << 20):
            f.seek(-(1 << 20), os.SEEK_END)
            h.update(f.read(1 << 20))
    return h.hexdigest()[:16]


def cache_dir_for(path: str | Path) -> Path:
    d = CACHE_DIR / "features" / file_key(path)
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_cached(path, module: str):
    f = cache_dir_for(path) / f"{module}.json"
    if f.exists():
        data = json.loads(f.read_text())
        if data.get("_v") == MODULE_VERSIONS[module]:
            return data
    return None


def save_cached(path, module: str, data: dict) -> dict:
    data = {**data, "_v": MODULE_VERSIONS[module]}
    (cache_dir_for(path) / f"{module}.json").write_text(json.dumps(data, indent=1, default=_json_default))
    return data


def save_array(path, name: str, arr: np.ndarray) -> None:
    np.save(cache_dir_for(path) / f"{name}.npy", arr.astype(np.float32))


def load_array(path, name: str) -> np.ndarray | None:
    f = cache_dir_for(path) / f"{name}.npy"
    return np.load(f) if f.exists() else None


def _json_default(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))


def load_audio(path, sr: int | None = 22050, mono: bool = True) -> tuple[np.ndarray, int]:
    """Decode bằng ffmpeg để hỗ trợ mọi định dạng Suno tải về (wav/mp3/m4a). Trả về float32."""
    cmd = ["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le"]
    if mono:
        cmd += ["-ac", "1"]
    else:
        cmd += ["-ac", "2"]
    if sr:
        cmd += ["-ar", str(sr)]
    cmd += ["-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    y = np.frombuffer(raw, dtype=np.float32)
    if not sr:
        sr = probe(path)["sample_rate"]
    if not mono:
        y = y.reshape(-1, 2).T
    return y.copy(), sr


def probe(path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=sample_rate,channels,codec_name,bit_rate:format=duration,bit_rate",
         "-of", "json", str(path)],
        capture_output=True, check=True, text=True).stdout
    j = json.loads(out)
    s = j["streams"][0]
    return {
        "duration": float(j["format"]["duration"]),
        "sample_rate": int(s["sample_rate"]),
        "channels": int(s["channels"]),
        "codec": s.get("codec_name"),
        "bit_rate": int(s.get("bit_rate") or j["format"].get("bit_rate") or 0),
    }


def db(x, floor=1e-10):
    return 20 * np.log10(np.maximum(np.abs(x), floor))


def frame_rms_db(y: np.ndarray, sr: int, hop_s: float = 0.05, win_s: float = 0.1) -> tuple[np.ndarray, float]:
    hop = int(sr * hop_s)
    win = int(sr * win_s)
    if len(y) < win:
        return np.array([db(np.sqrt(np.mean(y ** 2)))]), hop_s
    n = 1 + (len(y) - win) // hop
    idx = np.arange(win)[None, :] + hop * np.arange(n)[:, None]
    rms = np.sqrt(np.mean(y[idx] ** 2, axis=1))
    return db(rms), hop_s


def device() -> str:
    import torch
    if torch.cuda.is_available():
        return "cuda"
    return "mps" if torch.backends.mps.is_available() else "cpu"

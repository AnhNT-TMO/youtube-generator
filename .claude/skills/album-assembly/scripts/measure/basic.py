"""Nhóm A — thông số file, loudness (EBU R128), khoảng lặng, clipping, kiểu kết bài."""
from __future__ import annotations

import re
import subprocess

import numpy as np

from .common import frame_rms_db, load_audio, load_cached, probe, save_cached

SILENCE_DB = -50.0


def _ebur128(path) -> dict:
    err = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
        capture_output=True, text=True).stderr
    summary = err[err.rfind("Summary:"):]

    def grab(label):
        m = re.search(rf"{label}:\s+(-?[\d.]+|-inf)", summary)
        return float(m.group(1)) if m and m.group(1) != "-inf" else None

    return {"lufs_i": grab("I"), "lra": grab("LRA"), "true_peak": grab("Peak")}


def analyze(path, force=False) -> dict:
    if not force and (c := load_cached(path, "basic")):
        return c
    info = probe(path)
    info.update(_ebur128(path))

    y, sr = load_audio(path, sr=22050)
    info["clip_ratio"] = float(np.mean(np.abs(y) >= 0.999))

    rms, hop = frame_rms_db(y, sr, hop_s=0.05, win_s=0.1)
    active = rms > SILENCE_DB
    t = np.arange(len(rms)) * hop
    if active.any():
        first, last = np.argmax(active), len(active) - 1 - np.argmax(active[::-1])
    else:
        first, last = 0, len(active) - 1
    info["lead_silence"] = float(t[first])
    info["tail_silence"] = float(info["duration"] - t[last] - 0.1)
    info["content_end"] = float(t[last] + 0.1)

    # Khoảng lặng giữa bài (bỏ qua đầu/cuối)
    gaps, run = [], 0
    for i in range(first, last + 1):
        if not active[i]:
            run += 1
        else:
            if run * hop >= 1.0:
                gaps.append({"start": float(t[i - run]), "dur": float(run * hop)})
            run = 0
    info["mid_silences"] = gaps

    # Kiểu kết bài: mức to của đoạn ngay trước khi hết tiếng, so với mức trung vị của bài.
    body = rms[first:last + 1]
    median_db = float(np.median(body))
    n1 = int(1.0 / hop)
    n15 = int(15.0 / hop)
    last1 = float(np.mean(rms[max(first, last - n1):last + 1]))
    tail = rms[max(first, last - n15):last + 1]
    slope = float(np.polyfit(np.arange(len(tail)) * hop, tail, 1)[0]) if len(tail) > 10 else 0.0
    # Tốc độ sụt ở 0.3s cuối: bị cắt ngang thì sụt cả chục dB trong vài frame.
    n03 = max(2, int(0.3 / hop))
    drop = float(np.mean(rms[max(first, last - 2 * n03):last - n03 + 1]) - rms[last]) if last - 2 * n03 > first else 0.0
    info["end_level_rel_db"] = last1 - median_db
    info["end_slope_db_s"] = slope
    info["end_drop_db"] = drop
    if info["end_level_rel_db"] > -6:
        end_type = "hard_end"
    elif slope < -0.8:
        end_type = "fade"
    else:
        end_type = "sustain"
    info["end_type"] = end_type
    info["median_rms_db"] = median_db
    return save_cached(path, "basic", info)

"""Nhóm B — tempo bằng autocorrelation của onset (stem drums + mix).

Vì sao không dùng số BPM của beat tracker: với nhạc 6/8 chậm, beat_this lúc bắt phách chấm đen (~64),
lúc bắt móc đơn (~176) hay nhóm 2 móc (~120–136) — so giữa các bài là vô nghĩa. Autocorrelation cho thấy
mọi mức nhịp cùng lúc; cache lưu nguyên đường autocorrelation → đổi target không phải tính lại.

Chọn mức nhịp (felt tempo):
- `felt(ac, target)` — bản nháp của mình (biết target). Cửa sổ [target/1.45, target×1.45] rộng 2.1×, nên có thể chứa
  2 mức nhịp (vd. 44.9 và 67.1 của wtnl-01, tỉ lệ 3:2). Trước đây lấy đỉnh MẠNH NHẤT trong cửa sổ, nên cùng một file
  đổi target 70 → 58 là đổi mức (67.1 → 44.9). Giờ: lấy đỉnh rõ gần target nhất; chỉ khi một đỉnh rõ khác mạnh hơn
  ≥ 1.5× thì lấy đỉnh đó (bắt được bản render lệch hẳn 2/3 hay 3/2). Có ≥ 2 đỉnh rõ → `ambiguous` + `alt_bpm`.
- `structural_felt(ac, bar_s)` — video tham khảo (không có target): pulse móc đơn E + số móc trong một ô nhịp
  của beat_this (3/6/12 → nhịp kép 6/8·12/8, tempo = E/3; 2/4/8 → nhịp đơn, tempo = E/2).
"""
from __future__ import annotations

import librosa
import numpy as np

from . import stems
from .common import load_array, load_audio, load_cached, save_array, save_cached

SR, HOP = 22050, 256
MAX_LAG_S = 4.0
WIN_S, WIN_HOP_S = 40.0, 20.0


def _ac(oenv: np.ndarray) -> np.ndarray:
    ac = librosa.autocorrelate(oenv - oenv.mean(), max_size=int(MAX_LAG_S * SR / HOP))
    return ac / (ac[0] + 1e-12)


def lag_to_bpm(lag: np.ndarray | float) -> np.ndarray | float:
    return 60.0 * SR / HOP / np.asarray(lag)


def analyze(path, force=False) -> dict:
    if not force and (c := load_cached(path, "tempo")) and load_array(path, "tempo_ac") is not None:
        return c
    mix, _ = load_audio(path, sr=SR)
    drums, _ = stems.load_stem(path, "drums", sr=SR)
    n = min(len(mix), len(drums))
    env = {}
    for name, y in (("mix", mix[:n]), ("drums", drums[:n])):
        env[name] = librosa.onset.onset_strength(y=y, sr=SR, hop_length=HOP)
    # Drums sạch hơn cho nhịp; mix bù khi drums gần như không có (intro/outro, bài không trống)
    drum_level = float(np.sqrt(np.mean(drums ** 2)) / (np.sqrt(np.mean(mix ** 2)) + 1e-9))
    wd = 0.7 if drum_level > 0.15 else 0.3
    ac = wd * _ac(env["drums"]) + (1 - wd) * _ac(env["mix"])
    save_array(path, "tempo_ac", ac)
    # Theo cửa sổ 40s (bỏ 45s cuối — outro hay chậm dần/tan nhịp) để đo tempo có trôi không
    fps = SR / HOP
    wins = []
    end = len(env["mix"]) - int(45 * fps)
    for s in range(0, max(1, end - int(WIN_S * fps)), int(WIN_HOP_S * fps)):
        seg = slice(s, s + int(WIN_S * fps))
        wins.append(wd * _ac(env["drums"][seg]) + (1 - wd) * _ac(env["mix"][seg]))
    if wins:
        save_array(path, "tempo_ac_win", np.stack(wins))
    return save_cached(path, "tempo", {"drum_level": drum_level, "n_windows": len(wins)})


def pulse(ac: np.ndarray, lo: float, hi: float) -> tuple[float | None, float]:
    """Đỉnh autocorrelation mạnh nhất có BPM trong [lo, hi]. Trả (bpm, độ rõ của đỉnh)."""
    lag_lo, lag_hi = int(np.floor(60 * SR / HOP / hi)), int(np.ceil(60 * SR / HOP / lo))
    lag_hi = min(lag_hi, len(ac) - 2)
    best, best_v = None, -1.0
    for L in range(max(2, lag_lo), lag_hi + 1):
        if ac[L] > ac[L - 1] and ac[L] >= ac[L + 1] and ac[L] > best_v:
            best, best_v = L, ac[L]
    if best is None:
        return None, 0.0
    return _interp(ac, best), float(best_v)


def _interp(ac: np.ndarray, L: int) -> float:
    a, b, c = ac[L - 1], ac[L], ac[L + 1]
    d = 0.5 * (a - c) / (a - 2 * b + c + 1e-12)  # nội suy parabol cho lag lẻ
    return float(lag_to_bpm(L + d))


def peaks(ac: np.ndarray, lo: float, hi: float) -> list[tuple[float, float]]:
    """Mọi đỉnh autocorrelation (bpm, độ rõ) có BPM trong [lo, hi], đỉnh mạnh trước."""
    lag_lo, lag_hi = int(np.floor(60 * SR / HOP / hi)), int(np.ceil(60 * SR / HOP / lo))
    lag_hi = min(lag_hi, len(ac) - 2)
    out = [(_interp(ac, L), float(ac[L])) for L in range(max(2, lag_lo), lag_hi + 1)
           if ac[L] > ac[L - 1] and ac[L] >= ac[L + 1] and ac[L] > 0]
    return sorted(((b, v) for b, v in out if lo <= b <= hi), key=lambda x: -x[1])


SPAN, SALIENT, OVERRIDE = 1.45, 0.6, 1.5


def felt(ac: np.ndarray, target: float, span: float = SPAN) -> dict:
    """Tempo cảm nhận của một bản nháp so với target (xem docstring đầu file). bpm None = không có đỉnh nào."""
    pk = peaks(ac, target / span, target * span)
    if not pk:
        return {"bpm": None, "salience": 0.0, "alt_bpm": None, "alt_salience": None, "ambiguous": False}
    top = pk[0][1]
    rich = [p for p in pk if p[1] >= SALIENT * top]
    near = min(rich, key=lambda p: abs(np.log(p[0] / target)))
    pick = pk[0] if pk[0][1] >= OVERRIDE * near[1] else near
    alt = next((p for p in rich if p is not pick), None)
    return {"bpm": pick[0], "salience": pick[1], "alt_bpm": alt[0] if alt else None,
            "alt_salience": alt[1] if alt else None, "ambiguous": alt is not None}


def structural_felt(ac: np.ndarray, bar_s: float | None) -> dict:
    """Tempo cảm nhận không cần target: pulse móc đơn E (đỉnh mạnh nhất 110–240 BPM) × số móc trong một ô nhịp
    (bar_s của beat_this). 3/6/12 móc → nhịp kép, tempo = E/3; 2/4/8 → nhịp đơn, tempo = E/2; bắt vào đỉnh
    autocorrelation mạnh nhất trong ±5 %. Không xác định được (E yếu, số móc lẻ) → bpm None: người gọi tự xử lý + gắn cờ."""
    e, ev = pulse(ac, 110, 240)
    res = {"bpm": None, "eighth_bpm": round(e, 1) if e else None, "eighths_per_bar": None, "meter": None}
    if not e or ev < 0.08 or not bar_s:
        return res
    epb = bar_s * e / 60
    res["eighths_per_bar"] = round(epb, 2)
    kind = next((m for m, ns in (("compound", (3, 6, 12)), ("simple", (2, 4, 8))) for n in ns if abs(epb / n - 1) <= 0.06), None)
    if not kind:
        return res
    s = e / (3 if kind == "compound" else 2)
    b, _ = pulse(ac, s / 1.05, s * 1.05)
    res.update({"bpm": b or s, "meter": kind})
    return res

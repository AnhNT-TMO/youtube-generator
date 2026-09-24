from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from .features import Track

RECIPES = {
    "crossfade": dict(a_tail=8.0, a_fade=8.0, b_keep=10.0, overlap=6.0, b_fade=3.0,
                      label="Crossfade nhạc cụ", sound="outro bài trước tan vào intro bài sau"),
    "quick": dict(a_tail=3.0, a_fade=3.0, b_keep=3.5, overlap=1.5, b_fade=0.3,
                  label="Vào nhanh", sound="bài trước fade gọn ngay sau câu cuối, bài sau hát gần như ngay"),
    "natural": dict(a_tail=None, a_fade=1.0, b_keep=6.0, overlap=1.0, b_fade=0.5,
                    label="Kết trọn rồi vào", sound="bài trước chơi hết ending của nó, bài sau vào trên tiếng ngân cuối"),
    "cold_open": dict(a_tail=5.0, a_fade=5.0, b_keep=0.8, overlap=-0.8, b_fade=0.03,
                      label="Cold open", sound="bài trước tan hết, lặng ngắn, bài sau mở thẳng bằng giọng hát"),
    "breath": dict(a_tail=4.0, a_fade=10.0, b_keep=14.0, overlap=-1.0, b_fade=1.5,
                   label="Khoảng thở", sound="bài trước fade dài về lặng, nghỉ một nhịp, intro dài của bài sau"),
    "build": dict(a_tail=6.0, a_fade=6.0, b_keep=18.0, overlap=4.0, b_fade=2.0,
                  label="Intro dựng dần", sound="bài trước lùi nhanh, intro dài của bài sau dựng không khí trước khi hát"),
}
TYPES = tuple(RECIPES)

BUCKET = {"cold_open": "ngay", "quick": "ngắn", "natural": "ngắn", "crossfade": "vừa", "breath": "dài", "build": "dài"}

MIN_A_TAIL = 0.6
VOCAL_CLEAR = 1.5
NATURAL_MAX_OUTRO = 22.0


@dataclass
class Cut:
    a_out: float
    a_fade: float
    b_in: float
    b_fade: float
    overlap: float

    def a_fade_start(self) -> float:
        return self.a_out - self.a_fade


def _lines(t: Track) -> np.ndarray:
    d = t.downbeats
    if len(d) > 2 and np.median(np.diff(d)) > 3.0:
        d = np.sort(np.concatenate([d, (d[:-1] + d[1:]) / 2]))
    return d


def _bar(t: Track) -> float:
    d = np.diff(_lines(t))
    return float(np.median(d)) if len(d) else 2.0


def _last_before(times: np.ndarray, t: float, lo: float) -> float | None:
    c = times[(times <= t + 1e-6) & (times >= lo)]
    return float(c[-1]) if len(c) else None


def _nearest(times: np.ndarray, t: float, lo: float, hi: float) -> float | None:
    c = times[(times >= lo) & (times <= hi)]
    return float(c[np.argmin(np.abs(c - t))]) if len(c) else None


def b_start(B: Track, keep: float) -> float:
    target = B.vocal_start - keep
    floor = max(B.lead_silence, 0.0)
    if target <= floor + 0.3:
        return round(floor, 2)
    if keep < 2.5:
        t = _last_before(B.beats, target, max(floor, target - 1.2))
    else:
        t = _nearest(_lines(B), target, max(floor, target - 1.1 * _bar(B)), min(target + 0.5, B.vocal_start - 0.5))
    return round(t if t is not None else target, 2)


def a_end(A: Track, tail: float | None, fade: float) -> tuple[float, float]:
    if tail is None:
        return round(A.content_end, 2), fade
    lo = A.vocal_end + MIN_A_TAIL
    target = max(lo, A.vocal_end + tail)
    s = _nearest(_lines(A), target, lo, target + _bar(A))
    s = s if s is not None else target
    out = min(s + fade, A.content_end)
    return round(out, 2), round(max(0.5, out - max(s, lo)), 2)


def cut_for(kind: str, A: Track, B: Track, **over) -> Cut:
    r = {**RECIPES[kind], **{k: v for k, v in over.items() if v is not None}}
    a_out, a_fade = a_end(A, r["a_tail"], r["a_fade"])
    b_in = b_start(B, r["b_keep"])
    keep = B.vocal_start - b_in
    overlap = min(r["overlap"], a_fade, keep - VOCAL_CLEAR)
    if overlap > 0.5:
        overlap = _phase_align(A, a_out, a_fade, overlap, keep - VOCAL_CLEAR)
    b_fade = min(r["b_fade"], max(0.03, keep - 0.2))
    return Cut(a_out=a_out, a_fade=a_fade, b_in=b_in, b_fade=round(b_fade, 2), overlap=round(overlap, 2))


def _phase_align(A: Track, a_out: float, a_fade: float, overlap: float, max_overlap: float) -> float:
    half = _bar(A) / 2
    lo, hi = max(a_out - a_fade, a_out - max_overlap), a_out - 0.3
    d = _nearest(_lines(A), a_out - overlap, max(lo, a_out - overlap - half), min(hi, a_out - overlap + half))
    return round(a_out - d, 2) if d is not None else overlap


def tempo_gap(A: Track, B: Track) -> float:
    return abs(B.bpm / A.bpm - 1) if A.bpm and B.bpm else 0.0


def describe(A: Track, B: Track, c: Cut) -> dict:
    a_tail = c.a_fade_start() - A.vocal_end
    b_keep = B.vocal_start - c.b_in
    gap = (c.a_out - A.vocal_end) - c.overlap + b_keep
    return {"a_tail": round(a_tail, 1), "b_keep": round(b_keep, 1), "silence": round(max(0.0, -c.overlap), 1),
            "vocal_gap": round(gap, 1), "b_entry_level_db": round(B.level(c.b_in, c.b_in + 3), 1),
            "b_entry_drums": B.drums_level(c.b_in, c.b_in + 3) > -8}


def suitability(kind: str, A: Track, B: Track, idx: int, n: int) -> tuple[float, list[str]]:
    s, why = 0.0, []
    dE = (B.energy or 0) - (A.energy or 0) if A.energy is not None and B.energy is not None else 0
    role = B.arc_role or ""
    outro, intro = A.outro_len, B.intro_len
    early = idx < 2
    c = cut_for(kind, A, B)
    d = describe(A, B, c)
    tg = tempo_gap(A, B)
    if tg > 0.05:
        pen = {"crossfade": -1.5, "build": -0.5, "quick": -0.3, "natural": 0.5, "cold_open": 0.5, "breath": 0.5}[kind]
        s += pen
        if pen > 0:
            why.append(f"tempo {A.bpm:.0f}→{B.bpm:.0f} BPM ({tg:+.0%}): ngắt gọn thay vì chồng hai nhịp lên nhau".replace("+", ""))

    if kind == "natural":
        if outro > NATURAL_MAX_OUTRO:
            return -math.inf, [f"outro bài {A.no} dài {outro:.0f}s, để nguyên thì quá lâu không lời"]
        s += 0.5
        if outro <= 10:
            s += 1.5; why.append(f"bài {A.no} kết ngay sau câu cuối (outro {outro:.0f}s): để nó kết trọn")
        if A.end_type in ("sustain", "hard_end"):
            s += 1.0; why.append(f"bài {A.no} có ending thật ({A.end_type}), không cần fade")
        if dE <= -2:
            s += 0.5; why.append(f"energy {A.energy:g}→{B.energy:g}: kết trọn giúp hạ nhiệt")
    elif kind == "crossfade":
        s += 1.0
        if dE < 0:
            s += 0.8; why.append(f"energy {A.energy:g}→{B.energy:g} hạ nhẹ: nhạc cụ tan vào nhau cho mềm")
        if dE == 0:
            s += 0.5; why.append("cùng mức energy: nối liền, không để hụt")
        if outro < 8:
            s -= 1.5
        if intro < 12:
            s -= 1.0
    elif kind == "quick":
        if dE >= 1:
            s += 1.5; why.append(f"energy {A.energy:g}→{B.energy:g} đi lên: vào nhanh giữ đà")
        if dE <= -2:
            s -= 2.0
        if early:
            s += 1.0; why.append("đầu album: không để người nghe chờ intro")
        if role in ("closer", "peak"):
            s -= 2.0
    elif kind == "cold_open":
        if dE >= 1:
            s += 1.5; why.append(f"energy {A.energy:g}→{B.energy:g} đi lên: mở thẳng bằng giọng tạo cú hích")
        elif dE == 0:
            s += 0.3
        else:
            s -= 2.0
        if role == "peak":
            s += 0.5
        if role == "closer":
            s -= 3.0
        if early:
            s += 0.5
        if d["b_entry_level_db"] < -10:
            s -= 1.0
    elif kind == "breath":
        if dE <= -2:
            s += 2.0; why.append(f"energy {A.energy:g}→{B.energy:g} hạ mạnh: cần một khoảng thở")
        if role == "closer":
            s += 2.0; why.append(f"bài {B.no} là bài kết: nghỉ một nhịp rồi vào lời cầu nguyện cuối")
        if dE >= 1:
            s -= 2.0
        if early:
            s -= 2.0
        if intro < 14:
            s -= 2.0
    elif kind == "build":
        if role == "peak":
            s += 2.5; why.append(f"bài {B.no} là cao trào: intro dài dựng không khí trước khi hát")
        if dE >= 1:
            s += 0.5
        if role == "closer":
            s += 0.8; why.append(f"bài {B.no} là bài kết: cho intro thở")
        if dE <= -2:
            s -= 0.5
        if early:
            s -= 1.5
        if intro < 16:
            s -= 2.0

    if early and d["b_keep"] >= 12:
        s -= 1.0
    if d["vocal_gap"] > 30:
        s -= 1.0; why.append(f"(khoảng không lời {d['vocal_gap']:.0f}s hơi dài)")
    if d["vocal_gap"] < 3:
        s -= 1.0
    return s, why


def caps(n_joins: int) -> dict[str, int]:
    common = max(1, math.ceil(n_joins * 0.34))
    rare = 2 if n_joins >= 6 else 1
    return {"crossfade": common, "quick": common, "natural": common, "cold_open": rare, "breath": rare, "build": rare}


def choose(tracks: list[Track], fixed: dict[int, str] | None = None) -> list[tuple[str, float, list[str]]]:
    fixed = fixed or {}
    joins = list(zip(tracks[:-1], tracks[1:]))
    n = len(joins)
    table = [{k: suitability(k, A, B, i, n) for k in TYPES} for i, (A, B) in enumerate(joins)]
    cap = caps(n)
    idx = {k: i for i, k in enumerate(TYPES)}

    @lru_cache(maxsize=None)
    def best(i: int, prev: str | None, counts: tuple[int, ...]) -> tuple[float, tuple[str, ...]]:
        if i == n:
            buckets = {BUCKET[k] for k, c in zip(TYPES, counts) if c}
            return (1.5 * len(buckets) if n >= 4 else 0.0), ()
        out = (-math.inf, ())
        for k in ([fixed[i]] if i in fixed else TYPES):
            s = table[i][k][0]
            if s == -math.inf and i not in fixed:
                continue
            if k == prev and i not in fixed:
                continue
            c = list(counts)
            c[idx[k]] += 1
            if c[idx[k]] > cap[k] and i not in fixed:
                continue
            sub, seq = best(i + 1, k, tuple(c))
            if s + sub > out[0]:
                out = (s + sub, (k,) + seq)
        return out

    total, seq = best(0, None, tuple([0] * len(TYPES)))
    if not seq:
        raise SystemExit("không tìm được cách nối thỏa luật đa dạng; nới `caps` hoặc khóa bớt join")
    return [(k, table[i][k][0], table[i][k][1]) for i, k in enumerate(seq)]


def opening(T1: Track, vocal_at: float) -> tuple[float, float]:
    t_in = b_start(T1, vocal_at)
    for _ in range(4):
        if T1.level(t_in, t_in + 3) >= -8 or T1.vocal_start - t_in < 5:
            break
        nxt = _lines(T1)[_lines(T1) > t_in + 0.2]
        if not len(nxt) or T1.vocal_start - nxt[0] < 4:
            break
        t_in = float(nxt[0])
    fade = 0.0 if t_in <= T1.lead_silence + 0.05 else 0.6
    return round(t_in, 2), fade


def ending(TN: Track) -> tuple[float, float]:
    out = min(TN.duration, TN.content_end + 0.3)
    fade = 3.0 if TN.end_type == "hard_end" else 1.5
    return round(out, 2), fade

"""Ghép album theo assembly.yaml → WAV 24-bit (+ MP3), preview từng điểm nối, rồi đo lại bản ghép."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import numpy as np

from .features import loudness_curve

CH = 2


def timeline(plan: dict) -> list[float]:
    """Thời điểm bắt đầu của mỗi bài trong bản ghép (giây)."""
    starts, t = [], 0.0
    tracks, joins = plan["tracks"], plan["joins"]
    for i, tr in enumerate(tracks):
        starts.append(t)
        if i < len(joins):
            t += (tr["out"] - tr["in"]) - joins[i]["overlap"]
    return starts


def _read(path: Path, t0: float, t1: float, sr: int) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.4f}", "-to", f"{t1:.4f}", "-i", str(path),
                          "-f", "f32le", "-ac", str(CH), "-ar", str(sr), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, CH).copy()


def _fade(n: int, kind: str, direction: str) -> np.ndarray:
    x = (np.arange(n) + 0.5) / max(n, 1)
    if kind == "equal_power":
        g = np.sin(x * np.pi / 2)
    else:  # fade về/ra khỏi im lặng: cong như tai nghe (nhanh ở đoạn nhỏ)
        g = x ** 2
    return (g if direction == "in" else g[::-1]).astype(np.float32)[:, None]


def segments(plan: dict, album: Path, sr: int):
    """Sinh (bắt đầu trên timeline theo sample, mảng audio đã gain + fade) cho từng bài."""
    tracks, joins = plan["tracks"], plan["joins"]
    for i, (tr, start) in enumerate(zip(tracks, timeline(plan))):
        y = _read(album / tr["audio"], tr["in"], tr["out"], sr) * np.float32(10 ** (tr["gain_db"] / 20))
        into = joins[i - 1]["overlap"] if i > 0 else -1
        outof = joins[i]["overlap"] if i < len(joins) else -1
        nin, nout = int(tr["fade_in"] * sr), int(tr["fade_out"] * sr)
        if nin:
            y[:nin] *= _fade(nin, "equal_power" if into > 0 else "silence", "in")
        if nout:
            y[-nout:] *= _fade(nout, "equal_power" if outof > 0 else "silence", "out")
        yield int(round(start * sr)), y


def render(plan: dict, album: Path, out_wav: Path, mp3=True) -> None:
    sr = int(plan.get("sample_rate", 48000))
    limit = 10 ** (plan["loudness"].get("limit_db", -1.0) / 20)
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(sr), "-ac", str(CH), "-i", "-",
                           "-af", f"alimiter=limit={limit:.4f}:attack=5:release=80:level=0:latency=1",
                           "-c:a", "pcm_s24le", str(out_wav)], stdin=subprocess.PIPE)
    buf, buf_start, written = None, 0, 0

    def write(a: np.ndarray):
        nonlocal written
        ff.stdin.write(np.ascontiguousarray(a, dtype=np.float32).tobytes())
        written += len(a)

    for start, y in segments(plan, album, sr):
        if buf is None:
            buf, buf_start = y, start
            continue
        rel = start - buf_start
        if rel >= len(buf):  # khoảng lặng giữa hai bài
            write(buf)
            write(np.zeros((rel - len(buf), CH), np.float32))
            buf, buf_start = y, start
            continue
        write(buf[:rel])
        ov = buf[rel:]
        y = y.copy()
        y[:len(ov)] += ov
        buf, buf_start = y, start
    tail = int(plan.get("tail_silence", 2.0) * sr)
    write(buf)
    write(np.zeros((tail, CH), np.float32))
    ff.stdin.close()
    if ff.wait():
        raise SystemExit("ffmpeg lỗi khi ghi bản ghép")
    if mp3:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(out_wav), "-c:a", "libmp3lame", "-b:a", "320k",
                        str(out_wav.with_suffix(".mp3"))], check=True)


def previews(plan: dict, master: Path, out_dir: Path) -> list[str]:
    """MP3 ngắn quanh mỗi điểm nối (từ ~6s trước câu hát cuối bài trước đến ~12s sau câu hát đầu bài sau)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in out_dir.glob("*.mp3"):
        f.unlink()
    files = []
    starts = timeline(plan)
    tracks = plan["tracks"]

    def cut(name, t0, t1):
        f = out_dir / name
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0, t0):.2f}", "-to", f"{t1:.2f}", "-i", str(master),
                        "-c:a", "libmp3lame", "-b:a", "192k", str(f)], check=True)
        files.append(str(f.relative_to(master.parent.parent.parent)))

    cut("00-opening.mp3", 0, 30)
    for j, (A, B) in enumerate(zip(tracks[:-1], tracks[1:])):
        a_voc = starts[j] + A["measured"]["vocal_end"] - A["in"]
        b_voc = starts[j + 1] + B["measured"]["vocal_start"] - B["in"]
        cut(f"{A['no']:02d}-{B['no']:02d}.mp3", a_voc - 6, b_voc + 12)
    return files


# ---------------------------------------------------------------- đo lại bản ghép

def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    d = np.diff(np.concatenate([[0], mask.astype(int), [0]]))
    return list(zip(np.where(d == 1)[0], np.where(d == -1)[0]))


def _summary(path: Path) -> dict:
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    s = err[err.rfind("Summary:"):]
    g = lambda lab: (float(m.group(1)) if (m := re.search(rf"{lab}:\s+(-?[\d.]+)", s)) else None)
    return {"lufs_i": g("I"), "lra": g("LRA"), "true_peak": g("Peak")}


def verify(plan: dict, master: Path) -> dict:
    M, S = loudness_curve(master)
    hop = 0.1
    at = lambda t: int(max(0, t) / hop)
    starts = timeline(plan)
    tracks, joins = plan["tracks"], plan["joins"]
    res = {"duration": round(len(M) * hop, 1), **_summary(master)}

    # Mở video: giọng hát vào ở giây nào, 10–15 giây đầu có nhỏ quá không
    t1 = tracks[0]
    body = float(np.median(S[at(60):at(starts[1]) if len(starts) > 1 else at(240)]))
    first_full = next((i * hop for i in range(at(15)) if S[i] >= body - 6), None)
    res["opening"] = {
        "vocal_at": round(t1["measured"]["vocal_start"] - t1["in"], 1),
        "m_0_5": round(float(np.mean(M[at(0.5):at(5)])) - body, 1),
        "m_5_15": round(float(np.mean(M[at(5):at(15)])) - body, 1),
        "reaches_body_at": round(first_full, 1) if first_full is not None else None,
    }

    res["joins"] = []
    for j, (A, B) in enumerate(zip(tracks[:-1], tracks[1:])):
        a_voc = starts[j] + A["measured"]["vocal_end"] - A["in"]
        b_voc = starts[j + 1] + B["measured"]["vocal_start"] - B["in"]
        # Cảm nhận ở chỗ nối: 20s cuối có hát của bài trước vs 20s đầu có hát của bài sau
        pre = float(np.median(S[at(a_voc - 20):at(a_voc)]))
        post = float(np.median(S[at(b_voc + 3):at(b_voc + 23)]))
        win = M[at(a_voc):at(b_voc)]
        m_s = np.convolve(win, np.ones(10) / 10, mode="same") if len(win) > 10 else win  # làm mượt 1 s
        dip = float(min(pre, post) - m_s.min()) if len(m_s) else 0.0
        sil = max(((b - a) * hop for a, b in _runs(win < -50)), default=0.0)
        res["joins"].append({"no": joins[j]["no"], "at": round(starts[j + 1], 1), "jump_lu": round(post - pre, 1),
                             "dip_lu": round(dip, 1), "silence": round(sil, 1),
                             "vocal_gap": round(b_voc - a_voc, 1)})
    res["chapters"] = [{"no": tr["no"], "title": tr["title"], "start": round(s, 2)} for tr, s in zip(tracks, starts)]
    return res

"""Dựng / cập nhật assembly.yaml: điểm cắt từng bài + kiểu nối từng điểm chuyển."""
from __future__ import annotations

from pathlib import Path

from . import planner
from .features import Track, segment_lufs

GAIN_LIMIT = 4.0  # dB; lệch hơn thì bài đó có vấn đề, báo chứ không cố bù


def _measured(t: Track) -> dict:
    return {"duration": round(t.duration, 2), "vocal_start": round(t.vocal_start, 2), "vocal_end": round(t.vocal_end, 2),
            "content_end": round(t.content_end, 2), "intro_len": round(t.intro_len, 1), "outro_len": round(t.outro_len, 1),
            "end_type": t.end_type, "lufs_i": t.lufs_i, "camelot": t.camelot, "ending_camelot": t.ending_camelot,
            "bpm": round(t.bpm, 1) if t.bpm else None, "energy": t.energy, "arc_role": t.arc_role,
            "bar_seconds": round(planner._bar(t), 2)}


def _join_entry(no: int, kind: str, A: Track, B: Track, c: planner.Cut, score, why: list[str], locked=False) -> dict:
    r = planner.RECIPES[kind]
    return {"no": no, "from": A.no, "to": B.no, "type": kind, "overlap": c.overlap, "locked": locked,
            "score": None if score is None else round(score, 2),
            "why": "; ".join(why) if why else r["sound"], "feel": planner.describe(A, B, c)}


def _apply(tr_a: dict, tr_b: dict, c: planner.Cut) -> None:
    tr_a["out"], tr_a["fade_out"] = c.a_out, c.a_fade
    tr_b["in"], tr_b["fade_in"] = c.b_in, c.b_fade


def build(album: Path, tracks: list[Track], prev: dict | None, vocal_at: float, target_lufs: float) -> dict:
    prev = prev or {}
    prev_joins = {j["no"]: j for j in prev.get("joins", [])}
    prev_tracks = {t["no"]: t for t in prev.get("tracks", [])}
    locked = {no - 1: j for no, j in prev_joins.items() if j.get("locked")}
    picks = planner.choose(tracks, {i: j["type"] for i, j in locked.items()})

    trs = [{"no": t.no, "id": t.id, "title": t.title, "audio": str(t.audio.relative_to(album)),
            "in": 0.0, "out": round(t.content_end, 2), "fade_in": 0.0, "fade_out": 0.0, "gain_db": 0.0,
            "measured": _measured(t)} for t in tracks]
    op = prev.get("opening") or {}
    if op.get("locked"):
        trs[0]["in"], trs[0]["fade_in"] = prev_tracks[1]["in"], prev_tracks[1]["fade_in"]
    else:
        op = {"vocal_at": vocal_at, "locked": False}
        trs[0]["in"], trs[0]["fade_in"] = planner.opening(tracks[0], vocal_at)
    trs[-1]["out"], trs[-1]["fade_out"] = planner.ending(tracks[-1])

    joins = []
    for i, ((A, B), (kind, score, why)) in enumerate(zip(zip(tracks[:-1], tracks[1:]), picks)):
        if i in locked:
            pj, pa, pb = locked[i], prev_tracks[A.no], prev_tracks[B.no]
            c = planner.Cut(a_out=pa["out"], a_fade=pa["fade_out"], b_in=pb["in"], b_fade=pb["fade_in"],
                            overlap=pj["overlap"])
            j = _join_entry(i + 1, kind, A, B, c, pj.get("score"), [], locked=True)
            j["why"] = pj.get("why", j["why"])
        else:
            c = planner.cut_for(kind, A, B)
            j = _join_entry(i + 1, kind, A, B, c, score, why)
        _apply(trs[i], trs[i + 1], c)
        joins.append(j)

    for tr, t in zip(trs, tracks):
        p = prev_tracks.get(t.no)
        if p and p.get("gain_locked"):
            tr["gain_db"], tr["gain_locked"] = p["gain_db"], True
            continue
        lufs = segment_lufs(t.audio, tr["in"], tr["out"])
        tr["measured"]["lufs_kept"] = lufs
        tr["gain_db"] = round(max(-GAIN_LIMIT, min(GAIN_LIMIT, target_lufs - lufs)), 2) if lufs is not None else 0.0

    name = album.name
    return {"album": name, "output": f"audio/master/{name}.wav", "sample_rate": 48000,
            "loudness": {"target_lufs": target_lufs, "limit_db": -1.5}, "tail_silence": 2.0,
            "opening": op, "tracks": trs, "joins": joins}


def build_single(single: Path, t: Track, audio_rel: Path, prev: dict | None, vocal_at: float, target_lufs: float) -> dict:
    """Bài đăng riêng: một bài, không điểm nối. Cắt intro để giọng vào ở giây `vocal_at` (như bài 01 của album),
    giữ ending tự nhiên, cân loudness về target."""
    prev = prev or {}
    tr = {"no": 1, "id": t.id, "title": t.title, "audio": str(audio_rel), "in": 0.0, "out": 0.0,
          "fade_in": 0.0, "fade_out": 0.0, "gain_db": 0.0, "measured": _measured(t)}
    op = prev.get("opening") or {}
    p = (prev.get("tracks") or [{}])[0]
    if op.get("locked") and p:
        tr["in"], tr["fade_in"] = p["in"], p["fade_in"]
    else:
        op = {"vocal_at": vocal_at, "locked": False}
        tr["in"], tr["fade_in"] = planner.opening(t, vocal_at)
    tr["out"], tr["fade_out"] = planner.ending(t)
    if p.get("gain_locked"):
        tr["gain_db"], tr["gain_locked"] = p["gain_db"], True
    else:
        lufs = segment_lufs(t.audio, tr["in"], tr["out"])
        tr["measured"]["lufs_kept"] = lufs
        tr["gain_db"] = round(max(-GAIN_LIMIT, min(GAIN_LIMIT, target_lufs - lufs)), 2) if lufs is not None else 0.0
    name = single.name
    return {"album": name, "kind": "single", "output": f"audio/master/{name}.wav", "sample_rate": 48000,
            "loudness": {"target_lufs": target_lufs, "limit_db": -1.5}, "tail_silence": 2.0,
            "opening": op, "tracks": [tr], "joins": []}


def set_join(plan: dict, tracks: list[Track], no: int, kind: str, **over) -> None:
    """Đổi kiểu / tham số một điểm nối, tính lại điểm cắt và khóa nó."""
    A, B = tracks[no - 1], tracks[no]
    c = planner.cut_for(kind, A, B, **over)
    tr_a, tr_b = plan["tracks"][no - 1], plan["tracks"][no]
    _apply(tr_a, tr_b, c)
    score, why = planner.suitability(kind, A, B, no - 1, len(tracks) - 1)
    extra = [f"{k}={v}" for k, v in over.items() if v is not None]
    plan["joins"][no - 1] = _join_entry(no, kind, A, B, c, score if score != float("-inf") else None,
                                        (why or [planner.RECIPES[kind]["sound"]]) + (["chỉnh tay: " + ", ".join(extra)] if extra else []),
                                        locked=True)
    for tr, t in ((tr_a, A), (tr_b, B)):
        if not tr.get("gain_locked"):
            lufs = segment_lufs(t.audio, tr["in"], tr["out"])
            tr["measured"]["lufs_kept"] = lufs
            tr["gain_db"] = round(max(-GAIN_LIMIT, min(GAIN_LIMIT, plan["loudness"]["target_lufs"] - lufs)), 2)
    plan.pop("result", None)

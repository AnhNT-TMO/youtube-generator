from __future__ import annotations

from collections import Counter
from pathlib import Path

from . import planner

NOTES_HEADING = "## Ghi chú"
MARK = "<!-- sinh bởi skill album-assembly -->"


def fmt_time(t: float) -> str:
    t = int(t)
    h, m, s = t // 3600, t // 60 % 60, t % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def camelot_dist(a: str | None, b: str | None) -> int | None:
    if not a or not b:
        return None
    na, la, nb, lb = int(a[:-1]), a[-1], int(b[:-1]), b[-1]
    d = min((na - nb) % 12, (nb - na) % 12)
    return d + (0 if la == lb else 1)


def checks(plan: dict) -> list[tuple[str, int | None, str]]:
    out = []
    tr, joins = plan["tracks"], plan["joins"]
    for a, b in zip(joins, joins[1:]):
        if a["type"] == b["type"]:
            out.append(("warn", b["no"], f"hai điểm nối liền nhau cùng kiểu `{a['type']}`: người nghe đoán được công thức"))
    for j in joins:
        A, B, f = tr[j["from"] - 1], tr[j["to"] - 1], j["feel"]
        if A["out"] - A["fade_out"] < A["measured"]["vocal_end"] - 0.05:
            out.append(("fail", j["no"], f"fade của bài {A['no']} đè lên câu hát cuối"))
        if B["in"] > B["measured"]["vocal_start"]:
            out.append(("fail", j["no"], f"bài {B['no']} bị cắt mất câu hát đầu"))
        if f["vocal_gap"] > 30:
            out.append(("warn", j["no"], f"{f['vocal_gap']:.0f}s không lời giữa hai bài"))
        if f["b_entry_level_db"] < -10 and j["type"] not in ("breath",):
            out.append(("warn", j["no"], f"bài {B['no']} vào nhỏ ({f['b_entry_level_db']:+.0f} dB so với thân bài): điểm vào thiếu ấn tượng"))
        ma, mb = A["measured"], B["measured"]
        if ma.get("bpm") and mb.get("bpm") and abs(mb["bpm"] / ma["bpm"] - 1) > 0.08:
            ov = " và đang chồng hai bài lên nhau" if j["overlap"] > 2 else ""
            out.append(("warn", j["no"], f"tempo {ma['bpm']:.0f}→{mb['bpm']:.0f} BPM lệch > 8%{ov}: nghe kỹ chỗ đổi nhịp"))
        d = camelot_dist(ma.get("ending_camelot"), mb.get("camelot"))
        if d is not None and d > 1:
            out.append(("warn", j["no"], f"key {ma.get('ending_camelot')}→{mb.get('camelot')} lệch {d} bước Camelot"))
    va = tr[0]["measured"]["vocal_start"] - tr[0]["in"]
    if va > 15:
        out.append(("fail", None, f"giọng hát vào ở giây {va:.0f} của video (> 15s, CLAUDE.md)"))
    elif va > 12:
        out.append(("warn", None, f"giọng hát vào ở giây {va:.0f} của video (lý tưởng ≤ 10–12s)"))

    res = plan.get("result")
    if res:
        op = res["opening"]
        if op["m_0_5"] < -10:
            out.append(("warn", None, f"0.5–5s đầu video nhỏ hơn thân bài {-op['m_0_5']:.0f} LU"))
        if op["reaches_body_at"] is None or op["reaches_body_at"] > 8:
            out.append(("warn", None, "đến giây 8 vẫn chưa đạt mức thân bài"))
        if res.get("true_peak") is not None and res["true_peak"] > -0.3:
            out.append(("warn", None, f"true peak {res['true_peak']:.1f} dBTP"))
        types = {j["no"]: j["type"] for j in joins}
        for r in res["joins"]:
            k = types[r["no"]]
            if r["jump_lu"] > 3 or r["jump_lu"] < -7:
                out.append(("fail", r["no"], f"chênh loudness ở chỗ nối {r['jump_lu']:+.1f} LU"))
            elif r["jump_lu"] > 1.5 or r["jump_lu"] < -5:
                out.append(("warn", r["no"], f"chênh loudness ở chỗ nối {r['jump_lu']:+.1f} LU"))
            gap = max(0.0, -next(j["overlap"] for j in joins if j["no"] == r["no"]))
            if r["silence"] > gap + 1.5 or (gap == 0 and r["silence"] > 0.3):
                out.append(("warn", r["no"], f"lặng {r['silence']:.1f}s ở chỗ nối kiểu `{k}` (dự kiến {gap:.1f}s)"))
            if gap == 0 and r["dip_lu"] > (25 if k == "natural" else 12):
                out.append(("warn", r["no"], f"hụt tiếng {r['dip_lu']:.0f} LU ở chỗ nối (không có khoảng lặng dự kiến)"))
    return out


def _dur(plan: dict) -> float:
    from .render import timeline
    st = timeline(plan)
    last = plan["tracks"][-1]
    return st[-1] + last["out"] - last["in"] + plan.get("tail_silence", 0)


def write_md(plan: dict, album: Path, path: Path) -> None:
    old = path.read_text() if path.exists() else ""
    notes = old[old.index(NOTES_HEADING) + len(NOTES_HEADING):].strip() if NOTES_HEADING in old else ""
    tr, joins, res = plan["tracks"], plan["joins"], plan.get("result")
    cnt = Counter(j["type"] for j in joins)
    buckets = Counter(planner.BUCKET[j["type"]] for j in joins)
    issues = checks(plan)
    L = []
    title = tr[0]["title"]
    single = plan.get("kind") == "single"
    L += [f"# Audio bài đăng riêng — {title}" if single else f"# Assembly — {title}", "", MARK,
          "> Sinh tự động từ [assembly.yaml](assembly.yaml) bởi skill `album-assembly` (`.claude/skills/album-assembly/scripts/assemble.py`).",
          ("> Muốn chỉnh: sửa `in`/`fade_in`/`gain_db` trong yaml (+ `opening.locked: true` / `gain_locked: true` để `single` không tính lại), rồi `assemble.py render`."
           if single else "> Muốn chỉnh: `assemble.py set` hoặc sửa số trong yaml, rồi `assemble.py render`.") + " Khi sinh lại, chỉ mục **Ghi chú** cuối file được giữ.",
          "", "## Tóm tắt", ""]
    if res:
        L.append(f"- Bản ghép: `{plan['output']}` (+ `.mp3`) · **{fmt_time(res['duration'])}** · "
                 f"{res['lufs_i']} LUFS · true peak {res['true_peak']} dBTP · LRA {res['lra']}")
    else:
        L.append(f"- Dự kiến dài **{fmt_time(_dur(plan))}**, chưa render.")
    if joins:
        L.append(f"- {len(tr)} bài, {len(joins)} điểm nối: " + ", ".join(f"{n}× {planner.RECIPES[k]['label']}" for k, n in cnt.most_common()))
        L.append("- Intro bài sau: " + " · ".join(f"{b} {buckets.get(b, 0)}" for b in ("ngay", "ngắn", "vừa", "dài")))
    else:
        L.append(f"- Một bài, giữ ending tự nhiên. Nguồn: `{tr[0]['audio']}`")
    nf, nw = sum(1 for i in issues if i[0] == "fail"), sum(1 for i in issues if i[0] == "warn")
    L.append(f"- Kiểm tra: {nf} lỗi, {nw} cảnh báo" + (" (xem mục Cảnh báo)" if issues else ""))
    L.append(f"- Loudness: mỗi bài cân về {plan['loudness']['target_lufs']} LUFS (đo trên đoạn được giữ), limiter {plan['loudness']['limit_db']} dBFS.")

    t1 = tr[0]
    L += ["", "## Mở video (0:00–0:15)", "",
          f"- Bài 01 vào từ giây **{t1['in']:.1f}** của file (bỏ {t1['in']:.0f}s intro Suno), fade-in {t1['fade_in']}s.",
          f"- Giọng hát vào ở giây **{t1['measured']['vocal_start'] - t1['in']:.1f}** của video."]
    if res:
        op = res["opening"]
        L.append(f"- Loudness so với thân bài: 0.5–5s **{op['m_0_5']:+.1f} LU**, 5–15s **{op['m_5_15']:+.1f} LU**; "
                 f"đạt mức thân bài ở giây {op['reaches_body_at']}.")
    L.append("- Video có logo intro ~4s phủ lên phần nhạc này (audio chạy từ 0:00).")

    if joins:
        L += ["", "## Các điểm nối", "",
              "| # | Nối | Kiểu | Bài trước kết | Bài sau vào | Chồng / lặng | Không lời | Vì sao |",
              "|---|---|---|---|---|---|---|---|"]
        for j in joins:
            A, B, f = tr[j["from"] - 1], tr[j["to"] - 1], j["feel"]
            a_end = (f"kết trọn (outro {A['measured']['outro_len']:.0f}s)" if j["type"] == "natural"
                     else f"giữ {f['a_tail']:.0f}s sau câu cuối, fade {A['fade_out']:.0f}s")
            b_in = f"intro {f['b_keep']:.1f}s (từ {B['in']:.1f}s), " + ("có trống" if f["b_entry_drums"] else "chưa trống")
            ov = f"chồng {j['overlap']:.1f}s" if j["overlap"] > 0 else f"lặng {-j['overlap']:.1f}s"
            lock = " 🔒" if j.get("locked") else ""
            L.append(f"| {j['no']} | {A['no']:02d} → {B['no']:02d} | {planner.RECIPES[j['type']]['label']}{lock} | {a_end} | "
                     f"{b_in} | {ov} | {f['vocal_gap']:.0f}s | {j['why']} |")

    L += ["", "## Điểm cắt từng bài", "",
          "Giây tính trong file gốc. *Giữ* = độ dài đoạn dùng. Intro/outro gốc = trước câu hát đầu / sau câu hát cuối.", "",
          "| # | Bài | Vào | Ra | Giữ | Fade vào / ra | Gain | Hát (file) | Intro / outro gốc | Kết gốc | BPM | Key | Energy |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for t in tr:
        m = t["measured"]
        L.append(f"| {t['no']:02d} | {t['title']} | {t['in']:.1f} | {t['out']:.1f} | {fmt_time(t['out'] - t['in'])} | "
                 f"{t['fade_in']} / {t['fade_out']} | {t['gain_db']:+.1f} dB | {m['vocal_start']:.1f}–{m['vocal_end']:.1f} | "
                 f"{m['intro_len']:.0f}s / {m['outro_len']:.0f}s | {m['end_type']} | {m['bpm'] or ''} | "
                 f"{m['camelot'] or ''} | {m['energy'] if m['energy'] is not None else ''} |")

    if not single:
        L += ["", "## Timestamps (chapters YouTube)", ""]
        if res:
            L += ["```"] + [f"{fmt_time(c['start'])} {c['title']}" for c in res["chapters"]] + ["```"]
        else:
            L.append("_Chưa render._")

    if res and joins:
        L += ["", "## Kiểm tra sau khi ghép", "",
              "*Chênh* = loudness 20s đầu có hát của bài sau − 20s cuối có hát của bài trước (nhỏ đi vài LU là tự nhiên: điệp khúc cuối → verse đầu). "
              "*Hụt* = chỗ nhỏ nhất ở vùng không lời so với hai bên (chỉ đáng lo ở kiểu nối không có khoảng lặng).", "",
              "| # | Tại | Kiểu | Chênh | Hụt | Lặng | Không lời |", "|---|---|---|---|---|---|---|"]
        for r, j in zip(res["joins"], joins):
            L.append(f"| {r['no']} | {fmt_time(r['at'])} | {planner.RECIPES[j['type']]['label']} | {r['jump_lu']:+.1f} LU | "
                     f"{r['dip_lu']:.0f} LU | {r['silence']:.1f}s | {r['vocal_gap']:.0f}s |")

    L += ["", "## Cảnh báo", ""]
    L += [f"- {'❌' if lv == 'fail' else '⚠️'} " + (f"Nối {no}: " if no else "") + msg for lv, no, msg in issues] or ["- Không có."]

    L += ["", "## Nghe thử", ""]
    if res and res.get("previews"):
        L.append("30 giây đầu (nghe như người lạ lướt YouTube, CLAUDE.md):" if single else
                 "Preview ngắn quanh từng điểm nối (từ ~6s trước câu cuối bài trước đến ~12s sau câu đầu bài sau):")
        L.append("")
        L += [f"- `{p}`" for p in res["previews"]]
        L += ["", "Với mỗi preview, nghe như người lạ (CLAUDE.md): nhảy volume? lặng quá lâu? intro quá dài? "
              "lặp công thức? drums vào đột ngột? room/reverb reset? giọng khác? tempo nhảy? "
              "Và: điểm vào bài mới có rõ, có ấn tượng không?"]
    else:
        L.append("_Chưa render._")

    L += ["", NOTES_HEADING, "", notes or "_(Ghi chú nghe thử của bạn ở đây; được giữ lại khi sinh lại file.)_", ""]
    path.write_text("\n".join(L))

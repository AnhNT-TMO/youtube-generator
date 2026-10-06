#!/usr/bin/env python3
import argparse
import json
import re
import statistics
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]
YT = ROOT / ".claude" / "skills" / "rnd-youtube-api"
MILESTONES = {"48h": 2.0, "7d": 7.0}
KINDS = ("album", "short")
LOW, HIGH = 0.7, 1.5
URL_ID = re.compile(r"(?:youtu\.be/|watch\?v=|/shorts/)([A-Za-z0-9_-]{11})")


def parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def front_matter(p: Path) -> dict:
    m = re.match(r"^---\s*\n(.*?)\n---", p.read_text(), re.S) if p.exists() else None
    return (yaml.safe_load(m.group(1)) or {}) if m else {}


def axes_of(kind: str, d: Path, ch: Path) -> dict:
    meta = front_matter(d / "short.md") if kind == "short" else {}
    if kind != "short":
        album = d
    elif d.name == "short" and d.parent.parent.name == "albums":
        album = d.parent
    else:
        album = ch / "albums" / Path(str(meta.get("album") or "")).name
    brief = front_matter(album / "album.md").get("brief") or {}
    target = brief.get("target") or {}
    goal = " / ".join(f"{target[k]:,}" if isinstance(target.get(k), int) else "–" for k in ("views_48h", "views_7d"))
    return {"topic": brief.get("topic"), "brief_source": brief.get("source"),
            "version": meta.get("version") if kind == "short" else brief.get("version"),
            "experiment": brief.get("experiment"), "target": None if kind == "short" or goal == "– / –" else goal}


def our_videos(ch: Path) -> dict:
    out = {}
    for kind, pattern in (("album", "albums/*/youtube.md"), ("short", "albums/*/short/youtube.md"),
                          ("short", "shorts/*/youtube.md")):
        for y in sorted(ch.glob(pattern)):
            m = re.search(r"Video URL:\*?\*?\s*(\S+)", y.read_text())
            vid = URL_ID.search(m.group(1)) if m else None
            if vid:
                out[vid.group(1)] = {"kind": kind, "dir": str(y.parent.relative_to(ROOT)), **axes_of(kind, y.parent, ch)}
    return out


def yt(*args) -> subprocess.CompletedProcess:
    py = YT / ".venv" / "bin" / "python"
    return subprocess.run([str(py if py.exists() else sys.executable), str(YT / "scripts" / "yt.py"), *args],
                          capture_output=True, text=True)


def own_channel_id(ch: Path, mapped: dict) -> str | None:
    tr = ch / "translate.yaml"
    m = re.search(r"^channel_id:[ \t]*['\"]?(UC[\w-]{22})", tr.read_text(), re.M) if tr.exists() else None
    if m:
        return m.group(1)
    r = yt("video", "--json", "--", next(iter(mapped)))
    if r.returncode or not json.loads(r.stdout or "[]"):
        return None
    cid = json.loads(r.stdout)[0]["channel_id"]
    print(f"⚠ channel/{ch.name}/translate.yaml chưa có channel_id: lấy từ video = {cid} (upload-youtube-translate auth điền)")
    return cid


def load_snapshots(cid: str) -> list:
    snaps = []
    for p in sorted((ROOT / "research" / "yt" / "videos" / cid).glob("*.json")):
        s = json.loads(p.read_text())
        snaps.append({"taken_at": s["taken_at"], "videos": {v["id"]: v for v in s.get("videos") or []}})
    return sorted(snaps, key=lambda s: s["taken_at"])


def series(snaps, vid):
    pts = []
    for s in snaps:
        v = s["videos"].get(vid)
        if v:
            age = (parse_ts(s["taken_at"]) - parse_ts(v["published"])).total_seconds() / 86400
            pts.append((age, v["views"], v["published"]))
    return sorted(pts)


def views_at(pts, age):
    if not pts or pts[-1][0] < age:
        return None
    prev = (0.0, 0)
    for a, v, _ in pts:
        if a >= age:
            return round(prev[1] + (v - prev[1]) * (age - prev[0]) / max(a - prev[0], 1e-6))
        prev = (a, v)
    return None


def main():
    ap = argparse.ArgumentParser(description="PM results: our albums + Shorts vs the channel median of the same kind at the same age (48 h, 7 d)")
    ap.add_argument("--channel", required=True)
    ap.add_argument("--no-fetch", action="store_true", help="don't read new view counts (rnd-youtube-api yt.py videos, ~2 units)")
    a = ap.parse_args()
    ch = ROOT / "channel" / a.channel
    mapped = our_videos(ch)
    if not mapped:
        sys.exit(f"chưa có video nào có Video URL trong channel/{a.channel}/albums/*/youtube.md, albums/*/short/youtube.md "
                 "(hay shorts/*/youtube.md cũ)")
    cid = own_channel_id(ch, mapped)
    if not cid:
        sys.exit("không biết channel id của kênh: điền channel_id trong translate.yaml")
    if not a.no_fetch:
        r = yt("videos", cid, "--kind", "all", "--json")
        if r.returncode:
            print(f"⚠ không lấy được view mới (rnd-youtube-api yt.py videos): {r.stderr.strip()[-300:]}; dùng snapshot đã có")
    snaps = load_snapshots(cid)
    if not snaps:
        sys.exit(f"chưa có snapshot research/yt/videos/{cid}/: chạy lại không có --no-fetch")
    rows = []
    for vid, info in mapped.items():
        pts = series(snaps, vid)
        if not pts:
            rows.append({"id": vid, **info, "published": None, "age_d": None, "views": None})
            continue
        age, views, pub = pts[-1]
        rows.append({"id": vid, **info, "published": pub[:10], "age_d": round(age, 1), "views": views,
                     **{k: views_at(pts, d) for k, d in MILESTONES.items()}})
    for k in MILESTONES:
        for kind in KINDS:
            vals = [r[k] for r in rows if r["kind"] == kind and r.get(k) is not None]
            med = statistics.median(vals) if vals else None
            for r in rows:
                if r["kind"] == kind:
                    r[f"{k}_x"] = round(r[k] / med, 2) if med and r.get(k) is not None else None
    for r in rows:
        last = next((r[f"{k}_x"] for k in reversed(list(MILESTONES)) if r.get(f"{k}_x") is not None), None)
        r["verdict"] = ("chưa đủ tuổi" if last is None else "dưới kỳ vọng → phân tích" if last < LOW
                        else "vượt" if last > HIGH else "ngang trung vị")
    an = ROOT / "production" / a.channel / "analytics.json"
    stats = json.loads(an.read_text())["videos"] if an.exists() else {}
    for r in rows:
        v = stats.get(r["id"]) or {}
        r["ret30"] = v.get("ret_30s")
        r["avd_pct"] = v.get("averageViewPercentage")
        r["ctr"] = v.get("impressionClickThroughRate")
        r["top_source"] = max(v["traffic"], key=v["traffic"].get) if v.get("traffic") else None
    out = ROOT / "production" / a.channel
    out.mkdir(parents=True, exist_ok=True)
    unmapped = [{"id": vid, "title": v["title"], "published": v["published"][:10], "views": v["views"]}
                for vid, v in snaps[-1]["videos"].items() if vid not in mapped]
    (out / "results.json").write_text(json.dumps({"snapshot": snaps[-1]["taken_at"], "videos": rows, "unmapped": unmapped},
                                                 indent=1, ensure_ascii=False))
    lines = [f"# Kết quả video · {a.channel} · snapshot {snaps[-1]['taken_at'][:16]}", "",
             f"View ở mốc 48 h / 7 d nội suy từ các snapshot `research/yt/videos/{cid}/`; `x` = so với trung vị cùng loại "
             f"(album / short) của kênh ở cùng mốc; dưới {LOW} = PM phân tích nguyên nhân, trên {HIGH} = ghi lại điều đã làm khác.", "",
             f"Analytics (`analytics.py fetch`): {'có, ' + json.loads(an.read_text())['fetched_at'][:16] if an.exists() else 'chưa có dữ liệu: chạy `analytics.py fetch` (lỗi nó in ra cho biết thiếu token hay chưa bật API)'}.", "",
             "| video | loại | đăng | tuổi | view | 48h (x) | 7d (x) | ret 30s | % xem | CTR | nguồn chính | chủ đề | version | experiment | kỳ vọng PM 48h / 7d | kết luận |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    fmt = lambda v, x: "–" if v is None else f"{v:,}" + (f" ({x})" if x is not None else "")
    for r in sorted(rows, key=lambda r: r.get("published") or "", reverse=True):
        lines.append(f"| [{Path(r['dir']).name}]({r['dir']}) | {r['kind']} | {r.get('published') or '–'} | {r.get('age_d') or '–'} d | "
                     f"{fmt(r.get('views'), None)} | {fmt(r.get('48h'), r.get('48h_x'))} | {fmt(r.get('7d'), r.get('7d_x'))} | "
                     f"{r.get('ret30') if r.get('ret30') is not None else '–'} | {r.get('avd_pct') if r.get('avd_pct') is not None else '–'} | "
                     f"{r.get('ctr') if r.get('ctr') is not None else '–'} | {r.get('top_source') or '–'} | "
                     f"{r.get('topic') or '–'} | {r.get('version') or '–'} | {r.get('experiment') or '–'} | {r.get('target') or '–'} | {r['verdict']} |")
    if unmapped:
        lines += ["", "## Video trên kênh chưa khớp thư mục nào (thiếu Video URL trong youtube.md)", ""]
        lines += [f"- {u['title']} · {u['published']} · {u['views']:,} view · https://youtu.be/{u['id']}" for u in unmapped]
    (out / "results.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import argparse
import json
import re
import statistics
import sys
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]
MILESTONES = {"48h": 2.0, "7d": 7.0}
LOW, HIGH = 0.7, 1.5
URL_ID = re.compile(r"(?:youtu\.be/|watch\?v=|/shorts/)([A-Za-z0-9_-]{11})")


def parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def front_matter(p: Path) -> dict:
    m = re.match(r"^---\s*\n(.*?)\n---", p.read_text(), re.S) if p.exists() else None
    return (yaml.safe_load(m.group(1)) or {}) if m else {}


def load_yaml(p: Path) -> dict:
    return (yaml.safe_load(p.read_text()) or {}) if p.exists() else {}


def axes_of(kind: str, d: Path, ch: Path) -> dict:
    plan = load_yaml(d / "plan.yaml")
    meta = {}
    if kind == "single":
        meta = front_matter(d / "single.md")
        album = meta.get("album") or ""
        plan = load_yaml(ch / "albums" / Path(str(album)).name / "plan.yaml") if album else {}
    elif kind == "short":
        meta = front_matter(d / "short.md")
        plan = load_yaml(ch / "albums" / Path(str(meta.get("album") or "")).name / "plan.yaml")
    brief = plan.get("brief") or {}
    dec = brief.get("decisions") or {}
    exp = plan.get("experiment") or {}
    return {"topic": brief.get("topic"), "brief_source": brief.get("source"),
            "version": meta.get("version") or dec.get("packaging_version"),
            "experiment": ",".join(exp.get("axes") or []) or None,
            "target": (dec.get("success") or {}).get("target")}


def our_videos(ch: Path) -> dict:
    out = {}
    for kind, sub in (("album", "albums"), ("single", "singles"), ("short", "shorts")):
        for y in sorted((ch / sub).glob("*/youtube.md")):
            m = re.search(r"Video URL:\*?\*?\s*(\S+)", y.read_text())
            vid = URL_ID.search(m.group(1)) if m else None
            if vid:
                out[vid.group(1)] = {"kind": kind, "dir": str(y.parent.relative_to(ROOT)), **axes_of(kind, y.parent, ch)}
    return out


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
    ap = argparse.ArgumentParser(description="PM results: our videos vs the channel median at the same age (48 h, 7 d)")
    ap.add_argument("--channel", required=True)
    a = ap.parse_args()
    ch = ROOT / "channel" / a.channel
    snaps = [json.loads(p.read_text()) for p in sorted((ROOT / "research" / "trends" / a.channel / "snapshots").glob("*.json"))]
    if not snaps:
        sys.exit("no pulse snapshot: youtube-trend-research trend.py pulse first")
    own_id = snaps[-1].get("own_channel")
    mapped = our_videos(ch)
    own_in_snap = {vid: v for vid, v in snaps[-1]["videos"].items() if v["ch"] == own_id}
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
        for kind in ("album", "single", "short"):
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
    unmapped = [{"id": vid, "title": v["title"], "published": v["published"][:10], "views": v["views"]}
                for vid, v in own_in_snap.items() if vid not in mapped]
    out = ROOT / "production" / a.channel
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps({"snapshot": snaps[-1]["taken_at"], "videos": rows, "unmapped": unmapped},
                                                 indent=1, ensure_ascii=False))
    lines = [f"# Kết quả video · {a.channel} · snapshot {snaps[-1]['taken_at'][:16]}", "",
             f"View ở mốc 48 h / 7 d nội suy từ các pulse; `x` = so với trung vị cùng loại của kênh ở cùng mốc; dưới {LOW} = PM phân tích "
             f"nguyên nhân (CLAUDE.md §0), trên {HIGH} = ghi lại điều đã làm khác.", "",
             f"Analytics (`analytics.py fetch`): {'có, ' + json.loads(an.read_text())['fetched_at'][:16] if an.exists() else 'chưa có dữ liệu: chạy `analytics.py fetch` (lỗi nó in ra cho biết thiếu token hay chưa bật API)'}.", "",
             "| video | loại | đăng | tuổi | view | 48h (x) | 7d (x) | ret 30s | % xem | CTR | nguồn chính | chủ đề | version | experiment | kỳ vọng PM | kết luận |",
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

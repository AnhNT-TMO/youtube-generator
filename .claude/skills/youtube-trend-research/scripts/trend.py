#!/usr/bin/env python3
import argparse
import json
import os
import re
import statistics
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]
API = "https://www.googleapis.com/youtube/v3/"
KEY_FILE = Path("~/.config/yt-research/api_key").expanduser()
COST = {"search": 100}
HIT_X = 3.0
SHORT_MAX_S = 180
SNAPSHOT_MAX_AGE_D = 2
RECENT_DAYS = 14
FRESH_CHANNEL_DAYS = 120


class Api:
    def __init__(self, data_dir: Path, cmd: str):
        key = os.environ.get("YT_API_KEY") or (KEY_FILE.read_text().strip() if KEY_FILE.exists() else "")
        if not key:
            sys.exit(f"no API key: put it in {KEY_FILE} (chmod 600) or YT_API_KEY")
        self.key, self.units, self.data_dir, self.cmd = key, 0, data_dir, cmd

    def call(self, endpoint: str, **params):
        params["key"] = self.key
        url = API + endpoint + "?" + urllib.parse.urlencode(params)
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                self.units += COST.get(endpoint, 1)
                return json.load(r)
        except urllib.error.HTTPError as e:
            self.units += COST.get(endpoint, 1)
            body = e.read().decode("utf-8", "replace")
            if "quotaExceeded" in body:
                self.log()
                sys.exit("YouTube API quota exceeded for today (resets at midnight Pacific time)")
            raise RuntimeError(f"{endpoint} HTTP {e.code}: {body[:200]}")

    def log(self):
        pac = (datetime.now(timezone.utc) - timedelta(hours=7)).date().isoformat()
        with open(self.data_dir / "units.log", "a") as f:
            f.write(f"{pac}\t{datetime.now().isoformat(timespec='seconds')}\t{self.cmd}\t{self.units}\n")
        total = sum(int(l.split("\t")[3]) for l in (self.data_dir / "units.log").read_text().splitlines() if l.startswith(pac))
        print(f"units: {self.units} this run, {total} / 10000 today (Pacific {pac})")


def chunks(items, n=50):
    items = list(items)
    for i in range(0, len(items), n):
        yield items[i:i + n]


def iso_seconds(d: str) -> int:
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d or "")
    if not m:
        return 0
    dd, h, mi, s = (int(x or 0) for x in m.groups())
    return dd * 86400 + h * 3600 + mi * 60 + s


def now_utc():
    return datetime.now(timezone.utc)


def parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def load_config(ch: str) -> dict:
    f = ROOT / "channel" / ch / "trends.yaml"
    if not f.exists():
        sys.exit(f"missing {f.relative_to(ROOT)} (copy channel/_template/trends.yaml)")
    return yaml.safe_load(f.read_text()) or {}


def data_dir(ch: str) -> Path:
    d = ROOT / "research" / "trends" / ch
    for sub in ("snapshots", "discover", "topics", "comments", "sheets", "reports", "shorts"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    return d


def read_json(p: Path, default):
    return json.loads(p.read_text()) if p.exists() else default


def write_json(p: Path, obj):
    p.write_text(json.dumps(obj, indent=1, ensure_ascii=False))


def matcher(words):
    pats = [re.compile(r"(?<![a-z])" + re.escape(str(w).lower()) + r"(?![a-z])") for w in words or []]
    return lambda text: any(p.search(text.lower()) for p in pats)


def fetch_channels(api: Api, ids):
    out = {}
    for batch in chunks(ids):
        for c in api.call("channels", part="snippet,statistics,contentDetails", id=",".join(batch)).get("items", []):
            out[c["id"]] = {"title": c["snippet"]["title"], "created": c["snippet"]["publishedAt"][:10],
                            "subs": int(c["statistics"].get("subscriberCount", 0) or 0),
                            "video_count": int(c["statistics"].get("videoCount", 0) or 0),
                            "uploads": c["contentDetails"]["relatedPlaylists"]["uploads"]}
    return out


def fetch_uploads(api: Api, uploads_playlist: str, n: int = 50):
    try:
        items = api.call("playlistItems", part="contentDetails", playlistId=uploads_playlist, maxResults=n).get("items", [])
    except RuntimeError:
        return []
    return [i["contentDetails"]["videoId"] for i in items]


def fetch_videos(api: Api, ids):
    out = {}
    for batch in chunks(ids):
        for v in api.call("videos", part="snippet,statistics,contentDetails", id=",".join(batch)).get("items", []):
            s, st = v["snippet"], v["statistics"]
            out[v["id"]] = {"ch": s["channelId"], "title": s["title"], "published": s["publishedAt"],
                            "dur_s": iso_seconds(v["contentDetails"].get("duration", "")),
                            "live": s.get("liveBroadcastContent", "none") != "none",
                            "views": int(st.get("viewCount", 0) or 0), "likes": int(st.get("likeCount", 0) or 0),
                            "comments": int(st.get("commentCount", 0) or 0),
                            "tags": s.get("tags", [])[:30], "desc_head": (s.get("description") or "")[:300]}
    return out


FOREIGN_WORDS = set("de para que com y en la el los las del das do da dos et le les pour une mi con por sus nos ao".split())


def foreign(title: str) -> bool:
    if any(ord(c) > 127 and c.isalpha() for c in title):
        return True
    return len(FOREIGN_WORDS & set(re.findall(r"[a-z]+", title.lower()))) >= 2


def channel_check(cfg: dict, info: dict, titles, kind: str = "long") -> tuple[bool, str, int]:
    nc = cfg.get("niche") or {}
    keywords = ((cfg.get("shorts") or {}).get("niche_keywords") or nc.get("keywords")) if kind == "shorts" else nc.get("keywords")
    titles = list(titles)
    n = sum(1 for t in titles if matcher(keywords)(t))
    if n < min(int(nc.get("min_matches", 10)), max(3, (len(titles) + 1) // 2)):
        return False, f"niche {n}/{len(titles)}", n
    music = (cfg.get("shorts") or {}).get("music_keywords") if kind == "shorts" else None
    if music:
        nm = sum(1 for t in titles if matcher(music)(t))
        if nm < max(3, len(titles) // 5):
            return False, f"music words in {nm}/{len(titles)} titles", n
    ex_words = list(nc.get("exclude") or []) + (list((cfg.get("shorts") or {}).get("exclude_extra") or []) if kind == "shorts" else [])
    ex = sum(1 for t in titles if matcher(ex_words)(t))
    if ex >= max(3, len(titles) // 10):
        return False, f"exclude words in {ex} titles", n
    fs = sum(1 for t in titles if foreign(t)) / max(len(titles), 1)
    if fs > float(nc.get("foreign_max_share", 0.3)):
        return False, f"other language {fs:.0%}", n
    if nc.get("max_subs") and info.get("subs", 0) > int(nc["max_subs"]):
        return False, f"{info.get('subs'):,} subs > max_subs", n
    return True, "ok", n


def cmd_discover(a, cfg, d: Path):
    api = Api(d, "discover")
    wl = read_json(d / "watchlist.json", {})
    window = int(cfg.get("window_days", 60))
    after = (now_utc() - timedelta(days=window)).strftime("%Y-%m-%dT%H:%M:%SZ")
    disc = cfg.get("discover") or {}
    kind = "shorts" if a.shorts else "long"
    if a.shorts:
        disc = {**disc, "queries": (cfg.get("shorts") or {}).get("discover_queries") or [], "duration": "short"}
    queries = list(disc.get("queries") or [])[: a.max_queries or None]
    hits, cand = {}, {}
    if not a.no_search:
        for q in queries:
            res = api.call("search", part="snippet", q=q, type="video", order="viewCount", publishedAfter=after,
                           videoDuration=disc.get("duration", "long"), maxResults=int(disc.get("per_query", 50)),
                           relevanceLanguage=cfg.get("language", "en"))
            for rank, it in enumerate(res.get("items", []), 1):
                hits.setdefault(it["id"]["videoId"], []).append([q, rank])
                cand.setdefault(it["snippet"]["channelId"], f"search{' shorts' if a.shorts else ''}: {q}")
    for f in a.import_json or []:
        rows = json.loads(Path(f).read_text())
        rows = rows if isinstance(rows, list) else list(rows.values())
        for r in rows:
            cid = r.get("channel_id") or r.get("ch") or r.get("id") if isinstance(r, dict) else None
            if cid and str(cid).startswith("UC"):
                cand.setdefault(cid, f"import: {Path(f).name}")
    for cid in (cfg.get("seed_channels") or []):
        cand.setdefault(cid, "seed")
    seen = read_json(d / "candidates.json", {})
    today = now_utc().date()
    fresh = {c for c, v in seen.items() if (today - datetime.fromisoformat(v["checked"]).date()).days < 30}
    new = [c for c in cand if c not in wl and c not in fresh and c != cfg.get("own_channel")]
    info = fetch_channels(api, new)
    added, rejected = [], []
    for cid, c in info.items():
        titles = [v["title"] for v in fetch_videos(api, fetch_uploads(api, c["uploads"])).values()]
        ok, why, n = channel_check(cfg, c, titles, kind)
        seen[cid] = {"title": c["title"], "subs": c["subs"], "created": c["created"], "checked": today.isoformat(),
                     "ok": ok, "why": why, "via": cand[cid], "kind": kind, "titles": titles}
        if ok:
            wl[cid] = {**c, "added": today.isoformat(), "via": cand[cid], "kind": kind, "niche_titles": n,
                       "niche_share": round(n / max(len(titles), 1), 2)}
            added.append([cid, c["title"], n, cand[cid]])
        else:
            rejected.append([cid, c["title"], why])
    write_json(d / "candidates.json", seen)
    wl = cap_watchlist(wl, cfg)
    write_json(d / "watchlist.json", wl)
    write_json(d / "discover" / f"{now_utc().date().isoformat()}{'-shorts' if a.shorts else ''}.json",
               {"queries": queries, "published_after": after, "hits": hits, "added": added, "rejected": rejected})
    print(f"candidates {len(cand)}, new {len(new)}, added {len(added)}, rejected {len(rejected)}, watchlist {len(wl)}")
    for _, t, n, via in added:
        print(f"  + {t} ({n} niche titles; {via})")
    api.log()


def cap_watchlist(wl: dict, cfg: dict) -> dict:
    cap = int(cfg.get("watchlist_max", 150))
    if len(wl) <= cap:
        return wl
    print(f"watchlist {len(wl)} > watchlist_max {cap}: keeping the {cap} with the highest share of niche titles")
    return dict(sorted(wl.items(), key=lambda kv: -kv[1].get("niche_share", 0))[:cap])


def cmd_prune(a, cfg, d: Path):
    wl = read_json(d / "watchlist.json", {})
    snaps = snapshots(d)
    if not snaps:
        sys.exit("no snapshot: run pulse first")
    snap = json.loads(snaps[-1].read_text())
    titles = {}
    for v in snap["videos"].values():
        titles.setdefault(v["ch"], []).append(v["title"])
    keep, dropped = {}, []
    for cid, w in wl.items():
        if cid not in titles:
            keep[cid] = w
            continue
        ok, why, n = channel_check(cfg, {**w, **(snap["channels"].get(cid) or {})}, titles[cid], w.get("kind", "long"))
        if ok:
            keep[cid] = {**w, "niche_titles": n, "niche_share": round(n / max(len(titles[cid]), 1), 2)}
        else:
            dropped.append((w.get("title"), why))
    keep = cap_watchlist(keep, cfg)
    write_json(d / "watchlist.json", keep)
    print(f"watchlist {len(wl)} -> {len(keep)} (dropped {len(dropped)})")
    for t, why in dropped:
        print(f"  - {t}: {why}")


def cmd_pulse(a, cfg, d: Path):
    api = Api(d, "pulse")
    wl = read_json(d / "watchlist.json", {})
    if not wl:
        sys.exit("watchlist empty: run discover first")
    own = cfg.get("own_channel")
    ids = list(wl) + ([own] if own else [])
    chans = fetch_channels(api, ids)
    vids = {}
    for cid, c in chans.items():
        for vid in fetch_uploads(api, c["uploads"]):
            vids[vid] = cid
    videos = fetch_videos(api, vids)
    for cid, c in chans.items():
        if cid in wl:
            wl[cid].update({k: c[k] for k in ("title", "subs", "video_count", "uploads")})
    write_json(d / "watchlist.json", wl)
    snap = {"taken_at": now_utc().isoformat(timespec="seconds"), "own_channel": own,
            "channels": {cid: {k: c[k] for k in ("title", "created", "subs", "video_count")} for cid, c in chans.items()},
            "videos": videos}
    write_json(d / "snapshots" / f"{now_utc().date().isoformat()}.json", snap)
    print(f"snapshot: {len(chans)} channels, {len(videos)} videos")
    api.log()


def snapshots(d: Path):
    return sorted((d / "snapshots").glob("*.json"))


def previous_snapshot(d: Path, latest_at: datetime, min_days=0.7, max_days=8):
    best = None
    for p in snapshots(d):
        s = json.loads(p.read_text())
        age = (latest_at - parse_ts(s["taken_at"])).total_seconds() / 86400
        if min_days <= age <= max_days:
            best = s
    return best


def enrich(snap: dict, prev: dict | None, cfg: dict):
    at = parse_ts(snap["taken_at"])
    rows = []
    by_ch = {}
    for vid, v in snap["videos"].items():
        by_ch.setdefault(v["ch"], []).append(v["views"])
    med = {c: statistics.median(vs) for c, vs in by_ch.items() if vs}
    pv = (prev or {}).get("videos") or {}
    gap = (at - parse_ts(prev["taken_at"])).total_seconds() / 86400 if prev else None
    for vid, v in snap["videos"].items():
        age = max((at - parse_ts(v["published"])).total_seconds() / 86400, 0.5)
        vel = None
        if vid in pv and gap:
            vel = max(v["views"] - pv[vid]["views"], 0) / gap
        elif gap and age <= gap:
            vel = v["views"] / age
        ch = snap["channels"].get(v["ch"], {})
        rows.append({"id": vid, **v, "age_d": round(age, 1), "vpd": round(v["views"] / age, 1),
                     "vel": None if vel is None else round(vel, 1),
                     "x": round(v["views"] / med[v["ch"]], 2) if med.get(v["ch"]) else None,
                     "channel": ch.get("title"), "ch_created": ch.get("created"), "subs": ch.get("subs"),
                     "own": v["ch"] == snap.get("own_channel")})
    return rows, gap


def in_window(r, cfg):
    return (not r["live"] and r["age_d"] <= int(cfg.get("window_days", 60))
            and r["dur_s"] >= 60 * float(cfg.get("min_minutes", 20)))


def label_rows(rows, groups: dict):
    ms = {name: matcher(words) for name, words in (groups or {}).items()}
    for r in rows:
        text = r["title"]
        r.setdefault("labels", [])
        r["labels"] += [n for n, m in ms.items() if m(text)]


def summarize(rows, names, key_field="labels"):
    total_vel = sum(r["vel"] or 0 for r in rows) or None
    total_vpd = sum(r["vpd"] for r in rows) or 1
    out = {}
    for name in names:
        g = [r for r in rows if name in r[key_field]]
        if not g:
            continue
        vels = [r["vel"] for r in g if r["vel"] is not None]
        hits = [r for r in g if (r["x"] or 0) >= HIT_X]
        top = sorted(g, key=lambda r: -(r["vel"] if r["vel"] is not None else r["vpd"]))[:3]
        out[name] = {"videos": len(g), "channels": len({r["ch"] for r in g}),
                     "median_vpd": round(statistics.median(r["vpd"] for r in g)),
                     "vel_sum": round(sum(vels)) if vels else None,
                     "share_vel": round(100 * sum(vels) / total_vel, 1) if vels and total_vel else None,
                     "share_vpd": round(100 * sum(r["vpd"] for r in g) / total_vpd, 1),
                     "hits": len(hits), "hit_rate": round(100 * len(hits) / len(g)),
                     "recent_hits": sum(1 for r in hits if r["age_d"] <= RECENT_DAYS),
                     "fresh_channel_hits": sum(1 for r in hits if r["ch_created"] and
                                               (datetime.now().date() - datetime.fromisoformat(r["ch_created"]).date()).days <= FRESH_CHANNEL_DAYS),
                     "top": [{"id": r["id"], "title": r["title"], "channel": r["channel"], "views": r["views"],
                              "vpd": r["vpd"], "vel": r["vel"], "x": r["x"], "age_d": r["age_d"]} for r in top]}
    return out


def status_of(cur: dict, old: dict | None):
    if old and cur.get("share_vel") is not None and old.get("share_vel"):
        ratio = cur["share_vel"] / old["share_vel"]
        return "rising" if ratio >= 1.2 else "fading" if ratio <= 0.8 else "steady"
    if cur["hits"] == 0:
        return "no hits"
    return "hits now" if cur["recent_hits"] else "old hits only"


def cmd_topics(a, cfg, d: Path):
    snaps = snapshots(d)
    if not snaps:
        sys.exit("no snapshot: run pulse first")
    snap = json.loads(snaps[-1].read_text())
    prev = previous_snapshot(d, parse_ts(snap["taken_at"]))
    rows, gap = enrich(snap, prev, cfg)
    wl = read_json(d / "watchlist.json", {})
    niche = [r for r in rows if in_window(r, cfg) and not r["own"] and r["ch"] in wl]
    for r in niche:
        r["labels"], r["branch"] = [], []
    label_rows(niche, cfg.get("topics"))
    bm = {n: matcher(w) for n, w in (cfg.get("branches") or {}).items()}
    for r in niche:
        r["branch"] = [n for n, m in bm.items() if m(r["title"])]
    topics = summarize(niche, list((cfg.get("topics") or {}).keys()))
    branches = summarize(niche, list((cfg.get("branches") or {}).keys()), "branch")
    date = snaps[-1].stem
    old = None
    for p in sorted((d / "topics").glob("*.json")):
        if p.stem < date and (datetime.fromisoformat(date) - datetime.fromisoformat(p.stem)).days >= 6:
            old = json.loads(p.read_text())
    for name, t in topics.items():
        t["status"] = status_of(t, ((old or {}).get("topics") or {}).get(name))
    for name, t in branches.items():
        t["status"] = status_of(t, ((old or {}).get("branches") or {}).get(name))
    unlabeled = sorted([r for r in niche if not r["labels"] and (r["x"] or 0) >= HIT_X],
                       key=lambda r: -r["vpd"])[:15]
    own = sorted([r for r in rows if r["own"]], key=lambda r: r["published"], reverse=True)
    own_ch = snap["channels"].get(snap.get("own_channel") or "", {})
    result = {"date": date, "taken_at": snap["taken_at"], "velocity_gap_days": gap, "niche_videos": len(niche),
              "niche_channels": len({r["ch"] for r in niche}), "compared_to": (old or {}).get("date"),
              "topics": topics, "branches": branches,
              "unlabeled_hits": [{k: r[k] for k in ("id", "title", "channel", "views", "vpd", "x", "age_d")} for r in unlabeled],
              "own": {"title": own_ch.get("title"), "subs": own_ch.get("subs"),
                      "videos": [{k: r[k] for k in ("id", "title", "published", "views", "vpd", "vel", "age_d")} for r in own]}}
    write_json(d / "topics" / f"{date}.json", result)
    md = render_topics(result, cfg)
    (d / "topics" / f"{date}.md").write_text(md)
    print(md)


def fmt(v, suffix=""):
    return "–" if v is None else f"{v:,}{suffix}" if isinstance(v, int) else f"{v}{suffix}"


def render_topics(r: dict, cfg: dict) -> str:
    vel_note = (f"view/ngày đo giữa 2 snapshot cách {r['velocity_gap_days']:.1f} ngày" if r["velocity_gap_days"]
                else "chưa có snapshot trước: cột `vel` trống, dùng `median vpd` (view/ngày tính từ lúc đăng)")
    out = [f"# Topics {r['date']}", "",
           f"{r['niche_videos']} video / {r['niche_channels']} kênh trong cửa sổ {cfg.get('window_days', 60)} ngày, ≥ {cfg.get('min_minutes', 20)} phút. "
           f"{vel_note}. So với: {r['compared_to'] or 'chưa có bảng cũ ≥ 6 ngày'}.", "",
           "`x` = view / trung vị 50 video gần nhất của chính kênh đó; hit = x ≥ 3; `recent` = hit đăng ≤ 14 ngày; "
           "`fresh` = hit của kênh tạo ≤ 120 ngày.", ""]
    for title, key in (("Chủ đề (lời, title)", "topics"), ("Nhánh nhạc", "branches")):
        out += [f"## {title}", "", "| | status | video | kênh | median vpd | vel Σ | % vel | % vpd | hit (rate) | recent | fresh | video mạnh nhất |",
                "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for name, t in sorted(r[key].items(), key=lambda kv: -(kv[1]["share_vel"] or kv[1]["share_vpd"])):
            best = t["top"][0]
            out.append(f"| {name} | {t['status']} | {t['videos']} | {t['channels']} | {fmt(t['median_vpd'])} | {fmt(t['vel_sum'])} | "
                       f"{fmt(t['share_vel'])} | {fmt(t['share_vpd'])} | {t['hits']} ({t['hit_rate']}%) | {t['recent_hits']} | "
                       f"{t['fresh_channel_hits']} | {best['title'][:60]} ({best['channel']}, {fmt(round(best['vpd']))}/d, x{best['x']}) |")
        out.append("")
    out += ["## Hit chưa gắn chủ đề (Claude đặt tên, thêm từ khóa vào trends.yaml nếu là chủ đề mới)", "",
            "| video | kênh | view | vpd | x | tuổi |", "|---|---|---|---|---|---|"]
    out += [f"| {u['title'][:80]} | {u['channel']} | {u['views']:,} | {round(u['vpd'])} | {u['x']} | {round(u['age_d'])} d |"
            for u in r["unlabeled_hits"]]
    o = r["own"]
    out += ["", f"## Kênh mình: {o['title']} · {fmt(o['subs'])} sub", "", "| video | đăng | view | vpd | vel |", "|---|---|---|---|---|"]
    out += [f"| {v['title'][:70]} | {v['published'][:10]} | {v['views']:,} | {v['vpd']} | {fmt(v['vel'])} |" for v in o["videos"]]
    return "\n".join(out) + "\n"


def latest_rows(d: Path, cfg: dict):
    snaps = snapshots(d)
    if not snaps:
        sys.exit("no snapshot: run pulse first")
    snap = json.loads(snaps[-1].read_text())
    rows, _ = enrich(snap, previous_snapshot(d, parse_ts(snap["taken_at"])), cfg)
    return rows


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())[:24] or "channel"


def cmd_refs(a, cfg, d: Path):
    wl = read_json(d / "watchlist.json", {})
    rows = [r for r in latest_rows(d, cfg) if in_window(r, cfg) and not r["own"] and r["ch"] in wl]
    groups = {**(cfg.get("topics") or {}), **(cfg.get("branches") or {})}
    need = [g for g in (a.topic or []) if g not in groups]
    if need:
        sys.exit(f"unknown topic/branch {need}; known: {sorted(groups)}")
    ms = [matcher(groups[g]) for g in a.topic or []]
    g = [r for r in rows if all(m(r["title"]) for m in ms) and (r["x"] or 0) >= a.min_x
         and r["dur_s"] <= 60 * a.max_minutes]
    g.sort(key=lambda r: -(r["vel"] if r["vel"] is not None else r["vpd"]))
    seen, picked = set(), []
    for r in g:
        if r["ch"] in seen:
            continue
        seen.add(r["ch"])
        picked.append(r)
        if len(picked) >= a.n:
            break
    tag = "-".join(a.topic or ["niche"])
    print(f"{len(g)} candidates for {tag} (x ≥ {a.min_x}, ≤ {a.max_minutes} min, 1 per channel):")
    for r in picked:
        print(f"https://www.youtube.com/watch?v={r['id']}  research/{slugify(r['channel'])}-{tag}-{r['id'][:6].lower()}  "
              f"| {r['channel']} | {r['title'][:70]} | {r['views']:,} v, {round(r['vpd'])}/d, x{r['x']}, {r['dur_s'] // 60} min")


def cmd_comments(a, cfg, d: Path):
    api = Api(d, "comments")
    for vid in a.video:
        res = api.call("commentThreads", part="snippet", videoId=vid, order="relevance", maxResults=50, textFormat="plainText")
        rows = [{"likes": it["snippet"]["topLevelComment"]["snippet"].get("likeCount", 0),
                 "text": it["snippet"]["topLevelComment"]["snippet"]["textDisplay"]} for it in res.get("items", [])]
        write_json(d / "comments" / f"{vid}.json", rows)
        print(f"== {vid}: {len(rows)} comments")
        for c in rows[: a.show]:
            print(f"  [{c['likes']}] {c['text'][:220].replace(chr(10), ' ')}")
    api.log()


def cmd_sheet(a, cfg, d: Path):
    from io import BytesIO
    from PIL import Image, ImageDraw
    rows = {r["id"]: r for r in latest_rows(d, cfg)}
    W, H, COLS = 640, 360, 2
    tiles = []
    for i, vid in enumerate(a.video, 1):
        img = None
        for q in ("maxresdefault", "hqdefault"):
            try:
                img = Image.open(BytesIO(urllib.request.urlopen(f"https://i.ytimg.com/vi/{vid}/{q}.jpg", timeout=20).read())).convert("RGB")
                break
            except Exception:
                continue
        if img is None:
            print("skip", vid)
            continue
        w, h = img.size
        ch = int(w * 9 / 16)
        img = img.crop((0, (h - ch) // 2, w, (h - ch) // 2 + ch)).resize((W, H))
        r = rows.get(vid, {})
        label = f"{i:02d} {r.get('channel', '')[:28]} {round(r['vpd']) if r else ''}/d x{r.get('x', '')}"
        dr = ImageDraw.Draw(img)
        dr.rectangle((0, 0, 8 + 7 * len(label), 22), fill=(0, 0, 0))
        dr.text((5, 5), label, fill=(255, 230, 0))
        tiles.append(img)
    if not tiles:
        sys.exit("no thumbnails")
    rows_n = (len(tiles) + COLS - 1) // COLS
    sheet = Image.new("RGB", (W * COLS, H * rows_n), (25, 25, 25))
    for k, im in enumerate(tiles):
        sheet.paste(im, ((k % COLS) * W, (k // COLS) * H))
    out = d / "sheets" / f"{now_utc().date().isoformat()}-{a.name}.jpg"
    sheet.save(out, quality=88)
    print(out.relative_to(ROOT))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def shorts_url_status(vid: str):
    req = urllib.request.Request(f"https://www.youtube.com/shorts/{vid}", method="HEAD",
                                 headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en"})
    try:
        with urllib.request.build_opener(NoRedirect).open(req, timeout=15) as r:
            return True if r.status == 200 else None
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308) and "/watch" in (e.headers.get("Location") or ""):
            return False
        return None
    except Exception:
        return None


def confirm_shorts(d: Path, ids) -> dict:
    from concurrent.futures import ThreadPoolExecutor
    cache_file = d / "shorts" / "is_short.json"
    cache = read_json(cache_file, {})
    todo = [v for v in ids if v not in cache]
    if todo:
        print(f"checking {len(todo)} video(s) at youtube.com/shorts/<id> (cached {len(ids) - len(todo)})")
        with ThreadPoolExecutor(8) as ex:
            for vid, st in zip(todo, ex.map(shorts_url_status, todo)):
                if st is not None:
                    cache[vid] = st
        write_json(cache_file, cache)
    return {v: cache.get(v) for v in ids}


def fmt_dur(s: int) -> str:
    return f"{s // 60}:{s % 60:02d}"


def shorts_settings(a, cfg: dict):
    sc = cfg.get("shorts") or {}
    days = a.days or int(sc.get("days", cfg.get("window_days", 60)))
    top = a.top or int(sc.get("top", 20))
    per_channel = a.per_channel if a.per_channel is not None else int(sc.get("per_channel", 3))
    max_s = int(sc.get("max_seconds", SHORT_MAX_S))
    return days, top, per_channel, max_s


def cmd_shorts(a, cfg, d: Path):
    days, top_n, per_channel, max_s = shorts_settings(a, cfg)
    snaps = snapshots(d)
    age = (now_utc() - parse_ts(json.loads(snaps[-1].read_text())["taken_at"])).total_seconds() / 86400 if snaps else None
    if a.fetch or age is None or age > SNAPSHOT_MAX_AGE_D:
        print(f"latest snapshot {'missing' if age is None else f'{age:.1f} days old'}: running pulse (~2 units / channel)")
        cmd_pulse(a, cfg, d)
    else:
        print(f"using snapshot {snaps[-1].name} ({age:.1f} days old, 0 units)")
    wl = read_json(d / "watchlist.json", {})
    rows = [r for r in latest_rows(d, cfg) if (r["ch"] in wl or r["own"]) and not r["live"]]
    oldest = {}
    for r in rows:
        oldest[r["ch"]] = max(oldest.get(r["ch"], 0), r["age_d"])
    win = [r for r in rows if r["age_d"] <= days]
    cand = [r for r in win if 0 < r["dur_s"] <= max_s]
    status = confirm_shorts(d, [r["id"] for r in cand])
    shorts = []
    for r in cand:
        if status[r["id"]] is False:
            continue
        r["short"] = "yes" if status[r["id"]] else "unconfirmed"
        shorts.append(r)
    niche = sorted([r for r in shorts if not r["own"]], key=lambda r: -r["vpd"])
    top, per = [], {}
    for r in niche:
        if per_channel and per.get(r["ch"], 0) >= per_channel:
            continue
        per[r["ch"]] = per.get(r["ch"], 0) + 1
        top.append(r)
        if len(top) >= top_n:
            break
    channels = []
    for cid in {r["ch"] for r in niche}:
        mine = [r for r in niche if r["ch"] == cid]
        longs = [r for r in win if r["ch"] == cid and (r["dur_s"] > max_s or status.get(r["id"]) is False)]
        span = max(min(days, oldest[cid]), 1)
        channels.append({"ch": cid, "channel": mine[0]["channel"], "subs": mine[0]["subs"], "shorts": len(mine),
                         "shorts_per_week": round(7 * len(mine) / span, 1), "span_d": round(span),
                         "median_vpd_shorts": round(statistics.median(r["vpd"] for r in mine), 1),
                         "median_vpd_long": round(statistics.median(r["vpd"] for r in longs), 1) if longs else None,
                         "long_videos": len(longs), "vpd_sum_shorts": round(sum(r["vpd"] for r in mine))})
    channels.sort(key=lambda c: -c["vpd_sum_shorts"])
    med_short = {c["ch"]: c["median_vpd_shorts"] for c in channels}
    for r in niche:
        r["xs"] = round(r["vpd"] / med_short[r["ch"]], 2) if med_short.get(r["ch"]) else None
    formats = shorts_groups(niche, (cfg.get("shorts") or {}).get("formats") or {})
    topics = shorts_groups(niche, cfg.get("topics") or {})
    own = sorted([r for r in shorts if r["own"]], key=lambda r: r["published"], reverse=True)
    own_long = [r for r in win if r["own"] and (r["dur_s"] > max_s or status.get(r["id"]) is False)]
    date = now_utc().date().isoformat()
    out_dir = d / "shorts"
    sheet = shorts_sheet(top, out_dir / f"{date}-sheet.jpg")
    keys = ("id", "channel", "title", "published", "views", "likes", "comments", "dur_s", "age_d", "vpd", "vel", "short")
    result = {"date": date, "days": days, "max_seconds": max_s, "per_channel": per_channel,
              "watchlist_channels": len(wl), "candidates": len(cand),
              "confirmed": sum(1 for r in shorts if r["short"] == "yes"),
              "unconfirmed": sum(1 for r in shorts if r["short"] == "unconfirmed"),
              "not_shorts": sum(1 for r in cand if status[r["id"]] is False),
              "sheet": str(sheet.relative_to(ROOT)) if sheet else None,
              "top": [{"rank": i, **{k: r[k] for k in keys}, "url": f"https://www.youtube.com/shorts/{r['id']}"}
                      for i, r in enumerate(top, 1)],
              "channels": channels, "formats": formats, "topics": topics,
              "own": {"shorts": [{k: r[k] for k in keys} for r in own],
                      "median_vpd_long": round(statistics.median(r["vpd"] for r in own_long), 1) if own_long else None}}
    write_json(out_dir / f"{date}.json", result)
    md = render_shorts(result)
    (out_dir / f"{date}.md").write_text(md)
    print(md)
    print(out_dir.relative_to(ROOT) / f"{date}.md")
    if sheet:
        print(sheet.relative_to(ROOT))


def shorts_groups(rows, groups: dict) -> dict:
    total = sum(r["vpd"] for r in rows) or 1
    out = {}
    for name, words in groups.items():
        m = matcher(words)
        g = [r for r in rows if m(r["title"])]
        if not g:
            continue
        hits = [r for r in g if (r.get("xs") or 0) >= HIT_X]
        best = max(g, key=lambda r: r["vpd"])
        out[name] = {"shorts": len(g), "channels": len({r["ch"] for r in g}),
                     "median_vpd": round(statistics.median(r["vpd"] for r in g), 1),
                     "share_vpd": round(100 * sum(r["vpd"] for r in g) / total, 1),
                     "hits": len(hits), "hit_rate": round(100 * len(hits) / len(g)),
                     "recent_hits": sum(1 for r in hits if r["age_d"] <= RECENT_DAYS),
                     "best": {"id": best["id"], "title": best["title"], "channel": best["channel"], "vpd": best["vpd"]}}
    return dict(sorted(out.items(), key=lambda kv: -kv[1]["share_vpd"]))


def render_shorts(r: dict) -> str:
    cell = lambda v: str(v or "").replace("|", "/").strip()
    link = lambda t: f"[{cell(t['title'][:60])}](https://www.youtube.com/shorts/{t['id']})"
    mark = lambda t: "" if t["short"] == "yes" else " ?"
    out = [f"# Shorts {r['date']}", "",
           f"Video ≤ {r['max_seconds']} s của {r['watchlist_channels']} kênh watchlist + kênh mình, đăng ≤ {r['days']} ngày: "
           f"{r['candidates']} ứng viên → {r['confirmed']} Short xác nhận (youtube.com/shorts/<id> trả 200), "
           f"{r['unconfirmed']} chưa xác nhận (`?`, chỉ theo độ dài), {r['not_shorts']} là video thường. "
           f"Xếp theo view/ngày từ lúc đăng; tối đa {r['per_channel'] or '∞'} Short / kênh.", "",
           f"Contact sheet (ảnh dọc, cùng thứ tự): `{r['sheet']}`", "",
           f"## Top {len(r['top'])} Short trong ngách", "",
           "| # | Short | kênh | view/ngày | vel | view | like | cmt | dài | tuổi |", "|---|---|---|---|---|---|---|---|---|---|"]
    out += [f"| {t['rank']} | {link(t)}{mark(t)} | {cell(t['channel'])} | {fmt(round(t['vpd']))} | {fmt(t['vel'])} | {t['views']:,} | "
            f"{t['likes']:,} | {t['comments']:,} | {fmt_dur(t['dur_s'])} | {round(t['age_d'])} d |" for t in r["top"]]
    for title, key, note in (("Loại Short (theo title, `shorts.formats`)", "formats", "bổ sung bằng mắt trên sheet: lyric card / mặt ca sĩ / cảnh / chữ lớn"),
                             ("Chủ đề trên Shorts (`topics`)", "topics", "cùng từ vựng với video dài")):
        rows = r.get(key) or {}
        out += ["", f"## {title}", "", f"hit = view/ngày ≥ 3 × trung vị Short của chính kênh đó; {note}.", "",
                "| | Short | kênh | median vpd | % vpd | hit (rate) | recent | mạnh nhất |", "|---|---|---|---|---|---|---|---|"]
        out += [f"| {n} | {g['shorts']} | {g['channels']} | {fmt(g['median_vpd'])} | {g['share_vpd']} | {g['hits']} ({g['hit_rate']}%) | "
                f"{g['recent_hits']} | {link(g['best'])} ({cell(g['best']['channel'])}, {fmt(round(g['best']['vpd']))}/d) |"
                for n, g in rows.items()] or ["| — | | | | | | | |"]
    out += ["", "## Kênh làm Shorts", "",
            "`/tuần` tính trên min(cửa sổ, khoảng thời gian 50 upload gần nhất của kênh phủ được). "
            "`vpd long` = trung vị view/ngày video thường của kênh trong cùng cửa sổ.", "",
            "| kênh | sub | Short | /tuần | median vpd Short | median vpd long (n) | Σ vpd Short |", "|---|---|---|---|---|---|---|"]
    out += [f"| {cell(c['channel'])} | {fmt(c['subs'])} | {c['shorts']} | {c['shorts_per_week']} | {fmt(c['median_vpd_shorts'])} | "
            f"{fmt(c['median_vpd_long'])} ({c['long_videos']}) | {c['vpd_sum_shorts']:,} |" for c in r["channels"]]
    o = r["own"]
    out += ["", f"## Kênh mình: {len(o['shorts'])} Short · median vpd video thường {fmt(o['median_vpd_long'])}", ""]
    if o["shorts"]:
        out += ["| Short | đăng | view/ngày | vel | view | like | cmt | dài |", "|---|---|---|---|---|---|---|---|"]
        out += [f"| {link(t)}{mark(t)} | {t['published'][:10]} | {fmt(round(t['vpd']))} | {fmt(t['vel'])} | {t['views']:,} | "
                f"{t['likes']:,} | {t['comments']:,} | {fmt_dur(t['dur_s'])} |" for t in o["shorts"]]
    else:
        out.append("Chưa có Short nào trong cửa sổ.")
    return "\n".join(out) + "\n"


def vertical_frame(vid: str):
    from io import BytesIO
    from PIL import Image
    for q in ("oar2", "hqdefault"):
        try:
            img = Image.open(BytesIO(urllib.request.urlopen(f"https://i.ytimg.com/vi/{vid}/{q}.jpg", timeout=20).read())).convert("RGB")
        except Exception:
            continue
        w, h = img.size
        if w * 16 > h * 9:
            cw = h * 9 // 16
            img = img.crop(((w - cw) // 2, 0, (w - cw) // 2 + cw, h))
        else:
            ch = w * 16 // 9
            img = img.crop((0, (h - ch) // 2, w, (h - ch) // 2 + ch))
        return img, q
    return None, None


def shorts_sheet(top, out: Path):
    from PIL import Image, ImageDraw, ImageFont
    W, H, COLS, TOP, BOTTOM = 270, 480, 5, 28, 22
    try:
        font, small = ImageFont.load_default(size=20), ImageFont.load_default(size=14)
    except TypeError:
        font = small = ImageFont.load_default()
    tiles = []
    for rank, r in enumerate(top, 1):
        img, q = vertical_frame(r["id"])
        if img is None:
            print("skip", r["id"])
            continue
        tile = Image.new("RGB", (W, TOP + H + BOTTOM), (0, 0, 0))
        tile.paste(img.resize((W, H)), (0, TOP))
        dr = ImageDraw.Draw(tile)
        label = f"#{rank} {fmt(round(r['vpd']))}/d {fmt_dur(r['dur_s'])}"
        label += "" if r["short"] == "yes" else " ?"
        label += "" if q == "oar2" else " (hq)"
        dr.text((6, 4), label, fill=(255, 230, 0), font=font)
        dr.text((6, TOP + H + 3), (r["channel"] or "")[:32], fill=(230, 230, 230), font=small)
        tiles.append(tile)
    if not tiles:
        return None
    cols = min(COLS, len(tiles))
    th = TOP + H + BOTTOM
    sheet = Image.new("RGB", (W * cols, th * ((len(tiles) + cols - 1) // cols)), (25, 25, 25))
    for k, im in enumerate(tiles):
        sheet.paste(im, ((k % cols) * W, (k // cols) * th))
    sheet.save(out, quality=88)
    return out


THUMB_FIELDS = {
    "subject": "person_close | person_half | person_full | group | hands | objects | scene | text_only",
    "setting": "church | home_inside | porch_yard | nature | road | studio_stage | night_sky | abstract",
    "text_words": "number of words on the image",
    "text_style": "gold_3d_serif | clean_serif | sans_bold | handwritten | tracklist | none",
    "text_role": "same_as_title | plea | promise_benefit | nostalgia | song_list | none",
    "palette": "warm_gold | sepia | green | blue_night | bright_day | black_white | mixed",
    "props": "list: mic, guitar, cross, bible, hymnal, lamp, candle, window, dog, family_photo, spectrum_bars, duration_bar, lyrics_badge…",
    "mood": "two or three words",
}


def cmd_thumbs(a, cfg, d: Path):
    out = d / "thumbs"
    out.mkdir(exist_ok=True)
    date = now_utc().date().isoformat()
    labels = out / f"{date}.yaml"
    if a.summarize:
        return thumbs_summary(a, out)
    wl = read_json(d / "watchlist.json", {})
    rows = [r for r in latest_rows(d, cfg) if in_window(r, cfg) and not r["own"] and r["ch"] in wl]
    groups = cfg.get("branches") or {}
    if a.topic:
        groups = {k: v for k, v in {**(cfg.get("topics") or {}), **groups}.items() if k in a.topic}
    per = a.n or 6
    entries, rank, taken = [], 0, set()
    for name, words in groups.items():
        m = matcher(words)
        g = sorted([r for r in rows if m(r["title"]) and r["age_d"] <= 30 and (r["x"] or 0) >= a.min_x],
                   key=lambda r: -r["vpd"])
        seen, picked = set(), []
        for r in g:
            if r["ch"] in seen or r["id"] in taken:
                continue
            seen.add(r["ch"])
            picked.append(r)
            if len(picked) >= per:
                break
        low = sorted([r for r in rows if m(r["title"]) and r["age_d"] <= 30 and r["ch"] in seen and (r["x"] or 0) < 0.5
                      and r["id"] not in taken], key=lambda r: r["vpd"])[:2]
        taken.update(r["id"] for r in picked + low)
        if not picked:
            continue
        ids = []
        for r in picked + low:
            rank += 1
            ids.append(r["id"])
            entries.append({"n": rank, "id": r["id"], "group": name, "role": "hit" if r in picked else "flop",
                            "channel": r["channel"], "title": r["title"], "vpd": round(r["vpd"]), "x": r["x"],
                            "age_d": round(r["age_d"]), **{k: None for k in THUMB_FIELDS}})
        a.video, a.name = ids, f"thumbs-{name}"
        cmd_sheet(a, cfg, d)
    if labels.exists() and not a.force:
        sys.exit(f"{labels.relative_to(ROOT)} exists (labelled?): --force to rebuild")
    with open(labels, "w") as f:
        f.write("# Nhãn thumbnail (Claude điền bằng mắt trên sheets/<date>-thumbs-<group>.jpg, cùng thứ tự n).\n"
                "# Giá trị cho phép:\n" + "".join(f"#   {k}: {v}\n" for k, v in THUMB_FIELDS.items())
                + "# Xong: trend.py thumbs --summarize\n")
        yaml.safe_dump({"date": date, "videos": entries}, f, sort_keys=False, allow_unicode=True, width=140)
    print(f"{len(entries)} thumbnails in {len(groups)} groups → label {labels.relative_to(ROOT)}")


def thumbs_summary(a, out: Path):
    files = sorted(out.glob("*.yaml"))
    if not files:
        sys.exit("no labels: run thumbs first")
    data = yaml.safe_load(files[-1].read_text()) or {}
    vids = [v for v in data.get("videos") or [] if v.get("subject")]
    if not vids:
        sys.exit(f"{files[-1].name} has no labels yet")
    lines = [f"# Thumbnail patterns {data.get('date')}", "",
             f"{len(vids)} thumbnail đã gắn nhãn (hit = x ≥ {a.min_x} trong 30 ngày, flop = x < 0.5 cùng kênh). "
             "`hit share` = tỉ lệ video mang giá trị đó trong nhóm hit; giá trị có ở cả hit lẫn flop là **điều kiện vào sân / bão hòa**, "
             "không phải lý do thắng.", ""]
    hits = [v for v in vids if v["role"] == "hit"]
    flops = [v for v in vids if v["role"] == "flop"]
    for field in THUMB_FIELDS:
        if field in ("mood", "text_words"):
            continue
        vals = {}
        for v in vids:
            xs = v.get(field)
            for x in (xs if isinstance(xs, list) else [xs]):
                if x is not None:
                    vals.setdefault(str(x), []).append(v)
        lines += [f"## {field}", "", "| giá trị | hit share | flop share | median vpd (hit) | nhóm |", "|---|---|---|---|---|"]
        for val, vs in sorted(vals.items(), key=lambda kv: -len([v for v in kv[1] if v["role"] == "hit"])):
            h = [v for v in vs if v["role"] == "hit"]
            fl = [v for v in vs if v["role"] == "flop"]
            lines.append(f"| {val} | {round(100 * len(h) / max(len(hits), 1))}% | {round(100 * len(fl) / max(len(flops), 1))}% | "
                         f"{fmt(round(statistics.median(x['vpd'] for x in h))) if h else '–'} | {', '.join(sorted({x['group'] for x in vs}))} |")
        lines.append("")
    tw = [v["text_words"] for v in hits if isinstance(v.get("text_words"), int)]
    if tw:
        lines += [f"Chữ trên ảnh (hit): trung vị {statistics.median(tw):g} từ, {min(tw)}–{max(tw)}.", ""]
    md = out / f"{data.get('date')}.md"
    md.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(md.relative_to(ROOT))


def main():
    ap = argparse.ArgumentParser(description="R&D trend research on YouTube (Data API v3, API key)")
    ap.add_argument("cmd", choices=["discover", "pulse", "prune", "topics", "refs", "comments", "sheet", "shorts", "thumbs"])
    ap.add_argument("--channel", required=True, help="channel dir name under channel/")
    ap.add_argument("--max-queries", type=int, help="discover: use only the first N queries (100 units each)")
    ap.add_argument("--no-search", action="store_true", help="discover: no search, only --import-json / seed_channels")
    ap.add_argument("--shorts", action="store_true", help="discover: search Shorts (shorts.discover_queries) and admit Shorts-first channels (shorts.niche_keywords)")
    ap.add_argument("--import-json", nargs="*", help="discover: JSON files with channel_id fields as candidates")
    ap.add_argument("--topic", nargs="*", help="refs: topic and/or branch names (all must match the title)")
    ap.add_argument("--n", type=int, default=5, help="refs: videos to pick; comments: comments per video")
    ap.add_argument("--min-x", type=float, default=2.0, help="refs: minimum outlier factor")
    ap.add_argument("--max-minutes", type=float, default=150, help="refs: longest video (analyzer time)")
    ap.add_argument("--video", nargs="*", default=[], help="comments / sheet: video ids (also comma-separated; an id starting with '-' as --video=ID,ID)")
    ap.add_argument("--show", type=int, default=15, help="comments: how many to print")
    ap.add_argument("--name", default="sheet", help="sheet: file name part")
    ap.add_argument("--days", type=int, help="shorts: window in days (default shorts.days, else window_days)")
    ap.add_argument("--top", type=int, help="shorts: rows in the table and tiles in the sheet (default shorts.top or 20)")
    ap.add_argument("--per-channel", type=int, help="shorts: max Shorts per channel in the top (default shorts.per_channel or 3; 0 = no cap)")
    ap.add_argument("--summarize", action="store_true", help="thumbs: turn the latest labelled thumbs/<date>.yaml into the pattern table")
    ap.add_argument("--force", action="store_true", help="thumbs: rebuild today's label file")
    ap.add_argument("--fetch", action="store_true", help="shorts: run pulse first even if the latest snapshot is fresh")
    a = ap.parse_args()
    a.video = [v for x in a.video for v in x.split(",") if v]
    cfg = load_config(a.channel)
    d = data_dir(a.channel)
    {"discover": cmd_discover, "pulse": cmd_pulse, "prune": cmd_prune, "topics": cmd_topics, "refs": cmd_refs,
     "comments": cmd_comments, "sheet": cmd_sheet, "shorts": cmd_shorts, "thumbs": cmd_thumbs}[a.cmd](a, cfg, d)


if __name__ == "__main__":
    main()

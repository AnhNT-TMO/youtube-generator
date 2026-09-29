#!/usr/bin/env python3
import argparse
import atexit
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
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "research" / "yt"
API = "https://www.googleapis.com/youtube/v3/"
KEY_FILE = Path("~/.config/yt-research/api_key").expanduser()
BANK_DIR = ROOT / "research" / "phrase-bank"
COST = {"search": 100}
DAY_CAP = 9000
SHORT_MAX_S = 180
MIN_BASE = 5
FRESH_DAYS = 30
KIND_PLAYLIST = {"long": "UULF", "short": "UUSH"}
CHANNEL_ID = re.compile(r"UC[\w-]{22}")
VIDEO_ID = re.compile(r"(?:v=|youtu\.be/|shorts/|embed/|live/)([\w-]{11})")
SORT = {"vpd": lambda r: -r["vpd"], "x": lambda r: -(r["vpd_x"] or 0), "views": lambda r: -r["views"],
        "date": lambda r: r["age_days"]}


class ApiError(Exception):
    pass


def pacific_day():
    return datetime.now(ZoneInfo("America/Los_Angeles")).date().isoformat()


def units_today():
    log, day = OUT / "units.log", pacific_day()
    rows = (line.split("\t") for line in (log.read_text().splitlines() if log.exists() else []))
    return sum(int(p[3]) for p in rows if len(p) > 3 and p[0] == day and p[3].isdigit())


class Api:
    def __init__(self, cmd):
        self.key = os.environ.get("YT_API_KEY") or (KEY_FILE.read_text().strip() if KEY_FILE.exists() else "")
        if not self.key:
            sys.exit(f"no API key: put it in {KEY_FILE} (chmod 600) or set YT_API_KEY")
        self.cmd, self.units, self.before = cmd, 0, units_today()
        atexit.register(self.log)

    def get(self, endpoint, **params):
        cost = COST.get(endpoint, 1)
        if self.before + self.units + cost > DAY_CAP:
            sys.exit(f"stop: {self.before + self.units} units logged today (Pacific) + {cost} would pass {DAY_CAP}; "
                     "the key is shared, wait for midnight Pacific")
        self.units += cost
        url = API + endpoint + "?" + urllib.parse.urlencode({**params, "key": self.key})
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            if "quotaExceeded" in body:
                sys.exit("YouTube API quota exceeded for today (resets at midnight Pacific)")
            try:
                msg = json.loads(body)["error"]["message"]
            except (ValueError, KeyError):
                msg = body[:200]
            raise ApiError(f"{endpoint} HTTP {e.code}: {msg}")

    def log(self):
        if not self.units:
            return
        OUT.mkdir(parents=True, exist_ok=True)
        day = pacific_day()
        with open(OUT / "units.log", "a") as f:
            f.write(f"{day}\t{datetime.now().isoformat(timespec='seconds')}\t{self.cmd}\t{self.units}\n")
        print(f"units: {self.units} this run, {self.before + self.units} / 10000 today (Pacific {day})", file=sys.stderr)


def now():
    return datetime.now(timezone.utc)


def parse_ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def iso_seconds(d):
    m = re.fullmatch(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?", d or "")
    dd, h, mi, s = (int(x or 0) for x in m.groups()) if m else (0, 0, 0, 0)
    return dd * 86400 + h * 3600 + mi * 60 + s


def hms(s):
    h, m = divmod(s // 60, 60)
    return f"{h}:{m:02d}:{s % 60:02d}" if h else f"{m}:{s % 60:02d}"


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "x"


def rel(p):
    p = Path(p).resolve()
    return str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)


def save(path, obj):
    p = OUT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, ensure_ascii=False))
    return p


def chunks(items, n=50):
    items = list(items)
    return [items[i:i + n] for i in range(0, len(items), n)]


def video_ids(refs):
    return list(dict.fromkeys(m.group(1) if (m := VIDEO_ID.search(r)) else r.strip() for r in refs))


def channel_ids(api, refs):
    ids = []
    for r in refs:
        if m := CHANNEL_ID.search(r):
            ids.append(m.group())
        elif items := api.get("channels", part="id", forHandle="@" + r.split("@")[-1].strip("/").split("/")[0]).get("items"):
            ids.append(items[0]["id"])
        else:
            print(f"no channel for {r}", file=sys.stderr)
    return list(dict.fromkeys(ids))


def fetch_channels(api, ids):
    out = {}
    for batch in chunks(ids):
        for c in api.get("channels", part="snippet,statistics,contentDetails", id=",".join(batch)).get("items", []):
            s, st = c["snippet"], c["statistics"]
            out[c["id"]] = {"id": c["id"], "title": s["title"], "handle": s.get("customUrl"),
                            "created": s["publishedAt"][:10], "age_days": (now() - parse_ts(s["publishedAt"])).days,
                            "subs": None if st.get("hiddenSubscriberCount") else int(st.get("subscriberCount", 0)),
                            "views": int(st.get("viewCount", 0)), "videos": int(st.get("videoCount", 0)),
                            "country": s.get("country"), "uploads": c["contentDetails"]["relatedPlaylists"]["uploads"],
                            "description": s.get("description", "")}
    return out


def uploads(api, playlist, n, quiet=False):
    ids, page = [], {}
    while len(ids) < n:
        try:
            res = api.get("playlistItems", part="contentDetails", playlistId=playlist, maxResults=min(50, n - len(ids)), **page)
        except ApiError as e:
            if not quiet:
                print(e, file=sys.stderr)
            break
        ids += [i["contentDetails"]["videoId"] for i in res.get("items", [])]
        if not res.get("nextPageToken"):
            break
        page = {"pageToken": res["nextPageToken"]}
    return ids


def fetch_videos(api, ids, full=False):
    rows, t = [], now()
    for batch in chunks(ids):
        for v in api.get("videos", part="snippet,statistics,contentDetails", id=",".join(batch)).get("items", []):
            s, st = v["snippet"], v.get("statistics", {})
            dur = iso_seconds(v["contentDetails"].get("duration"))
            age = (t - parse_ts(s["publishedAt"])).total_seconds() / 86400
            views = int(st.get("viewCount", 0))
            live = s.get("liveBroadcastContent", "none") != "none"
            rows.append({"id": v["id"], "url": f"https://www.youtube.com/watch?v={v['id']}", "channel": s["channelTitle"],
                         "channel_id": s["channelId"], "title": s["title"], "published": s["publishedAt"],
                         "age_days": round(age, 1), "duration_s": dur,
                         "kind": "live" if live else "short" if 0 < dur <= SHORT_MAX_S else "long",
                         "views": views, "likes": int(st.get("likeCount", 0)), "comments": int(st.get("commentCount", 0)),
                         "vpd": round(views / max(age, 1), 1), "vpd_x": None, "tags": s.get("tags", []),
                         "description": (s.get("description") or "")[: None if full else 300]})
    return rows


def add_x(rows):
    base = {}
    for r in rows:
        if r["kind"] != "live":
            base.setdefault(r["kind"], []).append(r["vpd"])
    med = {k: statistics.median(v) for k, v in base.items() if len(v) >= MIN_BASE}
    for r in rows:
        r["vpd_x"] = round(r["vpd"] / med[r["kind"]], 2) if med.get(r["kind"]) else None
    return med


def collect(api, refs, n, kind="all"):
    chans = fetch_channels(api, channel_ids(api, refs))
    taken, rows = now().isoformat(timespec="seconds"), []
    for c in chans.values():
        ids = uploads(api, KIND_PLAYLIST[kind] + c["uploads"][2:], n, quiet=True) if kind in KIND_PLAYLIST else []
        if kind in KIND_PLAYLIST and not ids:
            print(f"{c['title']}: no {KIND_PLAYLIST[kind]} playlist, scanning all uploads (kind by duration)", file=sys.stderr)
        vids = fetch_videos(api, ids or uploads(api, c["uploads"], n))
        if ids:
            for r in vids:
                r["kind"] = "live" if r["kind"] == "live" else kind
        c["median_vpd"] = {k: round(m, 1) for k, m in add_x(vids).items()}
        c["scanned"] = len(vids)
        name = now().date().isoformat() + ("" if kind == "all" else f"-{kind}")
        p = save(f"videos/{c['id']}/{name}.json", {"taken_at": taken, "channel": c, "videos": vids})
        print(f"saved: {rel(p)}", file=sys.stderr)
        rows += vids
    return chans, rows


def emit(a, result, path, show):
    if a.json:
        print(json.dumps(result, indent=1, ensure_ascii=False))
    else:
        show()
    if path:
        print(f"saved: {rel(path)}", file=sys.stderr if a.json else sys.stdout)


def show_channels(chans, detail=False):
    for c in chans:
        subs = "hidden" if c["subs"] is None else f"{c['subs']:,}"
        med = " | median vpd " + ", ".join(f"{k} {v:,.0f}" for k, v in c["median_vpd"].items()) if c.get("median_vpd") else ""
        found = f" | {c['results']} result(s), best {c['best_vpd']:,.0f}/d" if "results" in c else ""
        print(f"{c['title'][:36]:<36} {c['id']} {c.get('handle') or ''} | {subs} subs | {c['videos']} videos | "
              f"created {c['created']} ({c['age_days']} d){med}{found}")
        if detail:
            print(f"  views {c['views']:,} | country {c['country'] or '-'} | uploads playlist {c['uploads']}")
            print("  " + c["description"][:400].replace("\n", " "))


def show_videos(rows, with_channel=True):
    for i, r in enumerate(rows, 1):
        x = "x-" if r["vpd_x"] is None else f"x{r['vpd_x']}"
        ch = f" | {r['channel'][:24]}" if with_channel else ""
        print(f"{i:>3}. {r['published'][:10]} {r['age_days']:>6.1f}d {hms(r['duration_s']):>8} {r['kind']:<5} "
              f"{r['views']:>10,}v {r['vpd']:>9,.0f}/d {x:>7}{ch} | {r['title'][:80]} [{r['id']}]")


def cmd_search(a):
    api = Api("search")
    p = {"q": a.query, "type": "video", "order": a.order, "maxResults": 50, "relevanceLanguage": a.lang}
    if a.days:
        p["publishedAfter"] = (now() - timedelta(days=a.days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    if a.duration != "any":
        p["videoDuration"] = a.duration
    items = api.get("search", part="snippet", **p).get("items", [])
    videos = sorted(fetch_videos(api, [i["id"]["videoId"] for i in items]), key=SORT["vpd"])
    chans = fetch_channels(api, {v["channel_id"] for v in videos})
    for c in chans.values():
        mine = [v["vpd"] for v in videos if v["channel_id"] == c["id"]]
        c.update(results=len(mine), best_vpd=max(mine))
    chans = sorted(chans.values(), key=lambda c: -c["best_vpd"])
    result = {"taken_at": now().isoformat(timespec="seconds"), "params": p, "videos": videos, "channels": chans}
    path = save(f"search/{now().date()}-{slug(a.query)}.json", result)
    emit(a, result, path, lambda: (show_videos(videos), print(), show_channels(chans)))


def cmd_channel(a):
    api = Api("channel")
    chans = list(fetch_channels(api, channel_ids(api, a.refs)).values())
    for c in chans:
        save(f"channels/{c['id']}.json", c)
    emit(a, chans, None, lambda: show_channels(chans, detail=True))


def cmd_videos(a):
    chans, rows = collect(Api("videos"), a.refs, a.n, a.kind)
    rows = sorted((r for r in rows if a.kind in ("all", r["kind"])), key=SORT[a.sort])[: a.top]
    emit(a, {"channels": list(chans.values()), "videos": rows}, None,
         lambda: (show_channels(chans.values()), show_videos(rows, len(chans) > 1)))


def cmd_fast(a):
    refs = list(a.refs) + [c for f in a.file or [] for c in CHANNEL_ID.findall(Path(f).read_text())]
    if not refs:
        sys.exit("give channels (UC… ids, @handles, URLs) or --file with channel ids in it")
    chans, rows = collect(Api("fast"), list(dict.fromkeys(refs)), a.n, a.kind)
    pick = sorted((r for r in rows if r["kind"] != "live" and a.kind in ("all", r["kind"]) and r["age_days"] <= a.days
                   and (r["vpd_x"] or 0) >= a.min_x), key=SORT[a.sort])
    per, out = {}, []
    for r in pick:
        per[r["channel_id"]] = per.get(r["channel_id"], 0) + 1
        if per[r["channel_id"]] <= a.per_channel and len(out) < a.top:
            out.append(r)
    params = {k: getattr(a, k) for k in ("days", "kind", "min_x", "sort", "per_channel", "top", "n")}
    result = {"taken_at": now().isoformat(timespec="seconds"), "params": params,
              "channels": [{k: v for k, v in c.items() if k != "description"} for c in chans.values()], "videos": out}
    path = save(f"fast/{now().date()}-{slug(a.name)}.json", result)
    emit(a, result, path, lambda: (print(f"{len(out)} of {len(rows)} uploads from {len(chans)} channels (≤ {a.days:g} d, "
                                         f"{a.kind}, x ≥ {a.min_x:g}, ≤ {a.per_channel}/channel)"), show_videos(out)))


def cmd_video(a):
    rows = fetch_videos(Api("video"), video_ids(a.ids), full=True)
    for r in rows:
        save(f"video/{r['id']}.json", r)

    def show():
        for r in rows:
            print(f"{r['title']}\n  {r['url']} | {r['channel']} ({r['channel_id']})")
            print(f"  published {r['published'][:10]} ({r['age_days']} d) | {hms(r['duration_s'])} {r['kind']} | "
                  f"{r['views']:,} views, {r['likes']:,} likes, {r['comments']:,} comments | {r['vpd']:,.0f}/d")
            print(f"  thumbnail https://i.ytimg.com/vi/{r['id']}/maxresdefault.jpg")
            print("  tags: " + (", ".join(r["tags"]) or "-"))
            print("  " + "\n  ".join(r["description"].splitlines()[:20]))
    emit(a, rows, None, show)


def cmd_comments(a):
    api, out = Api("comments"), {}
    for vid in video_ids(a.ids):
        try:
            res = api.get("commentThreads", part="snippet", videoId=vid, order="relevance", maxResults=100, textFormat="plainText")
        except ApiError as e:
            print(f"{vid}: {e}", file=sys.stderr)
            continue
        out[vid] = [{"likes": c["likeCount"], "replies": it["snippet"]["totalReplyCount"], "published": c["publishedAt"][:10],
                     "text": c["textDisplay"]} for it in res.get("items", []) for c in [it["snippet"]["topLevelComment"]["snippet"]]]
        save(f"comments/{vid}.json", out[vid])

    def show():
        for vid, rows in out.items():
            print(f"== {vid}: {len(rows)} comments (research/yt/comments/{vid}.json)")
            for c in rows[: a.show]:
                print(f"  [{c['likes']} likes, {c['replies']} replies] {c['text'][:240].replace(chr(10), ' ')}")
    emit(a, out, None, show)


def load_rows(path):
    text = Path(path).read_text()
    data = json.loads(text) if str(path).endswith(".json") else yaml.safe_load(text)
    return (data.get("videos") or entries_of(data)) if isinstance(data, dict) else data or []


def thumb(vid, size):
    from PIL import Image, ImageOps
    vertical = size[1] > size[0]
    cache = OUT / "thumbs" / f"{vid}{'-v' if vertical else ''}.jpg"
    if not cache.exists():
        for q in ("oar2", "hqdefault") if vertical else ("maxresdefault", "sddefault", "hqdefault"):
            try:
                data = urllib.request.urlopen(f"https://i.ytimg.com/vi/{vid}/{q}.jpg", timeout=20).read()
            except (urllib.error.URLError, TimeoutError):
                continue
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(data)
            break
        else:
            return None
    return ImageOps.fit(Image.open(cache).convert("RGB"), size, Image.LANCZOS)


def cmd_sheet(a):
    from PIL import Image, ImageDraw, ImageFont
    info = {r["id"]: r for r in load_rows(a.from_)} if a.from_ else {}
    ids = video_ids(a.ids) or list(info)[: a.top]
    if not ids:
        sys.exit("give video ids (after -- when one starts with '-') or --from <json/yaml with videos>")
    (W, H), BAR, cols = ((360, 640), 28, 4) if a.vertical else ((640, 360), 28, 2)
    font = ImageFont.load_default(size=18)
    tiles, legend = [], []
    for i, vid in enumerate(ids, 1):
        img = thumb(vid, (W, H))
        if img is None:
            print(f"no thumbnail: {vid}", file=sys.stderr)
            continue
        r = info.get(vid, {})
        label = f"#{i} {vid}" + (f"  {r['vpd']:,.0f}/d  x{r.get('vpd_x') or '-'}" if r.get("vpd") is not None else "")
        tile = Image.new("RGB", (W, H + BAR), (0, 0, 0))
        tile.paste(img, (0, BAR))
        ImageDraw.Draw(tile).text((6, 4), label, fill=(255, 220, 0), font=font)
        tiles.append(tile)
        legend.append(" | ".join(x for x in (f"#{i} {vid}", r.get("channel"), r.get("title")) if x))
    if not tiles:
        sys.exit("no thumbnails downloaded")
    cols = min(cols, len(tiles))
    sheet = Image.new("RGB", (W * cols, (H + BAR) * -(-len(tiles) // cols)), (30, 30, 30))
    for k, t in enumerate(tiles):
        sheet.paste(t, ((k % cols) * W, (k // cols) * (H + BAR)))
    path = OUT / "sheets" / f"{now().date()}-{slug(a.name)}.jpg"
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path, quality=90)
    print("\n".join(legend))
    print(f"saved: {rel(path)} (full-size originals: research/yt/thumbs/<id>.jpg)")


def entries_of(doc):
    if not isinstance(doc.get("entries", []), list):
        sys.exit("the bank's top-level `entries` must be a list")
    return doc.setdefault("entries", [])


def load_bank(a):
    banks = [Path(a.bank)] if a.bank else sorted(BANK_DIR.glob("*.yaml"))
    if len(banks) != 1:
        sys.exit(f"{len(banks)} bank files in {rel(BANK_DIR)}: pass --bank <file.yaml> or set YT_PHRASE_BANK")
    text = banks[0].read_text() if banks[0].exists() else ""
    doc = (yaml.safe_load(text) if text.strip() else None) or {}
    if not isinstance(doc, dict):
        sys.exit(f"{rel(banks[0])}: top level must be a mapping (updated, source_note, channels, entries)")
    return banks[0], doc, entries_of(doc), re.match(r"(?:#[^\n]*\n)*", text).group()


def save_bank(path, doc, head):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(head + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=1000))


def bank_entry(r, text_as_list):
    return {"id": r["id"], "url": r.get("url") or f"https://www.youtube.com/watch?v={r['id']}", "channel": r["channel"],
            "channel_id": r["channel_id"], "published": r["published"][:10], "age_days": round(r["age_days"]),
            "views": r["views"], "vpd": round(r["vpd"]), "vpd_x": r["vpd_x"], "duration_min": round(r["duration_s"] / 60, 1),
            "title": r["title"], "thumb_text": [] if text_as_list else "", "addressee": "", "theme": [], "pattern": "",
            "fresh": r["age_days"] <= FRESH_DAYS, "branch": "", "used_by": []}


def flat(v):
    return " / ".join(map(str, v)) if isinstance(v, list) else str(v or "").replace("\n", " / ")


def show_bank(rows, total, path):
    print(f"{len(rows)} of {total} entries in {rel(path)}")
    for e in rows:
        print(f"{e.get('id')} x{e.get('vpd_x') or '-'} {e.get('vpd') or '-'}/d | {e.get('addressee') or '-'} | {flat(e.get('theme')) or '-'} | "
              f"{e.get('pattern') or '-'} | used {len(e.get('used_by') or [])} | {flat(e.get('thumb_text')) or '(thumb_text empty)'}"
              f" | {str(e.get('title', ''))[:70]}")


def cmd_bank(a):
    path, doc, entries, head = load_bank(a)
    if a.action == "list":
        rows = [e for e in entries if not (a.unused and e.get("used_by")) and not (a.todo and e.get("thumb_text"))
                and (not a.theme or a.theme.lower() in flat(e.get("theme")).lower())]
        rows.sort(key=lambda e: -(e.get("vpd_x") or 0))
        return emit(a, rows, None, lambda: show_bank(rows, len(entries), path))
    if a.action == "use":
        e = next((e for e in entries if e.get("id") == a.id), None)
        if e is None:
            sys.exit(f"{a.id} is not in {rel(path)}")
        by, used = rel(a.by).rstrip("/"), list(e.get("used_by") or [])
        if by not in used:
            used.append(by)
        e["used_by"] = used
        save_bank(path, doc, head)
        return print(f"{a.id}: used_by {e['used_by']}")
    have, want = {e.get("id") for e in entries}, set(video_ids(a.ids))
    text_as_list = any(isinstance(e.get("thumb_text"), list) for e in entries)
    cand = [r for r in load_rows(a.from_) if not want or r["id"] in want]
    new = [r for r in cand if r["id"] not in have][: a.top]
    entries += [bank_entry(r, text_as_list) for r in new]
    save_bank(path, doc, head)
    print(f"added {len(new)}, skipped {len(cand) - len(new)} (already in the bank or over --top) → {rel(path)}")
    if new:
        print("next: read their thumbnails, then fill thumb_text, addressee, theme, pattern in the bank:")
        print(f"  yt.py sheet --from {rel(a.from_)} --name bank -- {' '.join(r['id'] for r in new)}")


def main():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="print the result as JSON (data files are saved anyway)")
    refs = {"help": "UC… channel id, @handle or channel URL"}
    ids = {"help": "video ids or URLs (put them after -- when one starts with '-')"}
    ap = argparse.ArgumentParser(description="YouTube Data API v3 for R&D (data: research/yt/, units: research/yt/units.log)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, text):
        return sub.add_parser(name, parents=[common], help=text)

    def scan(name, text, nargs):
        p = add(name, text)
        p.add_argument("refs", nargs=nargs, **refs)
        p.add_argument("--n", type=int, default=50, help="uploads to scan per channel, newest first (the median base)")
        p.add_argument("--sort", choices=list(SORT), default="vpd")
        return p
    p = add("search", "search.list for videos (100 units) + their details and channels (~2 units)")
    p.add_argument("query")
    p.add_argument("--order", choices=["viewCount", "date", "relevance"], default="viewCount")
    p.add_argument("--days", type=int, default=30, help="published in the last N days (0 = any time)")
    p.add_argument("--duration", choices=["any", "short", "medium", "long"], default="any",
                   help="search's own filter: short < 4 min, medium 4-20, long > 20")
    p.add_argument("--lang", default="en", help="relevanceLanguage")
    p = add("channel", "channel overview (1 unit per 50 channels, +1 per @handle)")
    p.add_argument("refs", nargs="+", **refs)
    p = scan("videos", "a channel's last uploads ranked by views/day (~2 units per channel per 50 uploads)", "+")
    p.add_argument("--kind", choices=["all", "long", "short", "live"], default="all")
    p.add_argument("--top", type=int, default=50)
    p = scan("fast", "fast-growing recent videos across channels (~2 units per channel)", "*")
    p.add_argument("--file", action="append", help="text/JSON file: every UC… channel id in it is used (repeatable)")
    p.add_argument("--days", type=float, default=30, help="only videos uploaded in the last N days")
    p.add_argument("--kind", choices=["all", "long", "short"], default="long")
    p.add_argument("--min-x", type=float, default=2.0, help="vpd ÷ the channel's median vpd (same kind) at least this")
    p.add_argument("--per-channel", type=int, default=3)
    p.add_argument("--top", type=int, default=30)
    p.add_argument("--name", default="fast", help="research/yt/fast/<date>-<name>.json")
    p = add("video", "details of videos (1 unit per 50)")
    p.add_argument("ids", nargs="+", **ids)
    p = add("comments", "top comments by relevance (1 unit per video)")
    p.add_argument("ids", nargs="+", **ids)
    p.add_argument("--show", type=int, default=20)
    p = add("sheet", "thumbnail contact sheet from i.ytimg.com (0 units)")
    p.add_argument("ids", nargs="*", **ids)
    p.add_argument("--from", dest="from_", help="fast/search/videos JSON or the bank YAML: labels, and ids when none given")
    p.add_argument("--top", type=int, default=6, help="with --from and no ids: the first N videos")
    p.add_argument("--name", default="sheet")
    p.add_argument("--vertical", action="store_true", help="Shorts: 9:16 frames (oar2.jpg)")
    bank = argparse.ArgumentParser(add_help=False, parents=[common])
    bank.add_argument("--bank", default=os.environ.get("YT_PHRASE_BANK"),
                      help="bank YAML (default: YT_PHRASE_BANK, else the only *.yaml in research/phrase-bank/)")
    bs = sub.add_parser("bank", help="phrase bank research/phrase-bank/: list / use / add").add_subparsers(dest="action", required=True)
    q = bs.add_parser("list", parents=[bank], help="entries, best vpd_x first")
    q.add_argument("--unused", action="store_true", help="used_by empty")
    q.add_argument("--todo", action="store_true", help="thumb_text still empty")
    q.add_argument("--theme")
    q = bs.add_parser("use", parents=[bank], help="record that an album used this entry")
    q.add_argument("id")
    q.add_argument("--by", required=True, help="album dir, e.g. channel/<ch>/albums/NNN-slug")
    q = bs.add_parser("add", parents=[bank], help="add the videos of a fast JSON that are not in the bank yet")
    q.add_argument("--from", dest="from_", required=True, help="research/yt/fast/<date>-<name>.json (or a search/videos JSON)")
    q.add_argument("ids", nargs="*", help="only these video ids (after -- when one starts with '-')")
    q.add_argument("--top", type=int, help="at most N new entries, in the file's order")
    a = ap.parse_args()
    {"search": cmd_search, "channel": cmd_channel, "videos": cmd_videos, "fast": cmd_fast, "video": cmd_video,
     "comments": cmd_comments, "sheet": cmd_sheet, "bank": cmd_bank}[a.cmd](a)


if __name__ == "__main__":
    try:
        main()
    except ApiError as e:
        sys.exit(str(e))

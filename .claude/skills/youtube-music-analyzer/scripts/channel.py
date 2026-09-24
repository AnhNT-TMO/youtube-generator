#!/usr/bin/env python3
import argparse
import collections
import json
import os
import re
import statistics
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
YTDLP = os.path.join(os.path.dirname(HERE), ".venv", "bin", "yt-dlp")
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿✝✨]")
WORD = re.compile(r"[A-Za-z][A-Za-z']+")
STOP = set("the a an and or of to in for with my your you me i is it on at by from that this be are was".split())


def flat(url, limit):
    args = [YTDLP, "--js-runtimes", "node", "--no-warnings", "-q", "--flat-playlist", "-J",
            "--extractor-args", "youtubetab:approximate_date", "--playlist-end", str(limit), url]
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    return json.loads(r.stdout)


def bucket(d):
    if d is None:
        return "unknown"
    if d <= 70:
        return "short"
    if d <= 600:
        return "single"
    if d < 1500:
        return "ep"
    return "compilation"


def title_features(titles):
    n = max(1, len(titles))
    words = collections.Counter()
    for t in titles:
        words.update(w.lower() for w in WORD.findall(t) if w.lower() not in STOP)
    return {
        "n": len(titles),
        "mean_chars": round(statistics.mean(len(t) for t in titles), 1) if titles else None,
        "with_emoji": round(sum(bool(EMOJI.search(t)) for t in titles) / n, 2),
        "with_pipe": round(sum("|" in t for t in titles) / n, 2),
        "with_dash": round(sum(bool(re.search(r"\s[–—-]\s", t)) for t in titles) / n, 2),
        "with_year": round(sum(bool(re.search(r"\b20\d\d\b", t)) for t in titles) / n, 2),
        "with_hours": round(sum(bool(re.search(r"\b\d+\s*(hour|hr)s?\b", t, re.I)) for t in titles) / n, 2),
        "top_words": [w for w, _ in words.most_common(25)],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="channel URL or a video.info.json (its channel_url is used)")
    ap.add_argument("out")
    ap.add_argument("--limit", type=int, default=1000, help="uploads per tab (flat listing is cheap; big channels need a high limit for 'oldest')")
    a = ap.parse_args()
    focus = None
    if a.source.endswith(".json"):
        info = json.load(open(a.source))
        url, focus = info["channel_url"], info.get("id")
    else:
        url = a.source.rstrip("/")
    os.makedirs(a.out, exist_ok=True)

    tabs = {}
    for tab in ("videos", "shorts", "streams"):
        d = flat(f"{url}/{tab}", a.limit)
        if d and d.get("entries"):
            tabs[tab] = d
    if not tabs:
        sys.exit(f"no uploads listed for {url}")
    meta = next(iter(tabs.values()))
    vids = []
    for tab, d in tabs.items():
        for i, e in enumerate(d.get("entries") or []):
            ts = e.get("timestamp")
            vids.append({
                "id": e.get("id"), "title": e.get("title"), "tab": tab,
                "duration_s": e.get("duration"), "views": e.get("view_count"),
                "upload_date_approx": time.strftime("%Y-%m-%d", time.gmtime(ts)) if ts else None,
                "order_newest_first": i, "kind": "short" if tab == "shorts" else bucket(e.get("duration")),
            })
    long_ = [v for v in vids if v["tab"] != "shorts"]
    views = [v["views"] for v in long_ if v["views"] is not None]
    total = sum(views) or 1
    by_kind = {}
    for k in ("single", "ep", "compilation", "short"):
        vs = [v for v in vids if v["kind"] == k]
        vv = [v["views"] for v in vs if v["views"] is not None]
        by_kind[k] = {"n": len(vs), "views_total": sum(vv), "views_median": statistics.median(vv) if vv else None,
                      "views_max": max(vv) if vv else None}
    top = sorted(long_, key=lambda v: -(v["views"] or 0))[:15]
    vids_tab = [v for v in long_ if v["tab"] == "videos"] or long_
    oldest = sorted(vids_tab, key=lambda v: -v["order_newest_first"])[:12]
    truncated = any(len(d.get("entries") or []) >= a.limit for d in tabs.values())
    dated = sorted(v["upload_date_approx"] for v in long_ if v["upload_date_approx"])
    out = {
        "channel": meta.get("channel") or meta.get("uploader"), "channel_id": meta.get("channel_id"),
        "channel_url": url, "subscribers": meta.get("channel_follower_count"),
        "description": meta.get("description"), "tags": meta.get("tags"),
        "scanned_at": time.strftime("%Y-%m-%d"),
        "n_uploads": {t: len(d.get("entries") or []) for t, d in tabs.items()},
        "first_upload_approx": dated[0] if dated else None, "last_upload_approx": dated[-1] if dated else None,
        "views_total_listed": sum(views), "views_by_kind": by_kind,
        "top1_share": round((top[0]["views"] or 0) / total, 3) if top else None,
        "top": top, "oldest": oldest,
        "title_patterns": {k: title_features([v["title"] for v in long_ if v["kind"] == k and v["title"]])
                           for k in ("single", "compilation")},
        "focus_video": focus, "listing_truncated": truncated,
        "videos": vids,
    }
    if focus:
        f = next((v for v in vids if v["id"] == focus), None)
        if f:
            out["focus_rank_by_views"] = 1 + sorted(views, reverse=True).index(f["views"]) if f["views"] in views else None
            out["focus_share_of_views"] = round((f["views"] or 0) / total, 3)
            order = sorted(vids_tab, key=lambda v: -v["order_newest_first"])
            out["focus_upload_index_from_oldest"] = (1 + order.index(f)) if f in order else None
    json.dump(out, open(os.path.join(a.out, "channel.json"), "w"), indent=1, ensure_ascii=False)

    L = [f"# Channel scan: {out['channel']}", "",
         f"- {url} · {out['subscribers']} subs · uploads {out['n_uploads']} · first ≈ {out['first_upload_approx']} · "
         f"last ≈ {out['last_upload_approx']} · listed views {out['views_total_listed']:,}",
         f"- Views by kind: " + "; ".join(f"{k} n={v['n']} median={v['views_median']} max={v['views_max']}"
                                          for k, v in by_kind.items() if v["n"]),
         f"- Top video share of all views: {out['top1_share']}"]
    if focus and "focus_rank_by_views" in out:
        L.append(f"- Analysed video: rank {out['focus_rank_by_views']} by views, {out['focus_share_of_views']} of views, "
                 f"upload #{out['focus_upload_index_from_oldest']} from the oldest")
    L += ["", "## Top by views", "", "| views | dur | kind | date≈ | title |", "|---|---|---|---|---|"]
    L += [f"| {v['views']:,} | {v['duration_s']} | {v['kind']} | {v['upload_date_approx']} | {v['title']} |" for v in top if v["views"]]
    L += ["", "## First uploads (launch strategy)", "", "| # | views | dur | kind | title |", "|---|---|---|---|---|"]
    L += [f"| {i+1} | {v['views']} | {v['duration_s']} | {v['kind']} | {v['title']} |" for i, v in enumerate(oldest)]
    L += ["", "## Title patterns", ""]
    for k, tf in out["title_patterns"].items():
        if tf["n"]:
            L.append(f"- **{k}** (n={tf['n']}): {tf['mean_chars']} chars, emoji {tf['with_emoji']}, '|' {tf['with_pipe']}, "
                     f"dash {tf['with_dash']}, year {tf['with_year']}, 'N hours' {tf['with_hours']}; top words: "
                     + ", ".join(tf["top_words"][:15]))
    open(os.path.join(a.out, "channel.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L[:8]))


if __name__ == "__main__":
    main()

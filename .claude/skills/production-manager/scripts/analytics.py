#!/usr/bin/env python3
import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
from results import our_videos  # noqa: E402

SECRET = ROOT / ".claude" / "skills" / "youtube-translate" / ".cache" / "client_secret.json"
TOKENS = HERE.parent / ".cache" / "tokens"
SCOPES = ["https://www.googleapis.com/auth/yt-analytics.readonly", "https://www.googleapis.com/auth/youtube.readonly"]
MARKS_S = (15, 30, 60)


def token_path(ch: str) -> Path:
    return TOKENS / f"{ch}.json"


def cmd_auth(a):
    from google_auth_oauthlib.flow import InstalledAppFlow
    if not SECRET.exists():
        sys.exit(f"missing {SECRET.relative_to(ROOT)} (the OAuth client of youtube-translate)")
    flow = InstalledAppFlow.from_client_secrets_file(str(SECRET), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
    TOKENS.mkdir(parents=True, exist_ok=True)
    token_path(a.channel).write_text(creds.to_json())
    print(f"saved {token_path(a.channel).relative_to(ROOT)} (scopes: {', '.join(SCOPES)}); sign in with the channel's Google account")


def client(ch: str):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    p = token_path(ch)
    if not p.exists():
        sys.exit(f"no analytics token: the CEO runs once `analytics.py auth --channel {ch}` (browser sign-in)")
    c = Credentials.from_authorized_user_file(str(p), SCOPES)
    if not c.valid:
        c.refresh(Request())
        p.write_text(c.to_json())
    return build("youtubeAnalytics", "v2", credentials=c, cache_discovery=False)


def query(ya, **kw):
    from googleapiclient.errors import HttpError
    try:
        r = ya.reports().query(ids="channel==MINE", **kw).execute()
    except HttpError as e:
        msg = str(e)
        if "accessNotConfigured" in msg or "has not been used" in msg:
            sys.exit("YouTube Analytics API is not enabled in the Cloud project of the OAuth client: enable it in Google Cloud "
                     "Console → APIs & Services → Library → 'YouTube Analytics API', then run fetch again")
        return {"error": msg[:300]}
    cols = [h["name"] for h in r.get("columnHeaders", [])]
    return {"rows": [dict(zip(cols, row)) for row in r.get("rows") or []]}


def retention_at(rows, duration_s):
    if not rows or not duration_s:
        return {}
    pts = sorted((float(r["elapsedVideoTimeRatio"]), float(r["audienceWatchRatio"])) for r in rows)
    out = {}
    for s in MARKS_S:
        x = s / duration_s
        if x > 1:
            continue
        near = min(pts, key=lambda p: abs(p[0] - x))
        out[f"ret_{s}s"] = round(near[1], 3)
    return out


def cmd_fetch(a):
    ya = client(a.channel)
    ch = ROOT / "channel" / a.channel
    snaps = sorted((ROOT / "research" / "trends" / a.channel / "snapshots").glob("*.json"))
    meta = json.loads(snaps[-1].read_text())["videos"] if snaps else {}
    end = date.today().isoformat()
    out = {"fetched_at": datetime.now().isoformat(timespec="seconds"), "videos": {}}
    for vid, info in our_videos(ch).items():
        m = meta.get(vid) or {}
        start = (m.get("published") or (date.today() - timedelta(days=90)).isoformat())[:10]
        f = f"video=={vid}"
        tot = query(ya, startDate=start, endDate=end, filters=f,
                    metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,likes,subscribersGained")
        reach = query(ya, startDate=start, endDate=end, filters=f, metrics="impressions,impressionClickThroughRate")
        ret = query(ya, startDate=start, endDate=end, filters=f, dimensions="elapsedVideoTimeRatio",
                    metrics="audienceWatchRatio,relativeRetentionPerformance")
        src = query(ya, startDate=start, endDate=end, filters=f, dimensions="insightTrafficSourceType", metrics="views",
                    sort="-views")
        row = (tot.get("rows") or [{}])[0]
        out["videos"][vid] = {"dir": info["dir"], "kind": info["kind"], **row,
                              **({k: v for k, v in ((reach.get("rows") or [{}])[0]).items()} if "rows" in reach
                                 else {"ctr_note": "impressions/CTR not returned by the Analytics API: Studio screenshot"}),
                              **retention_at(ret.get("rows"), m.get("dur_s")),
                              "traffic": {r["insightTrafficSourceType"]: r["views"] for r in src.get("rows") or []},
                              "errors": [x["error"] for x in (tot, ret, src) if "error" in x] or None}
        v = out["videos"][vid]
        print(f"{Path(info['dir']).name:40} views {v.get('views', '–')} · avg {v.get('averageViewDuration', '–')} s "
              f"({v.get('averageViewPercentage', '–')} %) · ret30 {v.get('ret_30s', '–')} · CTR {v.get('impressionClickThroughRate', '–')} · "
              f"top source {max(v['traffic'], key=v['traffic'].get) if v['traffic'] else '–'}")
    dest = ROOT / "production" / a.channel / "analytics.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(dest.relative_to(ROOT), "(data lags YouTube by ~1–2 days)")


def main():
    ap = argparse.ArgumentParser(description="Our channel's YouTube Analytics per video (retention, watch time, traffic, CTR if available)")
    ap.add_argument("cmd", choices=["auth", "fetch"])
    ap.add_argument("--channel", required=True)
    a = ap.parse_args()
    {"auth": cmd_auth, "fetch": cmd_fetch}[a.cmd](a)


if __name__ == "__main__":
    main()

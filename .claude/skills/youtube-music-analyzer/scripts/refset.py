#!/usr/bin/env python3
import argparse
import collections
import datetime
import os
import statistics as st
import sys

import yaml

from build_reference import REPO, med, mmss, density, register, our_baseline


def load_ref(run):
    p = os.path.join(run, "reference.yaml")
    if not os.path.exists(p):
        sys.exit(f"{p} missing: run the analyzer on that video first")
    return yaml.safe_load(open(p)) or {}


def majority(vals):
    vals = [v for v in vals if v]
    return collections.Counter(vals).most_common(1)[0][0] if vals else None


def build_set(runs, topic, trend, channel_dir):
    refs = [(os.path.relpath(os.path.abspath(r), REPO), load_ref(r)) for r in runs]
    C = [r["criteria"] for _, r in refs]

    def pick(*path):
        out = []
        for c in C:
            v = c
            for k in path:
                v = (v or {}).get(k)
            out.append(v)
        return out

    tempos = [x for x in pick("tempo", "felt_bpm_median") if x]
    ranges = [x for x in pick("tempo", "felt_bpm_range") if x]
    meter_counts = collections.Counter()
    for mc in pick("tempo", "meter_counts"):
        meter_counts.update({k: v for k, v in (mc or {}).items() if v})
    calls = collections.Counter()
    for cl in pick("voice", "calls"):
        calls.update(cl or {})
    gender = majority(pick("voice", "gender"))
    f0 = med(pick("voice", "f0_median_hz"))
    wpm = med(pick("lyric_density", "words_per_min_sung"))
    voice_s, lyric_s, lvl = med(pick("opening", "voice_s")), med(pick("opening", "first_lyric_s")), med(pick("opening", "level_0_15s_db"))
    lens = [x for x in pick("song_length", "median_s") if x]
    durs = [x for x in pick("video", "duration_s") if x]
    criteria = {
        "video": {"duration_s": med(durs), "duration": mmss(med(durs)), "n_songs": med(pick("video", "n_songs"), 0)},
        "song_length": {"median_s": med(lens), "median": mmss(med(lens)),
                        "min_s": min([x for x in pick("song_length", "min_s") if x is not None], default=None),
                        "max_s": max([x for x in pick("song_length", "max_s") if x is not None], default=None)},
        "tempo": {"felt_bpm_median": med(tempos), "felt_bpm_range": [min(r[0] for r in ranges), max(r[1] for r in ranges)] if ranges else None,
                  "members_felt_bpm": pick("tempo", "felt_bpm_median"),
                  "spread_pct": round(100 * (max(tempos) / min(tempos) - 1)) if len(tempos) > 1 else None,
                  "meter": {"compound": "6/8·12/8", "simple": "4/4"}.get(meter_counts.most_common(1)[0][0]) if meter_counts else None,
                  "meter_counts": dict(meter_counts) or None,
                  "_unit": "felt BPM (dotted quarter in 6/8·12/8, quarter in 4/4) = the unit of verify.py and the Style prompt",
                  "_how": "median of the members' medians"},
        "voice": {"gender": gender, "register": register(gender, f0), "f0_median_hz": f0,
                  "members_f0_hz": pick("voice", "f0_median_hz"), "calls": dict(calls) or None,
                  "_prov": "median of the members (AudioSet + pYIN on the Demucs vocal stem)"},
        "opening": {"voice_s": voice_s, "first_lyric_s": lyric_s, "level_0_15s_db": lvl,
                    "members": [{"voice_s": c["opening"].get("voice_s"), "first_lyric_s": c["opening"].get("first_lyric_s"),
                                 "level_0_15s_db": c["opening"].get("level_0_15s_db")} for c in C],
                    "gate": {"voice_within_10s": voice_s is not None and voice_s <= 10,
                             "lyric_within_15s": lyric_s is not None and lyric_s <= 15,
                             "level_ok": lvl is not None and lvl >= -4}},
        "lyric_density": {"words_per_min_sung": wpm, "label": density(wpm), "members": pick("lyric_density", "words_per_min_sung"),
                          "source": "median of the members"},
    }
    members, tracks, n = [], [], 0
    guard = collections.defaultdict(set)
    tags = collections.Counter()
    for i, (rel, r) in enumerate(refs, 1):
        s = r.get("source") or {}
        members.append({"i": i, "research": rel, "url": s.get("url"), "video_id": s.get("video_id"), "title": s.get("title"),
                        "channel": s.get("channel"), "subscribers": s.get("subscribers"), "views": s.get("views"),
                        "upload_date": s.get("upload_date"), "duration_s": s.get("duration_s"),
                        "felt_bpm": r["criteria"]["tempo"].get("felt_bpm_median"), "f0_hz": r["criteria"]["voice"].get("f0_median_hz"),
                        "words_per_min": r["criteria"]["lyric_density"].get("words_per_min_sung")})
        for t in r.get("tracks") or []:
            n += 1
            tracks.append({**t, "n": n, "title": f"[{i}] {t.get('title') or ''}".strip()})
        for k, v in (r.get("copy_guard_seed") or {}).items():
            guard[k].update(x for x in v or [] if x is not None)
        tags.update(x.lower() for x in (r.get("packaging") or {}).get("tags") or [])
    views = [m["views"] for m in members if m["views"]]
    warnings = []
    if len(refs) < 3:
        warnings.append(f"only {len(refs)} member(s): a set of 1-2 videos drifts toward copying them (SKILL.md: 3-5)")
    chans = [m["channel"] for m in members]
    if len(set(chans)) < len(chans):
        warnings.append("several members from the same channel: prefer one video per channel")
    if criteria["tempo"]["spread_pct"] and criteria["tempo"]["spread_pct"] > 20:
        warnings.append(f"member tempos spread {criteria['tempo']['spread_pct']}% (> 20 %, one album = one tempo band): "
                        "drop the outlier or split into two sets")
    return {
        "schema": "reference-set/v1", "generated_at": datetime.date.today().isoformat(),
        "source": {"kind": "reference set", "title": f"Reference set: {topic or 'niche'} ({len(members)} videos)",
                   "channel": f"{len(set(chans))} channels", "views": int(st.median(views)) if views else None,
                   "duration_s": criteria["video"]["duration_s"], "topic": topic, "trend_report": trend},
        "members": members, "criteria": criteria, "tracks": tracks,
        "packaging": {"titles": [m["title"] for m in members], "tags_top": [t for t, _ in tags.most_common(20)]},
        "copy_guard_seed": {k: sorted(v, key=str) for k, v in guard.items()},
        "our_baseline": our_baseline(channel_dir) if channel_dir else None,
        "warnings": warnings,
    }


def main():
    ap = argparse.ArgumentParser(description="Combine several analyzed reference videos into one reference set (medians)")
    ap.add_argument("out", help="research/<set-slug> (created)")
    ap.add_argument("runs", nargs="+", help="research/<slug> of each analyzed video")
    ap.add_argument("--topic", help="trend topic / branch the set stands for")
    ap.add_argument("--trend", help="trend report the set comes from")
    ap.add_argument("--channel-dir")
    a = ap.parse_args()
    ref = build_set(a.runs, a.topic, a.trend, a.channel_dir)
    os.makedirs(a.out, exist_ok=True)
    p = os.path.join(a.out, "reference.yaml")
    with open(p, "w") as f:
        f.write("# Reference set (youtube-music-analyzer refset.py): medians of several trend videos. Interpretation in analysis.md.\n")
        yaml.safe_dump(ref, f, sort_keys=False, allow_unicode=True, width=120)
    c = ref["criteria"]
    print(f"wrote {p}")
    print(f"members {len(ref['members'])}: tempo {c['tempo']['felt_bpm_median']} felt BPM (members {c['tempo']['members_felt_bpm']}), "
          f"voice {c['voice']['gender']} {c['voice']['register']} f0 {c['voice']['f0_median_hz']} Hz, "
          f"{c['lyric_density']['words_per_min_sung']} words/sung min, song {c['song_length']['median']}, "
          f"video {c['video']['duration']} / {c['video']['n_songs']} songs, voice at {c['opening']['voice_s']} s")
    for w in ref["warnings"]:
        print("WARN", w)


if __name__ == "__main__":
    main()

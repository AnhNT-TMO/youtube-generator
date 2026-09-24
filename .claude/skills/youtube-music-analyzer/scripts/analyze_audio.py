#!/usr/bin/env python3
"""Split a long music video (album / playlist mix) into songs: video length, song count, song lengths, and the
level of the first 15 s of the video (criteria 1, 2, 5 of SKILL.md).

Outputs into --out:
  analysis.json   song split + per-song length + level of the first 15 s of the video
  report.md       the same as a table
  overview.png    whole-video loudness + song boundaries + YouTube most-replayed (to check the split)

Song boundaries come from (in priority order): --segments (reviewed segments.yaml/json with titles),
--boundaries, YouTube chapters, timestamps in the description, or automatic detection: level dips +
timbre change, the caption words changing (--captions), dips whose two sides share the same harmonic
material rejected (an internal break), then the set of joins chosen with a song-length prior.
Tempo, meter and voice are measured by measure.py (verification-audio's QC units), not here.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

import warnings

import numpy as np

warnings.filterwarnings("ignore")

SR = 22050
HOP = 512
FPS = SR / HOP  # feature frames per second (~43)

def log(*a):
    print(*a, file=sys.stderr, flush=True)


def fmt_t(sec):
    sec = int(round(sec))
    h, m, s = sec // 3600, sec % 3600 // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def parse_t(s):
    parts = [int(p) for p in s.split(":")]
    t = 0
    for p in parts:
        t = t * 60 + p
    return t


def decode(path):
    import soundfile as sf
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-ac", "1", "-ar", str(SR), tmp], check=True)
    y, _ = sf.read(tmp, dtype="float32")
    os.unlink(tmp)
    return y


# ---------------------------------------------------------------- boundaries

TS = r"[\[(]?(\d{1,2}(?::\d{2}){1,2})[\])]?"


def boundaries_from_description(desc, duration):
    """Tracklist lines '00:00 Song Title' / '1. 3:45 Title' (timestamp at the START of the line) or
    'Song Title - 03:45' (timestamp at the END) -> [(start, title)]. Timestamps inside text (scripture
    such as 'Isaiah 41:10', 'John 3:16') are ignored. Keeps the longest increasing chain that starts
    near 0, so one stray timestamp does not throw the whole tracklist away."""
    head = re.compile(r"^\s*(?:[-*•▶►]\s*)?(?:\d{1,2}[.)]\s+)?" + TS + r"(?![\d:])\s*[-–—|:.)]*\s*(.*)$")
    tail = re.compile(r"^\s*(?:\d{1,2}[.)]\s+)?(.+?)\s*[-–—|]\s*" + TS + r"\s*$")
    cand = []
    for line in (desc or "").splitlines():
        m = head.match(line)
        if m:
            t, title = parse_t(m.group(1)), m.group(2)
        else:
            m = tail.match(line)
            if not m:
                continue
            t, title = parse_t(m.group(2)), m.group(1)
        title = (title or "").strip(" -–—|:.)([]\t") or None
        if t < duration:
            cand.append((t, title))
    # longest strictly increasing subsequence that starts within 5 s of 0 (DP; a stray timestamp is skipped, not fatal)
    n = len(cand)
    L, prev = [1] * n, [-1] * n
    for i in range(n):
        for j in range(i):
            if cand[j][0] < cand[i][0] and L[j] + 1 > L[i] and (cand[j][0] <= 5 or prev[j] != -1 or cand[j][0] <= 5):
                L[i], prev[i] = L[j] + 1, j
    best = []
    for i in sorted(range(n), key=lambda i: -L[i]):
        chain, k = [], i
        while k != -1:
            chain.append(cand[k]); k = prev[k]
        chain.reverse()
        if chain and chain[0][0] <= 5:
            best = chain
            break
    if best and len(best) < len(cand):
        dropped = [c for c in cand if c not in best]
        print(f"description timestamps: ignored {len(dropped)} out-of-order line(s): {dropped[:4]}", file=sys.stderr)
    return best if len(best) >= 3 else []


def load_segments(path):
    """segments.yaml / .json: a list of {start: "m:ss" or seconds, title, source, confidence}
    (or {"segments": [...]}). Written by Claude after reviewing the evidence (SKILL.md step 2)."""
    txt = open(path).read()
    if path.endswith((".yaml", ".yml")):
        import yaml
        data = yaml.safe_load(txt)
    else:
        data = json.loads(txt)
    if isinstance(data, dict):
        data = data.get("segments", [])
    out = []
    for s in data:
        st = s["start"]
        st = float(parse_t(st)) if isinstance(st, str) and ":" in st else float(st)
        out.append({**s, "start_s": st})
    out.sort(key=lambda s: s["start_s"])
    if out and out[0]["start_s"] > 0:
        out[0]["start_s"] = 0.0
    return out


def block_level_db(y, sec):
    """Power-mean level in dB over blocks of `sec` seconds."""
    n = int(SR * sec)
    k = len(y) // n
    out = np.empty(k)
    step = max(1, int(600 / sec))   # 10 min of blocks at a time: no full-length float64 copy
    for i in range(0, k, step):
        j = min(k, i + step)
        out[i:j] = (y[i * n: j * n].reshape(j - i, n).astype(np.float32) ** 2).mean(1)
    return 10 * np.log10(out + 1e-12)


def chunked_features(y, chunk_s=120):
    """MFCC + chroma per 1-second block, computed in chunks to bound memory."""
    import librosa
    per = int(FPS)
    out = []
    n = int(chunk_s * SR)
    for i in range(0, len(y), n):
        seg = y[i:i + n]
        if len(seg) < SR:
            break
        S = np.abs(librosa.stft(seg, hop_length=HOP)) ** 2
        mf = librosa.feature.mfcc(S=librosa.power_to_db(librosa.feature.melspectrogram(S=S, sr=SR)), n_mfcc=20)
        ch = librosa.feature.chroma_stft(S=S, sr=SR)
        F = np.vstack([mf[1:], ch * 3])
        k = F.shape[1] // per
        out.append(F[:, : k * per].reshape(F.shape[0], k, per).mean(axis=2))
    return np.hstack(out)


def snap_to_joins(y, starts, window=40.0):
    """Chapters / description timestamps are often a few seconds (sometimes 30+ s) off.
    Move each start to the deepest dip within +-window s if that dip is clearly a join."""
    from scipy.ndimage import median_filter
    Q = 0.25
    L = block_level_db(y, Q)
    base = median_filter(L, size=int(30 / Q) | 1, mode="nearest")
    out, report = [starts[0]], []
    for t in starts[1:]:
        i = int(t / Q)
        lo, hi = max(0, i - int(window / Q)), min(len(L), i + int(window / Q))
        m = lo + int(np.argmin(L[lo:hi]))
        at_chapter = float(L[min(i, len(L) - 1)])
        dip = float(base[m] - L[m])
        if dip > 20 and L[m] < at_chapter - 15:
            out.append(round(m * Q, 2))
            report.append({"given_s": t, "snapped_s": round(m * Q, 1), "offset_s": round(m * Q - t, 1),
                           "level_at_given_db": round(at_chapter, 1), "dip_db": round(dip, 1)})
        else:
            out.append(t)
    return out, report


def otsu(vals, floor=1.2):
    """Threshold splitting scores into two groups with max between-class variance."""
    v = np.sort(np.asarray(vals, dtype=float))
    if len(v) < 3:
        return floor
    best, thr = -1, floor
    for i in range(1, len(v)):
        a, b = v[:i], v[i:]
        between = len(a) * len(b) * (a.mean() - b.mean()) ** 2
        if between > best:
            best, thr = between, (v[i - 1] + v[i]) / 2
    return max(floor, thr)


def recurrence(C, t, q=30, back=240, gap=3):
    """How strongly the harmonic material right after t already occurred in the 4 min before it
    (and vice versa): max mean cosine of 1 s chroma blocks over all lags. An internal break of one
    song scores high (~0.93 on the vintagegospel mix) because the chorus comes back; a real join
    scores like any two songs of the album (~0.78-0.87)."""
    t = int(t)
    if t - gap - q < 0 or t + gap + q > C.shape[1]:
        return None

    def best(Qm, R):
        if R.shape[1] < Qm.shape[1]:
            return None
        n = R.shape[1] - Qm.shape[1] + 1
        sims = [float((Qm * R[:, l:l + Qm.shape[1]]).sum(0).mean()) for l in range(n)]
        return max(sims)
    a = best(C[:, t + gap:t + gap + q], C[:, max(0, t - back):t - gap])
    b = best(C[:, t - gap - q:t - gap], C[:, t + gap:t + gap + back])
    vals = [v for v in (a, b) if v is not None]
    return round(float(np.mean(vals)), 3) if vals else None


def length_prior(L):
    """Log-prior for a song of L seconds (AI/Suno album songs: mostly 2.5-8 min)."""
    if L < 150:
        return -((150 - L) / 25.0) ** 2
    if L > 480:
        return -((L - 480) / 90.0) ** 2
    return 0.0


def auto_boundaries(y, min_len, expected=None, cues=None):
    """Find song joins in a continuous mix.

    Songs in AI/playlist albums are usually joined by a fade-out -> fade-in, which shows up as a short,
    deep dip below the surrounding level. Candidates = dips; each is scored by dip depth + timbre/harmony
    change between the 20 s before and after + caption word change, minus a penalty when both sides share
    the same harmonic (or lyric) material - an internal break where the chorus comes back. The final set
    maximises score + song-length prior (dynamic programming), optionally with an exact song count.
    """
    from scipy.ndimage import median_filter, minimum_filter1d
    from scipy.signal import find_peaks

    cues = cues or []
    dur = len(y) / SR
    Q = 0.25  # level resolution (s)
    L = block_level_db(y, Q)
    base = median_filter(L, size=int(30 / Q) | 1, mode="nearest")
    depth = np.clip(base - minimum_filter1d(L, size=int(1 / Q), mode="nearest"), 0, None)

    feat = chunked_features(y)
    chroma = feat[-12:] / (np.linalg.norm(feat[-12:], axis=0, keepdims=True) + 1e-9)
    feat = (feat - feat.mean(1, keepdims=True)) / (feat.std(1, keepdims=True) + 1e-9)
    k = feat.shape[1]
    W = 20
    cs = np.cumsum(np.pad(feat, ((0, 0), (1, 0))), axis=1)
    nov = np.zeros(k)
    for i in range(W, k - W):
        nov[i] = np.linalg.norm((cs[:, i] - cs[:, i - W]) / W - (cs[:, i + W] - cs[:, i]) / W)
    nov = nov / (np.percentile(nov, 99) + 1e-9)

    def dip_at(sec, win=4.0):
        i = int(sec / Q)
        lo, hi = max(0, i - int(win / Q)), min(len(L), i + int(win / Q))
        return (lo + int(np.argmin(L[lo:hi]))) * Q

    # candidates: dips at least 20 s apart
    pk, _ = find_peaks(depth, distance=int(20 / Q), height=6)
    cand = sorted(round(c * Q, 2) for c in pk if min_len / 2 < c * Q < dur - min_len / 2)

    if cues:
        from captions import lexical_recurrence
    recs = {t: recurrence(chroma, t) for t in cand}
    # "same material on both sides" is judged against joins we are sure of (deep dips)
    sure = [recs[t] for t in cand if recs[t] is not None and depth[int(t / Q)] >= 40]
    rvals = [v for v in recs.values() if v is not None]
    rbase = float(np.median(sure)) if len(sure) >= 3 else (float(np.percentile(rvals, 25)) if rvals else 0.0)

    scored = []
    for t in cand:
        j = int(t)
        n_here = float(nov[max(0, j - 5): j + 6].max()) if j < k else 0.0
        d = float(depth[int(t / Q)])
        # depth counts up to 60 dB: joins through digital silence (~90 dB dips) must win
        # over nearby in-song dips that merely have a larger timbre change
        s_base = min(d, 60.0) / 30.0 + n_here
        lx = lexical_recurrence(cues, t) if cues else None
        s_lex = 0.5 if lx is not None and lx < 0.12 else 0.0
        pen_lex = float(np.clip((lx - 0.25) / 0.15, 0, 2)) if lx is not None else 0.0
        r = recs.get(t)
        pen = float(np.clip((r - (rbase + 0.04)) / 0.02, 0, 2)) if r is not None else 0.0
        scored.append({"at_s": t, "score": round(s_base + s_lex - pen - pen_lex, 2), "base": round(s_base, 2),
                       "dip_db": round(d, 1), "novelty": round(n_here, 2), "lexical_recurrence": lx,
                       "recurrence": r, "recurrence_penalty": round(pen + pen_lex, 2)})

    thr = otsu([s["base"] for s in scored]) if scored else 1.2
    nodes = [{"at_s": 0.0, "gain": 0.0}] + [{**s, "gain": s["score"] - thr} for s in scored] + [{"at_s": dur, "gain": 0.0}]
    n = len(nodes)
    K = (expected + 1) if expected else None
    NEG = -1e18
    if K:
        best = np.full((n, K + 1), NEG); best[0, 1] = 0.0
        back = np.zeros((n, K + 1), dtype=int)
    else:
        best = np.full(n, NEG); best[0] = 0.0
        back = np.zeros(n, dtype=int)
    for j in range(1, n):
        tj = nodes[j]["at_s"]
        for i in range(j - 1, -1, -1):
            Lseg = tj - nodes[i]["at_s"]
            if Lseg > 1500 and j != n - 1:
                break  # no song is 25 min: keeps long (3-12 h) mixes tractable
            if Lseg < min_len * (0.5 if j == n - 1 else 1.0):
                continue
            add = nodes[j]["gain"] + length_prior(Lseg)
            if K:
                for c in range(1, K):
                    if best[i, c] > NEG and best[i, c] + add > best[j, c + 1]:
                        best[j, c + 1] = best[i, c] + add; back[j, c + 1] = i
            elif best[i] > NEG and best[i] + add > best[j]:
                best[j] = best[i] + add; back[j] = i
    j = n - 1
    if K and best[j, K] <= NEG:  # impossible count -> fall back to unconstrained
        return auto_boundaries(y, min_len, None, cues)
    path, c = [], K
    while j > 0:
        i = back[j, c] if c else back[j]
        path.append(j)
        if c:
            c -= 1
        j = i
    chosen_idx = sorted(p for p in path if 0 < p < n - 1)
    starts = [0.0] + [round(dip_at(nodes[p]["at_s"]), 2) for p in chosen_idx]
    chosen_t = {nodes[p]["at_s"] for p in chosen_idx}
    rejected = sorted([s for s in scored if s["at_s"] not in chosen_t], key=lambda s: -s["score"])[:15]
    return starts, {"threshold": round(thr, 2), "recurrence_base": round(rbase, 3),
                    "chosen": [{k2: v for k2, v in nodes[p].items() if k2 != "gain"} for p in chosen_idx],
                    "top_rejected": rejected}


def plot_overview(path, rms_db, tracks, heatmap, duration, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    per = int(FPS)
    lvl = rms_db[: len(rms_db) // per * per].reshape(-1, per).mean(1)
    fig, ax = plt.subplots(2, 1, figsize=(18, 6), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    ax[0].plot(np.arange(len(lvl)) / 60, lvl, lw=0.6, color="#4a6fa5")
    for i, t in enumerate(tracks):
        ax[0].axvline(t["start_s"] / 60, color="#c0392b", lw=0.8)
        ax[0].text(t["start_s"] / 60 + 0.1, ax[0].get_ylim()[1] - 2, str(i + 1), fontsize=8, va="top")
    ax[0].set_ylabel("level dB (1s)")
    ax[0].set_title(title[:120])
    if heatmap:
        xs = [(h["start_time"] + h["end_time"]) / 2 / 60 for h in heatmap]
        ax[1].fill_between(xs, [h["value"] for h in heatmap], color="#e67e22", alpha=0.7)
        ax[1].set_ylabel("most replayed")
    for t in tracks:
        ax[1].axvline(t["start_s"] / 60, color="#c0392b", lw=0.8)
    ax[1].set_xlabel("minutes")
    ax[1].set_xlim(0, duration / 60)
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--info", help="yt-dlp .info.json (chapters, description, heatmap)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--segments", help="reviewed segments file (.yaml/.json): [{start, title, source, confidence}]")
    ap.add_argument("--captions", help="captions .vtt (word-change evidence for auto-detection)")
    ap.add_argument("--boundaries", help="comma-separated start times (s or m:ss) to force song splits")
    ap.add_argument("--expected-tracks", type=int, help="force auto-detection to this many songs")
    ap.add_argument("--min-track", type=int, default=90, help="minimum song length for auto-detect (s)")
    ap.add_argument("--single", action="store_true", help="treat the whole file as one song")
    ap.add_argument("--no-snap", action="store_true", help="use chapter times exactly as given")
    ap.add_argument("--force-auto", action="store_true",
                    help="ignore chapters/description; auto-detect (and score against chapters if present)")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    import librosa
    info = json.load(open(args.info)) if args.info else {}
    log("decoding audio ...")
    y = decode(args.audio)
    duration = len(y) / SR
    rms_db = librosa.amplitude_to_db(librosa.feature.rms(y=y, hop_length=HOP)[0], ref=1.0)
    desc_bd = [] if args.force_auto else boundaries_from_description(info.get("description"), duration)

    titles, curves, seg_meta, merged_short, snaps = None, None, None, [], []
    cues = []
    if args.captions and os.path.exists(args.captions):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from captions import parse_vtt
        cues = parse_vtt(args.captions)
    if args.single:
        starts, source = [0.0], "single"
    elif args.segments:
        seg_meta = load_segments(args.segments)
        starts = [s["start_s"] for s in seg_meta]
        titles = [s.get("title") for s in seg_meta]
        source = "segments_file"
    elif args.boundaries:
        starts, source = sorted(float(parse_t(b)) if ":" in b else float(b) for b in args.boundaries.split(",")), "manual"
        if starts[0] > 0:
            starts = [0.0] + starts
    elif not args.force_auto and info.get("chapters") and len(info["chapters"]) >= 2:
        starts = [float(c["start_time"]) for c in info["chapters"]]
        titles = [c.get("title") for c in info["chapters"]]
        source = "youtube_chapters"
    elif desc_bd:
        starts, titles, source = [float(b[0]) for b in desc_bd], [b[1] for b in desc_bd], "description_timestamps"
    else:
        log("no chapters/timestamps -> auto-detecting song boundaries ...")
        starts, curves = auto_boundaries(y, args.min_track, args.expected_tracks, cues)
        source = "auto_detected" + ("+captions" if cues else "")
    if source in ("youtube_chapters", "description_timestamps"):
        if not args.no_snap:
            starts, snaps = snap_to_joins(y, starts)
            if any(abs(x["offset_s"]) >= 3 for x in snaps):
                log(f"snapped {sum(abs(x['offset_s']) >= 3 for x in snaps)} timestamps that were >=3 s off the real join")
        # a 10-60 s "Intro"/"Outro" chapter must not become Track 01 (or a song): merge it into its neighbour
        starts = [0.0] + list(starts[1:])
        tl = list(titles) if titles else [None] * len(starts)
        i = 0
        while len(starts) > 1 and i < len(starts):
            end = starts[i + 1] if i + 1 < len(starts) else duration
            if end - starts[i] < args.min_track:   # < 90 s: an intro/outro sting, not a song
                merged_short.append({"start_s": starts[i], "len_s": round(end - starts[i], 1), "title": tl[i]})
                if i + 1 < len(starts):          # join with the next song (it keeps its own title)
                    del starts[i + 1]; tl[i] = tl[i + 1]; del tl[i + 1]
                else:                             # last one: join with the previous song
                    del starts[i]; del tl[i]
                continue
            i += 1
        titles = tl if titles else None
        if merged_short:
            log(f"merged {len(merged_short)} short chapter(s) into neighbours: {merged_short}")
    log(f"{len(starts)} songs ({source})")

    ends = starts[1:] + [duration]
    tracks = []
    for i, (s, e) in enumerate(zip(starts, ends)):
        f = {"n": i + 1, "start_s": round(s, 1), "start": fmt_t(s), "end": fmt_t(e), "duration_s": round(e - s, 1),
             "title": titles[i] if titles and i < len(titles) else None}
        if seg_meta:
            f["segment_confidence"] = seg_meta[i].get("confidence")
            f["segment_evidence"] = seg_meta[i].get("source")
        tracks.append(f)

    # first 10-15 s of the VIDEO (CLAUDE.md §3): level per 5 s window vs the body of song 1
    L1 = block_level_db(y[: int(ends[0] * SR)], 1.0)
    body = float(np.median(L1))

    def pm(x):  # power mean of 1 s block levels (dB)
        return float(10 * np.log10(np.mean(10 ** (np.asarray(x) / 10)) + 1e-12))
    opening = {
        "rel_db_0_15s": round(pm(L1[0:15]) - body, 1),                              # 0-15 s level vs the body of song 1
        "quiet_start_s": next((i for i, v in enumerate(L1) if v > body - 20), None),   # seconds of near-silence at 0:00
        "_unit": "dB vs median 1 s block level of song 1, power mean",
    }

    heat = info.get("heatmap") or []
    result = {
        "video": {k: info.get(k) for k in ("id", "title", "channel", "duration", "view_count", "like_count",
                                            "upload_date", "channel_follower_count")},
        "segmentation_source": source, "n_tracks": len(tracks),
        "heatmap_bin_s": round(float(heat[0]["end_time"] - heat[0]["start_time"]), 1) if heat else None,
        "video_opening": opening, "tracks": tracks,
    }
    if [x for x in snaps if abs(x["offset_s"]) >= 3]:
        result["timestamp_corrections"] = [x for x in snaps if abs(x["offset_s"]) >= 3]
    if merged_short:
        result["merged_short_chapters"] = merged_short
    if curves is not None:
        result["auto_segmentation"] = curves
        if info.get("chapters"):  # calibration: compare with the real chapters
            truth = [c["start_time"] for c in info["chapters"]][1:]
            hits = [min(abs(t - s) for s in starts) for t in truth]
            curves["vs_chapters"] = {"chapters": len(truth) + 1, "detected": len(starts),
                                     "chapter_errors_s": [round(h, 1) for h in hits],
                                     "within_5s": sum(h <= 5 for h in hits), "within_15s": sum(h <= 15 for h in hits)}
            log("vs chapters:", curves["vs_chapters"])
    json.dump(result, open(os.path.join(args.out, "analysis.json"), "w"), indent=1, ensure_ascii=False)
    plot_overview(os.path.join(args.out, "overview.png"), rms_db, tracks, heat, duration, info.get("title", ""))

    L = [f"# Audio analysis: {info.get('title', args.audio)}", "",
         f"Split: **{source}**, {len(tracks)} songs. Tempo / voice: audio/qc.json (measure.py).", "",
         f"**First 15 s of the video**: {opening['rel_db_0_15s']:+.1f} dB vs the body of song 1; "
         f"near-silence at the start: {opening['quiet_start_s']} s.", "",
         "| # | start | len | title |", "|---|---|---|---|"]
    L += [f"| {t['n']} | {t['start']} | {fmt_t(t['duration_s'])} | {t['title'] or ''} |" for t in tracks]
    if result.get("timestamp_corrections"):
        L += ["", "Timestamps snapped to the real join: " + ", ".join(
            f'{fmt_t(c["given_s"])}→{fmt_t(c["snapped_s"])} ({c["offset_s"]:+.0f}s)' for c in result["timestamp_corrections"])]
    if curves is not None:
        def ev(r):
            bits = [f"score {r['score']}", f"dip {r['dip_db']} dB"]
            if r.get("lexical_recurrence") is not None:
                bits.append(f"words-repeat {r['lexical_recurrence']}")
            if r.get("recurrence") is not None:
                bits.append(f"chroma-repeat {r['recurrence']}")
            if r.get("recurrence_penalty"):
                bits.append(f"same-song penalty −{r['recurrence_penalty']}")
            return f'{fmt_t(r["at_s"])} ({", ".join(bits)})'
        L += ["", f"Auto split (threshold {curves['threshold']}, chroma-repeat baseline {curves['recurrence_base']}). "
              "Chosen joins: " + ", ".join(ev(r) for r in curves["chosen"]),
              "", "Strongest rejected candidates (check overview.png; fix with segments.yaml): " +
              ", ".join(ev(r) for r in curves["top_rejected"][:8])]
    open(os.path.join(args.out, "report.md"), "w").write("\n".join(L) + "\n")
    log("done ->", args.out)


if __name__ == "__main__":
    main()

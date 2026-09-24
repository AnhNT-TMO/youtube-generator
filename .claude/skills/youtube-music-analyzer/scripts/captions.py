#!/usr/bin/env python3
"""Per-track vocal statistics from YouTube (auto) captions.

  captions.py captions.en.vtt analysis.json

Adds to each track in analysis.json:  vocals = {first_line_s, words_per_min_sung, caption_lines}
and prints a small table. Deliberately does NOT store the lyric text itself: only "where does the first lyric
come / how wordy", never a copy of someone else's lyrics. Auto-captions on sung music are approximate (+-2 s).

Also importable: parse_vtt() and lexical_recurrence() are used by analyze_audio.py as evidence
for song boundaries (the words change completely when a new song starts).
"""
import bisect
import collections
import json
import math
import re
import sys

STOP = set("""a an the and or but if then so of to in on at by for with from up down out over under is are was were be
been being am i me my mine you your yours he him his she her it its we us our they them their this that these those
there here what when where who why how all any each no not only own same than too very can will just don dont should
now oh ooh yeah yea ah hey la na mm hmm im ive ill youre its thats gonna wanna gotta let lets do does did got get
one more every through into as like cause cuz ever never always still again yes music applause singing
hes shes theyre were weve youve youll hell well id wed youd theres whats cant wont didnt doesnt isnt aint
know said say see come came go going gone make made take""".split())


def _clean(text):
    text = re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", text)          # inline [singing], (music)
    return re.sub(r"\s+", " ", text).strip()


def parse_vtt(path):
    """Return [(start, end, text)] with YouTube's rolling-caption duplication removed."""
    cues, seen = [], set()
    block = open(path, encoding="utf-8").read().split("\n\n")
    ts = re.compile(r"(\d+):(\d+):(\d+\.\d+) --> (\d+):(\d+):(\d+\.\d+)")
    for b in block:
        m = ts.search(b)
        if not m:
            continue
        s = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])
        e = int(m[4]) * 3600 + int(m[5]) * 60 + float(m[6])
        lines = [re.sub(r"<[^>]+>", "", l).strip() for l in b.split("\n")[1:] if "-->" not in l]
        lines = [l for l in lines if l]
        if not lines:
            continue
        text = _clean(lines[-1])
        if not text or text in seen:
            continue
        seen.add(text)
        cues.append((s, e, text))
    return cues


def tokens(text):
    """Lower-case content words; contractions folded ("he's" -> dropped, "everything's" -> "everything")."""
    out = []
    for w in re.findall(r"[a-z']+", text.lower().replace("’", "'")):
        w = re.sub(r"'(s|re|ve|ll|d|m|t)$", "", w).replace("'", "")
        if len(w) > 2 and w not in STOP:
            out.append(w)
    return out


_IDX = {}


def _window(cues, a, b):
    """Cues starting in [a, b), via bisect on a cached start index (cues are in time order)."""
    k = id(cues)
    if k not in _IDX:
        _IDX[k] = [c[0] for c in cues]
    st = _IDX[k]
    return cues[bisect.bisect_left(st, a - 1e-9): bisect.bisect_left(st, b)]


def lexical_recurrence(cues, t, q=60.0, back=240.0):
    """How much the words right after t already occurred in the 4 min before it (and vice versa):
    max of the two TF cosines. Inside one song the chorus comes back (vintagegospel mix: 0.18-0.59);
    across a real join the new song's words are new (0.01-0.22). None = too few words."""
    def tf(a, b):
        return collections.Counter(w for s, e, x in _window(cues, a, b) for w in tokens(x))

    def cos(p, r):
        if sum(p.values()) < 4 or sum(r.values()) < 4:
            return None
        dot = sum(p[w] * r.get(w, 0) for w in p)
        na = math.sqrt(sum(v * v for v in p.values())) or 1
        nb = math.sqrt(sum(v * v for v in r.values())) or 1
        return dot / (na * nb)
    vals = [v for v in (cos(tf(t, t + q), tf(t - back, t)), cos(tf(t - q, t), tf(t, t + back))) if v is not None]
    return round(max(vals), 3) if vals else None


def main():
    vtt, analysis = sys.argv[1], sys.argv[2]
    cues = parse_vtt(vtt)
    A = json.load(open(analysis))
    tracks = A["tracks"]
    ends = [t["start_s"] for t in tracks[1:]] + [A["video"].get("duration") or 1e9]
    for t, end in zip(tracks, ends):
        cs = [c for c in cues if t["start_s"] <= c[0] < end]
        words = [w for c in cs for w in re.findall(r"[a-z']+", c[2].lower())]
        # first caption with >= 3 words = first real lyric line (a lone "Oh" is an ad-lib)
        line = next((c for c in cs if len(c[2].split()) >= 3), None)
        sung = (min(cs[-1][1], end) - line[0]) if line else 0      # first lyric line -> last caption = sung span
        t["vocals"] = {
            "first_line_s": round(line[0] - t["start_s"], 1) if line else None,
            "words_per_min_sung": round(len(words) / sung * 60, 1) if sung > 30 else None,
            "caption_lines": len(cs),
        }
    A["vocals_source"] = {"captions_file": vtt, "cues": len(cues)}
    json.dump(A, open(analysis, "w"), indent=1, ensure_ascii=False)
    v1 = tracks[0]["vocals"]
    print(f"**Song 1 = video opening: first lyric line (>=3 words) {v1['first_line_s']} s** "
          "(Demucs first sung sound, hums included, is in qc.json).\n")
    print("| # | first line | words / sung min | caption lines |")
    print("|---|---|---|---|")
    for t in tracks:
        v = t["vocals"]
        print(f"| {t['n']} | {v['first_line_s']}s | {v['words_per_min_sung']} | {v['caption_lines']} |")


if __name__ == "__main__":
    main()

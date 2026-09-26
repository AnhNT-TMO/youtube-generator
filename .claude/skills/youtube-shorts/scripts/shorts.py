#!/usr/bin/env python3
USAGE = """youtube-shorts: cut a Short from one song of an album (python3 stdlib only, runs on this Mac).

  shorts.py new   <album dir> --slot N --role A|B [--related <album|single dir>]
                                  → channel/<ch>/shorts/NNN-slug/short.md (template templates/short.md)
  shorts.py pick  <short dir> [--pick K] [--length MIN-MAX]
                                  điệp khúc: lời bài (track .md) dóng với timestamp Whisper đã có (cache verification-audio)
                                  → bảng ứng viên + <short>/short.json (audio, in/out, lời theo câu, hook, CTA)
  shorts.py check <short dir>     short.md, short.json, youtube.md (title, hashtags, link video đích), thumbnail 9:16,
                                  video đã render (video/video.mp4.json); exit 1 khi có ❌
  shorts.py list  --channel <ch>  mọi Short của kênh: bài, video đích, độ dài, trạng thái

Chạy từ gốc repo.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from difflib import SequenceMatcher
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
TEMPLATE = REPO / "templates" / "short.md"
VERIFY_CACHE = REPO / ".claude" / "skills" / "verification-audio" / ".cache" / "features"
DEFAULT_LENGTH = (25.0, 65.0)
PRE_ROLL = 0.25
MAX_TAIL = 2.5
FADE_OUT = 0.6
CTA_SECONDS = 4.0
HOLD = 1.2
WORD_MAX = 1.2
MAX_GAP = 6.0
MIN_LENGTH = 20.0
KEEP_GAP = 4.0
TITLE_MAX = 100
TITLE_WARN = 60
HASHTAGS_MAX = 15
TAGS_MAX = 500
INSTRUMENTAL = ("instrumental", "intro", "outro", "break", "solo", "interlude", "end")
DIRECTION_WORDS = ("enters", "keep the", "gradually", "no additional", "no dramatic", "let the", "leave only",
                   "organ", "guitar", "choir", "drums", "piano", "vocal", "harmony", "sustain", "unhurried")


def rel(p):
    try:
        return str(Path(p).resolve().relative_to(REPO))
    except ValueError:
        return str(p)


def die(msg):
    sys.exit(f"❌ {msg}")


def front_matter(path):
    text = Path(path).read_text()
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    fm = {}
    if not m:
        return fm
    for line in m.group(1).splitlines():
        if not line or line.startswith((" ", "#")):
            continue
        k, sep, v = line.partition(":")
        if not sep:
            continue
        v = re.sub(r"\s+#.*$", "", v).strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        fm[k.strip()] = v
    return fm


def set_fields(path, values):
    text = Path(path).read_text()
    for k, v in values.items():
        if isinstance(v, str):
            val = json.dumps(v, ensure_ascii=False) if re.search(r"[:#\"']|^\s|\s$", v) or not v else v
        else:
            val = json.dumps(v, ensure_ascii=False) if isinstance(v, list) else ("" if v is None else str(v))
        pat = re.compile(rf"^{re.escape(k)}:[^\n]*?(\s+#[^\n]*)?$", re.M)
        m = pat.search(text)
        if m:
            text = text[:m.start()] + f"{k}: {val}" + (m.group(1) or "") + text[m.end():]
        else:
            text = text.replace("\n---", f"\n{k}: {val}\n---", 1)
    Path(path).write_text(text)


def channel_of(d):
    parts = Path(d).resolve().relative_to(REPO).parts
    if len(parts) < 2 or parts[0] != "channel":
        die(f"{d}: phải nằm trong channel/<ch>/")
    return REPO / "channel" / parts[1]


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower().replace("’", "'").replace("'", "")).strip("-")


def track_file(album, slot):
    hits = sorted((Path(album) / "tracks").glob(f"{slot:02d}-*.md"))
    hits = [h for h in hits if h.name.count(".") == 1]
    if not hits:
        die(f"không có tracks/{slot:02d}-*.md trong {rel(album)}")
    return hits[0]


def track_audio(track_md):
    fm = front_matter(track_md)
    a = fm.get("audio")
    if not a:
        die(f"{rel(track_md)} chưa có `audio:` (bài chưa accept?)")
    album = Path(track_md).resolve().parent.parent
    cands = [album / a]
    if fm.get("origin_album"):
        cands.append(album.parent / fm["origin_album"] / a)
    for c in cands:
        if c.exists():
            return c
    die(f"không thấy audio {a} của {rel(track_md)}")


def youtube_url(d):
    f = Path(d) / "youtube.md"
    if not f.exists():
        return None
    m = re.search(r"\*\*Video URL:\*\*[ \t]*(\S*)", f.read_text())
    url = m.group(1) if m else ""
    return url if url.startswith("http") else None


def cmd_new(a):
    album = Path(a.album).resolve()
    ch = channel_of(album)
    track = track_file(album, a.slot)
    fm = front_matter(track)
    related = Path(a.related).resolve() if a.related else album
    if not (related / "youtube.md").exists() and not (related / "single.md").exists():
        print(f"⚠️  {rel(related)} chưa có youtube.md/single.md: nhớ tạo video đích trước khi đăng Short")
    root = ch / "shorts"
    root.mkdir(exist_ok=True)
    nums = [int(p.name[:3]) for p in root.iterdir() if p.is_dir() and p.name[:3].isdigit()]
    d = root / f"{max(nums or [0]) + 1:03d}-{slugify(fm.get('title', track.stem))}"
    d.mkdir()
    text = TEMPLATE.read_text()
    text = text.replace("<Song Title>", fm.get("title", track.stem)).replace("<role>", a.role)
    (d / "short.md").write_text(text)
    set_fields(d / "short.md", {
        "album": album.name,
        "track": os.path.relpath(track, d),
        "role": a.role,
        "related_video": os.path.relpath(related, d),
        "length": list(DEFAULT_LENGTH),
    })
    print(f"✔ {rel(d)}/short.md · bài {fm.get('title')} · video đích {rel(related)}")


def file_key(path):
    size = path.stat().st_size
    h = hashlib.sha1(str(size).encode())
    with open(path, "rb") as f:
        h.update(f.read(1 << 20))
        if size > (2 << 20):
            f.seek(-(1 << 20), os.SEEK_END)
            h.update(f.read(1 << 20))
    return h.hexdigest()[:16]


def with_ends(words):
    out = []
    for i, w in enumerate(words):
        nxt = words[i + 1]["s"] if i + 1 < len(words) else w["s"] + WORD_MAX
        out.append({"w": w["w"], "s": w["s"], "e": w.get("e") or min(nxt - 0.05, w["s"] + WORD_MAX),
                    "p": w.get("p")})
    return out


def whisper_words(audio):
    d = VERIFY_CACHE / file_key(audio)
    for name in ("lyrics_mix.json", "lyrics.json"):
        f = d / name
        if f.exists():
            words = json.loads(f.read_text()).get("words") or []
            if words:
                return with_ends(words), name
    die(f"chưa có timestamp Whisper cho {rel(audio)} (cache verification-audio {rel(d)}): chạy verification-audio "
        "`verify.py check` cho album đó trên server rồi `remote.sh pull`, xong chạy lại pick")


def lyric_sections(track_md):
    text = Path(track_md).read_text()
    m = re.search(r"^##\s+Lyrics.*?$(.*)", text, re.M | re.S)
    b = re.search(r"```[a-z]*\n(.*?)```", m.group(1), re.S) if m else None
    if not b:
        die(f"{rel(track_md)} không có khối lời trong ## Lyrics")
    sections, cur = [], None
    for raw in b.group(1).splitlines():
        line = raw.strip()
        if not line:
            continue
        tag = re.fullmatch(r"\[(.*)\]", line)
        if tag:
            name = tag.group(1).split(":")[0].strip().lower()
            cur = {"tag": name, "lines": [], "instrumental": any(k in name for k in INSTRUMENTAL)}
            sections.append(cur)
            continue
        if cur is None:
            cur = {"tag": "verse", "lines": [], "instrumental": False}
            sections.append(cur)
        low = line.lower()
        if cur["instrumental"] or (line.endswith(".") and any(w in low for w in DIRECTION_WORDS)):
            continue
        if re.fullmatch(r"\(.*\)", line):
            continue
        cur["lines"].append(line)
    return [s for s in sections if s["lines"]]


def norm(text):
    text = text.lower().replace("’", "'")
    return [t for t in re.sub(r"[^a-z' ]+", " ", text).split() if t]


def align(sections, words):
    toks = [(norm(w["w"]) or [""])[0] for w in words]
    out, cur = [], 0
    for si, sec in enumerate(sections):
        for li, line in enumerate(sec["lines"]):
            lt = norm(line)
            n = len(lt)
            best, bi, bj = 0.0, None, None
            for i in range(cur, min(len(toks), cur + 80)):
                for m in (n - 1, n, n + 1, n + 2):
                    if m <= 0 or i + m > len(toks):
                        continue
                    r = SequenceMatcher(None, lt, toks[i:i + m]).ratio()
                    if r > best:
                        best, bi, bj = r, i, i + m - 1
            row = {"sec": si, "tag": sec["tag"], "line": li, "text": line, "ratio": round(best, 2)}
            if best >= 0.55:
                probs = [words[k]["p"] for k in range(bi, bj + 1) if words[k].get("p") is not None]
                row.update(s=words[bi]["s"], e=words[bj]["e"], wi=bi, wj=bj,
                           p=sum(probs) / len(probs) if probs else best)
                cur = bj + 1
            out.append(row)
    return out


def chorus_sections(sections, hook):
    idx = [i for i, s in enumerate(sections) if "chorus" in s["tag"] or "refrain" in s["tag"]]
    if idx:
        return idx
    h = norm(hook or "")
    if h:
        idx = [i for i, s in enumerate(sections)
               if any(SequenceMatcher(None, h, norm(l)).ratio() > 0.8 for l in s["lines"])]
    if idx:
        return idx
    first = {}
    for i, s in enumerate(sections):
        first.setdefault(tuple(s["lines"][:1]), []).append(i)
    rep = max(first.values(), key=len)
    return rep if len(rep) > 1 else [0]


def candidates(sections, rows, words, lo, hi, content_end, hook=None):
    starts = chorus_sections(sections, hook)
    got = [r for r in rows if "s" in r]
    out = []
    for k, si in enumerate(starts):
        first = next((r for r in got if r["sec"] == si), None)
        if not first:
            continue
        prev_end = max([w["e"] for w in words if w["e"] <= first["s"]] or [0.0])
        t_in = max(prev_end + 0.05, first["s"] - PRE_ROLL, 0.0)
        after = [r for r in got if r["s"] >= first["s"]]
        chorus_rows = [r for r in after if r["sec"] == si]
        best = None
        for j, r in enumerate(after):
            if j and r["s"] - after[j - 1]["e"] > MAX_GAP:
                break
            ends_section = j + 1 >= len(after) or after[j + 1]["sec"] != r["sec"]
            if not ends_section:
                continue
            nxt = next((w["s"] for w in words if w["s"] > r["e"] + 0.05), content_end)
            tail = max(0.0, min(MAX_TAIL, nxt - r["e"] - 0.3))
            t_out = min(r["e"] + tail + FADE_OUT * 0.5, content_end)
            dur = t_out - t_in
            if dur > hi:
                break
            if dur < MIN_LENGTH:
                continue
            lines = after[:j + 1]
            complete = all(x in lines for x in chorus_rows) and len(chorus_rows) == len(sections[si]["lines"])
            fits = lo <= dur <= hi
            score = (2.0 * complete + 1.0 * fits + min(nxt - r["e"], 2.0) / 2.0
                     + sum(x["p"] for x in lines) / len(lines) - 0.15 * k)
            cand = {"section": si, "tag": sections[si]["tag"], "in": round(t_in, 2), "out": round(t_out, 2),
                    "dur": round(dur, 1), "lines": lines, "ends_section": True, "fits": fits,
                    "gap_after": round(nxt - r["e"], 2), "chorus_complete": complete, "score": round(score, 2)}
            if best is None or score >= best["score"]:
                best = cand
        if best:
            best["k"] = len(out) + 1
            out.append(best)
    return out


def captions(cand):
    lines = cand["lines"]
    total = cand["out"] - cand["in"]
    caps = []
    for i, r in enumerate(lines):
        t0 = max(0.0, r["s"] - cand["in"] - 0.1)
        if i + 1 < len(lines):
            nxt = lines[i + 1]["s"] - cand["in"] - 0.1
            t1 = nxt if nxt - (r["e"] - cand["in"]) <= KEEP_GAP else r["e"] - cand["in"] + HOLD
        else:
            t1 = total
        caps.append({"t0": round(t0, 2), "t1": round(max(t1, t0 + 0.8), 2), "text": r["text"]})
    return caps


def parse_length(v):
    if isinstance(v, str) and "-" in v and not v.startswith("["):
        lo, hi = v.split("-")
        return float(lo), float(hi)
    try:
        lo, hi = json.loads(v) if isinstance(v, str) else v
        return float(lo), float(hi)
    except (ValueError, TypeError):
        return DEFAULT_LENGTH


def content_end_of(audio):
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                              str(audio)], capture_output=True, text=True, check=True).stdout
        return float(out.strip())
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        return 1e9


def cmd_pick(a):
    d = Path(a.dir).resolve()
    sm = d / "short.md"
    if not sm.exists():
        die(f"{rel(sm)} chưa có: `shorts.py new` trước")
    fm = front_matter(sm)
    track = (d / fm["track"]).resolve()
    tfm = front_matter(track)
    audio = track_audio(track)
    words, src = whisper_words(audio)
    sections = lyric_sections(track)
    rows = align(sections, words)
    lo, hi = parse_length(a.length or fm.get("length") or "")
    cands = candidates(sections, rows, words, lo, hi, content_end_of(audio), tfm.get("hook_phrase"))
    matched = sum("s" in r for r in rows)
    print(f"bài: {tfm.get('title')} · {rel(audio)} · Whisper {src}: {len(words)} chữ · dóng được {matched}/{len(rows)} "
          f"dòng lời · độ dài {lo:.0f}–{hi:.0f} s")
    if not cands:
        die("không có đoạn điệp khúc nào vừa độ dài: đổi `length:` trong short.md hoặc --length")
    print("\n| # | bắt đầu ở | in → out | dài | trọn điệp khúc | vừa độ dài | lặng sau | dòng cuối | điểm |\n"
          "|---|---|---|---|---|---|---|---|---|")
    for c in cands:
        print(f"| {c['k']} | {c['tag']} (§{c['section'] + 1}) | {c['in']:.2f} → {c['out']:.2f} | {c['dur']} s | "
              f"{'✔' if c['chorus_complete'] else '—'} | {'✔' if c['fits'] else '—'} | {c['gap_after']} s | "
              f"{c['lines'][-1]['text'][:28]} | {c['score']} |")
    want = a.pick or (int(fm["pick"]) if fm.get("pick", "").isdigit() else None)
    chosen = next((c for c in cands if c["k"] == want), None) if want else max(cands, key=lambda c: c["score"])
    if not chosen:
        die(f"không có ứng viên #{want}")
    caps = captions(chosen)
    dur = chosen["out"] - chosen["in"]
    spec = {"audio": rel(audio), "track": rel(track), "in": chosen["in"], "out": chosen["out"],
            "fade_in": 0.03, "fade_out": FADE_OUT, "captions": caps,
            "hook": {"text": fm.get("hook_text", "")}, "cta": {"text": fm.get("cta_text", ""),
                                                              "t0": round(dur - CTA_SECONDS, 2)},
            "picked": chosen["k"], "whisper": src}
    (d / "short.json").write_text(json.dumps(spec, indent=1, ensure_ascii=False))
    set_fields(sm, {"segment": f"{chosen['in']:.2f}-{chosen['out']:.2f}"})
    print(f"\n→ chọn #{chosen['k']}: {chosen['in']:.2f} → {chosen['out']:.2f} ({dur:.1f} s), giọng vào ở "
          f"{caps[0]['t0']:.2f} s · {len(caps)} dòng lời → {rel(d / 'short.json')}")
    for c in caps:
        print(f"   {c['t0']:6.2f}–{c['t1']:6.2f}  {c['text']}")
    for k in ("hook_text", "cta_text"):
        if not fm.get(k):
            print(f"⚠️  short.md chưa có {k}: viết rồi chạy lại pick (short.json lấy chữ từ short.md)")


def code_block(text, heading):
    i = text.find(heading)
    if i < 0:
        return None
    m = re.search(r"```[a-z]*\n(.*?)\n```", text[i:], re.S)
    return m.group(1) if m else None


def image_dims(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                          "-of", "csv=p=0:s=x", str(path)], capture_output=True, text=True).stdout.strip()
    try:
        w, h = out.split("x")
        return int(w), int(h)
    except ValueError:
        return None


def cmd_check(a):
    d = Path(a.dir).resolve()
    err, warn = [], []
    sm = d / "short.md"
    if not sm.exists():
        die(f"{rel(sm)} chưa có")
    fm = front_matter(sm)
    for k in ("album", "track", "role", "related_video", "hook_text", "cta_text"):
        if not fm.get(k):
            err.append(f"short.md thiếu {k}")
    related = (d / fm.get("related_video", "")).resolve() if fm.get("related_video") else None
    url = youtube_url(related) if related else None
    if related and not url:
        warn.append(f"video đích {rel(related)} chưa có Video URL trong youtube.md: upload video đích trước, "
                    "rồi điền link vào description + pinned comment của Short")
    spec_f = d / "short.json"
    if spec_f.exists():
        spec = json.loads(spec_f.read_text())
        dur = spec["out"] - spec["in"]
        if not 5 <= dur <= 180:
            err.append(f"độ dài {dur:.1f} s ngoài 5–180 s (quá 180 s YouTube không coi là Short)")
        if spec["captions"] and spec["captions"][0]["t0"] > 1.0:
            err.append(f"giọng vào ở {spec['captions'][0]['t0']:.2f} s: phải ≤ 1 s (người xem quyết định trong ~1 s)")
        if spec["hook"].get("text") != fm.get("hook_text") or spec["cta"].get("text") != fm.get("cta_text"):
            err.append("short.json khác hook_text/cta_text trong short.md: chạy lại `shorts.py pick`")
    else:
        err.append("chưa có short.json: `shorts.py pick`")
        dur = None
    thumb = d / "thumbnail.png"
    dims = image_dims(thumb) if thumb.exists() else None
    if not dims:
        err.append("chưa có thumbnail.png (ảnh dọc: skill thumbnail-prompt)")
    elif abs(dims[0] / dims[1] - 9 / 16) > 0.01:
        err.append(f"thumbnail.png {dims[0]}×{dims[1]} không phải 9:16")
    probe = d / "video" / "video.mp4.json"
    if probe.exists():
        p = json.loads(probe.read_text())
        v = next((s for s in p["streams"] if s["codec_type"] == "video"), {})
        vd = float(p["format"]["duration"])
        if (v.get("width"), v.get("height")) != (1080, 1920):
            err.append(f"video {v.get('width')}×{v.get('height')}, không phải 1080×1920")
        if vd > 180:
            err.append(f"video dài {vd:.1f} s > 180 s")
        if dur and abs(vd - dur) > 0.5:
            warn.append(f"video {vd:.1f} s ≠ short.json {dur:.1f} s: render lại (`video.py short`)")
        if not any(s["codec_type"] == "audio" for s in p["streams"]):
            err.append("video không có audio")
    else:
        warn.append("chưa render video (`video.py short <short>`)")
    ym = d / "youtube.md"
    if ym.exists():
        text = ym.read_text()
        title, desc = code_block(text, "## Title"), code_block(text, "## Description")
        tags, pin = code_block(text, "## Tags"), code_block(text, "## Pinned comment")
        for name, v in (("Title", title), ("Description", desc), ("Tags", tags), ("Pinned comment", pin)):
            if not v:
                err.append(f"youtube.md thiếu khối ``` dưới ## {name}")
        if title:
            t = title.strip()
            if len(t) > TITLE_MAX:
                err.append(f"title {len(t)} ký tự > {TITLE_MAX}")
            elif len(t) > TITLE_WARN:
                warn.append(f"title {len(t)} ký tự: Shorts feed chỉ hiện ~{TITLE_WARN}")
            if "<" in t:
                err.append("title còn placeholder <...>")
        if desc:
            tags_in = re.findall(r"(?<!\w)#\w+", desc)
            if len(tags_in) > HASHTAGS_MAX:
                err.append(f"{len(tags_in)} hashtag > {HASHTAGS_MAX}")
            elif not 3 <= len(tags_in) <= 5:
                warn.append(f"{len(tags_in)} hashtag: nên 3–5, đúng chủ đề")
            if re.search(r"<[^>\n]+>", desc):
                err.append("description còn placeholder <...>")
            if url and url not in desc:
                err.append(f"description chưa có link video đích {url}")
            if re.search(r"\b(AI[- ]generated|made with AI|Suno)\b", desc, re.I):
                err.append("description có dòng AI/Suno: khai báo AI bằng mục Altered content trong Studio")
        if pin and url and url not in pin:
            warn.append("pinned comment chưa có link video đích")
        if tags and len(tags.strip()) > TAGS_MAX:
            err.append(f"tags {len(tags.strip())} ký tự > {TAGS_MAX}")
    else:
        err.append("chưa có youtube.md (mẫu templates/youtube-short.md)")
    for x in warn:
        print(f"⚠️  {x}")
    for x in err:
        print(f"❌ {x}")
    if not err:
        print("✅ Short sẵn sàng (vẫn phải NHÌN check_hook/mid/cta.png: chữ không đè mặt, đọc được ở cỡ điện thoại)")
    sys.exit(1 if err else 0)


def cmd_list(a):
    root = REPO / "channel" / a.channel / "shorts"
    if not root.is_dir():
        print("chưa có Short nào")
        return
    print("| Short | role | bài | video đích | đoạn | ảnh | video | S3 | URL |\n|---|---|---|---|---|---|---|---|---|")
    for d in sorted(p for p in root.iterdir() if (p / "short.md").exists()):
        fm = front_matter(d / "short.md")
        track = (d / fm.get("track", "")).resolve()
        title = front_matter(track).get("title", "?") if track.exists() else "?"
        related = (d / fm.get("related_video", "")).resolve() if fm.get("related_video") else None
        print(f"| {d.name} | {fm.get('role', '')} | {title} | {related.name if related else '—'} | "
              f"{fm.get('segment') or '—'} | {'✔' if (d / 'thumbnail.png').exists() else '—'} | "
              f"{'✔' if (d / 'video' / 'video.mp4.json').exists() else '—'} | "
              f"{'✔' if (d / 's3-package.json').exists() else '—'} | {youtube_url(d) or '—'} |")


def main():
    ap = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("new")
    p.add_argument("album")
    p.add_argument("--slot", type=int, required=True)
    p.add_argument("--role", choices=["A", "B"], required=True)
    p.add_argument("--related", help="thư mục video đích (mặc định: album)")
    p = sub.add_parser("pick")
    p.add_argument("dir")
    p.add_argument("--pick", type=int, help="số ứng viên trong bảng (mặc định: điểm cao nhất)")
    p.add_argument("--length", help="MIN-MAX giây, vd. 40-65 (mặc định: short.md length)")
    p = sub.add_parser("check")
    p.add_argument("dir")
    p = sub.add_parser("list")
    p.add_argument("--channel", required=True)
    a = ap.parse_args()
    {"new": cmd_new, "pick": cmd_pick, "check": cmd_check, "list": cmd_list}[a.cmd](a)


if __name__ == "__main__":
    main()

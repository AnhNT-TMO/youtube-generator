#!/usr/bin/env python3
USAGE = """audio-song-naming: tên bài lấy từ lời + mỗi clip một đoạn Short. Một lượt Suno ra 2 clip:
cùng lời (≥ 0.8) = MỘT bài, 2 bản v1 / v2 cùng tên: songs/<type>/<tên>_v1.* / <tên>_v2.* (v1 = clip đầu của lượt trong
songs/manifest.json); khác lời = 2 bài riêng, mỗi bài một tên từ lời của nó: songs/<type>/<tên>.* (không _vN, version null).

  songs.py list       --channel <ch>                    clip thô chưa tên (raw/, tỉ lệ lời giống bản kia) + bài đã tên + clip bỏ
  songs.py words      --channel <ch> [--clip ID8 …] [--force]
                                                        Whisper timestamp từng chữ cho mọi clip chưa tên, MỘT job
                                                        trên GPU server → songs/.cache/words/<id8>.json
  songs.py candidates <id8> [--channel <ch>]            lời theo dòng (t0/t1, đọc/hát), cùng bài hay bài riêng với bản kia
                                                        + các đoạn Short xếp hạng, mỗi đoạn một khóa L<dòng đầu>-L<dòng cuối>
  songs.py name       <id8> --title "<Title>" --short L12-L19 [--hook "<dòng>"] [--why "<…>"] [--channel <ch>]
                                                        raw/<id8>.wav → songs/<type>/<slug>_vN.* (cùng lời, --title phải
                                                        đúng tên bản kia nếu nó đã tên) hoặc songs/<type>/<slug>.* (bài riêng)
  songs.py drop       <id8> --reason "<…>" [--channel <ch>] | <id8> --undo
                                                        clip hỏng/không dùng: raw/<id8>.wav → raw/dropped/, ghi songs/dropped.json
  songs.py rename     <slug> --title "<New Title>" [--update-albums] [--channel <ch>]
                                                        đổi tên cả bài: mọi bản cùng lời của lượt (file, card, sibling)
  songs.py catalog    --channel <ch>                    → songs/catalog.md (nhóm theo type, các bản đứng cạnh nhau)
  songs.py migrate    --channel <ch> [--yes]            bài bố cục cũ songs/<slug>.* → songs/<type>/ + sửa đường dẫn trong
                                                        albums/*/tracks, assembly.json, albums/*/short/ (và shorts/*/ cũ)
                                                        short.md + short.json
                                                        (mặc định chỉ in thay đổi; --yes mới làm)

Chạy từ gốc repo: .claude/skills/audio-song-naming/.venv/bin/python .claude/skills/audio-song-naming/scripts/songs.py …
Không bao giờ ghi songs/manifest.json hay file trong raw/ (của audio-suno-generate); chỉ chuyển raw/<id8>.wav khi đặt tên
hoặc drop.
"""
import argparse
import json
import os
import re
import shlex
import struct
import subprocess
import sys
import time
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path

import yaml

SKILL = Path(__file__).resolve().parents[1]
REPO = SKILL.parents[2]
REMOTE_SH = SKILL / "scripts" / "remote.sh"
TEMPLATE = REPO / "templates" / "song.md"
PHRASE_BANK = REPO / "research" / "phrase-bank"
ID8 = re.compile(r"[0-9a-f]{8}")
SETTLE_S = 5.0
DURATION_TOL_S = 1.5
LINE_MATCH = 0.55
GOOD_MATCH = 0.8
SEARCH_AHEAD = 80
PRE_ROLL = 0.25
MAX_TAIL = 2.5
FADE_OUT = 0.6
EST_PENALTY = 0.2
TITLE_SMALL_WORDS = {"a", "an", "and", "as", "at", "but", "by", "for", "from", "in", "into", "nor", "of", "on", "or",
                     "over", "the", "to", "up", "with"}
SHORT_KEY = re.compile(r"L(\d+)-L(\d+)", re.I)
SHOW = 8
SAME_LYRICS = 0.8
NOT_TYPE_DIRS = {"raw"}
RULE_DEFAULTS = {"short_length_s": [30, 60], "short_pre_roll_s": 1.0, "short_max_gap_s": 6.0}
INSTRUMENTAL = ("instrumental", "break", "solo", "interlude")
SPOKEN = ("spoken", "speak", "narrat", "recit", "monolog")
CHORUS = ("chorus", "refrain", "hook")


def die(msg, code=1):
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(code)


def rel(p):
    return os.path.relpath(Path(p).absolute(), REPO)


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower().replace("’", "'").replace("'", "")).strip("-")


def norm(text):
    text = str(text).lower().replace("’", "'")
    return [t for t in re.sub(r"[^a-z' ]+", " ", text).split() if t]


def mmss(s):
    return "—" if s is None else f"{int(s // 60)}:{int(s % 60):02d}"


def r2(x):
    return None if x is None else round(float(x), 2)


def split_front(text):
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    return (m.group(1), m.group(2)) if m else ("", text)


def front_matter(path):
    head, _ = split_front(Path(path).read_text())
    return (yaml.safe_load(head) or {}) if head else {}


def scalar(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return repr(round(v, 3))
    if isinstance(v, int):
        return str(v)
    s = str(v)
    try:
        plain = yaml.safe_load(s) == s and "#" not in s and "\n" not in s and not s[:1] in "'\"{[&*!|>%@`-?:,"
    except yaml.YAMLError:
        plain = False
    return s if plain else json.dumps(s, ensure_ascii=False)


def quoted(s):
    return json.dumps(str(s), ensure_ascii=False)


def set_field(text, key, value):
    head, body = split_front(text)
    line = f"{key}: {scalar(value)}"
    head, n = re.subn(rf"^{re.escape(key)}:.*$", lambda _: line, head, count=1, flags=re.M)
    if not n:
        head += "\n" + line
    return f"---\n{head}\n---\n{body}"


def lyrics_block(text):
    m = re.search(r"^##\s+Lyrics.*?$(.*)", text, re.M | re.S)
    b = re.search(r"```[a-z]*\n(.*?)```", m.group(1), re.S) if m else None
    return b.group(1) if b else None


def lyric_words(text):
    return [t for line in str(text).splitlines() if not re.fullmatch(r"\s*\[.*\]\s*", line) for t in norm(line)]


def lyrics_ratio(a, b):
    a, b = lyric_words(a), lyric_words(b)
    return round(max(SequenceMatcher(None, a, b, autojunk=False).ratio(),
                     SequenceMatcher(None, b, a, autojunk=False).ratio()), 2)


def wav_info(path):
    try:
        size = path.stat().st_size
        with open(path, "rb") as f:
            head = f.read(12)
            if len(head) < 12:
                return None, "đang tải (chưa có header)"
            riff, rsize, wave = struct.unpack("<4sI4s", head)
            if riff != b"RIFF" or wave != b"WAVE":
                return None, "không phải WAV RIFF"
            if size < rsize + 8:
                return None, f"đang tải ({size}/{rsize + 8} byte)"
            pos, fmt = 12, None
            while pos + 8 <= size:
                f.seek(pos)
                cid, cs = struct.unpack("<4sI", f.read(8))
                if cid == b"fmt ":
                    fmt = struct.unpack("<HHIIHH", f.read(16))
                elif cid == b"data":
                    if not fmt:
                        return None, "WAV thiếu chunk fmt"
                    if pos + 8 + cs > size:
                        return None, "đang tải (chunk data chưa đủ)"
                    return {"duration_s": cs / (fmt[2] * fmt[4]), "size": size}, None
                pos += 8 + cs + (cs & 1)
    except OSError as e:
        return None, str(e)
    return None, "WAV thiếu chunk data"


class Pool:
    def __init__(self, ch):
        self.ch = ch
        self.dir = REPO / "channel" / ch / "songs"
        if not self.dir.is_dir():
            die(f"không có {rel(self.dir)}")
        self.raw = self.dir / "raw"
        self.words_dir = self.dir / ".cache" / "words"
        self.dropped_file = self.dir / "dropped.json"
        self.dropped_dir = self.raw / "dropped"
        self.cards = {}
        self.gens = None
        self._dropped = None

    def dropped(self):
        if self._dropped is None:
            try:
                self._dropped = json.loads(self.dropped_file.read_text()) if self.dropped_file.exists() else {}
            except (json.JSONDecodeError, OSError) as e:
                die(f"{rel(self.dropped_file)} không đọc được ({e}): chỉ songs.py ghi file này, sửa lại cho đúng JSON")
        return self._dropped

    def save_dropped(self, data):
        self.dropped_file.write_text(json.dumps(dict(sorted(data.items())), indent=1, ensure_ascii=False) + "\n")
        self._dropped = data

    def lyrics_of(self, id8, named):
        f = self.raw / f"{id8}.lyrics.txt"
        if f.exists() and f.read_text().strip():
            return f.read_text()
        slug = next((s for s, fm in named.items() if str(fm.get("clip_id"))[:8] == id8), None)
        return lyrics_block(self.card(slug).read_text()) if slug else None

    def gen_ids(self, clip_id, gen, named):
        ids = [x[:8] for x in self.generation_of(clip_id)[2]]
        if not ids and gen:
            ids = sorted({str(fm.get("clip_id"))[:8] for fm in named.values() if fm.get("generation") == gen})
        return ids

    def twins(self, named, id8, clip_id=None, gen=None):
        mine = self.lyrics_of(id8, named)
        out = {"same": [], "differ": [], "unknown": [], "dropped": [], "mine": bool(mine)}
        for x in self.gen_ids(clip_id or id8, gen, named):
            if x == id8:
                continue
            if x in self.dropped():
                out["dropped"].append(x)
                continue
            other = self.lyrics_of(x, named)
            if not (mine and other):
                out["unknown"].append(x)
                continue
            r = lyrics_ratio(mine, other)
            out["same" if r >= SAME_LYRICS else "differ"].append((x, r))
        return out

    def type_dirs(self):
        return sorted(p for p in self.dir.iterdir()
                      if p.is_dir() and p.name not in NOT_TYPE_DIRS and not p.name.startswith("."))

    def card_files(self):
        legacy = sorted(p for p in self.dir.glob("*.md") if p.name != "catalog.md")
        return legacy + [p for d in self.type_dirs() for p in sorted(d.glob("*.md"))]

    def songs(self):
        out, self.cards = {}, {}
        for md in self.card_files():
            fm = front_matter(md)
            if fm.get("clip_id"):
                out[md.stem] = fm
                self.cards[md.stem] = md
        return dict(sorted(out.items(), key=lambda kv: (str(kv[1].get("type")), str(kv[1].get("generation")),
                                                        slugify(kv[1].get("title", "")), str(kv[1].get("version")), kv[0])))

    def card(self, slug):
        if slug not in self.cards:
            self.songs()
        return self.cards.get(slug)

    def wav_of(self, slug):
        card = self.card(slug)
        return card.with_suffix(".wav") if card else None

    def legacy(self, slug):
        card = self.card(slug)
        return card is not None and card.parent == self.dir

    def types(self):
        f = self.dir.parent / "prompt_suno.md"
        fm = front_matter(f) if f.exists() else {}
        return [str(t) for t in fm.get("types") or []]

    def type_problem(self, song_type):
        t, types = str(song_type or ""), self.types()
        if types and t not in types:
            return f"type {quoted(t)} không có trong prompt_suno.md types {types}"
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", t) or t in NOT_TYPE_DIRS:
            return f"type {quoted(t)} không làm tên thư mục songs/<type>/ được"
        return None

    def type_dir(self, song_type):
        problem = self.type_problem(song_type)
        if problem:
            die(problem)
        return self.dir / str(song_type)

    def occupied(self, slug):
        return [p for d in [self.dir, *self.type_dirs()] for p in (d / f"{slug}.wav", d / f"{slug}.md") if p.exists()]

    def raw_ids(self):
        if not self.raw.is_dir():
            return []
        return sorted({p.name[:8] for p in self.raw.iterdir() if ID8.fullmatch(p.name[:8]) and p.name[8:9] == "."})

    def clips(self, named=None):
        named = self.songs() if named is None else named
        return [Clip(self, i, named) for i in self.raw_ids()]

    def manifest_gen(self, clip_id):
        cid = str(clip_id or "")[:8]
        self.generation_of(cid)
        return next((g for g in self.gens if cid and any(str(x)[:8] == cid for x in g.get("clip_ids") or [])), {})

    def generation_of(self, clip_id):
        if self.gens is None:
            f = self.dir / "manifest.json"
            try:
                self.gens = json.loads(f.read_text()).get("generations") or [] if f.exists() else []
            except (json.JSONDecodeError, OSError):
                self.gens = []
        cid = str(clip_id or "")[:8]
        for g in self.gens:
            ids = [str(x) for x in g.get("clip_ids") or []]
            for i, x in enumerate(ids):
                if cid and x[:8] == cid:
                    return g.get("id"), f"v{i + 1}", ids
        return None, None, []

    def rules(self):
        f = self.dir.parent / "naming.md"
        fm = front_matter(f) if f.exists() else {}
        return {**RULE_DEFAULTS, **{k: v for k, v in fm.items() if v is not None}}


class Clip:
    def __init__(self, pool, id8, named):
        self.pool, self.id8 = pool, id8
        self.wav = pool.raw / f"{id8}.wav"
        self.json_path = pool.raw / f"{id8}.json"
        self.lyrics_path = pool.raw / f"{id8}.lyrics.txt"
        self.slug = next((s for s, fm in named.items() if str(fm["clip_id"]).startswith(id8)), None)
        self.song = named.get(self.slug) if self.slug else None
        try:
            self.meta = json.loads(self.json_path.read_text()) if self.json_path.exists() else None
        except (json.JSONDecodeError, OSError):
            self.meta = None
        src = self.song or self.meta or {}
        g = {} if src else pool.manifest_gen(id8)
        self.clip_id = str(src.get("clip_id") or "") or next((x for x in g.get("clip_ids") or [] if x[:8] == id8), None)
        gen, self.position, _ = pool.generation_of(self.clip_id or id8)
        self.generation = src.get("generation") or gen
        self.type = src.get("type") or g.get("type")
        self.drop = pool.dropped().get(id8)
        self._twins = None

    def twins(self, named):
        if self._twins is None:
            self._twins = self.pool.twins(named, self.id8, self.clip_id, self.generation)
        return self._twins

    def version(self, named):
        return self.position if self.twins(named)["same"] else None

    @property
    def audio(self):
        return self.pool.wav_of(self.slug) if self.slug else self.wav

    def lyrics(self):
        if self.lyrics_path.exists() and self.lyrics_path.read_text().strip():
            return self.lyrics_path.read_text()
        if self.slug:
            return lyrics_block(self.pool.card(self.slug).read_text())
        return None

    def problem(self, for_words=False):
        if self.drop and not self.slug:
            return f"đã bỏ ({self.drop.get('reason')}): `drop {self.id8} --undo` để lấy lại"
        if not self.audio.exists():
            return "chưa có wav"
        info, err = wav_info(self.audio)
        if err:
            return err
        if not self.slug and time.time() - self.wav.stat().st_mtime < SETTLE_S:
            return f"wav vừa ghi (< {SETTLE_S:g} s), chờ"
        if for_words or self.slug:
            return None
        if self.meta is None:
            return "chưa có raw json (Suno skill chưa ghi xong)"
        miss = [k for k in ("clip_id", "generation", "type") if not self.meta.get(k)]
        if miss:
            return f"raw json thiếu {', '.join(miss)}"
        if not (self.lyrics() or "").strip():
            return "chưa có lyrics.txt"
        want = next((self.meta[k] for k in ("file_duration", "duration_s", "duration") if self.meta.get(k)), None)
        if isinstance(want, (int, float)) and abs(info["duration_s"] - want) > DURATION_TOL_S:
            return f"wav {info['duration_s']:.1f} s ≠ raw json {want:.1f} s (đang tải?)"
        return None

    def words(self):
        f = self.pool.words_dir / f"{self.id8}.json"
        if not f.exists() or not self.audio.exists():
            return None
        d = json.loads(f.read_text())
        return d if d.get("file_size") == self.audio.stat().st_size else None


def channels():
    root = REPO / "channel"
    return sorted(p.name for p in root.iterdir() if (p / "songs").is_dir() and not p.name.startswith("."))


def find_clip(ident, ch=None):
    id8 = ident[:8].lower()
    if not ID8.fullmatch(id8):
        die(f"{ident}: cần id8 (8 ký tự hex đầu của Suno clip id)")
    hits = []
    for c in ([ch] if ch else channels()):
        pool = Pool(c)
        named = pool.songs()
        clip = Clip(pool, id8, named)
        if clip.slug or clip.wav.exists() or clip.json_path.exists() or clip.position:
            hits.append(clip)
    if not hits:
        die(f"không thấy clip {id8} trong songs/raw/ của kênh nào")
    if len(hits) > 1:
        die(f"{id8} có ở nhiều kênh ({', '.join(h.pool.ch for h in hits)}): thêm --channel")
    return hits[0]


def find_song(slug, ch=None):
    hits = [pool for pool in (Pool(c) for c in ([ch] if ch else channels())) if pool.card(slug)]
    if not hits:
        die(f"không có bài {slug} (songs/<type>/{slug}.md)")
    if len(hits) > 1:
        die(f"{slug} có ở nhiều kênh ({', '.join(p.ch for p in hits)}): thêm --channel")
    return hits[0]


def remote(args, stdin=None):
    r = subprocess.run(["bash", str(REMOTE_SH), *args], input=stdin, text=True)
    if r.returncode:
        die(f"GPU server lỗi ở bước `{args[0]}` (exit {r.returncode}): kiểm tra mạng/server rồi chạy lại. "
            "Không chạy Whisper trên Mac; server không lên được thì báo PM.", 3)


def parse_lyrics(text, song_type):
    sections, cur = [], None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        tag = re.fullmatch(r"\[(.*)\]", line)
        if tag:
            cur = {"tag": tag.group(1).split(":")[0].strip().lower(), "lines": []}
            sections.append(cur)
            continue
        if cur is None:
            cur = {"tag": "", "lines": []}
            sections.append(cur)
        if re.fullmatch(r"\(.*\)", line):
            continue
        cur["lines"].append(line)
    sections = [s for s in sections if s["lines"] and not any(k in s["tag"] for k in INSTRUMENTAL)]
    before_sung = True
    for i, s in enumerate(sections):
        tagged_spoken = any(k in s["tag"] for k in SPOKEN)
        intro_spoken = song_type == "spoken" and before_sung and (s["tag"].startswith("intro") or (i == 0 and not s["tag"]))
        s["spoken"] = tagged_spoken or intro_spoken
        if not s["spoken"]:
            before_sung = False
    return sections


def align(sections, words):
    pairs = [(t, k) for k, w in enumerate(words) for t in norm(w["w"])]
    toks = [t for t, _ in pairs]
    rows, cur, no = [], 0, 0
    for si, sec in enumerate(sections):
        for li, line in enumerate(sec["lines"]):
            no += 1
            lt = norm(line)
            n = len(lt)
            best, bi, bj = 0.0, None, None
            for i in range(cur, min(len(toks), cur + SEARCH_AHEAD)):
                for m in (n - 1, n, n + 1, n + 2):
                    if m <= 0 or i + m > len(toks):
                        continue
                    r = SequenceMatcher(None, lt, toks[i:i + m]).ratio()
                    if r > best:
                        best, bi, bj = r, i, i + m - 1
                if best >= GOOD_MATCH:
                    break
            row = {"no": no, "sec": si, "tag": sec["tag"], "line": li, "text": line, "spoken": sec["spoken"],
                   "ratio": round(best, 2)}
            if best >= LINE_MATCH:
                wi, wj = pairs[bi][1], pairs[bj][1]
                probs = [words[k]["p"] for k in range(wi, wj + 1) if words[k].get("p") is not None]
                row.update(s=words[wi]["s"], e=words[wj]["e"], p=sum(probs) / len(probs) if probs else best)
                cur = bj + 1
            rows.append(row)
    return rows


def entries(rows, words):
    got = [r for r in rows if "s" in r]
    vocal = min((r["s"] for r in got), default=words[0]["s"] if words else None)
    sung = min((r["s"] for r in got if not r["spoken"]), default=None)
    return vocal, sung


def short_candidates(sections, rows, words, rules, content_end):
    lo, hi = map(float, rules["short_length_s"])
    pre = min(PRE_ROLL, float(rules["short_pre_roll_s"]))
    max_gap = float(rules["short_max_gap_s"])
    got = [r for r in rows if "s" in r]
    out, seen = [], {}
    for si, sec in enumerate(sections):
        if sec["spoken"]:
            continue
        sec_rows = [r for r in rows if r["sec"] == si]
        first = sec_rows[0]
        if "s" not in first:
            continue
        prev_end = max((w["e"] for w in words if w["e"] <= first["s"]), default=0.0)
        t_in = max(prev_end + 0.05, first["s"] - pre, 0.0)
        after = [r for r in got if r["s"] >= first["s"]]
        chorus = any(k in sec["tag"] for k in CHORUS)
        best = None
        for j, r in enumerate(after):
            if r["spoken"]:
                break
            seg = [w for w in words if first["s"] <= w["s"] <= r["e"]]
            gap = max((b["s"] - a["e"] for a, b in zip(seg, seg[1:])), default=0.0)
            if gap > max_gap:
                break
            nxt = next((w["s"] for w in words if w["s"] > r["e"] + 0.05), content_end)
            tail = max(0.0, min(MAX_TAIL, nxt - r["e"] - 0.3))
            t_out = min(r["e"] + tail + FADE_OUT / 2, content_end)
            dur = t_out - t_in
            if dur > hi:
                break
            if dur < lo:
                continue
            lines = [x for x in rows if first["no"] <= x["no"] <= r["no"]]
            if any(x["spoken"] for x in lines):
                break
            matched = [x for x in lines if "s" in x]
            est = len(lines) - len(matched)
            ends_section = r["no"] == max(x["no"] for x in rows if x["sec"] == r["sec"])
            complete = all(x in lines for x in sec_rows)
            prob = sum(x["p"] for x in matched) / len(matched)
            score = (2.0 * chorus + 1.0 * complete + 1.0 * ends_section + min(nxt - r["e"], 2.0) / 2 + prob
                     - EST_PENALTY * est)
            cand = {"sec": si, "tag": sec["tag"] or "—", "in": round(t_in, 2), "out": round(t_out, 2),
                    "dur": round(dur, 1), "lines": lines, "est": est, "complete": complete,
                    "ends_section": ends_section, "gap_after": round(nxt - r["e"], 1), "max_gap": round(gap, 1),
                    "score": score}
            if best is None or score >= best["score"]:
                best = cand
        if not best:
            continue
        key = tuple(norm(best["lines"][0]["text"]))
        best["score"] -= 0.1 * seen.get(key, 0)
        seen[key] = seen.get(key, 0) + 1
        out.append(best)
    out.sort(key=lambda c: -c["score"])
    for k, c in enumerate(out, 1):
        c["k"] = k
        c["key"] = f"L{c['lines'][0]['no']}-L{c['lines'][-1]['no']}"
        c["score"] = round(c["score"], 2)
    return out


def timed(lines):
    out, i = [], 0
    while i < len(lines):
        if "s" in lines[i]:
            out.append({"t0": r2(lines[i]["s"]), "t1": r2(lines[i]["e"]), "text": lines[i]["text"]})
            i += 1
            continue
        j = i
        while "s" not in lines[j]:
            j += 1
        t0, t1 = lines[i - 1]["e"], lines[j]["s"]
        step = max(t1 - t0, 0.0) / (j - i)
        out += [{"t0": r2(t0 + step * (k - i)), "t1": r2(t0 + step * (k - i + 1)), "text": lines[k]["text"]}
                for k in range(i, j)]
        i = j
    return out


def by_clip(named):
    return {str(fm.get("clip_id"))[:8]: s for s, fm in named.items()}


def other_versions(clip, named):
    same, ids = {x for x, _ in clip.twins(named)["same"]}, by_clip(named)
    done = [(ids[x], named[ids[x]]) for x in sorted(same) if x in ids]
    return done, sorted(same - set(ids))


def version_label(version, tw):
    return version or ("?" if tw["unknown"] else "bài riêng")


def twin_note(tw, named):
    if not tw["mine"]:
        return "clip này chưa có lời"
    ids = by_clip(named)

    def who(x):
        return f" = {ids[x]}" if x in ids else " chưa tên"

    bits = [f"{x}{who(x)} lời giống {r:.2f} → cùng bài" for x, r in tw["same"]]
    bits += [f"{x}{who(x)} lời khác {r:.2f} → bài riêng" for x, r in tw["differ"]]
    bits += [f"{x} chưa có lời" for x in tw["unknown"]] + [f"{x} đã bỏ" for x in tw["dropped"]]
    return ", ".join(bits) or "không có"


def analyse(clip, named):
    lyrics = clip.lyrics()
    if not lyrics:
        die(f"{clip.id8}: chưa có lời (raw/{clip.id8}.lyrics.txt)")
    w = clip.words()
    if not w:
        die(f"{clip.id8}: chưa có timestamp Whisper cho file hiện tại → `songs.py words --channel {clip.pool.ch}`")
    words = w["words"]
    info, err = wav_info(clip.audio)
    if err:
        die(f"{clip.id8}: {err}")
    sections = parse_lyrics(lyrics, clip.type)
    rows = align(sections, words)
    vocal, sung = entries(rows, words)
    done, waiting = other_versions(clip, named)
    cands = short_candidates(sections, rows, words, clip.pool.rules(), info["duration_s"])
    return {"lyrics": lyrics, "words": words, "sections": sections, "rows": rows, "vocal": vocal, "sung": sung,
            "duration": info["duration_s"], "done": done, "waiting": waiting, "cands": cands,
            "tw": clip.twins(named), "note": twin_note(clip.twins(named), named), "version": clip.version(named)}


def print_analysis(clip, an):
    rules = clip.pool.rules()
    suno = (clip.meta or {}).get("title")
    tw = an["tw"]
    print(f"== {clip.id8} · {clip.type} · lượt {clip.generation} · "
          f"{'bản ' + an['version'] if an['version'] else version_label(None, tw)} · "
          f"{mmss(an['duration'])} · Suno: {quoted(suno) if suno else '—'} · bản kia: {an['note']}"
          + (f" · đã tên: {clip.slug}" if clip.slug else ""))
    if tw["unknown"]:
        print(f"⚠️  bản kia {', '.join(tw['unknown'])} chưa có lời: chưa biết cùng bài hay bài riêng, `name` sẽ từ chối "
              "(chờ lane Suno; bản kia hỏng thì `drop` nó)")
    elif an["done"] and not clip.slug:
        print(f"→ cùng lời với bản kia = một bài: bản này phải tên đúng {quoted(an['done'][0][1].get('title'))} "
              f"(`name --title` như bản kia) → <tên>_{an['version']}")
    elif tw["same"] and not clip.slug:
        print(f"→ cùng lời với bản kia = một bài 2 bản: một tên chung, file <tên>_{an['version']}")
    elif not clip.slug:
        print("→ bài riêng (lời khác bản kia, hoặc bản kia đã bỏ): tên riêng từ lời bài này, file <tên> (không _vN, "
              "version null), không trùng tên bài kia")
    if not clip.position:
        print("⚠️  clip không có trong songs/manifest.json generations[].clip_ids: chưa biết lượt, `name` sẽ từ chối")
    rows = an["rows"]
    matched = sum("s" in r for r in rows)
    print(f"Whisper {len(an['words'])} chữ · dóng được {matched}/{len(rows)} dòng lời · "
          f"vocal_entry_s {r2(an['vocal'])} · sung_entry_s {r2(an['sung'])}")
    if clip.type == "spoken" and not any(s["spoken"] for s in an["sections"]):
        print("⚠️  bài loại spoken nhưng lời không có tag [Spoken…]/[Intro] nào: sung_entry_s = dòng đầu, xem lại lời")
    if rows and matched / len(rows) < 0.5:
        print("⚠️  dóng được < 50 % dòng lời: timestamp kém tin cậy, chọn đoạn Short cẩn thận")
    print("\n  #  giọng  t0 → t1           [đoạn] dòng")
    for r in rows:
        t = f"{r['s']:7.2f} → {r['e']:7.2f}" if "s" in r else "   (không dóng được)"
        print(f"{r['no']:3d}  {'đọc' if r['spoken'] else 'hát'}   {t}  [{r['tag'] or '—'}] {r['text']}")
    lo, hi = rules["short_length_s"]
    print(f"\n== Đoạn Short ({lo:g}–{hi:g} s, vào ≤ {rules['short_pre_roll_s']:g} s trước chữ đầu, "
          f"không lặng > {rules['short_max_gap_s']:g} s, chỉ phần hát, kết cuối dòng) — xếp theo điểm; "
          "`name --short <khóa>` (khóa = dòng lời đầu–cuối, không đổi khi bảng xếp lại)")
    if not an["cands"]:
        print("không có đoạn nào vừa luật: xem lại lời/timestamp; báo PM nếu bài không có đoạn hát nào hợp")
        return
    print("| # | khóa | bắt đầu | in → out | dài | dòng ước lượng giờ | trọn đoạn | hết đoạn | lặng sau | lặng dài nhất "
          "| điểm | dòng đầu |\n|---|---|---|---|---|---|---|---|---|---|---|---|")
    for c in an["cands"][:SHOW]:
        print(f"| {c['k']} | {c['key']} | {c['tag']} | {c['in']:.2f} → {c['out']:.2f} | {c['dur']} s | "
              f"{c['est'] or '—'} | {'✔' if c['complete'] else '—'} | "
              f"{'✔' if c['ends_section'] else '—'} | {c['gap_after']} s | {c['max_gap']} s | {c['score']} | "
              f"{c['lines'][0]['text'][:40]} |")


def phrase_bank():
    out = {}
    for f in sorted(PHRASE_BANK.glob("*.yaml")) if PHRASE_BANK.is_dir() else []:
        try:
            data = yaml.safe_load(f.read_text())
        except yaml.YAMLError as e:
            print(f"⚠️  {rel(f)} không đọc được ({e}): bỏ qua kiểm kho câu")
            continue
        for entry in (data.get("entries") if isinstance(data, dict) else None) or []:
            for field in ("title", "thumb_text"):
                full = str(entry.get(field) or "").strip()
                parts = [t.strip() for t in re.split(r"\n| / |\|", re.sub(r"\([^)]*\)", " ", full)) if t.strip()]
                for t in parts + ([" ".join(parts)] if len(parts) > 1 else []):
                    out.setdefault(slugify(t), (entry.get("id"), field, full, f.name))
    return out


def check_title(pool, named, title, slugs, own=()):
    base, errs = slugify(title), []
    if not base:
        errs.append("title rỗng")
    if not title.isascii() or not title.isprintable():
        errs.append("title chỉ gồm ký tự tiếng Anh (ASCII in được): không emoji, không dấu tiếng Việt")
    clash = [s for s, fm in named.items() if s not in own and (s in slugs or slugify(fm.get("title", "")) == base)]
    if clash:
        fm = named[clash[0]]
        errs.append(f"trùng tên bài {quoted(fm.get('title'))} của lượt {fm.get('generation')} ({', '.join(clash)}): một tên "
                    "chỉ dùng cho các bản cùng lời của một lượt (lời khác = bài riêng, tên riêng)")
    taken = [p for s in slugs if s not in own and s not in clash for p in pool.occupied(s)]
    if taken:
        errs.append(f"đã có {', '.join(rel(p) for p in taken)}")
    rules = pool.rules()
    words = title.split()
    if rules.get("title_words"):
        lo, hi = rules["title_words"]
        if not lo <= len(words) <= hi:
            errs.append(f"title {len(words)} từ, naming.md cần {lo}–{hi}")
    if rules.get("title_case") and any(not (w[0].isupper() or w[0].isdigit()) and (i == 0 or w not in TITLE_SMALL_WORDS)
                                       for i, w in enumerate(words)):
        errs.append("naming.md: Title Case (mọi từ viết hoa chữ đầu; từ nhỏ " + ", ".join(sorted(TITLE_SMALL_WORDS))
                    + " viết thường được, trừ từ đầu)")
    bad = [ch for ch in str(rules.get("title_forbidden") or "") if ch in title]
    if bad:
        errs.append(f"naming.md cấm ký tự {' '.join(bad)} trong title")
    if errs:
        die("title không dùng được: " + "; ".join(errs))
    hit = phrase_bank().get(base)
    if hit:
        print(f"⚠️  title trùng nguyên văn kho câu R&D: id {hit[0]} ({hit[3]} → {hit[1]}: {quoted(hit[2])}). Được dùng: "
              "câu cầu nguyện chung / câu kinh điển (CEO 2026-09-28); tên, branding kênh khác thì không bao giờ.")


def dump_front(fm):
    L = []
    for k, v in fm.items():
        if k != "short":
            L.append(f"{k}: {scalar(v)}")
            continue
        L += ["short:", f"  start_s: {scalar(v['start_s'])}", f"  end_s: {scalar(v['end_s'])}", "  lines:"]
        L += [f"    - {{t0: {scalar(x['t0'])}, t1: {scalar(x['t1'])}, text: {quoted(x['text'])}}}" for x in v["lines"]]
        L += [f"  hook: {quoted(v['hook'])}", f"  why: {quoted(v['why'])}"]
    text = "\n".join(L)
    if yaml.safe_load(text) != fm:
        die("front matter ghi ra không đọc lại đúng (lỗi của songs.py)")
    return text


def song_md(fm, lyrics, ch):
    head, body = split_front(TEMPLATE.read_text())
    keys = list(yaml.safe_load(head) or {})
    fm = {**{k: fm[k] for k in keys if k in fm}, **{k: v for k, v in fm.items() if k not in keys}}
    body = (body.replace("<Song Title>", fm["title"]).replace("<ch>", ch).replace("<type>", str(fm["type"]))
            .replace("<lyrics exactly as Suno stored them>", lyrics.strip("\n")))
    return f"---\n{dump_front(fm)}\n---\n{body}"


def auto_why(c):
    bits = [f"[{c['tag']}] dòng {c['lines'][0]['no']}–{c['lines'][-1]['no']}", f"{c['dur']} s"]
    if c["complete"]:
        bits.append("trọn đoạn")
    if c["ends_section"]:
        bits.append("kết cuối đoạn, lặp mượt")
    return ", ".join(bits)


def folder_label(pool, slug):
    return "songs/ ⚠️ bố cục cũ" if pool.legacy(slug) else f"{pool.card(slug).parent.name}/"


def song_key(slug, fm):
    return fm.get("generation") if fm.get("version") and fm.get("generation") else slug


def song_count(named):
    return len({song_key(s, fm) for s, fm in named.items()})


def layout_slug(title, version):
    return slugify(title) + (f"_{version}" if version else "")


def misfiled(pool, named):
    out = []
    for s, fm in named.items():
        tw = pool.twins(named, str(fm.get("clip_id"))[:8], fm.get("clip_id"), fm.get("generation"))
        if tw["unknown"]:
            continue
        want = (pool.generation_of(fm.get("clip_id"))[1] or fm.get("version")) if tw["same"] else None
        if (tw["same"] and not want) or fm.get("version") != want or s != layout_slug(fm.get("title"), want):
            out.append(s)
    return out


def legacy_hint(pool, named):
    old = [s for s in named if pool.legacy(s)]
    if old:
        print(f"\n⚠️  {len(old)} bài còn nằm thẳng trong songs/ (bố cục cũ): `songs.py migrate --channel {pool.ch}` "
              "(xem thay đổi) rồi `--yes`")
    loose = misfiled(pool, named)
    if loose:
        print(f"\n⚠️  {len(loose)} bản sai bố cục (cùng lời với bản kia → <tên>_vN + `version`; lời khác hoặc bản kia bỏ → "
              f"<tên>, `version` null): {', '.join(loose)} → `songs.py rename <slug> --title \"<tên>\" --update-albums` "
              "(đổi mọi bản cùng lời của lượt cùng lúc)")


def cmd_list(a):
    pool = Pool(a.channel)
    named = pool.songs()
    clips = pool.clips(named)
    raw = [c for c in clips if not c.slug and not c.drop]
    print(f"== Clip chưa đặt tên ({len(raw)}) · {rel(pool.raw)} · lời giống bản kia ≥ {SAME_LYRICS:g} = cùng bài (v1/v2), "
          "thấp hơn = bài riêng")
    if raw:
        print("| id8 | loại | lượt | bản | lời vs bản kia | dài | Whisper | trạng thái | tên Suno |\n"
              "|---|---|---|---|---|---|---|---|---|")
    for c in raw:
        p = c.problem()
        info, _ = wav_info(c.wav) if c.wav.exists() else (None, None)
        w = c.words() if not c.problem(for_words=True) else None
        done, _ = other_versions(c, named)
        tw = c.twins(named)
        state = p or ("sẵn sàng: candidates → name" if w else "cần `words`")
        if not p and tw["mine"] and tw["unknown"]:
            state += f" · chờ lời bản kia {', '.join(tw['unknown'])} (`name` từ chối tới khi có; hỏng thì `drop` nó)"
        if done:
            state += f" · tên = {quoted(done[0][1].get('title'))} (như bản kia)"
        print(f"| {c.id8} | {c.type or '?'} | {c.generation or '?'} | {version_label(c.version(named), tw)} | "
              f"{twin_note(tw, named)} | {mmss(info['duration_s'] if info else None)} | {'✔' if w else '—'} | {state} | "
              f"{(c.meta or {}).get('title') or '—'} |")
    print(f"\n== Bài đã đặt tên ({song_count(named)} bài · {len(named)} bản) · {rel(pool.dir)}/<type>/")
    if named:
        print("| bài | bản | slug | loại | thư mục | lượt | dài | vào lời / hát | Short |\n"
              "|---|---|---|---|---|---|---|---|---|")
    for slug, fm in named.items():
        sh = fm.get("short") or {}
        warn = "" if pool.wav_of(slug).exists() else " ⚠️ thiếu wav"
        print(f"| {fm.get('title')} | {fm.get('version') or 'bài riêng'} | {slug}{warn} | {fm.get('type')} | "
              f"{folder_label(pool, slug)} | {fm.get('generation')} | {mmss(fm.get('duration_s'))} | "
              f"{fm.get('vocal_entry_s')} / {fm.get('sung_entry_s')} s | {sh.get('start_s')}–{sh.get('end_s')} s |")
    dropped = pool.dropped()
    if dropped:
        print(f"\n== Clip đã bỏ ({len(dropped)}) · {rel(pool.dropped_file)}\n| id8 | loại | lượt | ngày | lý do |\n"
              "|---|---|---|---|---|")
        for x, d in dropped.items():
            print(f"| {x} | {d.get('type') or '?'} | {d.get('generation') or '?'} | {d.get('dropped')} | {d.get('reason')} |")
    legacy_hint(pool, named)


def cmd_words(a):
    pool = Pool(a.channel)
    named = pool.songs()
    want = {x[:8].lower() for x in a.clip or []}
    todo = []
    for c in pool.clips(named):
        if want and c.id8 not in want:
            continue
        if c.slug:
            if want:
                print(f"{c.id8}: đã đặt tên ({c.slug}), bỏ qua")
            continue
        if c.drop and not want:
            continue
        p = c.problem(for_words=True)
        if p:
            print(f"{c.id8}: bỏ qua ({p})")
            continue
        if a.force or not c.words():
            todo.append(c)
    for x in sorted(want - set(pool.raw_ids())):
        print(f"{x}: không có trong {rel(pool.raw)}")
    if not todo:
        print("Không clip nào cần Whisper.")
        return
    wavs = [rel(c.wav) for c in todo]
    out = rel(pool.words_dir)
    skr = rel(SKILL)
    print(f"Whisper {len(todo)} clip trên GPU server: {' '.join(c.id8 for c in todo)}", flush=True)
    remote(["push"], "\n".join([f"{skr}/scripts/whisper_words.py", *wavs]) + "\n")
    q = " ".join(map(shlex.quote, wavs))
    remote(["exec", f"{skr}/.venv/bin/python {skr}/scripts/whisper_words.py --out {shlex.quote(out)} {q} && rm -f {q}"])
    remote(["pull", out])
    for c in todo:
        w = c.words()
        if not w:
            print(f"❌ {c.id8}: không kéo được kết quả Whisper")
            continue
        first = w["words"][0]["s"] if w["words"] else None
        print(f"✔ {c.id8}: {len(w['words'])} chữ, chữ đầu ở {r2(first)} s")


def cmd_candidates(a):
    clip = find_clip(a.id8, a.channel)
    named = clip.pool.songs()
    if not clip.slug and (p := clip.problem()):
        die(f"{clip.id8}: {p}")
    print_analysis(clip, analyse(clip, named))


def cmd_name(a):
    clip = find_clip(a.id8, a.channel)
    pool = clip.pool
    named = pool.songs()
    title = " ".join(a.title.split())
    if not clip.position:
        die(f"{clip.id8}: không có trong {rel(pool.dir / 'manifest.json')} generations[].clip_ids → chưa biết lượt, bản kia, "
            "v1 hay v2 (lane Suno chưa ghi xong lượt?): chờ rồi chạy lại, không đoán")
    if not clip.slug and (p := clip.problem()):
        die(f"{clip.id8}: {p}")
    tw = clip.twins(named)
    if tw["unknown"]:
        die(f"{clip.id8}: bản kia của lượt {clip.generation} ({', '.join(tw['unknown'])}) chưa có lời → chưa biết cùng bài "
            "(v1/v2) hay bài riêng: chờ lane Suno ghi xong rồi chạy lại; bản kia hỏng thì `drop` nó trước")
    version = clip.version(named)
    slug = layout_slug(title, version)
    if clip.slug and (title != named[clip.slug]["title"] or clip.slug != slug):
        die(f"{clip.id8} đã tên {quoted(named[clip.slug]['title'])} ({clip.slug}; đúng bố cục bây giờ: "
            f"{layout_slug(named[clip.slug]['title'], version)}): đổi tên / bố cục bằng `rename {clip.slug} --title …`")
    done, waiting = other_versions(clip, named)
    differ = [(s, fm) for s, fm in done if fm.get("title") != title]
    if differ:
        s, fm = differ[0]
        die(f"bản kia của lượt {clip.generation} là {s} tên {quoted(fm.get('title'))}, cùng lời "
            f"({dict(tw['same'])[str(fm.get('clip_id'))[:8]]:.2f}) = cùng một bài: các bản cùng tên "
            f"→ --title {quoted(fm.get('title'))} (muốn tên khác cho cả bài: `rename {s} --title …` trước)")
    folder = pool.card(clip.slug).parent if clip.slug else pool.type_dir(clip.type)
    check_title(pool, named, title, [slug], own={clip.slug, *(s for s, _ in done)} - {None})
    m = SHORT_KEY.fullmatch(a.short.strip())
    if not m:
        die(f"--short {a.short}: cần khóa đoạn dạng L12-L19 (cột `khóa` của `candidates {clip.id8}`; số # đổi khi bảng "
            "xếp lại nên không dùng)")
    key = f"L{int(m.group(1))}-L{int(m.group(2))}"
    an = analyse(clip, named)
    cand = next((c for c in an["cands"] if c["key"] == key), None)
    if not cand:
        die(f"không có đoạn Short {key} trong bảng hiện tại ({', '.join(c['key'] for c in an['cands']) or 'trống'}): "
            f"chạy lại `candidates {clip.id8}`")
    hook = " ".join((a.hook or cand["lines"][0]["text"]).split())
    seg_text = " ".join(" ".join(norm(r["text"])) for r in cand["lines"])
    if not norm(hook) or " ".join(norm(hook)) not in seg_text:
        die(f"hook {quoted(hook)} không nằm trong lời của đoạn {key}")
    fm = {"title": title, "slug": slug, "type": clip.type, "clip_id": clip.clip_id, "generation": clip.generation,
          "version": version, "sibling": done[0][0] if done else None,
          "suno_url": f"https://suno.com/song/{clip.clip_id}", "audio": f"{slug}.wav",
          "duration_s": r2(an["duration"]), "vocal_entry_s": r2(an["vocal"]), "sung_entry_s": r2(an["sung"]),
          "named": f"{date.today()} audio-song-naming",
          "short": {"start_s": cand["in"], "end_s": cand["out"],
                    "lines": timed(cand["lines"]),
                    "hook": hook, "why": " ".join((a.why or auto_why(cand)).split())}}
    text = song_md(fm, an["lyrics"], pool.ch)
    dst_wav, dst_md = folder / f"{slug}.wav", folder / f"{slug}.md"
    moved = False
    if not clip.slug:
        folder.mkdir(exist_ok=True)
        os.replace(clip.wav, dst_wav)
        moved = True
    try:
        dst_md.write_text(text)
    except OSError:
        if moved:
            os.replace(dst_wav, clip.wav)
        raise
    for s, _ in done:
        sib_md = pool.card(s)
        sib_md.write_text(set_field(sib_md.read_text(), "sibling", slug))
    verb = "cập nhật" if clip.slug else "đặt tên"
    print(f"✔ {verb}: {clip.id8} → {rel(dst_wav)} · {rel(dst_md)}")
    print(f"  {title} · {'bản ' + version if version else 'bài riêng'} · {clip.type} · {mmss(an['duration'])} · "
          f"vào lời {fm['vocal_entry_s']} s · vào hát {fm['sung_entry_s']} s · bản kia: {an['note']}")
    print(f"  Short {key}: {cand['in']:.2f} → {cand['out']:.2f} ({cand['dur']} s) · hook {quoted(hook)}")
    if done:
        print(f"  bản kia: {', '.join(s for s, _ in done)} (đã ghi sibling hai chiều)")
    for x in waiting:
        print(f"  bản kia {x} cùng lời, chưa tên: đặt tên nó bằng đúng {quoted(title)} → {slugify(title)}_vN, sibling tự nối")
    ids = by_clip(named)
    for x, r in tw["differ"]:
        if x not in ids:
            print(f"  bản kia {x} lời khác ({r:.2f}): bài riêng → tên riêng từ lời của nó, file <tên> không _vN")


def cmd_drop(a):
    clip = find_clip(a.id8, a.channel)
    pool = clip.pool
    named = pool.songs()
    dropped = dict(pool.dropped())
    if a.undo:
        entry = dropped.pop(clip.id8, None)
        if not entry:
            die(f"{clip.id8} không có trong {rel(pool.dropped_file)}")
        src = pool.dir / entry["wav"] if entry.get("wav") else None
        if src and src.exists():
            if clip.wav.exists():
                die(f"đã có {rel(clip.wav)}: không đè, xem tay")
            os.replace(src, clip.wav)
        pool.save_dropped(dropped)
        print(f"✔ lấy lại {clip.id8}" + (f": {rel(src)} → {rel(clip.wav)}" if src and clip.wav.exists() else " (không có wav)"))
        return
    if clip.slug:
        die(f"{clip.id8} đã tên ({clip.slug}): drop chỉ dành cho clip thô chưa tên")
    if clip.id8 in dropped:
        die(f"{clip.id8} đã bỏ ngày {dropped[clip.id8].get('dropped')}: {dropped[clip.id8].get('reason')}")
    reason = " ".join((a.reason or "").split())
    if not reason:
        die("cần --reason \"<vì sao không dùng được>\"")
    wav = None
    if clip.wav.exists():
        if time.time() - clip.wav.stat().st_mtime < SETTLE_S:
            die(f"{rel(clip.wav)} vừa ghi (< {SETTLE_S:g} s): lane Suno đang tải, chờ rồi drop")
        dst = pool.dropped_dir / clip.wav.name
        if dst.exists():
            die(f"đã có {rel(dst)}: xem tay")
        pool.dropped_dir.mkdir(exist_ok=True)
        os.replace(clip.wav, dst)
        wav = os.path.relpath(dst, pool.dir)
    dropped[clip.id8] = {"clip_id": clip.clip_id, "generation": clip.generation, "type": clip.type, "reason": reason,
                         "dropped": str(date.today()), "wav": wav,
                         "downloaded": bool(wav or clip.json_path.exists() or clip.lyrics_path.exists())}
    try:
        pool.save_dropped(dropped)
    except OSError:
        if wav:
            os.replace(pool.dir / wav, clip.wav)
        raise
    print(f"✔ bỏ {clip.id8} (lượt {clip.generation}): {reason}"
          + (f" · wav → {wav}" if wav else " · không có wav" if dropped[clip.id8]["downloaded"] else " · chưa từng tải về")
          + f" · ghi {rel(pool.dropped_file)}")
    ids = by_clip(named)
    for x in pool.gen_ids(clip.clip_id or clip.id8, clip.generation, named):
        if x == clip.id8 or x in dropped:
            continue
        tw = pool.twins(named, x, None, clip.generation)
        s = ids.get(x)
        if s and named[s].get("version") and not tw["same"]:
            print(f"  ⚠️  {s} giờ là bài riêng (không còn bản cùng lời) → `songs.py rename {s} --title "
                  f"{quoted(named[s].get('title'))}` (bỏ _vN, version null)")
        elif not s:
            print(f"  bản kia {x}: {'cùng bài với bản khác của lượt' if tw['same'] else 'bài riêng'} → đặt tên theo "
                  f"`candidates {x}`")


def short_dirs(ch):
    return sorted(p for p in ch.glob("albums/*/short") if p.is_dir()) + sorted(p for p in ch.glob("shorts/*") if p.is_dir())


def album_refs(pool, songs):
    refs, ch = [], pool.dir.parent
    by_wav = {f"{s}.wav": s for s in songs}
    by_clip = {str(c)[:8]: s for s, c in songs.items() if c}
    for album in sorted((ch / "albums").glob("*/")):
        for md in sorted((album / "tracks").glob("*.md")):
            fm = front_matter(md)
            s = fm.get("slug") if fm.get("slug") in songs else by_wav.get(Path(str(fm.get("audio", ""))).name)
            if s:
                refs.append(("track", md, s))
        am = album / "album.md"
        if am.exists():
            fm = front_matter(am)
            short = ((fm.get("brief") or {}).get("short") or {}).get("song")
            refs += [("album", am, s) for s in songs if s in (fm.get("tracklist") or []) or short == s]
        aj = album / "assembly.json"
        if aj.exists():
            used = {t.get("slug") for t in json.loads(aj.read_text()).get("tracks", [])}
            refs += [("assembly", aj, s) for s in songs if s in used]
    for sm in (d / "short.md" for d in short_dirs(ch) if (d / "short.md").exists()):
        fm = front_matter(sm)
        s = next((x for x in songs if str(fm.get("song") or "") == x or Path(str(fm.get("track") or "")).stem == x),
                 by_clip.get(str(fm.get("clip_id") or "")[:8]))
        if s:
            refs.append(("short", sm, s))
    return refs


def update_refs(refs, mapping):
    token = re.compile(r"(?<![\w-])(" + "|".join(map(re.escape, sorted(mapping, key=len, reverse=True))) + r")(?![\w-])")

    def swap(text):
        return token.sub(lambda m: mapping[m.group(1)][0], text)

    files, albums = {}, set()
    for kind, path, old in refs:
        files.setdefault((kind, path), []).append(old)
    for (kind, path), olds in files.items():
        if kind == "track":
            fm = front_matter(path)
            new, title = mapping[olds[0]]
            text = set_field(swap(path.read_text()), "title", title)
            if fm.get("title"):
                text = re.sub(rf"^(#.*){re.escape(str(fm['title']))}", lambda m: m.group(1) + title, text, count=1,
                              flags=re.M)
            old = olds[0]
            dst = path.with_name(path.name[:-len(old) - 3] + f"{new}.md") if path.name.endswith(f"{old}.md") else path
            dst.write_text(text)
            if dst != path:
                path.unlink()
            albums.add(path.parent.parent)
            print(f"  ✔ track: {rel(path)} → {rel(dst)}")
            continue
        if kind == "album":
            head, body = split_front(path.read_text())
            path.write_text(f"---\n{swap(head)}\n---\n{body}")
            albums.add(path.parent)
        elif kind == "assembly":
            data = json.loads(path.read_text())
            for t in data.get("tracks", []):
                if t.get("slug") in mapping:
                    new, title = mapping[t["slug"]]
                    t.update(slug=new, title=title, audio=swap(str(t.get("audio") or "")))
            path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
            albums.add(path.parent)
        print(f"  ✔ {kind}: {rel(path)} ({', '.join(f'{o} → {mapping[o][0]}' for o in olds)})")
    for al in sorted(albums):
        print(f"  → {rel(al)}: `python3 .claude/skills/audio-album-assembly/scripts/assemble.py report {rel(al)}` "
              "(assembly.md + chapters theo tên mới); youtube.md (chapters) phải soạn lại")


def song_versions(pool, named, slug):
    fm = named[slug]
    tw = pool.twins(named, str(fm.get("clip_id"))[:8], fm.get("clip_id"), fm.get("generation"))
    if tw["unknown"]:
        die(f"{slug}: bản kia của lượt {fm.get('generation')} ({', '.join(tw['unknown'])}) chưa có lời → chưa biết cùng bài "
            "hay bài riêng: chờ lane Suno rồi chạy lại")
    ids = by_clip(named)
    members = [slug] + [ids[x] for x, _ in tw["same"] if x in ids]
    out = []
    for s in members:
        f = named[s]
        version = None
        if tw["same"]:
            version = pool.generation_of(f.get("clip_id"))[1] or f.get("version")
            if not version:
                die(f"{s}: không biết bản v1/v2 (card không có `version`, clip không có trong songs/manifest.json)")
        out.append((s, f, version))
    versions = [v for _, _, v in out]
    if len(set(versions)) != len(versions):
        die(f"lượt {fm.get('generation')}: các bản {', '.join(s for s, _, _ in out)} trùng version {versions}: sửa "
            "`version` trong card")
    return sorted(out, key=lambda x: x[2] or "")


def cmd_rename(a):
    pool = find_song(a.slug, a.channel)
    named = pool.songs()
    title = " ".join(a.title.split())
    plan = [(old, fm, v, layout_slug(title, v)) for old, fm, v in song_versions(pool, named, a.slug)]
    if all(fm.get("title") == title and old == new and fm.get("version") == v for old, fm, v, new in plan):
        die("tên không đổi")
    own = {old for old, *_ in plan}
    if any(new in own and new != old for old, _, _, new in plan):
        die("slug mới của một bản trùng slug cũ của bản kia: sửa `version` trong card cho đúng rồi chạy lại")
    check_title(pool, named, title, [new for *_, new in plan], own=own)
    mapping = {old: (new, title) for old, _, _, new in plan}
    refs = album_refs(pool, {old: fm.get("clip_id") for old, fm, _, _ in plan})
    shorts = sorted({p for k, p, _ in refs if k == "short"})
    refs = [r for r in refs if r[0] != "short"]
    if refs and not a.update_albums:
        die(f"{', '.join(old for old, *_ in plan)} đang được dùng ở: " + ", ".join(sorted({rel(p) for _, p, _ in refs}))
            + " → thêm --update-albums để sửa luôn các file đó (album đã đăng thì đừng đổi)")
    news = [new for *_, new in plan]
    cards = []
    for old, fm, v, new in plan:
        md = pool.card(old)
        lyrics = lyrics_block(md.read_text())
        if lyrics is None:
            die(f"{rel(md)} không có khối ## Lyrics: không ghi lại card được")
        others = [n for n in news if n != new]
        fm = {**fm, "title": title, "slug": new, "version": v, "sibling": others[0] if others else None,
              "audio": f"{new}.wav"}
        cards.append((old, md, new, v, song_md(fm, lyrics, pool.ch)))
    for old, md, new, v, text in cards:
        wav = md.with_suffix(".wav")
        has_wav = wav.exists()
        if new != old and has_wav:
            os.replace(wav, md.with_name(f"{new}.wav"))
        md.with_name(f"{new}.md").write_text(text)
        if new != old:
            md.unlink()
        print(f"✔ {v or 'bài riêng'}: {rel(md.with_suffix(''))}.* → {rel(md.with_name(new))}.* · {quoted(title)}"
              + ("" if has_wav else " ⚠️ không có wav"))
    for s, f in named.items():
        if s not in own and f.get("sibling") in mapping:
            p = pool.card(s)
            p.write_text(set_field(p.read_text(), "sibling", None))
            print(f"  sibling của {s} bỏ trống (lời khác {f['sibling']}: bài riêng)"
                  + (f" → {s} còn `version` {f.get('version')}: `rename {s} --title …` bỏ _vN" if f.get("version") else ""))
    if refs:
        update_refs(refs, mapping)
    for p in shorts:
        print(f"  ⚠️  {rel(p)}: Short dùng bản cũ (không sửa file Short ở đây) → đồng bộ lại:\n"
              f"     python3 .claude/skills/video-shorts/scripts/shorts.py spec {rel(p.parent)}")


def write_catalog(pool):
    named = pool.songs()
    raw = [c for c in pool.clips(named) if not c.slug and not c.drop]
    dropped = pool.dropped()
    L = [f"# Kho bài: {pool.ch}", "",
         f"_Sinh bởi audio-song-naming `songs.py catalog` · {date.today()} · {song_count(named)} bài ({len(named)} bản) "
         f"đã tên · {len(raw)} clip chưa tên · {len(dropped)} clip bỏ (songs/dropped.json). Lượt Suno 2 clip cùng lời = một "
         "bài, các bản v1 / v2 cùng tên đứng cạnh nhau; 2 clip khác lời = 2 bài riêng (bản —). "
         "Đừng sửa tay: nguồn là front matter songs/<type>/*.md._"]
    groups = {}
    for slug, fm in named.items():
        groups.setdefault(str(fm.get("type")), []).append((slug, fm))
    order = [t for t in pool.types() if t in groups] + sorted(t for t in groups if t not in pool.types())
    total, number = 0.0, {}
    for t in order:
        rows = groups[t]
        mins = sum(float(fm.get("duration_s") or 0) for _, fm in rows) / 60
        L += ["", f"## {t} · {song_count(dict(rows))} bài · {len(rows)} bản · {mins:.1f} phút · `songs/{t}/`", "",
              "| # | Bài | bản | slug | lượt | dài | vào lời | vào hát | Short | hook |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for slug, fm in rows:
            n = number.setdefault(song_key(slug, fm), len(number) + 1)
            sh = fm.get("short") or {}
            mark = " ⚠️ songs/ (cũ)" if pool.legacy(slug) else ""
            L.append(f"| {n} | {fm.get('title')} | {fm.get('version') or '—'} | `{slug}`{mark} | {fm.get('generation')} | "
                     f"{mmss(fm.get('duration_s'))} | {fm.get('vocal_entry_s')} s | {fm.get('sung_entry_s')} s | "
                     f"{sh.get('start_s')}–{sh.get('end_s')} s | {sh.get('hook') or '—'} |")
        total += mins
    old, loose = sum(pool.legacy(s) for s in named), misfiled(pool, named)
    L += ["", f"Tổng {total:.1f} phút · " + " · ".join(f"{t}: {song_count(dict(groups[t]))} bài ({len(groups[t])} bản)"
                                                        for t in order)]
    if old:
        L += ["", f"⚠️ {old} bài còn ở bố cục cũ songs/<slug>.*: `songs.py migrate --channel {pool.ch}`"]
    if loose:
        L += ["", f"⚠️ {len(loose)} bản sai bố cục v1/v2 ↔ bài riêng ({', '.join(loose)}): `songs.py rename <slug> --title "
                  "\"<tên>\"`"]
    out = pool.dir / "catalog.md"
    out.write_text("\n".join(L) + "\n")
    print(f"✔ {rel(out)} · {song_count(named)} bài · {len(named)} bản · {total:.1f} phút")


def cmd_catalog(a):
    write_catalog(Pool(a.channel))


def swap_value(text, key, new):
    head, body = split_front(text)
    head, n = re.subn(rf"^({re.escape(key)}:[ \t]*)(\"[^\"]*\"|'[^']*'|[^\s#]+)", lambda m: m.group(1) + scalar(new), head,
                      count=1, flags=re.M)
    return f"---\n{head}\n---\n{body}" if n else text


def legacy_moves(pool):
    moves, errs = [], []
    for md in pool.card_files():
        if md.parent != pool.dir:
            continue
        fm = front_matter(md)
        if not fm.get("clip_id"):
            continue
        problem = pool.type_problem(fm.get("type"))
        if problem:
            errs.append(f"{rel(md)}: {problem} → sửa `type` trong song card rồi chạy lại")
            continue
        folder = pool.dir / str(fm["type"])
        wav = md.with_suffix(".wav")
        clash = [p for p in (folder / md.name, folder / wav.name) if p.exists()]
        if clash:
            errs.append(f"{rel(md)}: đã có {', '.join(rel(p) for p in clash)} (cả hai bố cục cùng có bài này) → xem tay")
            continue
        moves.append({"slug": md.stem, "md": md, "wav": wav if wav.exists() else None,
                      "new_md": folder / md.name, "new_wav": folder / wav.name})
    return moves, errs


def relocations(pool, moves):
    where = {}
    for m in moves:
        where[m["md"]] = m["new_md"]
        where[m["md"].with_suffix(".wav")] = m["new_wav"]
    for slug, card in pool.cards.items():
        if card.parent != pool.dir:
            for old, new in ((pool.dir / card.name, card), (pool.dir / f"{slug}.wav", card.with_suffix(".wav"))):
                if not old.exists():
                    where.setdefault(old, new)
    return where


def ref_changes(pool, where):
    ch, out = pool.dir.parent, []

    def moved(base, value):
        new = where.get((base / str(value)).resolve()) if value else None
        return os.path.relpath(new, base) if new else None

    for album in sorted(p for p in (ch / "albums").glob("*/") if p.is_dir()):
        for md in sorted((album / "tracks").glob("*.md")):
            old = front_matter(md).get("audio")
            new = moved(album, old)
            if new:
                cards = [rel((album / x).resolve().with_suffix(".md")) for x in (old, new)]
                out.append(("track audio", md, old, new,
                            lambda t, v=new, c=cards: swap_value(t, "audio", v).replace(f"`{c[0]}`", f"`{c[1]}`")))
        aj = album / "assembly.json"
        if aj.exists():
            data = json.loads(aj.read_text())
            for t in data.get("tracks", []):
                new = moved(album, t.get("audio"))
                if new:
                    out.append((f"assembly.json bài {t.get('track_no')} audio", aj, t["audio"], new,
                                lambda text, no=t.get("track_no"), v=new: json_tracks_audio(text, no, v)))
    for short in short_dirs(ch):
        sm = short / "short.md"
        if sm.exists():
            old = front_matter(sm).get("track")
            new = moved(short, old)
            if new:
                out.append(("short.md track", sm, old, new, lambda t, v=new: swap_value(t, "track", v)))
        sj = short / "short.json"
        if sj.exists():
            spec = json.loads(sj.read_text())
            for key in ("audio", "track"):
                new = moved(REPO, spec.get(key))
                if new:
                    out.append((f"short.json {key}", sj, spec[key], new,
                                lambda text, k=key, v=new: json.dumps({**json.loads(text), k: v}, indent=1, ensure_ascii=False)))
    return out


def json_tracks_audio(text, track_no, value):
    data = json.loads(text)
    for t in data.get("tracks", []):
        if t.get("track_no") == track_no:
            t["audio"] = value
    return json.dumps(data, indent=1, ensure_ascii=False) + "\n"


def cmd_migrate(a):
    pool = Pool(a.channel)
    pool.songs()
    moves, errs = legacy_moves(pool)
    changes = ref_changes(pool, relocations(pool, moves))
    mode = "làm" if a.yes else "thử (chưa đổi gì; thêm --yes để làm)"
    print(f"== migrate {pool.ch}: {len(moves)} bài songs/<slug>.* → songs/<type>/ · {len(changes)} đường dẫn · {mode}")
    for m in moves:
        print(f"  bài  {rel(m['md'])} → {rel(m['new_md'])}")
        print(f"       " + (f"{rel(m['wav'])} → {rel(m['new_wav'])}" if m["wav"] else f"⚠️ không có {m['md'].stem}.wav (chỉ chuyển card)"))
    for kind, path, old, new, _ in changes:
        print(f"  sửa  {rel(path)} · {kind}: {old} → {new}")
    for e in errs:
        print(f"  ❌ {e}")
    if not moves and not changes and not errs:
        print("Không còn gì phải chuyển.")
    if not a.yes:
        sys.exit(1 if errs else 0)
    for m in moves:
        m["new_md"].parent.mkdir(exist_ok=True)
        if m["wav"]:
            os.replace(m["wav"], m["new_wav"])
        os.replace(m["md"], m["new_md"])
    for _, path, _, _, edit in changes:
        path.write_text(edit(path.read_text()))
    if moves or changes:
        print(f"✔ đã chuyển {len(moves)} bài, sửa {len(changes)} đường dẫn")
        write_catalog(pool)
        albums = sorted({p.parent.parent if p.parent.name == "tracks" else p.parent for kind, p, _, _, _ in changes
                         if "albums" in p.parts and not kind.startswith("short")})
        for al in albums:
            print(f"  → {rel(al)}: `album.py check {al.name}`; file bài trên GPU server nằm ở đường mới, lần ghép sau "
                  "tự đẩy lại (bản cũ songs/<slug>.wav trên server không dùng nữa)")
    sys.exit(1 if errs else 0)


def main():
    ap = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list")
    p.add_argument("--channel", required=True)
    p = sub.add_parser("words")
    p.add_argument("--channel", required=True)
    p.add_argument("--clip", nargs="+", help="chỉ các id8 này (mặc định: mọi clip chưa tên chưa có timestamp)")
    p.add_argument("--force", action="store_true", help="chạy lại Whisper dù đã có cache")
    p = sub.add_parser("candidates")
    p.add_argument("id8")
    p.add_argument("--channel")
    p = sub.add_parser("name")
    p.add_argument("id8")
    p.add_argument("--title", required=True)
    p.add_argument("--short", required=True, help="khóa đoạn Short L<đầu>-L<cuối> (cột `khóa` của `candidates`)")
    p.add_argument("--hook", help="dòng hiện đầu Short (mặc định: dòng đầu của đoạn)")
    p.add_argument("--why", help="một dòng: vì sao chọn đoạn này")
    p.add_argument("--channel")
    p = sub.add_parser("drop", help="clip thô không dùng được: raw/<id8>.wav → raw/dropped/, ghi songs/dropped.json")
    p.add_argument("id8")
    p.add_argument("--reason", help="một dòng: vì sao bỏ (bắt buộc, trừ --undo)")
    p.add_argument("--undo", action="store_true", help="lấy lại clip đã bỏ (wav về raw/, xóa khỏi dropped.json)")
    p.add_argument("--channel")
    p = sub.add_parser("rename")
    p.add_argument("slug")
    p.add_argument("--title", required=True)
    p.add_argument("--update-albums", action="store_true",
                   help="sửa luôn tracks/*.md, album.md, assembly.json đang dùng bài; in lệnh shorts.py spec cho Short dùng bài")
    p.add_argument("--channel")
    p = sub.add_parser("catalog")
    p.add_argument("--channel", required=True)
    p = sub.add_parser("migrate", help="chuyển bài bố cục cũ songs/<slug>.* vào songs/<type>/ và sửa đường dẫn tham chiếu")
    p.add_argument("--channel", required=True)
    p.add_argument("--yes", action="store_true", help="làm thật (mặc định chỉ in các thay đổi)")
    a = ap.parse_args()
    {"list": cmd_list, "words": cmd_words, "candidates": cmd_candidates, "name": cmd_name, "drop": cmd_drop,
     "rename": cmd_rename, "catalog": cmd_catalog, "migrate": cmd_migrate}[a.cmd](a)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import argparse
import hashlib
import json
import math
import os
import re
import struct
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]
TEMPLATES = ROOT / "templates"
FM = re.compile(r"^---\n(.*?)\n---[ \t]*\n?", re.S)
URL = re.compile(r"\*\*Video URL:\*\*\s*(https?://\S+)")
ALBUM_SIZE, SHORT_SIZE = (3840, 2160), (2160, 3840)
TRACK_HEAD = "| # | bài | tên | bản | loại | dài | album đã dùng |\n|---|---|---|---|---|---|---|"
BRIEF_FIELDS = ("topic", "story", "title_direction", "thumbnail_text", "thumbnail_concept")
LENGTH_MARGIN_S = 60
VOCAL_ENTRY_MAX_S = 10


def rel(p):
    return str(Path(p).resolve().relative_to(ROOT))


def front_matter(p):
    m = FM.match(p.read_text(encoding="utf-8")) if p.exists() else None
    if not m:
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        sys.exit(f"{rel(p)}: front matter không đọc được: {e}")


def unset(v):
    return v in (None, "", []) or (isinstance(v, str) and v.strip().startswith("<") and v.strip().endswith(">"))


def num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", re.sub(r"['’]", "", s.lower())).strip("-")


def mmss(s):
    s = int(round(s or 0))
    return f"{s // 60}:{s % 60:02d}"


def song_cards(songs_dir):
    legacy = sorted(p for p in songs_dir.glob("*.md") if p.name != "catalog.md")
    typed = sorted(p for p in songs_dir.glob("*/*.md") if p.parent.name != "raw" and not p.parent.name.startswith("."))
    return legacy + typed


def siblings(a, b):
    return a["slug"] != b["slug"] and (a["slug"] == b.get("sibling") or b["slug"] == a.get("sibling") or (
        not unset(a.get("version")) and not unset(b.get("version")) and not unset(a.get("generation"))
        and a.get("generation") == b.get("generation")))


class Channel:
    def __init__(self, d):
        if not (d / "album_rules.md").exists():
            sys.exit(f"không có {rel(d / 'album_rules.md')} (luật chọn bài của kênh)")
        self.dir, self.name = d, d.name
        self.rules = front_matter(d / "album_rules.md")
        miss = [k for k in ("length_min", "crossfade_s", "pattern") if k not in self.rules]
        if miss:
            sys.exit(f"{rel(d / 'album_rules.md')}: front matter thiếu {', '.join(miss)}")
        self.songs = {}
        for md in song_cards(d / "songs"):
            fm = front_matter(md)
            if fm.get("clip_id"):
                slug = str(fm.get("slug") or md.stem)
                self.songs[slug] = {**fm, "slug": slug, "md": md,
                                    "wav": md.parent / Path(str(fm.get("audio") or slug + ".wav")).name}
        self.albums = {}
        for md in sorted((d / "albums").glob("*/album.md")):
            fm = front_matter(md)
            self.albums[md.parent.name] = {"dir": md.parent, "fm": fm,
                                           "tracklist": [str(s) for s in fm.get("tracklist") or [] if not unset(s)]}
        named = {str(s["clip_id"])[:8] for s in self.songs.values()}
        raw = {p.name.split(".")[0] for p in (d / "songs" / "raw").glob("*") if p.suffix in (".wav", ".json")}
        dropped = d / "songs" / "dropped.json"
        self.raw = sorted(raw - named - set(json.loads(dropped.read_text()) if dropped.exists() else {}))
        self.shorts = []
        for md in sorted((d / "albums").glob("*/short/short.md")):
            fm = front_matter(md)
            self.shorts.append({"dir": md.parent, "album": md.parent.parent.name, "label": f"{md.parent.parent.name}/short",
                                "song": str(fm.get("song") or ""), "legacy": False})
        for md in sorted((d / "shorts").glob("*/short.md")):
            fm = front_matter(md)
            self.shorts.append({"dir": md.parent, "album": Path(str(fm.get("album") or "")).name,
                                "label": f"shorts/{md.parent.name}", "song": str(fm.get("song") or ""), "legacy": True})

    def usage(self, names=None):
        used = {}
        for n in self.albums if names is None else names:
            for s in dict.fromkeys(self.albums[n]["tracklist"]):
                used.setdefault(s, []).append(n)
        return used

    def song_key(self, slug):
        song = self.songs.get(slug) or {}
        return song.get("generation") if not unset(song.get("version")) and not unset(song.get("generation")) else slug

    def titles(self, names=None):
        out = {}
        for n in self.albums if names is None else names:
            if self.albums[n]["tracklist"]:
                out.setdefault(self.song_key(self.albums[n]["tracklist"][0]), []).append(n)
        return out


def channel_dir(ch):
    d = ROOT / "channel" / ch
    if not d.is_dir():
        sys.exit(f"không có channel/{ch}")
    return d


def open_album(arg, channel=None):
    d = Path(arg).resolve()
    d = d.parent if d.name == "album.md" else d
    if not (d / "album.md").exists():
        name = arg.rstrip("/")
        hits = [] if "/" in name else sorted(ROOT.glob(f"channel/{channel or '*'}/albums/{name}/album.md"))
        if len(hits) > 1:
            sys.exit(f"{arg} có ở nhiều kênh ({', '.join(h.parents[2].name for h in hits)}): thêm --channel")
        if not hits:
            sys.exit(f"không có album {arg}" + (f" trong channel/{channel}" if channel else "")
                     + " (thư mục albums/NNN-slug hoặc tên NNN-slug; tạo bằng album.py new)")
        d = hits[0].parent
    return d, Channel(d.parent.parent)


def check(ch, name):
    a, r = ch.albums[name], ch.rules
    tl, waivers = a["tracklist"], a["fm"].get("waivers") or {}
    err, warn = [], []

    def rule(key, msg):
        (warn if key in waivers else err).append(msg + (f" (waiver: {waivers[key]})" if key in waivers else ""))

    songs = []
    for i, s in enumerate(tl, 1):
        song = ch.songs.get(s)
        if song is None:
            err.append(f"bài {i:02d} `{s}`: " + ("clip chưa đặt tên → audio-song-naming" if s[:8] in ch.raw
                                                 else f"không có trong kho (songs/<type>/{s}.md)"))
        elif unset(song.get("title")) or not num(song.get("duration_s")):
            err.append(f"bài {i:02d} `{s}`: song md thiếu title / duration_s → audio-song-naming")
            song = None
        songs.append(song)
    no_audio = [s["slug"] for s in songs if s and not s["wav"].exists()]
    if no_audio:
        warn.append(f"{len(no_audio)} bài chưa có file audio trong songs/: {', '.join(no_audio[:4])}{' …' if len(no_audio) > 4 else ''}")
    if not tl:
        err.append("tracklist trống: album.py suggest --write, hoặc PM ghi tay vào album.md")
    for s in sorted({s for s in tl if tl.count(s) > 1}):
        err.append(f"`{s}` nằm {tl.count(s)} lần trong tracklist")
    pat = r["pattern"]
    for i, song in enumerate(songs):
        if song and song.get("type") != pat[i % len(pat)]:
            err.append(f"bài {i + 1:02d} `{song['slug']}` là {song.get('type')}, luật xen kẽ {pat} cần {pat[i % len(pat)]}")
    entry = num((songs[0] or {}).get("vocal_entry_s")) if songs else None
    if entry is not None and entry > VOCAL_ENTRY_MAX_S:
        warn.append(f"bài 1 `{songs[0]['slug']}` vào giọng ở {entry:g} s > {VOCAL_ENTRY_MAX_S} s: video phải mở bằng giọng "
                    "(CLAUDE.md §6) → chọn bài 1 vào lời sớm hơn")
    gap = int(r.get("sibling_min_gap") or 0)
    for i in range(len(songs)):
        for j in range(i + 1, min(len(songs), i + gap)):
            if songs[i] and songs[j] and siblings(songs[i], songs[j]):
                rule("sibling_min_gap", f"bài {i + 1:02d} và {j + 1:02d} là hai bản của cùng một bài (lượt "
                                        f"{songs[i].get('generation')}), cách {j - i} < {gap} vị trí")
    xf = float(r["crossfade_s"])
    durs = [num(s["duration_s"]) for s in songs if s]
    est = sum(durs) - max(len(durs) - 1, 0) * xf
    lo, hi = r["length_min"]
    if durs:
        step = sum(durs) / len(durs) - xf
        part = "" if len(durs) == len(tl) else f" (chỉ tính {len(durs)}/{len(tl)} bài có trong kho)"
        if est < lo * 60:
            err.append(f"ước lượng {mmss(est)}{part} < {lo} phút: thêm ~{math.ceil((lo * 60 - est) / step)} bài")
        elif est < lo * 60 + LENGTH_MARGIN_S:
            warn.append(f"ước lượng {mmss(est)} hơn {lo} phút chưa tới {LENGTH_MARGIN_S} s: bỏ im lặng hai đầu mỗi bài có "
                        f"thể đưa master < {lo} phút (assembly exit 4) → thêm 1 bài")
        elif est > hi * 60:
            err.append(f"ước lượng {mmss(est)} > {hi} phút: bớt ~{math.ceil((est - hi * 60) / step)} bài")
    prev = [n for n in ch.albums if n < name]
    titles = ch.titles(prev)
    if tl and r.get("title_song_unique") and ch.song_key(tl[0]) in titles:
        rule("title_song_unique", f"bài 1 `{tl[0]}` (hoặc bản kia của nó) đã là bài 1 của "
                                  f"{', '.join(titles[ch.song_key(tl[0])])}")
    same = [n for n in prev if ch.albums[n]["tracklist"] == tl]
    if tl and r.get("order_must_differ") and same:
        rule("order_must_differ", f"thứ tự trùng hệt album {', '.join(same)}")
    used = ch.usage(prev)
    used_songs = {ch.song_key(s) for s in used}
    new = [s for s in tl if ch.song_key(s) not in used_songs]
    need = len(tl) if str(r.get("min_new_songs")).lower() == "all" else int(r.get("min_new_songs") or 0)
    if len(new) < need:
        rule("min_new_songs", f"{len(new)} bài mới < {need} (min_new_songs)")
    brief = a["fm"].get("brief") or {}
    short = (brief.get("short") or {}).get("song")
    if unset(short):
        short = tl[0] if tl else None
        warn.append("brief.short.song chưa ghi: Short mặc định lấy bài 1")
    elif short not in tl:
        rule("short", f"brief.short.song `{short}` không nằm trong tracklist")
    ss = ch.songs.get(short) if short else None
    if ss and num((ss.get("short") or {}).get("start_s")) is None:
        rule("short", f"bài cho Short `{short}` chưa có đoạn `short` (audio-song-naming)")
    todo = [k for k in BRIEF_FIELDS if unset(brief.get(k))]
    if todo:
        warn.append(f"brief chưa điền: {', '.join(todo)}")
    return {"tracklist": tl, "songs": songs, "est": est, "errors": err, "warnings": warn, "used": used, "new": new}


def song_row(i, s, song, used):
    u = used.get(s, [])
    if not song:
        return f"| {i:02d} | {s} | ? | ? | ? | ? | ? |"
    return (f"| {i:02d} | {s} | {song.get('title')} | {song.get('version') or '—'} | {song.get('type')} | "
            f"{mmss(song.get('duration_s'))} | {len(u)}{' · ' + u[-1] if u else ' (mới)'} |")


def print_check(ch, name, res):
    print(f"# {name} · {len(res['tracklist'])} bài · ước lượng master {mmss(res['est'])} "
          f"(Σ thời lượng − (n−1) × {ch.rules['crossfade_s']} s) · luật {rel(ch.dir / 'album_rules.md')}\n")
    print(TRACK_HEAD)
    for i, (s, song) in enumerate(zip(res["tracklist"], res["songs"]), 1):
        print(song_row(i, s, song, res["used"]))
    print(f"\nbài mới (chưa ở album nào trước): {len(res['new'])}/{len(res['tracklist'])}\n")
    for line in [f"✖ {e}" for e in res["errors"]] + [f"⚠ {w}" for w in res["warnings"]]:
        print(line)
    print(f"\n✖ {len(res['errors'])} lỗi" if res["errors"] else "✔ đạt mọi luật của album_rules.md")


def cmd_new(a):
    d_ch = channel_dir(a.channel)
    nums = [int(m.group(1)) for p in (d_ch / "albums").glob("*") if (m := re.match(r"(\d{3})-", p.name))]
    slug = slugify(a.title)
    if not slug:
        sys.exit("--title rỗng")
    name = f"{max(nums, default=0) + 1:03d}-{slug}"
    d = d_ch / "albums" / name
    d.mkdir(parents=True)
    text = (TEMPLATES / "album.md").read_text(encoding="utf-8")
    text = text.replace("<NNN-slug>", name).replace("<ch>", d_ch.name).replace("<Album working title>", a.title)
    text = re.sub(r"^tracklist:\n(?:[ \t]+- .*\n)*", "tracklist: []\n", text, count=1, flags=re.M)
    (d / "album.md").write_text(text, encoding="utf-8")
    ck = ROOT / "production" / d_ch.name / "checklists" / f"{name}.md"
    if not ck.exists():
        ck.parent.mkdir(parents=True, exist_ok=True)
        ck.write_text((TEMPLATES / "checklist.md").read_text(encoding="utf-8")
                      .replace("<NNN-slug>", name).replace("<Album title>", a.title), encoding="utf-8")
    print(f"✔ {rel(d / 'album.md')} + {rel(ck)}\n  → điền brief, rồi album.py suggest {rel(d)} --write (hoặc ghi tracklist tay)")


def cmd_pool(a):
    ch = Channel(channel_dir(a.channel))
    used, titles = ch.usage(), ch.titles()
    made = {s["song"]: s["label"] for s in ch.shorts}
    rows = [s for s in ch.songs.values()
            if (not a.type or s.get("type") == a.type) and (not a.unused or s["slug"] not in used)]
    rows.sort(key=lambda s: (str(s.get("type")), len(used.get(s["slug"], [])), str(s.get("generation") or ""),
                             str(s.get("version") or ""), s["slug"]))
    print(f"# Kho bài {ch.name} · {len({ch.song_key(s['slug']) for s in rows})} bài · {len(rows)} bản"
          + (f" loại {a.type}" if a.type else "") + (" chưa dùng" if a.unused else "") + "\n")
    print("| bài | tên | bản | lượt | loại | dài | số album | album gần nhất | bài 1 của | short |\n"
          "|---|---|---|---|---|---|---|---|---|---|")
    for s in rows:
        u = used.get(s["slug"], [])
        seg = "✔" if num((s.get("short") or {}).get("start_s")) is not None else "–"
        print(f"| {s['slug']} | {s.get('title')} | {s.get('version') or '—'} | {s.get('generation') or '–'} | "
              f"{s.get('type')} | {mmss(s.get('duration_s'))} | {len(u)} | {u[-1] if u else '–'} | "
              f"{', '.join(titles.get(ch.song_key(s['slug']), [])) or '–'} | "
              f"{seg}{' · Short ' + made[s['slug']] if s['slug'] in made else ''} |")
    print()
    pool_summary(ch)


def pool_summary(ch):
    used = ch.usage()
    for t in ch.rules["pattern"]:
        of = [s for s in ch.songs.values() if s.get("type") == t]
        print(f"- {t}: {len({ch.song_key(s['slug']) for s in of})} bài ({len(of)} bản) · "
              f"{sum(1 for s in of if s['slug'] not in used)} bản chưa dùng · "
              f"{sum(num(s.get('duration_s')) or 0 for s in of) / 60:.0f} phút")
    print(f"- clip chưa đặt tên trong songs/raw/: {len(ch.raw)}" + (f" ({', '.join(ch.raw[:6])}{' …' if len(ch.raw) > 6 else ''})" if ch.raw else ""))
    old = [s["slug"] for s in ch.songs.values() if s["md"].parent == ch.dir / "songs"]
    if old:
        print(f"- ⚠ {len(old)} bài còn ở bố cục cũ songs/<slug>.md → audio-song-naming `songs.py migrate --channel {ch.name}`")


def write_tracklist(md, tl):
    text = md.read_text(encoding="utf-8")
    m = FM.match(text)
    block = "tracklist:\n" + "".join(f"  - {s}\n" for s in tl)
    head, n = re.subn(r"^tracklist:.*?(?=^\S|\Z)", lambda _: block, m.group(1) + "\n", count=1, flags=re.M | re.S)
    md.write_text("---\n" + (head if n else head + block) + "---\n" + text[m.end():], encoding="utf-8")


def cmd_suggest(a):
    d, ch = open_album(a.album, a.channel)
    me, r = ch.albums[d.name], ch.rules
    pat, xf, lo = r["pattern"], float(r["crossfade_s"]), r["length_min"][0] * 60 + LENGTH_MARGIN_S
    gap = int(r.get("sibling_min_gap") or 0)
    waived = me["fm"].get("waivers") or {}
    others = [n for n in ch.albums if n != d.name]
    used, taken = ch.usage(others), ch.titles(others)
    used_song = {}
    for s, names in used.items():
        used_song.setdefault(ch.song_key(s), []).extend(names)
    ok = {s: v for s, v in ch.songs.items() if num(v.get("duration_s")) and not unset(v.get("title"))}

    def rank(s):
        u = used_song.get(ch.song_key(s), [])
        return len(u), u[-1] if u else "", hashlib.md5(f"{d.name}/{s}".encode()).hexdigest()

    free = [s for s in ok if ok[s].get("type") == pat[0] and not (
        r.get("title_song_unique") and ch.song_key(s) in taken and "title_song_unique" not in waived)]
    first = a.title_song or next((s for s in me["tracklist"][:1] if s in free), None)
    if first is None:
        if not free:
            sys.exit(f"kho không còn bài {pat[0]} nào làm bài 1 được (mọi bài đã là bài 1 của album khác): tạo thêm bài")
        first = min(free, key=lambda s: (num((ok[s].get("short") or {}).get("start_s")) is None,
                                         (num(ok[s].get("vocal_entry_s")) or 0) > VOCAL_ENTRY_MAX_S, rank(s)))
    if first not in ok:
        sys.exit(f"`{first}` không có trong kho đã đặt tên (album.py pool --channel {ch.name})")
    if ok[first].get("type") != pat[0]:
        sys.exit(f"bài 1 phải là {pat[0]}; `{first}` là {ok[first].get('type')}")
    if r.get("title_song_unique") and ch.song_key(first) in taken and "title_song_unique" not in waived:
        sys.exit(f"`{first}` (hoặc bản kia của nó) đã là bài 1 của {', '.join(taken[ch.song_key(first)])} "
                 "(title_song_unique): chọn bài khác, "
                 "hoặc ghi waivers.title_song_unique + lý do trong album.md")
    tl, est = [first], num(ok[first]["duration_s"])
    while est < lo:
        want = pat[len(tl) % len(pat)]
        near = [ok[s] for s in tl[max(0, len(tl) - gap + 1):]]
        cands = [s for s in ok if s not in tl and ok[s].get("type") == want and not any(siblings(ok[s], n) for n in near)]
        if not cands:
            print(f"⚠ hết bài {want} hợp luật cho vị trí {len(tl) + 1:02d}: kho thiếu bài {want} (tạo thêm) — dừng ở {mmss(est)}")
            break
        pick = min(cands, key=rank)
        tl.append(pick)
        est += num(ok[pick]["duration_s"]) - xf
    if not a.write:
        print(f"# Đề xuất tracklist {d.name} · {len(tl)} bài · ước lượng {mmss(est)}\n")
        print(TRACK_HEAD)
        for i, s in enumerate(tl, 1):
            print(song_row(i, s, ok[s], used))
        print(f"\nchưa ghi: thêm --write để ghi vào {rel(d / 'album.md')}")
        return
    write_tracklist(d / "album.md", tl)
    print(f"✔ đã ghi tracklist ({len(tl)} bài) vào {rel(d / 'album.md')}\n")
    ch = Channel(ch.dir)
    print_check(ch, d.name, check(ch, d.name))


def cmd_check(a):
    d, ch = open_album(a.album, a.channel)
    res = check(ch, d.name)
    print_check(ch, d.name, res)
    sys.exit(1 if res["errors"] else 0)


def track_text(no, song, ch, album_dir):
    lyr = re.search(r"^##\s+Lyrics\s*\n+```[^\n]*\n(.*?)```", song["md"].read_text(encoding="utf-8"), re.M | re.S)
    tpl = (TEMPLATES / "track.md").read_text(encoding="utf-8")
    m = FM.match(tpl)
    values = {"track_no": no, "title": str(song["title"]), "slug": song["slug"], "type": song.get("type"),
              "audio": os.path.relpath(song["wav"], album_dir),
              "duration_s": song.get("duration_s"), "clip_id": str(song["clip_id"])}
    keys = list(yaml.safe_load(m.group(1)) or {})
    body = tpl[m.end():]
    for k, v in (("<NN>", f"{no:02d}"), ("<Song Title>", values["title"]), ("<song-slug>", song["slug"]), ("<ch>", ch),
                 ("<type>/", "".join(f"{x}/" for x in song["md"].parent.relative_to(album_dir.parents[1] / "songs").parts)),
                 ("<lyrics>", lyr.group(1).rstrip("\n") if lyr else "")):
        body = body.replace(k, v)
    head = yaml.safe_dump({k: values.get(k) for k in keys}, sort_keys=False, allow_unicode=True, width=1000)
    return f"---\n{head}---\n{body}"


def cmd_build(a):
    d, ch = open_album(a.album, a.channel)
    res = check(ch, d.name)
    print_check(ch, d.name, res)
    if res["errors"] and not a.force:
        sys.exit("✖ không build: sửa album.md (hoặc --force khi PM chấp nhận lỗi, ghi lý do vào album.md)")
    if not res["songs"] or None in res["songs"]:
        sys.exit("✖ không build được: có bài không nằm trong kho đã đặt tên")
    want = {f"{i:02d}-{s['slug']}.md": track_text(i, s, ch.name, d) for i, s in enumerate(res["songs"], 1)}
    (tdir := d / "tracks").mkdir(exist_ok=True)
    gone = [p for p in sorted(tdir.glob("*.md")) if p.name not in want]
    for p in gone:
        p.unlink()
        print(f"- xoá {rel(p)} (không còn trong tracklist)")
    changed = [n for n, t in want.items() if not (tdir / n).exists() or (tdir / n).read_text(encoding="utf-8") != t]
    for n in changed:
        (tdir / n).write_text(want[n], encoding="utf-8")
    print(f"\n✔ {rel(tdir)}: {len(want)} bài · {len(changed)} file ghi mới/cập nhật · {len(gone)} file xoá")
    if (changed or gone) and (d / "audio" / "master" / f"{d.name}.wav").exists():
        print("⚠ album đã có master: tracklist đổi → ghép lại (audio-album-assembly) trước khi làm video")


def png_size(p):
    try:
        with open(p, "rb") as f:
            h = f.read(24)
    except OSError:
        return None
    return struct.unpack(">II", h[16:24]) if len(h) == 24 and h[:8] == b"\x89PNG\r\n\x1a\n" else None


def last_package(f):
    try:
        return (json.loads(f.read_text()) or [None])[-1]
    except (OSError, ValueError):
        return None


def media(d, size):
    yt = (d / "youtube.md").read_text(encoding="utf-8") if (d / "youtube.md").exists() else ""
    s3 = last_package(d / "s3-package.json")
    if s3 is None and d.name == "short" and d.parent.parent.name == "albums":
        s3 = last_package(d.parent / "s3-package.json")
        s3 = s3 if "short" in ((s3 or {}).get("parts") or {}) else None
    url = URL.search(yt)
    return {"thumb": png_size(d / "thumbnail.png") == size and (d / "thumbnail.jpg").exists(),
            "thumb_any": (d / "thumbnail.png").exists(), "loop": (d / "video" / "loop.mp4").exists(),
            "video": (d / "video" / "video.mp4.json").exists(), "yt": bool(yt), "s3": s3,
            "url": url.group(1) if url else None, "translated": (d / "title-translations.yaml").exists()}


def yn(v):
    return "✔" if v else "–"


def short_next(d, m):
    if m["url"]:
        return [] if m["translated"] else ["upload-youtube-translate"]
    spec = (d / "short.json").exists()
    todo = [] if spec else ["video-shorts: short.json"]
    if not m["thumb"]:
        todo.append("thumbnail-prompt (ảnh dọc 2160×3840)")
    elif spec and not m["video"]:
        todo.append("video.py short")
    if not m["yt"]:
        todo.append("youtube.md (video-shorts)")
    elif m["video"] and not m["s3"]:
        todo.append("shorts.py check → video.py package <album> (một zip: album + Short)")
    if m["s3"]:
        todo.append("CEO: upload + Related video → album")
    return todo


def short_cell(sh, sm):
    if not sh:
        return "–"
    return ("shorts/" + sh["dir"].name[:3] + " (cũ)" if sh["legacy"] else "short/") + (" ✔ S3" if sm["s3"] else " …")


def album_next(res, tracks, master, m, sh, sm):
    if m["url"]:
        todo = [] if m["translated"] else ["upload-youtube-translate"]
        if sh and not sm["url"]:
            todo.append("CEO: upload Short")
        return todo + ["results 48 h / 7 d"]
    if not res["tracklist"]:
        return ["PM + CEO: brief + chọn bài (album.py pool / suggest)"]
    todo = []
    if res["errors"]:
        todo.append(f"album.py check ({len(res['errors'])} lỗi)")
    elif tracks != "✔":
        todo.append("album.py build")
    elif not master:
        todo.append("audio-album-assembly")
    if tracks == "✔" and not m["thumb"]:
        todo.append("thumbnail-prompt" + (" (ảnh chưa 4K + jpg: thumb.py fit)" if m["thumb_any"] else ""))
    elif tracks == "✔" and not m["loop"]:
        todo.append("video.py loop")
    if master and not m["yt"]:
        todo.append("upload-youtube-publish")
    if master and m["loop"] and not m["video"]:
        todo.append("video.py album")
    elif m["video"] and m["yt"] and not m["s3"]:
        todo.append("video.py package")
    if tracks == "✔" and not sh:
        todo.append("video-shorts")
    if m["s3"] and sh and sm["s3"]:
        todo.append("CEO: upload album → Short")
    return todo


def cmd_board(a):
    ch = Channel(channel_dir(a.channel))
    print(f"# Board {ch.name}\n\n## Albums\n")
    print("| album | bài | ước lượng | check | tracks | master | ảnh 4K | loop | video (server) | youtube.md | S3 | Short | "
          "đã đăng | việc tiếp theo |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for name, al in ch.albums.items():
        res = check(ch, name)
        built = sorted(p.name for p in (al["dir"] / "tracks").glob("*.md"))
        tracks = "✔" if built and built == [f"{i:02d}-{s}.md" for i, s in enumerate(res["tracklist"], 1)] else (
            "cũ" if built else "–")
        master = (al["dir"] / "audio" / "master" / f"{name}.wav").exists()
        m = media(al["dir"], ALBUM_SIZE)
        sh = next((s for s in ch.shorts if s["album"] == name), None)
        sm = media(sh["dir"], SHORT_SIZE) if sh else None
        short = short_cell(sh, sm)
        print(f"| {name} | {len(res['tracklist'])} | {mmss(res['est'])} | {'✖ ' + str(len(res['errors'])) if res['errors'] else '✔'} | "
              f"{tracks} | {yn(master)} | {yn(m['thumb']) if m['thumb'] or not m['thumb_any'] else 'chưa 4K'} | {yn(m['loop'])} | "
              f"{yn(m['video'])} | {yn(m['yt'])} | {m['s3']['uploaded'] if m['s3'] else '–'} | {short} | {yn(m['url'])} | "
              f"{' · '.join(album_next(res, tracks, master, m, sh, sm)) or 'xong'} |")
    if ch.shorts:
        print("\n## Shorts\n\n| short | album | bài | short.json | ảnh 9:16 | video | youtube.md | S3 | đã đăng | việc tiếp theo |\n"
              "|---|---|---|---|---|---|---|---|---|---|")
        for s in ch.shorts:
            m = media(s["dir"], SHORT_SIZE)
            todo = short_next(s["dir"], m) + (["video-shorts `shorts.py migrate` (bố cục cũ)"] if s["legacy"] else [])
            print(f"| {s['label']} | {s['album'] or '?'} | {s['song'] or '?'} | {yn((s['dir'] / 'short.json').exists())} | "
                  f"{yn(m['thumb'])} | {yn(m['video'])} | {yn(m['yt'])} | {m['s3']['uploaded'] if m['s3'] else '–'} | "
                  f"{yn(m['url'])} | {' · '.join(todo) or 'xong'} |")
    print(f"\n## Kho bài ({len(ch.songs)} bài đã đặt tên; chi tiết: album.py pool --channel {ch.name})\n")
    pool_summary(ch)


def main():
    ap = argparse.ArgumentParser(description="PM: album từ kho bài của kênh (album.md → tracks/) + board sản xuất")
    sub = ap.add_subparsers(dest="cmd", required=True)
    cmds = {"new": (cmd_new, "album mới: số NNN tiếp theo, albums/NNN-slug/album.md từ templates/album.md + checklist"),
            "pool": (cmd_pool, "kho bài đã đặt tên: bản v1/v2, lượt, loại, thời lượng, số album đã dùng, đoạn short"),
            "check": (cmd_check, "kiểm album.md theo album_rules.md (exit 1 nếu có lỗi)"),
            "suggest": (cmd_suggest, "đề xuất tracklist hợp luật: xen kẽ loại, bài ít dùng trước, hai bản v1/v2 cách xa, "
                                     "≥ length_min[0] + 1 phút (bù phần im lặng bị bỏ khi ghép)"),
            "build": (cmd_build, "ghi tracks/NN-<slug>.md từ album.md (từ chối nếu check lỗi), xoá file bài cũ"),
            "board": (cmd_board, "trạng thái mọi album + Short của kênh và việc tiếp theo")}
    ps = {}
    for name, (fn, text) in cmds.items():
        ps[name] = sub.add_parser(name, help=text)
        ps[name].set_defaults(fn=fn)
        if name in ("new", "pool", "board"):
            ps[name].add_argument("--channel", required=True)
        else:
            ps[name].add_argument("album", help="thư mục channel/<ch>/albums/NNN-slug, hoặc tên NNN-slug")
            ps[name].add_argument("--channel", help="kênh của album khi đưa tên NNN-slug (mặc định: tìm trong channel/*/albums)")
    ps["new"].add_argument("--title", required=True, help="tên làm việc của album (slug lấy từ đây)")
    ps["pool"].add_argument("--type", help="chỉ một loại bài (vd. spoken)")
    ps["pool"].add_argument("--unused", action="store_true", help="chỉ bài chưa nằm trong album nào")
    ps["suggest"].add_argument("--title-song", help="slug bài 1 (mặc định: bài 1 đang có trong album.md, hoặc bài ít dùng nhất hợp luật)")
    ps["suggest"].add_argument("--write", action="store_true", help="ghi tracklist vào album.md rồi chạy check")
    ps["build"].add_argument("--force", action="store_true", help="build dù check còn lỗi (PM ghi lý do vào album.md)")
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

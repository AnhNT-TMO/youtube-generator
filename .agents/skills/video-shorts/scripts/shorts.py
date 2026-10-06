#!/usr/bin/env python3
USAGE = """video-shorts: một Short cho mỗi album, cắt từ đoạn `short` của một bài (song card do audio-song-naming ghi).

  shorts.py new   <album dir> [--song <slug>] [--hook "…"] [--cta "…"] [--version V] [--force]
                                  bài mặc định: album.md brief.short.song, không có thì bài 1 của tracklist
                                  → <album dir>/short/short.md + short.json (đã có short/: --force mới ghi lại)
  shorts.py spec  <short dir>     ghi lại short.json từ short.md + song card (sau khi sửa hook_text / cta_text,
                                  khi audio-song-naming đổi đoạn short của bài, hoặc đổi tên bài: tìm lại bài
                                  theo clip_id rồi sửa song/title/track trong short.md)
  shorts.py check <short dir>     short.md, short.json, thumbnail 9:16, video đã render (video/video.mp4.json),
                                  youtube.md (title, hashtags, link album); exit 1 khi có ❌
  shorts.py list  --channel <ch>  mọi Short của kênh: album, bài, đoạn, ảnh, video, S3, URL
  shorts.py migrate --channel <ch> [--yes]
                                  Short bố cục cũ channel/<ch>/shorts/NNN-slug/ → albums/<album trong short.md>/short/,
                                  sửa đường dẫn tương đối + chữ `shorts/NNN-slug` trong các file; mặc định chỉ in, --yes mới làm

<short dir> = channel/<ch>/albums/NNN-slug/short (bố cục cũ channel/<ch>/shorts/NNN-slug vẫn đọc được).

Chạy từ gốc repo. new/spec đọc YAML (album.md, song card): tự chạy lại bằng .venv của skill.
check/list/migrate chỉ cần python3 (video.py package gọi check).
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SK = Path(__file__).resolve().parents[1]
REPO = SK.parents[2]
VENV_PY = SK / ".venv" / "bin" / "python"
TEMPLATE = REPO / "templates" / "short.md"
FADE_IN = 0.03
FADE_OUT = 0.6
LEAD = 0.1
HOLD = 1.2
KEEP_GAP = 4.0
MIN_CAPTION = 0.8
CTA_SECONDS = 4.0
VOICE_MAX = 1.0
SHORT_MIN = 5.0
SHORT_MAX = 180.0
TITLE_MAX = 100
TITLE_WARN = 60
HASHTAGS_MAX = 60
TAGS_MAX = 500
REQUIRED = ("album", "song", "track", "hook_text", "cta_text")
SHORT_DIR = "short"
LEGACY_DIR = "shorts"


def rel(p):
    try:
        return str(Path(p).resolve().relative_to(REPO))
    except ValueError:
        return str(p)


def die(msg):
    sys.exit(f"❌ {msg}")


def ensure_yaml():
    try:
        import yaml  # noqa: F401
    except ImportError:
        if VENV_PY.exists() and not os.environ.get("VIDEO_SHORTS_VENV"):
            os.execve(str(VENV_PY), [str(VENV_PY), str(Path(__file__).resolve())] + sys.argv[1:],
                      dict(os.environ, VIDEO_SHORTS_VENV="1"))
        die(f"thiếu PyYAML: python3.12 -m venv {rel(SK / '.venv')} && "
            f"{rel(VENV_PY.parent)}/pip install -r {rel(SK / 'requirements.txt')}")


def yaml_front(path):
    import yaml
    m = re.match(r"^---\n(.*?)\n---", Path(path).read_text(), re.S)
    return (yaml.safe_load(m.group(1)) or {}) if m else {}


def flat_value(v):
    v = v.strip()
    if v.startswith('"'):
        try:
            return json.JSONDecoder().raw_decode(v)[0]
        except ValueError:
            pass
    v = re.sub(r"\s+#.*$", "", v).strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        v = v[1:-1]
    return v


def front_matter(path):
    m = re.match(r"^---\n(.*?)\n---", Path(path).read_text(), re.S)
    fm = {}
    for line in (m.group(1).splitlines() if m else []):
        if not line or line.startswith((" ", "#")):
            continue
        k, sep, v = line.partition(":")
        if sep:
            fm[k.strip()] = flat_value(v)
    return fm


def set_fields(path, values):
    text = Path(path).read_text()
    for k, v in values.items():
        val = json.dumps(v, ensure_ascii=False) if (not v or re.search(r"[:#\"'\[\]{}]|^\s|\s$", v)) else v
        pat = re.compile(rf"^{re.escape(k)}:[^\n]*?(\s+#[^\n]*)?$", re.M)
        m = pat.search(text)
        if m:
            text = text[:m.start()] + f"{k}: {val}" + (m.group(1) or "") + text[m.end():]
        else:
            text = text.replace("\n---", f"\n{k}: {val}\n---", 1)
    Path(path).write_text(text)


def filled(v):
    s = str(v or "").strip()
    return "" if not s or s.startswith("<") or s.lower() in ("null", "none", "~") else s


def channel_of(d):
    parts = Path(d).resolve().relative_to(REPO).parts
    if len(parts) < 2 or parts[0] != "channel":
        die(f"{d}: phải nằm trong channel/<ch>/")
    return REPO / "channel" / parts[1]


def youtube_url(d):
    f = Path(d) / "youtube.md"
    if not f.exists():
        return None
    m = re.search(r"\*\*Video URL:\*\*[ \t]*(\S*)", f.read_text())
    url = m.group(1) if m else ""
    return url if url.startswith("http") else None


def channel_cta(ch):
    pub = ch / "publish.md"
    m = re.search(r"`cta_text`[^`\n]*`([^`\n]+)`", pub.read_text()) if pub.exists() else None
    return m.group(1).strip() if m and "<" not in m.group(1) else ""


def song_cards(ch):
    root = ch / "songs"
    typed = sorted(p for p in root.glob("*/*.md") if p.parent.name != "raw" and not p.parent.name.startswith("."))
    return typed + sorted(p for p in root.glob("*.md") if p.name != "catalog.md")


def song_card(ch, slug):
    return next((p for p in song_cards(ch) if slug and p.stem == slug), None)


def load_song(card):
    if not card.exists():
        die(f"không có song card {rel(card)}: bài chưa được audio-song-naming đặt tên?")
    fm = yaml_front(card)
    seg = fm.get("short") or {}
    try:
        t_in, t_out = float(seg["start_s"]), float(seg["end_s"])
    except (KeyError, TypeError, ValueError):
        die(f"{rel(card)} chưa có short.start_s / short.end_s: audio-song-naming chọn đoạn Short trước")
    lines = [{"t0": float(x["t0"]), "t1": float(x["t1"]), "text": str(x["text"]).strip()}
             for x in seg.get("lines") or [] if str(x.get("text") or "").strip()]
    if not lines:
        die(f"{rel(card)}: short.lines trống (cần lời theo câu để chạy chữ trên Short)")
    audio = card.parent / str(fm.get("audio") or f"{card.stem}.wav")
    if not audio.exists():
        die(f"không thấy audio {rel(audio)} của {rel(card)}")
    return {"slug": fm.get("slug") or card.stem, "title": str(fm.get("title") or card.stem), "card": card,
            "clip_id": str(fm.get("clip_id") or ""), "audio": audio, "in": round(t_in, 3), "out": round(t_out, 3), "lines": lines,
            "hook": str(seg.get("hook") or "").strip()}


def captions(lines, t_in, t_out):
    dur = t_out - t_in
    inside = [x for x in sorted(lines, key=lambda x: x["t0"]) if x["t1"] > t_in and x["t0"] < t_out]
    caps = []
    for i, x in enumerate(inside):
        t0 = max(0.0, x["t0"] - t_in - LEAD)
        if i + 1 < len(inside):
            nxt = inside[i + 1]["t0"] - t_in - LEAD
            end = x["t1"] - t_in
            t1 = nxt if nxt - end <= KEEP_GAP else end + HOLD
        else:
            t1 = dur
        caps.append({"t0": round(t0, 2), "t1": round(min(max(t1, t0 + MIN_CAPTION), dur), 2), "text": x["text"]})
    return caps


def build_spec(song, hook, cta):
    dur = song["out"] - song["in"]
    if not SHORT_MIN <= dur <= SHORT_MAX:
        die(f"đoạn {song['in']}–{song['out']} dài {dur:.1f} s: phải trong {SHORT_MIN:.0f}–{SHORT_MAX:.0f} s "
            "(quá 180 s YouTube không coi là Short)")
    caps = captions(song["lines"], song["in"], song["out"])
    if not caps:
        die(f"không dòng lời nào của short.lines nằm trong {song['in']}–{song['out']}")
    return {"audio": rel(song["audio"]), "song": song["slug"], "track": rel(song["card"]),
            "in": song["in"], "out": song["out"], "fade_in": FADE_IN, "fade_out": FADE_OUT, "captions": caps,
            "hook": {"text": hook}, "cta": {"text": cta, "t0": round(dur - CTA_SECONDS, 2)}}


def in_album(d):
    d = Path(d).resolve()
    return d.name == SHORT_DIR and d.parent.parent.name == "albums"


def short_dirs(ch):
    return ([d for d in sorted(ch.glob(f"albums/*/{SHORT_DIR}")) if (d / "short.md").exists()]
            + [d for d in sorted(ch.glob(f"{LEGACY_DIR}/*")) if (d / "short.md").exists()])


def label(d):
    d = Path(d).resolve()
    return f"{d.parent.name}/{d.name}" if in_album(d) else f"{LEGACY_DIR}/{d.name}"


def album_dir(d, fm, ch):
    if in_album(d):
        return Path(d).resolve().parent
    return ch / "albums" / fm["album"] if fm.get("album") else None


def shorts_of(ch):
    out = []
    for d in short_dirs(ch):
        f = d / "short.json"
        out.append((d, front_matter(d / "short.md"), json.loads(f.read_text()) if f.exists() else None))
    return out


def reused_segment(ch, spec, skip=None):
    return next((d for d, _, s in shorts_of(ch) if d != skip and s and s.get("audio") == spec["audio"]
                 and round(s["in"], 2) == round(spec["in"], 2) and round(s["out"], 2) == round(spec["out"], 2)),
                None)


def reused_hook(ch, hook, skip=None):
    low = hook.strip().lower()
    return next((d for d, fm, _ in shorts_of(ch) if d != skip and low
                 and fm.get("hook_text", "").strip().lower() == low), None)


def write_spec(d, spec):
    (d / "short.json").write_text(json.dumps(spec, indent=1, ensure_ascii=False))
    dur = spec["out"] - spec["in"]
    print(f"→ {rel(d / 'short.json')}: {spec['in']:.2f} → {spec['out']:.2f} ({dur:.1f} s) của {spec['audio']}, "
          f"giọng vào ở {spec['captions'][0]['t0']:.2f} s, {len(spec['captions'])} dòng lời")
    for c in spec["captions"]:
        print(f"   {c['t0']:6.2f}–{c['t1']:6.2f}  {c['text']}")
    if spec["captions"][0]["t0"] > VOICE_MAX:
        print(f"⚠️  giọng vào sau {VOICE_MAX:.0f} s: Short phải vào giọng ngay (audio-song-naming chọn lại đoạn)")
    for k in ("hook", "cta"):
        if not spec[k]["text"]:
            print(f"⚠️  chưa có {k}_text: viết vào short.md rồi `shorts.py spec {rel(d)}`")


def cmd_new(a):
    album = Path(a.album).resolve()
    ch = channel_of(album)
    am = album / "album.md"
    if not am.exists():
        die(f"{rel(album)} không có album.md")
    afm = yaml_front(am)
    tracklist = [t for t in (filled(x) for x in afm.get("tracklist") or []) if t]
    short_brief = (afm.get("brief") or {}).get("short")
    chosen = filled(short_brief.get("song")) if isinstance(short_brief, dict) else ""
    slug = filled(a.song) or chosen or (tracklist[0] if tracklist else "")
    if not slug:
        die("không biết Short lấy bài nào: album.md chưa có tracklist (brief.short.song trống thì lấy bài 1); "
            "cho --song <slug>")
    if slug not in tracklist:
        die(f"bài {slug} không có trong tracklist của {album.name}: Related video của Short là album, bài phải ở trong album")
    song = load_song(song_card(ch, slug) or ch / "songs" / "<type>" / f"{slug}.md")
    d = album / SHORT_DIR
    legacy = [x for x, fm, _ in shorts_of(ch) if not in_album(x) and fm.get("album") == album.name]
    if legacy:
        die(f"{album.name} đã có Short ở bố cục cũ {label(legacy[0])}: "
            f"`python3 {rel(Path(__file__).resolve())} migrate --channel {ch.name}` rồi sửa ở {rel(d)}")
    if d.is_dir() and any(d.iterdir()) and not a.force:
        die(f"{rel(d)} đã có (mỗi album một Short): sửa short.md rồi `spec`; --force để ghi lại short.md + short.json")
    hook = (a.hook if a.hook is not None else song["hook"]).strip()
    cta = (a.cta if a.cta is not None else channel_cta(ch)).strip()
    spec = build_spec(song, hook, cta)
    used = reused_segment(ch, spec, skip=d)
    if used:
        die(f"đoạn {spec['in']}–{spec['out']} của {slug} đã dùng ở Short {label(used)}: chọn bài khác (--song) "
            "hoặc để audio-song-naming chọn đoạn khác cho bài này")
    old = sorted(p.name for p in d.iterdir() if p.name not in ("short.md", "short.json")) if d.is_dir() else []
    d.mkdir(exist_ok=True)
    (d / "short.md").write_text(TEMPLATE.read_text().replace("<Song Title>", song["title"]))
    set_fields(d / "short.md", {"album": album.name, "song": slug, "title": song["title"],
                                "track": os.path.relpath(song["card"], d), "hook_text": hook, "cta_text": cta,
                                "version": a.version or "", "clip_id": song["clip_id"]})
    print(f"✔ {rel(d)}/short.md · bài {song['title']} · video đích (Related video) = album {album.name}")
    write_spec(d, spec)
    if old:
        print(f"⚠️  --force: {', '.join(old)} trong {rel(d)} làm cho bản trước: xem lại ảnh / video / youtube.md")
    dup = reused_hook(ch, hook, skip=d)
    if dup:
        print(f"⚠️  hook_text trùng Short {label(dup)}: viết câu khác từ lời đoạn này rồi `shorts.py spec`")
    if not youtube_url(album):
        print(f"⚠️  album {album.name} chưa có Video URL trong youtube.md: đăng album trước, Short sau")


def track_path(d, fm):
    return (d / fm["track"]).resolve() if fm.get("track") else None


def card_path(d, fm, ch):
    track = track_path(d, fm)
    if track and track.exists():
        return track
    return song_card(ch, fm.get("song", "")) or track or ch / "songs" / "<type>" / f"{fm.get('song', '')}.md"


def spec_command(d):
    return f"python3 {rel(Path(__file__).resolve())} spec {rel(d)}"


def same_segment(seg, old):
    if not isinstance(seg, dict) or "in" not in old or "out" not in old:
        return False
    try:
        if abs(float(seg["start_s"]) - old["in"]) > 0.01 or abs(float(seg["end_s"]) - old["out"]) > 0.01:
            return False
    except (KeyError, TypeError, ValueError):
        return False
    texts = {str(x.get("text") or "").strip() for x in seg.get("lines") or []}
    return all(c["text"] in texts for c in old.get("captions") or [])


def find_renamed_song(d, fm, ch):
    cards = {p: yaml_front(p) for p in song_cards(ch)}
    clip, how = filled(fm.get("clip_id")), "clip_id trong short.md"
    album = album_dir(d, fm, ch) if filled(fm.get("album")) or in_album(d) else None
    tracks = album / "tracks" if album else None
    for md in (sorted(tracks.glob("*.md")) if tracks and not clip else []):
        tfm = yaml_front(md)
        if tfm.get("slug") == fm.get("song") and tfm.get("clip_id"):
            clip, how = str(tfm["clip_id"]), f"clip_id của {rel(md)}"
    if clip:
        hits = [p for p, c in cards.items() if str(c.get("clip_id") or "") == clip]
    else:
        f = d / "short.json"
        old = json.loads(f.read_text()) if f.exists() else {}
        hits = [p for p, c in cards.items() if same_segment(c.get("short"), old)]
        how = "đoạn in/out + lời của short.json cũ (short.md chưa có clip_id)"
    if len(hits) != 1:
        die(f"bài {fm.get('song')} không còn trong kho và tìm lại theo {how} ra {len(hits)} song card"
            + (f" ({', '.join(p.stem for p in hits)})" if hits else "")
            + ": sửa `song` + `track` trong short.md cho đúng bài rồi chạy lại `spec`")
    return hits[0], how


def cmd_spec(a):
    d = Path(a.dir).resolve()
    sm = d / "short.md"
    if not sm.exists():
        die(f"{rel(sm)} chưa có: `shorts.py new <album>` trước")
    fm = front_matter(sm)
    ch = channel_of(d)
    if in_album(d) and filled(fm.get("album")) and fm["album"] != d.parent.name:
        die(f"short.md album: {fm['album']} ≠ album chứa Short này ({d.parent.name}): sửa short.md")
    card, how = card_path(d, fm, ch), None
    if not card.exists():
        card, how = find_renamed_song(d, fm, ch)
    elif card != track_path(d, fm):
        how = "slug trong kho (song card đã chuyển thư mục)"
    song = load_song(card)
    spec = build_spec(song, fm.get("hook_text", "").strip(), fm.get("cta_text", "").strip())
    used = reused_segment(ch, spec, skip=d)
    if used:
        die(f"đoạn {spec['in']}–{spec['out']} đã dùng ở Short {label(used)}: chọn đoạn khác cho bài này")
    updates = {}
    if how:
        updates = {"song": song["slug"], "title": song["title"], "track": os.path.relpath(song["card"], d)}
    if song["clip_id"] and fm.get("clip_id") != song["clip_id"]:
        updates["clip_id"] = song["clip_id"]
    if updates:
        set_fields(sm, updates)
    if how:
        old_title = fm.get("title", "")
        if old_title and old_title != song["title"]:
            sm.write_text(sm.read_text().replace(f"# Short: {old_title}", f"# Short: {song['title']}", 1))
        f = d / "short.json"
        old_audio = json.loads(f.read_text()).get("audio") if f.exists() else "—"
        if song["slug"] == fm.get("song"):
            print(f"↻ song card của {song['slug']} đã chuyển chỗ: {fm.get('track') or '—'} → {updates['track']}, tìm lại theo {how}")
        else:
            print(f"↻ bài đã đổi tên: {fm.get('song')} → {song['slug']} ({song['title']}), tìm lại theo {how}")
        print(f"   short.md: {', '.join(updates)} · short.json audio: {old_audio} → {spec['audio']}")
        ym = d / "youtube.md"
        if old_title and ym.exists() and old_title in ym.read_text():
            print(f"⚠️  youtube.md của Short còn tên cũ \"{old_title}\": sửa title/description")
    elif "clip_id" in updates:
        print(f"✔ short.md: thêm clip_id {song['clip_id']}")
    write_spec(d, spec)


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


def card_segment(card):
    if not card.exists():
        return None
    m = re.search(r"^short:[ \t]*\n((?:[ \t]+.*\n?)*)", card.read_text(), re.M)
    got = [re.search(rf"^[ \t]+{k}:[ \t]*([\d.]+)", m.group(1), re.M) if m else None for k in ("start_s", "end_s")]
    return tuple(float(g.group(1)) for g in got) if all(got) else None


def cmd_check(a):
    d = Path(a.dir).resolve()
    ch = channel_of(d)
    err, warn = [], []
    sm = d / "short.md"
    if not sm.exists():
        die(f"{rel(sm)} chưa có")
    fm = front_matter(sm)
    for k in REQUIRED:
        if not fm.get(k):
            err.append(f"short.md thiếu {k}")
    card = card_path(d, fm, ch) if fm.get("track") or fm.get("song") else None
    moved = card is not None and not card.exists()
    if moved:
        err.append(f"bài {fm.get('song')} không còn trong kho ({rel(card)} không có; đã đổi tên?): "
                   f"`{spec_command(d)}` tìm lại theo clip_id và sửa short.md + short.json")
    elif card and fm.get("track") and card != track_path(d, fm):
        err.append(f"short.md track `{fm['track']}` không còn; song card đang ở {rel(card)} → `{spec_command(d)}` "
                   "(hoặc audio-song-naming `songs.py migrate`)")
    album = album_dir(d, fm, ch)
    if in_album(d) and fm.get("album") and fm["album"] != album.name:
        err.append(f"short.md album: {fm['album']} ≠ album chứa Short này ({album.name})")
    elif album and not (album / "album.md").exists():
        err.append(f"short.md album: {fm['album']} không có ở {rel(ch / 'albums')}")
    url = youtube_url(album) if album else None
    if album and not url:
        warn.append(f"album {fm.get('album')} chưa có Video URL trong youtube.md: đăng album trước, "
                    "rồi điền link vào description + pinned comment của Short")
    dup = reused_hook(ch, fm.get("hook_text", ""), skip=d)
    if dup:
        err.append(f"hook_text trùng Short {label(dup)}: mỗi Short một câu hook riêng")
    if not in_album(d):
        warn.append(f"Short ở bố cục cũ {label(d)}: `python3 {rel(Path(__file__).resolve())} migrate --channel {ch.name}` "
                    "chuyển vào albums/<album>/short/")
    spec_f = d / "short.json"
    dur = None
    if spec_f.exists():
        spec = json.loads(spec_f.read_text())
        dur = spec["out"] - spec["in"]
        if not SHORT_MIN <= dur <= SHORT_MAX:
            err.append(f"độ dài {dur:.1f} s ngoài {SHORT_MIN:.0f}–{SHORT_MAX:.0f} s (quá 180 s YouTube không coi là Short)")
        if not moved and not (REPO / spec["audio"]).exists():
            err.append(f"short.json trỏ tới audio không có: {spec['audio']}")
        if spec["captions"] and spec["captions"][0]["t0"] > VOICE_MAX:
            err.append(f"giọng vào ở {spec['captions'][0]['t0']:.2f} s: phải ≤ {VOICE_MAX:.0f} s (người xem quyết định trong ~1 s)")
        if not spec["captions"]:
            err.append("short.json không có dòng lời nào")
        if spec["hook"].get("text") != fm.get("hook_text") or spec["cta"].get("text") != fm.get("cta_text"):
            err.append("short.json khác hook_text/cta_text trong short.md: `shorts.py spec`")
        seg = card_segment(card) if card and not moved else None
        if seg and (abs(seg[0] - spec["in"]) > 0.01 or abs(seg[1] - spec["out"]) > 0.01):
            err.append(f"song card đã đổi đoạn short ({seg[0]}–{seg[1]}) ≠ short.json ({spec['in']}–{spec['out']}): "
                       "`shorts.py spec` rồi render lại")
    else:
        err.append("chưa có short.json: `shorts.py spec`")
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
        if vd > SHORT_MAX:
            err.append(f"video dài {vd:.1f} s > {SHORT_MAX:.0f} s")
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
            if re.search(r"[<>]", t):
                err.append("title còn placeholder <...> hoặc ký tự < > (YouTube không nhận)")
        if desc:
            tags_in = re.findall(r"(?<!\w)#\w+", desc)
            if len(tags_in) > HASHTAGS_MAX:
                err.append(f"{len(tags_in)} hashtag > {HASHTAGS_MAX}: YouTube bỏ qua toàn bộ hashtag của video")
            elif not 3 <= len(tags_in) <= 5:
                warn.append(f"{len(tags_in)} hashtag: nên 3–5, đúng chủ đề")
            if re.search(r"[<>]", desc):
                err.append("description còn placeholder <...> hoặc ký tự < >")
            if url and url not in desc:
                err.append(f"description chưa có link album {url}")
            if re.search(r"\b(AI[- ]generated|made with AI|Suno)\b", desc, re.I):
                err.append("description có dòng AI/Suno: khai báo AI bằng mục Altered content trong Studio")
        if pin and url and url not in pin:
            warn.append("pinned comment chưa có link album")
        if pin and re.search(r"[<>]", pin):
            err.append("pinned comment còn placeholder <...>")
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


def packaged(d):
    if (d / "s3-package.json").exists():
        return True
    f = d.parent / "s3-package.json"
    try:
        rec = (json.loads(f.read_text()) or [{}])[-1] if in_album(d) and f.exists() else {}
    except ValueError:
        return False
    return "short" in (rec.get("parts") or {})


def cmd_list(a):
    rows = shorts_of(REPO / "channel" / a.channel)
    if not rows:
        print("chưa có Short nào")
        return
    print("| Short | album | bài | đoạn | hook | ảnh | video | S3 | URL |\n|---|---|---|---|---|---|---|---|---|")
    for d, fm, spec in rows:
        seg = f"{spec['in']:.2f}–{spec['out']:.2f}" if spec else "—"
        print(f"| {label(d)} | {fm.get('album') or '—'} | {fm.get('title') or fm.get('song') or '?'} | {seg} | "
              f"{fm.get('hook_text') or '—'} | {'✔' if (d / 'thumbnail.png').exists() else '—'} | "
              f"{'✔' if (d / 'video' / 'video.mp4.json').exists() else '—'} | "
              f"{'✔' if packaged(d) else '—'} | {youtube_url(d) or '—'} |")


REL_PATH = re.compile(r"(?<![\w./-])((?:\.\./)+[^\s`'\"()\[\]<>|,;]*)")
TEXT_SUFFIXES = (".md", ".json", ".yaml", ".yml", ".txt")


def moved_path(p, src, dst):
    try:
        return dst / p.relative_to(src)
    except ValueError:
        return p


def retarget(text, src, dst, old_name, new_name):
    def fix(m):
        target = Path(os.path.normpath(src / m.group(1)))
        new = os.path.relpath(moved_path(target, src, dst), dst)
        return new + ("/" if m.group(1).endswith("/") and not new.endswith("/") else "")
    text = REL_PATH.sub(fix, text)
    return re.sub(rf"(?<![\w-]){re.escape(old_name)}(?![\w-])", new_name, text)


def server_job(d):
    return re.sub(r"[^A-Za-z0-9_.-]+", "__", "/".join(Path(d).relative_to(REPO).parts[1:]))


def migrate_plan(ch):
    plans, errs, taken = [], [], {}
    for src in sorted(p for p in (ch / LEGACY_DIR).glob("*") if (p / "short.md").exists()):
        fm = front_matter(src / "short.md")
        name = filled(fm.get("album"))
        album = ch / "albums" / name if name else None
        dst = album / SHORT_DIR if album else None
        if not name:
            errs.append(f"{label(src)}: short.md không có album: điền `album:` rồi chạy lại")
        elif not (album / "album.md").exists():
            errs.append(f"{label(src)}: album {name} không có ở {rel(ch / 'albums')}")
        elif dst.exists():
            errs.append(f"{label(src)}: {rel(dst)} đã có (mỗi album một Short): gộp tay hoặc xoá một bên rồi chạy lại")
        elif name in taken:
            errs.append(f"{label(src)}: album {name} đã nhận Short {label(taken[name])} (mỗi album một Short)")
        else:
            taken[name] = src
            old_name, new_name = f"{LEGACY_DIR}/{src.name}", f"albums/{name}/{SHORT_DIR}"
            edits = []
            for f in sorted(x for x in src.rglob("*") if x.is_file() and x.suffix in TEXT_SUFFIXES
                            and "thumbnail-drafts" not in x.relative_to(src).parts):
                text = f.read_text()
                new = retarget(text, src, dst, old_name, new_name)
                if new != text:
                    edits.append((f.relative_to(src), text, new))
            plans.append({"src": src, "dst": dst, "edits": edits})
    return plans, errs


def cmd_migrate(a):
    ch = REPO / "channel" / a.channel
    if not ch.is_dir():
        die(f"không có channel/{a.channel}")
    plans, errs = migrate_plan(ch)
    mode = "làm" if a.yes else "thử (chưa đổi gì; thêm --yes để làm)"
    print(f"== migrate Short {a.channel}: {len(plans)} thư mục {LEGACY_DIR}/NNN-slug → albums/<album>/{SHORT_DIR}/ · {mode}")
    for pl in plans:
        print(f"  chuyển {rel(pl['src'])} → {rel(pl['dst'])}")
        for f, old, new in pl["edits"]:
            changed = [(o, n) for o, n in zip(old.splitlines(), new.splitlines()) if o != n]
            for o, n in changed:
                print(f"    sửa {f}: {o.strip()[:90]}\n         → {n.strip()[:90]}")
        rj = pl["src"] / "video" / "remote.json"
        if rj.exists() and json.loads(rj.read_text()).get("video"):
            print(f"    ⚠️  video đã render trên server theo job {server_job(pl['src'])}; job mới là {server_job(pl['dst'])}: "
                  f"sau migrate chạy lại `video.py short {rel(pl['dst'])}` (~1–2 phút) trước khi đóng gói album (`video.py package <album>`)")
    for e in errs:
        print(f"  ❌ {e}")
    if not plans and not errs:
        print(f"Không còn Short nào ở {LEGACY_DIR}/.")
    if not a.yes:
        sys.exit(1 if errs else 0)
    for pl in plans:
        os.replace(pl["src"], pl["dst"])
        for f, _, new in pl["edits"]:
            (pl["dst"] / f).write_text(new)
        print(f"✔ {rel(pl['dst'])}")
    if plans:
        print(f"→ `python3 {rel(Path(__file__).resolve())} check <short dir>` cho từng Short đã chuyển")
    sys.exit(1 if errs else 0)


def main():
    ap = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("new")
    p.add_argument("album")
    p.add_argument("--song", help="slug bài trong tracklist (mặc định: album.md brief.short.song, rồi bài 1)")
    p.add_argument("--hook", help="hook_text (mặc định: short.hook của song card)")
    p.add_argument("--cta", help="cta_text (mặc định: `cta_text` trong channel/<ch>/publish.md → Shorts)")
    p.add_argument("--version", help="version đóng gói đang thử (R&D / PM)")
    p.add_argument("--force", action="store_true", help="làm thêm Short cho album đã có Short")
    p = sub.add_parser("spec")
    p.add_argument("dir")
    p = sub.add_parser("check")
    p.add_argument("dir")
    p = sub.add_parser("list")
    p.add_argument("--channel", required=True)
    p = sub.add_parser("migrate")
    p.add_argument("--channel", required=True)
    p.add_argument("--yes", action="store_true", help="chuyển thật (mặc định chỉ in thay đổi)")
    a = ap.parse_args()
    if a.cmd in ("new", "spec"):
        ensure_yaml()
    {"new": cmd_new, "spec": cmd_spec, "check": cmd_check, "list": cmd_list, "migrate": cmd_migrate}[a.cmd](a)


if __name__ == "__main__":
    main()

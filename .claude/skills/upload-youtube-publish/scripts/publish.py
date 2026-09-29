#!/usr/bin/env python3
USAGE = """upload-youtube-publish helper.

  chapters <album>                    chapters của video album, đọc từ <album>/assembly.json (audio-album-assembly);
                                      dán dưới dòng TRACKLIST của mẫu description (khối không có dòng TRACKLIST)
  check    <album> [--video <file>]   kiểm youtube.md trước khi dán vào YouTube Studio (mẫu description của kênh,
                                      chapters = assembly.json, độ dài master theo album_rules.md, độ dài video,
                                      kho câu + tên kênh khác, tags, thumbnail)
  tags     [<album>] [--try "a, b"] [--expand "seed, seed"] [--own "tên bài"] [--trends]
                                      research tags bằng YouTube autocomplete (có người gõ không, người gõ tìm gì)
                                      + --trends: lượng tìm Google Trends (YouTube Search, 5 năm) cho từng tag

Chạy từ gốc repo. <album> = channel/<ch>/albums/NNN-slug.
"""
import argparse
import json
import math
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BANK = ROOT / "research" / "phrase-bank"
RAW_GLOB = "raw/videos-*.json"
ADDRESSEES = {"lord", "jesus", "god", "father", "abba", "yahweh", "yeshua"}
PLEA_END = re.compile(r"🙏|\||\s-\s|—")
NAME_TAIL = {"official", "music", "channel", "tv"}
FRESH_DAYS = 30
TITLE_MAX = 70
TAGS_FILL_MIN = 470
SUGGEST = "https://suggestqueries.google.com/complete/search"
TRENDS_MIN = 1.0
CHAPTER_MIN_GAP = 10
LAST_CHAPTER_MARGIN = 10
DURATION_TOLERANCE = 3.0
BANK_MIN_WORDS = 4
TS_RE = re.compile(r"^\d{1,2}:\d{2}(:\d{2})?\s")


def fmt(t):
    t = int(t)
    h, m, s = t // 3600, t % 3600 // 60, t % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def parse_ts(s):
    v = 0
    for p in s.split(":"):
        v = v * 60 + int(p)
    return v


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True).stdout.strip()
    return float(out)


def front_matter(md):
    import yaml
    m = re.match(r"^---\n(.*?)\n---", Path(md).read_text(), re.S)
    return (yaml.safe_load(m.group(1)) or {}) if m else {}


def assembly(album):
    f = Path(album) / "assembly.json"
    return json.loads(f.read_text()) if f.exists() else None


def chapters_of(asm):
    rows = sorted(asm.get("tracks") or [], key=lambda t: int(t["track_no"]))
    return [(0 if i == 0 else int(math.floor(float(t["start_s"]))), str(t["title"]).strip())
            for i, t in enumerate(rows)]


def track_titles(album):
    out = {}
    for md in sorted((Path(album) / "tracks").glob("*.md")):
        fm = front_matter(md)
        if fm.get("track_no"):
            out[int(fm["track_no"])] = str(fm.get("title", "")).strip()
    return [out[n] for n in sorted(out)]


def known_duration(album, video):
    if video:
        return duration(video), f"file {video}"
    probe = Path(album) / "video" / "video.mp4.json"
    if probe.exists():
        return float(json.loads(probe.read_text())["format"]["duration"]), "video/video.mp4.json (video trên server)"
    return None, None


def chapter_problems(chapters, total=None):
    err = []
    ts = [t for t, _ in chapters]
    if not ts:
        return ["không có chapter nào"]
    if ts[0] != 0:
        err.append("chapter đầu phải là 0:00")
    if len(ts) < 3:
        err.append("cần ít nhất 3 chapters (YouTube không tạo chapters khi ít hơn)")
    for k in range(1, len(ts)):
        if ts[k] - ts[k - 1] < CHAPTER_MIN_GAP:
            err.append(f"chapter {chapters[k - 1][1]} → {chapters[k][1]}: cách nhau {ts[k] - ts[k - 1]} s "
                       f"< {CHAPTER_MIN_GAP} s hoặc không tăng dần")
    if total is not None and ts[-1] >= total - LAST_CHAPTER_MARGIN:
        err.append(f"chapter cuối {fmt(ts[-1])} vượt/quá sát độ dài {fmt(total)}")
    return err


def cmd_chapters(a):
    album = Path(a.album)
    asm = assembly(album)
    if not asm:
        sys.exit(f"❌ {album}/assembly.json chưa có: audio-album-assembly ghép album trước")
    chapters = chapters_of(asm)
    total = float(asm.get("duration_s") or 0) or None
    print(f"# {album.name}: {asm.get('master')} ({fmt(total) if total else '?'}), {len(chapters)} bài")
    print("dán khối dưới dòng TRACKLIST của mẫu description (mẫu kênh đã có dòng đó)\n")
    print("```")
    for t, title in chapters:
        print(f"{fmt(t)} {title}")
    print("```\n")
    rows = sorted(asm["tracks"], key=lambda t: int(t["track_no"]))
    print("| # | chapter | start_s | bài | type |\n|---|---|---|---|---|")
    for (t, title), r in zip(chapters, rows):
        print(f"| {int(r['track_no']):02d} | {fmt(t)} | {float(r['start_s']):.2f} | {title} | {r.get('type', '')} |")
    problems = chapter_problems(chapters, total)
    names = [n for _, n in chapters]
    want = track_titles(album)
    if want and want != names:
        problems.append(f"tên/thứ tự bài trong assembly.json khác tracks/*.md: {names} vs {want}")
    for p in problems:
        print(f"❌ {p}")
    sys.exit(1 if problems else 0)


def code_block(text, heading):
    i = text.find(heading)
    if i < 0:
        return None
    m = re.search(r"```[a-z]*\n(.*?)\n```", text[i:], re.S)
    return m.group(1) if m else None


def section(text, heading):
    i = text.find(heading)
    if i < 0:
        return ""
    j = text.find("\n## ", i + len(heading))
    return text[i:j if j > 0 else len(text)]


def tags_len(tags):
    return sum(len(t) + (2 if " " in t else 0) for t in tags) + max(0, len(tags) - 1)


def words(s):
    return re.findall(r"[^\W_]+", re.sub(r"[’‘'`´]", "", str(s or "").lower()))


def contains_run(hay, needle):
    n = len(needle)
    return n and any(hay[i:i + n] == needle for i in range(len(hay) - n + 1))


def plea_part(title):
    return PLEA_END.split(str(title or ""), 1)[0]


def without_addressee(ws):
    i = 0
    while i < len(ws) and ws[i] in ADDRESSEES:
        i += 1
    return ws[i:]


def core(text):
    return without_addressee(words(text))


def grams(ws):
    n = BANK_MIN_WORDS
    return {tuple(ws[i:i + n]) for i in range(len(ws) - n + 1)}


def longest_run(a, b):
    best, at = 0, 0
    prev = [0] * (len(b) + 1)
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best, at = cur[j], i
        prev = cur
    return tuple(a[at - best:at])


def shared_run(ours, theirs):
    if len(ours) < BANK_MIN_WORDS:
        return tuple(ours) if len(ours) >= 2 and ours == theirs else ()
    return longest_run(ours, theirs) if grams(ours) & grams(theirs) else ()


def thumb_sentence(thumb):
    text = " / ".join(map(str, thumb)) if isinstance(thumb, list) else str(thumb or "")
    return re.sub(r"\[[^\]]*\]", " ", text)


def load_bank():
    import yaml
    entries, names = {}, set()
    for f in (sorted(BANK.glob("*.yaml")) if BANK.is_dir() else []):
        doc = yaml.safe_load(f.read_text()) or {}
        if not isinstance(doc, dict):
            continue
        names |= {str(c["channel"]) for c in doc.get("channels") or [] if isinstance(c, dict) and c.get("channel")}
        for e in doc.get("entries") or []:
            if isinstance(e, dict) and e.get("id"):
                entries[str(e["id"])] = e
                if e.get("channel"):
                    names.add(str(e["channel"]))
    return entries, names


def bank_phrases(entry):
    return [("title", core(plea_part(entry.get("title")))), ("thumbnail", core(thumb_sentence(entry.get("thumb_text"))))]


def raw_titles():
    files = sorted(BANK.glob(RAW_GLOB)) if BANK.is_dir() else []
    videos, chans, taken = {}, {}, {}
    for f in files:
        data = json.loads(f.read_text())
        for cid, c in (data.get("channels") or {}).items():
            chans[cid] = c.get("title") or cid
        for vid, v in (data.get("videos") or {}).items():
            videos[vid] = v
            taken[vid] = data.get("taken_at") or ""
    rows, index = [], {}
    for vid, v in videos.items():
        ws = core(plea_part(v.get("title")))
        if len(ws) < 2:
            continue
        age = 1.0
        try:
            age = max(1.0, (datetime.fromisoformat(taken[vid].replace("Z", "+00:00"))
                            - datetime.fromisoformat(str(v["published"]).replace("Z", "+00:00"))).total_seconds() / 86400)
        except (KeyError, ValueError):
            pass
        rows.append({"id": vid, "title": v.get("title", ""), "channel": chans.get(v.get("ch"), v.get("ch") or "?"),
                     "vpd": round(float(v.get("views") or 0) / age), "ws": ws})
        i = len(rows) - 1
        for g in grams(ws) or {tuple(ws)}:
            index.setdefault(g, set()).add(i)
    return (files[-1].name if files else None), rows, index


def raw_hits(ours, rows, index):
    if len(ours) < BANK_MIN_WORDS:
        return [rows[i] for i in index.get(tuple(ours), ()) if rows[i]["ws"] == ours]
    hit = set()
    for g in grams(ours):
        hit |= index.get(g, set())
    return [rows[i] for i in hit]


def channels_using(run, rows, index):
    if len(run) < BANK_MIN_WORDS:
        cand = index.get(tuple(run), ())
    else:
        cand = index.get(tuple(run[:BANK_MIN_WORDS]), ())
    return {rows[i]["channel"] for i in cand if contains_run(rows[i]["ws"], list(run))}


def name_words(name):
    ws = words(name)
    while len(ws) > 1 and ws[-1] in NAME_TAIL:
        ws = ws[:-1]
    return ws


def check_branding(texts, names, vocab, err, warn):
    for where, text in texts.items():
        ws = words(text)
        for name in sorted(names):
            nw = name_words(name)
            if not nw or not contains_run(ws, nw):
                continue
            if all(w in vocab for w in nw):
                warn.append(f"{where} có đúng tên kênh \"{name}\" (chỉ gồm chữ thể loại mà mẫu kênh mình cũng dùng: "
                            "không tính là branding, nhưng tìm cụm này sẽ ra kênh đó)")
            else:
                err.append(f"{where} có tên kênh khác \"{name}\": không bao giờ lấy tên / branding của kênh khác")


def listed_ids(ytmd):
    m = re.search(r"\*\*Kho câu[^*]*:\*\*[ \t]*(.*)", ytmd)
    raw = m.group(1) if m else ""
    if "<" in raw:
        return []
    return [x for x in re.split(r"[,;\s`]+", raw) if re.fullmatch(r"[\w.:-]+", x) and x.lower() not in ("không", "none")]


def brief_ids(brief):
    ids = brief.get("phrase_bank") or []
    return [str(x) for x in ([ids] if isinstance(ids, str) else ids) if x and not str(x).startswith("<")]


def filled(v):
    s = str(v or "").strip()
    return "" if s.startswith("<") else s


def album_key(album):
    p = Path(album).resolve()
    return str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(album)


def is_fresh(e):
    if e.get("fresh") is not None:
        return bool(e["fresh"])
    return float(e.get("age_days") or 1e9) <= FRESH_DAYS


def check_bank(album, brief, y, title, ch_text, err, warn, info):
    ids = listed_ids(y)
    wanted = brief_ids(brief)
    for i in wanted:
        if i not in ids:
            err.append(f"album.md brief.phrase_bank có {i} nhưng youtube.md chưa ghi ở dòng **Kho câu (phrase bank):**")
    entries, names = load_bank()
    thumb, bar = filled(brief.get("thumbnail_text")), filled(brief.get("bar_line"))
    vocab = set(words(f"{code_block(ch_text, '## Description YouTube mặc định') or ''} "
                      f"{code_block(ch_text, '## Tags YouTube mặc định') or ''}"))
    check_branding({"title": title or "", "chữ thumbnail (brief.thumbnail_text)": thumb,
                    "thanh dưới thumbnail (brief.bar_line)": bar}, names, vocab, err, warn)
    if not entries:
        if ids or wanted:
            warn.append(f"không đọc được kho câu research/phrase-bank/*.yaml: chưa kiểm id {ids or wanted}, used_by, tên kênh khác")
        return ids
    for i in sorted(set(ids) | set(wanted)):
        if i not in entries:
            warn.append(f"id {i} không có trong kho câu research/phrase-bank")
    key = album_key(album)
    for i in wanted:
        e = entries.get(i)
        if e is not None and key not in {str(x).rstrip("/") for x in e.get("used_by") or []}:
            warn.append(f"kho câu {i}: used_by chưa có album này → PM: yt.py bank use {i} --by {key}")
    ours = {k: v for k, v in (("title", core(plea_part(title))), ("chữ thumbnail", core(thumb))) if len(v) >= 2}
    raw_name, rows, index = raw_titles()
    seen = set()
    for eid, e in entries.items():
        for kind, phrase in bank_phrases(e):
            for where, ws in ours.items():
                run = shared_run(ws, phrase)
                if not run or (where, eid) in seen:
                    continue
                seen.add((where, eid))
                used = f" · {len(channels_using(run, rows, index))} kênh có cụm này trong title ({raw_name})" if rows else ""
                age = "fresh" if is_fresh(e) else f"{e.get('age_days')} ngày tuổi"
                info.append(f"{where} trùng {len(run)} chữ liền với kho {eid} ({kind}: \"{' '.join(run)}\") · "
                            f"vpd {e.get('vpd')} · x{e.get('vpd_x')} · {age}{used}")
                if eid not in wanted:
                    warn.append(f"{where} dựa trên kho {eid} nhưng album.md brief.phrase_bank chưa ghi id này")
    for where, ws in ours.items():
        hits = sorted((r for r in raw_hits(ws, rows, index) if r["id"] not in entries), key=lambda r: -r["vpd"])
        if hits:
            eg = " · ".join(f"\"{r['title'][:60]}\" ({r['channel']}, {r['vpd']}/d)" for r in hits[:2])
            warn.append(f"{where} trùng ≥ {BANK_MIN_WORDS} chữ liền (hoặc cả câu) với {len(hits)} title của "
                        f"{len({r['channel'] for r in hits})} kênh ngoài kho ({raw_name}), vd. {eg}")
    return ids


def check_title(title, total, err):
    if len(title) > TITLE_MAX:
        err.append(f"title {len(title)} ký tự > {TITLE_MAX}: YouTube cắt phần sau trên search/mobile; "
                   "rút gọn theo SKILL.md → Title")
    if re.search(r"[<>]", title):
        err.append("title có ký tự < hoặc > (placeholder, YouTube không nhận)")
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:-\s*)?(?:hours?|hrs?)\b", title, re.I)
    if m and total and total < float(m.group(1)) * 3600 - 60:
        err.append(f"title ghi {m.group(0)} nhưng video dài {fmt(total)}")


def check_description(desc, ch_text, chapters, err, warn):
    if len(desc) > 5000:
        err.append(f"description {len(desc)} ký tự > 5000")
    if re.search(r"[<>]", desc):
        err.append("description có ký tự < hoặc > (placeholder, YouTube không nhận)")
    tpl = code_block(ch_text, "## Description YouTube mặc định")
    if not tpl:
        err.append("publish.md của kênh chưa có khối ``` dưới ## Description YouTube mặc định")
    else:
        holes = [l.strip() for l in tpl.splitlines() if re.search(r"<[^>\n]+>", l)]
        if holes:
            err.append(f"mẫu description trong publish.md còn chỗ <…> ({len(holes)} dòng, vd. {holes[0][:50]}): "
                       "chờ CEO gửi mẫu của kênh, chưa đăng được")
        for line in tpl.splitlines():
            if not line.strip() or re.search(r"<[^>\n]+>", line):
                continue
            if line.startswith("["):
                if line.strip() in desc:
                    err.append(f"description còn placeholder của mẫu: {line.strip()[:60]}")
            elif line not in desc:
                err.append(f"description thiếu dòng của mẫu kênh: {line[:60]}")
    headings = [l for l in desc.splitlines() if l.strip().rstrip(":").upper() == "TRACKLIST"]
    if len(headings) > 1:
        err.append(f"description có {len(headings)} dòng TRACKLIST: mẫu kênh đã có dòng này, chỉ dán các dòng chapter "
                   "của `publish.py chapters` bên dưới")
    if len(re.findall(r"(?<!\w)#\w+", desc)) > 60:
        err.append("quá 60 hashtag: YouTube bỏ qua toàn bộ hashtag của video")
    lines = [l for l in desc.splitlines() if TS_RE.match(l)]
    got = [(parse_ts(l.split()[0]), l.split(None, 1)[1].strip()) for l in lines]
    stray = [l for l in desc.splitlines() if not TS_RE.match(l) and re.search(r"(?<![\w:])\d{1,2}:\d{2}(?![\w])", l)]
    if stray:
        warn.append(f"description có timestamp ngoài TRACKLIST ({stray[0][:50]}): YouTube có thể không tạo chapters")
    if not got:
        err.append("description chưa có chapters (dòng dạng `0:00 Title`): `publish.py chapters <album>`")
    elif chapters is not None and got != chapters:
        err.append("chapters trong description khác assembly.json: dán lại khối của `publish.py chapters <album>`")
    return dict(got)


def check_comment(comment, chapters, err):
    if len(comment) > 10000:
        err.append(f"comment {len(comment)} ký tự > 10000")
    if re.search(r"<[^>\n]+>|\[[^\]\n]*(?:TODO|điền)[^\]\n]*\]", comment):
        err.append("pinned comment còn placeholder")
    for m in re.finditer(r"(?<![\d:])(\d{1,2}:\d{2}(?::\d{2})?)\s+(.+)", comment):
        t, rest = parse_ts(m.group(1)), m.group(2)
        if chapters and (t not in chapters or not rest.startswith(chapters[t])):
            err.append(f"comment: `{m.group(0)[:50]}` không khớp chapter nào trong description")


def check_tags(y, ch_text, err, warn):
    tags_txt = code_block(y, "## Tags")
    if not tags_txt:
        err.append("thiếu khối tags trong ## Tags")
        return
    tags = [t.strip() for t in tags_txt.replace("\n", ",").split(",") if t.strip()]
    n = tags_len(tags)
    if n > 500:
        err.append(f"tags {n}/500 ký tự (tính cả ngoặc kép cho tag có dấu cách)")
    low = [t.lower() for t in tags]
    dups = {t for t in low if low.count(t) > 1}
    if dups:
        err.append(f"tag trùng: {sorted(dups)}")
    dtpl = code_block(ch_text, "## Tags YouTube mặc định")
    if dtpl:
        defaults = [t.strip().lower() for t in dtpl.split(",") if t.strip()]
        if any("<" in t for t in defaults):
            err.append("tags mặc định trong publish.md còn chỗ <…>: kênh chưa chốt tags mặc định")
            defaults = [t for t in defaults if "<" not in t]
        miss = [t for t in defaults if t not in low]
        if miss:
            err.append(f"thiếu tag mặc định của kênh: {miss}")
        extra = len([t for t in low if t not in defaults])
        if not extra:
            warn.append("chưa có tag riêng của album (chọn qua `publish.py tags --expand`)")
    if n < TAGS_FILL_MIN:
        warn.append(f"tags mới {n}/500 ký tự: thêm tag riêng của album cho tới ≥ {TAGS_FILL_MIN}")
    if not re.search(r"autocomplete|trends", section(y, "## Tags").lower()):
        warn.append("bảng tag chưa có cột bằng chứng (Trends / autocomplete): `publish.py tags <album>`")
    print(f"tags: {len(tags)} tag, {n}/500 ký tự")


def check_thumbnail(album, err, warn):
    thumb, jpg = album / "thumbnail.png", album / "thumbnail.jpg"
    if not thumb.exists() or (thumb.stat().st_size > 2 * 1024 * 1024 and jpg.exists()):
        thumb = jpg
    if not thumb.exists():
        warn.append("không thấy thumbnail.png/jpg trong thư mục album")
        return
    size = thumb.stat().st_size
    if size > 2 * 1024 * 1024:
        err.append(f"thumbnail {size / 1e6:.2f} MB > 2 MB: xuất JPG (sips -s format jpeg -s formatOptions 90)")
    elif thumb == jpg:
        print(f"thumbnail: upload {jpg.name} ({size / 1e6:.2f} MB)")


def check_length(ch_dir, master_s, err, warn):
    rules = ch_dir / "album_rules.md"
    if not master_s or not rules.exists():
        return
    try:
        lo, hi = (float(x) for x in front_matter(rules).get("length_min"))
    except (TypeError, ValueError):
        warn.append(f"{rules.name} không có length_min: [min, max] (phút): chưa kiểm độ dài master")
        return
    if not lo * 60 <= master_s <= hi * 60:
        err.append(f"master {fmt(master_s)} ngoài {lo:g}–{hi:g} phút ({rules.name} length_min): "
                   "PM thêm/bớt bài trong album.md rồi ghép lại (audio-album-assembly)")


def cmd_check(a):
    album = Path(a.album)
    ch_dir = album.parent.parent
    ym = album / "youtube.md"
    if not ym.exists():
        sys.exit(f"❌ {ym} chưa có: soạn theo templates/youtube.md")
    y = ym.read_text()
    ch_text = "\n".join(f.read_text() for f in (ch_dir / "publish.md", ch_dir / "channel.md") if f.exists())
    err, warn, info = [], [], []
    brief = (front_matter(album / "album.md").get("brief") or {}) if (album / "album.md").exists() else {}
    if not (album / "album.md").exists():
        warn.append("không có album.md: không đối chiếu được brief của PM")
    elif not brief.get("title_direction") or str(brief.get("title_direction")).startswith("<"):
        warn.append("album.md chưa có brief.title_direction / description_angle: hỏi PM trước khi chốt title")

    asm = assembly(album)
    chapters = chapters_of(asm) if asm else None
    if not asm:
        err.append("chưa có assembly.json (audio-album-assembly): không có chapters để đối chiếu")
    total, source = known_duration(album, a.video)
    if total is None:
        warn.append("chưa có video render (video/video.mp4.json) và không có --video: độ dài đối chiếu theo master; "
                    "`video.py package` kiểm lại sau khi render")
    master_s = float(asm.get("duration_s") or 0) if asm else 0
    check_length(ch_dir, master_s, err, warn)
    if total is None and master_s:
        total, source = master_s, "assembly.json duration_s (master)"
    elif total is not None and master_s and abs(total - master_s) > DURATION_TOLERANCE:
        err.append(f"video dài {fmt(total)} ≠ master trong assembly.json {fmt(master_s)}: video dựng từ bản ghép khác, "
                    "chapters của assembly.json KHÔNG đúng cho nó; render lại video từ master")
    rj = album / "video" / "remote.json"
    if asm and rj.exists():
        used = json.loads(rj.read_text()).get("audio")
        if used and (ROOT / used).resolve() != (album / asm.get("master", "")).resolve():
            err.append(f"video trên server dựng từ {used}, không phải master {asm.get('master')}")
    if chapters is not None:
        err.extend(chapter_problems(chapters, total))
        want = track_titles(album)
        if want and want != [n for _, n in chapters]:
            warn.append("tên/thứ tự bài trong assembly.json khác tracks/*.md: chapters theo assembly.json")
    if total is None:
        warn.append("chưa biết độ dài video (không có --video, video/video.mp4.json, assembly.json duration_s)")

    title = (code_block(y, "## Title") or "").strip()
    if not title:
        err.append("thiếu khối title trong ## Title")
    else:
        check_title(title, total, err)
    desc = code_block(y, "## Description")
    got = {}
    if not desc:
        err.append("thiếu khối description trong ## Description")
        desc = ""
    else:
        got = check_description(desc, ch_text, chapters, err, warn)
    comment = code_block(y, "## Pinned comment")
    if not comment:
        err.append("thiếu khối comment trong ## Pinned comment")
    else:
        check_comment(comment, got, err)
    check_tags(y, ch_text, err, warn)
    check_thumbnail(album, err, warn)
    check_bank(album, brief, y, title, ch_text, err, warn, info)

    if title:
        print(f"title: {len(title)}/{TITLE_MAX} ký tự")
    print(f"description: {len(desc)}/5000 ký tự, {len(got)} chapters"
          + (f"; độ dài theo {source}: {fmt(total)}" if total else ""))
    for i in info:
        print(f"ℹ️  {i}")
    for w in warn:
        print(f"⚠️  {w}")
    for e in err:
        print(f"❌ {e}")
    if not err:
        print("✅ youtube.md sẵn sàng để dán vào YouTube Studio")
    sys.exit(1 if err else 0)


def split_list(s):
    return [t.strip() for t in (s or "").replace("\n", ",").split(",") if t.strip()]


def compact(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def suggest(q, gl):
    from urllib.parse import urlencode
    from urllib.request import urlopen
    url = SUGGEST + "?" + urlencode({"client": "firefox", "ds": "yt", "hl": "en", "gl": gl, "q": q})
    with urlopen(url, timeout=10) as r:
        return [s.lower() for s in json.loads(r.read().decode("utf-8", "replace"))[1]]


def trends_anchor(album, channel=None):
    pub = (ROOT / "channel" / channel / "publish.md") if channel else (Path(album).resolve().parents[1] / "publish.md" if album else None)
    m = re.search(r"Mốc Google Trends:\*\*\s*`([^`]+)`\s*=\s*([\d.]+)", pub.read_text()) if pub and pub.exists() else None
    if not m:
        sys.exit("--trends cần mốc so sánh: dòng '**Mốc Google Trends:** `<cụm>` = <số>' trong channel/<ch>/publish.md; cho <album> hoặc --channel <ch>")
    return m.group(1), float(m.group(2))


def trends_volume(tags, anchor):
    import time
    from pytrends.request import TrendReq
    term, scale = anchor
    req, out = TrendReq(hl="en-US", tz=0), {}
    for i in range(0, len(tags), 4):
        kw = [term] + [t for t in tags[i:i + 4] if t != term]
        for attempt in range(3):
            try:
                req.build_payload(kw, timeframe="today 5-y", geo="", gprop="youtube")
                df = req.interest_over_time()
                break
            except Exception as e:
                if attempt == 2:
                    sys.exit(f"Google Trends từ chối ({e}); đợi vài phút rồi chạy lại")
                time.sleep(20)
        means = df.mean(numeric_only=True) if len(df) else {}
        base = means.get(term, 0) or 1e-9
        for t in kw[1:]:
            out[t] = round(float(means.get(t, 0)) / base * scale, 2)
        time.sleep(4)
    out[term] = scale
    return out


def reference_handles():
    measured = {p.parent.name.split("-")[0].lower() for p in (ROOT / "research").glob("*/reference.yaml")}
    niche = {compact(n) for n in load_bank()[1]}
    return sorted(h for h in measured | niche if len(h) >= 4)


def own_names(folder):
    folder = Path(folder)
    names = [folder.parent.parent.name.replace("_", " ")]
    asm = assembly(folder)
    names += [t for _, t in chapters_of(asm)] if asm else track_titles(folder)
    return [n.lower() for n in names if n]


def cmd_tags(a):
    tags, own = split_list(a.try_), split_list(a.own)
    if a.album:
        own += own_names(a.album)
        y = Path(a.album) / "youtube.md"
        if y.exists() and not a.try_:
            tags += split_list(code_block(y.read_text(), "## Tags"))
    refs = reference_handles()
    if not tags and not a.expand:
        sys.exit("không có tag nào để kiểm tra: cho <album> có youtube.md, hoặc --try / --expand")

    def fetch(q):
        try:
            return suggest(q, a.gl)
        except Exception as e:
            sys.exit(f"không gọi được YouTube autocomplete ({e}); kiểm tra mạng rồi chạy lại")

    def ref_of(s):
        return next((h for h in refs if h in compact(s)), None)

    for seed in split_list(a.expand):
        got = fetch(seed)
        marked = [f"{s} (kênh tham khảo)" if ref_of(s) else s for s in got]
        print(f"🔎 {seed}: {' | '.join(marked) or '(không có gợi ý)'}")
    if a.expand:
        print()
    if not tags:
        return

    anchor = trends_anchor(a.album, a.channel) if a.trends else None
    vol = trends_volume([t.lower() for t in tags], anchor) if anchor else {}
    print(f"autocomplete YouTube, gl={a.gl}. ✅ có người gõ đúng cụm · ⚠️ chỉ gõ dạng khác/ra thứ khác · ❌ bỏ")
    if vol:
        print(f"Trends = Google Trends YouTube Search 5 năm, thang \"{anchor[0]}\" = {anchor[1]}; < {TRENDS_MIN} = gần như không ai tìm")
    print()
    print("| tag | kết luận |" + (" Trends |" if vol else "") + " người gõ cụm này tìm (gợi ý đầu) |\n|---|---|" + ("---|" if vol else "") + "---|")
    for t in tags:
        low = t.lower()
        got = fetch(low)
        longer = [s for s in got if s.startswith(low) and s != low]
        ref = ref_of(low)
        if ref:
            verdict = f"❌ trùng tên kênh tham khảo `{ref}`"
        elif any(low == n or compact(low) == compact(n) for n in own):
            verdict = "✅ tên riêng" + ("" if low in got else " (chưa ai gõ, vẫn giữ)")
        elif low in got:
            verdict = f"✅ có người gõ, {len(longer)} cụm dài hơn"
        elif longer:
            verdict = f"⚠️ không ai gõ đúng cụm; dùng dạng người ta gõ: {longer[0]}"
        elif got:
            verdict = "⚠️ gõ vào ra thứ khác: xem ý định"
        else:
            verdict = "❌ không có gợi ý nào: gần như không ai gõ"
        top = " · ".join(s for s in got if s != low)[:160]
        if vol:
            v = vol.get(low, 0)
            if v < TRENDS_MIN and verdict.startswith("✅") and not verdict.startswith("✅ tên riêng"):
                verdict = "⚠️ có người gõ nhưng lượng tìm ≈ 0: thay bằng cụm rộng hơn"
            print(f"| {t} | {verdict} | {v} | {top} |")
        else:
            print(f"| {t} | {verdict} | {top} |")
    print("\nMáy chỉ biết có người gõ hay không. Ý định (cột cuối: đúng dòng nhạc của kênh, hay beat, podcast, ca sĩ khác?) phải tự đọc.")


def main():
    ap = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("chapters")
    c.add_argument("album")
    c.set_defaults(fn=cmd_chapters)
    k = sub.add_parser("check")
    k.add_argument("album")
    k.add_argument("--video", help="file video sẽ upload (nếu có trên máy), để đối chiếu độ dài với chapters")
    k.set_defaults(fn=cmd_check)
    t = sub.add_parser("tags")
    t.add_argument("album", nargs="?", help="thư mục album: đọc khối ## Tags của youtube.md + tên riêng (tên bài)")
    t.add_argument("--try", dest="try_", help="tag ứng viên, cách nhau bằng dấu phẩy (thay cho khối trong youtube.md)")
    t.add_argument("--expand", help="từ gốc để xem người ta gõ tiếp gì (tìm ứng viên), cách nhau bằng dấu phẩy")
    t.add_argument("--own", help="tên riêng thêm (tên bài), luôn giữ dù ít người gõ")
    t.add_argument("--gl", default="US", help="thị trường autocomplete (mặc định US)")
    t.add_argument("--channel", help="kênh (channel/<ch>) để đọc mốc Google Trends khi không cho <album>")
    t.add_argument("--trends", action="store_true", help="thêm cột lượng tìm Google Trends (YouTube Search, 5 năm); chậm ~5 s mỗi 4 tag")
    t.set_defaults(fn=cmd_tags)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

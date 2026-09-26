#!/usr/bin/env python3
USAGE = """youtube-publish helper.

  chapters <album> --audio <video.mp4|master.wav>   dò timestamps từng bài trong đúng file sẽ upload
  check    <album> [--video <video.mp4>]            kiểm tra youtube.md trước khi dán vào YouTube Studio
  tags     [<album>] [--try "a, b"] [--expand "seed, seed"] [--own "tên bài, hook"] [--trends]
                                                    research tags bằng YouTube autocomplete (có người gõ không, người gõ tìm gì)
                                                    + --trends: lượng tìm Google Trends (YouTube Search, 5 năm) cho từng tag

Chạy từ gốc repo. <album> = channel/<channel>/albums/NNN-slug, hoặc channel/<channel>/singles/NNN-slug
(bài đăng riêng, có single.md: không chapters, không "Full Album", link về video album).
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]

SR = 2000
PROBE = 10.0
MATCH_R = 0.4
TITLE_MAX = 70
SUGGEST = "https://suggestqueries.google.com/complete/search"
TRENDS_MIN = 1.0


def fmt(t):
    t = int(t)
    h, m, s = t // 3600, t % 3600 // 60, t % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def parse_ts(s):
    parts = [int(p) for p in s.split(":")]
    v = 0
    for p in parts:
        v = v * 60 + p
    return v


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True).stdout.strip()
    return float(out)


def front_matter(md):
    import yaml
    text = Path(md).read_text()
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    return yaml.safe_load(m.group(1)) if m else {}


def is_single(folder):
    return (Path(folder) / "single.md").exists()


def album_tracks(album):
    import yaml
    rows = {}
    for md in sorted((album / "tracks").glob("*.md")):
        fm = front_matter(md)
        if fm.get("track_no"):
            rows[int(fm["track_no"])] = [fm["title"], album / fm["audio"], None, None]
    ay = album / "assembly.yaml"
    if ay.exists():
        for t in yaml.safe_load(ay.read_text()).get("tracks", []):
            n = int(t["no"])
            if n in rows:
                ms = t.get("measured") or {}
                rows[n][2], rows[n][3] = ms.get("vocal_start"), ms.get("vocal_end")
    return [(n, *rows[n]) for n in sorted(rows)]


def load(path):
    import numpy as np
    b = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                       capture_output=True, check=True).stdout
    return np.frombuffer(b, np.float32).copy()


def cmd_chapters(a):
    import numpy as np
    from scipy.signal import fftconvolve

    album = Path(a.album)
    if is_single(album):
        sys.exit("bài đăng riêng (single.md): không cần chapters, video chỉ có một bài")
    tracks = album_tracks(album)
    if not tracks:
        sys.exit(f"không thấy tracks/*.md có track_no trong {album}")
    M = load(a.audio)
    total = len(M) / SR
    rows, search_from, prev_vocal_end = [], 0.0, None
    for n, title, path, vs, ve in tracks:
        T = load(path)
        probe_at = (vs + 5) if vs is not None else min(60.0, len(T) / SR / 3)
        q = T[int(probe_at * SR):int((probe_at + PROBE) * SR)]
        lo = int(max(0, search_from - 60) * SR)
        seg = M[lo:]
        c = fftconvolve(seg, q[::-1], mode="valid")
        p = int(np.argmax(np.abs(c)))
        r_probe = float(np.corrcoef(seg[p:p + len(q)], q)[0, 1])
        off = (lo + p) / SR - probe_at
        v_in = (vs + off) if vs is not None else None
        v_out = (ve + off) if ve is not None else None
        note = ""
        if n == tracks[0][0]:
            start = 0.0
        else:
            floor_t = (prev_vocal_end + 1) if prev_vocal_end is not None else max(0.0, off)
            ceil_t = (v_in - 1) if v_in is not None else off + probe_at
            start = None
            s = max(floor_t, off)
            while s < ceil_t:
                x = T[int((s - off) * SR):int((s - off + 1) * SR)]
                m = M[int(s * SR):int((s + 1) * SR)]
                if len(x) == len(m) == SR and np.std(x) > 1e-5 and np.corrcoef(m, x)[0, 1] > MATCH_R:
                    start = s
                    break
                s += 0.5
            if start is None:
                start = max(floor_t, ceil_t - 3)
                note = "ước lượng (chồng lên outro bài trước)"
        if r_probe < 0.8:
            note = (note + "; " if note else "") + f"khớp yếu r={r_probe:.2f}: file trong video có đúng bản này không?"
        rows.append((n, title, start, v_in, r_probe, note))
        search_from, prev_vocal_end = off + probe_at, v_out

    print(f"# {a.audio}  ({fmt(total)})\n")
    print("```")
    for n, title, start, *_ in rows:
        print(f"{fmt(start)} {title}")
    print("```\n")
    print("| # | chapter | câu hát đầu | khớp r | ghi chú |\n|---|---|---|---|---|")
    for n, title, start, v_in, r, note in rows:
        print(f"| {n:02d} | {fmt(start)} ({start:.1f}s) | {'' if v_in is None else f'{v_in:.1f}s'} | {r:.2f} | {note} |")


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


def cmd_check(a):
    album = Path(a.album)
    single = is_single(album)
    sfm = front_matter(album / "single.md") if single else {}
    ch_dir = album.parent.parent
    y = (album / "youtube.md").read_text()
    ch = "\n".join(f.read_text() for f in (ch_dir / "publish.md", ch_dir / "channel.md") if f.exists())
    err, warn = [], []

    title = code_block(y, "## Title")
    desc = code_block(y, "## Description")
    tags_txt = code_block(y, "## Tags")
    if not title:
        err.append("thiếu khối title trong ## Title")
    else:
        title = title.strip()
        if len(title) > 100:
            err.append(f"title {len(title)} ký tự > 100")
        if re.search(r"[<>]", title):
            err.append("title có ký tự < hoặc > (YouTube không nhận)")
        if single and re.search(r"full album|playlist|\b\d+\s*(hour|hr)", title, re.I):
            err.append("title của bài đăng riêng không được ghi Full Album / playlist / số giờ")
        if len(title) > TITLE_MAX:
            err.append(f"title {len(title)} ký tự > {TITLE_MAX}: YouTube cắt phần sau trên search/mobile (vidIQ cảnh báo); "
                       "rút gọn theo thứ tự bỏ trong SKILL.md → Title")
    if not desc:
        err.append("thiếu khối description trong ## Description")
        desc = ""
    else:
        if len(desc) > 5000:
            err.append(f"description {len(desc)} ký tự > 5000")
        if re.search(r"[<>]", desc):
            err.append("description có ký tự < hoặc > (YouTube không nhận)")
        ph = re.findall(r"\[[^\]\n]*(?:CHÉP|Write|TODO|điền|chapters,)[^\]\n]*\]", desc)
        for p in ph:
            err.append(f"description còn placeholder: {p}")
        tpl = code_block(ch, "## Description YouTube mặc định")
        if tpl:
            for line in tpl.splitlines():
                if single and line.strip() == "TRACKLIST":
                    continue
                if line.strip() and not line.startswith("[") and line not in desc:
                    err.append(f"description thiếu dòng của mẫu channel: {line[:60]}")
        hashtags = re.findall(r"(?<!\w)#\w+", desc)
        if len(hashtags) > 15:
            err.append(f"{len(hashtags)} hashtag > 15: YouTube bỏ qua toàn bộ")

    ch_lines = [l for l in desc.splitlines() if re.match(r"^\d{1,2}:\d{2}(:\d{2})?\s", l)]
    ts, names = [], []
    if single:
        if ch_lines:
            err.append("single: description có dòng bắt đầu bằng timestamp; bỏ đi (video một bài, không chapters)")
        url = (sfm.get("album_video_url") or "").strip()
        if url and url not in desc:
            err.append(f"description chưa có link video album {url}")
        elif not url:
            warn.append("single.md chưa có album_video_url: description/comment chưa trỏ về album (điền sau khi album lên)")
        if a.video:
            m = album / "audio" / "master" / f"{album.name}.wav"
            if m.exists() and abs(duration(m) - duration(a.video)) > 3:
                warn.append(f"video dài {fmt(duration(a.video))} ≠ audio đã chuẩn bị {fmt(duration(m))}: dựng lại video từ {m.name}?")
    elif ch_lines:
        ts = [parse_ts(l.split()[0]) for l in ch_lines]
        names = [l.split(None, 1)[1].strip() for l in ch_lines]
        if ts[0] != 0:
            err.append("chapter đầu phải là 0:00")
        if len(ts) < 3:
            err.append("cần ít nhất 3 chapters")
        for k in range(1, len(ts)):
            if ts[k] - ts[k - 1] < 10:
                err.append(f"chapter {names[k - 1]} → {names[k]}: cách nhau {ts[k] - ts[k - 1]}s < 10s hoặc không tăng dần")
        want = [t[1] for t in album_tracks(album)]
        if want and names != want:
            err.append(f"tên/thứ tự chapters khác tracks/*.md: {names} vs {want}")
        if a.video:
            d = duration(a.video)
            if ts[-1] >= d - 10:
                err.append(f"chapter cuối {fmt(ts[-1])} vượt/quá sát độ dài video {fmt(d)}")
            ay = album / "assembly.yaml"
            if ay.exists():
                import yaml
                out = album / yaml.safe_load(ay.read_text()).get("output", "")
                if out.exists() and abs(duration(out) - d) > 3:
                    warn.append(f"video dài {fmt(d)} ≠ bản ghép trong assembly.yaml {fmt(duration(out))}: "
                                "timestamps của assembly.md KHÔNG dùng được, dò bằng `publish.py chapters --audio <video>`")
        else:
            warn.append("không có --video: chưa kiểm tra chapters có khớp file video sẽ upload")
    else:
        err.append("description chưa có chapters (dòng dạng `0:00 Title`)")

    comment = code_block(y, "## Pinned comment")
    if not comment:
        err.append("thiếu khối comment trong ## Pinned comment")
    else:
        if len(comment) > 10000:
            err.append(f"comment {len(comment)} ký tự > 10000")
        if re.search(r"\[[^\]\n]*(?:CHÉP|TODO|điền)[^\]\n]*\]", comment):
            err.append("comment còn placeholder")
        chapters = dict(zip(ts, names)) if ch_lines else {}
        if single:
            bare = [m.group(0) for m in re.finditer(r"(?<![\w:/=?&])\d{1,2}:\d{2}(?::\d{2})?(?![\w:])", comment)]
            if bare:
                err.append(f"comment của single có timestamp {bare}: sẽ nhảy trong video này, không phải album; "
                           "dùng link album kèm ?t=<giây>")
            url = (sfm.get("album_video_url") or "").strip()
            if url and url.split("&")[0] not in comment:
                err.append(f"comment chưa có link video album {url}")
        for m in re.finditer(r"(?<![\d:])(\d{1,2}:\d{2}(?::\d{2})?)\s+(.+)", comment):
            t, rest = parse_ts(m.group(1)), m.group(2)
            if chapters and (t not in chapters or not rest.startswith(chapters[t])):
                err.append(f"comment: `{m.group(0)[:50]}` không khớp chapter nào trong description")

    if not tags_txt:
        err.append("thiếu khối tags trong ## Tags")
    else:
        tags = [t.strip() for t in tags_txt.replace("\n", ",").split(",") if t.strip()]
        L = tags_len(tags)
        if L > 500:
            err.append(f"tags {L}/500 ký tự (tính cả ngoặc kép cho tag có dấu cách)")
        low = [t.lower() for t in tags]
        dups = {t for t in low if low.count(t) > 1}
        if dups:
            err.append(f"tag trùng: {sorted(dups)}")
        dtpl = code_block(ch, "## Tags YouTube mặc định")
        if dtpl:
            defaults = [t.strip().lower() for t in dtpl.split(",") if t.strip()]
            miss = [t for t in defaults if t not in low]
            if miss:
                err.append(f"thiếu tag mặc định của channel: {miss}")
            extra = len([t for t in low if t not in defaults])
            if not 5 <= extra <= 12:
                warn.append(f"{extra} tag riêng của {'bài' if single else 'album'} (quy ước 5–12, chỉ tag qua `publish.py tags`)")
        if not re.search(r"autocomplete|trends", section(y, "## Tags").lower()):
            warn.append("bảng tag chưa có cột bằng chứng (Trends / autocomplete): chạy `publish.py tags <album> --trends` rồi ghi kết quả vào bảng")
        print(f"tags: {len(tags)} tag, {L}/500 ký tự")

    thumb = album / "thumbnail.png"
    jpg = album / "thumbnail.jpg"
    if not thumb.exists() or (thumb.stat().st_size > 2 * 1024 * 1024 and jpg.exists()):
        thumb = jpg
    if thumb.exists():
        size = thumb.stat().st_size
        if size > 2 * 1024 * 1024:
            err.append(f"thumbnail {size / 1e6:.2f} MB > 2 MB: xuất JPG (sips -s format jpeg -s formatOptions 90)")
        elif thumb == jpg:
            print(f"thumbnail: upload {jpg.name} ({size / 1e6:.2f} MB)")
    else:
        warn.append("không thấy thumbnail.png/jpg trong thư mục album")

    if title:
        print(f"title: {len(title)}/{TITLE_MAX} ký tự")
    print(f"description: {len(desc)}/5000 ký tự" + ("" if single else f", {len(ch_lines)} chapters"))
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
    import json
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
    root = Path("research")
    return sorted({p.name.split("-")[0].lower() for p in root.iterdir() if p.is_dir()}) if root.is_dir() else []


def own_names(folder):
    folder = Path(folder)
    names = [folder.parent.parent.name.replace("_", " ")]
    if is_single(folder):
        sfm = front_matter(folder / "single.md")
        fm = front_matter((folder / sfm["track"]).resolve())
        names += [fm.get("title", ""), fm.get("hook_phrase", "")]
        origin = folder.parent.parent / "albums" / str(sfm.get("album", ""))
        if (origin / "tracks").is_dir():
            names += [t[1] for t in album_tracks(origin)[:1]]
    elif (folder / "tracks").is_dir():
        names += [t[1] for t in album_tracks(folder)]
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

    anchor = trends_anchor(a.album, a.channel) if a.trends and tags else None
    vol = trends_volume([t.lower() for t in tags], anchor) if anchor else {}
    print(f"autocomplete YouTube, gl={a.gl}. ✅ có người gõ đúng cụm · ⚠️ chỉ gõ dạng khác/ra thứ khác · ❌ bỏ")
    if vol:
        print(f"Trends = Google Trends YouTube Search 5 năm, thang \"{anchor[0]}\" = {anchor[1]}; < {TRENDS_MIN} = gần như không ai tìm")
    print()
    print("| tag | kết luận |" + (" Trends |" if vol else "") + " người gõ cụm này tìm (gợi ý đầu) |\n|---|---|" + ("---|" if vol else "") + "---|")
    for t in tags:
        low = t.lower()
        got = fetch(low)
        longer = [s for s in got if s.startswith(low) and s != low]   # "song" → "songs" cũng tính
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
            own_name = verdict.startswith("✅ tên riêng")
            if v < TRENDS_MIN and verdict.startswith("✅") and not own_name:
                verdict = f"⚠️ có người gõ nhưng lượng tìm ≈ 0: thay bằng cụm rộng hơn"
            print(f"| {t} | {verdict} | {v} | {top} |")
        else:
            print(f"| {t} | {verdict} | {top} |")
    print("\nMáy chỉ biết có người gõ hay không. Ý định (cột 3: đúng dòng nhạc của kênh, hay beat, podcast, ca sĩ khác?) phải tự đọc.")


def main():
    ap = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("chapters")
    c.add_argument("album")
    c.add_argument("--audio", required=True, help="file sẽ upload (video .mp4) hoặc master audio của nó")
    c.set_defaults(fn=cmd_chapters)
    k = sub.add_parser("check")
    k.add_argument("album")
    k.add_argument("--video", help="file video sẽ upload, để đối chiếu độ dài/chapters")
    k.set_defaults(fn=cmd_check)
    t = sub.add_parser("tags")
    t.add_argument("album", nargs="?", help="thư mục album/single: đọc khối ## Tags của youtube.md + tên riêng (tên bài, hook)")
    t.add_argument("--try", dest="try_", help="tag ứng viên, cách nhau bằng dấu phẩy (thay cho khối trong youtube.md)")
    t.add_argument("--expand", help="từ gốc để xem người ta gõ tiếp gì (tìm ứng viên), cách nhau bằng dấu phẩy")
    t.add_argument("--own", help="tên riêng thêm (tên bài, hook), luôn giữ dù ít người gõ")
    t.add_argument("--gl", default="US", help="thị trường autocomplete (mặc định US)")
    t.add_argument("--channel", help="kênh (channel/<ch>) để đọc mốc Google Trends khi không cho <album>")
    t.add_argument("--trends", action="store_true", help="thêm cột lượng tìm Google Trends (YouTube Search, 5 năm); chậm ~5 s mỗi 4 tag")
    t.set_defaults(fn=cmd_tags)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

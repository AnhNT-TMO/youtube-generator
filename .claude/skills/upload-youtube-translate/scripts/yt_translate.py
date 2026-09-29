#!/usr/bin/env python3
USAGE = """upload-youtube-translate: dịch TITLE (và DESCRIPTION nếu translate.yaml bật translate_description) của video YouTube
qua video localizations. Không đụng title gốc, description gốc, tags, ảnh.

  auth   --channel <ch>             đăng nhập OAuth một lần cho kênh (token ở .cache/tokens/<ch>.json)
  list   --channel <ch>             mọi video của kênh: ngôn ngữ đã có / còn thiếu, thư mục trong repo
  pull   <target>... [--channel]    lấy title + description gốc từ YouTube → title-translations.yaml (ô trống / dòng
                                    [[dịch]] để điền bản dịch; dòng đã dịch ở video khác được điền sẵn)
  apply  <target>... [--yes]        kiểm bản dịch, in thay đổi; --yes mới ghi lên YouTube, rồi đọc lại để xác nhận
  pull/apply --missing --channel <ch>   thay cho <target>: mọi video của kênh còn thiếu bản dịch hoặc có bản dịch cũ

<target> = thư mục album/Short (channel/<ch>/albums/NNN-slug, …/albums/NNN-slug/short) có youtube.md (dòng "Video URL"),
hoặc video id / URL (cần --channel; file dịch lưu ở channel/<ch>/translations/<id>.yaml).
Ngôn ngữ đích + chữ giữ nguyên: channel/<ch>/translate.yaml. Chạy từ gốc repo.
"""
import argparse
import datetime
import re
import sys
from collections import Counter
import time
import unicodedata
from pathlib import Path

import yaml

ROOT = Path.cwd()
SK = Path(__file__).resolve().parents[1]
SECRET = SK / ".cache" / "client_secret.json"
TOKENS = SK / ".cache" / "tokens"
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
VID_RE = re.compile(r"(?:v=|youtu\.be/|/shorts/|/live/|/video/)([\w-]{11})")
TITLE_MAX = 100
TITLE_SEEN = 70
DESC_MAX_BYTES = 5000
TODO_MARK = "[[dịch]]"
TIMESTAMP_RE = re.compile(r"^\s*\(?\d{1,2}:\d{2}(?::\d{2})?\)?\s")
URL_RE = re.compile(r"https?://\S+")


def die(msg):
    sys.exit(f"❌ {msg}")


def cfg_path(ch):
    return ROOT / "channel" / ch / "translate.yaml"


def load_cfg(ch):
    p = cfg_path(ch)
    if not p.exists():
        die(f"thiếu {p.relative_to(ROOT)} (ngôn ngữ đích của kênh), xem SKILL.md")
    cfg = yaml.safe_load(p.read_text()) or {}
    cfg.setdefault("source_language", "en")
    cfg.setdefault("translate_description", False)
    cfg.setdefault("keep_lyrics", True)
    cfg["codes"] = [l["code"] for l in cfg.get("languages", [])]
    cfg["also"] = {l["code"]: l.get("also", []) for l in cfg.get("languages", [])}
    cfg["all_codes"] = cfg["codes"] + sum(cfg["also"].values(), [])
    if not cfg["codes"]:
        die(f"{p.relative_to(ROOT)}: languages trống")
    return cfg


def front_matter(md):
    m = re.match(r"^---\n(.*?)\n---", Path(md).read_text(), re.S)
    return yaml.safe_load(m.group(1)) if m else {}


def track_files(folder):
    single = folder / "single.md"
    if single.exists():
        track = front_matter(single).get("track")
        return [folder / track] if track and (folder / track).exists() else []
    return sorted((folder / "tracks").glob("*.md"))


def song_title(folder):
    is_single = (folder / "single.md").exists()
    for md in track_files(folder):
        fm = front_matter(md)
        if is_single or str(fm.get("track_no")) == "1":
            return fm.get("title")
    return None


def lyric_lines(folder):
    out = set()
    for md in track_files(folder):
        m = re.search(r"^## Lyrics.*?\n```\n(.*?)\n```", md.read_text(), re.S | re.M)
        if m:
            out |= {l.strip() for l in m.group(1).splitlines() if l.strip() and not l.strip().startswith("[")}
    return out


def verbatim_lines(cfg, folder, lines):
    lyrics = lyric_lines(folder) if folder is not None and cfg["keep_lyrics"] else set()
    return {i for i, l in enumerate(lines) if l.strip() and (
        TIMESTAMP_RE.match(l) or all(w.startswith("#") for w in l.split()) or l.strip() in lyrics)}


def record_files(ch):
    base = ROOT / "channel" / ch
    return (list(base.glob("*/*/title-translations.yaml")) + list(base.glob("albums/*/short/title-translations.yaml"))
            + list(base.glob("translations/*.yaml")))


def line_memory(ch, code):
    votes = {}
    for p in record_files(ch):
        d = yaml.safe_load(p.read_text()) or {}
        src = (d.get("source_description") or "").split("\n")
        tr = ((d.get("descriptions") or {}).get(code) or "").rstrip().split("\n")
        if len(src) != len(tr):
            continue
        for a, b in zip(src, tr):
            if a.strip() and b.strip() and TODO_MARK not in b and a.strip() != b.strip():
                votes.setdefault(a.strip(), Counter())[b] += 1
    return {a: c.most_common(1)[0][0] for a, c in votes.items()}


def draft_description(lines, keep_idx, memory):
    out = []
    for i, l in enumerate(lines):
        if not l.strip():
            out.append("")
        elif i in keep_idx:
            out.append(l)
        else:
            out.append(memory.get(l.strip()) or f"{TODO_MARK} {l}")
    return "\n".join(out)


def refill(text, memory):
    out = []
    for l in text.split("\n"):
        src = l[len(TODO_MARK):].strip() if l.startswith(TODO_MARK) else None
        out.append(memory.get(src) or l if src else l)
    return "\n".join(out)


def video_id_in(text):
    m = VID_RE.search(text)
    return m.group(1) if m else None


def resolve(target, ch_arg):
    p = Path(target)
    if p.is_dir():
        try:
            ch = p.resolve().relative_to(ROOT / "channel").parts[0]
        except ValueError:
            die(f"{target}: không nằm trong channel/<ch>/")
        yt_md = p / "youtube.md"
        line = next((l for l in yt_md.read_text().splitlines() if "Video URL" in l), "") if yt_md.exists() else ""
        vid = video_id_in(line)
        if not vid:
            die(f"{target}: youtube.md chưa có Video URL (điền link sau khi upload, hoặc truyền video id + --channel)")
        return ch, vid, p / "title-translations.yaml", p
    vid = video_id_in(target) or (target if re.fullmatch(r"[\w-]{11}", target) else None)
    if not vid:
        die(f"{target}: không phải thư mục, video id hay URL YouTube")
    if not ch_arg:
        die(f"{target}: video id cần --channel <ch>")
    return ch_arg, vid, ROOT / "channel" / ch_arg / "translations" / f"{vid}.yaml", None


def record_path(ch, vid, folders):
    return ROOT / folders[vid] / "title-translations.yaml" if vid in folders else ROOT / "channel" / ch / "translations" / f"{vid}.yaml"


def repo_folders(ch):
    out = {}
    base = ROOT / "channel" / ch
    for md in [*base.glob("*/*/youtube.md"), *base.glob("albums/*/short/youtube.md")]:
        line = next((l for l in md.read_text().splitlines() if "Video URL" in l), "")
        vid = video_id_in(line)
        if vid:
            out[vid] = str(md.parent.relative_to(ROOT))
    return out


def rel(p):
    return p.relative_to(ROOT) if p.is_absolute() else p


class BlockDumper(yaml.SafeDumper):
    pass


BlockDumper.add_representer(str, lambda d, s: d.represent_scalar("tag:yaml.org,2002:str", s, style="|" if "\n" in s else None))


def write_yaml(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    head = ("# skill upload-youtube-translate. Chỉ điền `titles`, `descriptions` (thay mọi dòng [[dịch]], giữ đúng số dòng) và sửa `keep`\n"
            "# nếu cần; phần còn lại do `pull` ghi từ YouTube. Ô trống = chưa dịch, apply bỏ qua.\n"
            "# Luật dịch: .claude/skills/upload-youtube-translate/SKILL.md\n")
    path.write_text(head + yaml.dump(data, Dumper=BlockDumper, allow_unicode=True, sort_keys=False, width=1000))


def api_error(e):
    try:
        import json
        err = json.loads(e.content)["error"]
        reasons = ", ".join(x.get("reason", "") for x in err.get("errors", []))
        return f"YouTube API {err.get('code')}: {err.get('message')} ({reasons})"
    except Exception:
        return str(e)


def service(ch):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    tok = TOKENS / f"{ch}.json"
    if not tok.exists():
        die(f"chưa đăng nhập cho kênh {ch}: chạy `auth --channel {ch}`")
    creds = Credentials.from_authorized_user_file(str(tok), SCOPES)
    if not creds.valid:
        try:
            creds.refresh(Request())
        except Exception as e:
            die(f"token hết hạn / bị thu hồi ({e}): chạy lại `auth --channel {ch}`")
        tok.write_text(creds.to_json())
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def my_channel(yt):
    items = yt.channels().list(part="snippet,contentDetails", mine=True).execute().get("items", [])
    if not items:
        die("tài khoản đã đăng nhập không có kênh YouTube (chọn đúng brand account khi auth)")
    return items[0]


def guard_channel(yt, ch, cfg):
    me = my_channel(yt)
    want = cfg.get("channel_id")
    if not want:
        die(f"{rel(cfg_path(ch))}: channel_id trống, chạy `auth --channel {ch}`")
    if me["id"] != want:
        die(f"token đang là kênh {me['snippet']['title']} ({me['id']}), không phải {ch} ({want}): chạy lại auth")
    return me


def get_video(yt, vid, hl=None):
    kw = {"hl": hl} if hl else {}
    items = yt.videos().list(part="snippet,localizations", id=vid, **kw).execute().get("items", [])
    if not items:
        die(f"{vid}: không thấy video (sai id, đã xoá, hoặc không thuộc kênh đang đăng nhập)")
    return items[0]


def cmd_auth(a):
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    cfg = load_cfg(a.channel)
    if not SECRET.exists():
        die(f"thiếu {rel(SECRET)}: tải OAuth client (Desktop app) từ Google Cloud Console, xem SKILL.md mục Cài đặt")
    flow = InstalledAppFlow.from_client_secrets_file(str(SECRET), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
    me = my_channel(build("youtube", "v3", credentials=creds, cache_discovery=False))
    want = cfg.get("channel_id")
    if want and me["id"] != want:
        die(f"đã đăng nhập kênh {me['snippet']['title']} ({me['id']}), khác channel_id {want} của {a.channel}: "
            "chạy lại và chọn đúng kênh ở màn chọn tài khoản. Token KHÔNG được lưu.")
    TOKENS.mkdir(parents=True, exist_ok=True)
    (TOKENS / f"{a.channel}.json").write_text(creds.to_json())
    if not want:
        p = cfg_path(a.channel)
        p.write_text(re.sub(r"(?m)^channel_id:.*$", f"channel_id: {me['id']}   # {me['snippet']['title']}", p.read_text()))
        print(f"ghi channel_id vào {rel(p)}")
    print(f"✅ {a.channel} = {me['snippet']['title']} ({me['id']}), token {rel(TOKENS / (a.channel + '.json'))}")


def channel_videos(yt, me):
    uploads = me["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, tok, out = [], None, []
    while True:
        r = yt.playlistItems().list(part="contentDetails", playlistId=uploads, maxResults=50, pageToken=tok).execute()
        ids += [x["contentDetails"]["videoId"] for x in r.get("items", [])]
        tok = r.get("nextPageToken")
        if not tok:
            break
    for i in range(0, len(ids), 50):
        out += yt.videos().list(part="snippet,localizations,status", id=",".join(ids[i:i + 50])).execute().get("items", [])
    return out


def missing(v, cfg):
    locs = v.get("localizations", {})
    titles = [c for c in cfg["all_codes"] if not locs.get(c, {}).get("title")]
    descs = [c for c in cfg["all_codes"] if cfg["translate_description"] and v["snippet"].get("description", "").strip()
             and not locs.get(c, {}).get("description")]
    return titles, descs


def stale(v, path):
    if not path.exists():
        return []
    d = yaml.safe_load(path.read_text()) or {}
    out = []
    if d.get("source_title") and d["source_title"] != v["snippet"]["title"]:
        out.append("title")
    if any((d.get("descriptions") or {}).values()) and d.get("source_description") != v["snippet"].get("description", ""):
        out.append("description")
    return out


def status_label(v, cfg, path):
    titles, descs = missing(v, cfg)
    parts = ([f"thiếu title {' '.join(titles)}"] if titles else []) + ([f"thiếu mô tả {' '.join(descs)}"] if descs else [])
    parts += [f"{f} gốc đã đổi, dịch lại" for f in stale(v, path)]
    return "; ".join(parts)


def missing_targets(ch):
    cfg = load_cfg(ch)
    yt = service(ch)
    folders = repo_folders(ch)
    out = [folders.get(v["id"], v["id"]) for v in channel_videos(yt, guard_channel(yt, ch, cfg))
           if status_label(v, cfg, record_path(ch, v["id"], folders))]
    print(f"{len(out)} video còn thiếu / cần dịch lại: {' '.join(out) or '-'}")
    return out


def cmd_list(a):
    cfg = load_cfg(a.channel)
    yt = service(a.channel)
    me = guard_channel(yt, a.channel, cfg)
    vids = channel_videos(yt, me)
    folders = repo_folders(a.channel)
    fields = "title + mô tả" if cfg["translate_description"] else "title"
    print(f"{me['snippet']['title']}: {len(vids)} video · đích: {' '.join(cfg['codes'])} · dịch {fields}\n")
    for v in vids:
        mark = status_label(v, cfg, record_path(a.channel, v["id"], folders)) or "✅ đủ"
        print(f"{v['id']}  {v['status']['privacyStatus']:<8}  {folders.get(v['id'], '-')}")
        print(f"             {v['snippet']['title']}")
        print(f"             {mark}")


def keep_list(cfg, folder, source_title):
    keep = [k for k in cfg.get("keep_verbatim", []) if k in source_title]
    if folder is not None and cfg.get("keep_song_title", True):
        t = song_title(folder)
        if t and t in source_title and t not in keep:
            keep.insert(0, t)
    return keep


def cmd_pull(a):
    services, memories = {}, {}
    for target in a.targets:
        ch, vid, path, folder = resolve(target, a.channel)
        cfg = load_cfg(ch)
        if ch not in services:
            services[ch] = service(ch)
            guard_channel(services[ch], ch, cfg)
        v = get_video(services[ch], vid)
        s, locs = v["snippet"], v.get("localizations", {})
        old = yaml.safe_load(path.read_text()) if path.exists() else {}
        titles = {c: (old.get("titles") or {}).get(c) or "" for c in cfg["codes"]}
        data = {
            "video_id": vid,
            "channel": ch,
            "default_language": s.get("defaultLanguage") or "",
            "source_title": s["title"],
            "pulled": datetime.date.today().isoformat(),
            "keep": old.get("keep") or keep_list(cfg, folder, s["title"]),
            "on_youtube": {k: l.get("title", "") for k, l in locs.items()},
            "titles": titles,
        }
        if old.get("source_title") and old["source_title"] != s["title"]:
            data["old_titles"] = {"source_title": old["source_title"], **{k: t for k, t in titles.items() if t}}
            data["titles"] = {c: "" for c in cfg["codes"]}
            data["keep"] = keep_list(cfg, folder, s["title"])
            print(f"⚠️  {vid}: title gốc đã đổi trên YouTube, bản dịch cũ chuyển sang old_titles, cần dịch lại")
        elif not old:
            for c in data["titles"]:
                data["titles"][c] = data["on_youtube"].get(c, "")
        if data["default_language"] in data["titles"]:
            del data["titles"][data["default_language"]]
        todo_d = []
        if cfg["translate_description"]:
            src_d = s.get("description", "")
            same = old.get("source_description") == src_d
            if old.get("source_description") is not None and not same:
                print(f"⚠️  {vid}: description gốc đã đổi trên YouTube, dựng lại bản nháp (dòng không đổi giữ bản dịch cũ)")
            lines = src_d.split("\n")
            keep_idx = verbatim_lines(cfg, folder, lines)
            old_d = old.get("descriptions") or {}
            descs = {}
            def memory(code):
                if (ch, code) not in memories:
                    memories[ch, code] = line_memory(ch, code)
                return memories[ch, code]
            for c in data["titles"]:
                live_d = locs.get(c, {}).get("description", "")
                if same and old_d.get(c):
                    descs[c] = refill(old_d[c], memory(c)) if TODO_MARK in old_d[c] else old_d[c]
                elif live_d and (same or old.get("source_description") is None):
                    descs[c] = live_d
                elif src_d.strip():
                    descs[c] = draft_description(lines, keep_idx, memory(c))
                else:
                    descs[c] = ""
            data["source_description"] = src_d
            data["descriptions"] = descs
            todo_d = [f"{c}({d.count(TODO_MARK)})" for c, d in descs.items() if TODO_MARK in d]
        if old.get("applied"):
            data["applied"] = old["applied"]
        write_yaml(path, data)
        todo = [c for c, t in data["titles"].items() if not t]
        print(f"{rel(path)}  {s['title']}")
        print(f"   default_language={data['default_language'] or '(chưa đặt)'}  keep={data['keep']}  "
              f"cần dịch title: {' '.join(todo) or 'không'}"
              + (f"  mô tả còn dòng {TODO_MARK}: {' '.join(todo_d) or 'không'}" if cfg["translate_description"] else ""))


def emojis(text):
    return [ch for ch in text if unicodedata.category(ch) == "So"]


def check_title(code, t, src, keep):
    err, warn = [], []
    if len(t) > TITLE_MAX:
        err.append(f"{len(t)} ký tự > {TITLE_MAX}")
    if "<" in t or ">" in t:
        err.append("có < hoặc > (YouTube từ chối)")
    for k in keep:
        if k not in t:
            err.append(f"mất chữ phải giữ nguyên: {k!r}")
    if t.strip() == src.strip():
        warn.append("giống hệt title gốc (không dịch gì?)")
    if sorted(emojis(t)) != sorted(emojis(src)):
        warn.append(f"emoji khác bản gốc ({''.join(emojis(src))} → {''.join(emojis(t))})")
    if len(t) > TITLE_SEEN and len(src) <= TITLE_SEEN:
        warn.append(f"{len(t)} ký tự: dài hơn ~{TITLE_SEEN}, phần cuối bị cắt ở kết quả tìm kiếm")
    return err, warn


def check_description(d, src, keep_idx, keep):
    err, warn = [], []
    size = len(d.encode())
    if size > DESC_MAX_BYTES:
        err.append(f"mô tả {size} byte > {DESC_MAX_BYTES}")
    if "<" in d or ">" in d:
        err.append("mô tả có < hoặc > (YouTube từ chối)")
    for k in keep:
        if k not in d:
            err.append(f"mô tả mất chữ phải giữ nguyên: {k!r}")
    a, b = src.split("\n"), d.split("\n")
    if len(a) != len(b):
        err.append(f"mô tả {len(b)} dòng, bản gốc {len(a)}: dịch từng dòng, giữ nguyên dòng trống")
        return err, warn
    same = []
    for i, (s, t) in enumerate(zip(a, b)):
        n = i + 1
        if TODO_MARK in t:
            err.append(f"dòng {n} chưa dịch: {s.strip()[:60]!r}")
        elif bool(s.strip()) != bool(t.strip()):
            err.append(f"dòng {n}: dòng trống / có chữ phải khớp bản gốc")
        elif i in keep_idx and t.strip() != s.strip():
            err.append(f"dòng {n} phải giữ nguyên (chapters / hashtag / lời bài): {s.strip()[:60]!r}")
        elif URL_RE.findall(s) != URL_RE.findall(t):
            err.append(f"dòng {n}: link khác bản gốc")
        elif s.strip() and i not in keep_idx and s.strip() == t.strip():
            same.append(str(n))
    if same:
        warn.append(f"mô tả: dòng {', '.join(same)} giống hệt bản gốc (chưa dịch?)")
    if sorted(emojis(d)) != sorted(emojis(src)):
        warn.append(f"mô tả: emoji khác bản gốc ({''.join(emojis(src))} → {''.join(emojis(d))})")
    return err, warn


def expand(cfg, per_code):
    out = {}
    for code, t in (per_code or {}).items():
        for c in [code] + cfg["also"].get(code, []):
            out.setdefault(c, t)
    return out


def cmd_apply(a):
    services, failed = {}, False
    for target in a.targets:
        ch, vid, path, folder = resolve(target, a.channel)
        if not path.exists():
            die(f"{rel(path)} chưa có: chạy pull trước")
        cfg = load_cfg(ch)
        if ch not in services:
            services[ch] = service(ch)
            guard_channel(services[ch], ch, cfg)
        yt = services[ch]
        data = yaml.safe_load(path.read_text())
        if data.get("video_id") != vid:
            die(f"{rel(path)}: video_id {data.get('video_id')} khác {vid}")
        v = get_video(yt, vid)
        s, live = v["snippet"], v.get("localizations", {})
        print(f"\n{vid}  {s['title']}")
        if s["title"] != data["source_title"]:
            print("   ❌ title gốc trên YouTube đã khác source_title: chạy pull rồi dịch lại")
            failed = True
            continue
        src_d = s.get("description", "")
        titles, descs = expand(cfg, data.get("titles")), expand(cfg, data.get("descriptions"))
        if any((d or "").strip() for d in descs.values()) and src_d != data.get("source_description"):
            print("   ❌ description gốc trên YouTube đã khác source_description: chạy pull rồi dịch các dòng [[dịch]]")
            failed = True
            continue
        dl = s.get("defaultLanguage") or cfg["source_language"]
        errs, new, changes = 0, {k: dict(l) for k, l in live.items()}, []
        keep_idx = verbatim_lines(cfg, folder, src_d.split("\n"))
        keep_d = keep_list(cfg, folder, src_d)
        for code in dict.fromkeys(list(titles) + list(descs)):
            t = (titles.get(code) or "").strip()
            d = (descs.get(code) or "").rstrip()
            old = live.get(code, {}).get("title")
            old_d = live.get(code, {}).get("description", "")
            if not t and not d:
                print(f"   ·  {code:<7} chưa dịch, bỏ qua")
                continue
            if code == dl:
                print(f"   ❌ {code:<7} trùng default language của video")
                errs += 1
                continue
            err, warn = [], []
            if t:
                if old == t:
                    print(f"   =  {code:<7} {t}")
                else:
                    print(f"   {'~' if old else '+'}  {code:<7} {t}  ({len(t)})" + (f"\n              cũ: {old}" if old else ""))
                err, warn = check_title(code, t, s["title"], data.get("keep") or [])
            elif not old:
                err.append("có mô tả nhưng chưa có title (YouTube cần title cho mỗi ngôn ngữ)")
            if d:
                mark = "=" if old_d == d else "~" if old_d else "+"
                print(f"   {mark}  {code:<7} mô tả: {d.count(chr(10)) + 1} dòng, {len(d.encode())} byte")
                e2, w2 = check_description(d, src_d, keep_idx, keep_d)
                err += e2
                warn += w2
            for m in err:
                print(f"      ❌ {m}")
            for m in warn:
                print(f"      ⚠️  {m}")
            errs += len(err)
            if (not t or old == t) and (not d or old_d == d):
                continue
            entry = new.setdefault(code, {})
            entry["title"] = t or old
            if d:
                entry["description"] = d
            changes.append(code)
        if errs:
            print(f"   ❌ {errs} lỗi: sửa {rel(path)}, không ghi gì")
            failed = True
            continue
        if not changes:
            print("   không có gì thay đổi")
            continue
        body, parts = {"id": vid, "localizations": new}, ["localizations"]
        if not s.get("defaultLanguage"):
            body["snippet"] = {k: s[k] for k in ("title", "description", "tags", "categoryId", "defaultAudioLanguage") if k in s}
            body["snippet"]["defaultLanguage"] = dl
            parts.append("snippet")
            print(f"   ⚠️  video chưa có default language: sẽ đặt = {dl} (gửi lại snippet y nguyên, chỉ thêm defaultLanguage)")
        if not a.yes:
            print(f"   (dry run) {len(changes)} ngôn ngữ sẽ ghi: {' '.join(changes)}. Chạy lại với --yes để ghi lên YouTube")
            continue
        from googleapiclient.errors import HttpError
        try:
            yt.videos().update(part=",".join(parts), body=body).execute()
        except HttpError as e:
            print(f"   ❌ {api_error(e)}")
            failed = True
            continue
        failed |= not verify(yt, vid, s, {c: new[c] for c in changes})
        data["applied"] = {"date": datetime.date.today().isoformat(), "languages": changes}
        data["on_youtube"] = {k: l.get("title", "") for k, l in new.items()}
        write_yaml(path, data)
    if failed:
        sys.exit(1)


def verify(yt, vid, before, want):
    ok = True
    for wait in (0, 2, 4, 8, 16):
        time.sleep(wait)
        v = get_video(yt, vid)
        locs = v.get("localizations", {})
        if all(all(locs.get(c, {}).get(f) == x for f, x in w.items()) for c, w in want.items()):
            break
    s = v["snippet"]
    for k in ("title", "description", "tags", "categoryId"):
        if s.get(k) != before.get(k):
            print(f"   ❌ {k} gốc đã bị đổi sau update! Kiểm tra ngay trong Studio")
            ok = False
    for code, w in want.items():
        got = v.get("localizations", {}).get(code, {})
        bad = [f for f, x in w.items() if got.get(f) != x]
        if bad:
            print(f"   ❌ {code}: YouTube chưa lưu {' + '.join(bad)}")
            ok = False
            continue
        loc = get_video(yt, vid, hl=code)["snippet"].get("localized", {})
        notes = [f"hl={code} trả về {f} khác" for f, x in w.items() if loc.get(f) != x]
        saved = "title + mô tả" if w.get("description") else "title"
        print(f"   ✅ {code:<7} đã lưu {saved}" + (f" ({'; '.join(notes)})" if notes else ""))
    return ok


def main():
    ap = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("auth")
    p.add_argument("--channel", required=True)
    p = sub.add_parser("list")
    p.add_argument("--channel", required=True)
    for name in ("pull", "apply"):
        p = sub.add_parser(name)
        p.add_argument("targets", nargs="*")
        p.add_argument("--channel")
        p.add_argument("--missing", action="store_true", help="mọi video của --channel còn thiếu bản dịch hoặc có bản dịch cũ")
        if name == "apply":
            p.add_argument("--yes", action="store_true", help="ghi thật lên YouTube (mặc định chỉ in thay đổi)")
    a = ap.parse_args()
    if getattr(a, "missing", False):
        if not a.channel:
            die("--missing cần --channel <ch>")
        a.targets = a.targets + missing_targets(a.channel)
    elif a.cmd in ("pull", "apply") and not a.targets:
        die("cần <target> hoặc --missing --channel <ch>")
    {"auth": cmd_auth, "list": cmd_list, "pull": cmd_pull, "apply": cmd_apply}[a.cmd](a)


if __name__ == "__main__":
    main()

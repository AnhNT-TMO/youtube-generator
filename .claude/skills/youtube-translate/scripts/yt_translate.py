#!/usr/bin/env python3
USAGE = """youtube-translate: chỉ dịch TITLE của video YouTube (video localizations). Không đụng title gốc, description, tags, ảnh.

  auth   --channel <ch>             đăng nhập OAuth một lần cho kênh (token ở .cache/tokens/<ch>.json)
  list   --channel <ch>             mọi video của kênh: ngôn ngữ đã có / còn thiếu, thư mục trong repo
  pull   <target>... [--channel]    lấy title gốc từ YouTube → title-translations.yaml (ô trống để điền bản dịch)
  apply  <target>... [--yes]        kiểm bản dịch, in thay đổi; --yes mới ghi lên YouTube, rồi đọc lại để xác nhận
  pull/apply --missing --channel <ch>   thay cho <target>: mọi video của kênh còn thiếu ít nhất một ngôn ngữ

<target> = thư mục album/single có youtube.md (dòng "Video URL"), hoặc video id / URL (cần --channel; file dịch lưu ở
channel/<ch>/translations/<id>.yaml). Ngôn ngữ đích + chữ giữ nguyên: channel/<ch>/translate.yaml. Chạy từ gốc repo.
"""
import argparse
import datetime
import re
import sys
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
    cfg["codes"] = [l["code"] for l in cfg.get("languages", [])]
    cfg["also"] = {l["code"]: l.get("also", []) for l in cfg.get("languages", [])}
    if not cfg["codes"]:
        die(f"{p.relative_to(ROOT)}: languages trống")
    return cfg


def front_matter(md):
    m = re.match(r"^---\n(.*?)\n---", Path(md).read_text(), re.S)
    return yaml.safe_load(m.group(1)) if m else {}


def song_title(folder):
    single = folder / "single.md"
    if single.exists():
        track = front_matter(single).get("track")
        return front_matter(folder / track).get("title") if track and (folder / track).exists() else None
    for md in sorted((folder / "tracks").glob("*.md")):
        fm = front_matter(md)
        if str(fm.get("track_no")) == "1":
            return fm.get("title")
    return None


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


def repo_folders(ch):
    out = {}
    for md in (ROOT / "channel" / ch).glob("*/*/youtube.md"):
        line = next((l for l in md.read_text().splitlines() if "Video URL" in l), "")
        vid = video_id_in(line)
        if vid:
            out[vid] = str(md.parent.relative_to(ROOT))
    return out


def rel(p):
    return p.relative_to(ROOT) if p.is_absolute() else p


def write_yaml(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    head = ("# skill youtube-translate. Chỉ điền `titles` (và sửa `keep` nếu cần); phần còn lại do `pull` ghi từ YouTube.\n"
            "# Ô trống = chưa dịch, apply bỏ qua. Luật dịch: .claude/skills/youtube-translate/SKILL.md\n")
    path.write_text(head + yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=1000))


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


def missing_codes(v, cfg):
    have = set(v.get("localizations", {}))
    return [c for c in cfg["codes"] + sum(cfg["also"].values(), []) if c not in have]


def missing_targets(ch):
    cfg = load_cfg(ch)
    yt = service(ch)
    folders = repo_folders(ch)
    out = [folders.get(v["id"], v["id"]) for v in channel_videos(yt, guard_channel(yt, ch, cfg)) if missing_codes(v, cfg)]
    print(f"{len(out)} video còn thiếu bản dịch: {' '.join(out) or '-'}")
    return out


def cmd_list(a):
    cfg = load_cfg(a.channel)
    yt = service(a.channel)
    me = guard_channel(yt, a.channel, cfg)
    vids = channel_videos(yt, me)
    folders = repo_folders(a.channel)
    print(f"{me['snippet']['title']}: {len(vids)} video · đích: {' '.join(cfg['codes'])}\n")
    for v in vids:
        missing = missing_codes(v, cfg)
        mark = "✅ đủ" if not missing else f"thiếu {' '.join(missing)}"
        print(f"{v['id']}  {v['status']['privacyStatus']:<8}  {mark:<28}  {folders.get(v['id'], '-')}")
        print(f"             {v['snippet']['title']}")


def keep_list(cfg, folder, source_title):
    keep = [k for k in cfg.get("keep_verbatim", []) if k in source_title]
    if folder is not None and cfg.get("keep_song_title", True):
        t = song_title(folder)
        if t and t in source_title and t not in keep:
            keep.insert(0, t)
    return keep


def cmd_pull(a):
    services = {}
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
        write_yaml(path, data)
        todo = [c for c, t in data["titles"].items() if not t]
        print(f"{rel(path)}  {s['title']}")
        print(f"   default_language={data['default_language'] or '(chưa đặt)'}  keep={data['keep']}  "
              f"cần dịch: {' '.join(todo) or 'không'}")


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


def cmd_apply(a):
    services, failed = {}, False
    for target in a.targets:
        ch, vid, path, _ = resolve(target, a.channel)
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
        dl = s.get("defaultLanguage") or cfg["source_language"]
        errs, new, changes = 0, {k: dict(l) for k, l in live.items()}, []
        titles = {}
        for code, t in (data.get("titles") or {}).items():
            for c in [code] + cfg["also"].get(code, []):
                titles.setdefault(c, t)
        for code, t in titles.items():
            t = (t or "").strip()
            if not t:
                print(f"   ·  {code:<7} chưa dịch, bỏ qua")
                continue
            if code == dl:
                print(f"   ❌ {code:<7} trùng default language của video")
                errs += 1
                continue
            old = live.get(code, {}).get("title")
            if old == t:
                print(f"   =  {code:<7} {t}")
            else:
                print(f"   {'~' if old else '+'}  {code:<7} {t}  ({len(t)})" + (f"\n              cũ: {old}" if old else ""))
            err, warn = check_title(code, t, s["title"], data.get("keep") or [])
            for m in err:
                print(f"      ❌ {m}")
            for m in warn:
                print(f"      ⚠️  {m}")
            errs += len(err)
            if old == t:
                continue
            new.setdefault(code, {})["title"] = t
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
        failed |= not verify(yt, vid, s, {c: new[c]["title"] for c in changes})
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
        if all(v.get("localizations", {}).get(c, {}).get("title") == t for c, t in want.items()):
            break
    s = v["snippet"]
    for k in ("title", "description", "tags", "categoryId"):
        if s.get(k) != before.get(k):
            print(f"   ❌ {k} gốc đã bị đổi sau update! Kiểm tra ngay trong Studio")
            ok = False
    for code, t in want.items():
        if v.get("localizations", {}).get(code, {}).get("title") != t:
            print(f"   ❌ {code}: YouTube chưa lưu title này")
            ok = False
            continue
        loc = get_video(yt, vid, hl=code)["snippet"].get("localized", {})
        note = "" if loc.get("title") == t else f" (hl={code} trả về title khác: {loc.get('title')!r})"
        print(f"   ✅ {code:<7} đã lưu{note}")
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
        p.add_argument("--missing", action="store_true", help="mọi video của --channel còn thiếu ít nhất một ngôn ngữ")
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

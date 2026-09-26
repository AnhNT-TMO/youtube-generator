from __future__ import annotations

import os
import re
import shutil
from datetime import date
from pathlib import Path

import yaml

PACKAGE_SINGLES = 1
PACKAGE_SHORTS = 1

ROOT = Path(__file__).resolve().parents[4]
IDEA_ASSETS = ["thumbnail.png", "thumbnail.jpg", "thumbnail-prompt.md", "video.json", "idea.md",
               "video/loop.mp4", "video/loop_intro.mp4", "video/loop_seam.mp4"]


def rel(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def front_matter(md: Path) -> dict:
    text = md.read_text()
    if not text.startswith("---"):
        return {}
    head = text.split("\n---", 2)
    try:
        return yaml.safe_load(head[0].lstrip("-\n")) or {}
    except yaml.YAMLError:
        return {}


def load_yaml(f: Path) -> dict:
    if not f.exists():
        return {}
    try:
        return yaml.safe_load(f.read_text()) or {}
    except yaml.YAMLError:
        return {}


def source_idea(album: Path) -> Path | None:
    src = (load_yaml(album / "plan.yaml").get("sources") or {}).get("idea")
    if not src:
        return None
    p = (ROOT / src).resolve()
    d = p.parent if p.suffix in (".yaml", ".yml") else p
    return d if d.is_dir() else None


def sync_assets(album: Path, log: list, dry: bool = False) -> list[str]:
    idea = source_idea(album)
    if not idea:
        return []
    done = []
    for f in IDEA_ASSETS:
        s, d = idea / f, album / f
        if not s.exists():
            continue
        if d.exists() and d.stat().st_mtime >= s.stat().st_mtime:
            continue
        done.append(f)
        if not dry:
            existed = d.exists()
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(s, d)
            log.append(f"⇐ {f} (từ {rel(idea)}{', thay bản cũ hơn' if existed else ''})")
    return done


def cmd_sync(a):
    from album_plan import album_dir  # noqa: WPS433 — dùng chung cách tìm album
    album = album_dir(a.album)
    if not source_idea(album):
        print(f"{rel(album)}: không làm từ idea (plan.yaml sources.idea trống) → không có gì để sync")
        return
    log = []
    sync_assets(album, log)
    print("\n".join(log) if log else f"✔ {rel(album)}: đã có bản mới nhất của mọi file hình ảnh từ idea")


CAT_COLS = ["id", "Title", "Hook", "Persona", "BPM", "Key", "Energy", "Emotion", "Role", "Intro", "Uses", "Albums",
            "Singles", "Override", "File"]


def track_rows(channel: str) -> tuple[list[dict], dict[str, list[str]]]:
    ch = ROOT / "channel" / channel
    rows, uses = [], {}
    for md in sorted(ch.glob("albums/*/tracks/*.md")):
        fm = front_matter(md)
        tid, audio = fm.get("id"), fm.get("audio")
        if not tid or not audio:
            continue
        album = md.parent.parent
        uses.setdefault(tid, []).append(album.name)
        if str(audio).startswith(".."):
            continue
        rows.append({"fm": fm, "md": md, "album": album})
    return rows, uses


def override_of(album: Path, audio: str) -> str:
    import json
    f = album / "audio" / "raw_tracks" / "manifest.json"
    if not f.exists():
        return ""
    name = Path(audio).name
    for c in json.loads(f.read_text()).get("clips", []):
        if c.get("track_file", "").endswith(name) and c.get("accept_override"):
            return c["accept_override"].get("decision") or "yes"
    return ""


def singles_of(channel: str) -> dict[str, list[str]]:
    out = {}
    for md in (ROOT / "channel" / channel).glob("singles/*/single.md"):
        fm = front_matter(md)
        if fm.get("track_id"):
            out.setdefault(str(fm["track_id"]), []).append(md.parent.name)
    return out


def cmd_catalog(a):
    ch = ROOT / "channel" / a.channel
    rows, uses = track_rows(a.channel)
    sing = singles_of(a.channel)
    cat = ch / "library" / "catalog.md"
    cell = lambda v: "" if v is None else (", ".join(map(str, v)) if isinstance(v, list) else str(v)).replace("|", "/")  # noqa: E731
    L = ["# Song Library — Catalog", "",
         f"_Sinh tự động bởi `album_plan.py catalog --channel {a.channel}` ({date.today()}). Đừng sửa tay: nguồn chính là front matter "
         "của `albums/*/tracks/*.md` (CLAUDE.md). Chỉ gồm bài đã chọn (có `audio`). Uses/Albums đếm cả album dùng lại bài "
         "qua library slot; Override = bài được duyệt dù verify không chọn (manifest `accept_override`)._", "",
         "| " + " | ".join(CAT_COLS) + " |", "|" + "---|" * len(CAT_COLS)]
    for r in sorted(rows, key=lambda r: (r["album"].name, r["fm"].get("track_no") or 0)):
        fm, tid = r["fm"], r["fm"]["id"]
        albums = uses.get(tid, [])
        link = Path(os.path.relpath(r["md"], cat.parent)).as_posix()
        vals = [tid, fm.get("title"), fm.get("hook_phrase"), fm.get("vocal_persona"), fm.get("bpm") or fm.get("target_bpm"),
                fm.get("camelot") or fm.get("key"), fm.get("energy"), fm.get("emotion"), fm.get("arc_role"), fm.get("intro_type"),
                len(albums), albums, sing.get(str(tid), []), override_of(r["album"], str(fm.get("audio"))), f"[→]({link})"]
        L.append("| " + " | ".join(cell(v) for v in vals) + " |")
    L += ["", "BPM = số đo của verify.py accept khi có, không thì tempo mục tiêu của plan (`target_bpm`)."]
    cat.parent.mkdir(parents=True, exist_ok=True)
    old = cat.read_text() if cat.exists() else ""
    cat.write_text("\n".join(L) + "\n")
    print(f"✔ {rel(cat)}: {len(rows)} bài" + (" (không đổi)" if old == "\n".join(L) + "\n" else ""))
    from album_plan import set_fm  # noqa: WPS433
    for r in rows:
        tid, albums = r["fm"]["id"], uses.get(r["fm"]["id"], [])
        want = {"used_in_albums": albums, "use_count": len(albums)}
        if str(r["fm"].get("use_count")) != str(len(albums)) or list(r["fm"].get("used_in_albums") or []) != albums:
            r["md"].write_text(set_fm(r["md"].read_text(), want))
            print(f"~ {rel(r['md'])}: use_count {len(albums)}")


def idea_state(d: Path) -> dict:
    y = load_yaml(d / "idea.yaml")
    todo = len(y.get("todo") or []) + len(re.findall(r"TODO\(claude\)", (d / "idea.yaml").read_text())) if y else 0
    st = y.get("status") or "?"
    thumb = any((d / f).exists() for f in ("thumbnail.png", "thumbnail.jpg"))
    loop = (d / "video" / "loop.mp4").exists()
    todo_l = []
    if todo:
        todo_l.append(f"analyzer: {todo} TODO trong idea.yaml")
    elif st != "promoted":
        todo_l.append("album-plan init")
    if st == "promoted":
        todo_l.append(f"(đã thành album {Path(y.get('album') or '').name}: xem dòng album)")
    elif not thumb:
        todo_l.append("thumbnail-prompt")
    elif not loop:
        todo_l.append("video-generator loop")
    return {"kind": "idea", "name": d.name, "status": st, "thumb": thumb, "loop": loop,
            "next": " · ".join(todo_l) or "xong phần idea"}


def video_state(d: Path) -> tuple[bool, bool]:
    import json
    packaged = False
    if (d / "s3-package.json").exists():
        try:
            packaged = bool(json.loads((d / "s3-package.json").read_text()))
        except ValueError:
            pass
    remote = False
    if (d / "video" / "remote.json").exists():
        try:
            remote = bool(json.loads((d / "video" / "remote.json").read_text()).get("video"))
        except ValueError:
            pass
    return (d / "video" / f"{d.name}.mp4").exists() or remote or packaged, packaged


def publish_todo(d: Path, url, yt: str, packaged: bool) -> list[str]:
    if url:
        return ([] if (d / "title-translations.yaml").exists() else ["youtube-translate"]) + ["LEARN: retention 0:15/0:30/1:00 vào youtube.md"]
    if packaged:
        return ["CHỦ KÊNH: upload từ zip S3 (s3-package.json) rồi điền Video URL vào youtube.md"]
    if not yt:
        return ["youtube-publish (soạn youtube.md) → video.py package"]
    return ["video.py package (youtube.md có rồi: publish.py check)"]


def album_state(d: Path) -> dict:
    import json
    plan = load_yaml(d / "plan.yaml")
    gen = load_yaml(d / "generation.yaml")
    tracks = sorted(d.glob("tracks/*.md"))
    fms = [front_matter(t) for t in tracks]
    n = len(plan.get("slots") or []) or len(tracks)
    chosen = sum(1 for f in fms if f.get("audio"))
    lyr_missing = 0
    for t in tracks:
        m = re.search(r"^##\s+Lyrics.*?```[a-z]*\n(.*?)```", t.read_text(), re.M | re.S)
        lyr_missing += not (m and len(m.group(1).strip().splitlines()) >= 4)
    man_f = d / "audio" / "raw_tracks" / "manifest.json"
    man = json.loads(man_f.read_text()) if man_f.exists() else {}
    drafts = sum(1 for c in man.get("clips", []) if c.get("status") == "draft" and c.get("slot") is not None)
    idea = source_idea(d)
    thumb = any((d / f).exists() for f in ("thumbnail.png", "thumbnail.jpg"))
    idea_thumb = bool(idea and any((idea / f).exists() for f in ("thumbnail.png", "thumbnail.jpg")))
    loop = (d / "video" / "loop.mp4").exists() or bool(idea and (idea / "video" / "loop.mp4").exists())
    master = (d / "audio" / "master" / f"{d.name}.wav").exists()
    video, packaged = video_state(d)
    yt = (d / "youtube.md").read_text() if (d / "youtube.md").exists() else ""
    url = re.search(r"\*\*Video URL:\*\*\s*(https?://\S+)", yt)
    pending_sync = sync_assets(d, [], dry=True) if idea else []
    status = plan.get("status") or ("legacy" if tracks else "?")
    todo = []
    if url:
        status = "uploaded"
        todo += publish_todo(d, url, yt, packaged)
    else:
        if not master:
            if not plan and not tracks:
                todo.append("album-plan init")
            elif plan and plan.get("status") != "approved":
                todo.append("album-plan: " + (f"lyrics ({lyr_missing} bài thiếu) → " if lyr_missing else "") + "duyệt → approve")
            elif drafts:
                todo.append(f"verification-audio ({drafts} clip draft)")
            elif chosen < n:
                todo.append(f"suno-generate ({n - chosen} slot)" if gen.get("status") == "approved" or not plan
                            else "album-plan build/approve")
            else:
                todo.append("album-assembly")
        if not (thumb or idea_thumb):
            todo.append("thumbnail-prompt")
        elif not loop:
            todo.append("video-generator loop")
        if pending_sync:
            todo.append("album_plan.py sync")
        if master and (thumb or idea_thumb) and not video:
            todo.append("video-generator album")
        if video:
            todo += publish_todo(d, url, yt, packaged)
    return {"kind": "album", "name": d.name, "status": status, "tracks": f"{chosen}/{n}", "drafts": drafts,
            "thumb": thumb or (f"ở idea{' (chưa sync)' if pending_sync else ''}" if idea_thumb else False),
            "loop": loop, "master": master, "video": video, "next": " · ".join(todo), "sync": pending_sync}


def single_state(d: Path) -> dict:
    fm = front_matter(d / "single.md") if (d / "single.md").exists() else {}
    thumb = any((d / f).exists() for f in ("thumbnail.png", "thumbnail.jpg"))
    master = (d / "audio" / "master" / f"{d.name}.wav").exists()
    video, packaged = video_state(d)
    yt = (d / "youtube.md").read_text() if (d / "youtube.md").exists() else ""
    url = re.search(r"\*\*Video URL:\*\*\s*(https?://\S+)", yt)
    todo = []
    if re.search(r"\*\*Trạng thái:\*\*\s*KHÔNG ĐĂNG", yt):
        todo.append("không đăng (dự phòng, xem youtube.md)")
    elif url:
        todo += publish_todo(d, url, yt, packaged)
    else:
        if not master:
            todo.append("album-assembly single")
        if not thumb:
            todo.append("thumbnail-prompt")
        elif not (d / "video" / "loop.mp4").exists():
            todo.append("video-generator loop")
        if master and thumb and not video:
            todo.append("video-generator album")
        if video:
            todo += publish_todo(d, url, yt, packaged)
    return {"kind": "single", "name": d.name, "album": Path(str(fm.get("album") or "?")).name, "status": fm.get("status") or "?", "thumb": thumb,
            "loop": (d / "video" / "loop.mp4").exists(), "master": master, "video": video, "next": " · ".join(todo)}


def short_state(d: Path) -> dict:
    fm = front_matter(d / "short.md") if (d / "short.md").exists() else {}
    thumb = (d / "thumbnail.png").exists()
    rendered = (d / "video" / "video.mp4.json").exists()
    video, packaged = video_state(d)
    yt = (d / "youtube.md").read_text() if (d / "youtube.md").exists() else ""
    url = re.search(r"\*\*Video URL:\*\*\s*(https?://\S+)", yt)
    todo = []
    if url:
        todo.append("LEARN: engaged views / viewed vs swiped / subs / click Related video vào youtube.md")
    elif packaged:
        todo.append("CHỦ KÊNH: upload từ zip S3 + gắn Related video, rồi điền Video URL")
    else:
        if not (d / "short.json").exists():
            todo.append("hook/cta → shorts.py pick")
        if not thumb:
            todo.append("thumbnail-prompt (dọc)")
        if thumb and (d / "short.json").exists() and not rendered:
            todo.append("video.py short")
        if not yt:
            todo.append("youtube.md (youtube-shorts)")
        if rendered and yt:
            todo.append("shorts.py check → video.py package")
    return {"kind": "short", "name": d.name, "album": fm.get("album") or "?", "role": fm.get("role") or "?",
            "thumb": thumb, "video": rendered, "next": " · ".join(todo)}


def cmd_board(a):
    ch = ROOT / "channel" / a.channel
    if not ch.is_dir():
        raise SystemExit(f"Không có channel/{a.channel}")
    yn = lambda v: "✔" if v is True else ("–" if not v else str(v))  # noqa: E731
    ideas = [idea_state(d) for d in sorted(ch.glob("ideas/*/")) if (d / "idea.yaml").exists()]
    albums = [album_state(d) for d in sorted(ch.glob("albums/*/")) if d.is_dir()]
    singles = [single_state(d) for d in sorted(ch.glob("singles/*/")) if d.is_dir()]
    shorts = [short_state(d) for d in sorted(ch.glob("shorts/*/")) if (d / "short.md").exists()]
    for r in albums:
        ns = sum(1 for s in singles if s["album"] == r["name"])
        n = sum(1 for s in shorts if s["album"] == r["name"])
        if r["master"] and r["video"] and ns < PACKAGE_SINGLES:
            r["next"] = " · ".join(x for x in (r["next"], f"single ({ns}/{PACKAGE_SINGLES})") if x)
        if r["master"] and r["video"] and n < PACKAGE_SHORTS:
            r["next"] = " · ".join(x for x in (r["next"], f"youtube-shorts ({n}/{PACKAGE_SHORTS} Short)") if x)
    print(f"# {a.channel} · {date.today()}\n")
    if ideas:
        print("## Ideas\n\n| Idea | Status | Thumb | Loop | Việc còn lại (làm song song được) |\n|---|---|---|---|---|")
        for r in ideas:
            print(f"| {r['name']} | {r['status']} | {yn(r['thumb'])} | {yn(r['loop'])} | {r['next']} |")
    if albums:
        print("\n## Albums\n\n| Album | Plan | Bài | Draft | Thumb | Loop | Master | Video | Việc còn lại |\n|---|---|---|---|---|---|---|---|---|")
        for r in albums:
            print(f"| {r['name']} | {r['status']} | {r['tracks']} | {r['drafts'] or '–'} | {yn(r['thumb'])} | {yn(r['loop'])} | "
                  f"{yn(r['master'])} | {yn(r['video'])} | {r['next']} |")
    if singles:
        print("\n## Singles\n\n| Single | Status | Thumb | Master | Video | Việc còn lại |\n|---|---|---|---|---|---|")
        for r in singles:
            print(f"| {r['name']} | {r['status']} | {yn(r['thumb'])} | {yn(r['master'])} | {yn(r['video'])} | {r['next']} |")
    if shorts:
        print("\n## Shorts\n\n| Short | Album | Role | Ảnh dọc | Video | Việc còn lại |\n|---|---|---|---|---|---|")
        for r in shorts:
            print(f"| {r['name']} | {r['album']} | {r['role']} | {yn(r['thumb'])} | {yn(r['video'])} | {r['next']} |")
    stale = [r["name"] for r in albums if r.get("sync")]
    if stale:
        print(f"\n⚠ Idea có file hình ảnh mới hơn album: {', '.join(stale)} → `album_plan.py sync <album>`")

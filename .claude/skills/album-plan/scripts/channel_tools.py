"""Việc ở cấp channel, để các bước chạy độc lập và không theo thứ tự (analyze 20 video → plan → thumbnail/loop cho
nhiều idea → lúc khác mới Suno/verify/ghép/upload):

  board    bảng trạng thái mọi idea / album / single của channel + bước tiếp theo của từng cái (chỉ đọc)
  sync     album làm từ idea: chép sang album các file hình ảnh mà idea có bản mới hơn (thumbnail, video.json, loop)
  catalog  dựng lại library/catalog.md từ front matter của mọi bài đã chọn (nguồn chính = tracks/*.md)

Gọi qua album_plan.py: `P board --channel <ch>` · `P sync <album>` · `P catalog --channel <ch>`.
"""
from __future__ import annotations

import os
import re
import shutil
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]
# Khi idea đã thành album, các file này có thể được làm (lại) ở thư mục idea sau lúc init → sync chép bản mới hơn.
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
    """Thư mục idea gốc của album (plan.yaml sources.idea), None nếu album không làm từ idea."""
    src = (load_yaml(album / "plan.yaml").get("sources") or {}).get("idea")
    if not src:
        return None
    p = (ROOT / src).resolve()
    d = p.parent if p.suffix in (".yaml", ".yml") else p
    return d if d.is_dir() else None


# ---------------------------------------------------------------- sync

def sync_assets(album: Path, log: list, dry: bool = False) -> list[str]:
    """Chép từ idea gốc những file album chưa có hoặc cũ hơn. Không bao giờ xoá; bản ở album mới hơn thì giữ."""
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


# ---------------------------------------------------------------- catalog

CAT_COLS = ["id", "Title", "Hook", "Persona", "BPM", "Key", "Energy", "Emotion", "Role", "Intro", "Uses", "Albums",
            "Singles", "Override", "File"]


def track_rows(channel: str) -> tuple[list[dict], dict[str, list[str]]]:
    """(các bài gốc đã chọn, id → mọi album dùng bài đó). Bài gốc = track md có audio nằm trong chính album đó;
    bản chép của library slot (audio trỏ sang album khác) chỉ tính là một lần dùng."""
    ch = ROOT / "channel" / channel
    rows, uses = [], {}
    for md in sorted(ch.glob("albums/*/tracks/*.md")):
        fm = front_matter(md)
        tid, audio = fm.get("id"), fm.get("audio")
        if not tid or not audio:
            continue
        album = md.parent.parent
        uses.setdefault(tid, []).append(album.name)
        if str(audio).startswith(".."):   # library slot: audio ở album gốc
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
         "của `albums/*/tracks/*.md` (CLAUDE.md §7). Chỉ gồm bài đã chọn (có `audio`). Uses/Albums đếm cả album dùng lại bài "
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
    # Front matter `used_in_albums`/`use_count` của bài gốc theo đúng số lần dùng
    from album_plan import set_fm  # noqa: WPS433
    for r in rows:
        tid, albums = r["fm"]["id"], uses.get(r["fm"]["id"], [])
        want = {"used_in_albums": albums, "use_count": len(albums)}
        if str(r["fm"].get("use_count")) != str(len(albums)) or list(r["fm"].get("used_in_albums") or []) != albums:
            r["md"].write_text(set_fm(r["md"].read_text(), want))
            print(f"~ {rel(r['md'])}: use_count {len(albums)}")


# ---------------------------------------------------------------- board

def idea_state(d: Path) -> dict:
    y = load_yaml(d / "idea.yaml")
    todo = len(y.get("todo") or []) + len(re.findall(r"TODO\(claude\)", (d / "idea.yaml").read_text())) if y else 0
    st = y.get("status") or "?"
    thumb = any((d / f).exists() for f in ("thumbnail.png", "thumbnail.jpg"))
    loop = (d / "video" / "loop.mp4").exists()
    # Hai nhánh độc lập: nhạc (idea hoàn chỉnh → plan) và hình (thumbnail → loop). Làm nhánh nào trước cũng được.
    todo_l = []
    if todo:
        todo_l.append(f"analyzer: {todo} TODO trong idea.yaml")
    elif st != "promoted":
        todo_l.append("album-plan init")
    if not thumb:
        todo_l.append("thumbnail-prompt")
    elif not loop:
        todo_l.append("video-generator loop")
    if st == "promoted":
        todo_l.append(f"(đã thành album {Path(y.get('album') or '').name})")
    return {"kind": "idea", "name": d.name, "status": st, "thumb": thumb, "loop": loop,
            "next": " · ".join(todo_l) or "xong phần idea"}


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
    video = (d / "video" / f"{d.name}.mp4").exists()
    yt = (d / "youtube.md").read_text() if (d / "youtube.md").exists() else ""
    url = re.search(r"\*\*Video URL:\*\*\s*(https?://\S+)", yt)
    pending_sync = sync_assets(d, [], dry=True) if idea else []
    status = plan.get("status") or ("legacy" if tracks else "?")
    todo = []
    if url:
        status = "uploaded"
        todo.append("LEARN: retention 0:15/0:30/1:00 vào youtube.md")
    else:
        # nhánh nhạc: plan → Suno → verify → ghép
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
        # nhánh hình: thumbnail → loop (ở album hoặc ở idea gốc)
        if not (thumb or idea_thumb):
            todo.append("thumbnail-prompt")
        elif not loop:
            todo.append("video-generator loop")
        if pending_sync:
            todo.append("album_plan.py sync")
        # hợp hai nhánh
        if master and (thumb or idea_thumb) and not video:
            todo.append("video-generator album")
        if video:
            todo.append("youtube-publish → upload" + (" (youtube.md có rồi: publish.py check)" if yt else ""))
    return {"kind": "album", "name": d.name, "status": status, "tracks": f"{chosen}/{n}", "drafts": drafts,
            "thumb": thumb or (f"ở idea{' (chưa sync)' if pending_sync else ''}" if idea_thumb else False),
            "loop": loop, "master": master, "video": video, "next": " · ".join(todo), "sync": pending_sync}


def single_state(d: Path) -> dict:
    fm = front_matter(d / "single.md") if (d / "single.md").exists() else {}
    thumb = any((d / f).exists() for f in ("thumbnail.png", "thumbnail.jpg"))
    master = (d / "audio" / "master" / f"{d.name}.wav").exists()
    video = (d / "video" / f"{d.name}.mp4").exists()
    yt = (d / "youtube.md").read_text() if (d / "youtube.md").exists() else ""
    url = re.search(r"\*\*Video URL:\*\*\s*(https?://\S+)", yt)
    todo = []
    if url:
        todo.append("đã upload")
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
            todo.append("youtube-publish (single) → upload")
    return {"kind": "single", "name": d.name, "status": fm.get("status") or "?", "thumb": thumb,
            "loop": (d / "video" / "loop.mp4").exists(), "master": master, "video": video, "next": " · ".join(todo)}


def cmd_board(a):
    ch = ROOT / "channel" / a.channel
    if not ch.is_dir():
        raise SystemExit(f"Không có channel/{a.channel}")
    yn = lambda v: "✔" if v is True else ("–" if not v else str(v))  # noqa: E731
    ideas = [idea_state(d) for d in sorted(ch.glob("ideas/*/")) if (d / "idea.yaml").exists()]
    albums = [album_state(d) for d in sorted(ch.glob("albums/*/")) if d.is_dir()]
    singles = [single_state(d) for d in sorted(ch.glob("singles/*/")) if d.is_dir()]
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
    stale = [r["name"] for r in albums if r.get("sync")]
    if stale:
        print(f"\n⚠ Idea có file hình ảnh mới hơn album: {', '.join(stale)} → `album_plan.py sync <album>`")

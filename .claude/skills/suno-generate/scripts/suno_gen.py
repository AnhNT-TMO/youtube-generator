from __future__ import annotations
USAGE = """Sổ sách + kiểm tra cho skill `suno-generate` (điều khiển suno.com qua Chrome DevTools MCP, tải qua usesuno).

Claude thao tác trên browser; script này lo phần phải CHÍNH XÁC: settings của từng lượt, đối chiếu form/request/feed với
settings đó, đặt tên + kiểm tra file tải về, và ghi `audio/raw_tracks/manifest.json` (index clip ↔ slot ↔ lượt).

    SK=.claude/skills/suno-generate; P="$SK/.venv/bin/python $SK/scripts/suno_gen.py"
    $P validate <album>                                   # kiểm tra generation.yaml (+ lyrics trong track md)
    $P status   <album>                                   # slot nào đã tạo mấy lượt, clip nào chờ tải, credits
    $P next     <album> [--slot N] [--purpose more|regenerate|variant|test --reason "..."] [--variant NAME]
                                                          # → notes/suno/<gen>.spec.json (+ .lyrics.txt, .style.txt)
    $P js       <name> [--album A --gen G | --clip ID]    # in JS (scripts/js/<name>.js) đã điền tham số
    $P check-form <album> <gen> <form.json>               # form đang hiển thị == spec? (TRƯỚC khi bấm Create)
    $P submitted  <album> <gen> [--request F --response F | --clips id1,id2] [--credits-before N]
    $P complete   <album> <gen> <feed.json> [--credits-after N]
    $P ingest     <album> --clip ID [--file PATH]         # ~/Downloads → raw_tracks/<slug> <id8>.wav
    $P quota      <album> --credits N --downloads-used N --context "..."   # quota tải chính thức KHÔNG được tăng
    $P cover-source <album> <gen> --clip ID               # lượt Cover: ghi clip nguồn (bản upload hoặc clip của mình)

`<album>` là đường dẫn thư mục album hoặc chỉ tên (vd. `002-<slug>`). Mã lượt (gen) dạng `s01-r03`.
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
import wave
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]
JS_DIR = Path(__file__).resolve().parent / "js"
DOWNLOADS = Path.home() / "Downloads"

MODELS = {"v6": "chirp-hawk", "v6-wild": "chirp-hawk-wild"}
SLIDERS = {"weirdness": "Weirdness", "style_influence": "Style Influence",
           "audio_influence": "Audio Influence", "variety": "Variety"}
SUNO_DEFAULTS = {"weirdness": 50, "style_influence": 50, "audio_influence": 25, "variety": 1}
REQ_SLIDER_KEYS = {"weirdness": ["weirdness_constraint"], "style_influence": ["style_weight"],
                   "audio_influence": ["audio_weight"], "variety": ["aug_creativity"]}
OPEN_STATES = ("prepared", "submitted", "complete")
COVER_KINDS = ("own_rendition", "own_suno_clip", "pd_recording")
COVER_MAX_S = 480


def die(msg: str, code: int = 1):
    print(f"✖ {msg}", file=sys.stderr)
    sys.exit(code)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def album_dir(arg: str) -> Path:
    p = Path(arg)
    if p.is_dir():
        return p.resolve()
    hits = list(ROOT.glob(f"channel/*/albums/{arg}"))
    if len(hits) == 1:
        return hits[0]
    die(f"Không tìm thấy album '{arg}'")


def rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def arel(album: Path, p: Path | None) -> str | None:
    if p is None:
        return None
    try:
        return str(Path(p).resolve().relative_to(album.resolve()))
    except ValueError:
        return rel(Path(p))


def read_lyrics(md: Path) -> str | None:
    if not md.exists():
        return None
    m = re.search(r"^##\s+Lyrics.*?$(.*)", md.read_text(), re.M | re.S)
    b = m and re.search(r"```[a-z]*\n(.*?)```", m.group(1), re.S)
    if not b or len(b.group(1).strip().splitlines()) < 4:
        return None
    return b.group(1).strip("\n")


def lyric_lines(s: str | None) -> list[str]:
    return [ln.strip() for ln in (s or "").splitlines() if ln.strip()]


def norm(s: str | None) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def render_style(text: str, bpm) -> str:
    return text.replace("{bpm}", str(bpm)) if bpm is not None else text


def mmss(sec: float) -> str:
    return f"{int(sec) // 60}:{int(sec) % 60:02d}"


def load_json_loose(path: Path):
    txt = Path(path).read_text()
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        m = re.search(r"```(?:json)?\s*(.*?)```", txt, re.S) or re.search(r"([\[{].*[\]}])", txt, re.S)
        if not m:
            die(f"{path}: không đọc được JSON")
        return json.loads(m.group(1))


def audio_duration(p: Path) -> float:
    if p.suffix.lower() == ".wav":
        try:
            with wave.open(str(p)) as w:
                return w.getnframes() / w.getframerate()
        except wave.Error:
            pass
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                         capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Plan:
    def __init__(self, album: Path):
        self.album = album
        f = album / "generation.yaml"
        if not f.exists():
            die(f"Chưa có {rel(f)} — copy templates/generation.yaml rồi điền (xem skill suno-generate)")
        self.raw = yaml.safe_load(f.read_text()) or {}
        self.slots = {int(s["n"]): s for s in self.raw.get("slots") or []}

    @property
    def defaults(self) -> dict:
        return self.raw.get("defaults") or {}

    def slot(self, n: int) -> dict:
        if n not in self.slots:
            die(f"generation.yaml không có slot {n}")
        return self.slots[n]

    def variant(self, n: int, name: str | None) -> dict | None:
        if not name:
            return None
        for v in self.slot(n).get("variants") or []:
            if v.get("name") == name:
                return v
        die(f"Slot {n} không có variant '{name}'")

    def settings(self, n: int, variant: dict | None = None) -> dict:
        s = dict(self.defaults)
        s.update(self.slot(n).get("overrides") or {})
        if variant:
            s.update(variant.get("overrides") or {})
        return s

    def lyrics_path(self, n: int, variant: dict | None = None) -> Path:
        f = (variant or {}).get("lyrics_file") or self.slot(n).get("track")
        return self.album / f if f else None

    def credits_per_gen(self, settings: dict) -> int:
        c = (self.raw.get("budget") or {}).get("credits_per_generation") or {}
        return int(c.get("max", 20)) if settings.get("max_mode") else int(c.get("normal", 10))


def check_settings(s: dict, where: str, errs: list, warns: list):
    if s.get("model") not in MODELS:
        errs.append(f"{where}: model '{s.get('model')}' — chỉ dùng {list(MODELS)}")
    v = s.get("voice")
    if v is not None and not (isinstance(v, dict) and v.get("name") and v.get("id")):
        errs.append(f"{where}: voice phải là null hoặc {{name, id}}")
    if s.get("vocal_gender") not in ("male", "female", None):
        errs.append(f"{where}: vocal_gender = male | female | null")
    d = s.get("duration", "auto")
    if d != "auto" and not (isinstance(d, int) and 10 <= d <= 360):
        errs.append(f"{where}: duration = auto hoặc số giây 10–360 (đang là {d!r})")
    for k, hi in (("weirdness", 100), ("style_influence", 100), ("audio_influence", 100), ("variety", 4)):
        x = s.get(k)
        if k == "audio_influence" and not v:
            continue
        if not isinstance(x, int) or isinstance(x, bool) or not 0 <= x <= hi:
            errs.append(f"{where}: {k} phải là MỘT số nguyên 0–{hi} (đang là {x!r}; không dùng dải)")
    if s.get("variety", 0) >= 1:
        warns.append(f"{where}: variety >= 1 → Suno viết lại Style prompt (spike 23/09); nên để 0")
    if not isinstance(s.get("max_mode"), bool):
        errs.append(f"{where}: max_mode phải là true/false")
    b = s.get("bpm")
    if b is not None and (not isinstance(b, int) or isinstance(b, bool) or not 30 <= b <= 200):
        errs.append(f"{where}: bpm phải là số nguyên 30–200 (đang là {b!r})")
    if s.get("personalize", "off") not in ("off", False):
        warns.append(f"{where}: personalize nên để off")


def validate(plan: Plan, strict_status: bool = False) -> tuple[list, list]:
    errs, warns = [], []
    r = plan.raw
    if r.get("schema_version") != 1:
        errs.append("schema_version phải là 1")
    st = r.get("style") or {}
    text = norm(st.get("text"))
    if not text or text.startswith("("):
        errs.append("style.text trống")
    else:
        for n in sorted(plan.slots) or [None]:
            b = plan.settings(n).get("bpm") if n is not None else plan.defaults.get("bpm")
            if "{bpm}" in text and b is None:
                errs.append(f"style.text có {{bpm}} nhưng slot {n} không có bpm (defaults.bpm hoặc overrides.bpm)")
                break
            ln = len(render_style(text, b))
            if ln > 1000:
                errs.append(f"style.text dài {ln} ký tự sau khi thay {{bpm}} (> 1000, giới hạn ô Style của Suno)")
                break
    if not st.get("version"):
        warns.append("style.version trống (ghi vào track md style_prompt_version)")
    if re.search(r"[À-ỹđĐ]", text + (st.get("exclude") or "")):
        errs.append("style có ký tự tiếng Việt — text nhập vào Suno phải là tiếng Anh (CLAUDE.md)")
    check_settings(plan.defaults, "defaults", errs, warns)
    if not plan.slots:
        errs.append("slots trống")
    for n, sl in plan.slots.items():
        cv = sl.get("cover")
        if not cv:
            continue
        if cv.get("kind") not in COVER_KINDS:
            errs.append(f"slot {n}: cover.kind phải là {' | '.join(COVER_KINDS)}")
        elif cv["kind"] == "own_suno_clip":
            if not cv.get("clip_id"):
                errs.append(f"slot {n}: cover own_suno_clip cần clip_id (clip Suno của mình làm nguồn)")
        else:
            f = plan.album / str(cv.get("file") or "")
            if not cv.get("file"):
                errs.append(f"slot {n}: cover.file trống (đường dẫn tính từ thư mục album, vd. notes/suno/s{n:02d}-cover-source.wav)")
            elif not f.is_file():
                warns.append(f"slot {n}: chưa có nguồn cover {cv['file']} — dựng trước `next --slot {n}` (own_rendition: scripts/pd_source.py)")
            elif audio_duration(f) > COVER_MAX_S:
                errs.append(f"slot {n}: nguồn cover dài {audio_duration(f):.0f} s > {COVER_MAX_S} s")
    order = r.get("order") or []
    for n in order:
        if n not in plan.slots:
            errs.append(f"order có slot {n} nhưng slots không có")
    if order and set(plan.slots) - set(order):
        warns.append(f"slot {sorted(set(plan.slots) - set(order))} không có trong order (sẽ không được generate tự động)")
    if plan.slots and 1 in plan.slots and order and order[0] != 1:
        warns.append("order không bắt đầu bằng slot 1 (title track phải đi trước — CLAUDE.md)")
    planned_credits = 0
    for n, s in sorted(plan.slots.items()):
        w = f"slot {n}"
        if not s.get("title"):
            errs.append(f"{w}: thiếu title")
        elif re.search(r"[À-ỹđĐ]", s["title"]):
            errs.append(f"{w}: title có ký tự tiếng Việt")
        variants = s.get("variants") or []
        for v in [None] + variants:
            ww = w + (f" / variant {v.get('name')}" if v else "")
            if v is not None and not v.get("name"):
                errs.append(f"{ww}: variant thiếu name")
            check_settings(plan.settings(n, v), ww, errs, warns)
            if s.get("instrumental"):
                continue
            lp = plan.lyrics_path(n, v)
            if lp is None:
                errs.append(f"{ww}: thiếu track (file md chứa lyrics)")
                continue
            ly = read_lyrics(lp)
            if ly is None:
                errs.append(f"{ww}: {rel(lp)} chưa có lyrics (khối ``` sau '## Lyrics', >= 4 dòng)")
                continue
            if len(ly) > 5000:
                errs.append(f"{ww}: lyrics {len(ly)} ký tự (> 5000)")
            elif len(ly) > 3000:
                warns.append(f"{ww}: lyrics {len(ly)} ký tự (> 3000, dễ bị hát thiếu)")
            if re.search(r"[À-ỹđĐ]", ly):
                errs.append(f"{ww}: lyrics có ký tự tiếng Việt")
        rounds = s.get("rounds")
        if not isinstance(rounds, int) or rounds < 1:
            errs.append(f"{w}: rounds phải là số nguyên >= 1")
            rounds = 0
        if variants and sum(int(v.get("rounds", 0)) for v in variants) > rounds:
            warns.append(f"{w}: tổng rounds của variants > rounds của slot")
        if n == 1 and rounds * 2 < 4:
            warns.append("slot 1: < 4 clip dự kiến (title track nên có >= 4 clip để chọn)")
        if n > 1 and not plan.settings(n).get("voice"):
            warns.append(f"{w}: không dùng Voice → giọng dễ lệch khỏi Anchor (CLAUDE.md)")
        planned_credits += rounds * plan.credits_per_gen(plan.settings(n))
    cap = (r.get("budget") or {}).get("max_credits")
    if cap and planned_credits > cap:
        warns.append(f"credits dự kiến {planned_credits} > budget.max_credits {cap}")
    if not (plan.album / "selection.yaml").exists():
        warns.append("chưa có selection.yaml (verification-audio cần) → chạy album-plan build")
    if strict_status and r.get("status") != "approved":
        errs.append(f"status = {r.get('status')!r} — người dùng phải duyệt plan (status: approved) trước khi tốn credits")
    return errs, warns


def manifest_path(album: Path) -> Path:
    return album / "audio" / "raw_tracks" / "manifest.json"


def load_manifest(album: Path) -> dict:
    f = manifest_path(album)
    man = json.loads(f.read_text()) if f.exists() else {}
    man.setdefault("note", "Bản nháp tải về từ Suno. Bài được chọn nằm ở ../tracks/. Chỉ tải qua usesuno (không dùng Download của Suno).")
    man.setdefault("clips", [])
    man.setdefault("generations", [])
    man.setdefault("quota_log", [])
    return man


def save_manifest(album: Path, man: dict):
    f = manifest_path(album)
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(man, indent=1, ensure_ascii=False) + "\n")
    tmp.replace(f)


def get_gen(man: dict, gid: str) -> dict:
    for g in man["generations"]:
        if g["id"] == gid:
            return g
    die(f"Không có lượt '{gid}' trong manifest (chạy `next` trước)")


def slot_gens(man: dict, n: int) -> list[dict]:
    return [g for g in man["generations"] if g.get("slot") == n and g.get("status") != "abandoned"]


def credits_spent(man: dict, plan: Plan) -> int:
    tot = 0
    for g in man["generations"]:
        if g.get("status") in ("submitted", "complete", "downloaded", "failed"):
            tot += g.get("credits") if g.get("credits") is not None else g.get("expected_credits", 0)
    return tot


def slot_selected(man: dict, n: int) -> dict | None:
    return next((c for c in man["clips"] if c.get("slot") == n and c.get("status") == "selected"), None)


def spec_path(album: Path, gid: str, ext: str = "spec.json") -> Path:
    return album / "notes" / "suno" / f"{gid}.{ext}"


def load_spec(album: Path, gid: str) -> dict:
    f = spec_path(album, gid)
    if not f.exists():
        die(f"Không có {rel(f)}")
    return json.loads(f.read_text())


def cmd_validate(a):
    plan = Plan(album_dir(a.album))
    errs, warns = validate(plan, strict_status=False)
    for w in warns:
        print(f"⚠ {w}")
    for e in errs:
        print(f"✖ {e}")
    st = plan.raw.get("status")
    total = sum(int(s.get("rounds") or 0) for s in plan.slots.values())
    cr = sum(int(s.get("rounds") or 0) * plan.credits_per_gen(plan.settings(n)) for n, s in plan.slots.items())
    print(f"\n{len(plan.slots)} slot · {total} lượt dự kiến ({total * 2} clip) · ~{cr} credits · status: {st}")
    if errs:
        sys.exit(1)
    print("✔ plan hợp lệ" + ("" if st == "approved" else " — nhưng chưa approved: chưa được generate"))


def cmd_status(a):
    album = album_dir(a.album)
    plan = Plan(album)
    man = load_manifest(album)
    cap = (plan.raw.get("budget") or {}).get("max_credits")
    print(f"# {album.name} — generation status\n")
    print(f"credits đã dùng (theo manifest): {credits_spent(man, plan)}" + (f" / trần {cap}" if cap else ""))
    for q in man["quota_log"]:
        if q.get("alert"):
            print(f"🚨 quota tải chính thức từng TĂNG: {q['alert']} ({q['at']}, {q['context']}) — kiểm tra lại")
    if man["quota_log"]:
        q = man["quota_log"][-1]
        print(f"lần đọc tài khoản gần nhất: {q['at']} · credits {q['credits']} · downloads chính thức {q['downloads_used']}")
    print("\n| slot | title | lượt (dự kiến) | thêm | clip đã tải | chờ tải | verify | đã chọn |")
    print("|---|---|---|---|---|---|---|---|")
    order = plan.raw.get("order") or sorted(plan.slots)
    for n in order:
        s = plan.slot(n)
        gs = slot_gens(man, n)
        done = [g for g in gs if g["status"] in ("submitted", "complete", "downloaded")]
        extra = [g for g in done if g.get("purpose") not in ("planned", "variant")]
        clips = [c for c in man["clips"] if c.get("slot") == n and c.get("generation")]
        pending = sum(len(set(g.get("clip_ids", [])) - {c["clip_id"] for c in clips}) for g in done)
        vf = album / "notes" / f"verify-slot-{n:02d}.json"
        dec = json.loads(vf.read_text()).get("decision") if vf.exists() else "-"
        sel = slot_selected(man, n)
        print(f"| {n} | {s.get('title')} | {len(done) - len(extra)}/{s.get('rounds')} | {len(extra)} | {len(clips)} | "
              f"{pending or ''} | {dec} | {sel['file'] if sel else ''} |")
    opn = [g for g in man["generations"] if g["status"] in OPEN_STATES]
    if opn:
        print("\n## Lượt chưa xong (làm tiếp từ đây)")
        nxt = {"prepared": "điền form → check-form → Create → submitted", "submitted": "poll_feed → complete",
               "complete": "tải qua usesuno → ingest từng clip"}
        for g in opn:
            print(f"- `{g['id']}` slot {g['slot']} · {g['status']} → {nxt[g['status']]}")


def cmd_next(a):
    album = album_dir(a.album)
    plan = Plan(album)
    errs, _ = validate(plan, strict_status=a.purpose != "test")
    if errs:
        die("plan chưa hợp lệ:\n  " + "\n  ".join(errs) + f"\n(chạy: suno_gen.py validate {a.album})")
    man = load_manifest(album)
    opn = [g for g in man["generations"] if g["status"] == "submitted"]
    if opn and not a.force:
        die(f"Còn lượt chưa xong: {', '.join(g['id'] + ' (' + g['status'] + ')' for g in opn)} — poll + complete trước (tải có thể để cuối đợt)")
    order = plan.raw.get("order") or sorted(plan.slots)
    n = a.slot
    if n is None:
        n = next((k for k in order if not slot_selected(man, k) and
                  len([g for g in slot_gens(man, k) if g["status"] != "prepared" and g.get("purpose") in ("planned", "variant")])
                  < int(plan.slot(k).get("rounds", 0))), None)
        if n is None:
            die("Mọi slot đã đủ lượt dự kiến. Lượt thêm: --slot N --purpose more|regenerate --reason ...")
    s = plan.slot(n)
    gates = plan.raw.get("gates") or {}
    if n != 1 and gates.get("anchor_first", True) and 1 in plan.slots and not slot_selected(man, 1) and not a.force:
        die("Slot 1 (title track/Anchor) chưa được chốt (verification-audio accept) → chưa generate slot khác (gates.anchor_first)")
    if slot_selected(man, n) and not a.force:
        die(f"Slot {n} đã có bài được chọn ({slot_selected(man, n)['file']}). Muốn tạo tiếp: --force")

    gens = slot_gens(man, n)
    prepared = next((g for g in gens if g["status"] == "prepared"), None)
    counted = [g for g in gens if g["status"] != "prepared"]
    planned_done = len([g for g in counted if g.get("purpose") in ("planned", "variant")])
    purpose = a.purpose
    if purpose is None:
        if planned_done >= int(s.get("rounds", 0)):
            die(f"Slot {n} đã đủ {s.get('rounds')} lượt dự kiến. Lượt thêm phải ghi rõ: "
                "--purpose more (người dùng muốn thêm) | regenerate (verify: REGENERATE) --reason \"...\"")
        purpose = "planned"
    if purpose in ("more", "regenerate") and not a.reason:
        die(f"--purpose {purpose} cần --reason (vd. quyết định + hints của notes/verify-slot-{n:02d}.json)")

    variant = plan.variant(n, a.variant)
    if variant is None and s.get("variants") and purpose == "planned":
        for v in s["variants"]:
            if len([g for g in counted if g.get("variant") == v["name"]]) < int(v.get("rounds", 0)):
                variant = v
                break
    cv = s.get("cover") or {}
    if cv and cv.get("kind") != "own_suno_clip" and not (plan.album / str(cv.get("file") or "")).is_file():
        die(f"Slot {n} là Cover nhưng chưa có nguồn {cv.get('file')} (SKILL.md §3b: own_rendition → scripts/pd_source.py)")
    st = plan.settings(n, variant)
    lp = plan.lyrics_path(n, variant)
    lyrics = "" if s.get("instrumental") else read_lyrics(lp)
    lyrics_changed = False
    if s.get("lyrics_sha8") and not variant and lyrics:
        cur = hashlib.sha256(lyrics.encode()).hexdigest()[:8]
        if cur != s["lyrics_sha8"]:
            if not a.accept_lyrics_change:
                die(f"Lyrics slot {n} ({rel(lp)}) đã đổi so với bản đã duyệt ({s['lyrics_sha8']} → {cur}). "
                    "Trước khi generate: plan chưa generate → chạy album-plan build/approve lại; đang REGENERATE có sửa lời "
                    "và người dùng đã đồng ý → thêm --accept-lyrics-change")
            lyrics_changed = True
    expected = plan.credits_per_gen(st)
    cap = (plan.raw.get("budget") or {}).get("max_credits")
    spent = credits_spent(man, plan)
    if cap and spent + expected > cap and not a.allow_over_budget:
        die(f"Vượt trần credits: đã dùng {spent} + lượt này {expected} > {cap}. Hỏi người dùng rồi dùng --allow-over-budget")

    rnd = prepared["round"] if prepared else len(counted) + 1
    gid = f"s{n:02d}-r{rnd:02d}"
    d = st.get("duration", "auto")
    form = {
        "model": st["model"],
        "voice": st.get("voice"),
        "lyrics": lyrics,
        "instrumental": bool(s.get("instrumental")),
        "style": render_style(norm((plan.raw.get("style") or {}).get("text")), st.get("bpm")),
        "exclude": norm((plan.raw.get("style") or {}).get("exclude")),
        "vocal_gender": st.get("vocal_gender"),
        "duration": "auto" if d == "auto" else {"seconds": d, "mmss": mmss(d)},
        "max_mode": st["max_mode"],
        "weirdness": st["weirdness"],
        "style_influence": st["style_influence"],
        "audio_influence": st.get("audio_influence") if st.get("voice") else None,
        "variety": st["variety"],
        "personalize": "off",
        "title": s["title"],
        "cover": s.get("cover") or None,
    }
    spec = {"gen": gid, "album": album.name, "slot": n, "round": rnd, "purpose": purpose, "reason": a.reason,
            "variant": variant.get("name") if variant else None, "lyrics_file": arel(album, lp),
            "style_version": (plan.raw.get("style") or {}).get("version"), "prompt_bpm": st.get("bpm"), "form": form,
            "expect": {"credits": expected, "clips": 2}, "created_at": now()}
    sp = spec_path(album, gid)
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n")
    spec_path(album, gid, "lyrics.txt").write_text((lyrics or "") + "\n")
    spec_path(album, gid, "style.txt").write_text(form["style"] + "\n")
    entry = {"id": gid, "slot": n, "round": rnd, "title": s["title"], "purpose": purpose, "reason": a.reason,
             "variant": spec["variant"], "spec": arel(album, sp), "expected_credits": expected, "status": "prepared",
             "lyrics_changed_after_approval": lyrics_changed,
             "prepared_at": now(), "clip_ids": []}
    if prepared:
        prepared.update(entry)
    else:
        man["generations"].append(entry)
    save_manifest(album, man)

    v = form["voice"]
    print(f"GEN={gid}\nspec: {rel(sp)}\n")
    print(f"slot {n} · \"{s['title']}\" · lượt {rnd} · {purpose}" + (f" · variant {spec['variant']}" if spec["variant"] else "")
          + (f"\n  lý do: {a.reason}" if a.reason else ""))
    print(f"  model {form['model']} · voice {v['name'] if v else '—'} · gender {form['vocal_gender'] or 'tự do'} · "
          f"max {'On' if form['max_mode'] else 'Off'} · duration {d if d == 'auto' else mmss(d)}")
    if st.get("bpm") is not None:
        print(f"  tempo {st['bpm']} BPM (đã điền vào Style)")
    if form["cover"]:
        cv = form["cover"]
        print(f"  COVER ({cv['kind']}): nguồn {cv.get('clip_id') or cv.get('file')} → SKILL.md §3b: "
              + ("mở clip đó → ⋯ → Remix → Cover" if cv["kind"] == "own_suno_clip"
                 else "Upload Audio đúng file này → `cover-source` với clip id của bản upload → ⋯ → Remix → Cover")
              + "; rồi điền form như thường (lyrics PD, Style, Voice) và check-form")
    print(f"  weirdness {form['weirdness']} · style influence {form['style_influence']} · "
          f"audio influence {form['audio_influence'] if v else '—'} · variety {form['variety']} · personalize off")
    print(f"  style {len(form['style'])}/1000 ký tự ({rel(spec_path(album, gid, 'style.txt'))})")
    print(f"  lyrics {len(lyrics or '')} ký tự, {len(lyric_lines(lyrics))} dòng ({rel(spec_path(album, gid, 'lyrics.txt'))})"
          if not form["instrumental"] else "  instrumental: để trống lyrics")
    print(f"  exclude: {form['exclude']}")
    print(f"  credits dự kiến {expected} (đã dùng {spent}{f' / trần {cap}' if cap else ''})")


def cmd_js(a):
    f = JS_DIR / f"{a.name}.js"
    if not f.exists():
        die(f"Không có {rel(f)}. Có: {', '.join(p.stem for p in JS_DIR.glob('*.js'))}")
    src = f.read_text()
    params = None
    if "/*PARAMS*/" in src:
        album = album_dir(a.album) if a.album else None
        if a.name == "set_sliders":
            form = load_spec(album, a.gen)["form"]
            params = {SLIDERS[k]: form[k] for k in SLIDERS if form.get(k) is not None}
        elif a.name == "poll_feed":
            g = get_gen(load_manifest(album), a.gen)
            if not g.get("clip_ids"):
                die(f"{a.gen} chưa có clip id (chạy submitted trước)")
            params = {"ids": g["clip_ids"], "timeout_s": 240}
        elif a.name == "find_recent":
            g = get_gen(load_manifest(album), a.gen)
            params = {"title": g["title"], "since": g.get("form_ok_at") or g["prepared_at"]}
        elif a.name == "usesuno_download":
            c = find_clip_in_gens(load_manifest(album), a.clip)
            dur = c["duration"]
            params = {"url": f"https://suno.com/song/{c['id']}", "expect": sorted({mmss(dur), mmss(dur + 0.5)})}
        else:
            die(f"{a.name} cần tham số nhưng chưa được hỗ trợ")
        src = src.replace("/*PARAMS*/null", json.dumps(params, ensure_ascii=False))
    print(src)


def find_clip_in_gens(man: dict, clip: str) -> dict:
    for g in man["generations"]:
        for c in g.get("feed", []):
            if c["id"].startswith(clip):
                return {**c, "gen": g["id"]}
    die(f"Không thấy clip '{clip}' trong feed của lượt nào (chạy complete trước)")


def compare_form(spec: dict, f: dict) -> list[tuple[str, bool, str]]:
    s = spec["form"]
    rows = []
    add = lambda k, ok, d="": rows.append((k, bool(ok), d))
    if s.get("cover"):
        src = spec.get("cover_source_clip")
        add("cover_source_clip", bool(src), "đã ghi bằng `cover-source`" if src else "chưa có: `suno_gen.py cover-source <album> <gen> --clip <id>`")
        cov = f.get("cover_of")
        add("cover_mode", bool(cov), f"form {cov!r}" if cov else "form không hiện chế độ Cover (read_form.js `cover_of` = null): mở Cover từ ⋯ → Remix → Cover của clip nguồn")
    mode_on = [m["text"] for m in f.get("mode_buttons") or [] if m.get("on") or m.get("selected") == "true"]
    if mode_on:
        add("mode", "Simple" not in mode_on, f"đang bật: {mode_on}")
    add("model", f.get("model") == s["model"], f"form {f.get('model')!r} · spec {s['model']!r}")
    want_v = s["voice"]["name"] if s.get("voice") else None
    add("voice", (f.get("voice") or None) == want_v, f"form {f.get('voice')!r} · spec {want_v!r}")
    fl, sl = lyric_lines(f.get("lyrics")), lyric_lines(s["lyrics"])
    if fl == sl:
        add("lyrics", True, f"{len(sl)} dòng khớp")
    else:
        i = next((k for k in range(max(len(fl), len(sl))) if k >= len(fl) or k >= len(sl) or fl[k] != sl[k]), 0)
        add("lyrics", False, f"lệch từ dòng {i + 1}: form {fl[i] if i < len(fl) else '<hết>'!r} · spec {sl[i] if i < len(sl) else '<hết>'!r}"
            f" ({len(fl)} vs {len(sl)} dòng)")
    if f.get("style_candidates", 1) > 1 and f.get("style") is None:
        add("style", False, f"có {f['style_candidates']} textarea, không xác định được ô Style")
    else:
        ok = norm(f.get("style")) == s["style"]
        add("style", ok, f"{len(norm(f.get('style')))} ký tự" + ("" if ok else " — khác spec (chọn Voice sẽ ghi đè Style: điền lại Style SAU khi chọn Voice)"))
    if f.get("style_counter"):
        n_ = int(f["style_counter"].split("/")[0])
        add("style_counter", n_ == len(f.get("style") or ""), f"bộ đếm {f['style_counter']} · textarea {len(f.get('style') or '')} ký tự"
            + ("" if n_ == len(f.get("style") or "") else " — React chưa nhận Style: đặt lại bằng native setter + input event"))
    add("exclude", norm(f.get("exclude")) == s["exclude"], "" if norm(f.get("exclude")) == s["exclude"] else f"form {f.get('exclude')!r}")
    add("title", (f.get("title") or "").strip() == s["title"], f"form {f.get('title')!r}")
    g = f.get("vocal_gender")
    want_g = [s["vocal_gender"].capitalize()] if s.get("vocal_gender") else []
    add("vocal_gender", g == want_g, f"form {g} · spec {want_g}")
    add("max_mode", f.get("max_mode") == (["On"] if s["max_mode"] else ["Off"]), f"form {f.get('max_mode')}")
    add("personalize", f.get("personalize") == ["Off"], f"form {f.get('personalize')}")
    want_d = "Auto" if s["duration"] == "auto" else s["duration"]["mmss"]
    add("duration", (f.get("duration") or "") == want_d, f"form {f.get('duration')!r} · spec {want_d!r}")
    sliders = f.get("sliders") or {}
    for k, label in SLIDERS.items():
        want = s.get(k)
        if want is None:
            continue
        add(k, sliders.get(label) == want, f"form {sliders.get(label)} · spec {want}")
    return rows


def cmd_check_form(a):
    album = album_dir(a.album)
    spec = load_spec(album, a.gen)
    f = load_json_loose(Path(a.form))
    rows = compare_form(spec, f)
    bad = [r for r in rows if not r[1]]
    print("| field | | chi tiết |\n|---|---|---|")
    for k, ok, d in rows:
        print(f"| {k} | {'✔' if ok else '✖'} | {d} |")
    if f.get("credits") is not None:
        print(f"\ncredits trên trang: {f['credits']}")
    man = load_manifest(album)
    g = get_gen(man, a.gen)
    g["form_check"] = {"at": now(), "ok": not bad, "failed": [r[0] for r in bad]}
    if not bad:
        g["form_ok_at"] = now()
    save_manifest(album, man)
    if bad:
        die(f"{len(bad)} field sai → sửa trên form rồi đọc lại (read_form) trước khi bấm Create", 1)
    print("\n✔ FORM KHỚP SPEC — được bấm Create (click chuột thật vào button[aria-label=\"Create song\"])")


def dig(obj, key):
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            r = dig(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = dig(v, key)
            if r is not None:
                return r
    return None


def compare_request(spec: dict, req: dict) -> tuple[list, list]:
    s = spec["form"]
    bad, unk = [], []
    chk = lambda name, ok, d: None if ok else bad.append(f"{name}: {d}")
    tags, prompt = dig(req, "tags"), dig(req, "prompt")
    chk("style(tags)", norm(tags) == s["style"], f"request {norm(tags)[:80]!r}…")
    chk("lyrics(prompt)", lyric_lines(prompt) == lyric_lines(s["lyrics"]), "lyrics gửi đi khác spec")
    chk("title", (dig(req, "title") or "").strip() == s["title"], repr(dig(req, "title")))
    neg = dig(req, "negative_tags")
    chk("exclude(negative_tags)", norm(neg) == s["exclude"], repr(neg))
    mv = dig(req, "mv")
    chk("model(mv)", mv == MODELS[s["model"]], f"request {mv!r} · cần {MODELS[s['model']]!r}")
    pid = dig(req, "persona_id")
    chk("voice(persona_id)", (pid or None) == (s["voice"]["id"] if s.get("voice") else None), repr(pid))
    mx = dig(req, "is_max_mode")
    if mx is None:
        unk.append("is_max_mode không có trong request")
    else:
        chk("max_mode", bool(mx) == s["max_mode"], repr(mx))
    for k, keys in REQ_SLIDER_KEYS.items():
        want = s.get(k)
        if want is None:
            continue
        got = next((dig(req, kk) for kk in keys if dig(req, kk) is not None), None)
        if got is None:
            if want != SUNO_DEFAULTS[k]:
                unk.append(f"{k} không có trong request (spec {want})")
            continue
        ok = abs(got - want) < 0.01 or abs(got - want / 100) < 0.011
        chk(k, ok, f"request {got} · spec {want}")
    if s.get("cover"):
        src = spec.get("cover_source_clip")
        vals = [str(v) for _, v in walk(req)]
        if src and not any(src in v for v in vals):
            bad.append(f"cover: clip nguồn {src} không có trong request (Suno đang tạo bài thường, không phải Cover)")
        keys = [k for k, _ in walk(req) if "cover" in k.lower()]
        unk.append(f"cover: khóa request có chữ 'cover': {keys or 'không có'} (ghi vào references/suno-research.md sau lần chạy đầu)")
    if s["duration"] != "auto":
        dur = next((v for kk, v in walk(req) if "duration" in kk.lower() and isinstance(v, (int, float))), None)
        if dur is None:
            unk.append("không thấy trường duration trong request")
        else:
            chk("duration", abs(dur - s["duration"]["seconds"]) <= 1, f"request {dur}")
    return bad, unk


def walk(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield (prefix + k, v)
            yield from walk(v, prefix + k + ".")
    elif isinstance(obj, list):
        for v in obj:
            yield from walk(v, prefix)


def clip_ids_from_response(resp) -> list[str]:
    clips = resp.get("clips") if isinstance(resp, dict) else None
    if not clips:
        clips = [v for _, v in walk(resp) if isinstance(v, dict) and "id" in v and "status" in v]
    ids = []
    for c in clips or []:
        if isinstance(c, dict) and re.fullmatch(r"[0-9a-f-]{36}", str(c.get("id", ""))) and c["id"] not in ids:
            ids.append(c["id"])
    return ids


def cmd_submitted(a):
    album = album_dir(a.album)
    spec = load_spec(album, a.gen)
    man = load_manifest(album)
    g = get_gen(man, a.gen)
    if g["status"] != "prepared":
        die(f"{a.gen} đang ở trạng thái {g['status']}, không phải prepared")
    ids = [x.strip() for x in a.clips.split(",")] if a.clips else []
    if a.response:
        ids = ids or clip_ids_from_response(load_json_loose(Path(a.response)))
        g["response_file"] = arel(album, Path(a.response))
    if not ids:
        die("Không lấy được clip id: truyền --response (body của POST /api/generate/v2-web/) hoặc --clips, "
            "hoặc chạy `js find_recent` để tìm theo title")
    bad, unk = [], []
    if a.request:
        req = load_json_loose(Path(a.request))
        bad, unk = compare_request(spec, req)
        g["request_file"] = arel(album, Path(a.request))
        g["request_keys"] = sorted({k for k, _ in walk(req)})[:80]
    g.update(status="submitted", submitted_at=now(), clip_ids=ids,
             credits_before=a.credits_before, request_check={"mismatch": bad, "unverified": unk,
                                                             "checked": bool(a.request)})
    save_manifest(album, man)
    print(f"✔ {a.gen}: {len(ids)} clip → {', '.join(i[:8] for i in ids)}")
    for u in unk:
        print(f"  ? chưa kiểm được: {u}")
    if not a.request:
        print("  ? không có request body → chỉ còn kiểm bằng feed (complete)")
    if bad:
        print("\n✖ REQUEST KHÁC SPEC (credits đã tốn):\n  " + "\n  ".join(bad))
        print("→ Dừng. Báo người dùng; đừng tải/verify các clip này như bản hợp lệ trước khi họ quyết định.")
        sys.exit(2)


def compare_feed(spec: dict, c: dict) -> list[str]:
    s = spec["form"]
    bad = []
    if s["variety"] == 0 and norm(c.get("tags")) != s["style"]:
        bad.append(f"style (tags) bị đổi: {norm(c.get('tags'))[:90]!r}…")
    if norm(c.get("negative_tags")) != s["exclude"]:
        bad.append(f"exclude: {c.get('negative_tags')!r}")
    if c.get("prompt") is not None and lyric_lines(c["prompt"]) != lyric_lines(s["lyrics"]):
        bad.append("lyrics (prompt) khác spec")
    want_p = s["voice"]["name"] if s.get("voice") else None
    got_p = (c.get("persona") or {}).get("name")
    if got_p != want_p:
        bad.append(f"voice: {got_p!r} · spec {want_p!r}")
    if c.get("is_max_mode") is not None and bool(c["is_max_mode"]) != s["max_mode"]:
        bad.append(f"max_mode: {c['is_max_mode']}")
    if c.get("model_name") and c["model_name"] != MODELS[s["model"]]:
        bad.append(f"model: {c['model_name']}")
    return bad


def cmd_complete(a):
    album = album_dir(a.album)
    spec = load_spec(album, a.gen)
    man = load_manifest(album)
    g = get_gen(man, a.gen)
    if g["status"] not in ("submitted", "complete"):
        die(f"{a.gen} đang ở trạng thái {g['status']}")
    feed = load_json_loose(Path(a.feed))
    clips = feed.get("clips", feed) if isinstance(feed, dict) else feed
    by_id = {c["id"]: c for c in clips}
    missing = [i for i in g["clip_ids"] if i not in by_id]
    if missing:
        die(f"feed thiếu clip {', '.join(m[:8] for m in missing)}")
    notdone = [i[:8] + ":" + by_id[i]["status"] for i in g["clip_ids"] if by_id[i]["status"] != "complete"]
    errs = [i for i in g["clip_ids"] if by_id[i]["status"] == "error"]
    if notdone and not errs:
        die(f"chưa xong: {', '.join(notdone)} → chạy lại poll_feed")
    report, anybad = [], False
    keep = []
    for i in g["clip_ids"]:
        c = by_id[i]
        bad = compare_feed(spec, c) if c["status"] == "complete" else [f"Suno báo lỗi: {c.get('error')}"]
        anybad |= bool(bad)
        d = spec["form"]["duration"]
        warn = []
        if c.get("duration") and d != "auto" and abs(c["duration"] - d["seconds"]) > 30:
            warn.append(f"dài {mmss(c['duration'])}, đặt {d['mmss']}")
        keep.append({k: c.get(k) for k in ("id", "title", "status", "duration", "created_at", "model_name", "tags",
                                           "negative_tags", "is_max_mode", "control_sliders", "persona")}
                    | {"feed_mismatch": bad, "warn": warn})
        report.append(f"  {i[:8]} {c['status']} {mmss(c['duration']) if c.get('duration') else '?'} "
                      + ("✔" if not bad else "✖ " + "; ".join(bad)) + (f" ⚠ {'; '.join(warn)}" if warn else ""))
    g.update(feed=keep, completed_at=now(), status="complete" if not errs else "failed")
    if a.credits_after is not None:
        g["credits_after"] = a.credits_after
        if g.get("credits_before") is not None:
            g["credits"] = g["credits_before"] - a.credits_after
    save_manifest(album, man)
    print(f"{a.gen}:\n" + "\n".join(report))
    if g.get("credits") is not None:
        exp = spec["expect"]["credits"]
        print(f"credits: {g['credits_before']} → {a.credits_after} = {g['credits']}" + ("" if g["credits"] == exp else f" ⚠ dự kiến {exp}"))
    if errs:
        die("Suno báo lỗi clip → lượt này failed; generate lại cùng spec (next --purpose regenerate --reason 'suno error')", 2)
    if anybad:
        print("\n✖ Settings Suno ghi nhận khác spec → báo người dùng trước khi tải/verify.")
        sys.exit(2)
    print(f"\n✔ Tải từng clip: suno_gen.py js usesuno_download --album {album.name} --clip <id8> → ingest")


def cmd_ingest(a):
    album = album_dir(a.album)
    man = load_manifest(album)
    info = find_clip_in_gens(man, a.clip)
    cid, g = info["id"], get_gen(man, info["gen"])
    spec = load_spec(album, g["id"])
    if any(c.get("clip_id") == cid for c in man["clips"]):
        die(f"clip {cid[:8]} đã có trong manifest")
    if a.file:
        src = Path(a.file).expanduser()
    else:
        deadline = time.time() + a.wait
        while True:
            partial = list(DOWNLOADS.glob("*.crdownload"))
            cands = [p for p in DOWNLOADS.glob("*usesuno.com*") if p.suffix.lower() in (".wav", ".mp3", ".m4a")
                     and time.time() - p.stat().st_mtime < a.since * 60]
            match = [p for p in cands if abs(audio_duration(p) - info["duration"]) <= 0.6]
            if match and not partial:
                break
            if time.time() > deadline:
                die(f"Không thấy file usesuno trong {DOWNLOADS} (≤ {a.since} phút) dài {info['duration']:.2f}s. "
                    f"Có: {[p.name for p in cands]}; đang tải dở: {[p.name for p in partial]}")
            time.sleep(2)
        if len(match) > 1:
            die(f"Nhiều file khớp thời lượng: {[p.name for p in match]} → chỉ rõ --file")
        src = match[0]
    dur = audio_duration(src)
    if abs(dur - info["duration"]) > 0.6:
        die(f"{src.name} dài {dur:.2f}s nhưng clip {cid[:8]} dài {info['duration']:.2f}s → sai file, KHÔNG ghi")
    dst = manifest_path(album).parent / f"{slugify(g['title'])} {cid[:8]}{src.suffix.lower()}"
    if dst.exists():
        die(f"{rel(dst)} đã tồn tại")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), dst)
    f = spec["form"]
    man["clips"].append({
        "file": dst.name, "clip_id": cid, "suno_url": f"https://suno.com/song/{cid}", "title": g["title"],
        "slot": g["slot"], "round": g["round"], "generation": g["id"], "purpose": g["purpose"], "reason": g.get("reason"),
        "variant": g.get("variant"), "duration": round(dur, 2), "created_at": (info.get("created_at") or now())[:10],
        "source": "usesuno",
        "settings": {"model": f["model"], "voice": f["voice"]["name"] if f.get("voice") else None,
                     "style_version": spec.get("style_version"), "bpm": spec.get("prompt_bpm"), "lyrics_file": spec.get("lyrics_file"),
                     "lyrics_sha8": hashlib.sha256((f["lyrics"] or "").encode()).hexdigest()[:8],
                     "max_mode": f["max_mode"], "vocal_gender": f["vocal_gender"],
                     "duration": f["duration"] if f["duration"] == "auto" else f["duration"]["seconds"],
                     "variety": f["variety"], "weirdness": f["weirdness"], "style_influence": f["style_influence"],
                     "audio_influence": f["audio_influence"], "spec": g["spec"]},
        "checks": {"form": (g.get("form_check") or {}).get("ok"),
                   "request": not (g.get("request_check") or {}).get("mismatch") if (g.get("request_check") or {}).get("checked") else None,
                   "feed": not info.get("feed_mismatch")},
        "sha256": sha256(dst), "downloaded_at": now(), "status": "draft",
    })
    got = {c["clip_id"] for c in man["clips"]}
    if all(x["id"] in got for x in g.get("feed", []) if x["status"] == "complete"):
        g["status"] = "downloaded"
    save_manifest(album, man)
    print(f"✔ {src.name} → {rel(dst)} ({mmss(dur)}, khớp clip {cid[:8]})")
    if g["status"] == "downloaded":
        print(f"✔ {g['id']} đã tải đủ → chạy skill verification-audio cho slot {g['slot']} ({rel(album)})")


def cmd_cover_source(a):
    album = album_dir(a.album)
    sp = spec_path(album, a.gen)
    spec = load_spec(album, a.gen)
    if not (spec.get("form") or {}).get("cover"):
        die(f"{a.gen} không phải lượt Cover (slot không có cover trong generation.yaml)")
    man = load_manifest(album)
    g = get_gen(man, a.gen)
    if g["status"] != "prepared":
        die(f"{a.gen} đang ở trạng thái {g['status']}: chỉ ghi nguồn trước khi Create")
    spec["cover_source_clip"] = a.clip
    sp.write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n")
    g["cover"] = {**spec["form"]["cover"], "source_clip": a.clip, "recorded_at": now()}
    save_manifest(album, man)
    print(f"✔ {a.gen}: nguồn Cover = clip {a.clip} ({spec['form']['cover']['kind']}); tiếp: ⋯ → Remix → Cover, điền form, check-form")


def cmd_quota(a):
    album = album_dir(a.album)
    man = load_manifest(album)
    prev = man["quota_log"][-1] if man["quota_log"] else None
    alert = bool(prev and a.downloads_used > prev["downloads_used"])
    man["quota_log"].append({"at": now(), "credits": a.credits, "downloads_used": a.downloads_used, "context": a.context}
                            | ({"alert": f"downloads {prev['downloads_used']} → {a.downloads_used}"} if alert else {}))
    save_manifest(album, man)
    print(f"credits {a.credits} · downloads chính thức {a.downloads_used}")
    if alert:
        die(f"QUOTA TẢI CHÍNH THỨC TĂNG {prev['downloads_used']} → {a.downloads_used} (từ '{prev['context']}'). "
            "DỪNG NGAY và báo người dùng — skill không bao giờ được dùng Download của Suno.", 3)
    if prev:
        print(f"  so với lần trước ({prev['context']}): credits {prev['credits']} → {a.credits}, downloads không đổi ✔")


def main():
    ap = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("validate"); p.add_argument("album"); p.set_defaults(fn=cmd_validate)
    p = sub.add_parser("status"); p.add_argument("album"); p.set_defaults(fn=cmd_status)
    p = sub.add_parser("next"); p.add_argument("album"); p.add_argument("--slot", type=int)
    p.add_argument("--purpose", choices=["planned", "more", "regenerate", "variant", "test"])
    p.add_argument("--reason"); p.add_argument("--variant")
    p.add_argument("--force", action="store_true", help="bỏ qua gate anchor_first / slot đã chọn / lượt dở")
    p.add_argument("--allow-over-budget", action="store_true")
    p.add_argument("--accept-lyrics-change", action="store_true",
                   help="lyrics khác bản album-plan đã duyệt (chỉ khi REGENERATE có sửa lời, người dùng đã đồng ý)")
    p.set_defaults(fn=cmd_next)
    p = sub.add_parser("js"); p.add_argument("name"); p.add_argument("--album"); p.add_argument("--gen"); p.add_argument("--clip")
    p.set_defaults(fn=cmd_js)
    p = sub.add_parser("check-form"); p.add_argument("album"); p.add_argument("gen"); p.add_argument("form"); p.set_defaults(fn=cmd_check_form)
    p = sub.add_parser("submitted"); p.add_argument("album"); p.add_argument("gen")
    p.add_argument("--request"); p.add_argument("--response"); p.add_argument("--clips")
    p.add_argument("--credits-before", type=int); p.set_defaults(fn=cmd_submitted)
    p = sub.add_parser("complete"); p.add_argument("album"); p.add_argument("gen"); p.add_argument("feed")
    p.add_argument("--credits-after", type=int); p.set_defaults(fn=cmd_complete)
    p = sub.add_parser("ingest"); p.add_argument("album"); p.add_argument("--clip", required=True); p.add_argument("--file")
    p.add_argument("--since", type=float, default=30, help="chỉ xét file trong ~/Downloads mới hơn N phút")
    p.add_argument("--wait", type=float, default=90, help="chờ file tải xong tối đa N giây"); p.set_defaults(fn=cmd_ingest)
    p = sub.add_parser("cover-source"); p.add_argument("album"); p.add_argument("gen"); p.add_argument("--clip", required=True)
    p.set_defaults(fn=cmd_cover_source)
    p = sub.add_parser("quota"); p.add_argument("album"); p.add_argument("--credits", type=int, required=True)
    p.add_argument("--downloads-used", type=int, required=True); p.add_argument("--context", default="")
    p.set_defaults(fn=cmd_quota)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

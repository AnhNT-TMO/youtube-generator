from __future__ import annotations
USAGE = """Sổ sách + kiểm tra cho skill `audio-suno-generate` (Suno Simple mode qua Chrome DevTools MCP, tải qua usesuno).

Claude thao tác trên browser; script lo phần phải CHÍNH XÁC: prompt của từng lượt (lấy nguyên văn từ
channel/<ch>/prompt_suno.md), đối chiếu form / request / feed với prompt đó, nhận file tải về, và ghi
channel/<ch>/songs/manifest.json + songs/raw/<id8>.{wav,json,lyrics.txt}.

    SK=.claude/skills/audio-suno-generate; P() { $SK/.venv/bin/python $SK/scripts/suno_gen.py "$@"; }
    P status     --channel CH                     # prompt_suno.md hợp lệ?, số lượt theo type, việc đang chờ
    P next       --channel CH --type T            # mở lượt mới gNNN (prepared) với prompt của type T
    P js NAME    --channel CH [--gen G | --clip ID8]   # in JS (scripts/js/NAME.js) đã điền tham số
    P check-form --channel CH [G] [--form F]      # form == spec? (TRƯỚC khi bấm Create)
    P submitted  --channel CH [G] --credits-before N [--request F --response F | --clips id1,id2]
    P complete   --channel CH [G] --credits-after N [--feed F]
    P ingest     --channel CH --clip ID8 [--file F] [--downloads DIR] [--pm-ok "..."]
    P quota      --channel CH --credits N --downloads-used N --context "..."

--channel: tên kênh (channel/<CH>/) hoặc đường dẫn một thư mục kênh có prompt_suno.md (dùng để thử trong scratchpad).
G bỏ trống = lượt duy nhất đang ở đúng trạng thái. File bằng chứng mặc định: songs/raw/gen/<G>.{form,request,response,feed}.json
Exit: 1 lỗi dùng lệnh · 2 Suno nhận/lưu khác spec · 3 quota tải chính thức tăng · 4 BLOCKED (prompt_suno.md/model không dùng được).
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
MENU_SEEN = "2026-09-28: v6 [Pro] · v6-wild [Pro] · v6-mini"
MODELS = {"v6": {"mv": "chirp-hawk", "credits": 10},
          "v6-wild": {"mv": "chirp-hawk-wild", "credits": None},
          "v6-mini": {"mv": "chirp-goose", "credits": 10}}
REQ_PROMPT_KEY = "gpt_description_prompt"
DURATION_TOL = 0.6
NEXT_STEP = {"prepared": "tab Simple → model → js fill_prompt → read_form → check-form → Create → submitted",
             "submitted": "js poll_feed → complete",
             "complete": "usesuno_download → ingest từng clip còn thiếu",
             "failed": "Suno báo lỗi clip → báo PM"}


def die(msg: str, code: int = 1):
    sys.stdout.flush()
    print(f"✖ {msg}", file=sys.stderr)
    sys.exit(code)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def mmss(sec: float) -> str:
    return f"{int(sec) // 60}:{int(sec) % 60:02d}"


def voice_label(v: dict | None) -> str:
    if isinstance(v, dict):
        return f"{v.get('name')!r} ({str(v.get('id'))[:8]})"
    return "không" if v is None else repr(v)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def audio_duration(p: Path) -> float:
    try:
        with wave.open(str(p)) as w:
            return w.getnframes() / w.getframerate()
    except wave.Error:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                             capture_output=True, text=True, check=True)
        return float(out.stdout.strip())


def load_json_loose(path: Path):
    path = Path(path)
    if not path.exists():
        die(f"Không có {rel(path)}")
    txt = path.read_text()
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        m = re.search(r"```(?:json)?\s*(.*?)```", txt, re.S) or re.search(r"([\[{].*[\]}])", txt, re.S)
        if not m:
            die(f"{rel(path)}: không đọc được JSON")
        return json.loads(m.group(1))


def prompt_diff(got: str | None, want: str) -> str:
    if got is None:
        return "không đọc được prompt"
    if got == want:
        return f"{len(want)} ký tự, khớp từng byte"
    i = next((k for k in range(min(len(got), len(want))) if got[k] != want[k]), min(len(got), len(want)))
    cut = " — BỊ CẮT" if want.startswith(got) else ""
    return f"lệch từ ký tự {i + 1}{cut}: {got[i:i + 30]!r} · spec {want[i:i + 30]!r} ({len(got)} vs {len(want)} ký tự)"


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


def walk(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield prefix + k, v
            yield from walk(v, prefix + k + ".")
    elif isinstance(obj, list):
        for v in obj:
            yield from walk(v, prefix)


def channel_dir(arg: str) -> Path:
    p = Path(arg).expanduser()
    if p.is_dir() and (p / "prompt_suno.md").exists():
        return p.resolve()
    d = ROOT / "channel" / arg
    if d.is_dir():
        return d
    die(f"Không có kênh '{arg}' (channel/<ch>/ hoặc thư mục kênh có prompt_suno.md)")


class Pool:
    def __init__(self, arg: str):
        self.dir = channel_dir(arg)
        self.name = self.dir.name
        self.songs = self.dir / "songs"
        self.raw = self.songs / "raw"
        self.gen_dir = self.raw / "gen"
        self.file = self.songs / "manifest.json"
        self.man = json.loads(self.file.read_text()) if self.file.exists() else {}
        self.man.setdefault("channel", self.name)
        self.man.setdefault("note", "Kho clip Suno của kênh (Simple mode). Chỉ skill audio-suno-generate ghi file này. "
                                    "Chỉ tải qua usesuno, không bao giờ dùng Download của Suno.")
        for k in ("generations", "clips", "quota_log"):
            self.man.setdefault(k, [])

    @property
    def gens(self) -> list[dict]:
        return self.man["generations"]

    def save(self):
        self.songs.mkdir(parents=True, exist_ok=True)
        tmp = self.file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.man, indent=1, ensure_ascii=False) + "\n")
        tmp.replace(self.file)

    def evidence(self, gid: str, kind: str) -> Path:
        return self.gen_dir / f"{gid}.{kind}.json"

    def pick(self, gid: str | None, states: tuple) -> dict:
        if gid:
            g = next((g for g in self.gens if g["id"] == gid), None)
            if g is None:
                die(f"Không có lượt '{gid}' trong manifest")
            if g["status"] not in states:
                die(f"{gid} đang ở trạng thái {g['status']}, cần {' | '.join(states)}")
            return g
        hits = [g for g in self.gens if g["status"] in states]
        if len(hits) != 1:
            die(f"{len(hits)} lượt ở trạng thái {' | '.join(states)}"
                + (f": {', '.join(g['id'] for g in hits)} → ghi rõ gen" if hits else ""))
        return hits[0]

    def feed_clip(self, clip: str) -> tuple[dict, dict]:
        for g in self.gens:
            for c in g.get("feed", []):
                if c["id"].startswith(clip):
                    return g, c
        die(f"Không thấy clip '{clip}' trong feed của lượt nào (chạy complete trước)")

    def downloaded(self) -> set[str]:
        return {c["clip_id"] for c in self.man["clips"]}


def load_prompts(pool: Pool) -> dict:
    f = pool.dir / "prompt_suno.md"
    cfg = {"file": f, "errors": [], "prompts": {}}
    if not f.exists():
        cfg["errors"].append(f"không có {rel(f)}")
        return cfg
    m = re.match(r"---\n(.*?)\n---\n(.*)", f.read_text(), re.S)
    if not m:
        cfg["errors"].append(f"{rel(f)} thiếu front matter")
        return cfg
    fm = yaml.safe_load(m.group(1)) or {}
    errs = cfg["errors"]
    cfg.update(mode=fm.get("mode"), model=fm.get("model"), clips=fm.get("clips_per_generation"),
               download=fm.get("download"), types=fm.get("types") or [], voice=fm.get("voice"))
    if cfg["mode"] != "simple":
        errs.append(f"mode {cfg['mode']!r}: skill chỉ làm Simple mode")
    if cfg["download"] != "all":
        errs.append(f"download {cfg['download']!r}: skill chỉ hỗ trợ 'all' (tải mọi clip của lượt)")
    if cfg["model"] not in MODELS:
        errs.append(f"model {cfg['model']!r} không có trong menu model của Suno (thấy {MENU_SEEN}) "
                    "→ DỪNG, báo PM: CEO/PM chọn model rồi sửa prompt_suno.md")
    v = cfg["voice"]
    if v is not None and not (isinstance(v, dict) and isinstance(v.get("name"), str) and v["name"].strip()
                              and re.fullmatch(r"[0-9a-f-]{36}", str(v.get("id", "")))):
        errs.append(f"voice {v!r}: cần {{name: <tên Voice trên Suno>, id: <uuid của Voice>}} hoặc bỏ hẳn (không Voice)")
    elif v is not None:
        cfg["voice"] = {"name": v["name"], "id": str(v["id"])}
    if not isinstance(cfg["clips"], int) or isinstance(cfg["clips"], bool) or cfg["clips"] < 1:
        errs.append(f"clips_per_generation {cfg['clips']!r} phải là số nguyên ≥ 1")
    sections = {s.group(1).strip(): s.group(2)
                for s in re.finditer(r"^## +(.+?)[ \t]*$(.*?)(?=^## |\Z)", m.group(2), re.S | re.M)}
    if not cfg["types"]:
        errs.append("types trống")
    for t in cfg["types"]:
        blocks = re.findall(r"^```text\n(.*?)\n```[ \t]*$", sections.get(t, ""), re.S | re.M)
        if len(blocks) != 1:
            errs.append(f"## {t}: cần đúng 1 khối ```text (thấy {len(blocks)})")
            continue
        p = blocks[0]
        if not p.strip():
            errs.append(f"## {t}: prompt trống")
        elif re.search(r"[À-ỹđĐ]", p):
            errs.append(f"## {t}: prompt có ký tự không phải tiếng Anh (text nhập vào Suno phải là tiếng Anh)")
        cfg["prompts"][t] = p
    return cfg


def cfg_or_block(pool: Pool) -> dict:
    cfg = load_prompts(pool)
    if cfg["errors"]:
        die(f"BLOCKED — {rel(cfg['file'])}:\n  " + "\n  ".join(cfg["errors"]), 4)
    return cfg


def cmd_status(a):
    pool = Pool(a.channel)
    cfg = load_prompts(pool)
    print(f"# {pool.name} — kho clip Suno ({rel(pool.songs)})\n")
    types = ", ".join(f"{t} {len(p)} ký tự" for t, p in cfg["prompts"].items())
    print(f"prompt_suno.md: mode {cfg.get('mode')} · model {cfg.get('model')} · Voice {voice_label(cfg.get('voice'))} · "
          f"{cfg.get('clips')} clip/lượt · {types}")
    for e in cfg["errors"]:
        print(f"  ✖ BLOCKED: {e}")
    got = pool.downloaded()
    today = now()[:10]
    print("\n| type | lượt xong | hôm nay | lỗi | clip đã tải | chờ tải |\n|---|---|---|---|---|---|")
    for t in sorted({*cfg.get("types", []), *(g["type"] for g in pool.gens)}):
        gs = [g for g in pool.gens if g["type"] == t]
        done = [g for g in gs if g["status"] in ("complete", "downloaded")]
        waiting = sum(1 for g in done for c in g.get("feed", []) if c["status"] == "complete" and c["id"] not in got)
        print(f"| {t} | {len(done)} | {sum(1 for g in done if (g.get('completed_at') or '')[:10] == today)} | "
              f"{sum(1 for g in gs if g['status'] == 'failed')} | {sum(1 for c in pool.man['clips'] if c['type'] == t)} | "
              f"{waiting or ''} |")
    measured = [g["credits"] for g in pool.gens if g.get("credits") is not None]
    print(f"\ncredits đã dùng (đo được): {sum(measured)} qua {len(measured)} lượt")
    for q in pool.man["quota_log"]:
        if q.get("alert"):
            print(f"🚨 quota tải chính thức từng TĂNG: {q['alert']} ({q['at']}, {q['context']})")
    if pool.man["quota_log"]:
        q = pool.man["quota_log"][-1]
        print(f"lần đọc tài khoản gần nhất: {q['at']} · credits {q['credits']} · downloads chính thức {q['downloads_used']}")
    on_disk = sorted(p.stem for p in pool.raw.glob("*.wav")) if pool.raw.exists() else []
    known = {c["id8"] for c in pool.man["clips"]}
    print(f"raw/ chưa đặt tên: {len(on_disk)} file .wav")
    stray = [s for s in on_disk if s not in known]
    if stray:
        print(f"  ⚠ có trong raw/ nhưng không có trong manifest: {', '.join(stray)}")
    opn = [g for g in pool.gens if g["status"] in NEXT_STEP]
    if opn:
        print("\n## Đang chờ (làm tiếp từ đây)")
        for g in opn:
            left = [c["id"][:8] for c in g.get("feed", []) if c["status"] == "complete" and c["id"] not in got]
            print(f"- `{g['id']}` {g['type']} · {g['status']} → {NEXT_STEP[g['status']]}"
                  + (f" · chờ tải: {', '.join(left)}" if left else ""))
    else:
        print("\nKhông có lượt nào đang dở.")


def cmd_next(a):
    pool = Pool(a.channel)
    cfg = cfg_or_block(pool)
    if a.type not in cfg["prompts"]:
        die(f"type '{a.type}' không có trong prompt_suno.md (có: {', '.join(cfg['prompts'])})")
    busy = [g["id"] for g in pool.gens if g["status"] == "submitted"]
    if busy:
        die(f"Còn lượt đã Create chưa complete: {', '.join(busy)} → poll_feed + complete trước (mỗi lần một lượt)")
    prepared = next((g for g in pool.gens if g["status"] == "prepared"), None)
    gid = prepared["id"] if prepared else f"g{max([int(g['id'][1:]) for g in pool.gens] or [0]) + 1:03d}"
    prompt, model = cfg["prompts"][a.type], cfg["model"]
    entry = {"id": gid, "type": a.type, "model": model, "mv": MODELS[model]["mv"], "voice": cfg["voice"], "prompt": prompt,
             "prompt_sha8": sha(prompt.encode())[:8], "prompt_file": rel(cfg["file"]),
             "expect": {"clips": cfg["clips"], "credits": MODELS[model]["credits"]},
             "status": "prepared", "prepared_at": now(), "clip_ids": []}
    if prepared:
        prepared.clear()
        prepared.update(entry)
    else:
        pool.gens.append(entry)
    pool.gen_dir.mkdir(parents=True, exist_ok=True)
    pool.save()
    exp = MODELS[model]["credits"]
    print(f"GEN={gid}\n{gid} · type {a.type} · model {model} · Voice {voice_label(cfg['voice'])} · "
          f"prompt {len(prompt)} ký tự (sha8 {entry['prompt_sha8']}) · "
          f"{cfg['clips']} clip · credits dự kiến {exp if exp is not None else 'chưa đo'}")
    print(f"Bằng chứng: {rel(pool.gen_dir)}/{gid}.{{form,request,response,feed}}.json")
    print(f"Tiếp: {NEXT_STEP['prepared']}")


def cmd_js(a):
    f = JS_DIR / f"{a.name}.js"
    if not f.exists():
        die(f"Không có {rel(f)}. Có: {', '.join(sorted(p.stem for p in JS_DIR.glob('*.js')))}")
    src = f.read_text()
    if "/*PARAMS*/" in src:
        if not a.channel:
            die(f"{a.name} cần --channel")
        pool = Pool(a.channel)
        if a.name == "fill_prompt":
            params = {"prompt": pool.pick(a.gen, ("prepared",))["prompt"]}
        elif a.name == "find_recent":
            g = pool.pick(a.gen, ("prepared", "submitted"))
            params = {"prompt": g["prompt"], "since": g.get("form_ok_at") or g["prepared_at"]}
        elif a.name == "poll_feed":
            g = pool.pick(a.gen, ("submitted", "complete"))
            params = {"ids": g["clip_ids"], "timeout_s": 240}
        elif a.name == "usesuno_download":
            if not a.clip:
                die("usesuno_download cần --clip ID8")
            _, c = pool.feed_clip(a.clip)
            params = {"url": f"https://suno.com/song/{c['id']}",
                      "expect": sorted({mmss(c["duration"]), mmss(c["duration"] + 0.5)})}
        else:
            die(f"{a.name} cần tham số nhưng chưa được hỗ trợ")
        src = src.replace("/*PARAMS*/null", json.dumps(params, ensure_ascii=False))
    print(src)


def compare_form(g: dict, f: dict) -> list[tuple[str, bool, str]]:
    rows = []
    add = lambda k, ok, d: rows.append((k, bool(ok), d))
    sel = [t["text"] for t in f.get("tabs") or [] if t.get("selected")]
    add("mode", sel == ["Simple"], f"tab đang chọn {sel}")
    add("model", f.get("model") == g["model"], f"form {f.get('model')!r} · spec {g['model']!r}")
    add("prompt_boxes", f.get("prompt_boxes") == 1, f"{f.get('prompt_boxes')} ô (Simple có đúng 1)")
    add("prompt", f.get("prompt") == g["prompt"], prompt_diff(f.get("prompt"), g["prompt"]))
    extra = [k for k in ("lyrics_editor", "style_counter") if f.get(k)]
    add("no_lyrics_style", not extra, f"đang hiện {extra}" if extra else "không có ô Lyrics/Style")
    want = (g.get("voice") or {}).get("name")
    add("voice", f.get("voice_name") == want and bool(f.get("voice_selected")) == bool(want),
        f"form {f.get('voice_name') if f.get('voice_selected') else None!r} · spec {want!r}"
        + (" (có Voice nhưng không đọc được tên)" if f.get("voice_selected") and not f.get("voice_name") else ""))
    others = [r for r in f.get("remove_buttons") or [] if r not in ("Remove selected Voice", f"Remove {want}")]
    add("attachments", not others, f"{others}" if others else "không đính kèm audio/ảnh")
    add("create_button", f.get("create_enabled") is True, "bấm được" if f.get("create_enabled") else "không thấy / bị khóa")
    return rows


def cmd_check_form(a):
    pool = Pool(a.channel)
    g = pool.pick(a.gen, ("prepared",))
    f = load_json_loose(Path(a.form) if a.form else pool.evidence(g["id"], "form"))
    rows = compare_form(g, f)
    bad = [k for k, ok, _ in rows if not ok]
    print("| field | | chi tiết |\n|---|---|---|")
    for k, ok, d in rows:
        print(f"| {k} | {'✔' if ok else '✖'} | {d} |")
    if f.get("credits") is not None:
        print(f"\ncredits trên trang: {f['credits']}")
    g["form_check"] = {"at": now(), "ok": not bad, "failed": bad}
    if not bad:
        g["form_ok_at"] = now()
    pool.save()
    if bad:
        die(f"{len(bad)} field sai → sửa form, đọc lại (read_form) rồi check-form lại trước khi bấm Create")
    print(f"\n✔ FORM KHỚP SPEC ({g['id']}) — được bấm Create MỘT lần (click chuột thật vào button[aria-label=\"Create song\"])")


def compare_request(g: dict, req) -> tuple[list, list]:
    bad, unk = [], []
    desc = dig(req, REQ_PROMPT_KEY)
    if desc is None:
        where = [k for k, v in walk(req) if v == g["prompt"]]
        if where:
            unk.append(f"prompt nằm ở khóa {where}, không phải {REQ_PROMPT_KEY} → ghim REQ_PROMPT_KEY")
        else:
            bad.append("không thấy prompt trong request (bị cắt hoặc sai khóa)")
    elif desc != g["prompt"]:
        bad.append(f"prompt ({REQ_PROMPT_KEY}): {prompt_diff(desc, g['prompt'])}")
    mv = dig(req, "mv")
    if mv is None:
        unk.append("không có khóa mv (model) trong request")
    elif mv != g["mv"]:
        bad.append(f"model (mv): {mv!r} · cần {g['mv']!r}")
    lyr, tags = dig(req, "prompt"), dig(req, "tags")
    if lyr:
        bad.append("request có lyrics (prompt) → form không ở Simple")
    if tags:
        bad.append("request có Style (tags) → form không ở Simple")
    if lyr is None and tags is None:
        unk.append("không có khóa prompt/tags: chưa rõ khóa nào đánh dấu Simple mode")
    want = (g.get("voice") or {}).get("id")
    pid = dig(req, "persona_id") or None
    where = [k for k, v in walk(req) if want and v == want]
    if pid != want and not (pid is None and where):
        bad.append(f"Voice (persona_id): {pid!r} · cần {want!r}")
    elif want and "persona_id" not in [k.rsplit(".", 1)[-1] for k in where]:
        unk.append(f"id Voice nằm ở khóa {where}, không phải persona_id → ghim khóa này")
    inst = dig(req, "make_instrumental")
    if inst:
        bad.append("make_instrumental = true")
    elif inst is None:
        unk.append("không có khóa make_instrumental")
    return bad, unk


def clip_ids_from_response(resp) -> list[str]:
    clips = resp.get("clips") if isinstance(resp, dict) else None
    if not clips:
        clips = [v for _, v in walk(resp) if isinstance(v, dict) and "id" in v and "status" in v]
    ids = []
    for c in clips or []:
        if isinstance(c, dict) and re.fullmatch(r"[0-9a-f-]{36}", str(c.get("id", ""))) and c["id"] not in ids:
            ids.append(c["id"])
    return ids


def evidence_or(pool: Pool, gid: str, kind: str, given: str | None) -> Path | None:
    if given:
        return Path(given)
    p = pool.evidence(gid, kind)
    return p if p.exists() else None


def cmd_submitted(a):
    pool = Pool(a.channel)
    g = pool.pick(a.gen, ("prepared",))
    if not (g.get("form_check") or {}).get("ok"):
        print("⚠ lượt này chưa có check-form khớp spec: đã bấm Create khi chưa kiểm form — ghi vào báo cáo cho PM")
    ids = [x.strip() for x in a.clips.split(",") if x.strip()] if a.clips else []
    resp = evidence_or(pool, g["id"], "response", a.response)
    if resp and not ids:
        ids = clip_ids_from_response(load_json_loose(resp))
        g["response_file"] = rel(resp)
    if not ids:
        die("Không lấy được clip id: cần body response của POST /api/generate/v2-web/ (--response) hoặc --clips "
            "(tìm bằng `js find_recent`)")
    req = evidence_or(pool, g["id"], "request", a.request)
    bad, unk = [], []
    if req:
        body = load_json_loose(req)
        bad, unk = compare_request(g, body)
        g["request_file"] = rel(req)
        g["request_keys"] = sorted({k for k, _ in walk(body)})[:80]
        g["request_persona_id"] = dig(body, "persona_id")
    g.update(status="submitted", submitted_at=now(), clip_ids=ids, credits_before=a.credits_before,
             request_check={"checked": bool(req), "mismatch": bad, "unverified": unk})
    pool.save()
    print(f"✔ {g['id']}: {len(ids)} clip → {', '.join(i[:8] for i in ids)}")
    if len(ids) != g["expect"]["clips"]:
        print(f"  ⚠ dự kiến {g['expect']['clips']} clip")
    for u in unk:
        print(f"  ? chưa kiểm được: {u}")
    if not req:
        print("  ? không có request body → chỉ còn kiểm bằng feed (complete)")
    elif g.get("request_keys"):
        print(f"  khóa request: {', '.join(g['request_keys'])}")
    if bad:
        print("\n✖ REQUEST KHÁC SPEC (credits đã tốn):\n  " + "\n  ".join(bad))
        print("→ Dừng job Suno của kênh này, báo PM; không tải các clip này như bản hợp lệ khi PM chưa quyết.")
        sys.exit(2)
    print(f"Tiếp: js poll_feed --channel {a.channel} → filePath {rel(pool.evidence(g['id'], 'feed'))} → complete")


def compare_feed(g: dict, c: dict) -> list[str]:
    bad = []
    if c.get("description") is None:
        bad.append(f"feed không có {REQ_PROMPT_KEY} (không phải bài Simple?)")
    elif c["description"] != g["prompt"]:
        bad.append(f"prompt Suno lưu: {prompt_diff(c['description'], g['prompt'])}")
    if c.get("model_name") != g["mv"]:
        bad.append(f"model {c.get('model_name')!r} · cần {g['mv']!r}")
    want = g.get("voice") or {}
    got = c.get("persona") or {}
    if (got.get("id") or c.get("persona_id")) != want.get("id"):
        bad.append(f"Voice {got.get('name') or c.get('persona_id')!r} · cần {want.get('name')!r}")
    if c.get("make_instrumental"):
        bad.append("instrumental")
    if not (c.get("lyrics") or "").strip():
        bad.append("feed không có lời (metadata.prompt trống)")
    return bad


def cmd_complete(a):
    pool = Pool(a.channel)
    g = pool.pick(a.gen, ("submitted", "complete"))
    fp = Path(a.feed) if a.feed else pool.evidence(g["id"], "feed")
    feed = load_json_loose(fp)
    clips = feed.get("clips", feed) if isinstance(feed, dict) else feed
    by_id = {c["id"]: c for c in clips}
    missing = [i[:8] for i in g["clip_ids"] if i not in by_id]
    if missing:
        die(f"feed thiếu clip {', '.join(missing)}")
    notdone = [i[:8] + ":" + by_id[i]["status"] for i in g["clip_ids"] if by_id[i]["status"] not in ("complete", "error")]
    if notdone:
        die(f"chưa xong: {', '.join(notdone)} → chạy lại poll_feed")
    errs = [i for i in g["clip_ids"] if by_id[i]["status"] == "error"]
    keep, report, anybad = [], [], False
    for i in g["clip_ids"]:
        c = by_id[i]
        bad = compare_feed(g, c) if c["status"] == "complete" else [f"Suno báo lỗi: {c.get('error')}"]
        anybad |= bool(bad)
        keep.append({k: c.get(k) for k in ("id", "title", "status", "duration", "created_at", "model_name",
                                           "batch_index", "persona", "tags", "lyrics", "task")} | {"feed_mismatch": bad})
        n_lines = len([ln for ln in (c.get("lyrics") or "").splitlines() if ln.strip()])
        report.append(f"  {i[:8]} {c['status']} {mmss(c['duration']) if c.get('duration') else '?'} "
                      f"{c.get('title')!r} · lời {n_lines} dòng " + ("✔" if not bad else "✖ " + "; ".join(bad)))
    g.update(feed=keep, feed_file=rel(fp), completed_at=now(), status="failed" if errs else "complete",
             credits_after=a.credits_after)
    if g.get("credits_before") is not None:
        g["credits"] = g["credits_before"] - a.credits_after
    pool.save()
    print(f"{g['id']} ({g['type']}):\n" + "\n".join(report))
    if g.get("credits") is not None:
        exp = g["expect"]["credits"]
        print(f"credits: {g['credits_before']} → {a.credits_after} = {g['credits']}"
              + ("" if g["credits"] == exp else f" ⚠ dự kiến {exp if exp is not None else 'chưa đo'}: ghi số này vào báo cáo cho PM"))
    if errs:
        die("Suno báo lỗi clip → lượt failed. Báo PM; không tạo lại khi PM chưa quyết.", 2)
    if anybad:
        print("\n✖ Suno lưu khác spec → dừng job Suno của kênh này, báo PM trước khi tải.")
        sys.exit(2)
    print("\n✔ Tải từng clip qua usesuno: " + " · ".join(
        f"js usesuno_download --clip {i[:8]} → ingest --clip {i[:8]}" for i in g["clip_ids"]))


def cmd_ingest(a):
    pool = Pool(a.channel)
    g, c = pool.feed_clip(a.clip)
    cid, id8 = c["id"], c["id"][:8]
    if cid in pool.downloaded():
        die(f"clip {id8} đã có trong manifest")
    if c["status"] != "complete":
        die(f"clip {id8}: {c['status']} → không có bài để tải")
    if c.get("feed_mismatch") and not a.pm_ok:
        die(f"clip {id8} lệch spec {c['feed_mismatch']} → chỉ nhận khi PM đồng ý: --pm-ok \"<quyết định của PM>\"")
    want = c["duration"]
    if a.file:
        src = Path(a.file).expanduser()
    else:
        downloads = Path(a.downloads).expanduser()
        deadline = time.time() + a.wait
        while True:
            partial = list(downloads.glob("*.crdownload"))
            cands = [p for p in downloads.glob("*usesuno.com*.wav") if time.time() - p.stat().st_mtime < a.since * 60]
            match = [p for p in cands if abs(audio_duration(p) - want) <= DURATION_TOL]
            if match and not partial:
                break
            if time.time() > deadline:
                die(f"Không thấy file usesuno .wav trong {downloads} (≤ {a.since:g} phút) dài {want:.2f}s. "
                    f"Có: {[p.name for p in cands]}; đang tải dở: {[p.name for p in partial]}")
            time.sleep(2)
        if len(match) > 1:
            die(f"Nhiều file khớp thời lượng: {[p.name for p in match]} → chỉ rõ --file")
        src = match[0]
    if src.suffix.lower() != ".wav":
        die(f"{src.name}: cần file .wav từ usesuno")
    dur = audio_duration(src)
    if abs(dur - want) > DURATION_TOL:
        die(f"{src.name} dài {dur:.2f}s nhưng clip {id8} dài {want:.2f}s → sai file, KHÔNG ghi")
    sib = next((x for x in g.get("feed", []) if x["id"] != cid), None)
    if sib and sib.get("duration") and abs(sib["duration"] - want) <= DURATION_TOL:
        print(f"⚠ clip cùng lượt {sib['id'][:8]} dài gần bằng ({sib['duration']:.2f}s): thời lượng không phân biệt được "
              "2 clip → chỉ tải + ingest từng clip một")
    wav, meta, lyr = pool.raw / f"{id8}.wav", pool.raw / f"{id8}.json", pool.raw / f"{id8}.lyrics.txt"
    for p in (wav, meta, lyr):
        if p.exists():
            die(f"{rel(p)} đã tồn tại")
    digest = file_sha256(src)
    pool.raw.mkdir(parents=True, exist_ok=True)
    lyr.write_text(c["lyrics"])
    facts = {"clip_id": cid, "id8": id8, "generation": g["id"], "type": g["type"], "prompt": g["prompt"],
             "title": c["title"], "duration": want, "created": c["created_at"], "model": g["model"],
             "model_name": c["model_name"], "voice": c.get("persona"), "sibling_clip_id": sib["id"] if sib else None,
             "suno_url": f"https://suno.com/song/{cid}", "tags": c.get("tags"), "audio": wav.name,
             "lyrics_file": lyr.name, "file_duration": round(dur, 3), "sha256": digest, "source": "usesuno",
             "downloaded_at": now()} | ({"feed_mismatch": c["feed_mismatch"], "pm_ok": a.pm_ok} if c.get("feed_mismatch") else {})
    meta.write_text(json.dumps(facts, indent=1, ensure_ascii=False) + "\n")
    shutil.move(str(src), wav)
    pool.man["clips"].append({"clip_id": cid, "id8": id8, "generation": g["id"], "type": g["type"],
                              "file": f"raw/{wav.name}", "duration": want, "file_duration": round(dur, 3),
                              "sha256": digest, "downloaded_at": facts["downloaded_at"]}
                             | ({"pm_ok": a.pm_ok} if c.get("feed_mismatch") else {}))
    got = pool.downloaded()
    if all(x["id"] in got for x in g["feed"] if x["status"] == "complete"):
        g["status"] = "downloaded"
    pool.save()
    print(f"✔ {src.name} → {rel(wav)} ({mmss(dur)}, khớp clip {id8}) + {meta.name} + {lyr.name}")
    if g["status"] == "downloaded":
        print(f"✔ {g['id']} đã tải đủ {len(g['feed'])} clip")


def cmd_quota(a):
    pool = Pool(a.channel)
    log = pool.man["quota_log"]
    prev = log[-1] if log else None
    alert = bool(prev and a.downloads_used > prev["downloads_used"])
    log.append({"at": now(), "credits": a.credits, "downloads_used": a.downloads_used, "context": a.context}
               | ({"alert": f"downloads {prev['downloads_used']} → {a.downloads_used}"} if alert else {}))
    pool.save()
    print(f"credits {a.credits} · downloads chính thức {a.downloads_used}")
    if alert:
        die(f"QUOTA TẢI CHÍNH THỨC TĂNG {prev['downloads_used']} → {a.downloads_used} (từ '{prev['context']}'). "
            "DỪNG lane Suno, báo PM — skill không bao giờ dùng Download của Suno.", 3)
    if prev:
        print(f"  so với lần trước ({prev['context']}): credits {prev['credits']} → {a.credits}, downloads không đổi ✔")


def main():
    ap = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def cmd(name, fn, gen=False):
        p = sub.add_parser(name)
        p.add_argument("--channel", required=name != "js")
        if gen:
            p.add_argument("gen", nargs="?", help="gNNN; bỏ trống = lượt duy nhất ở đúng trạng thái")
        p.set_defaults(fn=fn)
        return p

    cmd("status", cmd_status)
    p = cmd("next", cmd_next)
    p.add_argument("--type", required=True, help="một type trong prompt_suno.md (vd. spoken, sung)")
    p = cmd("js", cmd_js)
    p.add_argument("name")
    p.add_argument("--gen")
    p.add_argument("--clip")
    p = cmd("check-form", cmd_check_form, gen=True)
    p.add_argument("--form", help="JSON của read_form.js (mặc định songs/raw/gen/<gen>.form.json)")
    p = cmd("submitted", cmd_submitted, gen=True)
    p.add_argument("--credits-before", type=int, required=True)
    p.add_argument("--request")
    p.add_argument("--response")
    p.add_argument("--clips", help="id1,id2 khi không có response (tìm bằng js find_recent)")
    p = cmd("complete", cmd_complete, gen=True)
    p.add_argument("--credits-after", type=int, required=True)
    p.add_argument("--feed", help="JSON của poll_feed.js (mặc định songs/raw/gen/<gen>.feed.json)")
    p = cmd("ingest", cmd_ingest)
    p.add_argument("--clip", required=True)
    p.add_argument("--file")
    p.add_argument("--downloads", default=str(Path.home() / "Downloads"))
    p.add_argument("--since", type=float, default=30, help="chỉ xét file mới hơn N phút")
    p.add_argument("--wait", type=float, default=90, help="chờ file tải xong tối đa N giây")
    p.add_argument("--pm-ok", help="quyết định của PM khi nhận clip lệch spec (ghi vào manifest + raw json)")
    p = cmd("quota", cmd_quota)
    p.add_argument("--credits", type=int, required=True)
    p.add_argument("--downloads-used", type=int, required=True)
    p.add_argument("--context", default="")
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

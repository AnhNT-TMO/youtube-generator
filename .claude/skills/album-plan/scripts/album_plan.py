"""Cầu nối research/idea → plan album → các skill sau (suno-generate, verification-audio, album-assembly).

<album>/plan.yaml là nguồn chính. Script này:
  init      tạo thư mục album + plan.yaml từ idea.yaml (hoặc chỉ từ research), ánh xạ máy móc, liệt kê chỗ cần quyết định
  validate  kiểm tra plan theo luật CLAUDE.md (§3, §4, §7.2) + tính khớp giữa các file; --final = đủ điều kiện duyệt
  build     sinh generation.yaml, selection.yaml, tracks/NN-*.md (front matter + brief), album.md từ plan
  summary   bảng tracklist để người dùng duyệt
  approve   (sau khi người dùng đồng ý) validate --final → build → status approved cho plan + generation.yaml
  board     trạng thái mọi idea/album/single của channel + bước tiếp theo (scripts/channel_tools.py)
  sync      chép thumbnail/video.json/loop mà idea gốc có bản mới hơn sang album (build tự chạy)
  catalog   dựng lại library/catalog.md + use_count từ front matter các bài đã chọn

    SK=.claude/skills/album-plan; P() { $SK/.venv/bin/python $SK/scripts/album_plan.py "$@"; }
    P init --channel lamplight_gospel --from-idea channel/lamplight_gospel/ideas/NNN-slug
    P init --channel lamplight_gospel --from-research <research-slug> --slug my-album --title "My Album"
    P validate <album> [--final] · P build <album> · P summary <album> · P approve <album> --by user
    P board --channel lamplight_gospel · P sync <album> · P catalog --channel lamplight_gospel
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]   # <repo>/.claude/skills/album-plan/scripts/album_plan.py
TEMPLATES = ROOT / "templates"
VI = re.compile(r"[À-ỹđĐ]")
INTRO_SECONDS = {"cold_open": 2, "short": 8, "medium": 20, "long": 35}   # ước lượng để tính mật độ lời
ARC_ROLES = {"anchor", "opener", "build", "peak", "release", "closer", "interlude"}
PLAN_KEYS_IN_TRACK = ["id", "title", "origin_album", "track_no", "genre_family", "subgenre", "time_signature",
                      "vocal_persona", "band_profile", "style_prompt_version", "energy", "valence", "emotion", "theme",
                      "arc_role", "intro_type", "hook_phrase", "lyric_keywords", "imagery", "echo_tracks",
                      "target_bpm", "target_duration", "source_ref"]
AUTO_BEGIN, AUTO_END = "<!-- album-plan:begin (sinh tự động từ plan.yaml, đừng sửa tay) -->", "<!-- album-plan:end -->"


# ---------------------------------------------------------------- helpers
def die(msg: str, code: int = 1):
    print(f"✖ {msg}", file=sys.stderr)
    sys.exit(code)


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


def norm_text(s: str | None) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", re.sub(r"\s+", " ", (s or "").lower().replace("’", "'"))).strip()


def secs(mmss) -> int | None:
    if mmss is None or mmss == "":
        return None
    if isinstance(mmss, (int, float)):
        return int(mmss)
    m = re.fullmatch(r"(\d+):(\d{2})", str(mmss).strip())
    if not m:
        raise ValueError(f"thời lượng '{mmss}' phải dạng m:ss")
    return int(m.group(1)) * 60 + int(m.group(2))


def mmss(s: float) -> str:
    return f"{int(s) // 60}:{int(s) % 60:02d}"


def rel(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def mid5(v):
    """Dải [a, b] → một số (giữa, làm tròn 5). Số đơn giữ nguyên."""
    if isinstance(v, list) and len(v) == 2:
        return int(5 * round((v[0] + v[1]) / 2 / 5))
    return v


def read_lyrics(md: Path) -> str | None:
    """Khối ``` đầu tiên sau '## Lyrics' — cùng quy tắc verification-audio (qc/lyrics.read_lyrics) và suno-generate."""
    if not md.exists():
        return None
    m = re.search(r"^##\s+Lyrics.*?$(.*)", md.read_text(), re.M | re.S)
    b = m and re.search(r"```[a-z]*\n(.*?)```", m.group(1), re.S)
    if not b or len(b.group(1).strip().splitlines()) < 4:
        return None
    return b.group(1).strip("\n")


def lyric_words(ly: str) -> list[str]:
    body = re.sub(r"\[[^\]]*\]", " ", ly)          # bỏ tag [..]
    body = re.sub(r"\([^)]*\)", " ", body)         # bỏ chỉ dẫn (..)
    return re.findall(r"[A-Za-z']+", body)


def album_dir(arg: str) -> Path:
    p = Path(arg)
    if p.is_dir():
        return p.resolve()
    hits = list(ROOT.glob(f"channel/*/albums/{arg}"))
    if len(hits) == 1:
        return hits[0]
    die(f"Không tìm thấy album '{arg}'")


def load_plan(album: Path) -> dict:
    f = album / "plan.yaml"
    if not f.exists():
        die(f"Chưa có {rel(f)} (chạy init)")
    return yaml.safe_load(f.read_text()) or {}


def set_top_scalar(path: Path, key: str, value: str):
    """Đổi một dòng `key: value` cấp ngoài cùng, giữ nguyên comment/định dạng phần còn lại."""
    txt = path.read_text()
    # giá trị cũ + khoảng trắng trước comment bị thay; comment cuối dòng giữ lại, cách giá trị mới 2 dấu cách
    new, n = re.subn(rf"^{key}:[^\n#]*?[ \t]*(#[^\n]*)?$", lambda m: f"{key}: {value}" + (f"  {m.group(1)}" if m.group(1) else ""),
                     txt, count=1, flags=re.M)
    if not n:
        new = txt.rstrip("\n") + f"\n{key}: {value}\n"
    path.write_text(new)


def append_status_log(path: Path, entry: dict):
    """Thêm 1 mục vào list `status_log` cấp ngoài cùng, đúng thụt lề của các mục đang có; giữ nguyên phần còn lại của file."""
    lines = path.read_text().splitlines(keepends=True)
    item = json.dumps(entry, ensure_ascii=False)
    i = next((k for k, ln in enumerate(lines) if re.match(r"status_log:", ln)), None)
    if i is None:
        lines += ["status_log:\n", f"  - {item}\n"]
    elif re.match(r"status_log:\s*\[\]", lines[i]):
        lines[i] = "status_log:\n"
        lines.insert(i + 1, f"  - {item}\n")
    else:
        j, indent = i + 1, None
        while j < len(lines) and (lines[j].startswith((" ", "-", "\t")) or not lines[j].strip()):
            m = re.match(r"(\s*)- ", lines[j])
            if m and indent is None:
                indent = m.group(1)
            j += 1
        while j > i + 1 and not lines[j - 1].strip():
            j -= 1
        lines.insert(j, f"{indent if indent is not None else '  '}- {item}\n")
    path.write_text("".join(lines))


def catalog_rows(channel: str) -> list[dict]:
    f = ROOT / "channel" / channel / "library" / "catalog.md"
    if not f.exists():
        return []
    rows, hdr = [], None
    for ln in f.read_text().splitlines():
        if not ln.startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if hdr is None:
            hdr = [c.lower() for c in cells]
            continue
        if set(cells[0]) <= set("-: "):
            continue
        rows.append(dict(zip(hdr, cells)))
    return rows


def channel_rules(channel: str) -> dict:
    """channel/<ch>/rules.md: khối ```yaml đầu tiên = luật máy đọc của channel (house style, mật độ lời, tên bài có thật…).
    {} khi channel chưa có rules.md (các check dựa trên rules được bỏ qua)."""
    f = ROOT / "channel" / channel / "rules.md"
    m = re.search(r"```yaml\n(.*?)```", f.read_text(), re.S) if f.is_file() else None
    try:
        return (yaml.safe_load(m.group(1)) or {}) if m else {}
    except yaml.YAMLError as e:
        die(f"{rel(f)}: khối yaml lỗi ({e})")


def ws(text) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


STOPWORDS = {"a", "an", "the", "to", "into", "of", "in", "on", "at", "for", "and", "or", "my", "me", "i", "you", "your",
             "it", "is", "be", "with", "oh", "im", "ill", "youre", "its"}


def content_tokens(text) -> set[str]:
    t = re.sub(r"['’]s\b", "", str(text or "").lower()).replace("'", "").replace("’", "")
    out = set()
    for w in re.findall(r"[a-z]+", t):
        if w in STOPWORDS:
            continue
        out.add(w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w)
    return out


def title_like(new: str, known: str) -> bool:
    """title/hook mới gần trùng một tên bài: chứa nguyên cụm (≥ 2 từ), hoặc mọi từ nội dung của bên ngắn nằm trong bên dài
    (≥ 2 từ nội dung; bỏ từ đệm và số nhiều: 'You still call me son' ~ 'Still Calls Me Son')."""
    a, b = norm_text(new), norm_text(known)
    if not a or not b:
        return False
    if (len(b.split()) >= 2 and f" {b} " in f" {a} ") or (len(a.split()) >= 2 and f" {a} " in f" {b} "):
        return True
    ta, tb = content_tokens(new), content_tokens(known)
    short, long_ = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    return len(short) >= 2 and short <= long_


def scripture_chapters(ref) -> set[str]:
    """'Luke 15:20; Psalm 42:5' → {'luke 15', 'psalm 42'} (so trùng Kinh Thánh giữa các album ở mức chương)."""
    return {f"{b.lower()} {c}" for b, c in re.findall(r"((?:[1-3] )?[A-Z][a-z]+)\s+(\d+)", str(ref or ""))}


def voice_entry(rules: dict, voice) -> dict | None:
    """Voice của plan (identity.voice {name, id}) trong rules.md voices[]; None khi không có."""
    vid = (voice or {}).get("id") if isinstance(voice, dict) else None
    return next((v for v in rules.get("voices") or [] if v.get("id") == vid), None)


def vocal_line(rules: dict, voice) -> str:
    """Câu giọng của Style: voices[].vocal_line của Voice đã chọn, không có thì house_style.vocal_line."""
    v = voice_entry(rules, voice) or {}
    return ws(v.get("vocal_line") or (rules.get("house_style") or {}).get("vocal_line"))


def reference_criteria(plan: dict) -> dict:
    """criteria của video tham khảo (research/<slug>/reference.yaml) theo sources.research của plan; {} khi không có."""
    for r in (plan.get("sources") or {}).get("research") or []:
        f = ROOT / Path(str(r)).parent / "reference.yaml"
        if f.is_file():
            c = (yaml.safe_load(f.read_text()) or {}).get("criteria") or {}
            if c:
                c["_file"] = rel(f)
                return c
    return {}


def channel_plans(channel: str, exclude: Path | None = None) -> list[tuple[str, dict]]:
    out = []
    for f in sorted((ROOT / "channel" / channel / "albums").glob("*/plan.yaml")):
        if exclude and f.parent.resolve() == exclude.resolve():
            continue
        try:
            out.append((f.parent.name, yaml.safe_load(f.read_text()) or {}))
        except yaml.YAMLError:
            continue
    return out


def other_plans(channel: str, album: Path) -> list[tuple[str, dict]]:
    """Slot mới của các album KHÁC trong channel đã có plan.yaml nhưng chưa phát hành: khi plan trước nhiều album cùng
    lúc (vd. 20 idea), title/hook không được đụng nhau dù chưa bài nào vào catalog."""
    out = []
    for f in (ROOT / "channel" / channel / "albums").glob("*/plan.yaml"):
        if f.parent.resolve() == album.resolve():
            continue
        try:
            p = yaml.safe_load(f.read_text()) or {}
        except yaml.YAMLError:
            continue
        out += [(f.parent.name, s) for s in p.get("slots") or [] if s.get("source") == "new"]
    return out


def channel_track_ids(channel: str, exclude: Path | None = None) -> set[str]:
    ids = set()
    for md in (ROOT / "channel" / channel / "albums").glob("*/tracks/*.md"):
        if exclude and exclude in md.parents:
            continue
        m = re.search(r"^id:\s*(\S+)", md.read_text(), re.M)
        if m:
            ids.add(m.group(1))
    return ids


# ---------------------------------------------------------------- init
def next_album_number(channel: str) -> int:
    nums = [int(p.name[:3]) for p in (ROOT / "channel" / channel / "albums").glob("[0-9][0-9][0-9]-*")]
    return max(nums, default=0) + 1


def make_prefix(slug: str, channel: str) -> str:
    base = "".join(w[0] for w in slug.split("-") if w) or "alb"
    used = {i.rsplit("-", 1)[0] for i in channel_track_ids(channel)}
    p, k = base, 2
    while p in used:
        p, k = f"{base}{k}", k + 1
    return p


def bpm_placeholder(text: str) -> tuple[str, list[str]]:
    """'around 64 BPM' → 'around {bpm} BPM'. Trả text mới + các số đã thay."""
    found = re.findall(r"\b(\d{2,3})(\s*)(?=BPM\b)", text, flags=re.I)
    new = re.sub(r"\b\d{2,3}(\s*)(?=BPM\b)", r"{bpm}\1", text, flags=re.I)
    return new, [f[0] for f in found]


def research_reference(slugs: list[str]) -> str:
    """Bảng tham chiếu số đo của research (notes/plan-reference.md). Chỉ để lên plan, không phải quyết định."""
    out = ["# Số đo tham chiếu từ research (album-plan init)", "",
           "Chỉ để tham khảo khi lên plan. `felt BPM` (reference.yaml) = tempo cảm nhận đo bằng qc của verification-audio,",
           "cùng đơn vị verify.py. Research cũ không có reference.yaml: `analyzer` = BPM librosa, **có thể lệch mức nhịp**",
           "(x2, x1/2, x2/3 với 6/8–12/8): đọc `.claude/skills/youtube-music-analyzer/references/interpretation.md` trước.", ""]
    for slug in slugs:
        d = ROOT / "research" / slug
        ry = d / "reference.yaml"
        if ry.exists():   # analyzer mới: số đo đã quy về đơn vị QC (bpm = felt), nguồn ưu tiên
            r = yaml.safe_load(ry.read_text()) or {}
            src, alb_ = r.get("source") or {}, r.get("album") or {}
            tm = (r.get("criteria") or {}).get("tempo") or alb_.get("tempo") or {}   # reference/v3, older
            out += [f"## {slug} (reference.yaml)", "", f"{src.get('title')} · {src.get('channel')} · {mmss(src.get('duration_s') or 0)} · "
                    f"{src.get('views')} views · felt tempo median {tm.get('felt_bpm_median', tm.get('felt_bpm_qc_median'))}", ""]
            if r.get("criteria"):
                out += ["Tiêu chí (youtube-music-analyzer SKILL.md): " + "; ".join(
                    f"{k}: " + ", ".join(f"{a}={b}" for a, b in v.items() if not str(a).startswith("_") and not isinstance(b, dict))
                    for k, v in r["criteria"].items()), ""]
            out += ["| # | title | dur | felt BPM | meter | voice (f0) | lyric s | words/sung min |", "|---|---|---|---|---|---|---|---|"]
            for t in r.get("tracks") or []:
                out.append(f"| {t.get('n')} | {t.get('title') or ''} | {mmss(t.get('duration_s') or 0)} | {t.get('bpm')} | {t.get('time_signature')} | "
                           f"{t.get('voice') or ''} ({t.get('f0_median_hz')}) | {t.get('first_lyric_s')} | "
                           f"{t.get('words_per_min_sung', t.get('words_per_min'))} |")
            out += ["", f"copy_guard_seed: {r.get('copy_guard_seed')}", ""]
            continue
        aj = d / "audio" / "analysis.json"
        if not aj.exists():
            out += [f"## {slug}", "", f"(không có {rel(aj)})", ""]
            continue
        a = json.loads(aj.read_text())
        qf = d / "audio" / "qc_measurements.json"
        qc = (json.loads(qf.read_text()).get("songs") or {}) if qf.exists() else {}
        v = a.get("video") or {}
        out += [f"## {slug}", "", f"{v.get('title')} · {v.get('channel')} · {mmss(v.get('duration') or 0)} · "
                f"{v.get('view_count')} views · chia bài: {a.get('segmentation_source')}", "",
                "| # | title | dur | felt BPM | analyzer BPM (meter hint) | camelot (conf) | energy | intro | vocal entry s | wpm | outro |",
                "|---|---|---|---|---|---|---|---|---|---|---|"]
        for t in a.get("tracks") or []:
            q = qc.get(f"{t['n']:02d}") or {}
            tp, k, it, ot, vo = t.get("tempo") or {}, t.get("key") or {}, t.get("intro") or {}, t.get("outro") or {}, t.get("vocals") or {}
            out.append(f"| {t['n']} | {t.get('title') or ''} | {mmss(t.get('duration_s') or 0)} | {q.get('felt_bpm_qc', '')} | "
                       f"{tp.get('bpm', '')} ({(tp.get('meter') or {}).get('hint', '')}) | {k.get('camelot', '')} ({k.get('confidence', '')}) | "
                       f"{t.get('energy', '')} | {it.get('type', '')} {it.get('seconds', '')} | {vo.get('entry_s', '')} | "
                       f"{vo.get('words_per_min', '')} | {ot.get('type', '')} {ot.get('seconds', '')} |")
        s = a.get("summary") or {}
        out += ["", f"Energy curve (tương đối trong video): {s.get('energy_curve')} · avg {mmss(s.get('avg_track_len_s') or 0)} · "
                f"LUFS {s.get('lufs_range')} · mở video: {a.get('video_opening')}", ""]
    return "\n".join(out) + "\n"


def plan_from_idea(idea: dict, idea_path: Path, album: Path) -> tuple[dict, list[str]]:
    """Ánh xạ máy móc idea.yaml → plan.yaml. Trả plan + ghi chú những gì đã đổi/bỏ qua."""
    notes = []
    tmpl = yaml.safe_load((TEMPLATES / "plan.yaml").read_text())
    p = tmpl
    ident, tgt, gen, sp = idea.get("identity") or {}, idea.get("target") or {}, idea.get("generation") or {}, idea.get("style_prompt") or {}
    settings = gen.get("settings") or {}
    p["sources"] = {"idea": rel(idea_path), "research": [r["path"] for r in (idea.get("provenance") or {}).get("research") or [] if r.get("path")]}
    p["concept"] = (idea.get("hypothesis") or {}).get("statement") or p["concept"]
    dif = idea.get("differentiation") or {}
    cg = dif.get("copy_guard") or {}
    avoid = cg.get("scripture_avoid") or []
    p["differentiation"] = {"keep": dif.get("keep") or [], "change": dif.get("change") or [],
                            "copy_guard": {"titles": cg.get("titles") or [], "hooks": cg.get("hooks") or [],
                                           "branding": cg.get("branding") or [],
                                           "source_avoid": [f"Psalm {x}" if isinstance(x, int) else str(x) for x in avoid],
                                           "lyric_rule": cg.get("lyric_rule") or p["differentiation"]["copy_guard"]["lyric_rule"]}}
    if avoid and all(isinstance(x, int) for x in avoid):
        notes.append(f"copy_guard.scripture_avoid {avoid} → source_avoid 'Psalm N' (so với slot.source_ref)")
    sv = ident.get("suno_voice") or {}
    p["identity"] = {"vocal_persona": ident.get("vocal_persona"), "band_profile": ident.get("band_profile"),
                     "voice": {"name": sv["name"], "id": sv["id"]} if sv.get("name") and sv.get("id") else None,
                     "vocal_gender": settings.get("vocal_gender") or p["identity"]["vocal_gender"]}
    if not settings.get("vocal_gender"):
        notes.append(f"idea không ghi generation.settings.vocal_gender → dùng '{p['identity']['vocal_gender']}' (mặc định template); kiểm tra lại")
    pd = ident.get("persona_decision") or {}
    if pd and not pd.get("decided"):
        notes.append(f"persona chưa chốt trong idea (recommended {pd.get('recommended')}) → đang dùng Voice của idea; xem open_questions")
    t = tgt.get("tempo") or {}
    bpm = t.get("felt_bpm_qc") or t.get("bpm") or t.get("target_bpm")
    p["sound"]["tempo"] = {"bpm": bpm, "meter": t.get("meter"), "unit": "felt",
                           "why": f"idea target (tham khảo đo {t.get('reference_measured')}, album mình đo {t.get('ours_measured', t.get('album001_measured'))})"}
    if t.get("prompt_bpm") and t.get("prompt_bpm") != bpm:
        notes.append(f"BỎ QUA idea target.tempo.prompt_bpm={t['prompt_bpm']} (bù trừ theo phỏng đoán về Suno). "
                     f"Prompt dùng đúng tempo mục tiêu {bpm}; lệch thật (nếu có) do verification-audio đo và xử lý lúc generate")
    text, nums = bpm_placeholder(sp.get("text") or "")
    if nums:
        notes.append(f"style: thay BPM cứng {nums} bằng {{bpm}} (mỗi bài điền bpm của bài đó, mặc định {bpm})")
    p["sound"]["style"] = {"version": sp.get("version"), "text": re.sub(r"\s+", " ", text).strip(),
                           "exclude": sp.get("exclude_styles") or p["sound"]["style"]["exclude"]}
    genre = (sp.get("text") or "").split(",")[0][:80]
    p["sound"]["genre_family"], p["sound"]["subgenre"] = None, None
    notes.append(f"sound.genre_family/subgenre để trống: điền theo channel.md (gợi ý từ style: '{genre}')")
    tv = tgt.get("vocal") or {}
    p["target"] = {"duration_min": tgt.get("duration_min") or p["target"]["duration_min"],
                   "track_count": tgt.get("track_count") or len(idea.get("slots") or []),
                   "track_duration": (tgt.get("track_duration") or {}).get("range") or p["target"]["track_duration"],
                   "energy_adjacent_max": 2, "bpm_adjacent_max_pct": tgt.get("adjacent_bpm_delta_max_pct", 8),
                   "reuse_per_album_max": 2, "reuse_total_max": 4,
                   "peak_slots": [s["n"] for s in idea.get("slots") or [] if s.get("arc_role") == "peak"] or p["target"]["peak_slots"],
                   "words_per_min": tv.get("words_per_min") or p["target"]["words_per_min"],
                   "tempo_range": t.get("felt_bpm_qc_range") or None,
                   "vocal": {"first_voice_max_s": tv.get("presence_max_s") or p["target"]["vocal"]["first_voice_max_s"],
                             "first_lyric_max_s": tv.get("first_lyric_max_s") or p["target"]["vocal"]["first_lyric_max_s"],
                             "first_hook_max_s": tv.get("first_hook_max_s") or p["target"]["vocal"].get("first_hook_max_s"),
                             "f0_median_hz": tv.get("f0_median_hz"),
                             "singer_similarity_min": next((v for k, v in tv.items() if k.startswith("ecapa_vs_")), None),
                             "singer_similarity_ref": next((k.removeprefix("ecapa_vs_").removesuffix("_min") for k in tv if k.startswith("ecapa_vs_")), None)},
                   "drums_in_s_max": tgt.get("drums_in_s_max"),
                   "loudness": tgt.get("loudness"),
                   "transition": tgt.get("transition"),
                   "key_policy": tgt.get("key_policy")}
    if idea.get("lyrics_rules"):
        lr = {k: v for k, v in idea["lyrics_rules"].items() if v is not None}
        lr.pop("file_format", None)
        p["lyrics_rules"] = {**p["lyrics_rules"], **lr}
    p["experiment"] = idea.get("experiment") or None
    si = settings.get("style_influence") or {}
    budget = gen.get("budget") or {}
    gens = budget.get("gens") or {}
    dur = settings.get("duration") or {}
    if gen.get("max_mode") or (gens.get("track01") or 2) > 2 or (gens.get("others_each") or 1) > 1:
        notes.append(f"generation: idea xin max_mode={gen.get('max_mode')} / gens={gens or '-'} → áp luật credits CLAUDE.md §4 "
                     f"(bài 1 = {LEAN_ROUNDS['track01']} lượt Max, bài khác = {LEAN_ROUNDS['others']} lượt thường); muốn hơn thì hỏi chủ kênh")
    p["generation"] = {"model": gen.get("model", "v6"), "max_mode": False,
                       "duration": "custom" if dur.get("mode", "custom") == "custom" else "auto",
                       "variety": settings.get("variety", 0), "weirdness": mid5(settings.get("weirdness", 25)),
                       "style_influence": {"track01": mid5(si.get("track01", 50)), "others": mid5(si.get("others", 50))},
                       "audio_influence": mid5((settings.get("audio_influence") or {}).get("others", 65)
                                               if isinstance(settings.get("audio_influence"), dict) else settings.get("audio_influence", 65)),
                       "personalize": "off",
                       "rounds": dict(LEAN_ROUNDS),
                       "budget_max_credits": CREDITS_CEILING,
                       "credits_per_generation": {"max": budget.get("credits_per_max_gen", 20), "normal": 10},
                       "anchor_first": True}
    ranged = [k for k in ("weirdness",) if isinstance(settings.get(k), list)] + \
             [f"style_influence.{k}" for k, v in si.items() if isinstance(v, list)]
    if ranged:
        notes.append(f"generation: dải {ranged} → số giữa làm tròn 5 (xem lại nếu muốn số khác)")
    qc = idea.get("qc") or {}

    def to_album_rel(g):   # idea ghi đường dẫn tính từ gốc repo; selection.yaml cần tương đối so với thư mục album
        return Path(os.path.relpath(ROOT / g, album)).as_posix() if g and (ROOT / g.split("*")[0]).parent.exists() else g
    refs = qc.get("references")
    refs = [refs] if isinstance(refs, str) else (refs or [])
    p["qc"] = {"references": [to_album_rel(r) for r in refs],
               "style": {"positive": (qc.get("style") or {}).get("positive") or [], "negative": (qc.get("style") or {}).get("negative") or {}},
               "rules": {**p["qc"]["rules"], **{k: v for k, v in (qc.get("rules") or {}).items() if v is not None}},
               "thresholds": qc.get("thresholds") or {},
               "intro_types": qc.get("intro_types") or {},
               "extra_checks": qc.get("extra_checks") or []}
    qt = (qc.get("tempo") or {}).get("target_bpm")
    if qt and qt != bpm:
        notes.append(f"idea qc.tempo.target_bpm={qt} ≠ target.tempo.felt_bpm_qc={bpm} → dùng {bpm} (selection.yaml lấy từ sound.tempo)")
    if qc.get("anchor"):
        notes.append("qc.anchor của idea KHÔNG chép: anchor của album mới do verification-audio điền khi chốt slot 1; "
                     "album chị em nằm trong qc.references làm baseline")
    p["library_check"] = idea.get("library_check") or p["library_check"]
    t01 = idea.get("track01") or {}
    slots = []
    for s in idea.get("slots") or []:
        n = int(s["n"])
        slot = {"n": n, "title": s.get("title"), "source": s.get("source", "new"), "library_id": s.get("library_id"),
                "arc_role": s.get("arc_role"), "emotion": s.get("emotion"), "theme": s.get("theme"),
                "source_ref": s.get("scripture") or s.get("source_ref"), "energy": s.get("energy"), "valence": s.get("valence"),
                "bpm": s.get("bpm"), "intro_type": s.get("intro_type"), "intro_length": s.get("intro_length"),
                "target_duration": s.get("target_duration") or (mmss(dur["seconds"]) if dur.get("seconds") else None),
                "hook_phrase": s.get("hook_phrase"),
                "imagery": s.get("imagery") or [], "lyric_keywords": s.get("lyric_keywords") or [],
                "echo_tracks": s.get("echo_tracks") or [],
                "arrangement": s.get("arrangement_note") or (t01.get("lyric_tags_hint") if n == 1 else "") or "",
                "opening_spec": t01.get("opening_spec") or [] if n == 1 else [],
                "gate": t01.get("gate") or [] if n == 1 else [],
                "reference_recipe": t01.get("reference_recipe") or [] if n == 1 else [],
                "rounds": None, "generation_overrides": {"max_mode": True} if n == 1 else {},
                "variants": (t01.get("variants") or []) if n == 1 and isinstance(t01.get("variants"), list) else [],
                "notes": "; ".join(str(x) for x in [s.get("note"), (t01.get("concept") if n == 1 else None),
                                                    (f"listener: {t01['listener']}" if n == 1 and t01.get("listener") else None)] if x)}
        if s.get("echo_tracks_planned"):
            slot["notes"] += f"; echo dự kiến: {s['echo_tracks_planned']}"
        slots.append(slot)
    p["slots"] = slots
    if t01.get("variants") and not isinstance(t01["variants"], list):
        notes.append(f"track01.variants không phải list ({type(t01['variants']).__name__}) → chưa chép; tự khai báo slot 1 variants")
    if dur.get("seconds") and all(s.get("target_duration") for s in idea.get("slots") or []):
        notes.append(f"generation.settings.duration.seconds={dur['seconds']} chỉ dùng cho slot thiếu target_duration (mọi slot đã có)")
    if t01.get("candidates_min") and t01["candidates_min"] > 2 * p["generation"]["rounds"]["track01"]:
        p["generation"]["rounds"]["track01"] = math.ceil(t01["candidates_min"] / 2)
    p["open_questions"] = [{"id": q.get("id"), "q": q.get("q"), "blocking": bool(q.get("blocking")),
                            "answer": q.get("answer"), **({"default": q["default"]} if "default" in q else {}),
                            **({"recommended": q["recommended"]} if "recommended" in q else {})}
                           for q in idea.get("open_questions") or []]
    return p, notes


def cmd_init(a):
    ch_dir = ROOT / "channel" / a.channel
    if not ch_dir.is_dir():
        die(f"Không có channel/{a.channel}")
    idea, idea_path = None, None
    if a.from_idea:
        d = Path(a.from_idea)
        idea_path = d / "idea.yaml" if d.is_dir() else d
        if not idea_path.exists():
            die(f"Không có {idea_path}")
        raw = idea_path.read_text()
        todos = len(re.findall(r"TODO\(claude\)", raw)) + len((yaml.safe_load(raw) or {}).get("todo") or [])
        if todos and not a.force:
            die(f"idea còn {todos} chỗ TODO(claude): analyzer chưa viết xong idea. Hoàn tất idea + chạy "
                ".claude/skills/youtube-music-analyzer/scripts/validate_idea.py trước (--force để bỏ qua)")
        idea = yaml.safe_load(raw)
        if idea.get("status") in ("rejected", "promoted", "published") and not a.force:
            die(f"idea đang ở trạng thái {idea['status']} (album: {idea.get('album')}). --force nếu vẫn muốn tạo")
    if not idea and not a.from_research:
        die("Cần --from-idea hoặc --from-research")
    slug = a.slug or (idea or {}).get("slug")
    if not slug:
        die("Cần --slug")
    num = next_album_number(a.channel)
    album = Path(a.out).resolve() if a.out else ch_dir / "albums" / f"{num:03d}-{slug}"
    if a.out and re.match(r"\d{3}-", album.name):
        num = int(album.name[:3])                 # --out quyết định số album (chạy nhiều init song song không tranh số)
    if (album / "plan.yaml").exists():
        die(f"{rel(album)}/plan.yaml đã có")
    (album / "tracks").mkdir(parents=True, exist_ok=True)
    (album / "notes").mkdir(exist_ok=True)
    notes = []
    if idea:
        plan, notes = plan_from_idea(idea, idea_path, album)
        research = [Path(r.get("reference") or r["path"]).parent.name
                    for r in (idea.get("provenance") or {}).get("research") or [] if r.get("reference") or r.get("path")]
    else:
        plan = yaml.safe_load((TEMPLATES / "plan.yaml").read_text())
        plan["sources"] = {"idea": None, "research": [f"research/{s}/analysis.md" for s in a.from_research]}
        plan["slots"] = []
        research = a.from_research
        for rs in a.from_research:
            ry = ROOT / "research" / rs / "reference.yaml"
            if ry.exists():
                g = (yaml.safe_load(ry.read_text()) or {}).get("copy_guard_seed") or {}
                cgp = plan["differentiation"]["copy_guard"]
                cgp["titles"] = sorted(set(cgp["titles"]) | set(g.get("titles") or []))
                cgp["branding"] = sorted(set(cgp["branding"]) | set(g.get("branding") or []))
                cgp["source_avoid"] = sorted(set(cgp["source_avoid"]) | {f"Psalm {x}" for x in g.get("psalms_used") or []})
                notes.append(f"copy_guard lấy từ research/{rs}/reference.yaml (copy_guard_seed)")
        notes.append("Không có idea: plan chỉ có khung. Lấy số đo từ notes/plan-reference.md + analysis.md, tự quyết concept, "
                     "copy_guard, tempo, style, tracklist (xem SKILL.md mục 2)")
    if a.from_research and idea:
        research = sorted(set(research) | set(a.from_research))
        plan["sources"]["research"] = sorted(set(plan["sources"]["research"]) | {f"research/{s}/analysis.md" for s in a.from_research})
    plan["album"] = {"number": num, "slug": slug, "title_working": a.title or (idea or {}).get("title_working") or slug,
                     "channel": a.channel, "id_prefix": make_prefix(slug, a.channel)}
    rules_ = channel_rules(a.channel)
    hs = rules_.get("house_style") or {}
    if hs and not (plan.get("experiment") or {}).get("axes"):
        st = plan["sound"]["style"]
        first = (st.get("text") or "").split(".")[0].split(",")
        mood = ",".join(first[2:]).strip() or "<album mood phrase>"
        meter = (plan["sound"].get("tempo") or {}).get("meter") or "6/8"
        st.update({"version": st.get("version") or f"{plan['album']['id_prefix']}-v1",
                   "text": f"{hs['genre_lead']}, {mood}. {vocal_line(rules_, (plan.get('identity') or {}).get('voice'))} "
                           f"{ws(hs['band_block'])} Slow {meter} groove, {{bpm}} BPM.",
                   "exclude": hs["exclude"]})
        notes.append(f"style: dựng từ house_style {hs.get('version')} của channel/{a.channel}/rules.md (cụm mood: '{mood}'); "
                     "album muốn khác mặc định → khai báo experiment")
    plan["status"] = "draft"
    plan["status_log"] = [{"date": str(date.today()), "status": "draft", "by": "album-plan init",
                           "note": f"from {plan['sources']['idea'] or ', '.join(plan['sources']['research'])}"}]
    out = album / "plan.yaml"
    header = ("# Plan album — nguồn chính (skill album-plan). Sửa ở đây rồi `build`; đừng sửa tay generation.yaml/selection.yaml.\n"
              "# Giải thích từng trường: templates/plan.yaml · hợp đồng với các skill khác: .claude/skills/album-plan/references/bridge.md\n")
    out.write_text(header + yaml.safe_dump(plan, sort_keys=False, allow_unicode=True, width=120))
    (album / "notes" / "plan-reference.md").write_text(research_reference(research))
    if idea:
        src_dir = idea_path.parent
        shutil.copy2(idea_path, album / "idea.yaml")
        for f in ("idea.md", "thumbnail.png", "video.json"):
            if (src_dir / f).exists() and not (album / f).exists():
                shutil.copy2(src_dir / f, album / f)
        if not a.no_promote:
            set_top_scalar(idea_path, "status", "promoted")
            set_top_scalar(idea_path, "album", rel(album))
            append_status_log(idea_path, {"date": str(date.today()), "status": "promoted", "by": "album-plan", "note": f"-> {rel(album)}"})
            notes.append(f"idea → status promoted, album: {rel(album)} (idea.yaml, idea.md, thumbnail, video.json đã chép sang album; "
                         "video/ không chép vì nặng)")
    print(f"✔ {rel(album)}/plan.yaml (album {num:03d}, id_prefix {plan['album']['id_prefix']})")
    print(f"✔ {rel(album)}/notes/plan-reference.md (số đo research)")
    for n_ in notes:
        print(f"• {n_}")
    print(f"\nTiếp: sửa plan.yaml → P validate {rel(album)} → P build {rel(album)} → viết lyrics vào tracks/*.md")


# ---------------------------------------------------------------- validate
class Issues:
    def __init__(self, waivers):
        self.errors, self.warns, self.waived = [], [], []
        self.credits, self.total = 0, 0
        self.waivers = waivers or []

    def err(self, rule, msg, slots=()):
        w = next((w for w in self.waivers if w.get("rule") == rule and set(slots) <= set(w.get("slots") or slots)), None)
        (self.waived if w else self.errors).append(f"[{rule}] {msg}" + (f" — waiver: {w.get('why')}" if w else ""))

    def warn(self, rule, msg, slots=()):   # slots: cùng chữ ký với err để gọi (I.warn if … else I.err)(rule, msg, slots)
        self.warns.append(f"[{rule}] {msg}")


CREDITS_CEILING = 250            # CLAUDE.md §4: trần credits một album (album 14–15 bài vẫn đủ)
LEAN_ROUNDS = {"track01": 2, "others": 1}   # CLAUDE.md §4: bài 1 = 2 lượt Max, bài khác = 1 lượt thường
TEMPO_BAND_MAX_RATIO = 1.20      # một album = một dải tempo: bpm bài nhanh nhất / chậm nhất ≤ 1.20; giữa các album dải được khác nhau


def slot_bpm(plan, s):
    return s.get("bpm") or ((plan.get("sound") or {}).get("tempo") or {}).get("bpm")


def main_track_files(album: Path, n: int) -> list[Path]:
    """File track chính của slot n: `NN-<slug>.md`. File lời biến thể (`NN-<slug>.<variant>.md`) không tính."""
    return sorted(p for p in (album / "tracks").glob(f"{n:02d}-*.md") if "." not in p.name[:-3])


def fm_value(text: str, key: str) -> str:
    """Giá trị `key:` trong front matter (bỏ comment cuối dòng và dấu nháy); "" khi trống. Không đọc sang dòng sau."""
    head = text.partition("\n---\n")[0]
    m = re.search(rf"^{re.escape(key)}:[ \t]*([^\n]*)$", head, re.M)
    if not m:
        return ""
    return re.sub(r"(^|\s+)#.*$", "", m.group(1)).strip().strip("\"'")


def track_path(album: Path, s: dict) -> Path:
    n = int(s["n"])
    hits = main_track_files(album, n)
    want = album / "tracks" / f"{n:02d}-{slugify(s.get('title'))}.md"
    return want if want.exists() or not hits else hits[0]


def validate(plan: dict, album: Path, final: bool) -> Issues:
    I = Issues(plan.get("waivers"))
    if plan.get("schema_version") != 1:
        I.err("schema", "schema_version phải là 1")
    alb, ident, sound = plan.get("album") or {}, plan.get("identity") or {}, plan.get("sound") or {}
    tempo, style, tgt = sound.get("tempo") or {}, sound.get("style") or {}, plan.get("target") or {}
    gen, qc, cg = plan.get("generation") or {}, plan.get("qc") or {}, ((plan.get("differentiation") or {}).get("copy_guard") or {})
    slots = sorted(plan.get("slots") or [], key=lambda s: s.get("n", 0))
    rules = channel_rules(alb.get("channel", ""))            # channel/<ch>/rules.md (nguồn chuẩn của channel)
    exp = plan.get("experiment") or {}
    axes = {str(x).lower() for x in exp.get("axes") or []}
    if exp and not (axes and exp.get("what") and exp.get("why")):
        I.err("experiment", "experiment cần axes (voice/tempo/energy/style/band/density/structure…) + what + why (+ measure)")
    hs = rules.get("house_style") or {}
    if hs:
        txt = ws(style.get("text"))
        parts = {"genre_lead": ws(hs.get("genre_lead")), "vocal_line (của Voice đã chọn)": vocal_line(rules, ident.get("voice")),
                 "band_block": ws(hs.get("band_block"))}
        miss = [k for k, v in parts.items() if v and v not in txt]
        have = {x.strip().lower() for x in str(style.get("exclude") or "").split(",") if x.strip()}
        ex_miss = sorted({x.strip().lower() for x in hs.get("exclude", "").split(",") if x.strip()} - have)
        if miss or ex_miss:
            what = (f"Style thiếu {', '.join(miss)} nguyên văn" if miss else "") + ("; " if miss and ex_miss else "") + \
                   (f"Exclude thiếu {ex_miss}" if ex_miss else "")
            if axes & {"style", "voice", "persona", "band", "exclude"}:
                I.warn("house_style", f"{what} — khác house sound {hs.get('version')} có chủ đích (experiment {sorted(axes)})")
            else:
                I.err("house_style", f"{what} so với house_style {hs.get('version')} (channel rules.md §1); "
                                     "muốn khác mặc định thì khai báo experiment")
    if re.search(r"<[^>]*>", str(style.get("text") or "")):
        I.err("style", "Style còn chỗ trống <…> (vd. <album mood phrase>)")
    rf = rules.get("reference_follow") or {}
    refc = reference_criteria(plan) if rf else {}
    ve = voice_entry(rules, ident.get("voice"))
    if rules.get("voices") and not ve:
        I.err("voice", f"identity.voice {((ident.get('voice') or {}).get('name'))!r} không có trong rules.md voices (dùng Voice của kênh)")
    if ve and ve.get("persona") and ident.get("vocal_persona") != ve["persona"]:
        I.err("voice", f"identity.vocal_persona {ident.get('vocal_persona')!r} ≠ persona của Voice {ve['name']} ({ve['persona']!r}, rules.md voices)")
    ref_f0 = ((refc.get("voice") or {}).get("f0_median_hz"))
    if ve and ref_f0 and rf.get("voice_f0_max_dev_pct") and "voice" not in axes:
        dev = abs(ve["f0_hz"] / ref_f0 - 1) * 100
        if dev > rf["voice_f0_max_dev_pct"]:
            best = min(rules["voices"], key=lambda v: abs(v["f0_hz"] - ref_f0))
            I.err("reference_follow", f"Voice {ve['name']} ({ve['f0_hz']} Hz) lệch {dev:.0f}% so với giọng video tham khảo ({ref_f0:.0f} Hz) "
                                      f"> {rf['voice_f0_max_dev_pct']}% → gần nhất: {best['name']} (rules.md §1b)")
    ref_bpm = ((refc.get("tempo") or {}).get("felt_bpm_median"))
    if ref_bpm and tempo.get("bpm") and rf.get("tempo_max_dev_pct") and "tempo" not in axes:
        dev = abs(tempo["bpm"] / ref_bpm - 1) * 100
        if dev > rf["tempo_max_dev_pct"]:
            I.err("reference_follow", f"sound.tempo.bpm {tempo['bpm']} lệch {dev:.0f}% so với tempo video tham khảo {ref_bpm} "
                                      f"> {rf['tempo_max_dev_pct']}% (rules.md §1b: tempo = video tham khảo)")
    hl = plan.get("highlight") or {}
    hcfg = rules.get("highlight") or {}
    hslot = hl.get("slot") if isinstance(hl, dict) else None
    if hcfg:
        if not hslot:
            (I.err if final and hcfg.get("required") else I.warn)("highlight", f"chưa có highlight (bài điểm nhấn ở slot {hcfg.get('slots')}, rules.md §1b)")
        else:
            if hcfg.get("slots") and hslot not in hcfg["slots"]:
                I.err("highlight", f"highlight.slot {hslot} phải là một trong {hcfg['slots']}")
            hs_ = next((x for x in slots if x["n"] == hslot), None)
            if not hs_ or hs_.get("source") != "new":
                I.err("highlight", f"highlight.slot {hslot} phải là bài mới")
            if not (hl.get("axis") and hl.get("what") and hl.get("why")):
                I.err("highlight", "highlight cần axis + what + why (+ single: true)")
    for k in ("slug", "channel", "id_prefix"):
        if not alb.get(k):
            I.err("album", f"album.{k} trống")
    # --- danh tính & âm thanh
    if not ident.get("vocal_persona") or not ident.get("band_profile"):
        I.err("identity", "identity.vocal_persona / band_profile trống (CLAUDE.md §4: khóa nghệ sĩ cho cả album)")
    v = ident.get("voice")
    if v is not None and not (isinstance(v, dict) and v.get("name") and v.get("id")):
        I.err("identity", "identity.voice phải là null hoặc {name, id}")
    if v is None and len(slots) > 1:
        I.warn("identity", "chưa có Suno Voice → trước slot 2 phải tạo Voice từ Anchor và điền vào đây")
    if not isinstance(tempo.get("bpm"), (int, float)) or not 30 <= tempo["bpm"] <= 200:
        I.err("tempo", f"sound.tempo.bpm phải là một số 30–200 (đang là {tempo.get('bpm')!r})")
    if not tempo.get("meter"):
        I.err("tempo", "sound.tempo.meter trống (đơn vị tempo phụ thuộc meter)")
    if tempo.get("unit") != "felt":
        I.err("tempo", "sound.tempo.unit phải là 'felt' (nhịp cảm nhận, cùng đơn vị với verification-audio)")
    for k in ("genre_family", "subgenre"):
        if not sound.get(k):
            I.warn("sound", f"sound.{k} trống (ghi vào track md, dùng cho catalog)")
    txt = re.sub(r"\s+", " ", style.get("text") or "").strip()
    if not txt or txt.startswith("("):
        I.err("style", "sound.style.text trống")
    else:
        hard = re.findall(r"\b\d{2,3}\s*BPM\b", txt, re.I)
        if hard:
            I.err("style", f"style ghi BPM cứng {hard} → dùng {{bpm}} để mỗi bài nhận đúng tempo của plan")
        longest = max([len(txt.replace("{bpm}", str(slot_bpm(plan, s) or tempo.get("bpm") or 0))) for s in slots] or [len(txt)])
        if longest > 1000:
            I.err("style", f"style dài {longest} ký tự sau khi thay {{bpm}} (> 1000)")
        if tempo.get("meter") and tempo["meter"] not in txt:
            I.warn("style", f"style không nhắc meter {tempo['meter']}")
        if VI.search(txt + (style.get("exclude") or "")):
            I.err("language", "style có ký tự tiếng Việt (text vào Suno phải là tiếng Anh)")
    if not style.get("version"):
        I.err("style", "sound.style.version trống")
    if not style.get("exclude"):
        I.warn("style", "sound.style.exclude trống")
    # --- slots cơ bản
    if not slots:
        I.err("slots", "chưa có slot nào")
        return I
    ns = [s.get("n") for s in slots]
    if ns != list(range(1, len(slots) + 1)):
        I.err("slots", f"slot n phải liên tục 1..{len(slots)} (đang là {ns})")
    if tgt.get("track_count") and tgt["track_count"] != len(slots):
        I.warn("slots", f"target.track_count {tgt['track_count']} ≠ {len(slots)} slot")
    titles = [norm_text(s.get("title")) for s in slots]
    for t in {t for t in titles if titles.count(t) > 1 and t}:
        I.err("title", f"trùng title '{t}'")
    catalog = catalog_rows(alb.get("channel", ""))
    cat_titles = {norm_text(r.get("title")): r.get("id") for r in catalog}
    cat_hooks = {norm_text(r.get("hook")): r.get("id") for r in catalog if r.get("hook")}
    others = other_plans(alb.get("channel", ""), album)   # album khác đang plan (chưa có bài trong catalog)
    oplans = channel_plans(alb.get("channel", ""), album)
    known = [(str(t), "rules.md known_titles") for t in rules.get("known_titles") or []]
    for o_album, op in oplans:                 # tên bài của MỌI video tham khảo trong channel, không chỉ của album này
        ocg = (op.get("differentiation") or {}).get("copy_guard") or {}
        known += [(str(t), f"copy_guard {o_album}") for t in (ocg.get("titles") or []) + (ocg.get("hooks") or [])]
    bad_words = [str(x).lower() for x in (rules.get("avoid_words") or []) + (rules.get("heteronyms") or [])]
    o_chap = {}                                # 'luke 15' → [(album, slot)]
    o_edge_img = {}                            # hình ảnh chủ đạo của title track / bài kết của album khác
    for o_album, op in oplans:
        osl = sorted(op.get("slots") or [], key=lambda x: x.get("n", 0))
        for o in osl:
            for c in scripture_chapters(o.get("source_ref")):
                o_chap.setdefault(c, []).append((o_album, o.get("n")))
        for o in (osl[:1] + osl[-1:]) if osl else []:
            im = norm_text((o.get("imagery") or [None])[0])
            if im:
                o_edge_img.setdefault(im, []).append((o_album, o.get("n")))
    guard_titles = [norm_text(x) for x in (cg.get("titles") or [])] + [norm_text(x) for x in (cg.get("hooks") or [])]
    guard_brand = [norm_text(x) for x in (cg.get("branding") or [])]
    avoid = cg.get("source_avoid") or []
    s1 = slots[0]
    if s1.get("source") != "new":
        I.err("title_track", "slot 1 (title track) phải là bài mới (CLAUDE.md §3, §7.2)", [1])
    if s1.get("arc_role") != "anchor":
        I.err("title_track", "slot 1 phải có arc_role: anchor", [1])
    durations, lyrics_by = {}, {}
    for s in slots:
        n, w = s.get("n"), f"slot {s.get('n')}"
        title = s.get("title") or ""
        if not title:
            I.err("title", f"{w}: thiếu title", [n])
        if VI.search(title + (s.get("hook_phrase") or "")):
            I.err("language", f"{w}: title/hook có ký tự tiếng Việt", [n])
        if s.get("arc_role") not in ARC_ROLES:
            I.err("slot", f"{w}: arc_role '{s.get('arc_role')}' không hợp lệ ({sorted(ARC_ROLES)})", [n])
        for k, lo, hi in (("energy", 1, 10), ("valence", 1, 10)):
            if not isinstance(s.get(k), (int, float)) or not lo <= s[k] <= hi:
                I.err("slot", f"{w}: {k} phải là số {lo}–{hi}", [n])
        if not s.get("intro_type"):
            I.err("slot", f"{w}: intro_type trống", [n])
        if s.get("intro_length") not in INTRO_SECONDS:
            I.err("slot", f"{w}: intro_length phải là {list(INTRO_SECONDS)}", [n])
        try:
            durations[n] = secs(s.get("target_duration"))
        except ValueError as e:
            I.err("slot", f"{w}: {e}", [n])
        if durations.get(n) is None:
            I.err("slot", f"{w}: target_duration trống", [n])
        elif gen.get("duration", "custom") == "custom" and s.get("source") == "new" and not 10 <= durations[n] <= 360:
            I.err("duration", f"{w}: target_duration {s['target_duration']} ngoài 0:10–6:00 (giới hạn Custom duration của Suno)", [n])
        if s.get("source") not in ("new", "library"):
            I.err("slot", f"{w}: source phải là new | library", [n])
        if s.get("source") == "library":
            if not s.get("library_id"):
                I.err("library", f"{w}: source library nhưng thiếu library_id", [n])
            elif s["library_id"] not in {r.get("id") for r in catalog}:
                I.err("library", f"{w}: library_id {s['library_id']} không có trong catalog", [n])
        else:
            ct = cat_titles.get(norm_text(title))
            if ct:
                I.err("freshness", f"{w}: title trùng bài trong library ({ct})", [n])
        hook = norm_text(s.get("hook_phrase"))
        if s.get("source") == "new" and not hook:
            I.err("hook", f"{w}: hook_phrase trống", [n])
        if s.get("source") == "new":
            if hook and hook in cat_hooks:
                I.warn("freshness", f"{w}: hook trùng hook của bài library {cat_hooks[hook]}")
            for o_album, o in others:
                if norm_text(title) and norm_text(title) == norm_text(o.get("title")):
                    I.err("cross_plan", f"{w}: title trùng slot {o.get('n')} của album đang plan {o_album}", [n])
                elif hook and hook == norm_text(o.get("hook_phrase")):
                    I.warn("cross_plan", f"{w}: hook trùng slot {o.get('n')} của album đang plan {o_album}")
        for g in guard_titles:
            if g and (norm_text(title) == g or hook == g or (len(g.split()) >= 2 and (g in norm_text(title) or g in hook))):
                I.err("copy_guard", f"{w}: title/hook trùng copy_guard '{g}'", [n])
        for g in guard_brand:
            if g and g in norm_text(title):
                I.err("copy_guard", f"{w}: title chứa branding của kênh khác '{g}'", [n])
        if s.get("source") == "new":
            for t, src in known:
                loose = src.startswith("copy_guard") and len(norm_text(t).split()) < 3   # 'Praise Him', 'Yes Lord': chỉ bắt khi trùng hẳn
                for what, val in (("title", title), ("hook", s.get("hook_phrase"))):
                    if val and (norm_text(val) == norm_text(t) if loose else title_like(val, t)):
                        I.err("known_title", f"{w}: {what} '{val}' gần trùng bài có sẵn '{t}' ({src})", [n])
            hit = sorted({b for b in bad_words if re.search(rf"\b{re.escape(b)}\b", f"{title} {s.get('hook_phrase') or ''}", re.I)})
            if hit:
                I.warn("avoid_words", f"{w}: title/hook có {hit} (từ Suno hay tự chèn / đọc hai cách, rules.md §3)")
            if rules and final and not s.get("title_check"):
                I.err("title_check", f"{w}: chưa tra title + hook trên web (slot.title_check, rules.md §3)", [n])
            for c in sorted(scripture_chapters(s.get("source_ref"))):
                if o_chap.get(c):
                    I.warn("cross_plan", f"{w}: Kinh Thánh '{c}' đã dùng ở {', '.join(f'{a_} slot {m}' for a_, m in o_chap[c][:3])}")
            if n in (slots[0]["n"], slots[-1]["n"]):
                im = norm_text((s.get("imagery") or [None])[0])
                if im and o_edge_img.get(im):
                    I.warn("cross_plan", f"{w}: hình ảnh chủ đạo '{im}' trùng title track/bài kết của "
                                         f"{', '.join(f'{a_} slot {m}' for a_, m in o_edge_img[im][:3])}")
        ref = s.get("source_ref") or ""
        for av in avoid:
            if re.search(rf"\b{re.escape(str(av))}(?![\d:])", ref, re.I) or re.search(rf"\b{re.escape(str(av))}:", ref, re.I):
                I.err("copy_guard", f"{w}: source_ref '{ref}' nằm trong source_avoid ({av})", [n])
        if n == 1 and not s.get("opening_spec"):
            I.warn("title_track", "slot 1 chưa có opening_spec (timeline 15 s đầu của video, CLAUDE.md §3)")
        r = s.get("rounds") or ((gen.get("rounds") or {}).get("track01" if n == 1 else "others"))
        if s.get("source") == "new" and (not isinstance(r, int) or r < 1):
            I.err("rounds", f"{w}: rounds phải là số nguyên >= 1", [n])
        if n == 1 and isinstance(r, int) and r * 2 < int((qc.get("rules") or {}).get("min_candidates_anchor", 4)):
            I.err("rounds", f"slot 1: {r} lượt = {r * 2} clip < min_candidates_anchor", [1])
        if s.get("source") == "new":
            lp = track_path(album, s)
            ly = read_lyrics(lp)
            if ly is None:
                (I.err if final else I.warn)("lyrics", f"{w}: chưa có lyrics trong {rel(lp)} (## Lyrics → khối ```)")
            else:
                lyrics_by[n] = ly
    # --- luật giữa các bài (CLAUDE.md §7.2)
    bpms = {s["n"]: slot_bpm(plan, s) for s in slots if isinstance(slot_bpm(plan, s), (int, float)) and s["n"] != hslot}
    if bpms and max(bpms.values()) / min(bpms.values()) > TEMPO_BAND_MAX_RATIO:
        lo_n, hi_n = min(bpms, key=bpms.get), max(bpms, key=bpms.get)
        I.err("tempo_band", f"tempo các bài trải {bpms[lo_n]}–{bpms[hi_n]} (slot {lo_n}–{hi_n}, "
                            f"{(bpms[hi_n] / bpms[lo_n] - 1) * 100:.0f}% > {(TEMPO_BAND_MAX_RATIO - 1) * 100:.0f}%): một album = một dải tempo",
              [lo_n, hi_n])
    tr_ = tgt.get("tempo_range")
    if tr_ and len(tr_) == 2:
        if not tr_[0] <= (tempo.get("bpm") or 0) <= tr_[1]:
            I.err("tempo_range", f"sound.tempo.bpm {tempo.get('bpm')} ngoài target.tempo_range {tr_}")
        for s in slots:
            b = slot_bpm(plan, s)
            if s.get("bpm") and not tr_[0] <= b <= tr_[1]:
                (I.warn if s["n"] == hslot else I.err)("tempo_range", f"slot {s['n']}: bpm {b} ngoài target.tempo_range {tr_}"
                                                      + (" (bài điểm nhấn: được miễn)" if s["n"] == hslot else ""), [s["n"]])
    emax, bmax = tgt.get("energy_adjacent_max", 2), tgt.get("bpm_adjacent_max_pct", 8)
    for a_, b_ in zip(slots, slots[1:]):
        na, nb = a_["n"], b_["n"]
        if isinstance(a_.get("energy"), (int, float)) and isinstance(b_.get("energy"), (int, float)) and abs(a_["energy"] - b_["energy"]) > emax:
            (I.warn if "energy" in axes or hslot in (na, nb) else I.err)("energy_step", f"slot {na}→{nb}: energy {a_['energy']}→{b_['energy']} lệch > {emax}"
                                                     + (" (experiment energy)" if "energy" in axes else ""), [na, nb])
        ba, bb = slot_bpm(plan, a_), slot_bpm(plan, b_)
        if ba and bb and abs(bb / ba - 1) * 100 > bmax:
            (I.warn if hslot in (na, nb) else I.err)("bpm_step", f"slot {na}→{nb}: tempo {ba}→{bb} lệch {abs(bb / ba - 1) * 100:.0f}% > {bmax}%"
                                                     + (" (bài điểm nhấn)" if hslot in (na, nb) else ""), [na, nb])
        if a_.get("intro_type") and a_.get("intro_type") == b_.get("intro_type"):
            (I.warn if hslot in (na, nb) else I.err)("intro_repeat", f"slot {na}→{nb}: cùng intro_type '{a_['intro_type']}' (CLAUDE.md §4: transition phải đa dạng)", [na, nb])
        ia, ib = (a_.get("imagery") or [None])[0], (b_.get("imagery") or [None])[0]
        if ia and ia == ib:
            I.warn("imagery", f"slot {na}→{nb}: cùng hình ảnh chủ đạo '{ia}'")
    lens = [s.get("intro_length") for s in slots]
    for i in range(len(lens) - 2):
        if lens[i] and lens[i] == lens[i + 1] == lens[i + 2]:
            I.warn("intro_repeat", f"slot {i + 1}–{i + 3}: 3 bài liền cùng intro_length '{lens[i]}'")
    en = [s.get("energy") or 0 for s in slots]
    peak = [s["n"] for s in slots if (s.get("energy") or 0) == max(en)]
    if tgt.get("peak_slots") and not set(peak) & set(tgt["peak_slots"]):
        I.warn("arc", f"energy cao nhất ở slot {peak}, ngoài peak_slots {tgt['peak_slots']}")
    if len(slots) > 2 and en[-1] > min(en[1:-1] or [en[-1]]):
        I.warn("arc", f"bài cuối energy {en[-1]} chưa phải thấp nhất (CLAUDE.md §4: kết thúc bình yên)")
    by_slot = {s["n"]: s for s in slots}
    hooks = {s["n"]: norm_text(s.get("hook_phrase")) for s in slots if s.get("hook_phrase")}
    for n, h in hooks.items():
        for m, h2 in hooks.items():
            if m > n and h == h2:
                I.err("hook_repeat", f"slot {n} và {m} cùng hook '{h}'", [n, m])
        for m, s in ((s["n"], s) for s in slots):
            if m != n and h == norm_text(s.get("title")) and n != 1:
                I.err("hook_repeat", f"hook slot {n} = title slot {m}", [n, m])
        if cat_titles.get(h) and n != 1 and cat_titles[h] != by_slot[n].get("library_id"):
            I.err("hook_repeat", f"hook slot {n} trùng title bài library {cat_titles[h]}", [n])
    # mỗi album cũ góp tối đa N bài: đếm theo mọi album bài đã xuất hiện (cột Albums), không chỉ album gốc
    cat_by_id = {r.get("id"): r for r in catalog}
    from_album = {}
    for s in slots:
        if s.get("source") == "library" and s.get("library_id") in cat_by_id:
            for a in (cat_by_id[s["library_id"]].get("albums") or "").split(","):
                if a.strip() and a.strip() != album.name:
                    from_album.setdefault(a.strip(), []).append(s["n"])
    omax = tgt.get("reuse_per_album_max", 2)
    for a, ns in from_album.items():
        if len(ns) > omax:
            I.err("album_overlap", f"slot {ns}: {len(ns)} bài đã có trong album {a} (> {omax}, CLAUDE.md §6: album mới không lặp album cũ)", ns)
    # tổng số bài lấy từ library: tối đa N, còn lại tạo mới
    rmax = tgt.get("reuse_total_max", 4)
    lib = [s["n"] for s in slots if s.get("source") == "library"]
    if len(lib) > rmax:
        I.err("reuse_total", f"slot {lib}: {len(lib)} bài library (> {rmax}, CLAUDE.md §6: tối đa {rmax} bài từ album cũ, còn lại tạo mới)", lib)
    # --- lời
    lr = plan.get("lyrics_rules") or {}
    wpm_lo, wpm_hi = (tgt.get("words_per_min") or [0, 0])[:2]
    by_n = {s["n"]: s for s in slots}
    for n, ly in lyrics_by.items():
        s, w = by_n[n], f"slot {n}"
        if VI.search(ly):
            I.err("language", f"{w}: lyrics có ký tự tiếng Việt", [n])
        if len(ly) > 5000:
            I.err("lyrics", f"{w}: lyrics {len(ly)} ký tự (> 5000, giới hạn Suno)", [n])
        elif len(ly) > int(lr.get("max_chars", 3000)):
            I.warn("lyrics", f"{w}: lyrics {len(ly)} ký tự (> max_chars {lr.get('max_chars', 3000)})")
        if not re.search(r"^\s*\[", ly, re.M):
            I.warn("lyrics", f"{w}: lyrics không có tag [Section] nào")
        body = norm_text(re.sub(r"\[[^\]]*\]", " ", ly))
        if s.get("hook_phrase") and norm_text(s["hook_phrase"]) not in body:
            I.err("hook_missing", f"{w}: hook_phrase '{s['hook_phrase']}' không có trong lyrics", [n])
        declared = {str(x) for x in s.get("echo_tracks") or []}
        for m, o in by_n.items():
            if m == n:
                continue
            for what in (o.get("title"), o.get("hook_phrase")):
                t = norm_text(what)
                if t and len(t.split()) >= 3 and t in body:
                    oid = f"{(plan.get('album') or {}).get('id_prefix')}-{m:02d}"
                    if str(m) not in declared and oid not in declared:
                        I.err("echo", f"{w}: lời nhắc title/hook của slot {m} ('{what}') mà echo_tracks chưa khai báo", [n, m])
                    elif abs(m - n) == 1:
                        I.err("echo", f"{w}: bài echo slot {m} đặt liền kề (CLAUDE.md §7.2)", [n, m])
        for g in (cg.get("titles") or []):
            if len(norm_text(g).split()) >= 2 and norm_text(g) in body:
                I.warn("copy_guard", f"{w}: lời chứa title của kênh khác '{g}'")
        lines = [l for l in ly.splitlines() if l.strip() and not l.strip().startswith(("[", "("))]
        for t, src in known:
            nt = norm_text(t)
            if len(nt.split()) >= (3 if src.startswith("copy_guard") else 2) and any(f" {nt} " in f" {norm_text(l)} " for l in lines):
                I.warn("known_title", f"{w}: lời chứa nguyên cụm '{t}' ({src})")
        hit = sorted({b for b in bad_words if re.search(rf"\b{re.escape(b)}\b", " ".join(lines), re.I)})
        if hit:
            I.warn("avoid_words", f"{w}: lời có {hit} (rules.md §3: viết lại câu)")
        d = durations.get(n)
        lyr = rules.get("lyrics") or {}
        if d and lyr.get("words_per_beat_max") and slot_bpm(plan, s):
            bpm_, nw = slot_bpm(plan, s), len(lyric_words(ly))
            sung_s = max(d - float(lyr.get("sung_allowance_s", 55)), 60)
            wpb = nw / (sung_s * bpm_ / 60)
            cap = int(float(lyr["words_per_beat_max"]) * bpm_ / 60 * sung_s)
            msg = (f"{w}: {nw} từ ≈ {wpb:.2f} từ/nhịp ở {bpm_} BPM, {s.get('target_duration')} "
                   f"(rules.md §2: tối đa {lyr['words_per_beat_max']} ≈ {cap} từ, nên ≤ {lyr.get('words_per_beat_warn')})")
            if wpb > float(lyr["words_per_beat_max"]):
                (I.warn if "density" in axes else I.err)("density", msg, [n])
            elif lyr.get("words_per_beat_warn") and wpb > float(lyr["words_per_beat_warn"]):
                I.warn("density", msg)
        if d and wpm_hi and not lyr:
            sung = max(d - INTRO_SECONDS.get(s.get("intro_length"), 10) - 25, 60) / 60
            wpm = len(lyric_words(ly)) / sung
            if wpm < wpm_lo * 0.75 or wpm > wpm_hi * 1.25:
                I.warn("density", f"{w}: ~{wpm:.0f} từ/phút (ước lượng từ {len(lyric_words(ly))} từ, {s.get('target_duration')}) "
                       f"ngoài {wpm_lo}–{wpm_hi} → lời quá {'thưa' if wpm < wpm_lo else 'dày'} cho thời lượng")
    ref_wpm = ((refc.get("lyric_density") or {}).get("words_per_min_sung")) if rf else None
    if ref_wpm and rf.get("words_per_min_max_dev_pct") and lyrics_by and "density" not in axes:
        sung_allow = float((rules.get("lyrics") or {}).get("sung_allowance_s", 55))
        wpms = sorted(len(lyric_words(ly)) / max(durations.get(n, 0) - sung_allow, 60) * 60
                      for n, ly in lyrics_by.items() if durations.get(n) and n != hslot)
        if wpms:
            med = wpms[len(wpms) // 2]
            dev = (med / ref_wpm - 1) * 100
            if abs(dev) > rf["words_per_min_max_dev_pct"]:
                I.warn("reference_follow", f"mật độ lời ~{med:.0f} từ/phút hát (trung vị, ước lượng) lệch {dev:+.0f}% so với video tham khảo "
                                           f"{ref_wpm} > ±{rf['words_per_min_max_dev_pct']}% (rules.md §1b)")
    # --- tổng
    tot = sum(v for v in durations.values() if v)
    lo, hi = (tgt.get("duration_min") or [0, 10 ** 6])[:2]
    if tot and not lo * 60 <= tot <= hi * 60 * 1.08:
        I.warn("duration", f"tổng {mmss(tot)} (chưa cắt ghép) ngoài {lo}–{hi} phút")
    tr = tgt.get("track_duration")
    if tr:
        a_, b_ = secs(tr[0]), secs(tr[1])
        for n, d in durations.items():
            if d and not a_ <= d <= b_:
                I.warn("duration", f"slot {n}: {mmss(d)} ngoài {tr[0]}–{tr[1]}")
    credits, cpg = 0, gen.get("credits_per_generation") or {}
    for s in slots:
        if s.get("source") == "new":
            mx = (s.get("generation_overrides") or {}).get("max_mode", gen.get("max_mode", True))   # Max bật/tắt theo từng bài
            per = int(cpg.get("max", 20)) if mx else int(cpg.get("normal", 10))
            credits += (s.get("rounds") or (gen.get("rounds") or {}).get("track01" if s["n"] == 1 else "others") or 0) * per
    if (gen.get("budget_max_credits") or 0) > CREDITS_CEILING:
        I.err("budget", f"budget_max_credits {gen['budget_max_credits']} > {CREDITS_CEILING} (trần album, CLAUDE.md §4)")
    rd = gen.get("rounds") or {}
    s1 = next((s for s in slots if s["n"] == 1), {})
    if gen.get("max_mode") or (rd.get("others") or 0) > LEAN_ROUNDS["others"] or (rd.get("track01") or 0) > LEAN_ROUNDS["track01"] \
            or not (s1.get("generation_overrides") or {}).get("max_mode"):
        I.warn("credits_policy", f"khác luật credits CLAUDE.md §4 (max_mode false, slot 1 generation_overrides.max_mode true, "
                                 f"rounds {LEAN_ROUNDS}); cần chủ kênh đồng ý")
    if gen.get("budget_max_credits") and credits > gen["budget_max_credits"]:
        I.warn("budget", f"credits dự kiến {credits} > budget_max_credits {gen['budget_max_credits']}")
    for k, hi_ in (("weirdness", 100), ("audio_influence", 100), ("variety", 4)):
        if not isinstance(gen.get(k), int) or not 0 <= gen[k] <= hi_:
            I.err("generation", f"generation.{k} phải là MỘT số nguyên 0–{hi_}")
    si = gen.get("style_influence") or {}
    if not all(isinstance(si.get(k), int) and 0 <= si[k] <= 100 for k in ("track01", "others")):
        I.err("generation", "generation.style_influence.{track01, others} phải là số nguyên 0–100")
    if not (qc.get("style") or {}).get("positive") or not (qc.get("style") or {}).get("negative"):
        I.err("qc", "qc.style.positive/negative trống (verification-audio cần để kiểm thể loại)")
    if not qc.get("references"):
        I.warn("qc", "qc.references trống → verification chưa có baseline tới khi chốt slot 1")
    for r in qc.get("references") or []:
        if not list(album.glob(r)) and not r.startswith("audio/tracks"):
            I.warn("qc", f"qc.references '{r}' chưa khớp file nào")
    if final:
        if not (plan.get("library_check") or {}).get("done"):
            I.err("library", "library_check.done chưa có (CLAUDE.md §7.2: kiểm tra library trước khi tạo mới)")
        for q in plan.get("open_questions") or []:
            if q.get("blocking") and not q.get("answer"):
                I.err("open_question", f"câu hỏi blocking chưa trả lời: {q.get('id')} {q.get('q')}")
    I.credits, I.total = credits, tot
    return I


def cmd_validate(a):
    album = album_dir(a.album)
    plan = load_plan(album)
    I = validate(plan, album, a.final)
    for m in I.warns:
        print(f"⚠ {m}")
    for m in I.waived:
        print(f"· (waived) {m}")
    for m in I.errors:
        print(f"✖ {m}")
    print(f"\n{len(plan.get('slots') or [])} bài · tổng {mmss(I.total)} · ~{I.credits} credits · status {plan.get('status')}"
          + (" · kiểm tra FINAL" if a.final else ""))
    if I.errors:
        sys.exit(1)
    print("✔ plan hợp lệ" + (" và đủ điều kiện duyệt" if a.final else ""))


# ---------------------------------------------------------------- build
def plan_fingerprint(plan: dict, album: Path) -> str:
    """Dấu vân tay nội dung được duyệt: plan (trừ status) + lyrics các bài mới. Đổi sau khi duyệt → phải duyệt lại."""
    core = {k: v for k, v in plan.items() if k not in ("status", "status_log")}
    ly = {s["n"]: read_lyrics(track_path(album, s)) for s in plan.get("slots") or [] if s.get("source") == "new"}
    return hashlib.sha256(json.dumps([core, ly], sort_keys=True, default=str).encode()).hexdigest()[:12]


def approved_fingerprint(plan: dict) -> str | None:
    for e in reversed(plan.get("status_log") or []):
        if e.get("status") == "approved":
            return e.get("fingerprint")
    return None


def generation_started(album: Path) -> list[str]:
    f = album / "audio" / "raw_tracks" / "manifest.json"
    if not f.exists():
        return []
    man = json.loads(f.read_text())
    return [g["id"] for g in man.get("generations") or [] if g.get("status") not in ("prepared", "abandoned")]


def yscalar(v) -> str:
    if v is None:
        return ""
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, str) and (v == "" or re.search(r"[:#\[\]{},&*!|>'\"%@`]|^\s|\s$", v) or v.lower() in ("yes", "no", "true", "false", "null", "on", "off")):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def set_fm(text: str, updates: dict) -> str:
    """Đổi `key: value` trong front matter, giữ comment cuối dòng (cùng kiểu verify.py set_front_matter)."""
    head, sep, body = text.partition("\n---\n")
    for k, v in updates.items():
        val = yscalar(v)
        m = re.search(rf"^{re.escape(k)}:[^\n]*$", head, re.M)
        if m:
            cm = re.search(r"\s+#.*$", m.group(0))
            line = f"{k}:" + (f" {val}" if val else "") + (cm.group(0) if cm else "")
            head = head[:m.start()] + line + head[m.end():]
        else:
            head += f"\n{k}:" + (f" {val}" if val else "")
    return head + sep + body


def replace_block(text: str, begin: str, end: str, content: str) -> str:
    pat = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.S)
    block = f"{begin}\n{content.rstrip()}\n{end}"
    return pat.sub(lambda _: block, text) if pat.search(text) else None


def brief_md(plan: dict, s: dict) -> str:
    tgt = (plan.get("target") or {}).get("vocal") or {}
    k = "track01" if s["n"] == 1 else "others"
    L = [f"- **Vai trò:** {s.get('arc_role')} · **Cảm xúc:** {s.get('emotion')} · **Chủ đề:** {s.get('theme')}"
         + (f" · **Nguồn:** {s['source_ref']}" if s.get("source_ref") else ""),
         f"- **Energy** {s.get('energy')} · **Valence** {s.get('valence')} · **Tempo** {slot_bpm(plan, s)} "
         f"({(plan.get('sound') or {}).get('tempo', {}).get('meter')}) · **Dài** {s.get('target_duration')}",
         f"- **Mở bài:** {s.get('intro_type')} / {s.get('intro_length')} · giọng trước {tgt.get('first_voice_max_s', {}).get(k)} s, "
         f"lời trước {tgt.get('first_lyric_max_s', {}).get(k)} s",
         f"- **Hook:** \"{s.get('hook_phrase')}\" · **Hình ảnh:** {', '.join(s.get('imagery') or [])}"
         + (f" · **Echo:** {s.get('echo_tracks')}" if s.get("echo_tracks") else ""),
         f"- **Arrangement:** {s.get('arrangement') or '—'}"]
    if s.get("opening_spec"):
        L.append("- **15 s đầu của video:** " + " → ".join(f"{o.get('t')}: {o.get('event')}" for o in s["opening_spec"]))
    if s.get("gate"):
        L.append("- **Gate:** " + " · ".join(str(g) for g in s["gate"]))
    if s.get("reference_recipe"):
        L.append("- **Tham khảo đã làm thế nào (học cách, không chép):** " + " · ".join(str(g) for g in s["reference_recipe"]))
    if s.get("notes"):
        L.append(f"- **Ghi chú:** {s['notes']}")
    return "\n".join(L)


def track_updates(plan: dict, s: dict, album: Path) -> dict:
    alb, snd = plan["album"], plan.get("sound") or {}
    return {"id": f"{alb['id_prefix']}-{s['n']:02d}", "title": s.get("title"), "origin_album": album.name,
            "track_no": s["n"], "genre_family": snd.get("genre_family"), "subgenre": snd.get("subgenre"),
            "time_signature": (snd.get("tempo") or {}).get("meter"),
            "vocal_persona": (plan.get("identity") or {}).get("vocal_persona"),
            "band_profile": (plan.get("identity") or {}).get("band_profile"),
            "style_prompt_version": (snd.get("style") or {}).get("version"), "energy": s.get("energy"),
            "valence": s.get("valence"), "emotion": s.get("emotion"), "theme": s.get("theme"), "arc_role": s.get("arc_role"),
            "intro_type": s.get("intro_type"), "hook_phrase": s.get("hook_phrase"), "lyric_keywords": s.get("lyric_keywords") or [],
            "imagery": s.get("imagery") or [], "echo_tracks": s.get("echo_tracks") or [], "target_bpm": slot_bpm(plan, s),
            "target_duration": s.get("target_duration"), "source_ref": s.get("source_ref")}


def build_tracks(plan: dict, album: Path, log: list):
    tmpl = (TEMPLATES / "track.md").read_text()
    catalog = {r.get("id"): r for r in catalog_rows(plan["album"]["channel"])}
    for s in plan["slots"]:
        n = s["n"]
        want = album / "tracks" / f"{n:02d}-{slugify(s.get('title'))}.md"
        old = next((p for p in main_track_files(album, n) if p != want), None)
        if old and want.exists():
            log.append(f"⚠ slot {n}: có cả {old.name} và {want.name} → không đổi tên file nào; gộp/xoá bản thừa bằng tay")
        elif old:
            if fm_value(old.read_text(), "audio"):
                log.append(f"⚠ slot {n}: title đổi nhưng {old.name} đã có audio → giữ tên cũ, không sửa")
                continue
            old.rename(want)
            log.append(f"↻ {old.name} → {want.name} (title đổi)")
        if s.get("source") == "library":
            if want.exists():
                continue
            row = catalog.get(s.get("library_id")) or {}
            m = re.search(r"\]\(([^)]+)\)", row.get("file", ""))
            src_md = (ROOT / "channel" / plan["album"]["channel"] / "library" / m.group(1)).resolve() if m else None
            if not src_md or not src_md.exists():
                log.append(f"✖ slot {n}: không tìm thấy track md của {s.get('library_id')} trong catalog")
                continue
            text = src_md.read_text()
            av = fm_value(text, "audio")
            audio = (src_md.parent.parent / av).resolve() if av else None
            text = set_fm(text, {"track_no": n, "audio": Path(os.path.relpath(audio, album)).as_posix() if audio else ""})
            want.write_text(text)
            log.append(f"+ {rel(want)} (library {s.get('library_id')}, audio trỏ về album gốc)")
            continue
        if want.exists():
            text = want.read_text()
            if fm_value(text, "audio"):
                log.append(f"· {want.name}: đã có audio (bài đã chọn) → không sửa")
                continue
            new = set_fm(text, track_updates(plan, s, album))
            blk = replace_block(new, "<!-- album-plan:brief:begin -->", "<!-- album-plan:brief:end -->", brief_md(plan, s))
            new = blk if blk is not None else new
            if new != text:
                want.write_text(new)
                log.append(f"~ {rel(want)} (front matter + brief)")
            continue
        text = set_fm(tmpl, track_updates(plan, s, album))
        head, sep, _ = text.partition("\n---\n")
        body = (f"\n# {n:02d} — {s.get('title')}\n\n## Brief (album-plan)\n\n<!-- album-plan:brief:begin -->\n{brief_md(plan, s)}\n"
                f"<!-- album-plan:brief:end -->\n\n## Arrangement tags / ghi chú generate\n\n{s.get('arrangement') or ''}\n\n"
                f"## Lyrics (bản đã nhập vào Suno)\n\n```\n```\n")
        want.write_text(head + sep + body)
        log.append(f"+ {rel(want)}")


def build_generation(plan: dict, album: Path, log: list):
    gen, snd, ident = plan["generation"], plan["sound"], plan["identity"]
    bpm0 = snd["tempo"]["bpm"]
    new = [s for s in plan["slots"] if s.get("source") == "new"]
    out_slots = []
    for s in new:
        ov = {}
        if s["n"] == 1 and gen["style_influence"]["track01"] != gen["style_influence"]["others"]:
            ov["style_influence"] = gen["style_influence"]["track01"]
        if gen.get("duration", "custom") == "custom":
            ov["duration"] = secs(s["target_duration"])
        if slot_bpm(plan, s) != bpm0:
            ov["bpm"] = slot_bpm(plan, s)
        ov.update(s.get("generation_overrides") or {})
        ly = read_lyrics(album / rel_track(album, s))
        out_slots.append({"n": s["n"], "title": s["title"], "track": rel_track(album, s),
                          "lyrics_sha8": hashlib.sha256(ly.encode()).hexdigest()[:8] if ly else None,
                          "rounds": s.get("rounds") or gen["rounds"]["track01" if s["n"] == 1 else "others"],
                          "instrumental": False, "overrides": ov, "variants": s.get("variants") or [],
                          "notes": f"{s.get('arc_role')} · {s.get('emotion')} · E{s.get('energy')} · {s.get('intro_type')}/{s.get('intro_length')}"})
    g = {"schema_version": 1, "album": album.name, "status": "draft",
         "source": {"plan": "plan.yaml", "idea": plan["sources"].get("idea"), "research": plan["sources"].get("research") or []},
         "budget": {"max_credits": gen["budget_max_credits"], "credits_per_generation": gen["credits_per_generation"]},
         "gates": {"anchor_first": gen.get("anchor_first", True), "confirm_each_generation": False},
         "style": {"version": snd["style"]["version"], "text": re.sub(r"\s+", " ", snd["style"]["text"]).strip(),
                   "exclude": snd["style"]["exclude"]},
         "defaults": {"model": gen["model"], "voice": ident.get("voice"), "vocal_gender": ident.get("vocal_gender"),
                      "max_mode": gen["max_mode"], "duration": "auto", "variety": gen["variety"], "weirdness": gen["weirdness"],
                      "style_influence": gen["style_influence"]["others"], "audio_influence": gen["audio_influence"],
                      "personalize": "off", "bpm": bpm0},
         "order": [s["n"] for s in new],
         "slots": out_slots,
         "changes": []}
    f = album / "generation.yaml"
    f.write_text("# SINH TỰ ĐỘNG bởi album-plan build từ plan.yaml. Sửa plan.yaml rồi build lại.\n"
                 "# Khi suno-generate đã bắt đầu (manifest có lượt đã submit), plan đóng băng: thay đổi lúc generate ghi thẳng ở đây\n"
                 "# (slot overrides / changes), build sẽ không ghi đè nữa.\n"
                 + yaml.safe_dump(g, sort_keys=False, allow_unicode=True, width=120))
    log.append(f"+ {rel(f)} ({len(new)} bài mới, order {g['order']})")


def rel_track(album: Path, s: dict) -> str:
    return f"tracks/{s['n']:02d}-{slugify(s['title'])}.md"


def build_selection(plan: dict, album: Path, log: list):
    f = album / "selection.yaml"
    old = yaml.safe_load(f.read_text()) if f.exists() else {}
    qc, tgt = plan["qc"], plan.get("target") or {}
    tr = tgt.get("track_duration")
    rules = dict(qc.get("rules") or {})
    if tr and "duration_range" not in rules:
        rules["duration_range"] = [max(secs(tr[0]) - 60, 60), secs(tr[1]) + 90]
    sel = {}
    if old.get("anchor"):
        sel["anchor"] = old["anchor"]
    sel.update({"references": qc.get("references") or ["audio/tracks/*.wav"],
                "tempo": {"target_bpm": plan["sound"]["tempo"]["bpm"], "meter": plan["sound"]["tempo"]["meter"]},
                "style": qc["style"], "rules": rules,
                "slots": {s["n"]: {"track": rel_track(album, s), "energy": s.get("energy")} for s in plan["slots"]}})
    if qc.get("thresholds"):
        sel["thresholds"] = qc["thresholds"]
    v = tgt.get("vocal") or {}
    pt = {"tempo_range": tgt.get("tempo_range"),
          "vocal": {k: v.get(k) for k in ("vocal_at_s", "first_voice_max_s", "first_lyric_max_s", "first_hook_max_s", "f0_median_hz",
                                          "singer_similarity_min", "singer_similarity_ref") if v.get(k) is not None},
          "drums_in_s_max": tgt.get("drums_in_s_max"), "loudness": tgt.get("loudness"),
          "slot_checks": {s["n"]: {k: x for k, x in {"gate": s.get("gate") or None}.items() if x}
                          for s in plan["slots"] if s.get("gate")},
          "intro_types": qc.get("intro_types") or None,
          "intro_type_by_slot": {s["n"]: s.get("intro_type") for s in plan["slots"]},
          "extra_checks": qc.get("extra_checks") or None}
    pt = {k: x for k, x in pt.items() if x}
    if pt:
        sel["plan_targets"] = pt
        unread = [k for k in pt if k not in ("vocal", "loudness", "tempo_range")]
        log.append("· selection.yaml plan_targets: verification-audio đọc vocal.{vocal_at_s, first_voice/lyric/hook_max_s} + "
                   "loudness.first15s_max_below_body_db (gate Track 01) + tempo_range (dải tempo của check tempo)"
                   + (f"; chưa đọc: {', '.join(unread)} (giữ làm brief)" if unread else ""))
    f.write_text("# SINH TỰ ĐỘNG bởi album-plan build (plan.yaml → qc, sound.tempo, slots). Dùng bởi verification-audio.\n"
                 "# `anchor` do verify.py accept --slot 1 điền; build giữ nguyên giá trị đó.\n"
                 "# tempo.target_bpm = tempo mục tiêu của plan (felt), cũng là số ghi trong Style prompt.\n"
                 "# plan_targets = mục tiêu đo được của plan; verify đọc phần gate Track 01 (xem album-plan bridge.md §4).\n"
                 + yaml.safe_dump(sel, sort_keys=False, allow_unicode=True, width=120))
    log.append(f"+ {rel(f)}" + (" (giữ anchor)" if old.get("anchor") else ""))


def summary_md(plan: dict, album: Path, I: Issues | None = None) -> str:
    snd, alb = plan.get("sound") or {}, plan.get("album") or {}
    t = snd.get("tempo") or {}
    L = [f"**{alb.get('title_working')}** · {len(plan.get('slots') or [])} bài · {t.get('meter')} ~{t.get('bpm')} BPM (felt) · "
         f"persona `{(plan.get('identity') or {}).get('vocal_persona')}` · Voice "
         f"{((plan.get('identity') or {}).get('voice') or {}).get('name', '—')} · style `{(snd.get('style') or {}).get('version')}`",
         "", "| # | Title | Vai trò | Cảm xúc | E | V | BPM | Mở bài | Dài | Hook | Nguồn | Lượt |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    gen = plan.get("generation") or {}
    for s in plan.get("slots") or []:
        r = "library" if s.get("source") == "library" else (s.get("rounds") or (gen.get("rounds") or {}).get("track01" if s["n"] == 1 else "others"))
        L.append(f"| {s['n']:02d} | {s.get('title')} | {s.get('arc_role')} | {s.get('emotion')} | {s.get('energy')} | {s.get('valence')} | "
                 f"{slot_bpm(plan, s)} | {s.get('intro_type')} / {s.get('intro_length')} | {s.get('target_duration')} | "
                 f"{s.get('hook_phrase')} | {s.get('source_ref') or s.get('library_id') or ''} | {r} |")
    en = " → ".join(str(s.get("energy")) for s in plan.get("slots") or [])
    L += ["", f"Energy: {en}"]
    if I is not None:
        hl_ = plan.get("highlight") or {}
        L.append(f"Bài điểm nhấn: slot {hl_.get('slot')} · {hl_.get('axis')} · {hl_.get('what')} · single: {hl_.get('single')}" if hl_ else "Bài điểm nhấn: CHƯA CÓ (rules.md §1b)")
        L.append(f"Voice: {((plan.get('identity') or {}).get('voice') or {}).get('name')} · tempo {((plan.get('sound') or {}).get('tempo') or {}).get('bpm')}")
        L.append(f"Tổng (chưa cắt ghép): {mmss(I.total)} · credits dự kiến ~{I.credits} / trần {gen.get('budget_max_credits')}")
    qs = [q for q in plan.get("open_questions") or [] if not q.get("answer")]
    if qs:
        L += ["", "Câu hỏi còn mở:"] + [f"- {'**[blocking]** ' if q.get('blocking') else ''}{q.get('id')}: {q.get('q')}" for q in qs]
    return "\n".join(L)


def build_album_md(plan: dict, album: Path, I: Issues, log: list):
    f = album / "album.md"
    snd, ident = plan.get("sound") or {}, plan.get("identity") or {}
    auto = "\n".join([
        f"- **Trạng thái plan:** {plan.get('status')} · nguồn: {plan['sources'].get('idea') or ''} {', '.join(plan['sources'].get('research') or [])}",
        f"- **Thể loại:** {snd.get('genre_family')} / {snd.get('subgenre')}",
        f"- **Vocal persona:** `{ident.get('vocal_persona')}` · **Band:** `{ident.get('band_profile')}` · **Style prompt:** `{(snd.get('style') or {}).get('version')}`",
        "", "## Concept", "", str(plan.get("concept") or "").strip(), "",
        "## Style prompt", "", "```", re.sub(r"\s+", " ", (snd.get("style") or {}).get("text") or "").strip(), "```",
        f"Exclude: `{(snd.get('style') or {}).get('exclude')}` · `{{bpm}}` = tempo từng bài trong bảng dưới", "",
        "## Tracklist & energy curve", "", summary_md(plan, album, I), "",
        "## Khác biệt so với nguồn tham khảo", "",
        *[f"- Giữ: {x}" for x in (plan.get("differentiation") or {}).get("keep") or []],
        *[f"- Đổi: {x}" for x in (plan.get("differentiation") or {}).get("change") or []]])
    if f.exists():
        text = f.read_text()
        new = replace_block(text, AUTO_BEGIN, AUTO_END, auto)
        if new is None:
            log.append(f"⚠ {rel(f)} đã có nhưng không có khối album-plan → không ghi đè; thêm 2 dòng marker nếu muốn tự cập nhật")
            return
    else:
        new = (f"# Album {plan['album']['number']:03d} — {plan['album']['title_working']}\n\n{AUTO_BEGIN}\n{auto}\n{AUTO_END}\n\n"
               "## Title track & 10–15 giây đầu (CLAUDE.md mục 3)\n\n- [ ] Title track là bản tốt nhất trong nhiều candidate\n"
               "- [ ] 10–15 giây đầu của video có giọng/hook/motif đặc trưng, không trống, không nhỏ hơn thân bài quá nhiều\n"
               "- [ ] Cách mở khác các album trước của kênh\n\n## Ghi chú\n\n")
    f.write_text(new)
    log.append(f"+ {rel(f)}")


def cmd_themes(a):
    """Bảng mọi album của channel để chọn concept/tempo/cách mở CHƯA CÓ (rules.md §1, §4): trước khi plan album mới."""
    base = ROOT / "channel" / a.channel / "albums"
    print(f"# Themes — {a.channel} ({date.today()})\n")
    for d in sorted(x for x in base.iterdir() if x.is_dir()):
        pf = d / "plan.yaml"
        if not pf.exists():
            mds = sorted((d / "tracks").glob("[0-9][0-9]-*.md"))
            titles = [fm_value(m.read_text(), "title") for m in mds if "." not in m.name[:-3]]
            print(f"## {d.name} (không có plan.yaml)\n- bài: {' · '.join(t for t in titles if t)}\n")
            continue
        p = yaml.safe_load(pf.read_text()) or {}
        sl = sorted(p.get("slots") or [], key=lambda x: x.get("n", 0))
        if not sl:
            continue
        s1, last = sl[0], sl[-1]
        bp = [b for b in (slot_bpm(p, x) for x in sl) if isinstance(b, (int, float))]
        t = (p.get("sound") or {}).get("tempo") or {}
        exp = p.get("experiment") or {}
        idea = yaml.safe_load((d / "idea.yaml").read_text()) if (d / "idea.yaml").exists() else {}
        tb = ((idea or {}).get("packaging") or {}).get("thumbnail_brief")
        thumb = ws(" · ".join(str(v) for v in tb.values() if v) if isinstance(tb, dict) else tb)
        cut = lambda x, k=170: (x[:k] + "…") if len(x) > k else x
        print(f"## {d.name} ({p.get('status')}) · {len(sl)} bài")
        print(f"- concept: {cut(ws(p.get('concept')))}")
        print(f"- tempo: {t.get('bpm')} {t.get('meter') or ''} (bài {min(bp) if bp else '?'}–{max(bp) if bp else '?'}) · "
              f"giọng: {(p.get('identity') or {}).get('vocal_persona')} · experiment: "
              f"{(sorted(exp.get('axes') or []), cut(ws(exp.get('what')), 90)) if exp else '—'}")
        print(f"- title track: \"{s1.get('title')}\" — hook \"{s1.get('hook_phrase')}\" — mở {s1.get('intro_type')}/{s1.get('intro_length')} — "
              f"biến thể {[v.get('name') for v in s1.get('variants') or []]} — hình ảnh {(s1.get('imagery') or [None])[0]}")
        print(f"- bài kết: \"{last.get('title')}\" — hook \"{last.get('hook_phrase')}\" — mở {last.get('intro_type')}/{last.get('intro_length')} — "
              f"hình ảnh {(last.get('imagery') or [None])[0]}")
        print(f"- Kinh Thánh: {' · '.join(sorted({c for x in sl for c in scripture_chapters(x.get('source_ref'))})) or '—'}")
        print(f"- hình ảnh chủ đạo: {' · '.join(str((x.get('imagery') or ['-'])[0]) for x in sl)}")
        print(f"- library: {[x.get('library_id') for x in sl if x.get('source') == 'library'] or '—'}")
        hl_ = p.get("highlight") or {}
        print(f"- bài điểm nhấn: {('slot ' + str(hl_.get('slot')) + ' · ' + str(hl_.get('axis')) + ' · ' + cut(ws(hl_.get('what')), 90)) if hl_ else '—'} · "
              f"Voice: {((p.get('identity') or {}).get('voice') or {}).get('name')}")
        print(f"- thumbnail: {cut(thumb) or '—'}\n")


def cmd_build(a):
    album = album_dir(a.album)
    plan = load_plan(album)
    started = generation_started(album)
    if started and not a.force:
        die(f"suno-generate đã chạy ({', '.join(started[:4])}…): plan đóng băng. Thay đổi lúc này ghi trong generation.yaml "
            "(slot overrides + changes) hoặc lyrics trong track md. --force chỉ khi người dùng muốn làm lại plan")
    I = validate(plan, album, final=False)
    if I.errors:
        for m in I.errors:
            print(f"✖ {m}")
        die("plan còn lỗi → sửa plan.yaml trước khi build")
    log = []
    from channel_tools import sync_assets
    sync_assets(album, log)
    build_tracks(plan, album, log)
    build_generation(plan, album, log)
    build_selection(plan, album, log)
    build_album_md(plan, album, I, log)
    if plan.get("status") == "approved":
        if approved_fingerprint(plan) == plan_fingerprint(plan, album):
            set_top_scalar(album / "generation.yaml", "status", "approved")
        else:
            set_top_scalar(album / "plan.yaml", "status", "draft")
            append_status_log(album / "plan.yaml", {"date": str(date.today()), "status": "draft", "by": "album-plan build",
                                                   "note": "plan/lyrics đổi sau khi duyệt → cần duyệt lại"})
            log.append("⚠ plan hoặc lyrics đã đổi sau khi duyệt → status về draft (plan + generation.yaml). Cho người dùng xem lại rồi approve")
    print("\n".join(log))
    for m in I.warns:
        print(f"⚠ {m}")
    print(f"\n✔ build xong ({mmss(I.total)}, ~{I.credits} credits)")


def cmd_summary(a):
    album = album_dir(a.album)
    plan = load_plan(album)
    I = validate(plan, album, final=False)
    print(summary_md(plan, album, I))
    if I.errors or I.warns:
        print(f"\n{len(I.errors)} lỗi, {len(I.warns)} cảnh báo (chạy validate để xem)")


def cmd_approve(a):
    album = album_dir(a.album)
    plan = load_plan(album)
    I = validate(plan, album, final=True)
    if I.errors:
        for m in I.errors:
            print(f"✖ {m}")
        die("chưa đủ điều kiện duyệt")
    # build trước (đổi tên file track, front matter…) để dấu vân tay tính trên đúng các file sẽ gửi Suno;
    # build tự dừng nếu plan đã đóng băng, nên không có gì được ghi khi suno-generate đã chạy
    a.force = False
    cmd_build(a)
    plan = load_plan(album)
    I = validate(plan, album, final=True)
    if I.errors:
        for m in I.errors:
            print(f"✖ {m}")
        die("sau build plan không còn đủ điều kiện duyệt")
    f = album / "plan.yaml"
    set_top_scalar(f, "status", "approved")
    append_status_log(f, {"date": str(date.today()), "status": "approved", "by": a.by, "note": a.note or "",
                          "fingerprint": plan_fingerprint(plan, album)})
    plan = load_plan(album)
    if approved_fingerprint(plan) != plan_fingerprint(plan, album):
        die("dấu vân tay không khớp ngay sau khi duyệt (lỗi nội bộ) → generation.yaml giữ draft")
    set_top_scalar(album / "generation.yaml", "status", "approved")
    build_album_md(plan, album, I, [])
    print(f"✔ plan + generation.yaml: status approved ({a.by}) → skill suno-generate có thể bắt đầu")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init")
    p.add_argument("--channel", required=True)
    p.add_argument("--from-idea")
    p.add_argument("--from-research", nargs="*", default=[])
    p.add_argument("--slug"); p.add_argument("--title")
    p.add_argument("--out", help="thư mục album (mặc định channel/<ch>/albums/NNN-<slug>)")
    p.add_argument("--no-promote", action="store_true", help="không đổi status của idea gốc")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_init)
    p = sub.add_parser("validate"); p.add_argument("album"); p.add_argument("--final", action="store_true"); p.set_defaults(fn=cmd_validate)
    p = sub.add_parser("build"); p.add_argument("album"); p.add_argument("--force", action="store_true"); p.set_defaults(fn=cmd_build)
    p = sub.add_parser("summary"); p.add_argument("album"); p.set_defaults(fn=cmd_summary)
    p = sub.add_parser("approve"); p.add_argument("album"); p.add_argument("--by", required=True); p.add_argument("--note")
    p.set_defaults(fn=cmd_approve)
    import channel_tools as ct
    p = sub.add_parser("board", help="trạng thái cả channel"); p.add_argument("--channel", required=True); p.set_defaults(fn=ct.cmd_board)
    p = sub.add_parser("sync", help="chép file hình ảnh mới hơn từ idea gốc"); p.add_argument("album"); p.set_defaults(fn=ct.cmd_sync)
    p = sub.add_parser("themes", help="concept/tempo/mở bài/Kinh Thánh/hình ảnh của mọi album (tránh trùng ý)")
    p.add_argument("--channel", required=True); p.set_defaults(fn=cmd_themes)
    p = sub.add_parser("catalog", help="dựng lại library/catalog.md"); p.add_argument("--channel", required=True); p.set_defaults(fn=ct.cmd_catalog)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

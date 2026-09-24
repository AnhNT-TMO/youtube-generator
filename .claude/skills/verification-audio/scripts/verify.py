#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
import warnings
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
warnings.filterwarnings("ignore")

from qc import basic  # noqa: E402
from qc import lyrics as lyr  # noqa: E402
from qc.common import REPO_DIR, SKILL_DIR, load_audio, load_cached, save_cached  # noqa: E402

AUDIO_EXT = {".wav", ".mp3", ".m4a", ".flac"}
REMOTE_SH = SKILL_DIR / "scripts" / "remote.sh"
SERVER_JOBS = 4
MIN_COVERAGE = 0.60
LYRIC_TIE = 0.10
TEMPO_TIE = 3.0
CUT_END_DB = -6.0
SILENCE_S = 2.0
LINE_MATCH = 0.6

HINTS = {
    "duration": "Bài ngoài độ dài quy định → thêm section (verse/bridge) hoặc đặt duration dài hơn.",
    "cut_end": "Bài bị cắt ngang → giữ tag outro: \"[Instrumental Outro] ... let the final chord sustain naturally\".",
    "silence": "Có khoảng lặng giữa bài → lỗi ngẫu nhiên của Suno, generate lại như cũ.",
    "lyrics": "Hát thiếu/sai lời → kiểm tra lời nhập vào Suno đúng slot; bớt tag chỉ dẫn nằm lẫn giữa lời, rút câu quá dài.",
}


def mmss(s: float) -> str:
    return f"{int(s // 60)}:{int(s % 60):02d}"


def short(name: str) -> str:
    m = re.search(r" ([0-9a-f]{8})(?: \[|\.[^.]+$)", name)
    return m.group(1) if m else Path(name).stem


class Album:
    def __init__(self, d: str | Path):
        self.dir = Path(d).resolve()
        self.cfg_path = self.dir / "selection.yaml"
        if not self.cfg_path.exists():
            sys.exit(f"Thiếu {self.cfg_path} → chạy album-plan build")
        cfg = yaml.safe_load(self.cfg_path.read_text()) or {}
        self.rules = cfg.get("rules") or {}
        self.slots = {int(k): v for k, v in (cfg.get("slots") or {}).items()}
        self.anchor = cfg.get("anchor")
        self.target_bpm_album = (cfg.get("tempo") or {}).get("target_bpm")
        self.raw = self.dir / "audio" / "raw_tracks"

    def track_md(self, slot: int) -> Path | None:
        return self.dir / self.slots[slot]["track"] if slot in self.slots else None

    def lyrics(self, slot: int) -> str | None:
        md = self.track_md(slot)
        return lyr.read_lyrics(md) if md else None

    def title(self, slot: int) -> str | None:
        md = self.track_md(slot)
        if md and md.exists() and (m := re.search(r'^title:\s*"?(.+?)"?\s*$', md.read_text(), re.M)):
            return m.group(1)
        return None

    def prompt_bpm(self, slot: int, entry: dict | None) -> float | None:
        st = (entry or {}).get("settings")
        if isinstance(st, dict) and isinstance(st.get("bpm"), (int, float)):
            return float(st["bpm"])
        md = self.track_md(slot)
        if md and md.exists() and (m := re.search(r"^target_bpm:\s*([\d.]+)", md.read_text(), re.M)):
            return float(m.group(1))
        return float(self.target_bpm_album) if isinstance(self.target_bpm_album, (int, float)) else None

    def duration_range(self) -> tuple[float, float]:
        lo, hi = self.rules.get("duration_range") or [180, 480]
        return float(lo), float(hi)


def load_manifest(al: Album) -> dict:
    f = al.raw / "manifest.json"
    return json.loads(f.read_text()) if f.exists() else {"clips": []}


def save_manifest(al: Album, man: dict) -> None:
    (al.raw / "manifest.json").write_text(json.dumps(man, indent=1, ensure_ascii=False) + "\n")


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def clips_for_slot(al: Album, slot: int, man: dict) -> list[Path]:
    title = al.title(slot)
    out = []
    for c in man.get("clips", []):
        f = al.raw / c["file"]
        if Path(c["file"]).suffix.lower() not in AUDIO_EXT or not f.exists():
            continue
        if c.get("status") in ("selected", "rejected", "reference"):
            continue
        if c.get("slot") == slot or (c.get("slot") is None and title and slugify(c.get("title", "")) == slugify(title)):
            out.append(f)
    return out


def transcribe(path: Path) -> list[dict]:
    if c := load_cached(path, "lyrics_mix"):
        return c["words"]
    y, _ = load_audio(path, sr=16000)
    res = lyr._transcribe(y, language="en", word_timestamps=True, condition_on_previous_text=False,
                          hallucination_silence_threshold=2.0, verbose=None)
    words = [{"w": w["word"].strip(), "s": float(w["start"])} for s in res["segments"] for w in s.get("words", [])]
    save_cached(path, "lyrics_mix", {"words": words})
    return words


def lyric_match(lyrics_block: str, words: list[dict]) -> dict:
    ws = [(t, w["s"]) for w in words for t in lyr.norm_tokens(w["w"])]
    hyp = [t for t, _ in ws]
    lines = list(dict.fromkeys(lyr.expected_lines(lyrics_block)))
    found, first, missing = 0, None, []
    for line in lines:
        toks = lyr.norm_tokens(line)
        best, at = 0.0, None
        for i in range(max(1, len(hyp) - len(toks) + 1)):
            r = SequenceMatcher(None, toks, hyp[i:i + len(toks) + 2]).ratio()
            if r > best:
                best, at = r, ws[i][1]
        if best >= LINE_MATCH:
            found += 1
            first = at if first is None else min(first, at)
        else:
            missing.append(line)
    return {"coverage": found / len(lines) if lines else 0.0, "first_lyric_s": first, "missing": missing}


def measure_bpm(path: Path, target: float) -> float | None:
    import librosa
    from qc import tempo as tmp
    y, _ = load_audio(path, sr=tmp.SR)
    ac = tmp._ac(librosa.onset.onset_strength(y=y, sr=tmp.SR, hop_length=tmp.HOP))
    return tmp.felt(ac, target)["bpm"]


def measure(path: Path, lyrics_block: str | None, dur_range: tuple[float, float], target_bpm: float | None) -> dict:
    b = basic.analyze(path)
    c = {"file": path.name, "duration": b["duration"], "lufs_i": b["lufs_i"], "true_peak": b["true_peak"],
         "end_type": b["end_type"], "problems": []}
    bad = c["problems"].append
    lo, hi = dur_range
    if not lo <= b["duration"] <= hi:
        bad({"id": "duration", "text": f"dài {mmss(b['duration'])}, album cần {mmss(lo)}–{mmss(hi)}"})
    if b["end_level_rel_db"] > CUT_END_DB:
        bad({"id": "cut_end", "text": "bị cắt ngang ở cuối (giây cuối vẫn còn to)"})
    gap = max(b["mid_silences"], key=lambda g: g["dur"], default=None)
    if gap and gap["dur"] >= SILENCE_S:
        bad({"id": "silence", "text": f"im lặng {gap['dur']:.1f} s ở {mmss(gap['start'])}"})
    if lyrics_block:
        L = lyric_match(lyrics_block, transcribe(path))
        c.update(coverage=round(L["coverage"], 3), first_lyric_s=L["first_lyric_s"], missing=L["missing"][:3])
        if L["coverage"] < MIN_COVERAGE:
            bad({"id": "lyrics", "text": f"chỉ nghe ra {L['coverage']:.0%} dòng lời"})
    if target_bpm and (bpm := measure_bpm(path, target_bpm)):
        c.update(bpm=round(bpm, 1), prompt_bpm=target_bpm, bpm_off_pct=round((bpm / target_bpm - 1) * 100, 1))
    return c


def decide(cands: list[dict], has_lyrics: bool) -> dict:
    ok = [c for c in cands if not c["problems"]]
    if not ok:
        best = min(cands, key=lambda c: (len(c["problems"]), -(c.get("coverage") or 0)))
        count: dict[str, int] = {}
        for c in cands:
            for p in {p["id"] for p in c["problems"]}:
                count[p] = count.get(p, 0) + 1
        n = len(cands)
        hints = [f"[{'cả ' + str(k) if k == n and n > 1 else f'{k}/{n}'} clip] {HINTS[p]}"
                 for p, k in sorted(count.items(), key=lambda kv: -kv[1])]
        return {"decision": "REGENERATE", "selected": None, "best_available": best["file"],
                "reasons": [f"{short(c['file'])}: " + "; ".join(p["text"] for p in c["problems"]) for c in cands],
                "hints": hints}
    if has_lyrics:
        top = max(c["coverage"] for c in ok)
        near = [c for c in ok if c["coverage"] >= top - LYRIC_TIE]
    else:
        near = ok
    if all(c.get("bpm_off_pct") is not None for c in near):
        lo = min(abs(c["bpm_off_pct"]) for c in near)
        near = [c for c in near if abs(c["bpm_off_pct"]) <= lo + TEMPO_TIE]
    best = min(near, key=lambda c: (c["first_lyric_s"] if c.get("first_lyric_s") is not None else 1e9,
                                    abs(c.get("bpm_off_pct") or 0), -(c.get("coverage") or 0)))
    others = [c for c in cands if c is not best]
    reasons = []
    if has_lyrics:
        vs = ", ".join(f"{short(c['file'])} {c['coverage']:.0%}" for c in others if c.get("coverage") is not None)
        reasons.append(f"hát đúng {best['coverage']:.0%} dòng lời" + (f" (bản khác: {vs})" if vs else ""))
    if best.get("bpm") is not None:
        vs = ", ".join(f"{short(c['file'])} {c['bpm']:.0f} ({c['bpm_off_pct']:+.0f} %)" for c in others if c.get("bpm") is not None)
        reasons.append(f"tempo {best['bpm']:.0f} BPM, lệch {best['bpm_off_pct']:+.0f} % so với prompt {best['prompt_bpm']:g}"
                       + (f" (bản khác: {vs})" if vs else ""))
    if has_lyrics:
        if best.get("first_lyric_s") is not None:
            vs = ", ".join(f"{short(c['file'])} giây {c['first_lyric_s']:.0f}" for c in others
                           if not c["problems"] and c.get("first_lyric_s") is not None)
            reasons.append(f"vào lời ở giây {best['first_lyric_s']:.0f}" + (f" (bản khác: {vs})" if vs else ""))
    reasons += [f"{short(c['file'])}: " + "; ".join(p["text"] for p in c["problems"]) for c in others if c["problems"]]
    return {"decision": "SELECT", "selected": best["file"], "reasons": reasons}


def report(dec: dict, cands: list[dict], album: str, slot: int, has_lyrics: bool) -> str:
    L = [f"# Verify — {album} · slot {slot}", "", f"_verification-audio · {date.today()}_", ""]
    if dec["decision"] == "SELECT":
        L += [f"## ✅ CHỌN: `{dec['selected']}`", ""] + [f"- {r}" for r in dec["reasons"]]
    else:
        L += ["## 🔁 TẠO LẠI — không clip nào qua", ""] + [f"- {r}" for r in dec["reasons"]]
        L += ["", "Gợi ý cho lượt generate tiếp theo:"] + [f"- {h}" for h in dec["hints"]]
        L += ["", f"(Không muốn tốn thêm credits: bản ít lỗi nhất là `{dec['best_available']}`, dùng được qua "
              "`accept --why`, được ghi là duyệt vượt verify.)"]
    if not has_lyrics:
        L += ["", "> ⚠ Track md của slot chưa có lời trong `## Lyrics` → chỉ xét được tiêu chí 1 (không hỏng)."]
    L += ["", "| Clip | Dài | Kết bài | Lời nghe ra | Tempo (so với prompt) | Vào lời | Lỗi |", "|---|---|---|---|---|---|---|"]
    for c in cands:
        cov = f"{c['coverage']:.0%}" if c.get("coverage") is not None else "–"
        fl = f"giây {c['first_lyric_s']:.0f}" if c.get("first_lyric_s") is not None else "–"
        bpm = f"{c['bpm']:.1f} ({c['bpm_off_pct']:+.0f} %)" if c.get("bpm") is not None else "–"
        L.append(f"| `{c['file']}` | {mmss(c['duration'])} | {c['end_type']} | {cov} | {bpm} | {fl} | "
                 + ("; ".join(p["text"] for p in c["problems"]) or "–") + " |")
    return "\n".join(L) + "\n"


def _measure_job(job: tuple) -> dict:
    f, lyrics, dur_range, bpm = job
    return measure(Path(f), lyrics, dur_range, bpm)


def measure_all(jobs: list[tuple], n_jobs: int) -> list[dict]:
    if n_jobs <= 1 or len(jobs) <= 1:
        out = []
        for j in jobs:
            out.append(_measure_job(j))
            print(f"  {Path(j[0]).name}", flush=True)
        return out
    import multiprocessing as mp
    from concurrent.futures import ProcessPoolExecutor, as_completed
    out: list[dict | None] = [None] * len(jobs)
    with ProcessPoolExecutor(max_workers=min(n_jobs, len(jobs)), mp_context=mp.get_context("spawn")) as ex:
        futs = {ex.submit(_measure_job, j): i for i, j in enumerate(jobs)}
        for fu in as_completed(futs):
            out[futs[fu]] = fu.result()
            print(f"  {Path(jobs[futs[fu]][0]).name}", flush=True)
    return out


def parse_slots(al: Album, man: dict, arg: list[str]) -> list[int]:
    if [x.lower() for x in arg] == ["all"]:
        slots = [n for n in sorted(al.slots) if clips_for_slot(al, n, man)]
        if not slots:
            sys.exit("Không slot nào còn clip draft.")
        return slots
    try:
        return sorted({int(x) for x in arg})
    except ValueError:
        sys.exit(f"--slot nhận số slot hoặc 'all', không phải {arg}")


def record(man: dict, dec: dict) -> bool:
    by_name = {c["file"]: c for c in man.get("clips", [])}
    hit = False
    for c in dec["candidates"]:
        if c["file"] in by_name:
            hit = True
            by_name[c["file"]]["slot"] = dec["slot"]
            by_name[c["file"]]["verify"] = {"date": dec["date"], "ok": not c["problems"],
                                           "problems": [p["id"] for p in c["problems"]],
                                           "coverage": c.get("coverage"), "first_lyric_s": c.get("first_lyric_s"),
                                           "bpm": c.get("bpm"), "prompt_bpm": c.get("prompt_bpm")}
    return hit


def summary_line(dec: dict) -> str:
    if dec["decision"] == "SELECT":
        return f"slot {dec['slot']:>2}: SELECT {short(dec['selected'])} — " + "; ".join(dec["reasons"][:2])
    return f"slot {dec['slot']:>2}: REGENERATE (bản ít lỗi nhất {short(dec['best_available'])}) — " + " | ".join(dec["reasons"])


def check_remote(al: Album, slots: list[int], a) -> list[dict]:
    rel = al.dir.relative_to(REPO_DIR)
    clips = [str(Path(p).absolute().relative_to(REPO_DIR)) for p in a.clips]
    fail = ("Server GPU không chạy được ({}). Kiểm tra mạng/server rồi chạy lại; hoặc thêm --local để đo trên Mac "
            "(Whisper ~30–80 s/clip, nặng máy) — hỏi chủ kênh trước khi chạy --local.")
    print(f"Đẩy {rel.name} lên server GPU…", flush=True)
    if subprocess.run(["bash", str(REMOTE_SH), "push"]).returncode:
        sys.exit(fail.format("push lỗi"))
    skr = SKILL_DIR.relative_to(REPO_DIR)
    cmd = (f"{skr}/.venv/bin/python {skr}/scripts/verify.py check --album {shlex.quote(str(rel))} "
           f"--slot {' '.join(map(str, slots))} --local --no-manifest --quiet --jobs {a.jobs or SERVER_JOBS} "
           + " ".join(shlex.quote(c) for c in clips))
    if subprocess.run(["bash", str(REMOTE_SH), "exec", cmd]).returncode:
        sys.exit(fail.format("lệnh trên server lỗi"))
    if subprocess.run(["bash", str(REMOTE_SH), "pull", str(rel)]).returncode:
        sys.exit(fail.format("kéo kết quả về lỗi"))
    return [json.loads((al.dir / "notes" / f"verify-slot-{n:02d}.json").read_text()) for n in slots]


def check_here(al: Album, slots: list[int], man: dict, a) -> list[dict]:
    files = {}
    for n in slots:
        files[n] = [Path(p).absolute() for p in a.clips] if a.clips else clips_for_slot(al, n, man)
        if not files[n]:
            sys.exit(f"Không có clip nào cho slot {n} (manifest cần `slot: {n}` hoặc title khớp track md, status draft).")
    by_name = {c["file"]: c for c in man.get("clips", [])}
    lyrics = {n: al.lyrics(n) for n in slots}
    jobs = [(str(f), lyrics[n], al.duration_range(), al.prompt_bpm(n, by_name.get(f.name))) for n in slots for f in files[n]]
    print(f"Đo {len(jobs)} clip của {len(slots)} slot, {a.jobs} clip một lúc (Whisper lần đầu ~30–80 s/clip trên Mac, "
          "vài giây trên GPU; sau đó dùng cache)…", flush=True)
    res = iter(measure_all(jobs, a.jobs))
    notes = al.dir / "notes"
    notes.mkdir(exist_ok=True)
    decs = []
    for n in slots:
        cands = [next(res) for _ in files[n]]
        dec = decide(cands, bool(lyrics[n]))
        dec.update(album=al.dir.name, slot=n, date=str(date.today()), candidates=cands)
        (notes / f"verify-slot-{n:02d}.md").write_text(report(dec, cands, al.dir.name, n, bool(lyrics[n])))
        (notes / f"verify-slot-{n:02d}.json").write_text(json.dumps(dec, indent=1, ensure_ascii=False))
        decs.append(dec)
    return decs


def cmd_check(a) -> None:
    al = Album(a.album)
    man = load_manifest(al)
    slots = parse_slots(al, man, a.slot)
    if a.clips and len(slots) > 1:
        sys.exit("Chỉ đưa danh sách clip khi check một slot.")
    decs = check_here(al, slots, man, a) if a.local else check_remote(al, slots, a)
    if a.quiet:
        return
    if not a.no_manifest and any([record(man, d) for d in decs]):
        save_manifest(al, man)
    for d in decs:
        print("\n" + (al.dir / "notes" / f"verify-slot-{d['slot']:02d}.md").read_text())
    print("== Tóm tắt")
    for d in decs:
        print(summary_line(d))
    for d in decs:
        print(f"SLOT={d['slot']} DECISION={d['decision']} SELECTED={d.get('selected') or ''}")


def set_front_matter(text: str, updates: dict) -> str:
    head, sep, body = text.partition("\n---\n")
    for k, v in updates.items():
        if v is None:
            continue
        line = f"{k}: {v}"
        if re.search(rf"^{re.escape(k)}:.*$", head, re.M):
            head = re.sub(rf"^{re.escape(k)}:.*$", lambda _: line, head, count=1, flags=re.M)
        else:
            head += "\n" + line
    return head + sep + body


def verify_override(al: Album, slot: int, clip: str, entry: dict | None) -> dict | None:
    f = al.dir / "notes" / f"verify-slot-{slot:02d}.json"
    if not f.exists():
        return {"decision": "UNVERIFIED", "verify_selected": None, "problems": []}
    dec = json.loads(f.read_text())
    if dec.get("decision") == "SELECT" and dec.get("selected") == clip:
        return None
    return {"decision": dec.get("decision"), "verify_selected": dec.get("selected"),
            "problems": ((entry or {}).get("verify") or {}).get("problems") or [], "verify_date": dec.get("date")}


def cmd_accept(a) -> None:
    al = Album(a.album)
    src = Path(a.clip).absolute()
    if src.parent.resolve() != al.raw.resolve():
        sys.exit(f"Clip phải nằm trong {al.raw}")
    name = re.sub(r" [0-9a-f]{8}(?=\.[^.]+$)", "", re.sub(r" \[usesuno\.com\]", "", src.name))
    dst = al.dir / "audio" / "tracks" / name
    if dst.exists() and not a.replace:
        sys.exit(f"{dst.name} đã có trong tracks/ → thêm --replace nếu thật sự muốn thay (bản cũ được đổi tên .replaced-<ngày>).")
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        dst.rename(dst.with_name(dst.stem + f".replaced-{date.today()}" + dst.suffix))
    shutil.copy2(src, dst)

    man = load_manifest(al)
    entry = next((c for c in man.get("clips", []) if c["file"] == src.name), None)
    override = verify_override(al, a.slot, src.name, entry)
    if override:
        override["why"] = a.why
        print(f"⚠ Duyệt vượt verify: quyết định {override['decision']}, verify chọn {override.get('verify_selected') or '—'}"
              + (f", clip này có lỗi {override['problems']}" if override.get("problems") else "") + " → ghi vào manifest (accept_override)")
    for c in man.get("clips", []):
        if c["file"] == src.name:
            c.update(status="selected", slot=a.slot, accepted=str(date.today()), track_file=f"audio/tracks/{name}")
            if override:
                c["accept_override"] = override
        elif c.get("slot") == a.slot and c.get("status") in (None, "draft", "selected"):
            c["status"] = "rejected"
    save_manifest(al, man)

    md = al.track_md(a.slot)
    if md and md.exists():
        b = basic.analyze(dst)
        up = {"audio": f"audio/tracks/{name}", "duration": f"\"{mmss(b['duration'])}\"",
              "lufs_integrated": b["lufs_i"], "true_peak": b["true_peak"], "outro_type": b["end_type"]}
        ver = (entry or {}).get("verify") or {}
        if ver.get("bpm") is not None:
            up["bpm"] = f"{ver['bpm']:.1f}"
        fl = ver.get("first_lyric_s")
        if fl is not None:
            up["vocal_entry_seconds"] = f"{fl:.1f}   # giây lời hát đầu tiên (Whisper); tiếng hum trước lời không tính"
        if entry and entry.get("suno_url"):
            up["suno_url"] = entry["suno_url"]
        md.write_text(set_front_matter(md.read_text(), up))
        print(f"✔ Cập nhật front matter: {md.relative_to(al.dir)}")
    else:
        print("⚠ Chưa có track md cho slot → chỉ copy audio, chưa ghi metadata.")
    if a.slot == 1 and not al.anchor:
        txt = al.cfg_path.read_text()
        line = f'anchor: "audio/tracks/{name}"'
        txt = re.sub(r"^anchor:.*$", line, txt, count=1, flags=re.M) if re.search(r"^anchor:", txt, re.M) else line + "\n" + txt
        al.cfg_path.write_text(txt)
        print(f"✔ selection.yaml: {line}")
    print(f"✔ {src.name} → audio/tracks/{name}\n✔ manifest: selected + các clip draft khác của slot → rejected")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--album", required=True)
    c.add_argument("--slot", nargs="+", required=True, help="một hoặc nhiều số slot, hoặc 'all' (mọi slot còn clip draft)")
    c.add_argument("--local", action="store_true", help="đo trên máy này thay vì server GPU")
    c.add_argument("--jobs", type=int, help=f"số clip đo cùng lúc (server: {SERVER_JOBS}, --local: 1)")
    c.add_argument("--no-manifest", action="store_true", help=argparse.SUPPRESS)
    c.add_argument("--quiet", action="store_true", help=argparse.SUPPRESS)
    c.add_argument("clips", nargs="*")
    c.set_defaults(fn=cmd_check)
    s = sub.add_parser("accept")
    s.add_argument("--album", required=True)
    s.add_argument("--slot", type=int, required=True)
    s.add_argument("--clip", required=True)
    s.add_argument("--replace", action="store_true")
    s.add_argument("--why", help="lý do khi duyệt clip mà verify không chọn (vd. 'người dùng: hết credits, dùng best_available')")
    s.set_defaults(fn=cmd_accept)
    a = ap.parse_args()
    if a.cmd == "check" and a.local and not a.jobs:
        a.jobs = 1
    a.fn(a)


if __name__ == "__main__":
    main()

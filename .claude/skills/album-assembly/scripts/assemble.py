#!/usr/bin/env python
"""Ghép các bài của một album thành một bản liên tục (thứ tự bài giữ nguyên theo track_no).

    assemble.py plan   <album>            # đo bài, chọn kiểu nối → assembly.yaml + assembly.md
    assemble.py set    <album> <nối> --type breath [--b-keep 14 ...]   # chỉnh một điểm nối (tự khóa)
    assemble.py unlock <album> <nối|all>
    assemble.py render <album>            # ghép → audio/master/<album>.wav/.mp3 + previews, đo lại
    assemble.py report <album>            # sinh lại assembly.md từ yaml
    assemble.py single <single>           # bài đăng riêng: cắt intro + cân loudness + render → audio/master/<single>.wav

Chạy từ gốc repo: SK=.claude/skills/album-assembly; $SK/.venv/bin/python $SK/scripts/assemble.py <lệnh> ...
plan / set / render / single mặc định chạy trên server GPU (scripts/remote.sh: đẩy album lên, chạy, kéo assembly.yaml/.md
và audio/master/ về). `--local` = chạy trên máy này (Demucs + ghép 1 giờ audio: nặng, chỉ khi server không kết nối được
và chủ kênh đồng ý). unlock / report luôn chạy local (không đo gì).
<album> = đường dẫn thư mục album hoặc tên (vd. 001-when-the-night-is-long).
<single> = thư mục channel/<channel>/singles/NNN-slug (có single.md, field `track` trỏ tới tracks/NN-*.md của album gốc).
"""
from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
import warnings
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
warnings.filterwarnings("ignore")

from assembly import planner, render as rnd  # noqa: E402
from assembly.features import load_single, load_tracks, measure  # noqa: E402
from assembly.plan import build, build_single, set_join  # noqa: E402
from assembly.report import MARK, checks, write_md  # noqa: E402
from measure.common import REPO_DIR, SKILL_DIR, find_album  # noqa: E402

REMOTE_SH = SKILL_DIR / "scripts" / "remote.sh"
HEAVY = ("plan", "set", "render", "single")   # đo (Demucs, beat_this) hoặc ghép audio → server

HEADER = """\
# Kế hoạch ghép album — sinh bởi skill album-assembly (scripts/assemble.py). Thứ tự bài = track_no, không đổi.
# Số giây tính trong FILE GỐC của từng bài. `render` chỉ đọc các số trong tracks[] (in/out/fade/gain) và joins[].overlap.
# overlap > 0: bài sau bắt đầu trước khi bài trước tắt hẳn (crossfade); overlap < 0: khoảng lặng giữa hai bài.
# Sửa tay được. Chạy lại `plan` sẽ tính lại mọi join KHÔNG có `locked: true` (và opening nếu opening.locked=false),
# giữ gain của track có `gain_locked: true`. `set` tự khóa join nó sửa.
"""


class Flow(dict):
    pass


yaml.SafeDumper.add_representer(Flow, lambda d, v: d.represent_mapping("tag:yaml.org,2002:map", v, flow_style=True))


def _clean(o):
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return round(float(o), 3)
    return o


def save(album: Path, plan: dict) -> None:
    plan = _clean(plan)
    for t in plan["tracks"]:
        t["measured"] = Flow(t["measured"])
    for j in plan["joins"]:
        j["feel"] = Flow(j["feel"])
    res = plan.get("result")
    if res:
        res["opening"] = Flow(res["opening"])
        res["joins"] = [Flow(r) for r in res["joins"]]
        res["chapters"] = [Flow(c) for c in res["chapters"]]
    body = yaml.safe_dump(plan, sort_keys=False, allow_unicode=True, width=160)
    (album / "assembly.yaml").write_text(HEADER + body)
    md = album / "assembly.md"
    if md.exists() and MARK not in md.read_text():
        backup = album / "notes" / "assembly-v0.md"
        backup.parent.mkdir(exist_ok=True)
        if not backup.exists():
            shutil.copy(md, backup)
            print(f"assembly.md cũ (viết tay) đã lưu sang {backup.relative_to(album)}")
    write_md(plan, album, md)


def load(album: Path) -> dict:
    f = album / "assembly.yaml"
    if not f.exists():
        raise SystemExit(f"chưa có {f}; chạy `plan` trước")
    return yaml.safe_load(f.read_text())


def resolve(arg: str) -> Path:
    p = Path(arg)
    return p.resolve() if p.is_dir() else find_album(arg)


def print_summary(plan: dict) -> None:
    tr = plan["tracks"]
    print(f"\nMở video: bài 01 vào từ {tr[0]['in']:.1f}s, giọng hát ở giây {tr[0]['measured']['vocal_start'] - tr[0]['in']:.1f}")
    if not plan["joins"]:
        print(f"  giữ {tr[0]['in']:.1f}–{tr[0]['out']:.1f}s của file, gain {tr[0]['gain_db']:+.1f} dB")
    for j in plan["joins"]:
        f = j["feel"]
        ov = f"chồng {j['overlap']:.1f}s" if j["overlap"] > 0 else f"lặng {-j['overlap']:.1f}s"
        print(f"  {j['from']:02d}→{j['to']:02d}  {planner.RECIPES[j['type']]['label']:<18} intro sau {f['b_keep']:>4.1f}s  "
              f"{ov:<10} không lời {f['vocal_gap']:>4.0f}s{'  🔒' if j.get('locked') else ''}")
    for lv, no, msg in checks(plan):
        print(f"  {'❌' if lv == 'fail' else '⚠️'}  " + (f"nối {no}: " if no else "") + msg)


def plan_targets(album: Path, vocal_at: float | None, lufs: float | None) -> tuple[float, float, str]:
    """Số mở bài + loudness: tham số dòng lệnh > plan.yaml (skill album-plan) > mặc định 8 s / −14 LUFS.
    Cùng quy tắc vocal_at với verification-audio (qc/opening.py), để gate Track 01 đo đúng giây mà video sẽ có:
    target.vocal.vocal_at_s, nếu không có thì min(8, first_voice_max_s của track01)."""
    import yaml
    f = album / "plan.yaml"
    tgt = ((yaml.safe_load(f.read_text()) or {}).get("target") or {}) if f.exists() else {}
    v, loud = tgt.get("vocal") or {}, tgt.get("loudness") or {}
    src = []
    if vocal_at is None:
        fv = v.get("first_voice_max_s")
        fv = fv.get("track01") if isinstance(fv, dict) else fv
        if v.get("vocal_at_s") is not None:
            vocal_at = float(v["vocal_at_s"]); src.append("vocal_at_s từ plan.yaml")
        elif isinstance(fv, (int, float)):
            vocal_at = min(8.0, float(fv)); src.append(f"min(8, first_voice_max_s {fv:g}) từ plan.yaml")
        else:
            vocal_at = 8.0
    if lufs is None:
        if isinstance(loud.get("master_lufs"), (int, float)):
            lufs = float(loud["master_lufs"]); src.append("master_lufs từ plan.yaml")
        else:
            lufs = -14.0
    return vocal_at, lufs, ", ".join(src) or "mặc định"


def run_remote(album: Path, cmd: str, argv: list[str], album_arg: str) -> None:
    """Chạy đúng lệnh này trên server (thêm --local ở đó), rồi kéo kết quả về."""
    rel = album.relative_to(REPO_DIR)
    i = argv.index(album_arg, argv.index(cmd) + 1)
    args = argv[:i] + [str(rel)] + argv[i + 1:] + ["--local"]
    fail = ("Server GPU không chạy được ({}). Kiểm tra mạng/server rồi chạy lại; hoặc thêm --local để chạy trên Mac "
            "(Demucs + ghép audio, nặng máy) — hỏi chủ kênh trước khi chạy --local.")
    print(f"Đẩy {rel.name} lên server GPU…", flush=True)
    if subprocess.run(["bash", str(REMOTE_SH), "push"]).returncode:
        raise SystemExit(fail.format("push lỗi"))
    skr = SKILL_DIR.relative_to(REPO_DIR)
    if subprocess.run(["bash", str(REMOTE_SH), "exec",
                       f"{skr}/.venv/bin/python {skr}/scripts/assemble.py " + " ".join(map(shlex.quote, args))]).returncode:
        raise SystemExit(fail.format("lệnh trên server lỗi"))
    print("kéo kết quả về…", flush=True)
    pull = ["bash", str(REMOTE_SH), "pull", str(rel)] + (["master"] if cmd in ("render", "single") else [])
    if subprocess.run(pull).returncode:
        raise SystemExit(fail.format("kéo kết quả về lỗi"))
    print(f"✔ đã kéo về {rel}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("album")
    p.add_argument("--vocal-at", type=float, help="giây giọng hát vào trong video (mặc định: plan.yaml, không có thì 8)")
    p.add_argument("--target-lufs", type=float, help="mặc định: plan.yaml target.loudness.master_lufs, không có thì −14")
    p.add_argument("--fresh", action="store_true", help="bỏ qua yaml cũ, kể cả join đã khóa")
    s = sub.add_parser("set")
    s.add_argument("album")
    s.add_argument("join", type=int, help="số điểm nối (1 = bài 1 → 2)")
    s.add_argument("--type", required=True, choices=planner.TYPES)
    for k in ("a-tail", "a-fade", "b-keep", "overlap", "b-fade"):
        s.add_argument(f"--{k}", type=float)
    u = sub.add_parser("unlock")
    u.add_argument("album")
    u.add_argument("join")
    r = sub.add_parser("render")
    r.add_argument("album")
    r.add_argument("--no-mp3", action="store_true")
    rp = sub.add_parser("report")
    rp.add_argument("album")
    sg = sub.add_parser("single")
    sg.add_argument("album", metavar="single")
    sg.add_argument("--vocal-at", type=float, default=8.0, help="giây giọng hát vào trong video (mặc định 8)")
    sg.add_argument("--target-lufs", type=float, default=-14.0)
    sg.add_argument("--fresh", action="store_true", help="bỏ qua yaml cũ, kể cả opening/gain đã khóa")
    sg.add_argument("--no-mp3", action="store_true")
    for sp in (p, s, r, sg):
        sp.add_argument("--local", action="store_true", help="chạy trên máy này thay vì server GPU")
    a = ap.parse_args()
    album = resolve(a.album)
    if a.cmd in HEAVY and not a.local:
        return run_remote(album, a.cmd, sys.argv[1:], a.album)

    if a.cmd == "plan":
        tracks = load_tracks(album)
        print(f"{album.name}: {len(tracks)} bài, đo…", flush=True)
        measure(tracks)
        prev = None if a.fresh or not (album / "assembly.yaml").exists() else load(album)
        vocal_at, lufs, src = plan_targets(album, a.vocal_at, a.target_lufs)
        print(f"giọng bài 1 vào ở giây {vocal_at:g} · {lufs:g} LUFS ({src})", flush=True)
        plan = build(album, tracks, prev, vocal_at, lufs)
        save(album, plan)
        print_summary(plan)
        print(f"\n→ {album / 'assembly.yaml'}\n→ {album / 'assembly.md'}")
    elif a.cmd == "set":
        plan = load(album)
        tracks = load_tracks(album)
        if not 1 <= a.join <= len(tracks) - 1:
            raise SystemExit(f"điểm nối phải trong 1..{len(tracks) - 1}")
        pair = [tracks[a.join - 1], tracks[a.join]]
        measure(pair, verbose=False)
        tracks[a.join - 1], tracks[a.join] = pair
        set_join(plan, tracks, a.join, a.type, a_tail=a.a_tail, a_fade=a.a_fade, b_keep=a.b_keep,
                 overlap=a.overlap, b_fade=a.b_fade)
        save(album, plan)
        print_summary(plan)
    elif a.cmd == "unlock":
        plan = load(album)
        for j in plan["joins"]:
            if a.join == "all" or j["no"] == int(a.join):
                j["locked"] = False
        save(album, plan)
        print("đã mở khóa; chạy `plan` để tính lại")
    elif a.cmd in ("render", "single"):
        if a.cmd == "single":
            t, audio_rel = load_single(album)
            print(f"{album.name}: {t.title} ({t.id}), đo…", flush=True)
            measure([t], verbose=False)
            prev = None if a.fresh or not (album / "assembly.yaml").exists() else load(album)
            plan = build_single(album, t, audio_rel, prev, a.vocal_at, a.target_lufs)
            save(album, plan)
        else:
            plan = load(album)
        out = album / plan["output"]
        print(f"ghép {len(plan['tracks'])} bài → {out.relative_to(album)}", flush=True)
        rnd.render(plan, album, out, mp3=not a.no_mp3)
        print("đo lại bản ghép…", flush=True)
        res = rnd.verify(plan, out)
        res["previews"] = rnd.previews(plan, out, out.parent / "previews")
        plan["result"] = res
        save(album, plan)
        print(f"{res['duration'] / 60:.1f} phút · {res['lufs_i']} LUFS · true peak {res['true_peak']} dBTP")
        print_summary(plan)
        print(f"\n→ {out}\n→ {album / 'assembly.md'}")
    elif a.cmd == "report":
        save(album, load(album))


if __name__ == "__main__":
    main()

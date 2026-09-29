#!/usr/bin/env python3
USAGE = """audio-album-assembly: nối các bài của một album (thứ tự track_no trong tracks/NN-*.md) bằng crossfade nhẹ.

  assemble.py render <album> [--crossfade S] [--no-mp3]
      bỏ im lặng số ở HAI ĐẦU từng file (< -60 dBFS; không cắt gì trong bài), cân mọi bài về cùng loudness,
      nối equal-power crossfade, master -14 LUFS, true peak <= -1.5 dBTP, 48 kHz 24-bit WAV + MP3
      → audio/master/<album>.wav/.mp3 + assembly.json + assembly.md. Chạy trên GPU server (scripts/remote.sh);
      kéo master về máy này, kiểm xong thì xoá master trên server (giữ file bài trong songs/ cho album sau).
  assemble.py report <album>
      sinh lại assembly.md từ assembly.json (trên máy này, không đo gì)

<album> = thư mục album hoặc tên NNN-slug. Crossfade: --crossfade, không có thì `crossfade_s` trong
channel/<ch>/album_rules.md. Exit 4 = đã ghép nhưng có kiểm tra ❌ (xem assembly.md).
Chạy từ gốc repo: python3 .claude/skills/audio-album-assembly/scripts/assemble.py …   (chỉ cần python3 + ffmpeg)
"""
import argparse
import json
import math
import os
import re
import shlex
import struct
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
REPO = SKILL.parents[2]
REMOTE_SH = SKILL / "scripts" / "remote.sh"
SR = 48000
OVERSAMPLE = 4
TARGET_LUFS = -14.0
LUFS_TOL = 0.5
TP_MAX = -1.5
LIMIT_MARGIN_DB = 0.5
SILENCE_DB = -60
SILENCE_MIN_S = 0.01
MEASURE_JOBS = 6
RENDER_TRIES = 3
DURATION_TOL_S = 0.05
LONG_EDGE_S = 2.0
LIMITER_WARN_DB = 3.0
CHAPTER_MIN_S = 10
CHECK_FAILED = 4


def die(msg, code=1):
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(code)


def rel(p):
    return os.path.relpath(Path(p).absolute(), REPO)


def value(v):
    v = v.strip()
    if not v:
        return None
    if v[0] in "[{\"" or re.fullmatch(r"-?\d+(\.\d+)?|true|false|null", v):
        try:
            return json.loads(v)
        except json.JSONDecodeError:
            pass
    if len(v) >= 2 and v[0] == v[-1] == "'":
        return v[1:-1].replace("''", "'")
    return re.sub(r"\s+#.*$", "", v)


def front_matter(path):
    m = re.match(r"^---\n(.*?)\n---", Path(path).read_text(), re.S)
    out = {}
    for line in m.group(1).splitlines() if m else []:
        if not line or line[0] in " #-":
            continue
        k, sep, v = line.partition(":")
        if sep:
            out[k.strip()] = value(v)
    return out


def clock(s):
    s = int(math.floor(s))
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def resolve(arg):
    p = Path(arg)
    if p.is_dir():
        return p.resolve()
    hits = sorted((REPO / "channel").glob(f"*/albums/{arg}"))
    if len(hits) != 1:
        die(f"không tìm thấy album {arg}" if not hits else f"{arg} có ở nhiều kênh: đưa đường dẫn thư mục")
    return hits[0].resolve()


def rules_of(album):
    f = album.parents[1] / "album_rules.md"
    return (front_matter(f) if f.exists() else {}), f


def load_tracks(album):
    files = sorted(f for f in (album / "tracks").glob("*.md") if f.name.count(".") == 1)
    if not files:
        die(f"{rel(album)}/tracks/ chưa có NN-*.md (pm-production album.py build)")
    tracks = []
    for f in files:
        fm = front_matter(f)
        if not isinstance(fm.get("track_no"), int) or not fm.get("audio"):
            die(f"{rel(f)}: thiếu track_no hoặc audio")
        path = (album / fm["audio"]).resolve()
        if not path.exists():
            die(f"{rel(f)}: không có file audio {fm['audio']}")
        tracks.append({"track_no": fm["track_no"], "slug": fm.get("slug") or f.stem[3:], "title": fm.get("title") or f.stem,
                       "type": fm.get("type"), "audio": fm["audio"], "path": path})
    tracks.sort(key=lambda t: t["track_no"])
    if [t["track_no"] for t in tracks] != list(range(1, len(tracks) + 1)):
        die(f"track_no phải là 1..{len(tracks)} liên tục, đang có {[t['track_no'] for t in tracks]}")
    return tracks


def crossfade_of(album, arg):
    if arg is not None:
        return float(arg)
    rules, f = rules_of(album)
    if not isinstance(rules.get("crossfade_s"), (int, float)):
        die(f"không có crossfade_s trong {rel(f)}: thêm vào album_rules.md hoặc dùng --crossfade")
    return float(rules["crossfade_s"])


def remote(args, stdin=None, ok=(0,), fatal=True):
    r = subprocess.run(["bash", str(REMOTE_SH), *args], input=stdin, text=True)
    if r.returncode not in ok and fatal:
        die(f"GPU server lỗi ở bước `{args[0]}` (exit {r.returncode}): kiểm tra mạng/server rồi chạy lại. "
            "Không ghép trên Mac; server không lên được thì báo PM.", 3)
    return r.returncode


def wav_duration(path):
    try:
        size = path.stat().st_size
        with open(path, "rb") as f:
            riff, rsize, wave = struct.unpack("<4sI4s", f.read(12))
            if riff != b"RIFF" or wave != b"WAVE" or size != rsize + 8:
                return None
            pos, rate_bytes = 12, None
            while pos + 8 <= size:
                f.seek(pos)
                cid, cs = struct.unpack("<4sI", f.read(8))
                if cid == b"fmt ":
                    rate_bytes = struct.unpack("<HHIIHH", f.read(16))[3]
                elif cid == b"data":
                    return cs / rate_bytes if rate_bytes and pos + 8 + cs <= size else None
                pos += 8 + cs + (cs & 1)
    except (OSError, struct.error):
        return None
    return None


def pulled_master_problem(album, no_mp3):
    wav = album / "audio" / "master" / f"{album.name}.wav"
    f = album / "assembly.json"
    if not f.exists():
        return f"chưa có {rel(f)} trên máy"
    want, got = json.loads(f.read_text())["duration_s"], wav_duration(wav)
    if got is None or abs(got - want) > DURATION_TOL_S:
        return f"{rel(wav)} trên máy không đọc được hoặc lệch assembly.json ({got} s vs {want} s)"
    mp3 = wav.with_suffix(".mp3")
    if not no_mp3 and not (mp3.exists() and mp3.stat().st_size):
        return f"thiếu {rel(mp3)} trên máy"
    return None


def render_remote(album, a):
    tracks = load_tracks(album)
    xf = crossfade_of(album, a.crossfade)
    ra = rel(album)
    _, rules_file = rules_of(album)
    files = [rel(__file__), *([rel(rules_file)] if rules_file.exists() else []),
             *(rel(f) for f in sorted((album / "tracks").glob("*.md"))), *(rel(t["path"]) for t in tracks)]
    if (album / "album.md").exists():
        files.append(rel(album / "album.md"))
    print(f"Đẩy {album.name} ({len(tracks)} bài, crossfade {xf:g} s) lên GPU server…", flush=True)
    remote(["push", ra], "\n".join(dict.fromkeys(files)) + "\n")
    cmd = f"python3 {shlex.quote(rel(__file__))} render {shlex.quote(ra)} --local --crossfade {xf:g}" + (" --no-mp3" if a.no_mp3 else "")
    rc = remote(["exec", cmd], ok=(0, CHECK_FAILED))
    print("Kéo master + assembly.json/.md về…", flush=True)
    remote(["pull", ra])
    print(f"✔ {ra}/audio/master/{album.name}.wav · {ra}/assembly.json · {ra}/assembly.md")
    problem = pulled_master_problem(album, a.no_mp3)
    if problem:
        print(f"⚠️  {problem}: giữ master trên server, kéo lại bằng `bash {rel(REMOTE_SH)} pull {ra}`")
        sys.exit(rc)
    master = f"{ra}/audio/master/{album.name}"
    if remote(["exec", f"rm -f {shlex.quote(master + '.wav')} {shlex.quote(master + '.mp3')}"], fatal=False):
        print("⚠️  chưa xoá được master trên server (lỗi ssh): lần render sau ghi đè, hoặc xoá bằng guard.sh run")
    else:
        print("✔ đã xoá master WAV/MP3 trên server (file bài trong songs/ giữ lại cho album sau)")
    sys.exit(rc)


def ffprobe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
                          "stream=sample_rate,channels:format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    return float(j["format"]["duration"]), int(j["streams"][0]["sample_rate"]), int(j["streams"][0]["channels"])


def loudness_summary(err):
    s = err[err.rfind("Summary:"):]
    grab = lambda lab: float(m.group(1)) if (m := re.search(rf"{lab}:\s+(-?[\d.]+)", s)) else None
    return {"lufs_i": grab("I"), "lra": grab("LRA"), "true_peak_db": grab("Peak")}


def measure(t):
    dur, rate, ch = ffprobe(t["path"])
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(t["path"]), "-af",
                          f"silencedetect=noise={SILENCE_DB}dB:d={SILENCE_MIN_S},ebur128=peak=true:framelog=quiet",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    silences, start = [], None
    for m in re.finditer(r"silence_(start|end): (-?[\d.]+)", err):
        if m.group(1) == "start":
            start = float(m.group(2))
        elif start is not None:
            silences.append((start, float(m.group(2))))
            start = None
    if start is not None:
        silences.append((start, dur))
    in_s = next((e for s, e in silences if s <= 0.001), 0.0)
    out_s = next((s for s, e in reversed(silences) if e >= dur - 0.02), dur)
    if out_s <= in_s:
        die(f"{rel(t['path'])}: cả file là im lặng")
    loud = loudness_summary(err)
    if loud["lufs_i"] is None:
        die(f"{rel(t['path'])}: không đo được loudness")
    start_sample, end_sample = round(in_s * rate), round(out_s * rate)
    return {"file_s": dur, "rate": rate, "channels": ch, "start_sample": start_sample, "end_sample": end_sample,
            "in_s": start_sample / rate, "out_s": end_sample / rate, **loud}


def filter_graph(tracks, xf, limit_db):
    parts = []
    for i, t in enumerate(tracks):
        parts.append(f"[{i}:a]atrim=start_sample={t['start_sample']}:end_sample={t['end_sample']},asetpts=PTS-STARTPTS,"
                     f"aresample={SR}:resampler=soxr,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                     f"volume={t['gain_db']:.3f}dB[t{i}]")
    n = len(tracks)
    if xf > 0 and n > 1:
        cur = "t0"
        for i in range(1, n):
            parts.append(f"[{cur}][t{i}]acrossfade=d={xf:g}:c1=qsin:c2=qsin[x{i}]")
            cur = f"x{i}"
    else:
        parts.append("".join(f"[t{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1[x0]")
        cur = "x0"
    parts.append(f"[{cur}]aresample={SR * OVERSAMPLE}:resampler=soxr,"
                 f"alimiter=limit={10 ** (limit_db / 20):.5f}:attack=5:release=50:level=0:latency=1,"
                 f"aresample={SR}:resampler=soxr[out]")
    return ";".join(parts)


def render_once(tracks, xf, limit_db, out_wav):
    cmd = ["ffmpeg", "-v", "error", "-y"]
    for t in tracks:
        cmd += ["-i", str(t["path"])]
    cmd += ["-filter_complex", filter_graph(tracks, xf, limit_db), "-map", "[out]", "-ar", str(SR),
            "-c:a", "pcm_s24le", str(out_wav)]
    if subprocess.run(cmd).returncode:
        die("ffmpeg lỗi khi ghép")
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(out_wav), "-af",
                          "ebur128=peak=true:framelog=quiet", "-f", "null", "-"], capture_output=True, text=True).stderr
    return {**loudness_summary(err), "duration_s": ffprobe(out_wav)[0]}


def render_local(album, a):
    tracks = load_tracks(album)
    xf = crossfade_of(album, a.crossfade)
    print(f"{album.name}: đo {len(tracks)} bài (im lặng hai đầu, loudness)…", flush=True)
    with ThreadPoolExecutor(MEASURE_JOBS) as ex:
        for t, m in zip(tracks, ex.map(measure, tracks)):
            t.update(m, gain_db=TARGET_LUFS - m["lufs_i"])
    short = [t["track_no"] for t in tracks if t["out_s"] - t["in_s"] < 2 * xf]
    if short:
        die(f"bài {short} ngắn hơn 2 lần crossfade")
    out_wav = album / "audio" / "master" / f"{album.name}.wav"
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    limit_db = TP_MAX - LIMIT_MARGIN_DB
    for attempt in range(1, RENDER_TRIES + 1):
        print(f"ghép lần {attempt}: crossfade {xf:g} s, limiter {limit_db:.1f} dB…", flush=True)
        res = render_once(tracks, xf, limit_db, out_wav)
        print(f"  {res['duration_s'] / 60:.2f} phút · {res['lufs_i']} LUFS · true peak {res['true_peak_db']} dBTP", flush=True)
        off = TARGET_LUFS - res["lufs_i"]
        if abs(off) <= LUFS_TOL and res["true_peak_db"] <= TP_MAX:
            break
        if attempt == RENDER_TRIES:
            break
        if abs(off) > LUFS_TOL:
            for t in tracks:
                t["gain_db"] += off
        if res["true_peak_db"] > TP_MAX:
            limit_db -= res["true_peak_db"] - TP_MAX + 0.2
    if not a.no_mp3:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(out_wav), "-c:a", "libmp3lame", "-b:a", "320k",
                        str(out_wav.with_suffix(".mp3"))], check=True)
    pos, rows = 0.0, []
    for t in tracks:
        dur = t["out_s"] - t["in_s"]
        rows.append({"track_no": t["track_no"], "slug": t["slug"], "title": t["title"], "type": t["type"],
                     "audio": t["audio"], "in_s": round(t["in_s"], 3), "out_s": round(t["out_s"], 3),
                     "gain_db": round(t["gain_db"], 2), "start_s": round(pos, 3), "end_s": round(pos + dur, 3)})
        pos += dur - xf
    data = {"album": album.name, "master": f"audio/master/{album.name}.wav",
            "duration_s": round(res["duration_s"], 3), "crossfade_s": xf, "target_lufs": TARGET_LUFS, "tracks": rows,
            "measured": {"rendered": str(date.today()), "lufs_i": res["lufs_i"], "true_peak_db": res["true_peak_db"],
                         "lra": res["lra"], "limiter_db": round(limit_db, 2), "renders": attempt,
                         "expected_duration_s": round(pos + xf, 3),
                         "sources": [{"track_no": t["track_no"], "file_s": round(t["file_s"], 3),
                                      "lufs_i": t["lufs_i"], "true_peak_db": t["true_peak_db"]} for t in tracks]}}
    (album / "assembly.json").write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    return write_report(album, data)


def checks(album, d):
    rules, _ = rules_of(album)
    m, tr = d["measured"], d["tracks"]
    out = []
    add = lambda ok, what, got: out.append(("✅" if ok is True else "❌" if ok is False else "⚠️", what, got))
    lm = rules.get("length_min")
    mins = d["duration_s"] / 60
    if isinstance(lm, list) and len(lm) == 2:
        add(lm[0] <= mins <= lm[1], f"độ dài trong {lm[0]}–{lm[1]} phút (album_rules `length_min`)", f"{mins:.1f} phút")
    else:
        add(None, "độ dài (album_rules không có `length_min`)", f"{mins:.1f} phút")
    add(abs(m["lufs_i"] - d["target_lufs"]) <= LUFS_TOL, f"loudness master {d['target_lufs']:g} ± {LUFS_TOL:g} LUFS",
        f"{m['lufs_i']} LUFS (LRA {m['lra']} LU)")
    add(m["true_peak_db"] <= TP_MAX, f"không clip: true peak ≤ {TP_MAX:g} dBTP", f"{m['true_peak_db']} dBTP")
    diff = d["duration_s"] - m["expected_duration_s"]
    add(abs(diff) <= DURATION_TOL_S, f"độ dài = Σ bài (đã bỏ im lặng hai đầu) − {len(tr) - 1} × {d['crossfade_s']:g} s",
        f"{d['duration_s']:.3f} s vs {m['expected_duration_s']:.3f} s ({diff:+.3f})")
    spans = [b["start_s"] - a["start_s"] for a, b in zip(tr, tr[1:])] + [d["duration_s"] - tr[-1]["start_s"]]
    add(len(tr) >= 3 and min(spans) >= CHAPTER_MIN_S and tr[0]["start_s"] == 0,
        f"chapters YouTube: ≥ 3 bài, bài 1 ở 0:00, mỗi chapter ≥ {CHAPTER_MIN_S} s", f"{len(tr)} bài, ngắn nhất {min(spans):.0f} s")
    src = {s["track_no"]: s for s in m["sources"]}
    for t in tr:
        s = src[t["track_no"]]
        lead, tail = t["in_s"], s["file_s"] - t["out_s"]
        if max(lead, tail) > LONG_EDGE_S:
            add(None, f"bài {t['track_no']}: im lặng số dài ở mép file (đã bỏ)", f"đầu {lead:.1f} s · cuối {tail:.1f} s")
        over = s["true_peak_db"] + t["gain_db"] - m["limiter_db"]
        if over > LIMITER_WARN_DB:
            add(None, f"bài {t['track_no']}: limiter ép đỉnh ~{over:.1f} dB (bài gốc nhỏ, phải tăng gain)",
                f"gain {t['gain_db']:+.1f} dB, đỉnh gốc {s['true_peak_db']} dBTP")
    return out


def write_report(album, d):
    res = checks(album, d)
    m = d["measured"]
    src = {s["track_no"]: s for s in m["sources"]}
    L = [f"# Ghép album: {d['album']}", "",
         f"_audio-album-assembly `assemble.py` · {m['rendered']} · crossfade {d['crossfade_s']:g} s equal-power · "
         f"{d['target_lufs']:g} LUFS · true peak ≤ {TP_MAX:g} dBTP · sinh từ assembly.json, đừng sửa tay._", "",
         f"Master: `{d['master']}` (+ `.mp3`) · **{clock(d['duration_s'])}** ({d['duration_s'] / 60:.1f} phút) · "
         f"{len(d['tracks'])} bài · không cắt, không sửa gì trong bài: chỉ bỏ im lặng số (< {SILENCE_DB} dBFS) ở hai "
         "đầu file và cân loudness.", "", "## Tracklist", "",
         "| # | Chapter | Bài | Loại | Dài (đã bỏ im lặng) | Bỏ đầu / cuối | Loudness gốc | Gain |",
         "|---|---|---|---|---|---|---|---|"]
    for t in d["tracks"]:
        s = src[t["track_no"]]
        L.append(f"| {t['track_no']} | {clock(t['start_s'])} | {t['title']} | {t['type'] or '—'} | "
                 f"{clock(t['out_s'] - t['in_s'])} | {t['in_s']:.2f} s / {s['file_s'] - t['out_s']:.2f} s | "
                 f"{s['lufs_i']} LUFS | {t['gain_db']:+.1f} dB |")
    L += ["", "Chapters (tính từ `start_s` = lúc bài bắt đầu fade-in; upload-youtube-publish đọc assembly.json):", "", "```"]
    L += [f"{clock(t['start_s'])} {t['title']}" for t in d["tracks"]]
    L += ["```", "", "## Kiểm tra", "", "| | Kiểm | Kết quả |", "|---|---|---|"]
    L += [f"| {mark} | {what} | {got} |" for mark, what, got in res]
    (album / "assembly.md").write_text("\n".join(L) + "\n")
    for mark, what, got in res:
        print(f"{mark} {what}: {got}")
    return CHECK_FAILED if any(mark == "❌" for mark, _, _ in res) else 0


def main():
    ap = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render")
    r.add_argument("album")
    r.add_argument("--crossfade", type=float, help="giây crossfade (mặc định: album_rules.md crossfade_s)")
    r.add_argument("--no-mp3", action="store_true")
    r.add_argument("--local", action="store_true",
                   help="ghép trên máy này (server tự dùng; trên Mac chỉ khi server không lên được VÀ CEO đồng ý)")
    p = sub.add_parser("report")
    p.add_argument("album")
    a = ap.parse_args()
    album = resolve(a.album)
    if a.cmd == "report":
        f = album / "assembly.json"
        if not f.exists():
            die(f"chưa có {rel(f)}: chạy render trước")
        sys.exit(write_report(album, json.loads(f.read_text())))
    if not a.local:
        render_remote(album, a)
    sys.exit(render_local(album, a))


if __name__ == "__main__":
    main()

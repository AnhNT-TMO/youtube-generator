#!/usr/bin/env python3
USAGE = """video-upscale (Mac): đẩy clip lên GPU server, upscale 1920×1080 bằng SeedVR2 3B theo cụm, kéo kết quả về.

  upscale.py setup                         một lần / khi hỏng: repo SeedVR2 đã vá, .venv, model 3B trên server
  upscale.py push PATH...                  rsync clip (*.mp4, bỏ *.try*, _rejected/) lên ~/video-upscale/src/<PATH>
  upscale.py run PATH... [--per-run 10]    push rồi chạy nền trên server; clip đã có bản 1080p thì bỏ qua
  --profile shared|low|full|2k             (run/night/status/pull) bộ config đã đo, mặc định shared ≤30 GB; 2k ra ~/video_sources_2k
  upscale.py night --first LIST [--batches 20] lượt đêm: LIST trước rồi mọi clip đạt còn thiếu, nghỉ 60 s/cụm,
                                           chạy độc lập trên server, xóa bản gốc khi xong
  upscale.py night --first LIST --until "2026-10-07 08:00"
                                           chạy liên tục mọi clip còn thiếu tới mốc giờ (giờ Mac), không trần số clip
  upscale.py status                        tiến độ, nhiệt độ, cụm đang chạy, clip lỗi
  upscale.py log [N]                       N dòng cuối log tổng
  upscale.py stop                          dừng (cụm đang chạy bị hủy; clip đã xong giữ nguyên)
  upscale.py pull PATH... --dest DIR       kéo bản 1080p của <PATH> về DIR/<PATH>

PATH là đường dẫn tương đối từ gốc repo (file hoặc thư mục). Bản 1080p nằm ở ~/video_sources/<library>/<đường dẫn
trong bộ resource>, library lấy từ trường "library" của <bộ>/resource.json (vd. image_source → christmas);
clip ngoài bộ có library → ~/video_sources/_other/<PATH>.
"""
import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
R = "video-upscale"
LIBRARY = "video_sources"
PROFILES = ["shared", "low", "full", "2k"]
PROFILE_LIBRARY = {"2k": "video_sources_2k"}
UNIT = "video-upscale"
FILTER = ["--prune-empty-dirs", "--exclude=_rejected/", "--exclude=*.try*", "--include=*/", "--include=*.mp4",
          "--exclude=*"]


def renv():
    p = HERE.parent / "remote.env"
    if not p.exists():
        sys.exit(f"thiếu {p}: chép từ remote.env.example rồi điền")
    env = {}
    for line in p.read_text().splitlines():
        k, sep, v = line.partition("=")
        if sep and not line.lstrip().startswith("#"):
            env[k.strip()] = os.path.expandvars(v.strip())
    if not env.get("VU_REMOTE"):
        sys.exit(f"điền VU_REMOTE trong {p}")
    return env


def ssh(env, cmd, **kw):
    return subprocess.run(["ssh", "-i", env["VU_KEY"], "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
                           env["VU_REMOTE"], cmd], **kw)


def rsh(env):
    return f"ssh -i {shlex.quote(env['VU_KEY'])} -o BatchMode=yes"


def reach(env):
    if ssh(env, "true", capture_output=True).returncode:
        sys.exit(f"GPU server {env['VU_REMOTE']} không kết nối được: job chờ server, không chạy trên Mac")
    ssh(env, f"mkdir -p {R}/scripts {R}/src {R}/log {LIBRARY}", check=True)
    subprocess.run(["rsync", "-a", "-e", rsh(env), str(HERE / "upscale_server.py"),
                    f"{env['VU_REMOTE']}:{R}/scripts/upscale_server.py"], check=True)
    ssh(env, f"cat > {R}/libraries.json", input=json.dumps(libraries(), indent=1), text=True, check=True)


def libraries():
    out = {}
    for rj in sorted([*REPO.glob("*/resource.json"), *REPO.glob("resource/*/resource.json"),
                      *REPO.glob("channel/*/*/resource.json")]):
        try:
            lib = json.loads(rj.read_text()).get("library")
        except ValueError:
            continue
        if lib:
            out[str(rj.parent.relative_to(REPO))] = lib
    return out


def library_path(rel, libs):
    for prefix, lib in libs.items():
        if rel == prefix or rel.startswith(prefix + "/"):
            return f"{lib}{rel[len(prefix):]}"
    return f"_other/{rel}"


def repo_path(lib_rel, libs):
    head, _, rest = lib_rel.partition("/")
    if head == "_other":
        return rest
    for prefix, lib in libs.items():
        if lib == head:
            return f"{prefix}/{rest}"
    return None


def lib_root(profile):
    return PROFILE_LIBRARY.get(profile, LIBRARY)


def rel_paths(paths):
    out = []
    for p in paths:
        a = Path(p).expanduser()
        a = (a if a.is_absolute() else Path.cwd() / a).resolve()
        try:
            rel = a.relative_to(REPO)
        except ValueError:
            sys.exit(f"{p} nằm ngoài repo {REPO}")
        if not a.exists():
            sys.exit(f"không có {rel}")
        out.append(str(rel))
    return out


def cmd_setup(_):
    env = renv()
    reach(env)
    sys.exit(ssh(env, f"python3 {R}/scripts/upscale_server.py setup").returncode)


def push(env, rels):
    for rel in rels:
        src = f"{REPO}/./{rel}" + ("/" if (REPO / rel).is_dir() else "")
        subprocess.run(["rsync", "-aR", *FILTER, "-e", rsh(env), src, f"{env['VU_REMOTE']}:{R}/src/"],
                       check=True)
        print(f"đã đẩy {rel}", flush=True)


def cmd_push(a):
    env = renv()
    reach(env)
    push(env, rel_paths(a.paths))


def cmd_run(a):
    env = renv()
    rels = rel_paths(a.paths)
    reach(env)
    if not ssh(env, f"systemctl --user is-active --quiet {UNIT}").returncode:
        sys.exit("đang có một lượt chạy: `upscale.py status` / `upscale.py stop`")
    if not a.no_push:
        push(env, rels)
    start_unit(env, [*rels, "--profile", a.profile, "--per-run", str(a.per_run), "--pause-c", str(a.pause_c), "--resume-c", str(a.resume_c),
                     "--start-c", str(a.start_c), "--rest", str(a.rest)])
    print("đã chạy nền trên server; xem `upscale.py status` / `upscale.py log`")


def cmd_status(a):
    env = renv()
    reach(env)
    ssh(env, f"python3 {R}/scripts/upscale_server.py status --profile {a.profile}; echo '-- log:'; tail -n 6 {R}/log/master.log 2>/dev/null; "
             "echo '-- guard kills:'; tail -n 3 ~/youtube-guard/kills.log 2>/dev/null || echo none")


def cmd_log(a):
    env = renv()
    ssh(env, f"tail -n {a.n} {R}/log/master.log")


def cmd_stop(_):
    env = renv()
    sys.exit(ssh(env, f"systemctl --user stop {UNIT} '{UNIT}-chunk-*.scope' && echo đã dừng").returncode)


def cmd_pull(a):
    env = renv()
    dest = Path(a.dest).expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)
    libs = libraries()
    for p in a.paths:
        rel = p.strip("/")
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        src = f"{env['VU_REMOTE']}:{lib_root(a.profile)}/{library_path(rel, libs)}"
        if (REPO / rel).is_dir():
            target.mkdir(parents=True, exist_ok=True)
            src, dst = src + "/", str(target) + "/"
        else:
            dst = str(target)
        subprocess.run(["rsync", "-a", *FILTER, "-e", rsh(env), src, dst], check=True)
        print(f"đã kéo {rel} → {target}", flush=True)


def accepted_clips(set_dir):
    out = []
    for card in sorted((REPO / set_dir).glob("*/*/*.json")):
        if card.name == "shots.json":
            continue
        try:
            v = json.loads(card.read_text()).get("video") or {}
        except ValueError:
            continue
        mp4 = card.with_name(v.get("file") or f"{card.stem}.mp4")
        if v.get("status") == "ok" and mp4.exists():
            out.append(str(mp4.relative_to(REPO)))
    return out


def start_unit(env, args):
    inner = (f"cd ~/{R} && echo \"== $(date '+%F %T') run {shlex.join(args)}\" >> log/master.log && "
             f"exec python3 -u scripts/upscale_server.py run {shlex.join(args)} >> log/master.log 2>&1")
    ssh(env, f"systemctl --user reset-failed {UNIT} 2>/dev/null; systemd-run --user --unit={UNIT} --collect "
             f"-p MemoryMax=2G bash -c {shlex.quote(inner)}", check=True)


def cmd_night(a):
    import tempfile
    import time
    env = renv()
    reach(env)
    if not ssh(env, f"systemctl --user is-active --quiet {UNIT}").returncode:
        sys.exit("đang có một lượt chạy: `upscale.py status` / `upscale.py stop`")
    linger = ssh(env, "loginctl show-user $USER -p Linger --value", capture_output=True, text=True).stdout.strip()
    if linger != "yes":
        sys.exit("server chưa bật linger: lượt chạy sẽ chết khi hết phiên ssh. Chạy trên server: loginctl enable-linger $USER")
    first = []
    for f in a.first:
        first += [x.strip() for x in Path(f).read_text().splitlines() if x.strip()]
    order = list(first)
    for f in a.then:
        order += [x.strip() for x in Path(f).read_text().splitlines() if x.strip()]
    for set_dir in a.set:
        order += accepted_clips(set_dir)
    libs = libraries()
    found = ssh(env, f"mkdir -p {lib_root(a.profile)} && cd {lib_root(a.profile)} && find . -name '*.mp4' -printf '%P\\n'", capture_output=True, text=True).stdout
    done = {repo_path(x, libs) for x in found.split()} - {None}
    seen, todo = set(), []
    for rel in order:
        if rel in seen or rel in done or not (REPO / rel).exists():
            continue
        seen.add(rel)
        todo.append(rel)
    priority = [rel for rel in todo if rel in set(first)]
    until = time.mktime(time.strptime(a.until, "%Y-%m-%d %H:%M")) if a.until else 0
    if a.until and until <= time.time():
        sys.exit(f"--until {a.until} đã qua")
    rest = [rel for rel in todo if rel not in set(first)]
    pick = priority + (rest if until else rest[:max(a.batches * a.per_run - len(priority), 0)])
    left = len(todo) - len(pick)
    print(f"{len(done)} clip đã có bản 1080p trên server; lượt này {len(pick)} clip ({len(priority)} ưu tiên từ --first, "
          + (f"xong thì nhường GPU cho {a.yield_unit}; " if a.yield_unit else "chạy song song với video album; ")
          + (f"chạy liên tục tới {a.until}, cụm không kịp xong thì để lượt sau" if until else f"{a.batches} cụm × {a.per_run}")
          + f"), còn {left} clip cho các lượt sau")
    if not pick:
        return
    stamp = time.strftime("%Y%m%d-%H%M%S")
    with tempfile.TemporaryDirectory() as tmp:
        lst = Path(tmp) / f"night-{stamp}.txt"
        lst.write_text("\n".join(priority + ["---"] + pick[len(priority):]) + "\n")
        files = Path(tmp) / "files.txt"
        files.write_text("\n".join(pick) + "\n")
        subprocess.run(["rsync", "-a", "-W", f"--files-from={files}", "-e", rsh(env), f"{REPO}/", f"{env['VU_REMOTE']}:{R}/src/"],
                       check=True)
        subprocess.run(["rsync", "-a", "-e", rsh(env), str(lst), f"{env['VU_REMOTE']}:{R}/log/"], check=True)
    start_unit(env, ["--list", f"log/night-{stamp}.txt", "--profile", a.profile, "--per-run", str(a.per_run),
                     "--rest", str(a.rest), "--pause-c", str(a.pause_c), "--resume-c", str(a.resume_c),
                     "--start-c", str(a.start_c), "--yield-unit", a.yield_unit] + (["--until", str(int(until))] if until else []))
    print(f"đã chạy nền trên server (không cần giữ ssh / máy Mac); danh sách: ~/{R}/log/night-{stamp}.txt; "
          "xem `upscale.py status`")


def main():
    ap = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup").set_defaults(fn=cmd_setup)
    p = sub.add_parser("push")
    p.add_argument("paths", nargs="+")
    p.set_defaults(fn=cmd_push)
    r = sub.add_parser("run")
    r.add_argument("paths", nargs="+")
    r.add_argument("--per-run", type=int, default=10, help="số clip mỗi lần nạp model (mặc định 10)")
    r.add_argument("--pause-c", type=int, default=83, help="GPU ≥ mức này thì cụm tạm dừng")
    r.add_argument("--resume-c", type=int, default=70, help="GPU ≤ mức này thì chạy tiếp")
    r.add_argument("--start-c", type=int, default=70, help="cụm mới chỉ bắt đầu khi GPU ≤ mức này")
    r.add_argument("--rest", type=int, default=0, help="giây nghỉ giữa hai cụm")
    r.add_argument("--profile", choices=PROFILES, default="shared", help="bộ config đã đo (references/benchmark.md): shared ≤30 GB (mặc định), low ~24 GB, full 74 GB nhanh nhất, 2k 2560×1440")
    r.add_argument("--no-push", action="store_true", help="clip đã có trên server, không rsync lại")
    r.set_defaults(fn=cmd_run)
    n = sub.add_parser("night", help="lượt chạy đêm: ưu tiên --first, rồi mọi clip đạt của --set, bỏ clip đã có ở ~/video_sources")
    n.add_argument("--first", nargs="*", default=[], help="file danh sách clip làm trước (vd. clips.txt của album)")
    n.add_argument("--then", nargs="*", default=[], help="file danh sách clip đứng đầu tầng 2 (sau --first, trước phần còn lại của --set)")
    n.add_argument("--set", nargs="*", default=["image_source"], help="bộ resource lấy clip đạt (video.status ok)")
    n.add_argument("--batches", type=int, default=20, help="số clip đêm nay = batches × per-run (20 × 10 ≈ 8–10 giờ); clip gom theo độ dài nên số cụm thực tế có thể nhiều hơn")
    n.add_argument("--until", help="\"YYYY-MM-DD HH:MM\" giờ Mac: chạy liên tục mọi clip còn thiếu tới mốc này (bỏ trần --batches)")
    n.add_argument("--per-run", type=int, default=10)
    n.add_argument("--profile", choices=PROFILES, default="shared", help="bộ config đã đo (references/benchmark.md): shared ≤30 GB (mặc định), low ~24 GB, full 74 GB nhanh nhất, 2k 2560×1440")
    n.add_argument("--rest", type=int, default=60, help="giây cho GPU nghỉ sau mỗi cụm")
    n.add_argument("--pause-c", type=int, default=83)
    n.add_argument("--resume-c", type=int, default=70)
    n.add_argument("--start-c", type=int, default=70)
    n.add_argument("--yield-unit", default="montage-render", help="xong clip ưu tiên thì chờ unit này xong ('' = chạy song song, khi VRAM đủ cho cả hai)")
    n.set_defaults(fn=cmd_night)
    st = sub.add_parser("status")
    st.add_argument("--profile", choices=PROFILES, default="shared")
    st.set_defaults(fn=cmd_status)
    lg = sub.add_parser("log")
    lg.add_argument("n", nargs="?", type=int, default=40)
    lg.set_defaults(fn=cmd_log)
    sub.add_parser("stop").set_defaults(fn=cmd_stop)
    pl = sub.add_parser("pull")
    pl.add_argument("paths", nargs="+", help="đường dẫn tương đối từ gốc repo")
    pl.add_argument("--dest", required=True, help="thư mục gốc trên Mac để đặt cây kết quả")
    pl.add_argument("--profile", choices=PROFILES, default="shared")
    pl.set_defaults(fn=cmd_pull)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
USAGE = """video-generator: still thumbnail -> 5-min loop video -> full-length music video.

    video.py frame DIR [--at 30]              # step 1 helper: one still, to tune DIR/video.json (cinema: on the server)
    video.py qa DIR                           # cinema channels: seam, lettering, still bar, edges, flicker -> PASS/FAIL
    video.py variant DIR [--seed N]           # cinema channels: pick this video's camera + parallax + particles +
                                              #   lights from the channel's cinema_pool, unlike its last videos
    video.py loop  DIR [--local] [--seconds N] # step 1: thumbnail -> 5-min seamless loop + logo intro (N: short preview)
    video.py batch channel/<name> [--local]   # step 1 for every idea / album / single with a thumbnail but no loop
    video.py album DIR AUDIO [--local]        # step 2: loop -> video as long as AUDIO, + spectrum bars
    video.py package ALBUM [--no-short] [--force] [--dry-run]
                                              # step 3: ONE zip for the album + its Short (ALBUM/short/): album video,
                                              #   thumbnails, youtube.md, paste fields + short/ with the same for the
                                              #   Short, README.txt with the upload order; built on the server -> S3
    video.py short DIR [--local]              # Short (DIR = channel/<name>/albums/NNN-slug/short, or the old
                                              #   channel/<name>/shorts/NNN-slug, with short.json + 9:16 thumbnail.png):
                                              #   loop as long as the clip + spectrum + lyric lines + hook + CTA,
                                              #   1080x1920; render only (it ships in the album's zip)
DIR sits inside channel/<name>/ (an idea, album or single folder, or an album's short/) and holds thumbnail.png. An album made from an
idea (plan.yaml sources.idea) that has no thumbnail.png / video.json / video/loop.mp4 of its own uses the idea's.
Config layers: tool defaults < channel/<name>/video.json < DIR/video.json.
Everything is written to DIR/video/.

loop / batch / album render on the GPU server from remote.env (next to this skill's SKILL.md) by default:
scripts, the channel's image_source/ and the job's inputs are synced over,
unchanged files are not uploaded again. Loops come back to DIR/video/; the full video of `album` stays on the
server (only its ffprobe + two check frames come back; --download also fetches the mp4) and `package` zips it there
with DIR/youtube.md, the thumbnails and the Short's part, and uploads the zip to S3 through presigned requests signed
with this Mac's AWS credentials (bucket/prefix in remote.env). `album` runs `package` itself only when youtube.md and
the Short (rendered + short/youtube.md) are both ready; otherwise it prints the `package` command to run later.
--local renders on this Mac instead (heavy: only when the server is unreachable and the owner agreed).
"""
import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SK = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import config  # noqa: E402  (stdlib only, safe before the venv exists)

REPO = config.REPO


def _remote_env():
    env = {"VG_REMOTE": "", "VG_KEY": "~/.ssh/id_rsa", "VG_JOBS": "16", "VG_DIR": "video-generator", "VG_ENCODER": "nvenc",
           "VG_S3_BUCKET": "", "VG_S3_REGION": "ap-northeast-1", "VG_S3_PREFIX": "", "VG_AWS_PROFILE": ""}
    path = os.path.join(SK, "remote.env")
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = os.path.expandvars(v.strip())
    env.update({k: v for k, v in os.environ.items() if k in env})
    env["VG_KEY"] = os.path.expanduser(env["VG_KEY"])
    return env


RENV = _remote_env()


def venv_python(extra=()):
    py = os.path.join(SK, ".venv", "bin", "python")
    if not os.path.exists(py):
        print("creating the skill venv (first run)...", flush=True)
        subprocess.run([sys.executable, "-m", "venv", os.path.join(SK, ".venv")], check=True)
        subprocess.run([py, "-m", "pip", "install", "-q", "-r",
                        os.path.join(SK, "requirements.txt")], check=True)
    for mod in extra:
        if subprocess.run([py, "-c", f"import {mod}"], capture_output=True).returncode:
            print(f"installing {mod} into the skill venv...", flush=True)
            subprocess.run([py, "-m", "pip", "install", "-q", mod], check=True)
    return py


class Job:

    def __init__(self, d):
        self.dir = os.path.abspath(d)
        rel = os.path.relpath(self.dir, REPO).split(os.sep)
        if len(rel) < 3 or rel[0] != "channel":
            sys.exit(f"{d}: expected a folder inside channel/<name>/")
        self.channel = rel[1]
        self.channel_dir = os.path.join(REPO, "channel", self.channel)
        self.layers = [os.path.join(self.channel_dir, "video.json")]
        if not os.path.exists(self.layers[0]):
            sys.exit(f"missing {self.layers[0]}")
        self.idea = source_idea(self.dir)
        look = [self.dir] + ([self.idea] if self.idea else [])
        own = next((os.path.join(d, "video.json") for d in look if os.path.exists(os.path.join(d, "video.json"))), None)
        if own:
            self.layers.append(own)
        self.image = next((os.path.join(d, f) for d in look for f in
                           ("thumbnail.png", "thumbnail.jpg", "thumbnail.jpeg")
                           if os.path.exists(os.path.join(d, f))), None)
        if self.image and self.idea and not self.image.startswith(self.idea + os.sep):
            newer = next((os.path.join(self.idea, f) for f in ("thumbnail.png", "thumbnail.jpg")
                          if os.path.exists(os.path.join(self.idea, f))
                          and os.path.getmtime(os.path.join(self.idea, f)) > os.path.getmtime(self.image)), None)
            if newer:
                print(f"⚠ {os.path.relpath(newer, REPO)} is newer than the album's thumbnail: using the album's; "
                      "run album-plan `album_plan.py sync <album>` to take the idea's", flush=True)
        self.album_short = len(rel) == 5 and rel[2] == "albums" and rel[4] == "short"
        self.short = self.album_short or (len(rel) >= 4 and rel[2] == "shorts")
        self.is_album = len(rel) == 4 and rel[2] == "albums"
        self.name = f"{rel[3]}-short" if self.album_short else os.path.basename(self.dir)
        self.out = os.path.join(self.dir, "video")
        self.id = re.sub(r"[^A-Za-z0-9_.-]+", "__", "/".join(rel[1:]))

    def need_image(self):
        if not self.image:
            sys.exit(f"{self.dir}: no thumbnail.png / thumbnail.jpg")
        os.makedirs(self.out, exist_ok=True)

    def presets(self):
        return sum((["--preset", p] for p in self.layers), [])

    def config(self):
        return config.merge_files(self.layers, short=self.short)

    def frame_env(self):
        if not self.short:
            return None
        w, h = self.config()["short"]["frame"]
        return dict(os.environ, VG_FRAME=f"{w}x{h}")


def source_idea(d):
    f = os.path.join(d, "plan.yaml")
    if not os.path.exists(f):
        return None
    m = re.search(r"^sources:\s*\n(?:[ \t]+.*\n)*?[ \t]+idea:\s*['\"]?([^'\"\n#]+?)['\"]?\s*$", open(f).read(), re.M)
    if not m or m.group(1) in ("null", "~"):
        return None
    p = os.path.join(REPO, m.group(1).strip())
    p = os.path.dirname(p) if p.endswith((".yaml", ".yml")) else p
    return p if os.path.isdir(p) else None


def run(cmd, **kw):
    print("$ " + " ".join(os.path.relpath(c, REPO) if c.startswith(REPO) else c
                          for c in cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


def album_out(job, a):
    return a.out or os.path.join(job.out, job.name + ".mp4")


def local_loop(job, a):
    run([venv_python(), os.path.join(HERE, "make_loop.py"), job.image,
         os.path.join(job.out, "loop.mp4"), "--seam-check", "--jobs", str(a.jobs or 4)]
        + job.presets() + (["--encoder", a.encoder] if a.encoder else []))


def local_album(job, a):
    loop = os.path.join(job.out, "loop.mp4")
    idea_loop = os.path.join(job.idea, "video", "loop.mp4") if job.idea else None
    if not os.path.exists(loop) and idea_loop and os.path.exists(idea_loop) and job.image.startswith(job.idea + os.sep):
        loop = idea_loop
        print(f"using the idea's loop {os.path.relpath(loop, REPO)}", flush=True)
    if not os.path.exists(loop):
        local_loop(job, a)
    run([venv_python(), os.path.join(HERE, "extend.py"), loop, a.audio, album_out(job, a),
         "--jobs", str(a.jobs or 4)] + job.presets()
        + (["--encoder", a.encoder] if a.encoder else []))


LIMIT = ("G=~/youtube-guard/guard.py; if [ -f $G ]; then systemctl --user is-active --quiet youtube-guard || systemd-run --user --unit=youtube-guard --collect -p MemoryMax=256M python3 $G >/dev/null 2>&1; else echo \"WARNING: youtube-guard not installed on the server (pm-production/scripts/server_guard/guard.sh install)\" >&2; fi; "
         "S=~/.config/systemd/user/youtube.slice; [ -f $S ] || { mkdir -p ${S%/*} && printf \"[Unit]\\nDescription="
         "youtube project: every skill shares this cap (CLAUDE.md)\\n[Slice]\\nCPUQuota=%s%%\\nMemoryHigh=60%%\\n"
         "MemoryMax=70%%\\n\" $(( $(nproc) * 60 )) > $S && systemctl --user daemon-reload; }; "
         "systemd-run --user --scope --quiet --collect --slice=youtube.slice -- bash -c ")


def limited(cmd):
    return LIMIT + shlex.quote(cmd)


def _ssh(cmd):
    return ["ssh", "-i", RENV["VG_KEY"], "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
            "-o", "ServerAliveInterval=30", RENV["VG_REMOTE"], cmd]


def _ssh_json(cmd):
    print("$ ssh " + cmd, flush=True)
    r = subprocess.run(_ssh(cmd), stdout=subprocess.PIPE, text=True)
    if r.returncode:
        raise subprocess.CalledProcessError(r.returncode, cmd)
    return json.loads(r.stdout.strip().splitlines()[-1])


def _paths(job):
    R = RENV["VG_DIR"]
    return R, f"{R}/in/{job.id}", f"{R}/out/{job.id}"


def _rsync(src, dst, *extra):
    run(["rsync", "-a", "-e", f"ssh -i {RENV['VG_KEY']} -o BatchMode=yes", *extra, src,
         f"{RENV['VG_REMOTE']}:{dst}"])


def _scp_back(src, dst):
    run(["scp", "-q", "-i", RENV["VG_KEY"], "-o", "BatchMode=yes",
         f"{RENV['VG_REMOTE']}:{src}", dst])


def _push_base(job, out_clean=""):
    if not RENV["VG_REMOTE"]:
        sys.exit("no VG_REMOTE in remote.env")
    R, inp, out = _paths(job)
    ch = f"channel/{job.channel}/image_source"
    badge = job.config()["badge"]
    if badge["enabled"] and not (badge["path"] or "").startswith(ch + "/"):
        sys.exit(f"badge.path {badge['path']}: put the badge image in {ch}/ (only that folder is synced to the server)")
    if subprocess.run(_ssh("true")).returncode:
        sys.exit(f"GPU server {RENV['VG_REMOTE']} unreachable. Check the network/server and retry; --local renders "
                 "on this Mac (heavy) — ask the channel owner before using it.")
    run(_ssh(f"mkdir -p {R}/scripts {R}/repo/{ch} {inp} {out} && rm -f {out}/loop_intro.mp4 {out_clean}"))
    _rsync(HERE + "/", f"{R}/scripts/", "--exclude", "__pycache__")
    _rsync(os.path.join(SK, "requirements.txt"), f"{R}/requirements.txt")
    _rsync(os.path.join(job.channel_dir, "image_source") + "/", f"{R}/repo/{ch}/")
    run(_ssh(f"test -x {R}/.venv/bin/python || (python3 -m venv {R}/.venv && "
             f"{R}/.venv/bin/pip install -q -r {R}/requirements.txt)"))
    if job.config()["cinema"]["enabled"]:
        _rsync(os.path.join(SK, "requirements-gpu.txt"), f"{R}/requirements-gpu.txt")
        run(_ssh(f"{R}/.venv/bin/python -c 'import torch, transformers' 2>/dev/null || "
                 f"{R}/.venv/bin/python -m pip install -q -r {R}/requirements-gpu.txt"))
    return R, inp, out


def _push_config(cfg, dst):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(cfg, fh, indent=1)
        cfg_file = fh.name
    _rsync(cfg_file, dst, "--checksum")
    os.remove(cfg_file)


def remote(job, a, audio=None):
    t0 = time.time()
    R, inp, out = _push_base(job)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(job.config(), fh, indent=1)
        cfg_file = fh.name
    ext = os.path.splitext(job.image)[1]
    _rsync(job.image, f"{inp}/image{ext}")
    _rsync(cfg_file, f"{inp}/preset.json", "--checksum")
    os.remove(cfg_file)
    if audio:
        aext = os.path.splitext(audio)[1]
        _rsync(audio, f"{inp}/audio{aext}")
    print(f"[{time.time() - t0:.0f}s] inputs synced", flush=True)

    enc = a.encoder or RENV["VG_ENCODER"]
    jobs = a.jobs or cinema_jobs(job) or int(RENV["VG_JOBS"])
    P = f"~/{R}/.venv/bin/python"
    secs = getattr(a, "seconds", None)
    name = "loop_preview.mp4" if secs else "loop.mp4"
    mode = "--intro-only" if getattr(a, "intro_only", False) else (f"--seconds {secs}" if secs else "--seam-check")
    cmd = (f"cd {R}/scripts && export VG_REPO=~/{R}/repo && "
           f"{P} make_loop.py ~/{inp}/image{ext} ~/{out}/{name} --preset ~/{inp}/preset.json "
           f"--jobs {jobs} --encoder {enc} {mode}")
    if audio:
        cmd += (f" && {P} extend.py ~/{out}/loop.mp4 ~/{inp}/audio{aext} ~/{out}/video.mp4 "
                f"--preset ~/{inp}/preset.json --jobs {jobs} --encoder {enc}")
    if audio:
        cmd += (f" && cd ~/{out} && rm -f video.mp4.json check_*.png"
                f" && ffprobe -v error -print_format json -show_format -show_streams video.mp4 > video.mp4.json"
                f" && D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 video.mp4)"
                f" && ffmpeg -v error -y -ss 5 -i video.mp4 -frames:v 1 check_5s.png"
                f" && ffmpeg -v error -y -ss $(python3 -c \"print($D/2)\") -i video.mp4 -frames:v 1 check_mid.png")
    run(_ssh(limited(cmd)))
    print(f"[{time.time() - t0:.0f}s] rendered, downloading", flush=True)

    for name in ("loop.mp4", "loop_seam.mp4", "loop_intro.mp4", "loop_preview.mp4"):
        if subprocess.run(_ssh(f"test -f {out}/{name}")).returncode == 0:
            _scp_back(f"{out}/{name}", os.path.join(job.out, name))
    if audio:
        for name in ("video.mp4.json", "check_5s.png", "check_mid.png"):
            _scp_back(f"{out}/{name}", os.path.join(job.out, name))
        json.dump({"server": RENV["VG_REMOTE"], "video": f"~/{out}/video.mp4", "audio": os.path.relpath(audio, REPO),
                   "rendered": time.strftime("%Y-%m-%d %H:%M")},
                  open(os.path.join(job.out, "remote.json"), "w"), indent=1)
        if a.download:
            _scp_back(f"{out}/video.mp4", album_out(job, a))
        else:
            print(f"video stays on the server: {RENV['VG_REMOTE']}:~/{out}/video.mp4 "
                  f"(probe + check frames in {os.path.relpath(job.out, REPO)}/)", flush=True)
    print(f"[{time.time() - t0:.0f}s] done -> {os.path.relpath(job.out, REPO)}/", flush=True)


def cinema_jobs(job):
    return min(8, int(RENV["VG_JOBS"])) if job.config()["cinema"]["enabled"] else 0


def remote_frame(job, at, out, qa=False):
    R, inp, rout = _push_base(job)
    ext = os.path.splitext(job.image)[1]
    _rsync(job.image, f"{inp}/image{ext}")
    _push_config(job.config(), f"{inp}/preset.json")
    name = os.path.basename(out)
    what = "--qa" if qa else f"--frame {at}"
    run(_ssh(limited(f"cd {R}/scripts && export VG_REPO=~/{R}/repo && ~/{R}/.venv/bin/python make_loop.py "
                     f"~/{inp}/image{ext} ~/{rout}/{name} --preset ~/{inp}/preset.json {what}")))
    _scp_back(f"{rout}/{name}", out)


def short_spec(job):
    f = os.path.join(job.dir, "short.json")
    if not os.path.exists(f):
        sys.exit(f"{os.path.relpath(f, REPO)} chưa có: chạy skill video-shorts (`shorts.py new`) trước")
    spec = json.load(open(f))
    audio = os.path.join(REPO, spec["audio"])
    if not os.path.exists(audio):
        sys.exit(f"short.json trỏ tới audio không có: {spec['audio']}")
    return spec, audio


def remote_short(job, a):
    spec, audio = short_spec(job)
    dur = spec["out"] - spec["in"]
    cfg = job.config()
    cfg["loop_seconds"] = round(dur, 3)
    w, h = cfg["short"]["frame"]
    t0 = time.time()
    R, inp, out = _push_base(job, "video.mp4 video.mp4.json check_*.png overlays.json")
    ext, aext = os.path.splitext(job.image)[1], os.path.splitext(audio)[1]
    _rsync(job.image, f"{inp}/image{ext}")
    _rsync(audio, f"{inp}/audio{aext}")
    _rsync(os.path.join(job.dir, "short.json"), f"{inp}/short.json", "--checksum")
    _push_config(cfg, f"{inp}/preset.json")
    print(f"[{time.time() - t0:.0f}s] inputs synced", flush=True)
    enc = a.encoder or RENV["VG_ENCODER"]
    P = f"~/{R}/.venv/bin/python"
    marks = {"hook": 1.0, "mid": dur / 2, "cta": max(0.0, dur - 2.0)}
    cmd = (f"cd {R}/scripts && export VG_REPO=~/{R}/repo VG_FRAME={w}x{h} && "
           f"{P} short.py ~/{inp}/image{ext} ~/{inp}/audio{aext} ~/{inp}/short.json ~/{inp}/preset.json ~/{out} "
           f"--jobs {a.jobs or int(RENV['VG_JOBS'])} --encoder {enc} && cd ~/{out} && "
           f"ffprobe -v error -print_format json -show_format -show_streams video.mp4 > video.mp4.json"
           + "".join(f" && ffmpeg -v error -y -ss {t:.2f} -i video.mp4 -frames:v 1 check_{k}.png"
                     for k, t in marks.items()))
    run(_ssh(limited(cmd)))
    os.makedirs(job.out, exist_ok=True)
    for name in ["video.mp4.json", "overlays.json"] + [f"check_{k}.png" for k in marks]:
        _scp_back(f"{out}/{name}", os.path.join(job.out, name))
    json.dump({"server": RENV["VG_REMOTE"], "video": f"~/{out}/video.mp4", "audio": spec["audio"],
               "in": spec["in"], "out": spec["out"], "rendered": time.strftime("%Y-%m-%d %H:%M")},
              open(os.path.join(job.out, "remote.json"), "w"), indent=1)
    if a.download:
        _scp_back(f"{out}/video.mp4", os.path.join(job.out, job.name + ".mp4"))
    print(f"[{time.time() - t0:.0f}s] done: {w}×{h}, {dur:.1f} s · check frames + overlays.json in "
          f"{os.path.relpath(job.out, REPO)}/", flush=True)


def local_short(job, a):
    spec, audio = short_spec(job)
    cfg = job.config()
    cfg["loop_seconds"] = round(spec["out"] - spec["in"], 3)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(cfg, fh, indent=1)
        preset = fh.name
    tmp = tempfile.mkdtemp(prefix="vg-short-")
    try:
        run([venv_python(), os.path.join(HERE, "short.py"), job.image, audio, os.path.join(job.dir, "short.json"),
             preset, tmp, "--jobs", str(a.jobs or 4)] + (["--encoder", a.encoder] if a.encoder else []),
            env=job.frame_env())
        os.makedirs(job.out, exist_ok=True)
        shutil.move(os.path.join(tmp, "video.mp4"), os.path.join(job.out, job.name + ".mp4"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        os.remove(preset)


def rel(p):
    return os.path.relpath(p, REPO)


def human(n):
    return f"{n / 1e9:.2f} GB" if n >= 1e9 else f"{n / 1e6:.1f} MB" if n >= 1e5 else f"{n / 1e3:.1f} KB"


def s3_folder(job):
    parts = rel(job.dir).split(os.sep)[1:]
    if len(parts) == 3 and parts[1] == "singles":
        sm = os.path.join(job.dir, "single.md")
        m = re.search(r"^album:[ \t]*[\"']?([^\s#\"']+)", open(sm).read(), re.M) if os.path.exists(sm) else None
        if not m:
            print(f"⚠ {rel(sm)} has no album: zip goes to albums/{parts[2]}/", flush=True)
        return f"{parts[0]}/albums/{m.group(1) if m else parts[2]}", "single-"
    return "/".join(parts), ""


def on_server(job):
    return subprocess.run(_ssh(f"test -f {_paths(job)[2]}/video.mp4")).returncode == 0


def short_part(job):
    d = os.path.join(job.dir, "short")
    if not os.path.exists(os.path.join(d, "short.md")):
        return None, [f"no {rel(d)}/short.md (video-shorts `shorts.py new {rel(job.dir)}`)"]
    sj = Job(d)
    missing = []
    if not sj.image:
        missing.append("no short/thumbnail.png (thumbnail-prompt, 9:16)")
    if not os.path.exists(os.path.join(sj.out, "remote.json")) or not on_server(sj):
        missing.append(f"no render on the server (`video.py short {rel(d)}`)")
    if not os.path.exists(os.path.join(d, "youtube.md")):
        missing.append("no short/youtube.md (video-shorts)")
    return sj, missing


def package_command(job):
    return f"python3 {rel(os.path.abspath(__file__))} package {rel(job.dir)}"


def run_checks(job, sj, a):
    pub = os.path.join(REPO, ".claude", "skills", "upload-youtube-publish")
    pub_py = os.path.join(pub, ".venv", "bin", "python")
    shorts_py = os.path.join(REPO, ".claude", "skills", "video-shorts", "scripts", "shorts.py")
    tests = [("album", "publish.py check", [pub_py, os.path.join(pub, "scripts", "publish.py"), "check", job.dir])]
    if sj:
        tests.append(("short", "shorts.py check", [sys.executable, shorts_py, "check", sj.dir]))
    res, failed = {}, []
    for key, name, cmd in tests:
        if not os.path.exists(cmd[0]):
            print(f"⚠ upload-youtube-publish venv not found: {key} youtube.md not checked", flush=True)
            res[key] = "not checked (no venv)"
            continue
        print(f"$ {name} {rel(cmd[-1])}", flush=True)
        ok = subprocess.run(cmd).returncode == 0
        res[key] = "pass" if ok else ("fail, packaged with --force" if a.force else "fail")
        if not ok:
            failed.append(f"{name} {rel(cmd[-1])}")
    if failed and not a.force:
        sys.exit(f"chưa đóng gói: {' + '.join(failed)} còn ❌; sửa rồi chạy lại (--force để đóng gói vẫn)")
    return res


def publish_order(ch):
    f = os.path.join(REPO, "channel", ch, "publish.md")
    text = open(f).read() if os.path.exists(f) else ""
    out = []
    for head in ("Giờ đăng", "Thứ tự đăng"):
        m = re.search(rf"^## {head}[ \t]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
        for line in (m.group(1).splitlines() if m else []):
            line = line.rstrip().replace("**", "").replace("`", "")
            if line.strip() and not re.search(r"<[^>\n]+>", line) and not re.fullmatch(r"\s*\|[-:| ]+\|", line):
                out.append(line)
    return out


def stage_part(py, pkg_py, pj, pkg, thumb):
    rj = os.path.join(pj.out, "remote.json")
    src_audio = json.load(open(rj)).get("audio") if os.path.exists(rj) else None
    run([py, pkg_py, "stage", pkg, "--youtube-md", os.path.join(pj.dir, "youtube.md"), "--thumbnail", thumb,
         "--jpg", os.path.join(pj.dir, "thumbnail.jpg"), "--channel", pj.channel]
        + (["--source-audio", src_audio] if src_audio else []) + (["--vertical"] if pj.short else []))


def package(job, a):
    t0 = time.time()
    if job.short:
        if job.album_short:
            sys.exit(f"{rel(job.dir)} là Short của album: nó nằm trong zip của album → "
                     f"`{package_command(Job(os.path.dirname(job.dir)))}`")
        sys.exit(f"{rel(job.dir)} là Short bố cục cũ: `shorts.py migrate --channel {job.channel}` rồi "
                 "`video.py package channel/<ch>/albums/<album>` (một zip: album + short/)")
    job.need_image()
    dry = getattr(a, "dry_run", False)
    R, inp, out = _paths(job)
    ytmd = os.path.join(job.dir, "youtube.md")
    if not os.path.exists(ytmd):
        sys.exit(f"{rel(ytmd)} chưa có: soạn bằng skill upload-youtube-publish rồi chạy `video.py package`")
    if not dry and not RENV["VG_S3_BUCKET"]:
        sys.exit("thiếu VG_S3_BUCKET trong remote.env")
    if not on_server(job):
        sys.exit(f"server chưa có video của {job.name}: chạy `video.py album {rel(job.dir)} <audio>` trước")
    no_short = getattr(a, "no_short", False)
    sj, missing = short_part(job) if job.is_album and not no_short else (None, [])
    if missing:
        sys.exit("chưa đóng gói, Short chưa sẵn sàng: " + "; ".join(missing)
                 + ". Làm xong Short rồi chạy lại, hoặc `--no-short` để zip chỉ có album")
    checks = run_checks(job, sj, a)
    if job.is_album and not sj:
        checks["short"] = "not included (--no-short)"
    parts = [(job, a.thumbnail and os.path.abspath(a.thumbnail) or job.image, "")] + ([(sj, sj.image, "short")] if sj else [])
    py = venv_python(extra=() if dry else ("boto3",))
    pkg_py = os.path.join(HERE, "package.py")
    stage = tempfile.mkdtemp(prefix="vg-pkg-")
    try:
        for pj, thumb, sub in parts:
            stage_part(py, pkg_py, pj, os.path.join(stage, job.name, sub), thumb)
        folder, tag = s3_folder(job)
        zipname = f"{tag}{job.name}-{time.strftime('%Y%m%d-%H%M%S')}.zip"
        spec = {"pkg": f"~/{inp}/pkg/{job.name}", "zip": f"~/{out}/{zipname}", "name": job.name,
                "kind": "album" if job.is_album else "video", "channel": job.channel,
                "short": "included" if sj else ("not included (--no-short)" if job.is_album else None),
                "order": publish_order(job.channel),
                "parts": [{"key": sub or "album", "sub": sub, "name": f"{pj.name}.mp4",
                           "video": f"~/{_paths(pj)[2]}/video.mp4", "audio_dir": None if pj.short else f"~/{inp}",
                           "warnings": [f"{'shorts' if pj.short else 'publish'}.py check còn ❌ (đóng gói bằng --force)"]
                           if checks.get(sub or "album", "").startswith("fail") else [],
                           "expect": "x".join(map(str, pj.config()["short"]["frame"])) if pj.short else "3840x2160"}
                          for pj, _, sub in parts]}
        json.dump(spec, open(os.path.join(stage, "build.json"), "w"), indent=1, ensure_ascii=False)
        run(_ssh(f"mkdir -p {R}/scripts && rm -rf {inp}/pkg && mkdir -p {inp}/pkg"))
        _rsync(HERE + "/", f"{R}/scripts/", "--exclude", "__pycache__")
        _rsync(stage + "/", f"{inp}/pkg/")
    finally:
        shutil.rmtree(stage)
    built = _ssh_json(limited(f"python3 {R}/scripts/pkg_server.py build ~/{inp}/pkg/build.json"))
    size = built["size"]
    print(f"[{time.time() - t0:.0f}s] {zipname}: {human(size)} on the server, {len(built['entries'])} files"
          + ("" if sj or not job.is_album else " · chỉ có album (--no-short)"), flush=True)
    for name, n in built["entries"]:
        print(f"  {name:<52} {human(n):>10}", flush=True)
    print("checks: " + " · ".join(f"{k} {v}" for k, v in checks.items()), flush=True)
    for w in built["warnings"]:
        print(f"⚠ {w}", flush=True)
    key = f"{RENV['VG_S3_PREFIX']}{folder}/{zipname}"
    if dry:
        print("\n--- README.txt ---\n" + built["readme"], flush=True)
        run(_ssh(f"rm -rf {inp}/pkg {out}/{zipname}"))
        print(f"dry run: không upload (sẽ là s3://{RENV['VG_S3_BUCKET']}/{key}); đã xoá zip thử trên server, "
              "video vẫn ở server", flush=True)
        return

    s3args = ["--bucket", RENV["VG_S3_BUCKET"], "--key", key, "--region", RENV["VG_S3_REGION"]] + (
        ["--profile", RENV["VG_AWS_PROFILE"]] if RENV["VG_AWS_PROFILE"] else [])
    up = json.loads(subprocess.run([py, pkg_py, "presign", "--size", str(size)] + s3args,
                                   stdout=subprocess.PIPE, text=True, check=True).stdout)
    print(f"upload: multipart, {len(up['urls'])} presigned parts -> s3://{RENV['VG_S3_BUCKET']}/{key}", flush=True)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(up, fh)
        spec_file = fh.name
    try:
        _rsync(spec_file, f"{inp}/s3spec.json")
        res = _ssh_json(limited(f"python3 {R}/scripts/pkg_server.py upload ~/{out}/{zipname} ~/{inp}/s3spec.json"))
        with open(spec_file, "w") as fh:
            json.dump(res, fh)
        run([py, pkg_py, "complete", "--upload-id", up["upload_id"], "--etags", spec_file] + s3args)
    except (subprocess.CalledProcessError, KeyError, ValueError):
        subprocess.run([py, pkg_py, "abort", "--upload-id", up["upload_id"]] + s3args)
        raise
    finally:
        os.remove(spec_file)
        subprocess.run(_ssh(f"rm -f {inp}/s3spec.json"))
    head = json.loads(subprocess.run([py, pkg_py, "head"] + s3args, stdout=subprocess.PIPE, text=True,
                                     check=True).stdout)
    if head["size"] != size:
        sys.exit(f"S3 có {head['size']} byte, zip {size} byte: upload chưa đủ, chạy lại `video.py package`")
    uri = f"s3://{RENV['VG_S3_BUCKET']}/{key}"
    cleaned = not a.keep_server
    if cleaned:
        dirs = [d for pj, _, _ in parts for d in _paths(pj)[1:]]
        gone = [f"{inp}/pkg", f"{out}/{zipname}"] + [f"{d}/{f}" for d in dirs for f in (
            "video.mp4", "video.mp4.json", "check_*.png", "audio.*", "bars.mp4", "seg.wav")]
        run(_ssh(f"rm -rf {' '.join(gone)}; du -sh {' '.join(dirs)} 2>/dev/null; true"))
        for pj, _, _ in parts:
            rj = os.path.join(pj.out, "remote.json")
            if os.path.exists(rj):
                info = json.load(open(rj))
                info.update(video=None, cleaned=time.strftime("%Y-%m-%d %H:%M"), s3=uri)
                json.dump(info, open(rj, "w"), indent=1)

    rec = {"s3": uri, "region": RENV["VG_S3_REGION"], "zip": zipname, "size": size, "sha256": built["sha256"],
           "uploaded": time.strftime("%Y-%m-%d %H:%M"),
           "parts": {k: dict(p, dir=rel((sj if k == "short" else job).dir)) for k, p in built["parts"].items()},
           "checks": checks, "files": sorted(built["files"]), "warnings": built["warnings"], "server_cleaned": cleaned}
    log = os.path.join(job.dir, "s3-package.json")
    hist = json.load(open(log)) if os.path.exists(log) else []
    json.dump(hist + [rec], open(log, "w"), indent=1, ensure_ascii=False)
    print(f"[{time.time() - t0:.0f}s] ✔ {uri} ({human(size)}, {' + '.join(built['parts'])}) · ghi vào {rel(log)}"
          + (" · đã dọn video/zip/audio trên server" if cleaned else ""), flush=True)


def main():
    ap = argparse.ArgumentParser(description=USAGE,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("frame", "loop", "album", "batch", "package", "short", "variant", "qa"):
        p = sub.add_parser(name)
        p.add_argument("dir")
        if name == "short":
            p.add_argument("--download", action="store_true", help="also fetch the Short's mp4 from the server")
            p.add_argument("--no-package", action="store_true", help=argparse.SUPPRESS)
        if name == "album":
            p.add_argument("audio", help="the mixed album audio (WAV or AAC)")
            p.add_argument("--out", help="default: DIR/video/<dir name>.mp4")
            p.add_argument("--download", action="store_true", help="also fetch the full mp4 from the server")
            p.add_argument("--no-package", action="store_true",
                           help="don't package even when youtube.md and the Short are ready")
        if name in ("album", "package"):
            p.add_argument("--thumbnail", help="album thumbnail for the package (default: the one the video was made from)")
            p.add_argument("--force", action="store_true",
                           help="package even if publish.py check / shorts.py check fails")
            p.add_argument("--keep-server", action="store_true",
                           help="after upload, keep the zip, the full videos and the audio on the server")
        if name == "package":
            p.add_argument("--no-short", action="store_true", help="zip only the album (no Short, the zip says so)")
            p.add_argument("--dry-run", action="store_true",
                           help="build the zip on the server, print its files + size, delete it; no upload")
        if name == "qa":
            continue
        if name == "variant":
            p.add_argument("--seed", type=int, help="default: derived from the folder name")
            p.add_argument("--dry-run", action="store_true", help="print the pick, don't write <dir>/video.json")
            p.add_argument("--set", action="append", default=[], metavar="AXIS=NAME",
                           help="fix one axis (camera, parallax, atmosphere, lighting), e.g. --set lighting=window_rays")
            continue
        if name == "frame":
            p.add_argument("--at", type=float, default=30.0, help="loop time, seconds")
            p.add_argument("--local", action="store_true", help="render the still on this Mac (cinema: torch on CUDA, else MPS, else CPU)")
        elif name != "package":
            p.add_argument("--remote", action="store_true", help=argparse.SUPPRESS)
            p.add_argument("--local", action="store_true", help="render on this Mac instead of the GPU server")
            p.add_argument("--jobs", type=int)
            p.add_argument("--encoder", choices=["x264", "nvenc", "videotoolbox"])
            if name == "loop":
                p.add_argument("--seconds", type=float, help="only render this much as DIR/video/loop_preview.mp4 (not seamless)")
                p.add_argument("--intro-only", action="store_true", help="only (re)render DIR/video/loop_intro.mp4")
    a = ap.parse_args()
    a.remote = a.cmd not in ("frame", "package", "variant", "qa") and not a.local
    if a.cmd == "qa":
        job = Job(a.dir)
        job.need_image()
        if not job.config()["cinema"]["enabled"]:
            sys.exit("qa checks cinema renders; this folder's channel has cinema off")
        out = os.path.join(job.out, "qa.json")
        remote_frame(job, 0, out, qa=True)
        rep = json.load(open(out))
        print(("PASS" if rep["pass"] else "FAIL: " + ", ".join(rep["failed"])) + f"  ({os.path.relpath(out, REPO)})")
        return
    if a.cmd == "variant":
        import variants
        bad = [x for x in a.set if "=" not in x]
        if bad:
            sys.exit(f"--set {bad[0]}: expected AXIS=NAME, e.g. --set lighting=window_rays "
                     f"(axes: {', '.join(variants.AXES)})")
        variants.pick(Job(a.dir), a.seed, a.dry_run, dict(x.split("=", 1) for x in a.set))
        return

    if a.cmd == "batch":
        ch = os.path.abspath(a.dir)
        todo = []
        for kind in ("ideas", "albums", "singles"):
            root = os.path.join(ch, kind)
            if not os.path.isdir(root):
                continue
            for d in sorted(os.listdir(root)):
                d = os.path.join(root, d)
                if not os.path.isdir(d) or os.path.exists(os.path.join(d, "video", "loop.mp4")):
                    continue
                if os.path.exists(os.path.join(d, "video", os.path.basename(d) + ".mp4")):
                    continue
                idea = source_idea(d)
                if idea and os.path.exists(os.path.join(idea, "video", "loop.mp4")) and not any(
                        os.path.exists(os.path.join(d, f)) for f in ("thumbnail.png", "thumbnail.jpg")):
                    continue
                todo.append(d)
        skipped = [d for d in todo if not Job(d).image]
        todo = [d for d in todo if d not in skipped]
        print(f"{len(todo)} folder(s) to render"
              + (f"; no thumbnail yet: {', '.join(os.path.basename(d) for d in skipped)}"
                 if skipped else ""), flush=True)
        for d in todo:
            job = Job(d)
            job.need_image()
            remote(job, a) if a.remote else local_loop(job, a)
        return

    job = Job(a.dir)
    if a.cmd == "package":
        package(job, a)
        return
    job.need_image()
    if a.cmd == "frame":
        out = os.path.join(job.out, f"frame_{a.at:g}s.png")
        if job.short:
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
                json.dump(job.config(), fh, indent=1)
            run([venv_python(), os.path.join(HERE, "make_loop.py"), job.image, out, "--frame", str(a.at),
                 "--preset", fh.name], env=job.frame_env())
            os.remove(fh.name)
        elif job.config()["cinema"]["enabled"] and not a.local:
            remote_frame(job, a.at, out)
        else:
            run([venv_python(), os.path.join(HERE, "make_loop.py"), job.image, out,
                 "--frame", str(a.at)] + job.presets())
    elif a.cmd == "loop":
        remote(job, a) if a.remote else local_loop(job, a)
    elif a.cmd == "short":
        if not job.short:
            sys.exit(f"{a.dir}: `short` needs a channel/<name>/albums/NNN-slug/short folder (or the old shorts/NNN-slug)")
        if not a.remote:
            local_short(job, a)
            return
        remote_short(job, a)
        if job.album_short:
            print(f"Short chỉ render, không đóng gói riêng: nó nằm trong zip của album → "
                  f"`{package_command(Job(os.path.dirname(job.dir)))}`", flush=True)
        else:
            print(f"Short bố cục cũ: `shorts.py migrate --channel {job.channel}`, rồi đóng gói cùng album "
                  "(`video.py package channel/<ch>/albums/<album>`)", flush=True)
    else:
        a.audio = os.path.abspath(a.audio)
        if not a.remote:
            local_album(job, a)
            return
        remote(job, a, a.audio)
        if a.no_package:
            return
        later = f"`{package_command(job)}`"
        if not os.path.exists(os.path.join(job.dir, "youtube.md")):
            print("chưa đóng gói, chưa có youtube.md: soạn bằng skill upload-youtube-publish (chapters đo trên file "
                  f"master audio), rồi {later} (một zip: album + Short)", flush=True)
            return
        missing = short_part(job)[1] if job.is_album else []
        if missing:
            print(f"chưa đóng gói, Short chưa sẵn sàng ({'; '.join(missing)}). Khi Short xong: {later} "
                  "(một zip: album + short/)", flush=True)
            return
        package(job, a)


if __name__ == "__main__":
    main()

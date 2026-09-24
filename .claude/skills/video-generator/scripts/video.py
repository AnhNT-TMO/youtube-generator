#!/usr/bin/env python3
"""video-generator: still thumbnail -> 5-min loop video -> full-length music video.

    video.py frame DIR [--at 30]              # step 1 helper: one still, to tune DIR/video.json
    video.py loop  DIR [--local]              # step 1: thumbnail -> 5-min seamless loop + logo intro
    video.py batch channel/<name> [--local]   # step 1 for every idea / album / single with a thumbnail but no loop
    video.py album DIR AUDIO [--local]        # step 2: loop -> video as long as AUDIO, + spectrum bars
    video.py package DIR                      # step 3: zip video + thumbnails + youtube.md on the server -> S3

DIR sits inside channel/<name>/ (an idea, album or single folder) and holds thumbnail.png. An album made from an
idea (plan.yaml sources.idea) that has no thumbnail.png / video.json / video/loop.mp4 of its own uses the idea's.
Config layers: tool defaults < channel/<name>/video.json < DIR/video.json.
Everything is written to DIR/video/.

loop / batch / album render on the GPU server from remote.env (next to this skill's SKILL.md) by default:
scripts, the channel's image_source/ and the job's inputs are synced over,
unchanged files are not uploaded again. Loops come back to DIR/video/; the full video of `album` stays on the
server (only its ffprobe + two check frames come back; --download also fetches the mp4) and `package` zips it there
with DIR/youtube.md and the thumbnails and uploads the zip to S3 through presigned requests signed with this Mac's
AWS credentials (bucket/prefix in remote.env). `album` runs `package` itself when DIR/youtube.md exists.
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
    """The skill's private venv (numpy + Pillow; `extra` modules, e.g. boto3 for package), created on first use."""
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
    """Where things are for one idea/album folder."""

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
        # Steps run in any order: the image/loop may have been made in the idea folder after the album was planned.
        # Album's own file first, then the source idea's (read-only; album-plan `sync` copies them for good).
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
        self.out = os.path.join(self.dir, "video")
        self.id = re.sub(r"[^A-Za-z0-9_.-]+", "__", "/".join(rel[1:]))

    def need_image(self):
        if not self.image:
            sys.exit(f"{self.dir}: no thumbnail.png / thumbnail.jpg")
        os.makedirs(self.out, exist_ok=True)

    def presets(self):
        return sum((["--preset", p] for p in self.layers), [])


def source_idea(d):
    """Idea folder an album was planned from (plan.yaml `sources.idea`), or None. Regex, so no yaml needed."""
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
    return a.out or os.path.join(job.out, os.path.basename(job.dir) + ".mp4")


# ------------------------------------------------------------------ local --
def local_loop(job, a):
    run([venv_python(), os.path.join(HERE, "make_loop.py"), job.image,
         os.path.join(job.out, "loop.mp4"), "--seam-check", "--jobs", str(a.jobs or 4)]
        + job.presets() + (["--encoder", a.encoder] if a.encoder else []))


def local_album(job, a):
    loop = os.path.join(job.out, "loop.mp4")
    idea_loop = os.path.join(job.idea, "video", "loop.mp4") if job.idea else None
    if not os.path.exists(loop) and idea_loop and os.path.exists(idea_loop) and job.image.startswith(job.idea + os.sep):
        loop = idea_loop           # loop made for the idea, same image: reuse it
        print(f"using the idea's loop {os.path.relpath(loop, REPO)}", flush=True)
    if not os.path.exists(loop):
        local_loop(job, a)
    run([venv_python(), os.path.join(HERE, "extend.py"), loop, a.audio, album_out(job, a),
         "--jobs", str(a.jobs or 4)] + job.presets()
        + (["--encoder", a.encoder] if a.encoder else []))


# ----------------------------------------------------------------- remote --
# Lệnh nặng chạy trong systemd user slice `youtube.slice`, dùng chung cho MỌI skill của project: tổng cộng tối đa
# ~60 % CPU, RAM 60 % (MemoryHigh) / 70 % (MemoryMax, kill trong slice) của server dùng chung (chủ kênh 2026-09-24,
# CLAUDE.md §4). Slice tự tạo ở lần đầu. Giữ chuỗi này giống hệt khối LIMIT trong các remote.sh.
LIMIT = ("S=~/.config/systemd/user/youtube.slice; [ -f $S ] || { mkdir -p ${S%/*} && printf \"[Unit]\\nDescription="
         "youtube project: every skill shares this cap (CLAUDE.md 4)\\n[Slice]\\nCPUQuota=%s%%\\nMemoryHigh=60%%\\n"
         "MemoryMax=70%%\\n\" $(( $(nproc) * 60 )) > $S && systemctl --user daemon-reload; }; "
         "systemd-run --user --scope --quiet --collect --slice=youtube.slice -- bash -c ")


def limited(cmd):
    return LIMIT + shlex.quote(cmd)


def _ssh(cmd):
    return ["ssh", "-i", RENV["VG_KEY"], "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
            "-o", "ServerAliveInterval=30", RENV["VG_REMOTE"], cmd]


def _ssh_json(cmd):
    """Run on the server, echo its stderr, return the JSON printed on the last stdout line."""
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


def remote(job, a, audio=None):
    """Sync, render on the server, bring the results back.

    Server layout under ~/$VG_DIR: scripts/ (this skill's scripts), .venv/,
    repo/channel/<name>/image_source/ (logo), in/<job>/, out/<job>/."""
    if not RENV["VG_REMOTE"]:
        sys.exit("no VG_REMOTE in remote.env")
    t0 = time.time()
    R, inp, out = _paths(job)
    ch = f"channel/{job.channel}/image_source"
    if subprocess.run(_ssh("true")).returncode:
        sys.exit(f"GPU server {RENV['VG_REMOTE']} unreachable. Check the network/server and retry; --local renders "
                 "on this Mac (heavy) — ask the channel owner before using it.")
    run(_ssh(f"mkdir -p {R}/scripts {R}/repo/{ch} {inp} {out} && rm -f {out}/loop_intro.mp4"))
    _rsync(HERE + "/", f"{R}/scripts/", "--exclude", "__pycache__")
    _rsync(os.path.join(SK, "requirements.txt"), f"{R}/requirements.txt")
    _rsync(os.path.join(job.channel_dir, "image_source") + "/", f"{R}/repo/{ch}/")
    run(_ssh(f"test -x {R}/.venv/bin/python || (python3 -m venv {R}/.venv && "
             f"{R}/.venv/bin/pip install -q -r {R}/requirements.txt)"))

    # one resolved config file, so the server needs no copy of the channel tree
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(config.merge_files(job.layers), fh, indent=1)
        cfg_file = fh.name
    ext = os.path.splitext(job.image)[1]
    _rsync(job.image, f"{inp}/image{ext}")
    _rsync(cfg_file, f"{inp}/preset.json", "--checksum")
    os.remove(cfg_file)
    if audio:
        aext = os.path.splitext(audio)[1]
        _rsync(audio, f"{inp}/audio{aext}")
    print(f"[{time.time() - t0:.0f}s] inputs synced", flush=True)

    enc = a.encoder or RENV["VG_ENCODER"]     # server: NVENC on the GPU (CPU/RAM stay free, owner 2026-09-24)
    jobs = a.jobs or int(RENV["VG_JOBS"])
    P = f"~/{R}/.venv/bin/python"
    cmd = (f"cd {R}/scripts && export VG_REPO=~/{R}/repo && "
           f"{P} make_loop.py ~/{inp}/image{ext} ~/{out}/loop.mp4 --preset ~/{inp}/preset.json "
           f"--jobs {jobs} --encoder {enc} --seam-check")
    if audio:
        cmd += (f" && {P} extend.py ~/{out}/loop.mp4 ~/{inp}/audio{aext} ~/{out}/video.mp4 "
                f"--preset ~/{inp}/preset.json --jobs {jobs} --encoder {enc}")
    if audio:      # probe + two still frames of the full video, so it can be checked without downloading it
        cmd += (f" && cd ~/{out} && rm -f video.mp4.json check_*.png"
                f" && ffprobe -v error -print_format json -show_format -show_streams video.mp4 > video.mp4.json"
                f" && D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 video.mp4)"
                f" && ffmpeg -v error -y -ss 5 -i video.mp4 -frames:v 1 check_5s.png"
                f" && ffmpeg -v error -y -ss $(python3 -c \"print($D/2)\") -i video.mp4 -frames:v 1 check_mid.png")
    run(_ssh(limited(cmd)))
    print(f"[{time.time() - t0:.0f}s] rendered, downloading", flush=True)

    for name in ("loop.mp4", "loop_seam.mp4", "loop_intro.mp4"):
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


# ---------------------------------------------------------------- package --
def package(job, a):
    """Zip the server's full video + DIR/youtube.md + thumbnails on the server and upload the zip to S3.

    Presigned requests are signed here with this Mac's AWS credentials; the server only sends the bytes."""
    t0 = time.time()
    R, inp, out = _paths(job)
    slug = os.path.basename(job.dir)
    ytmd = os.path.join(job.dir, "youtube.md")
    if not os.path.exists(ytmd):
        sys.exit(f"{os.path.relpath(ytmd, REPO)} chưa có: soạn bằng skill youtube-publish rồi chạy `video.py package`")
    if not RENV["VG_S3_BUCKET"]:
        sys.exit("thiếu VG_S3_BUCKET trong remote.env")
    if subprocess.run(_ssh(f"test -f {out}/video.mp4")).returncode:
        sys.exit(f"server chưa có video của {slug}: chạy `video.py album {os.path.relpath(job.dir, REPO)} <audio>` trước")
    thumb = os.path.abspath(a.thumbnail) if a.thumbnail else job.image
    py = venv_python(extra=("boto3",))
    pkg_py = os.path.join(HERE, "package.py")

    # 1. package folder built here: youtube.md, paste-ready fields, YouTube JPG (also saved as DIR/thumbnail.jpg,
    #    which youtube-publish uploads when the PNG is > 2 MB), full-resolution thumbnail, meta
    stage = tempfile.mkdtemp(prefix="vg-pkg-")
    pkg = os.path.join(stage, slug)
    src_audio = (json.load(open(os.path.join(job.out, "remote.json"))).get("audio")
                 if os.path.exists(os.path.join(job.out, "remote.json")) else None)
    run([py, pkg_py, "stage", pkg, "--youtube-md", ytmd, "--thumbnail", thumb,
         "--jpg", os.path.join(job.dir, "thumbnail.jpg"), "--channel", job.channel]
        + (["--source-audio", src_audio] if src_audio else []))

    # 2. youtube.md must pass youtube-publish's check (chapters vs video are its own job: measured on the master)
    pub = os.path.join(REPO, ".claude", "skills", "youtube-publish")
    pub_py = os.path.join(pub, ".venv", "bin", "python")
    if os.path.exists(pub_py):
        rc = subprocess.run([pub_py, os.path.join(pub, "scripts", "publish.py"), "check", job.dir]).returncode
        if rc and not a.force:
            shutil.rmtree(stage)
            sys.exit("youtube.md chưa qua publish.py check: sửa rồi chạy lại (--force để bỏ qua)")
    else:
        print("⚠ youtube-publish venv not found: youtube.md not checked", flush=True)

    # 3. zip on the server, next to the video (no multi-GB transfer through this Mac)
    run(_ssh(f"mkdir -p {R}/scripts && rm -rf {inp}/pkg && mkdir -p {inp}/pkg"))
    _rsync(HERE + "/", f"{R}/scripts/", "--exclude", "__pycache__")
    _rsync(pkg, f"{inp}/pkg/")
    shutil.rmtree(stage)
    zipname = f"{slug}-{time.strftime('%Y%m%d-%H%M%S')}.zip"
    built = _ssh_json(limited(f"python3 {R}/scripts/pkg_server.py build ~/{inp}/pkg/{slug} ~/{out}/video.mp4 ~/{inp} "
                      f"~/{out}/{zipname} --video-name {slug}.mp4"))
    for w in built["warnings"]:
        print(f"⚠ {w}", flush=True)
    size = built["size"]
    print(f"[{time.time() - t0:.0f}s] zip {size / 1e9:.2f} GB on the server", flush=True)

    # 4. presign here, upload from the server
    rel = os.path.relpath(job.dir, REPO).split(os.sep)[1:]          # <channel>/<albums|singles|ideas>/<slug>
    key = RENV["VG_S3_PREFIX"] + "/".join(rel) + "/" + zipname
    s3args = ["--bucket", RENV["VG_S3_BUCKET"], "--key", key, "--region", RENV["VG_S3_REGION"]] + (
        ["--profile", RENV["VG_AWS_PROFILE"]] if RENV["VG_AWS_PROFILE"] else [])
    spec = json.loads(subprocess.run([py, pkg_py, "presign", "--size", str(size)] + s3args,
                                     stdout=subprocess.PIPE, text=True, check=True).stdout)
    print(f"upload: multipart, {len(spec['urls'])} presigned parts -> s3://{RENV['VG_S3_BUCKET']}/{key}", flush=True)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(spec, fh)
        spec_file = fh.name
    try:
        _rsync(spec_file, f"{inp}/s3spec.json")
        res = _ssh_json(limited(f"python3 {R}/scripts/pkg_server.py upload ~/{out}/{zipname} ~/{inp}/s3spec.json"))
        with open(spec_file, "w") as fh:
            json.dump(res, fh)
        run([py, pkg_py, "complete", "--upload-id", spec["upload_id"], "--etags", spec_file] + s3args)
    except (subprocess.CalledProcessError, KeyError, ValueError):
        subprocess.run([py, pkg_py, "abort", "--upload-id", spec["upload_id"]] + s3args)
        raise
    finally:
        os.remove(spec_file)
        subprocess.run(_ssh(f"rm -f {inp}/s3spec.json"))
    head = json.loads(subprocess.run([py, pkg_py, "head"] + s3args, stdout=subprocess.PIPE, text=True,
                                     check=True).stdout)
    if head["size"] != size:
        sys.exit(f"S3 có {head['size']} byte, zip {size} byte: upload chưa đủ, chạy lại `video.py package`")
    # 5. clean the server: the upload is verified, so drop the zip, the full video and the pushed audio
    #    (GBs each); loop / image / preset stay (small) so a re-render doesn't redo the loop
    cleaned = not a.keep_server
    if cleaned:
        run(_ssh(f"rm -rf {inp}/pkg {out}/{zipname} {out}/video.mp4 {out}/video.mp4.json {out}/check_*.png "
                 f"{inp}/audio.* && du -sh {inp} {out}"))
        rj = os.path.join(job.out, "remote.json")
        if os.path.exists(rj):
            info = json.load(open(rj))
            info.update(video=None, cleaned=time.strftime("%Y-%m-%d %H:%M"), s3=f"s3://{RENV['VG_S3_BUCKET']}/{key}")
            json.dump(info, open(rj, "w"), indent=1)

    rec = {"s3": f"s3://{RENV['VG_S3_BUCKET']}/{key}", "region": RENV["VG_S3_REGION"], "zip": zipname,
           "size": size, "sha256": built["sha256"], "uploaded": time.strftime("%Y-%m-%d %H:%M"),
           "video": built["video"], "files": sorted(built["files"]), "warnings": built["warnings"],
           "server_cleaned": cleaned}
    log = os.path.join(job.dir, "s3-package.json")
    hist = json.load(open(log)) if os.path.exists(log) else []
    json.dump(hist + [rec], open(log, "w"), indent=1, ensure_ascii=False)
    print(f"[{time.time() - t0:.0f}s] ✔ {rec['s3']} ({size / 1e9:.2f} GB) · ghi vào {os.path.relpath(log, REPO)}"
          + (" · đã dọn video/zip/audio trên server" if cleaned else ""), flush=True)


# ------------------------------------------------------------------- main --
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("frame", "loop", "album", "batch", "package"):
        p = sub.add_parser(name)
        p.add_argument("dir")
        if name == "album":
            p.add_argument("audio", help="the mixed album audio (WAV or AAC)")
            p.add_argument("--out", help="default: DIR/video/<dir name>.mp4")
            p.add_argument("--download", action="store_true", help="also fetch the full mp4 from the server")
            p.add_argument("--no-package", action="store_true", help="don't zip + upload to S3 after rendering")
        if name in ("album", "package"):
            p.add_argument("--thumbnail", help="thumbnail for the package (default: the one the video was made from)")
            p.add_argument("--force", action="store_true", help="package even if publish.py check fails")
            p.add_argument("--keep-server", action="store_true",
                           help="after upload, keep the zip, the full video and the audio on the server")
        if name == "frame":
            p.add_argument("--at", type=float, default=30.0, help="loop time, seconds")
        elif name != "package":
            p.add_argument("--remote", action="store_true", help=argparse.SUPPRESS)   # old flag: remote is the default
            p.add_argument("--local", action="store_true", help="render on this Mac instead of the GPU server")
            p.add_argument("--jobs", type=int)
            p.add_argument("--encoder", choices=["x264", "nvenc", "videotoolbox"])
    a = ap.parse_args()
    a.remote = a.cmd not in ("frame", "package") and not a.local

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
                    continue            # final video already made
                idea = source_idea(d)
                if idea and os.path.exists(os.path.join(idea, "video", "loop.mp4")) and not any(
                        os.path.exists(os.path.join(d, f)) for f in ("thumbnail.png", "thumbnail.jpg")):
                    continue            # album uses its idea's loop
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
    job.need_image()
    if a.cmd == "frame":
        out = os.path.join(job.out, f"frame_{a.at:g}s.png")
        run([venv_python(), os.path.join(HERE, "make_loop.py"), job.image, out,
             "--frame", str(a.at)] + job.presets())
    elif a.cmd == "loop":
        remote(job, a) if a.remote else local_loop(job, a)
    elif a.cmd == "package":
        package(job, a)
    else:
        a.audio = os.path.abspath(a.audio)
        if not a.remote:
            local_album(job, a)
            return
        remote(job, a, a.audio)
        if a.no_package:
            return
        if os.path.exists(os.path.join(job.dir, "youtube.md")):
            package(job, a)
        else:
            print("chưa có youtube.md: soạn bằng skill youtube-publish (chapters đo trên file master audio), "
                  f"rồi `video.py package {os.path.relpath(job.dir, REPO)}` để zip + upload lên S3", flush=True)


if __name__ == "__main__":
    main()

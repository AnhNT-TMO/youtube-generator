#!/usr/bin/env python3
USAGE = """Phía GPU server của video-upscale: upscale clip lên 1920×1080 bằng SeedVR2 3B, theo cụm, có lính canh nhiệt.

  python3 upscale_server.py setup                       một lần / sửa khi hỏng: repo (commit cố định + bản vá), .venv, model
  python3 upscale_server.py run [REL ...] [--list F] [--max-chunks N] [--rest S]
                                                        chạy nền (upscale.py run/night gọi qua systemd-run); giữ thứ tự
                                                        ưu tiên, bỏ qua clip đã xong, xóa bản gốc src/ khi đạt
  python3 upscale_server.py status                      tiến độ, nhiệt độ, cụm đang chạy

~/video-upscale/: src/<đường dẫn như trên Mac> (tạm, xóa khi đạt), work/ (tạm), log/, status.json, libraries.json,
seedvr2/ (repo đã vá), .venv/, models/seedvr2/. Bản 1080p: ~/video_sources/<thư viện>/<đường dẫn trong bộ resource>
(libraries.json: bộ resource → thư viện, vd. image_source → christmas); đường dẫn ngoài bộ nào → ~/video_sources/_other/<đường dẫn>.
"""
import argparse
import json
import math
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.expanduser("~/video-upscale")
SRC, WORK, LOG = (os.path.join(ROOT, d) for d in ("src", "work", "log"))
LIBRARY = os.path.expanduser("~/video_sources")
LIBMAP = os.path.join(ROOT, "libraries.json")
STATUS = os.path.join(ROOT, "status.json")
REPO = os.path.join(ROOT, "seedvr2")
PY = os.path.join(ROOT, ".venv", "bin", "python")
MODEL_DIR = os.path.join(ROOT, "models", "seedvr2")
REPO_URL = "https://github.com/numz/ComfyUI-SeedVR2_VideoUpscaler"
REPO_COMMIT = "4490bd1f482e026674543386bb2a4d176da245b9"
HF = "https://huggingface.co/numz/SeedVR2_comfyUI/resolve/main/"
DIT = "seedvr2_ema_3b_fp16.safetensors"
MODELS = [DIT, "ema_vae_fp16.safetensors"]
SHARED_MODELS = [os.path.expanduser("~/thumbnail-prompt/models/seedvr2")]
TORCH = ["torch==2.11.0+cu128", "torchvision==0.26.0+cu128"]
DEPS = ["safetensors", "numpy", "tqdm", "psutil", "einops", "omegaconf>=2.3.0", "diffusers>=0.33.1", "peft>=0.17.0",
        "rotary_embedding_torch>=0.5.3", "opencv-python-headless", "gguf", "matplotlib", "pillow"]
W, H = 1920, 1080
PREPEND, OVERLAP, MAX_BATCH = 4, 4, 113
VAE_MAX_MEM_GB = 8
GPU_MEM_NEED_GB = 90
TIER_BREAK = "---"
GUARD_DIR = os.path.expanduser("~/youtube-guard")
GUARD_DEFAULT_TEMP = 88
GUARD_TEMP_NEED_C = 88
START_GUARD = ("systemctl --user is-active --quiet youtube-guard || systemd-run --user --unit=youtube-guard --collect "
               "-p MemoryMax=256M python3 ~/youtube-guard/guard.py >/dev/null 2>&1")
SLICE_FILE = os.path.expanduser("~/.config/systemd/user/youtube.slice")
CHUNK = 32 * 1024 * 1024

PATCHES = [
    ("inference_cli.py",
     "'-c:v', codec, '-pix_fmt', pix_fmt, '-preset', 'medium', '-crf', '12', path],",
     "'-c:v', 'hevc_nvenc', '-pix_fmt', 'p010le', '-preset', 'p5', '-tune', 'hq', '-rc', 'vbr', '-cq', '14', "
     "'-b:v', '0', '-tag:v', 'hvc1', path],"),
    ("inference_cli.py",
     "        if context_count > 0:\n            result = result[context_count:]\n",
     "        if context_count > 0:\n            result = result[context_count:]\n"
     "        if chunk_idx == 1 and args.prepend_frames > 0 and not log_prefix:\n"
     "            result = result[args.prepend_frames:]\n"),
    ("configs_3b/main.yaml", "conv_max_mem: 0.5", f"conv_max_mem: {VAE_MAX_MEM_GB}"),
    ("configs_3b/main.yaml", "norm_max_mem: 0.5", f"norm_max_mem: {VAE_MAX_MEM_GB}"),
]


def sh(cmd, **kw):
    print("$ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


def download(url, out, conn=16):
    def req(rng, timeout):
        r = urllib.request.Request(url, headers={"Range": rng, "User-Agent": "video-upscale"})
        return urllib.request.urlopen(r, timeout=timeout)

    total = int(req("bytes=0-0", 30).headers["Content-Range"].split("/")[1])
    part = out + ".part"
    if not os.path.exists(part):
        open(part, "wb").close()
    if os.path.getsize(part) < total:
        os.truncate(part, total)
    done = set()
    if os.path.exists(part + ".done"):
        done = {int(x) for x in open(part + ".done").read().split()}
    todo = [i for i in range((total + CHUNK - 1) // CHUNK) if i not in done]
    print(f"{os.path.basename(out)}: {total / 1e9:.2f} GB, còn {len(todo)} đoạn", flush=True)
    lock = threading.Lock()

    def fetch(i):
        a, b = i * CHUNK, min((i + 1) * CHUNK, total) - 1
        while True:
            try:
                with req(f"bytes={a}-{b}", 30) as r:
                    buf = r.read()
                if len(buf) != b - a + 1:
                    raise IOError(f"thiếu byte ({len(buf)})")
                with open(part, "r+b") as f:
                    f.seek(a)
                    f.write(buf)
                with lock:
                    open(part + ".done", "a").write(f"{i}\n")
                return
            except Exception as e:
                print(f"  đoạn {i} thử lại: {e}", flush=True)
                time.sleep(3)

    with ThreadPoolExecutor(conn) as ex:
        list(ex.map(fetch, todo))
    os.rename(part, out)
    os.remove(part + ".done")


def apply_patches():
    for rel, old, new in PATCHES:
        p = os.path.join(REPO, rel)
        text = open(p).read()
        if new in text:
            continue
        if text.count(old) != 1:
            sys.exit(f"bản vá không khớp {rel}: repo khác commit {REPO_COMMIT}?")
        open(p, "w").write(text.replace(old, new))
        print(f"vá {rel}", flush=True)


def cmd_setup(_):
    os.makedirs(MODEL_DIR, exist_ok=True)
    if not os.path.isdir(os.path.join(REPO, ".git")):
        sh(["git", "clone", "-q", REPO_URL, REPO])
    if subprocess.run(["git", "-C", REPO, "cat-file", "-e", REPO_COMMIT], capture_output=True).returncode:
        sh(["git", "-C", REPO, "fetch", "-q", "--depth", "1", "origin", REPO_COMMIT])
    head = subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if head != REPO_COMMIT:
        sh(["git", "-C", REPO, "checkout", "-q", "-f", REPO_COMMIT])
    apply_patches()

    if not os.path.exists(PY) or subprocess.run([PY, "-c", "import torch, diffusers, cv2; assert torch.cuda.is_available()"],
                                                capture_output=True).returncode:
        uv = next((p for p in ("/snap/bin/uv", os.path.expanduser("~/.local/bin/uv")) if os.path.exists(p)), None)
        idx = ["--index-url", "https://download.pytorch.org/whl/cu128", "--extra-index-url", "https://pypi.org/simple"]
        if uv:
            sh([uv, "venv", "-q", "--allow-existing", "-p", "3.12", os.path.join(ROOT, ".venv")])
            sh([uv, "pip", "install", "-q", "-p", PY, "--index-strategy", "unsafe-best-match", *TORCH, *DEPS, *idx])
        else:
            sh([sys.executable, "-m", "venv", os.path.join(ROOT, ".venv")])
            sh([PY, "-m", "pip", "install", "-q", *TORCH, *DEPS, *idx])
    for m in MODELS:
        out = os.path.join(MODEL_DIR, m)
        if os.path.exists(out):
            continue
        shared = next((os.path.join(d, m) for d in SHARED_MODELS if os.path.exists(os.path.join(d, m))), None)
        if shared:
            os.link(shared, out)
            print(f"{m}: hard link từ {shared}", flush=True)
        else:
            download(HF + m, out)
    gp = os.path.join(GUARD_DIR, "guard.json")
    g = json.load(open(gp)) if os.path.exists(gp) else {}
    if g.get("gpu_mem_gb", 60) < GPU_MEM_NEED_GB:
        g["gpu_mem_gb"] = GPU_MEM_NEED_GB
        os.makedirs(GUARD_DIR, exist_ok=True)
        json.dump(g, open(gp, "w"))
        print(f"youtube-guard: gpu_mem_gb → {GPU_MEM_NEED_GB} (job dùng ~74 GB VRAM)", flush=True)
    if g.get("gpu_temp_c", GUARD_DEFAULT_TEMP) < GUARD_TEMP_NEED_C:
        g["gpu_temp_c"] = GUARD_TEMP_NEED_C
        json.dump(g, open(gp, "w"))
        print(f"youtube-guard: gpu_temp_c → {GUARD_TEMP_NEED_C} (upscale tự nghỉ ở 83 °C)", flush=True)
    if subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True).stdout.find("hevc_nvenc") < 0:
        sys.exit("ffmpeg của server không có hevc_nvenc")
    sh([PY, "-c", "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available(), "
                  "torch.cuda.get_device_name(0))"])
    print("setup xong", flush=True)


def probe(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                        "stream=width,height,nb_read_packets,r_frame_rate", "-of", "json", path],
                       capture_output=True, text=True)
    s = (json.loads(p.stdout or "{}").get("streams") or [{}])[0]
    if not s:
        return None
    num, den = s["r_frame_rate"].split("/")
    return {"w": s["width"], "h": s["height"], "frames": int(s["nb_read_packets"]), "fps": float(num) / float(den)}


def best_batch(frames):
    options = []
    for b in range(5, MAX_BATCH + 1, 4):
        computed = b * math.ceil((frames + PREPEND - OVERLAP) / (b - OVERLAP))
        options.append((computed, -b))
    computed, neg_b = min(options)
    return -neg_b, computed


def library_map():
    return json.load(open(LIBMAP)) if os.path.exists(LIBMAP) else {}


def dest(rel, libs=None):
    libs = library_map() if libs is None else libs
    for prefix, lib in libs.items():
        if rel.startswith(prefix.rstrip("/") + "/"):
            return os.path.join(LIBRARY, lib, rel[len(prefix.rstrip("/")) + 1:])
    return os.path.join(LIBRARY, "_other", rel)


def wanted(rel):
    name = os.path.basename(rel)
    return name.endswith(".mp4") and ".try" not in name and "/_rejected/" not in f"/{rel}"


def clips(prefixes):
    found = []
    for base, _, files in os.walk(SRC):
        for f in files:
            rel = os.path.relpath(os.path.join(base, f), SRC)
            if wanted(rel) and (not prefixes or any(rel == p or rel.startswith(p.rstrip("/") + "/") for p in prefixes)):
                found.append(rel)
    return sorted(found)


def guard_cfg():
    c = {"gpu_temp_c": GUARD_DEFAULT_TEMP, "gpu_mem_gb": 60}
    p = os.path.join(GUARD_DIR, "guard.json")
    if os.path.exists(p):
        c.update(json.load(open(p)))
    return c


def gpu_free_gb():
    p = subprocess.run(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
                       capture_output=True, text=True, timeout=10)
    return min((int(x) for x in p.stdout.split() if x.strip().isdigit()), default=0) / 1024


def gpu_temp():
    p = subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
                       capture_output=True, text=True, timeout=10)
    return max((int(x) for x in p.stdout.split() if x.strip().isdigit()), default=0)


def ensure_slice():
    if not os.path.exists(SLICE_FILE):
        os.makedirs(os.path.dirname(SLICE_FILE), exist_ok=True)
        open(SLICE_FILE, "w").write("[Unit]\nDescription=youtube project: every skill shares this cap (CLAUDE.md)\n"
                                    f"[Slice]\nCPUQuota={os.cpu_count() * 60}%\nMemoryHigh=60%\nMemoryMax=70%\n")
        subprocess.run(["systemctl", "--user", "daemon-reload"])


class Run:
    def __init__(self, a):
        self.a = a
        self.state = {"pid": os.getpid(), "started": time.strftime("%Y-%m-%d %H:%M:%S"), "phase": "start",
                      "done": 0, "failed": 0, "todo": 0, "chunk": None, "paused": False, "pauses": 0,
                      "paused_seconds": 0, "temp_c": 0}
        self.scope = None
        self.stopping = False

    def save(self, **kw):
        self.state.update(kw, updated=time.strftime("%Y-%m-%d %H:%M:%S"))
        tmp = STATUS + ".tmp"
        json.dump(self.state, open(tmp, "w"), indent=1)
        os.replace(tmp, STATUS)

    def say(self, msg):
        print(time.strftime("%H:%M:%S ") + msg, flush=True)

    def signal_scope(self, sig):
        if self.scope:
            subprocess.run(["systemctl", "--user", "kill", f"--signal={sig}", f"{self.scope}.scope"],
                           capture_output=True)

    def cool_down(self, until_c):
        t0 = time.time()
        while not self.stopping:
            t = gpu_temp()
            self.save(temp_c=t)
            if t <= until_c:
                break
            time.sleep(5)
        return time.time() - t0

    def wait_for_free_gpu(self, n):
        free = gpu_free_gb()
        if free >= self.a.need_free_gb:
            return
        self.say(f"trước cụm {n}: GPU chỉ trống {free:.0f} GB (< {self.a.need_free_gb} GB), người khác đang dùng: chờ")
        self.save(phase="waiting_gpu", free_gb=round(free, 1))
        t0, ok = time.time(), 0
        while not self.stopping and ok < 2:
            time.sleep(self.a.gpu_poll)
            free = gpu_free_gb()
            ok = ok + 1 if free >= self.a.need_free_gb else 0
        self.save(phase="running", free_gb=round(free, 1), waited_gpu_seconds=round(self.state.get("waited_gpu_seconds", 0) + time.time() - t0))
        if not self.stopping:
            self.say(f"GPU trống {free:.0f} GB sau {time.time() - t0:.0f} s chờ: chạy tiếp")

    def yield_to_unit(self, n):
        unit = self.a.yield_unit
        active = lambda: unit and subprocess.run(["systemctl", "--user", "is-active", "--quiet", unit]).returncode == 0
        if not active():
            return
        missing = [r for r in self.tier1 if not os.path.exists(dest(r, self.libs))]
        if missing:
            if not getattr(self, "warned_tier1", False):
                self.say(f"{len(missing)} clip ưu tiên chưa có bản 1080p (lỗi ở cụm trước): không chờ {unit}, chạy tiếp; lượt sau làm lại")
                self.warned_tier1 = True
            return
        self.say(f"trước cụm {n}: xong clip ưu tiên, nhường GPU cho {unit} (video album), chờ nó xong")
        self.save(phase=f"waiting_{unit}")
        t0 = time.time()
        while active() and not self.stopping:
            time.sleep(self.a.gpu_poll)
        self.save(phase="running")
        self.say(f"{unit} xong sau {time.time() - t0:.0f} s: upscale tiếp phần còn lại")

    def thermal_watch(self, proc):
        while proc.poll() is None and not self.stopping:
            t = gpu_temp()
            self.save(temp_c=t)
            if t >= self.pause_c:
                self.signal_scope("SIGSTOP")
                self.say(f"GPU {t} °C ≥ {self.pause_c}: tạm dừng cụm, chờ ≤ {self.resume_c} °C")
                self.save(paused=True, pauses=self.state["pauses"] + 1)
                rested = self.cool_down(self.resume_c)
                self.signal_scope("SIGCONT")
                self.save(paused=False, paused_seconds=round(self.state["paused_seconds"] + rested))
                self.say(f"nghỉ {rested:.0f} s, chạy tiếp")
            time.sleep(self.a.poll)

    def stop(self, *_):
        self.stopping = True
        self.signal_scope("SIGCONT")
        if self.scope:
            subprocess.run(["systemctl", "--user", "stop", f"{self.scope}.scope"], capture_output=True)

    def chunk_script(self, items, batch, work):
        lines = ["set -e"]
        for i, (rel, _) in enumerate(items):
            pre = os.path.join(work, "in", f"{i:03d}.mp4")
            lines.append(f"ffmpeg -nostdin -v error -y -threads 8 -i {sh_quote(os.path.join(SRC, rel))} -an -vf "
                         f"'scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H}' "
                         f"-c:v libx264 -preset ultrafast -crf 0 -pix_fmt yuv420p {sh_quote(pre)}")
        lines.append(" ".join(sh_quote(x) for x in [
            PY, os.path.join(REPO, "inference_cli.py"), os.path.join(work, "in"), "--output", os.path.join(work, "out"),
            "--output_format", "mp4", "--video_backend", "ffmpeg", "--10bit", "--model_dir", MODEL_DIR,
            "--dit_model", DIT, "--resolution", str(H), "--max_resolution", str(W), "--batch_size", str(batch),
            "--uniform_batch_size", "--temporal_overlap", str(OVERLAP), "--prepend_frames", str(PREPEND),
            "--color_correction", "lab", "--input_noise_scale", "0", "--latent_noise_scale", "0",
            "--dit_offload_device", "none", "--vae_offload_device", "none", "--tensor_offload_device", "none",
            "--cache_dit", "--cache_vae", "--compile_vae"]))
        return "\n".join(lines)

    def run_chunk(self, n, items, batch):
        work = os.path.join(WORK, f"chunk-{n:03d}")
        shutil.rmtree(work, ignore_errors=True)
        os.makedirs(os.path.join(work, "in"))
        os.makedirs(os.path.join(work, "out"))
        self.scope = f"video-upscale-chunk-{os.getpid()}-{n:03d}"
        subprocess.run(["bash", "-c", START_GUARD])
        ensure_slice()
        log = open(os.path.join(LOG, f"chunk-{n:03d}.log"), "w")
        t0 = time.time()
        proc = subprocess.Popen(["systemd-run", "--user", "--scope", "--quiet", "--collect", "--slice=youtube.slice",
                                 f"--unit={self.scope}", "-p", f"CPUQuota={self.a.cpu_quota}%", "--",
                                 "bash", "-c", self.chunk_script(items, batch, work)],
                                stdout=log, stderr=subprocess.STDOUT, env={**os.environ, "PYTHONUNBUFFERED": "1"})
        watcher = threading.Thread(target=self.thermal_watch, args=(proc,), daemon=True)
        watcher.start()
        rc = proc.wait()
        watcher.join()
        self.scope = None
        seconds = time.time() - t0
        ok = 0
        for i, (rel, info) in enumerate(items):
            got = os.path.join(work, "out", f"{i:03d}.mp4")
            res = probe(got) if os.path.exists(got) else None
            good = bool(res and res["w"] == W and res["h"] == H and res["frames"] == info["frames"])
            dst = dest(rel, self.libs)
            if good:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                os.replace(got, dst)
                ok += 1
                if self.a.drop_src:
                    drop_source(rel)
            rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "rel": rel, "ok": good, "chunk": n, "batch": batch,
                   "src_frames": info["frames"], "out": res, "rc": rc}
            open(os.path.join(LOG, "clips.jsonl"), "a").write(json.dumps(rec) + "\n")
        shutil.rmtree(work, ignore_errors=True)
        log.close()
        oom = ok == 0 and "out of memory" in open(os.path.join(LOG, f"chunk-{n:03d}.log"), errors="replace").read()
        self.say(f"cụm {n}: {ok}/{len(items)} đạt, rc {rc}, {seconds:.0f} s ({seconds / max(len(items), 1):.0f} s/clip)"
                 + (" — hết VRAM vì người khác dùng GPU, chờ rồi chạy lại cụm này" if oom else ""))
        return ok, len(items) - ok, oom

    def main(self):
        if not os.path.exists(PY) or any(not os.path.exists(os.path.join(MODEL_DIR, m)) for m in MODELS):
            sys.exit("chưa setup: chạy `upscale.py setup`")
        g = guard_cfg()
        if g["gpu_mem_gb"] < GPU_MEM_NEED_GB:
            sys.exit(f"youtube-guard kill job > {g['gpu_mem_gb']} GB VRAM, cấu hình này dùng ~74 GB: "
                     f"đặt \"gpu_mem_gb\": {GPU_MEM_NEED_GB} trong ~/youtube-guard/guard.json")
        self.pause_c = min(self.a.pause_c, g["gpu_temp_c"] - 2)
        self.resume_c = min(self.a.resume_c, self.pause_c - 5)
        self.start_c = min(self.a.start_c, self.resume_c)
        if self.pause_c < self.a.pause_c:
            self.say(f"youtube-guard kill ở {g['gpu_temp_c']} °C: hạ ngưỡng nghỉ xuống {self.pause_c} °C "
                     f"(chạy lại `upscale.py setup` để đặt guard {GUARD_TEMP_NEED_C} °C)")
        signal.signal(signal.SIGTERM, self.stop)
        signal.signal(signal.SIGINT, self.stop)
        for d in (LIBRARY, WORK, LOG):
            os.makedirs(d, exist_ok=True)
        self.libs = library_map()
        wanted_rel = list(self.a.rel)
        tier_of = {rel: 1 for rel in wanted_rel}
        if self.a.list:
            tier = 1
            for x in open(self.a.list):
                x = x.strip()
                if x == TIER_BREAK:
                    tier += 1
                elif x:
                    wanted_rel.append(x)
                    tier_of.setdefault(x, tier)
        listed = clips(wanted_rel)
        rank = {rel: i for i, rel in enumerate(wanted_rel)}
        listed.sort(key=lambda r: rank.get(r, len(rank)))
        todo = [rel for rel in listed if not os.path.exists(dest(rel, self.libs))]
        infos = {}
        for rel in todo:
            info = probe(os.path.join(SRC, rel))
            if info:
                infos[rel] = info
            else:
                self.say(f"bỏ qua (không đọc được): {rel}")
        groups = {}
        for rel, info in infos.items():
            groups.setdefault((tier_of.get(rel, 1), best_batch(info["frames"])[0]), []).append((rel, info))
        order = {rel: i for i, rel in enumerate(todo)}
        chunks = sorted(((k[1], g[i:i + self.a.per_run]) for k, g in groups.items() for i in range(0, len(g), self.a.per_run)),
                        key=lambda c: (tier_of.get(c[1][0][0], 1), order[c[1][0][0]]))
        self.tier1 = [rel for rel in listed if tier_of.get(rel, 1) == 1]
        if self.a.max_chunks:
            chunks = chunks[:self.a.max_chunks]
        self.say(f"{len(infos)} clip chờ, chạy {sum(len(c[1]) for c in chunks)} clip trong {len(chunks)} cụm ≤ {self.a.per_run} clip; nghỉ khi ≥ {self.pause_c} °C, "
                 f"chạy lại khi ≤ {self.resume_c} °C, cụm mới chỉ bắt đầu khi ≤ {self.start_c} °C")
        self.save(phase="running", todo=len(infos), chunks=len(chunks), pause_c=self.pause_c, resume_c=self.resume_c, start_c=self.start_c)
        fails_in_row = 0
        queue = list(enumerate(chunks, 1))
        while queue:
            n, (batch, items) = queue[0]
            if self.stopping:
                break
            if tier_of.get(items[0][0], 1) > 1:
                self.yield_to_unit(n)
            self.wait_for_free_gpu(n)
            if self.stopping:
                break
            if gpu_temp() > self.start_c:
                self.say(f"trước cụm {n}: chờ GPU ≤ {self.start_c} °C")
                rested = self.cool_down(self.start_c)
                self.say(f"nghỉ {rested:.0f} s")
            self.save(chunk={"n": n, "of": len(chunks), "batch": batch, "clips": [r for r, _ in items]})
            ok, bad, oom = self.run_chunk(n, items, batch)
            if oom:
                time.sleep(self.a.gpu_poll)
                continue
            queue.pop(0)
            self.save(done=self.state["done"] + ok, failed=self.state["failed"] + bad, chunk=None)
            fails_in_row = fails_in_row + 1 if ok == 0 else 0
            if fails_in_row >= 2:
                self.say("2 cụm liền không ra clip nào: dừng (xem log/chunk-*.log và guard.sh kills)")
                break
            if self.a.rest and queue:
                time.sleep(self.a.rest)
        self.save(phase="stopped" if self.stopping else "finished")


def drop_source(rel):
    path = os.path.join(SRC, rel)
    if os.path.exists(path):
        os.remove(path)
    d = os.path.dirname(path)
    while d != SRC and os.path.isdir(d) and not os.listdir(d):
        os.rmdir(d)
        d = os.path.dirname(d)


def sh_quote(s):
    return "'" + str(s).replace("'", "'\"'\"'") + "'"


def cmd_run(a):
    Run(a).main()


def cmd_status(_):
    st = json.load(open(STATUS)) if os.path.exists(STATUS) else {}
    alive = st.get("pid") and os.path.exists(f"/proc/{st['pid']}")
    st["master_alive"] = bool(alive)
    st["temp_now_c"] = gpu_temp()
    rows = [json.loads(x) for x in open(os.path.join(LOG, "clips.jsonl"))] if os.path.exists(
        os.path.join(LOG, "clips.jsonl")) else []
    last = {r["rel"]: r for r in rows}
    st["library_total"] = {lib: sum(1 for _, _, fs in os.walk(os.path.join(LIBRARY, lib)) for f in fs if f.endswith(".mp4"))
                           for lib in sorted(os.listdir(LIBRARY))} if os.path.isdir(LIBRARY) else {}
    st["failed_last"] = [r for r, x in last.items() if not x["ok"] and not os.path.exists(dest(r))]
    print(json.dumps(st, indent=1, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup").set_defaults(fn=cmd_setup)
    r = sub.add_parser("run")
    r.add_argument("rel", nargs="*", help="đường dẫn (file hoặc thư mục) tương đối trong src/; trống = tất cả")
    r.add_argument("--per-run", type=int, default=10, help="số clip mỗi lần nạp model")
    r.add_argument("--pause-c", type=int, default=83, help="nhiệt độ GPU cho cụm nghỉ")
    r.add_argument("--resume-c", type=int, default=70, help="nhiệt độ GPU cho chạy lại")
    r.add_argument("--start-c", type=int, default=60, help="cụm mới chỉ bắt đầu khi GPU ≤ mức này")
    r.add_argument("--rest", type=int, default=0, help="giây nghỉ giữa hai cụm")
    r.add_argument("--poll", type=float, default=3, help="giây giữa hai lần đọc nhiệt độ")
    r.add_argument("--list", help="file: một đường dẫn tương đối trong src/ mỗi dòng, theo thứ tự ưu tiên")
    r.add_argument("--need-free-gb", type=float, default=80, help="cụm chỉ bắt đầu khi GPU trống ≥ mức này (GB); thiếu = người khác đang dùng, chờ")
    r.add_argument("--gpu-poll", type=float, default=60, help="giây giữa hai lần kiểm VRAM trống khi chờ")
    r.add_argument("--yield-unit", default="montage-render",
                   help="sau khi xong clip tầng 1 (trước dòng --- trong --list), chờ unit này (render video album) xong rồi mới chạy tầng sau")
    r.add_argument("--max-chunks", type=int, default=0, help="dừng sau N cụm (0 = hết)")
    r.add_argument("--keep-src", dest="drop_src", action="store_false",
                   help="giữ bản gốc trong src/ sau khi upscale đạt (mặc định xóa)")
    r.add_argument("--cpu-quota", type=int, default=1600, help="CPUQuota của scope mỗi cụm (%%)")
    r.set_defaults(fn=cmd_run)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

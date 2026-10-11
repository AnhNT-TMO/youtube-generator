#!/usr/bin/env python3
USAGE = """Bench VRAM / tốc độ / SSIM của config SeedVR2 trên GPU server (references/benchmark.md).

  python3 bench_server.py CONFIGS.json REF_DIR CLIP... [--only NAME ...]

CLIP = bản gốc trong ~/upscale-lab/vram/src/; REF_DIR/<CLIP> = bản 1080p production để so SSIM. Repo SeedVR2 riêng ở
~/upscale-lab/vram/seedvr2 (chép từ ~/video-upscale/seedvr2), kết quả ~/upscale-lab/vram/results.jsonl. Chạy trong
youtube.slice: systemd-run --user --unit=vram-bench --slice=youtube.slice -- bash -c 'cd ~/upscale-lab/vram && python3 bench_server.py ...'
"""
import json, os, re, subprocess, sys, threading, time

LAB = os.path.expanduser("~/upscale-lab/vram")
REPO = os.path.join(LAB, "seedvr2")
PY = os.path.expanduser("~/video-upscale/.venv/bin/python")
MODEL_DIR = os.path.expanduser("~/video-upscale/models/seedvr2")
REF = ""
CLIPS = []
CAP_GIB = float(os.environ.get("CAP_GIB", "28.5"))
RES = {"1080": (1920, 1080), "2k": (2560, 1440)}
OUT = os.path.join(LAB, "results.jsonl")

WRAP = """import os, sys, runpy, atexit, torch
torch.cuda.set_per_process_memory_fraction(min(1.0, %f * 2**30 / torch.cuda.get_device_properties(0).total_memory))
atexit.register(lambda: print("TORCH_PEAK_GIB %%.2f %%.2f" %% (torch.cuda.max_memory_reserved() / 2**30, torch.cuda.max_memory_allocated() / 2**30), flush=True))
sys.argv = [%r] + sys.argv[1:]
sys.path.insert(0, %r)
runpy.run_path(%r, run_name="__main__")
"""


def set_vae_mem(gb):
    p = os.path.join(REPO, "configs_3b/main.yaml")
    s = re.sub(r"(conv_max_mem|norm_max_mem): [0-9.]+", lambda m: f"{m.group(1)}: {gb}", open(p).read())
    open(p, "w").write(s)


def prep(res):
    w, h = RES[res]
    d = os.path.join(LAB, "in", res)
    os.makedirs(d, exist_ok=True)
    for i, rel in enumerate(CLIPS):
        out = os.path.join(d, f"{i:03d}.mp4")
        if not os.path.exists(out):
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", os.path.join(LAB, "src", rel), "-an",
                            "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h}",
                            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "0", "-pix_fmt", "yuv420p", out], check=True)
    return d


def gpu_used_by(pids):
    q = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"],
                       capture_output=True, text=True).stdout
    return sum(int(m) for p, m in (l.split(", ") for l in q.strip().splitlines() if l) if int(p) in pids)


def descendants(pid):
    out = {pid}
    q = subprocess.run(["ps", "-e", "-o", "pid=,ppid="], capture_output=True, text=True).stdout
    pairs = [tuple(map(int, l.split())) for l in q.strip().splitlines()]
    grew = True
    while grew:
        grew = False
        for c, p in pairs:
            if p in out and c not in out:
                out.add(c); grew = True
    return out


def ssim(a, b, scale=None):
    vf = f"[0:v]{'scale=1920:1080:flags=lanczos,' if scale else ''}format=yuv420p[a];[1:v]format=yuv420p[b];[a][b]ssim"
    r = subprocess.run(["ffmpeg", "-nostdin", "-i", a, "-i", b, "-lavfi", vf, "-f", "null", "-"], capture_output=True, text=True).stderr
    m = re.search(r"All:([0-9.]+) \(([0-9.inf]+)\)", r)
    return (float(m.group(1)), float(m.group(2))) if m else None


def frames(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
                        "stream=nb_read_packets,width,height", "-of", "json", p], capture_output=True, text=True).stdout
    s = json.loads(r)["streams"][0]
    return s["width"], s["height"], int(s["nb_read_packets"])


def run(cfg):
    name, res = cfg["name"], cfg["res"]
    w, h = RES[res]
    work = os.path.join(LAB, "out", name)
    subprocess.run(["rm", "-rf", work]); os.makedirs(work)
    set_vae_mem(cfg.get("vae_mem", 0.5))
    wrap = os.path.join(LAB, "wrap.py")
    cli = os.path.join(REPO, "inference_cli.py")
    open(wrap, "w").write(WRAP % (CAP_GIB, cli, REPO, cli))
    args = [PY, wrap, prep(res), "--output", work, "--output_format", "mp4", "--video_backend", "ffmpeg", "--10bit",
            "--model_dir", MODEL_DIR, "--dit_model", "seedvr2_ema_3b_fp16.safetensors", "--resolution", str(h),
            "--max_resolution", str(w), "--batch_size", str(cfg["batch"]), "--uniform_batch_size",
            "--temporal_overlap", "4", "--prepend_frames", "4", "--color_correction", "lab",
            "--input_noise_scale", "0", "--latent_noise_scale", "0", "--cache_dit", "--cache_vae"] + cfg["extra"]
    log = open(os.path.join(work, "run.log"), "w")
    t0 = time.time()
    p = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, cwd=REPO, env={**os.environ, "PYTHONUNBUFFERED": "1", "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"})
    peak = [0]
    def watch():
        while p.poll() is None:
            try:
                peak[0] = max(peak[0], gpu_used_by(descendants(p.pid)))
            except Exception:
                pass
            time.sleep(0.5)
    t = threading.Thread(target=watch, daemon=True); t.start()
    rc = p.wait(); t.join()
    secs = time.time() - t0
    text = open(os.path.join(work, "run.log"), errors="replace").read()
    tp = re.findall(r"TORCH_PEAK_GIB ([0-9.]+) ([0-9.]+)", text)
    rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), **{k: v for k, v in cfg.items()}, "rc": rc, "seconds": round(secs),
           "s_per_clip": round(secs / len(CLIPS)), "smi_peak_gib": round(peak[0] / 1024, 2),
           "torch_reserved_gib": float(tp[-1][0]) if tp else None, "oom": "out of memory" in text.lower(), "clips": []}
    for i, rel in enumerate(CLIPS):
        o = os.path.join(work, f"{i:03d}.mp4")
        if not os.path.exists(o):
            rec["clips"].append(None); continue
        fw, fh, n = frames(o)
        c = {"w": fw, "h": fh, "frames": n, "ssim_vs_prod1080": ssim(o, os.path.join(REF, rel), scale=(res != "1080"))}
        rec["clips"].append(c)
    rec["ok"] = rc == 0 and all(c and c["frames"] == 216 and (c["w"], c["h"]) == (w, h) for c in rec["clips"])
    open(OUT, "a").write(json.dumps(rec) + "\n")
    print(json.dumps(rec), flush=True)
    for i in range(len(CLIPS)):
        o = os.path.join(work, f"{i:03d}.mp4")
        if os.path.exists(o) and i > 0:
            os.remove(o)
    return rec


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) < 3:
        sys.exit(USAGE)
    only = set(args[args.index("--only") + 1:]) if "--only" in args else set()
    args = args[:args.index("--only")] if "--only" in args else args
    cfgs = json.load(open(args[0]))
    REF, CLIPS = os.path.expanduser(args[1]), args[2:]
    for cfg in cfgs:
        if only and cfg["name"] not in only:
            continue
        while True:
            free = int(subprocess.run(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
                                      capture_output=True, text=True).stdout.split()[0]) / 1024
            if free >= CAP_GIB + 3:
                break
            print(f"chờ GPU: trống {free:.1f} GiB", flush=True); time.sleep(60)
        run(cfg)

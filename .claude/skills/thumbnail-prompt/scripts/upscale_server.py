#!/usr/bin/env python3
"""Phía GPU server của `thumb.py fit`: upscale một ảnh lên 3840×2160 bằng SeedVR2 7B (diffusion, vẽ thêm chi tiết thật).

  python3 upscale_server.py setup              một lần / sửa khi hỏng: repo SeedVR2 (commit cố định), .venv (torch cu128), model
  .venv/bin/python upscale_server.py run IN OUT [--w 3840 --h 2160]

Thư mục ~/thumbnail-prompt/ trên server: scripts/ (thumb.py đẩy lên mỗi lần), seedvr2/ (repo), .venv/, models/seedvr2/,
jobs/<id>/ (xóa sau mỗi lần). Chọn SeedVR2 7B fp16 qua thử nghiệm 2026-09-24 (so với Lanczos, HAT-L, UltraSharpV2,
Real-ESRGAN, SeedVR2 3B / 7B-sharp, SUPIR): nhiều chi tiết mới nhất, giữ màu, giữ mặt ca sĩ, chữ sắc, ~20 s/ảnh.
"""
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.expanduser("~/thumbnail-prompt")
REPO_URL = "https://github.com/numz/ComfyUI-SeedVR2_VideoUpscaler"
REPO_COMMIT = "4490bd1f482e026674543386bb2a4d176da245b9"   # bản đã thử 2026-09-24
HF = "https://huggingface.co/numz/SeedVR2_comfyUI/resolve/main/"
DIT = "seedvr2_ema_7b_fp16.safetensors"    # fp8 của 7B bị lỗi chất lượng (README repo); 3B / 7B-sharp để lại vân da
MODELS = [DIT, "ema_vae_fp16.safetensors"]
# Driver server chỉ hỗ trợ CUDA 12.8: torch mặc định trên PyPI (CUDA 13) không chạy
TORCH = ["torch==2.11.0+cu128", "torchvision==0.26.0+cu128"]
DEPS = ["safetensors", "numpy", "tqdm", "psutil", "einops", "omegaconf>=2.3.0", "diffusers>=0.33.1", "peft>=0.17.0",
        "rotary_embedding_torch>=0.5.3", "opencv-python-headless", "gguf", "matplotlib", "pillow"]
CHUNK = 32 * 1024 * 1024


def sh(cmd, **kw):
    print("$ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


# ---------------------------------------------------------------- setup
def download(url, out, conn=16):
    """Tải song song theo Range, mỗi đoạn có timeout + thử lại, tải tiếp được (<out>.part + .part.done).
    Một kết nối tới Hugging Face từ server chỉ ~1 MB/s và hay treo (2026-09-24), nên không dùng wget."""
    def req(rng, timeout):
        r = urllib.request.Request(url, headers={"Range": rng, "User-Agent": "thumbnail-prompt"})
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
    lock, t0, got = threading.Lock(), time.time(), [0]

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
                    got[0] += len(buf)
                    if (got[0] // CHUNK) % 32 == 0:
                        print(f"  {got[0] / 1e9:.1f} GB, {got[0] / 1e6 / (time.time() - t0):.1f} MB/s", flush=True)
                return
            except Exception as e:
                print(f"  đoạn {i} thử lại: {e}", flush=True)
                time.sleep(3)

    with ThreadPoolExecutor(conn) as ex:
        list(ex.map(fetch, todo))
    os.rename(part, out)
    os.remove(part + ".done")


def cmd_setup(_):
    os.makedirs(os.path.join(ROOT, "models", "seedvr2"), exist_ok=True)
    repo = os.path.join(ROOT, "seedvr2")
    if not os.path.isdir(os.path.join(repo, ".git")):
        sh(["git", "clone", "-q", REPO_URL, repo])
    if subprocess.run(["git", "-C", repo, "cat-file", "-e", REPO_COMMIT], capture_output=True).returncode:
        sh(["git", "-C", repo, "fetch", "-q", "--depth", "1", "origin", REPO_COMMIT])
    sh(["git", "-C", repo, "checkout", "-q", REPO_COMMIT])

    py = os.path.join(ROOT, ".venv", "bin", "python")
    if not os.path.exists(py) or subprocess.run([py, "-c", "import torch, diffusers, PIL; assert torch.cuda.is_available()"],
                                                capture_output=True).returncode:
        uv = next((p for p in ("/snap/bin/uv", os.path.expanduser("~/.local/bin/uv")) if os.path.exists(p)), None)
        idx = ["--index-url", "https://download.pytorch.org/whl/cu128", "--extra-index-url", "https://pypi.org/simple"]
        if uv:
            sh([uv, "venv", "-q", "--allow-existing", "-p", "3.12", os.path.join(ROOT, ".venv")])
            sh([uv, "pip", "install", "-q", "-p", py, "--index-strategy", "unsafe-best-match", *TORCH, *DEPS, *idx])
        else:
            sh([sys.executable, "-m", "venv", os.path.join(ROOT, ".venv")])
            sh([py, "-m", "pip", "install", "-q", *TORCH, *DEPS, *idx])
    for m in MODELS:
        out = os.path.join(ROOT, "models", "seedvr2", m)
        if not os.path.exists(out):
            download(HF + m, out)
    sh([py, "-c", "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available(), "
                  "torch.cuda.get_device_name(0))"])
    print("setup xong", flush=True)


# ---------------------------------------------------------------- run
def cmd_run(a):
    from PIL import Image
    if a.w % 2 or a.h % 2:
        sys.exit("SeedVR2 làm tròn kích thước về số chẵn: --w/--h phải chẵn")
    for m in MODELS:
        if not os.path.exists(os.path.join(ROOT, "models", "seedvr2", m)):
            sys.exit(f"thiếu model {m}: chạy `thumb.py upscale-setup`")
    t0 = time.time()
    job = os.path.dirname(os.path.abspath(a.out))
    im = Image.open(a.inp).convert("RGB")
    src = im.size
    # Đưa vào đúng kích thước đích (Lanczos) để SeedVR2 không tự làm tròn cạnh (1672×941 → 3836×2160 nếu để nó tự tính)
    pre = os.path.join(job, "pre.png")
    im.resize((a.w, a.h), Image.LANCZOS).save(pre)
    raw = os.path.join(job, "raw.png")
    cli = [os.path.join(ROOT, ".venv", "bin", "python"), "inference_cli.py", pre, "--output", raw,
           "--output_format", "png", "--model_dir", os.path.join(ROOT, "models", "seedvr2"), "--dit_model", DIT,
           "--resolution", str(a.h), "--batch_size", "1", "--color_correction", "lab",
           "--vae_encode_tiled", "--vae_decode_tiled"]
    p = subprocess.run(cli, cwd=os.path.join(ROOT, "seedvr2"), capture_output=True, text=True)
    if p.returncode or not os.path.exists(raw):
        sys.exit("SeedVR2 lỗi:\n" + (p.stdout + p.stderr)[-3000:])
    out = Image.open(raw).convert("RGB")
    got = out.size
    if got != (a.w, a.h):
        out = out.resize((a.w, a.h), Image.LANCZOS)
    out.save(a.out)
    print(json.dumps({"src": src, "seedvr2_size": got, "out": [a.w, a.h], "model": DIT,
                      "seconds": round(time.time() - t0, 1)}), flush=True)


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup").set_defaults(fn=cmd_setup)
    r = sub.add_parser("run")
    r.add_argument("inp")
    r.add_argument("out")
    r.add_argument("--w", type=int, default=3840)
    r.add_argument("--h", type=int, default=2160)
    r.set_defaults(fn=cmd_run)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

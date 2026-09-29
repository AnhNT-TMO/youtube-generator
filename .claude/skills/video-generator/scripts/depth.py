import hashlib
import os
import sys

import numpy as np
from PIL import Image

MODEL = "depth-anything/Depth-Anything-V2-Small-hf"
SIZE = (960, 540)


def cache_path(image_path):
    h = hashlib.sha1(open(image_path, "rb").read()).hexdigest()[:16]
    return os.path.join(os.path.dirname(os.path.abspath(image_path)), f".depth-{h}.npy")


def estimate(image_path):
    import torch
    from transformers import pipeline
    dev = 0 if torch.cuda.is_available() else -1
    pipe = pipeline("depth-estimation", model=MODEL, device=dev)
    img = Image.open(image_path).convert("RGB")
    d = np.asarray(pipe(img)["predicted_depth"].squeeze().float().cpu().numpy(), np.float32)
    d = np.asarray(Image.fromarray(d).resize(SIZE, Image.BICUBIC), np.float32)
    lo, hi = np.percentile(d, 1), np.percentile(d, 99)
    return np.clip((d - lo) / max(1e-6, hi - lo), 0, 1).astype(np.float32)


def ensure(image_path):
    p = cache_path(image_path)
    if not os.path.exists(p):
        np.save(p, estimate(image_path))
        print(f"depth map: {p}", flush=True)
    return p


if __name__ == "__main__":
    out = ensure(sys.argv[1])
    if len(sys.argv) > 2:
        d = np.load(out)
        Image.fromarray((d * 255).astype(np.uint8)).save(sys.argv[2])

#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cv2
import numpy as np

W, H, FPS = 320, 180, 6
EMBED_MODEL = "facebook/dinov2-small"


def decode(path):
    cmd = ["ffmpeg", "-v", "error", "-threads", "2", "-i", str(path),
           "-vf", f"fps={FPS},scale={W}:{H}:flags=area", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    frames = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
    if len(frames) < 4:
        raise ValueError(f"only {len(frames)} frames decoded")
    return frames


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def luma(frames):
    f = frames.astype(np.float32) / 255.0
    return 0.2126 * f[..., 0] + 0.7152 * f[..., 1] + 0.0722 * f[..., 2]


def camera(frames):
    grays = [cv2.cvtColor(f, cv2.COLOR_RGB2GRAY) for f in frames]
    tx, ty, scale, used = [], [], [], 0
    for a, b in zip(grays, grays[1:]):
        pts = cv2.goodFeaturesToTrack(a, maxCorners=300, qualityLevel=0.01, minDistance=7)
        if pts is None or len(pts) < 12:
            continue
        nxt, st, _ = cv2.calcOpticalFlowPyrLK(a, b, pts, None)
        ok = st.reshape(-1) == 1
        if ok.sum() < 12:
            continue
        m, inl = cv2.estimateAffinePartial2D(pts[ok], nxt[ok], method=cv2.RANSAC, ransacReprojThreshold=1.5)
        if m is None:
            continue
        s = float(np.hypot(m[0, 0], m[1, 0]))
        cx, cy = W / 2, H / 2
        tx.append(float(m[0, 0] * cx + m[0, 1] * cy + m[0, 2] - cx))
        ty.append(float(m[1, 0] * cx + m[1, 1] * cy + m[1, 2] - cy))
        scale.append(s)
        used += 1
    if not used:
        return {"dx": 0.0, "dy": 0.0, "zoom": 1.0, "speed": 0.0, "pairs": 0}
    dx = sum(tx) / W
    dy = sum(ty) / H
    zoom = float(np.prod(scale))
    seconds = len(frames) / FPS
    path_len = sum(np.hypot(np.array(tx) / W, np.array(ty) / H))
    return {"dx": round(dx, 4), "dy": round(dy, 4), "zoom": round(zoom, 4),
            "speed": round(float(path_len) / seconds, 4), "pairs": used}


def measure_one(item):
    cid, path = item
    cv2.setNumThreads(1)
    try:
        frames = decode(path)
        y = luma(frames)
        f = frames.astype(np.float32) / 255.0
        k = max(1, FPS // 2)
        mx, mn = f.max(axis=-1), f.min(axis=-1)
        n = len(frames)
        picks = [frames[int(n * q)] for q in (0.25, 0.5, 0.75)]
        return cid, {
            "seconds": round(duration(path), 3),
            "luma": round(float(y.mean()), 4),
            "luma_in": round(float(y[:k].mean()), 4),
            "luma_out": round(float(y[-k:].mean()), 4),
            "warmth": round(float((f[..., 0] - f[..., 2]).mean()), 4),
            "sat": round(float((mx - mn).mean()), 4),
            "cam": camera(frames),
        }, picks, None
    except Exception as e:
        return cid, None, None, f"{type(e).__name__}: {e}"


def embedder(device):
    import torch
    from transformers import AutoImageProcessor, AutoModel
    torch.set_num_threads(int(os.environ.get("MEASURE_TORCH_THREADS", "8")))
    proc = AutoImageProcessor.from_pretrained(EMBED_MODEL)
    model = AutoModel.from_pretrained(EMBED_MODEL).to(device).eval()

    def run(images):
        with torch.no_grad():
            inp = proc(images=images, return_tensors="pt").to(device)
            out = model(**inp).last_hidden_state[:, 0]
            return torch.nn.functional.normalize(out, dim=-1).cpu().numpy()
    return run


def pick_device():
    import torch
    if not torch.cuda.is_available():
        return "cpu"
    free, _ = torch.cuda.mem_get_info()
    return "cuda" if free > 6 * 1024 ** 3 else "cpu"


def neighbours(store, top=8):
    ids = sorted(store)
    if len(ids) < 2:
        return {i: {"near": [], "distinct": 0.5} for i in ids}, np.array([])
    e = np.stack([store[i] for i in ids])
    sims = e @ e.T
    np.fill_diagonal(sims, -1.0)
    k = min(10, len(ids) - 1)
    crowd = np.sort(sims, axis=1)[:, -k:].mean(axis=1)
    rank = crowd.argsort().argsort() / max(1, len(ids) - 1)
    res = {}
    for r, cid in enumerate(ids):
        order = np.argsort(-sims[r])[:top]
        res[cid] = {"near": [{"id": ids[j], "sim": round(float(sims[r, j]), 4)} for j in order],
                    "distinct": round(float(1.0 - rank[r]), 4),
                    "crowd": round(float(crowd[r]), 4)}
    return res, sims[np.triu_indices(len(ids), 1)]


def main():
    ap = argparse.ArgumentParser(description="measure clips (luma, colour, camera move, embedding) and neighbours")
    ap.add_argument("--root", required=True, help="clip root on this host")
    ap.add_argument("--list", required=True, help="json: {'measure': [[id, relpath]...], 'current': [id...]}")
    ap.add_argument("--store", required=True, help="npz embedding store kept on this host")
    ap.add_argument("--out", required=True)
    ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args()

    job = json.loads(Path(a.list).read_text())
    items = [(cid, Path(a.root) / rel) for cid, rel in job["measure"]]
    store = {}
    if Path(a.store).exists():
        z = np.load(a.store, allow_pickle=False)
        store = {k: z[k] for k in z.files}

    t0 = time.time()
    results, errors, images = {}, {}, {}
    with ProcessPoolExecutor(a.jobs) as ex:
        for i, (cid, m, picks, err) in enumerate(ex.map(measure_one, items, chunksize=2), 1):
            if err:
                errors[cid] = err
            else:
                results[cid] = m
                images[cid] = picks
            if i % 25 == 0 or i == len(items):
                print(f"measured {i}/{len(items)} in {time.time() - t0:.0f}s", flush=True)

    if images:
        device = pick_device()
        print(f"embedding {len(images)} clips on {device}", flush=True)
        run = embedder(device)
        ids = list(images)
        for s in range(0, len(ids), 32):
            chunk = ids[s:s + 32]
            flat = [img for cid in chunk for img in images[cid]]
            vec = run(flat).reshape(len(chunk), 3, -1).mean(axis=1)
            vec /= np.linalg.norm(vec, axis=1, keepdims=True)
            for cid, v in zip(chunk, vec):
                store[key(cid)] = v.astype(np.float32)
        np.savez(a.store, **store)

    current = {key(c): c for c in job["current"]}
    present = {k: store[k] for k in current if k in store}
    nb, pair_sims = neighbours(present)
    q = np.quantile(pair_sims, [0.5, 0.9, 0.99, 0.999]).round(4).tolist() if len(pair_sims) else []
    out = {
        "measured": results,
        "errors": errors,
        "neighbours": {current[k]: v for k, v in nb.items()},
        "missing_embedding": [c for k, c in current.items() if k not in store],
        "pair_sim_quantiles": dict(zip(["p50", "p90", "p99", "p999"], q)),
        "embed_model": EMBED_MODEL,
        "seconds": round(time.time() - t0, 1),
    }
    Path(a.out).write_text(json.dumps(out))
    print(f"done: {len(results)} measured, {len(errors)} errors, {len(present)} in neighbour pass, {out['seconds']}s")


def key(cid):
    return cid.replace("/", "__")


if __name__ == "__main__":
    sys.exit(main())

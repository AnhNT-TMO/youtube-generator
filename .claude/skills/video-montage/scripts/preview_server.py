#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np


def frames_of(path, w, h):
    cap = cv2.VideoCapture(str(path))
    out = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        out.append(cv2.resize(f, (w, h), interpolation=cv2.INTER_AREA))
    cap.release()
    if not out:
        raise ValueError(f"no frames decoded from {path}")
    return out


def label(f, text, h):
    s = h / 720
    cv2.putText(f, text, (int(16 * s), int(h - 18 * s)), cv2.FONT_HERSHEY_SIMPLEX, 0.6 * s, (0, 0, 0), int(4 * s), cv2.LINE_AA)
    cv2.putText(f, text, (int(16 * s), int(h - 18 * s)), cv2.FONT_HERSHEY_SIMPLEX, 0.6 * s, (255, 255, 255), max(1, int(1.5 * s)), cv2.LINE_AA)


def main():
    ap = argparse.ArgumentParser(description="render a low-res review video of a montage.json sequence (silent)")
    ap.add_argument("--montage", required=True)
    ap.add_argument("--root", required=True, help="clip root on this host (holds <clip id>.mp4)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--xfade", type=float, default=1.0)
    ap.add_argument("--labels", action="store_true", help="burn clip id + time into the corner")
    ap.add_argument("--cq", type=int, default=30)
    ap.add_argument("--first", type=int, help="render only the first N slots")
    ap.add_argument("--size", help="final WxH, scaled from --height with Lanczos on the GPU (e.g. 3840x2160)")
    ap.add_argument("--hevc", action="store_true", help="encode HEVC instead of H.264")
    ap.add_argument("--require-all", action="store_true",
                    help="exit 3 without rendering when any clip is missing under --root (list in <out>.missing.txt)")
    ap.add_argument("--wait-clips", type=float, default=0,
                    help="seconds between checks: wait until every clip exists under --root, then render (0 = no wait)")
    ap.add_argument("--intro-logo", help="RGBA round logo png: opening logo intro over the first clip (intro_server.py)")
    ap.add_argument("--intro-title", default="", help="channel name under the logo")
    ap.add_argument("--intro-tagline", default="", help="small line under the name")
    ap.add_argument("--intro-font", help="ttf for the intro text")
    a = ap.parse_args()

    doc = json.loads(Path(a.montage).read_text())
    seq = doc["sequence"][:a.first] if a.first else doc["sequence"]
    missing = sorted({s["clip"] for s in seq if not (Path(a.root) / f"{s['clip']}.mp4").exists()})
    last = None
    while missing and a.wait_clips:
        if len(missing) != last:
            print(time.strftime("%T ") + f"{len(missing)} clips missing under {a.root}: waiting for upscale", flush=True)
            last = len(missing)
        time.sleep(a.wait_clips)
        missing = sorted({s["clip"] for s in seq if not (Path(a.root) / f"{s['clip']}.mp4").exists()})
    if missing and a.require_all:
        Path(a.out + ".missing.txt").write_text("\n".join(missing) + "\n")
        print(f"{len(missing)} clips missing under {a.root}, not rendering (list: {a.out}.missing.txt)")
        return 3
    h = a.height
    w = int(round(h * 16 / 9 / 2) * 2)
    nx = int(round(a.xfade * a.fps))
    codec = ["-c:v", "hevc_nvenc", "-tag:v", "hvc1"] if a.hevc else ["-c:v", "h264_nvenc"]
    if a.size:
        ow, oh = a.size.lower().split("x")
        scale = ["-init_hw_device", "cuda=cu", "-filter_hw_device", "cu", "-vf",
                 f"format=nv12,hwupload_cuda,scale_cuda={ow}:{oh}:interp_algo=lanczos"]
    else:
        scale = ["-pix_fmt", "yuv420p"]
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}",
                            "-r", str(a.fps), "-i", "-", *scale, *codec, "-preset", "p5", "-rc", "vbr",
                            "-cq", str(a.cq), "-b:v", "0", "-movflags", "+faststart", a.out],
                           stdin=subprocess.PIPE)
    intro = None
    if a.intro_logo:
        from intro_server import Intro
        intro = Intro(w, h, a.fps, a.intro_logo, a.intro_title, a.intro_tagline, a.intro_font)
    alpha = np.linspace(0, 1, nx + 2)[1:-1].reshape(-1, 1, 1, 1).astype(np.float32)
    tail, written, t0 = None, 0, time.time()
    for i, s in enumerate(seq):
        fr = frames_of(Path(a.root) / f"{s['clip']}.mp4", w, h)
        if s["flip"]:
            fr = [cv2.flip(f, 1) for f in fr]
        if i == 0 and intro:
            intro.apply(fr)
        if a.labels:
            tag = f"{i + 1}/{len(seq)}  {s['clip']}{'  (flip)' if s['flip'] else ''}"
            for f in fr:
                label(f, tag, h)
        fr = np.stack(fr)
        if tail is not None and len(fr) > 2 * nx:
            fr[:nx] = (tail * (1 - alpha) + fr[:nx] * alpha).astype(np.uint8)
        body, tail = fr[:-nx], fr[-nx:].astype(np.float32)
        enc.stdin.write(body.tobytes())
        written += len(body)
        if (i + 1) % 50 == 0:
            print(f"{i + 1}/{len(seq)} clips, {written / a.fps / 60:.1f} min video, {time.time() - t0:.0f}s", flush=True)
    enc.stdin.write(tail.astype(np.uint8).tobytes())
    enc.stdin.close()
    rc = enc.wait()
    print(f"done rc={rc}: {(written + nx) / a.fps / 60:.1f} min, {time.time() - t0:.0f}s -> {a.out}")
    return rc


if __name__ == "__main__":
    sys.exit(main())

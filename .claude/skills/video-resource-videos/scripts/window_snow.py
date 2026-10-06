#!/usr/bin/env python3
USAGE = """Loop một clip muse + tuyết rơi nhẹ chỉ trong ô kính (GPU, chạy trên server qua window_snow.sh).

  window_snow.py <clip.mp4> <out.mp4> --window X:Y:W:H [--seconds 30] [--skip 1.0] [--xfade 1.5]
                 [--density 1.0] [--speed 1.0] [--freeze-window] [--mask-out mask.png] [--track]

  Loop: bỏ --skip giây đầu, hòa tan đuôi vào đầu --xfade giây → một vòng; lặp tới ~--seconds (bội số của vòng).
  Tuyết: 3 lớp (xa / giữa / sát kính), chu kỳ = cả video nên out.mp4 tự lặp liền mạch.
  --freeze-window: trong mặt nạ thay bằng trung vị theo thời gian của mọi khung (xóa tuyết/chuyển động của muse ngoài cửa).
  Mặt nạ: trong --window, điểm ảnh lạnh (xanh > đỏ) = cảnh ngoài trời; khung gỗ, đèn, đồ ấm bị loại; mép làm mềm.
  --track: clip máy trôi: không loop (chỉ bỏ --skip giây đầu), mặt nạ tính lại ở từng khung; --window nên là cả khung
           0:0:W:H khi ô kính dịch theo máy; --freeze-window không dùng được.
"""
import argparse
import math
import subprocess

import numpy as np
import torch
import torch.nn.functional as F

LAYERS = (
    {"count": 420, "size": (0.8, 1.2), "blur": 0.7, "alpha": (0.35, 0.60), "fall_per_period": (3, 5), "sway_px": (2, 6)},
    {"count": 150, "size": (0.9, 1.3), "blur": 1.1, "alpha": (0.55, 0.80), "fall_per_period": (5, 8), "sway_px": (4, 12)},
    {"count": 36, "size": (0.9, 1.3), "blur": 1.8, "alpha": (0.50, 0.75), "fall_per_period": (8, 12), "sway_px": (8, 22)},
)
SNOW_RGB = (236, 242, 252)


def probe(clip):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate",
                          "-of", "csv=p=0", clip], capture_output=True, text=True, check=True).stdout.strip().split(",")
    num, den = out[2].split("/")
    return int(out[0]), int(out[1]), int(num) / int(den)


def read_frames(clip, w, h):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", clip, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)


def loop_cycle(frames, fps, skip, xfade):
    body = frames[int(round(skip * fps)):]
    x = int(round(xfade * fps))
    if len(body) <= 2 * x:
        raise SystemExit("clip quá ngắn cho --skip / --xfade")
    head, tail = body[:x].astype(np.float32), body[-x:].astype(np.float32)
    a = (np.arange(x, dtype=np.float32) / x)[:, None, None, None]
    blend = (tail * (1 - a) + head * a).round().astype(np.uint8)
    return np.concatenate([blend, body[x:-x]])


def window_mask(frame, box, dev):
    x, y, w, h = box
    img = torch.from_numpy(frame[y:y + h, x:x + w].copy()).to(dev).float()
    r, b = img[..., 0], img[..., 2]
    cold = ((b - r) > 6).float()[None, None]
    cold = -F.max_pool2d(-F.max_pool2d(cold, 5, 1, 2), 9, 1, 4)
    cold = F.max_pool2d(-F.max_pool2d(-cold, 5, 1, 2), 5, 1, 2)
    k = gaussian(3.0, dev)
    cold = F.conv2d(F.conv2d(cold, k[None, None, None, :], padding=(0, k.numel() // 2)), k[None, None, :, None],
                    padding=(k.numel() // 2, 0))
    return cold.clamp(0, 1)[0, 0]


def gaussian(sigma, dev):
    r = max(1, int(math.ceil(sigma * 3)))
    t = torch.arange(-r, r + 1, device=dev, dtype=torch.float32)
    k = torch.exp(-0.5 * (t / sigma) ** 2)
    return k / k.sum()


class Snow:
    def __init__(self, w, h, period, density, speed, dev, seed=7):
        g = torch.Generator(device="cpu").manual_seed(seed)
        self.w, self.h, self.period, self.dev = w, h, period, dev
        self.layers = []
        for spec in LAYERS:
            n = int(spec["count"] * density * (w * h) / (560 * 290))
            if n == 0:
                continue
            u = lambda lo, hi: (torch.rand(n, generator=g) * (hi - lo) + lo)
            fall = torch.randint(spec["fall_per_period"][0], spec["fall_per_period"][1] + 1, (n,), generator=g).float()
            fall = torch.clamp((fall * speed).round(), min=1)
            self.layers.append({
                "x0": u(0, w).to(dev), "y0": u(0, h + 20).to(dev), "fall": fall.to(dev),
                "sway": u(*spec["sway_px"]).to(dev), "sway_n": torch.randint(1, 4, (n,), generator=g).float().to(dev),
                "phase": u(0, 2 * math.pi).to(dev), "drift": torch.randint(-1, 2, (n,), generator=g).float().to(dev),
                "alpha": u(*spec["alpha"]).to(dev), "size": u(*spec["size"]).to(dev),
                "kernel": gaussian(spec["blur"], dev), "sigma": spec["blur"],
            })

    def alpha(self, i):
        t = (i % self.period) / self.period
        acc = torch.zeros(self.h, self.w, device=self.dev)
        out = torch.zeros(self.h, self.w, device=self.dev)
        for L in self.layers:
            wrap_h = self.h + 20
            y = (L["y0"] + L["fall"] * wrap_h * t) % wrap_h - 10
            x = (L["x0"] + L["drift"] * self.w * t + L["sway"] * torch.sin(2 * math.pi * L["sway_n"] * t + L["phase"])) % self.w
            acc.zero_()
            x0, y0 = x.floor(), y.floor()
            fx, fy = x - x0, y - y0
            amp = L["alpha"] * L["size"] * 2 * math.pi * L["sigma"] ** 2
            for dx, dy, wgt in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
                xi, yi = (x0 + dx).long(), (y0 + dy).long()
                ok = (xi >= 0) & (xi < self.w) & (yi >= 0) & (yi < self.h)
                acc.index_put_((yi[ok], xi[ok]), (amp * wgt)[ok], accumulate=True)
            k = L["kernel"]
            p = k.numel() // 2
            layer = F.conv2d(F.conv2d(acc[None, None], k[None, None, None, :], padding=(0, p)), k[None, None, :, None], padding=(p, 0))[0, 0]
            out = 1 - (1 - out) * (1 - layer.clamp(0, 1))
        return out


def main():
    ap = argparse.ArgumentParser(usage=USAGE)
    ap.add_argument("clip")
    ap.add_argument("out")
    ap.add_argument("--window", required=True)
    ap.add_argument("--seconds", type=float, default=30)
    ap.add_argument("--skip", type=float, default=1.0)
    ap.add_argument("--xfade", type=float, default=1.5)
    ap.add_argument("--density", type=float, default=1.0)
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--freeze-window", action="store_true")
    ap.add_argument("--mask-out")
    ap.add_argument("--cq", type=int, default=19)
    ap.add_argument("--track", action="store_true")
    a = ap.parse_args()
    if a.track and a.freeze_window:
        raise SystemExit("--track không đi cùng --freeze-window")
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    w, h, fps = probe(a.clip)
    box = tuple(int(v) for v in a.window.split(":"))
    frames = read_frames(a.clip, w, h)
    if a.track:
        cycle = frames[int(round(a.skip * fps)):]
        reps, total = 1, len(cycle)
    else:
        cycle = loop_cycle(frames, fps, a.skip, a.xfade)
        reps = max(1, round(a.seconds * fps / len(cycle)))
        total = reps * len(cycle)
    mask = window_mask(cycle[len(cycle) // 2], box, dev)
    if a.mask_out:
        full = np.zeros((h, w), np.uint8)
        full[box[1]:box[1] + box[3], box[0]:box[0] + box[2]] = (mask.cpu().numpy() * 255).astype(np.uint8)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{w}x{h}", "-i", "-", a.mask_out],
                       input=full.tobytes(), check=True)
    snow = Snow(box[2], box[3], max(total, round(30 * fps)) if a.track else total, a.density, a.speed, dev)
    color = torch.tensor(SNOW_RGB, device=dev, dtype=torch.float32)
    enc = ["-c:v", "h264_nvenc", "-preset", "p6", "-rc", "vbr", "-cq", str(a.cq), "-b:v", "0"] if dev == "cuda" else ["-c:v", "libx264", "-crf", "18"]
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", f"{fps}", "-i", "-",
                           *enc, "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out], stdin=subprocess.PIPE)
    x, y, bw, bh = box
    plate = None
    if a.freeze_window:
        stack = torch.from_numpy(np.ascontiguousarray(cycle[:, y:y + bh, x:x + bw])).to(dev)
        plate = stack.median(dim=0).values.float()
        del stack
    m3 = mask[..., None]
    for i in range(total):
        src = cycle[i % len(cycle)]
        frame = torch.from_numpy(src.copy()).to(dev).float()
        if a.track:
            mask = window_mask(src, box, dev)
        al = (snow.alpha(i) * mask)[..., None]
        region = frame[y:y + bh, x:x + bw]
        if plate is not None:
            region = region * (1 - m3) + plate * m3
        frame[y:y + bh, x:x + bw] = region * (1 - al) + color * al
        ff.stdin.write(frame.round().clamp(0, 255).byte().cpu().numpy().tobytes())
    ff.stdin.close()
    if ff.wait():
        raise SystemExit("ffmpeg lỗi")
    print(f"{a.out}: {total} khung = {total / fps:.1f} s ({reps} vòng × {len(cycle) / fps:.2f} s), tuyết {sum(len(L['x0']) for L in snow.layers)} hạt, {dev}")


if __name__ == "__main__":
    main()

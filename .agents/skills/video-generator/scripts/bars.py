import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from config import H, W

SR = 22050
WIN = 2048


def load_audio(path, start, dur):
    cmd = ["ffmpeg", "-v", "error"]
    if start:
        cmd += ["-ss", str(start)]
    cmd += ["-i", path, "-t", str(dur + 1), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, check=True)
    return np.frombuffer(p.stdout, dtype=np.float32)


def spectrum_track(samples, nframes, fps, c):
    nb = c["bands"]
    edges = np.round(np.geomspace(c["fmin"], c["fmax"], nb + 1) / (SR / WIN))
    edges = edges.astype(int).clip(1, WIN // 2 - 1)
    for b in range(nb):
        if edges[b + 1] <= edges[b]:
            edges[b + 1] = edges[b] + 1
    widths = np.diff(edges).astype(np.float32)

    win = np.hanning(WIN).astype(np.float32)
    centers = (np.arange(nframes) / fps * SR).astype(int)
    out = np.zeros((nframes, nb), dtype=np.float32)
    pad = np.pad(samples, (WIN, WIN + int(SR)))

    CH = 512
    for s in range(0, nframes, CH):
        e = min(nframes, s + CH)
        idx = centers[s:e, None] + WIN - WIN // 2 + np.arange(WIN)[None, :]
        mag = np.abs(np.fft.rfft(pad[idx] * win, axis=1))
        db = 20 * np.log10(mag + 1e-7)
        out[s:e] = np.add.reduceat(db, edges[:-1], axis=1)[:, :nb] / widths

    lo = np.percentile(out, 12, axis=0)
    hi = np.percentile(out, 97, axis=0)
    out = np.clip((out - lo) / np.maximum(hi - lo, 4.0), 0, 1) ** 1.05
    out *= np.linspace(1.0, 0.80, nb, dtype=np.float32)

    sm = np.empty_like(out)
    prev = out[0].copy()
    for i in range(nframes):
        cur = out[i]
        k = np.where(cur > prev, c["attack"], c["release"])
        prev = prev + (cur - prev) * k
        sm[i] = prev
    return sm


class BarStrip:

    def __init__(self, c):
        self.c = c
        n, max_h, gr = c["bands"], c["height_px"], c["glow_px"]
        span, center = c["span"] * W, c["center"] * W
        slot = span / n
        bw = max(2, int(round(slot * c["bar_width"])))
        x0 = center - span / 2 + (slot - bw) / 2
        self.yb = H - c["baseline_px"]
        m = 3 * gr + 2

        self.X = (int(x0) - m) // 2 * 2
        self.Y = (self.yb - max_h - m) // 2 * 2
        self.w = (int(x0 + (n - 1) * slot) + bw + m - self.X + 1) // 2 * 2
        self.h = (min(H, self.yb + m) - self.Y) // 2 * 2
        self.max_h = max_h

        self.col_bar = np.full(self.w, -1, np.int32)
        self.cap = np.zeros(self.w, np.float32)
        r = bw / 2
        for i in range(n):
            bx = int(x0 + i * slot) - self.X
            for j in range(bw):
                dx = abs(j + 0.5 - r) / r
                self.col_bar[bx + j] = i
                self.cap[bx + j] = r * (1 - np.sqrt(max(0.0, 1 - dx * dx)))
        self.on = self.col_bar >= 0
        self.rows = (np.arange(self.h, dtype=np.float32) + self.Y)[:, None]

    def mask(self, vals):
        hts = 6 + (self.max_h - 6) * np.clip(vals, 0, 1)
        top = (self.yb - hts[self.col_bar]) + self.cap
        bot = self.yb - self.cap
        cov = np.minimum(self.rows + 1, bot) - np.maximum(self.rows, top)
        cov = np.clip(cov, 0, 1) * self.on
        return (cov * (255 * self.c["opacity"]) + 0.5).astype(np.uint8)

    def gradient(self):
        tip = np.array(self.c["color_tip"], np.float32)
        base = np.array(self.c["color_base"], np.float32)
        f = np.clip((self.rows[:, 0] - (self.yb - self.max_h)) / max(1, self.max_h - 1), 0, 1)
        col = tip[None, :] + (base - tip)[None, :] * f[:, None]
        img = np.repeat(col[:, None, :], self.w, axis=1)
        return Image.fromarray((img + 0.5).astype(np.uint8), "RGB")

    def scrim(self):
        c = self.c
        max_h, span, center = c["height_px"], c["span"] * W, c["center"] * W
        x0 = int(max(0, center - span * 0.78)) // 2 * 2
        x1 = int(min(W, center + span * 0.78)) // 2 * 2
        y0 = int(H - max_h * 2.6) // 2 * 2
        y = np.arange(y0, H, dtype=np.float32)[:, None]
        x = np.arange(x0, x1, dtype=np.float32)[None, :]
        fy = np.clip((y - (H - max_h * 2.6)) / (max_h * 2.6), 0, 1) ** 1.8
        fx = np.clip(1 - (np.abs(x - center) / (span * 0.78)) ** 2.2, 0, 1)
        a = np.zeros((H - y0, x1 - x0, 4), np.uint8)
        a[..., 3] = np.round(255 * c["scrim"] * fy * fx).astype(np.uint8)
        return Image.fromarray(a, "RGBA"), (x0, y0)

    def filters(self, fps, bg, grad, mask, out):
        c = self.c
        k = c["glow_strength"] / max(1e-3, c["opacity"])
        gc = "0x%02x%02x%02x" % tuple(c["glow_color"])
        f = [f"[{mask}]split[m1][m2]",
             f"[m2]gblur=sigma={c['glow_px']},lut=y='min(255,val*{k:.4f})'[ga]",
             f"color=c={gc}:s={self.w}x{self.h}:r={fps}[gc]",
             "[gc][ga]alphamerge[glow]",
             f"[{grad}][m1]alphamerge[bars]"]
        f.append(f"[{bg}][glow]overlay={self.X}:{self.Y}[s1]")
        f.append(f"[s1][bars]overlay={self.X}:{self.Y},format=yuv420p[{out}]")
        return ";".join(f)

import math

import numpy as np
from PIL import Image, ImageFilter

from config import H, W
from effects import Particles


def _ease_out(u):
    u = min(1.0, max(0.0, u))
    return 1 - (1 - u) ** 3


def _ease_in_out(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


def _radial(w, h, power):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.hypot((x - w / 2) / (w / 2), (y - h / 2) / (h / 2))
    return np.clip(1 - d, 0, 1) ** power


class Intro:
    def __init__(self, scene, image_path, cfg):
        self.c, self.scene = cfg["intro"], scene
        c = self.c
        self.D = c["seconds"]
        self.fps = cfg["fps"]
        base = Image.open(image_path).convert("RGB").resize((W, H), Image.LANCZOS)
        bg = np.asarray(base.filter(ImageFilter.GaussianBlur(c["bg_blur_px"])), np.float32)
        vig = 0.55 + 0.45 * _radial(W, H, 0.6)[:, :, None]
        self.bg = bg * c["bg_dim"] * vig

        self.logo = Image.open(cfg["logo"]["path"]).convert("RGBA")
        self.lw = c["logo_width_px"]
        hs = int(self.lw * 2.2)
        self.halo = _radial(hs, hs, 2.2)[:, :, None] * (np.array(c["halo_color"], np.float32))
        fs = int(self.lw * 0.42)
        self.flame = _radial(fs, fs, 2.0)[:, :, None] * np.array([255, 224, 160], np.float32)
        self.particles = [l for l in scene.layers if isinstance(l, Particles)]

    def _logo(self, scale):
        w = max(8, int(self.lw * scale))
        img = self.logo.resize((w, w), Image.LANCZOS)
        a = np.asarray(img, np.float32) / 255.0
        return a[:, :, :3] * 255.0, a[:, :, 3], w

    @staticmethod
    def _add(frame, spr, cx, cy, gain):
        h, w = spr.shape[:2]
        x0, y0 = int(cx - w / 2), int(cy - h / 2)
        sx, sy = max(0, -x0), max(0, -y0)
        x1, y1 = min(W, x0 + w), min(H, y0 + h)
        x0c, y0c = max(0, x0), max(0, y0)
        frame[y0c:y1, x0c:x1] += spr[sy:sy + (y1 - y0c), sx:sx + (x1 - x0c)] * gain

    def frame(self, t):
        c, D = self.c, self.D
        x0 = D - c["crossfade_seconds"]
        xf = c["crossfade_seconds"] - 1 / self.fps
        u_in = _ease_out(t / c["fade_in_seconds"])
        u_out = _ease_in_out((t - x0) / xf)
        logo_op = u_in * (1 - _ease_in_out((t - x0) / (xf * 0.7)))
        scale = 0.86 + 0.14 * u_in + 0.06 * u_out
        cx, cy = W / 2, H / 2

        f = self.bg.copy()
        pulse = 0.75 + 0.25 * math.sin(2 * math.pi * t / 2.2)
        self._add(f, self.halo, cx, cy, c["halo_strength"] / 255.0 * pulse * logo_op)
        f8 = np.clip(f, 0, 255).astype(np.uint8)
        for p in self.particles:
            p.draw(f8, t - D)
        f = f8.astype(np.float32)

        if logo_op > 0.003:
            rgb, al, w = self._logo(scale)
            s0, s1 = c["shine_at"], c["shine_at"] + 0.9
            if s0 < t < s1:
                yy, xx = np.mgrid[0:w, 0:w].astype(np.float32) / w
                p = -0.4 + 1.8 * (t - s0) / (s1 - s0)
                band = np.exp(-(((xx + yy * 0.45) - p) / 0.10) ** 2)
                rgb = rgb + (255 - rgb) * (band * 0.55)[:, :, None]
            x, y = int(cx - w / 2), int(cy - w / 2)
            a = (al * logo_op)[:, :, None]
            f[y:y + w, x:x + w] = f[y:y + w, x:x + w] * (1 - a) + rgb * a
            if c.get("flame", True):
                ignite = _ease_out((t - 0.5) / 0.8) * (0.8 + 0.2 * math.sin(2 * math.pi * t / 1.3))
                self._add(f, self.flame, cx, cy - w * 0.21, 0.50 / 255.0 * ignite * logo_op)

        if u_out > 0:
            f = f * (1 - u_out) + self.scene.frame(t - D).astype(np.float32) * u_out
        return np.clip(f, 0, 255).astype(np.uint8)


def bars_gain(t, cfg):
    c = cfg["intro"]
    if not c["enabled"]:
        return 1.0
    x0 = c["seconds"] - c["crossfade_seconds"]
    return _ease_in_out((t - x0) / c["crossfade_seconds"])


def render(image, preset, bars, encoder, out):
    import subprocess
    import config
    from effects import make_scene
    from make_loop import encode_cmd
    cfg = config.load(preset)
    fps = cfg["fps"]
    it = Intro(make_scene(image, cfg, bars=bars), image, cfg)
    ff = subprocess.Popen(encode_cmd(out, fps, cfg["encode"], encoder), stdin=subprocess.PIPE)
    for k in range(int(round(it.D * fps))):
        ff.stdin.write(it.frame(k / fps).tobytes())
    ff.stdin.close()
    if ff.wait():
        raise RuntimeError("intro encode failed")
    return out

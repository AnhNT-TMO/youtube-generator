import math

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

GOLD = np.array([110, 196, 255], np.float32)
CREAM = np.array([214, 238, 252], np.float32)

T = {"seconds": 4.8, "black_in": 0.35, "sweep": (0.3, 1.5), "flare_at": 1.55, "letters_at": 1.5, "letter_step": 0.09,
     "letter_fade": 0.45, "line": (2.0, 2.8), "tagline": (2.5, 3.1), "shine": (3.0, 3.7), "out": (3.8, 4.8)}
L = {"logo_d": 0.40, "logo_y": 0.40, "title_px": 0.105, "title_y": 0.755, "track": (0.40, 0.20), "line_y": 0.845,
     "line_half": 0.17, "tag_px": 0.032, "tag_y": 0.885, "tag_track": 0.28, "blur": 0.012, "dim": 0.55, "dust": 90}


def ease_out(u):
    u = min(1.0, max(0.0, u))
    return 1 - (1 - u) ** 3


def ease_in_out(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


def span(t, a, b):
    return ease_in_out((t - a) / (b - a))


def gauss(n, sigma):
    r = np.arange(n, dtype=np.float32) - (n - 1) / 2
    return np.exp(-(r / sigma) ** 2 / 2)


def add(f, spr, cx, cy, gain):
    H, W = f.shape[:2]
    h, w = spr.shape[:2]
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    sx, sy = max(0, -x0), max(0, -y0)
    x1, y1 = min(W, x0 + w), min(H, y0 + h)
    x0c, y0c = max(0, x0), max(0, y0)
    if x1 > x0c and y1 > y0c:
        f[y0c:y1, x0c:x1] += spr[sy:sy + (y1 - y0c), sx:sx + (x1 - x0c)] * gain


def over(f, bgr, alpha, x0, y0):
    H, W = f.shape[:2]
    h, w = alpha.shape
    sx, sy = max(0, -x0), max(0, -y0)
    x1, y1 = min(W, x0 + w), min(H, y0 + h)
    x0c, y0c = max(0, x0), max(0, y0)
    if x1 <= x0c or y1 <= y0c:
        return
    a = alpha[sy:sy + (y1 - y0c), sx:sx + (x1 - x0c), None]
    c = bgr[sy:sy + (y1 - y0c), sx:sx + (x1 - x0c)] if bgr.ndim == 3 else bgr
    f[y0c:y1, x0c:x1] = f[y0c:y1, x0c:x1] * (1 - a) + c * a


def text_sprites(text, font_path, px, weight):
    font = ImageFont.truetype(font_path, px)
    try:
        font.set_variation_by_axes([weight])
    except Exception:
        pass
    pad = px // 2
    out = []
    for i, ch in enumerate(text):
        x = font.getlength(text[:i])
        w = int(font.getlength(ch)) + 2 * pad
        im = Image.new("L", (max(w, 1), px * 2), 0)
        ImageDraw.Draw(im).text((pad, px // 2), ch, font=font, fill=255)
        a = np.asarray(im, np.float32) / 255.0
        out.append((x, a, pad))
    return out, font.getlength(text)


class Intro:
    def __init__(self, W, H, fps, logo_path, title, tagline, font_path, seed=7):
        self.W, self.H, self.fps = W, H, fps
        logo = cv2.imread(logo_path, cv2.IMREAD_UNCHANGED)
        if logo is None or logo.shape[2] != 4:
            raise ValueError(f"{logo_path} must be an RGBA png")
        d = int(round(H * L["logo_d"]))
        logo = cv2.resize(logo, (d, d), interpolation=cv2.INTER_AREA).astype(np.float32)
        self.logo_bgr, self.logo_a = logo[:, :, :3], logo[:, :, 3] / 255.0
        self.d, self.cx, self.cy = d, W / 2, H * L["logo_y"]
        yy, xx = np.mgrid[0:d, 0:d].astype(np.float32) - (d - 1) / 2
        self.theta = (np.arctan2(xx, -yy) + 2 * np.pi) % (2 * np.pi)
        m = int(d * 1.2)
        ry, rx = np.mgrid[0:m, 0:m].astype(np.float32) - (m - 1) / 2
        r = np.hypot(rx, ry)
        self.R = d / 2 + H * 0.012
        self.ring_theta = (np.arctan2(rx, -ry) + 2 * np.pi) % (2 * np.pi)
        self.ring = np.exp(-((r - self.R) / (H * 0.0016)) ** 2) + 0.35 * np.exp(-((r - self.R) / (H * 0.007)) ** 2)
        self.m = m
        s = int(H * 0.05) | 1
        self.dot = np.outer(gauss(s, s / 6), gauss(s, s / 6))[:, :, None] * GOLD
        fl = int(H * 0.36) | 1
        arm_v = np.outer(gauss(fl, fl / 5), gauss(fl, H * 0.0018))
        arm_h = arm_v.T
        core = np.outer(gauss(fl, H * 0.012), gauss(fl, H * 0.012))
        self.flare = (np.maximum(arm_v, arm_h) + core)[:, :, None] * np.array([200, 235, 255], np.float32)
        self.title = text_sprites(title, font_path, int(H * L["title_px"]), 560) if title else None
        self.tag = text_sprites(tagline.upper() if tagline else "", font_path, int(H * L["tag_px"]), 500) if tagline else None
        rng = np.random.default_rng(seed)
        n = L["dust"]
        self.dust = np.stack([rng.uniform(0, W, n), rng.uniform(0, H, n), rng.uniform(4, 22, n) * H / 1080,
                              rng.uniform(0.15, 0.9, n), rng.uniform(0, 2 * np.pi, n), rng.uniform(1.5, 3.5, n),
                              rng.uniform(0.25, 0.8, n)], 1)
        self.vig = (0.45 + 0.55 * np.clip(1 - np.hypot(*(np.mgrid[0:H, 0:W].astype(np.float32)
                                                       / np.array([H, W], np.float32)[:, None, None] * 2 - 1)) / 1.2,
                                          0, 1) ** 0.8)[:, :, None]
        self.frames = int(round(T["seconds"] * fps))

    def draw_text(self, f, sprites, cx, base_y, px, track_em, t0, step, fade, rise, op, color, glow):
        letters, width = sprites
        track = track_em * px
        total = width + track * (len(letters) - 1)
        x_start = cx - total / 2
        for i, (x, a, pad) in enumerate(letters):
            u = ease_out((self.t - t0 - i * step) / fade)
            if u <= 0:
                continue
            x0 = int(round(x_start + x + track * i - pad))
            y0 = int(round(base_y - px * 1.25 + rise * (1 - u)))
            alpha = a * u * op
            if glow:
                g = cv2.GaussianBlur(a, (0, 0), px * 0.12)[:, :, None] * GOLD * (glow * u * op)
                h, w = a.shape
                add(f, g, x0 + w / 2, y0 + h / 2, 1.0)
            if self.shine is not None:
                xs = (x0 + np.arange(a.shape[1], dtype=np.float32)) / self.W
                band = np.exp(-((xs - self.shine) / 0.035) ** 2)[None, :, None]
                col = color + (255 - color) * band * 0.8
                over(f, np.broadcast_to(col, a.shape + (3,)), alpha, x0, y0)
            else:
                over(f, color, alpha, x0, y0)

    def apply(self, fr):
        H, W, fps = self.H, self.W, self.fps
        for k in range(min(len(fr), self.frames)):
            t = self.t = k / fps
            clip = fr[k].astype(np.float32)
            u_out = span(t, *T["out"])
            op = 1 - u_out
            f = cv2.GaussianBlur(clip, (0, 0), H * L["blur"]) * L["dim"] * self.vig
            f *= ease_out(t / T["black_in"])

            for x, y, size, spd, ph, tw, a in self.dust:
                yy = (y - spd * H * 0.02 * t) % H
                xx = x + math.sin(ph + t * 0.6) * H * 0.006
                g = a * (0.6 + 0.4 * math.sin(ph + 2 * math.pi * t / tw)) * op * 0.55
                add(f, cv2.resize(self.dot, (int(size), int(size))), xx, yy, g)

            sweep = span(t, *T["sweep"]) * 2 * np.pi
            if sweep > 0:
                soft = 0.35
                ring_m = np.clip((sweep - self.ring_theta) / 0.05 + 1, 0, 1) if sweep < 2 * np.pi else 1.0
                add(f, (self.ring * ring_m)[:, :, None] * GOLD, self.cx, self.cy, 0.9 * op)
                logo_m = np.clip((sweep - self.theta) / soft, 0, 1) if sweep < 2 * np.pi else 1.0
                pop = 0.94 + 0.06 * ease_out((t - T["sweep"][0]) / 1.4)
                d = int(self.d * pop) | 0
                bgr = cv2.resize(self.logo_bgr, (d, d), interpolation=cv2.INTER_AREA)
                al = cv2.resize(self.logo_a * logo_m, (d, d), interpolation=cv2.INTER_AREA)
                over(f, bgr, al * op, int(self.cx - d / 2), int(self.cy - d / 2))
                if sweep < 2 * np.pi:
                    hx = self.cx + self.R * math.sin(sweep)
                    hy = self.cy - self.R * math.cos(sweep)
                    add(f, self.dot, hx, hy, 2.2)
                    add(f, cv2.resize(self.flare, None, fx=0.35, fy=0.35), hx, hy, 0.6)

            fl = math.exp(-((t - T["flare_at"]) / 0.28) ** 2)
            if fl > 0.01:
                add(f, self.flare, self.cx, self.cy - self.R, fl * 1.1 * op)

            self.shine = (-0.1 + 1.2 * (t - T["shine"][0]) / (T["shine"][1] - T["shine"][0])) \
                if T["shine"][0] < t < T["shine"][1] else None
            if self.title:
                px = int(H * L["title_px"])
                track = L["track"][0] + (L["track"][1] - L["track"][0]) * ease_out((t - T["letters_at"]) / 1.4)
                self.draw_text(f, self.title, W / 2, H * L["title_y"], px, track, T["letters_at"], T["letter_step"],
                               T["letter_fade"], H * 0.02, op, CREAM, 0.55)
            lu = span(t, *T["line"])
            if lu > 0:
                half = W * L["line_half"] * lu
                xs = np.arange(int(half * 2) + 1, dtype=np.float32) - half
                prof = np.clip(1 - np.abs(xs) / max(half, 1), 0, 1) ** 0.6
                rows = int(H * 0.012) | 1
                spr = np.outer(gauss(rows, H * 0.0011) + 0.3 * gauss(rows, H * 0.004), prof)[:, :, None] * GOLD
                add(f, spr, W / 2, H * L["line_y"], 0.9 * op)
                add(f, self.dot, W / 2, H * L["line_y"], 1.4 * lu * op)
            if self.tag:
                self.shine = None
                tu = span(t, *T["tagline"])
                if tu > 0:
                    px = int(H * L["tag_px"])
                    self.draw_text(f, self.tag, W / 2, H * L["tag_y"], px, L["tag_track"], T["tagline"][0], 0.0,
                                   T["tagline"][1] - T["tagline"][0], 0.0, op, CREAM * 0.92, 0.0)

            if u_out > 0:
                f = f * (1 - u_out) + clip * u_out
            fr[k] = np.clip(f, 0, 255).astype(np.uint8)

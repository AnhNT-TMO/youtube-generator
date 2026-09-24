"""Loop-safe effects over a still photo.

Every effect is a pure function of the loop phase p = (t mod loop) / loop,
and everything that moves does a whole number of cycles per loop. The frame at
t = loop is therefore identical to the frame at t = 0, so copies of the loop
play back to back without a visible seam.
"""
import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import brand
from config import DIRECTIONS, H, PX_SCALE, W, cycles, wave


# ----------------------------------------------------------------- helpers --
def to_layers(sprite):
    a = np.asarray(sprite, np.float32) / 255.0
    return a[:, :, :3] * 255.0, a[:, :, 3]


def blit(frame, rgb, alpha, x, y, opacity=1.0):
    """Alpha-composite a precomputed sprite onto the uint8 frame in place."""
    h, w = alpha.shape
    sx, sy = max(0, -x), max(0, -y)
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0 or opacity <= 0.003:
        return
    a = alpha[sy:sy + (y1 - y0), sx:sx + (x1 - x0)] * opacity
    c = rgb[sy:sy + (y1 - y0), sx:sx + (x1 - x0)]
    reg = frame[y0:y1, x0:x1].astype(np.float32)
    frame[y0:y1, x0:x1] = (reg * (1 - a[:, :, None])
                           + c * a[:, :, None]).astype(np.uint8)


def add_glow(frame, glow, x0, y0):
    """Add a (h, w, 3) float sprite onto the frame at (x0, y0), clipped."""
    h, w = glow.shape[:2]
    sx, sy = max(0, -x0), max(0, -y0)
    cx0, cy0 = max(0, x0), max(0, y0)
    cx1, cy1 = min(W, x0 + w), min(H, y0 + h)
    if cx1 <= cx0 or cy1 <= cy0:
        return
    g = glow[sy:sy + (cy1 - cy0), sx:sx + (cx1 - cx0)]
    reg = frame[cy0:cy1, cx0:cx1].astype(np.int16)
    reg += g.astype(np.int16)
    frame[cy0:cy1, cx0:cx1] = np.clip(reg, 0, 255).astype(np.uint8)


def corner_xy(corner, w, h, margin):
    x = W - margin - w if corner[1] == "r" else margin
    y = margin if corner[0] == "t" else H - margin - h
    return x, y


# ------------------------------------------------------------------- light --
def light_mask(cfg):
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    for s in cfg["shapes"]:
        if isinstance(s, dict):
            cx, cy, rx, ry = s["ellipse"]
            d.ellipse([W * (cx - rx), H * (cy - ry), W * (cx + rx), H * (cy + ry)], fill=255)
        else:
            d.polygon([(W * x, H * y) for x, y in s], fill=255)
    return m.filter(ImageFilter.GaussianBlur(cfg["blur_px"]))


class Plates:
    """The photo with the light shaft at `levels` brightness steps, plus the
    logo burned in, so each frame starts from a plain array copy."""

    def __init__(self, base, cfg, loop):
        self.cfg, self.loop = cfg["light"], loop
        lc = self.cfg
        if lc["enabled"]:
            mask = light_mask(lc)
            tint = Image.new("RGB", (W, H), tuple(lc["color"]))
            n = lc["levels"]
            self.plates = [np.asarray(Image.composite(
                Image.blend(base, tint, lc["floor"] + lc["amount"] * k / (n - 1)),
                base, mask)) for k in range(n)]
        else:
            self.plates = [np.asarray(base)]
        self.plates = [p.copy() for p in self.plates]   # writable

    def burn(self, rgb, alpha, x, y, opacity=1.0):
        for p in self.plates:
            blit(p, rgb, alpha, x, y, opacity)

    def at(self, t):
        if len(self.plates) == 1:
            return self.plates[0].copy()
        lc = self.cfg
        b = lc["base"] + wave(t, lc["waves"], self.loop)
        k = int(round(min(1.0, max(0.0, b)) * (len(self.plates) - 1)))
        return self.plates[k].copy()


def add_scrim(plates, cfg):
    """The soft shade under the spectrum row is still, so it lives in the loop
    and extend.py only has to draw the moving bars."""
    from bars import BarStrip
    img, (x, y) = BarStrip(cfg["bars"]).scrim()
    rgb, al = to_layers(img)
    plates.burn(rgb, al, x, y)


def add_logo(plates, cfg):
    lc = cfg["logo"]
    if not lc["enabled"]:
        return
    img = Image.open(lc["path"]).convert("RGBA")
    w = lc["width_px"]
    img = img.resize((w, round(img.height * w / img.width)), Image.LANCZOS)
    sh = lc.get("shadow")
    pad = 0
    if sh:
        img = brand.drop_shadow(img, radius=sh["radius"], spread=sh["spread"], offset=(0, round(5 * PX_SCALE)))
        pad = img.info["pad"]
    x, y = corner_xy(lc["corner"], w, img.height - 2 * pad, lc["margin_px"])
    rgb, al = to_layers(img)
    plates.burn(rgb, al, x - pad, y - pad, lc["opacity"])


# ----------------------------------------------------------------- lantern --
class Lantern:
    def __init__(self, cfg, loop):
        self.c, self.loop = cfg, loop
        r = int(cfg["radius"] * W)
        cx, cy = int(cfg["center"][0] * W), int(cfg["center"][1] * H)
        yy, xx = np.mgrid[-r:r + 1, -r:r + 1].astype(np.float32)
        fall = np.clip(1 - np.hypot(xx, yy) / r, 0, 1) ** 2.6
        self.glow = fall[:, :, None] * (np.array(cfg["color"], np.float32) / 255.0)
        self.xy = (cx - r, cy - r)

    def draw(self, frame, t):
        f = self.c["base"] + wave(t, self.c["waves"], self.loop)
        add_glow(frame, self.glow * (self.c["strength"] * max(0.0, f)), *self.xy)


# --------------------------------------------------------------- particles --
def _dot(r, power=2.4):
    s = r * 2 + 1
    y, x = np.mgrid[0:s, 0:s].astype(np.float32)
    d = np.hypot(x - r, y - r) / max(r, 1)
    return np.clip(1 - d, 0, 1) ** power


def _flake(r):
    """Six thin arms with a soft core; tiny radii fall back to a dot."""
    if r < 4:
        return _dot(r)
    S = 4
    s = (r * 2 + 1) * S
    c = s / 2
    img = Image.new("L", (s, s), 0)
    d = ImageDraw.Draw(img)
    lw = max(1, int(S * max(1.0, r / 5)))
    for k in range(6):
        a = math.pi / 3 * k + math.pi / 2
        ex, ey = c + math.cos(a) * r * S * 0.95, c + math.sin(a) * r * S * 0.95
        d.line([(c, c), (ex, ey)], fill=255, width=lw)
        for f in (0.55,):                         # one pair of side branches
            bx, by = c + math.cos(a) * r * S * f, c + math.sin(a) * r * S * f
            for side in (-1, 1):
                b = a + side * math.pi / 4
                d.line([(bx, by), (bx + math.cos(b) * r * S * 0.30,
                                   by + math.sin(b) * r * S * 0.30)], fill=255, width=lw)
    img = img.filter(ImageFilter.GaussianBlur(S * 0.5)).resize((r * 2 + 1, r * 2 + 1),
                                                               Image.LANCZOS)
    arm = np.asarray(img, np.float32) / 255.0
    return np.clip(arm * 0.85 + _dot(r, 3.0) * 0.6, 0, 1)


class Particles:
    """One layer of drifting points coming from one of 8 sides/corners.

    Each particle moves on a wrap-around field slightly larger than the frame
    and crosses it a whole number of times per loop, so its position at the
    end of the loop is exactly where it started.
    """

    def __init__(self, c, loop):
        self.c, self.loop = c, loop
        rnd = random.Random(c["seed"])
        self.dx, self.dy = DIRECTIONS[c["from"]]
        rmin, rmax = c["size_px"]
        swmin, swmax = c["sway_px"]
        self.m = int(rmax + swmax + 8)               # off-screen margin, px
        self.FW, self.FH = W + 2 * self.m, H + 2 * self.m
        make = _flake if c["shape"] == "flake" else _dot
        self.spr = {r: make(r) for r in range(max(1, int(rmin)), int(rmax) + 1)}
        self.tint = np.array(c["color"], np.float32) / 255.0

        # one crossing of the screen along the motion, in crossings of the field
        screen, field = (H, self.FH) if self.dy else (W, self.FW)
        k0 = loop / c["cross_seconds"] * screen / field
        straight = self.dx == 0 or self.dy == 0
        n = c["count"]
        a = {k: np.empty(n, np.float32) for k in
             ("x0", "y0", "k", "amp", "sn", "sph", "tn", "tph", "val")}
        self.r = np.empty(n, np.int32)
        for i in range(n):
            depth = rnd.random()
            self.r[i] = int(round(rmin + (rmax - rmin) * depth ** c["size_curve"]))
            a["val"][i] = c["intensity"] * (c["far_intensity"]
                                            + (1 - c["far_intensity"]) * depth ** 1.3)
            f = (1 + c["speed_jitter"] * rnd.uniform(-1, 1)) \
                * (1 - c["parallax"] + 2 * c["parallax"] * depth)
            a["k"][i] = max(1, round(k0 * f))
            a["x0"][i], a["y0"][i] = rnd.random(), rnd.random()
            if straight:                              # across-the-motion position
                lanes = c["lanes"]
                lo, hi = (lanes if lanes and rnd.random() < c["lane_share"]
                          else (-0.02, 1.02))
                across = rnd.uniform(lo, hi)
                if self.dy:
                    a["x0"][i] = across
                else:
                    a["y0"][i] = across
            a["amp"][i] = rnd.uniform(swmin, swmax)
            a["sn"][i] = cycles(rnd.uniform(*c["sway_seconds"]), loop)
            a["sph"][i] = rnd.random()
            a["tn"][i] = cycles(rnd.uniform(*c["twinkle_seconds"]), loop)
            a["tph"][i] = rnd.random()
        self.a = a
        # sway runs perpendicular to the motion
        L = math.hypot(self.dx, self.dy)
        self.px, self.py = -self.dy / L, self.dx / L

    def positions(self, t):
        a, p = self.a, (t % self.loop) / self.loop
        if self.dy:
            y = ((a["y0"] + self.dy * a["k"] * p) % 1.0) * self.FH - self.m
        else:
            y = a["y0"] * H
        if self.dx:
            x = ((a["x0"] + self.dx * a["k"] * p) % 1.0) * self.FW - self.m
        else:
            x = a["x0"] * W
        s = a["amp"] * np.sin(2 * np.pi * (a["sn"] * p + a["sph"]))
        tw = 1 - self.c["twinkle_depth"] * (0.5 - 0.5 * np.sin(
            2 * np.pi * (a["tn"] * p + a["tph"])))
        return x + s * self.px, y + s * self.py, a["val"] * tw

    def draw(self, frame, t):
        xs, ys, vs = self.positions(t)
        for x, y, v, r in zip(xs.tolist(), ys.tolist(), vs.tolist(), self.r.tolist()):
            if v < 6:
                continue
            x0, y0 = int(x) - r, int(y) - r
            x1, y1 = x0 + 2 * r + 1, y0 + 2 * r + 1
            sx0, sy0 = max(0, -x0), max(0, -y0)
            x0c, y0c = max(0, x0), max(0, y0)
            x1c, y1c = min(W, x1), min(H, y1)
            if x1c <= x0c or y1c <= y0c:
                continue
            g = self.spr[r][sy0:sy0 + (y1c - y0c), sx0:sx0 + (x1c - x0c)] * v
            reg = frame[y0c:y1c, x0c:x1c].astype(np.int16)
            reg += (g[:, :, None] * self.tint[None, None, :]).astype(np.int16)
            frame[y0c:y1c, x0c:x1c] = np.clip(reg, 0, 255).astype(np.uint8)


# --------------------------------------------------------------- subscribe --
def subscribe_times(c, loop):
    """Start times of the like/subscribe group inside one loop.

    The gaps (including the one that wraps from the last appearance round to
    the first) add up to exactly one loop, so the rhythm carries on unbroken
    across copies of the loop.
    """
    if c.get("at_seconds"):
        return sorted(t % loop for t in c["at_seconds"])
    ev = c["every_seconds"]
    lo, hi = (ev, ev) if isinstance(ev, (int, float)) else ev
    n = max(1, round(loop / ((lo + hi) / 2)))
    rnd = random.Random(c["seed"])
    gaps = [loop / n] * n
    for _ in range(500):
        g = [rnd.uniform(lo, hi) for _ in range(n)]
        g = [x * loop / sum(g) for x in g]
        if all(lo - 1e-6 <= x <= hi + 1e-6 for x in g):
            gaps = g
            break
    times = [float(c["first_at"])]
    for g in gaps[:-1]:
        times.append(times[-1] + g)
    return [t % loop for t in times]


class Subscribe:
    """Slides in at each scheduled time of the loop, plays the clicks, slides
    out. A window that runs past the loop end wraps to the start."""

    def __init__(self, c, loop, move=50):
        self.c, self.loop, self.move = c, loop, move * PX_SCALE   # cursor travel, px at 1080p
        self.times = subscribe_times(c, loop)
        self.w = brand.SubscribeWidget(c["height_px"], c["label"], c["label_done"])
        self.x, self.y = corner_xy(c["corner"], self.w.W, self.w.h, c["margin_px"])
        sh = brand.drop_shadow(self.w.plate, radius=round(16 * PX_SCALE), spread=0.42, offset=(0, round(5 * PX_SCALE)))
        self.sh = to_layers(sh)
        self.sh_off = sh.info["pad"]

    def state(self, t):
        show = self.c["show_seconds"]
        for s in self.times:
            u = (t - s) % self.loop
            if u > show:
                continue
            IN = OUT = 0.6
            if u < IN:
                f = (u / IN) ** 0.6
                return f, (1 - f) * self.move, u
            if u > show - OUT:
                f = (show - u) / OUT
                return f, (1 - f) * self.move * 0.6, u
            return 1.0, 0.0, u
        return 0.0, 0.0, 0.0

    def draw(self, frame, t):
        o, dy, phase = self.state(t)
        if o <= 0.003:
            return
        y = int(self.y + dy)
        blit(frame, self.sh[0], self.sh[1], self.x - self.sh_off, y - self.sh_off, o)
        rgb, al = to_layers(self.w.render(phase))
        blit(frame, rgb, al, self.x, y, o)


# ------------------------------------------------------------------- scene --
class Scene:
    def __init__(self, image_path, cfg, bars=True):
        loop = cfg["loop_seconds"]
        base = Image.open(image_path).convert("RGB")
        if base.size != (W, H):
            base = base.resize((W, H), Image.LANCZOS)
        self.plates = Plates(base, cfg, loop)
        if bars and cfg["bars"]["enabled"] and cfg["bars"]["scrim"] > 0:
            add_scrim(self.plates, cfg)
        add_logo(self.plates, cfg)
        self.layers = []
        if cfg["lantern"]["enabled"]:
            self.layers.append(Lantern(cfg["lantern"], loop))
        self.layers += [Particles(p, loop) for p in cfg["particles"] if p["enabled"]]
        if cfg["subscribe"]["enabled"]:
            self.layers.append(Subscribe(cfg["subscribe"], loop))

    def frame(self, t):
        f = self.plates.at(t)
        for layer in self.layers:
            layer.draw(f, t)
        return f

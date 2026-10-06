import copy
import math

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

import depth
import effects_gpu
from config import H, PX_SCALE, W, cycles

PATHS = ("static", "push_pull", "pan_h", "pan_diag", "figure8", "arc", "drift")
LIGHTS = ("breathing", "god_rays", "halo", "glow", "spotlight", "sweep")
TAU = 2 * math.pi


def _rect_mask(xs, ys, rect, feather):
    x0, y0, x1, y1 = rect
    fx = torch.clamp(torch.minimum(xs - x0, x1 - xs) / max(feather, 1e-6) + 0.5, 0, 1)
    fy = torch.clamp(torch.minimum(ys - y0, y1 - ys) / max(feather, 1e-6) + 0.5, 0, 1)
    m = fx * fy
    return m * m * (3 - 2 * m)


def _fill(img, known, levels=9):
    x = (img * known[..., None]).permute(2, 0, 1)[None]
    m = known[None, None].clone()
    pyr = []
    for _ in range(levels):
        pyr.append((x, m))
        x, m = F.avg_pool2d(x, 2, ceil_mode=True), F.avg_pool2d(m, 2, ceil_mode=True)
    out = x / m.clamp_min(1e-6)
    for x, m in reversed(pyr):
        up = F.interpolate(out, size=x.shape[-2:], mode="bilinear", align_corners=False)
        own = x / m.clamp_min(1e-6)
        w = m.clamp(0, 1)
        out = own * w + up * (1 - w)
    return out[0].permute(1, 2, 0)


def _dilate(m, px):
    k = 2 * int(px) + 1
    return F.max_pool2d(m[None, None], k, 1, int(px))[0, 0] if px >= 1 else m


def _blur(m, px):
    k = 2 * int(px) + 1
    return F.avg_pool2d(F.pad(m[None, None], (int(px),) * 4, mode="replicate"), k, 1)[0, 0] if px >= 1 else m


def pick_device():
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def camera_at(c, p, loop):
    w = TAU * cycles(c["period"], loop) * p + c.get("phase", 0.0)
    ax, ay = c["pan"]
    path = c["path"]
    if path not in PATHS:
        raise ValueError(f"cinema.camera.path must be one of {PATHS}")
    ox = oy = 0.0
    if path == "pan_h":
        ox = ax * math.sin(w)
    elif path == "pan_diag":
        ox, oy = ax * math.sin(w), ay * math.sin(w)
    elif path == "figure8":
        ox, oy = ax * math.sin(w), ay * math.sin(2 * w)
    elif path == "arc":
        ox, oy = ax * math.cos(w), ay * math.sin(w)
    elif path == "drift":
        ox = ax * (0.62 * math.sin(w) + 0.28 * math.sin(2 * w + 1.3) + 0.10 * math.sin(3 * w + 2.1))
        oy = ay * (0.55 * math.sin(w + 0.9) + 0.30 * math.sin(2 * w + 2.4) + 0.15 * math.sin(3 * w + 0.4))
    if not c["zoom"]:
        return 1.0, ox, oy
    zw = TAU * cycles(c.get("zoom_period") or c["period"], loop) * p + c.get("zoom_phase", 0.0)
    return 1 + c["zoom"] * (0.5 - 0.5 * math.cos(zw)), ox, oy


def _src_extent(g, s, ox, oy, z, dd):
    se = 1 + (s - 1) * (1 + dd)
    return (g[0] - 2 * ox * (1 + dd)) * z * se, (g[1] - 2 * oy * (1 + dd)) * z * se


class CinemaScene(effects_gpu.GpuScene):

    def __init__(self, image_path, cfg, bars=True, device=None):
        self.cc = copy.deepcopy(cfg["cinema"])
        inner = copy.deepcopy(cfg)
        inner["light"]["enabled"] = False
        inner["logo"]["enabled"] = False
        inner["badge"]["enabled"] = False
        inner["bars"]["scrim"] = 0.0
        super().__init__(image_path, inner, bars=False, device=device or pick_device())
        self.loop = cfg["loop_seconds"]
        dev = self.dev
        self.base = self.plates[0].float()
        gy, gx = torch.meshgrid(torch.linspace(-1 + 1 / H, 1 - 1 / H, H, device=dev),
                                torch.linspace(-1 + 1 / W, 1 - 1 / W, W, device=dev), indexing="ij")
        self.gx, self.gy = gx, gy
        self.xs, self.ys = (gx + 1) / 2, (gy + 1) / 2
        self.X, self.Y = self.xs * (W / H), self.ys
        feather = self.cc["feather"]
        text_masks = [_rect_mask(self.xs, self.ys, r, feather) for r in self.cc["text_zones"]]
        self.text = torch.zeros((H, W), device=dev)
        for m in text_masks:
            self.text = torch.maximum(self.text, m)
        self.static = torch.zeros((H, W), device=dev)
        f = self.cc["static_feather"]
        for x0, y0, x1, y1 in self.cc["static_zones"]:
            grown = (x0 - f / 2, y0 - f / 2, x1 + f / 2, y1 + f / 2)
            self.static = torch.maximum(self.static, _rect_mask(self.xs, self.ys, grown, max(f, 0.002)))
        d = torch.from_numpy(np.load(depth.ensure(image_path))).to(dev)[None, None]
        d = F.interpolate(d, size=(H, W), mode="bilinear", align_corners=False)[0, 0]
        layered = bool(self.cc["text_layer"]["enabled"] and self.cc["text_zones"])
        self.text_depth = []
        for r, m in zip(self.cc["text_zones"], text_masks):
            sel = m > 0.5
            med = float(d[sel].median()) if sel.any() else self.cc["focus"]
            if not layered:
                d = d * (1 - m) + med * m
            self.text_depth.append((r, 2 * self.cc["parallax"] * (med - self.cc["focus"])))
        self.dd = 2 * self.cc["parallax"] * (d - self.cc["focus"])
        self.dd_range = (float(self.dd.min()), float(self.dd.max()))
        self.tl = self._prep_text_layer(self.cc["text_layer"]) if layered else None
        guard = self.tl["alpha"] if self.tl else self.text
        self.light_gate = (1 - (0.0 if self.tl else 0.85) * guard) * (1 - self.static)
        self.particle_gate = (1 - 0.75 * guard) * (1 - self.static)
        self.haze_guard = guard
        self.lights = [self._prep_light(l) for l in self.cc["lights"] if l.get("enabled", True)]
        self.haze = self._prep_haze(self.cc["haze"]) if self.cc["haze"]["enabled"] else None
        self.over_rgb, self.over_a = self._overlay(cfg, bars)
        self.fit = self._fit_text()

    def _prep_text_layer(self, c):
        rgb = self.base
        lum = rgb.mean(-1)
        sat = rgb.max(-1).values - rgb.min(-1).values
        zone = (self.text > 0.5).float()
        core = ((lum > (c.get("lum_core") or c["lum_min"])) & (sat < c["sat_max"])).float() * zone
        k = max(1, round(2 * PX_SCALE))
        core = _dilate(-_dilate(-core, k), k)
        near = _dilate(core, c.get("grow_px", 0)) if c.get("grow_px") else core
        letters = ((lum > c["lum_min"]) & (sat < c["sat_max"])).float() * zone * near
        letters = torch.maximum(letters, core)
        if not bool(letters.any()):
            raise SystemExit(f"cinema.text_layer: no lettering found in text_zones {self.cc['text_zones']} "
                             f"(pixels with brightness > lum_min {c['lum_min']} and colour spread < sat_max {c['sat_max']}); "
                             "fix text_zones in <dir>/video.json, lower lum_min / raise sat_max, or turn text_layer off")
        halo = _dilate(letters, c["halo_px"])
        shadow = halo * (lum < c.get("shadow_lum", 256)).float()
        mask = torch.maximum(letters, shadow)
        alpha = _blur(_dilate(mask, max(1, round(PX_SCALE))), c["feather_px"]).clamp(0, 1)
        hole = _dilate(mask, 3 * PX_SCALE)
        self.base_bg = _fill(rgb, 1 - hole) * hole[..., None] + rgb * (1 - hole[..., None])
        ys, xs = torch.nonzero(letters, as_tuple=True)
        cy, cx = float(ys.float().mean()) / H, float(xs.float().mean()) / W
        rgba = torch.cat([rgb, alpha[..., None] * 255], -1).permute(2, 0, 1)[None]
        return {"rgba": rgba, "alpha": alpha, "c": (cx, cy), "zoom": c["zoom"], "period": c["period"], "phase": c["phase"],
                "keep_above": c["keep_above"], "box": (float(xs.min()) / W, float(ys.min()) / H, float(xs.max()) / W, float(ys.max()) / H)}

    def _draw_text_layer(self, out, p):
        tl = self.tl
        s = 1 + tl["zoom"] * (0.5 - 0.5 * math.cos(TAU * self._cyc(tl["period"]) * p + tl["phase"]))
        cx, cy = 2 * tl["c"][0] - 1, 2 * tl["c"][1] - 1
        grid = torch.stack([cx + (self.gx - cx) / s, cy + (self.gy - cy) / s], -1)[None]
        t = F.grid_sample(tl["rgba"], grid, mode="bilinear", padding_mode="zeros", align_corners=False)[0].permute(1, 2, 0)
        a = t[..., 3:] / 255
        return out * (1 - a) + t[..., :3] * a

    @property
    def layers(self):
        return self.cpu.layers

    def _cyc(self, period):
        return cycles(period, self.loop)

    def camera(self, p):
        return camera_at(self.cam, p, self.loop)

    def _text_fits(self, k, margin):
        c0 = self.cc["camera"]
        cam = dict(c0, pan=[v * k for v in c0["pan"]], zoom=c0["zoom"] * k)
        z = 1 + self.cc["overscan"] * k
        lim = 1 - 2 * margin
        for i in range(720):
            s, ox, oy = camera_at(cam, i / 720, self.loop)
            for (x0, y0, x1, y1), dd in self.text_depth:
                for g in ((2 * x0 - 1, 2 * y0 - 1), (2 * x1 - 1, 2 * y1 - 1)):
                    ex, ey = _src_extent(g, s, ox, oy, z, dd)
                    if abs(ex) > lim or abs(ey) > lim:
                        return False
        return True

    def _fit_text_layer(self, margin):
        tl = self.tl
        cx, cy = tl["c"]
        x0, y0, x1, y1 = tl["box"]
        want = tl["zoom"]
        room = [(x0 - margin, cx - x0), (1 - margin - x1, x1 - cx), (y0 - margin, cy - y0),
                (min(1 - margin, tl["keep_above"]) - y1, y1 - cy)]
        zoom = want
        for free, arm in room:
            if arm > 1e-6:
                zoom = min(zoom, max(0.0, free / arm))
        if zoom < want:
            tl["zoom"] = zoom
            print(f"⚠ cinema.text_layer: zoom limited to {zoom:.3f} (of {want}) so the lettering box stays {margin:.0%} "
                  f"inside the frame and above y={tl['keep_above']}", flush=True)
        return zoom / want if want > 0 else 1.0

    def _fit_text(self, margin=0.01):
        k = 1.0
        if self.tl:
            self.cam = dict(self.cc["camera"])
            return self._fit_text_layer(margin)
        if self.text_depth and not self._text_fits(1.0, margin):
            lo, hi = 0.0, 1.0
            for _ in range(14):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if self._text_fits(mid, margin) else (lo, mid)
            k = lo
            print(f"⚠ cinema: camera + overscan scaled to {k:.2f}× so every text_zone stays {margin:.0%} inside the frame",
                  flush=True)
        c0 = self.cc["camera"]
        self.cam = dict(c0, pan=[v * k for v in c0["pan"]], zoom=c0["zoom"] * k)
        self.cc["overscan"] *= k
        return k

    def _prep_light(self, l):
        t = l["type"]
        if t not in LIGHTS:
            raise ValueError(f"cinema.lights type must be one of {LIGHTS}")
        L = dict(l)
        L["rgb"] = torch.tensor(l.get("color", [255, 226, 170]), device=self.dev, dtype=torch.float32) / 255
        if "color2" in l:
            L["rgb2"] = torch.tensor(l["color2"], device=self.dev, dtype=torch.float32) / 255
        if t in ("god_rays", "halo", "glow"):
            cx, cy = l["center"]
            dx, dy = self.X - cx * W / H, self.Y - cy
            r = torch.hypot(dx, dy)
            if t == "god_rays":
                th = torch.atan2(dy, dx)
                a0 = math.radians(l["angle"])
                diff = torch.atan2(torch.sin(th - a0), torch.cos(th - a0))
                cone = torch.exp(-0.5 * (diff / math.radians(l["spread"] / 2)) ** 2)
                fall = torch.clamp(1 - r / l["length"], 0, 1) ** 1.4 * torch.clamp(r / 0.04, 0, 1)
                L["mask"], L["theta"] = cone * fall * self.light_gate, th
                rnd = np.random.default_rng(l.get("seed", 3))
                L["waves"] = [(float(rnd.integers(9, 40)), float(rnd.uniform(0, TAU)), float(rnd.choice([-1, 1]) * (i + 1)))
                              for i in range(l.get("rays", 4))]
            else:
                L["mask"] = torch.exp(-2.0 * (r / l["radius"]) ** 2) * self.light_gate
        if t == "sweep":
            ang = math.radians(l.get("angle", 20))
            L["q"] = self.X * math.cos(ang) + self.Y * math.sin(ang)
            L["q_range"] = (float(L["q"].min()), float(L["q"].max()))
        return L

    def _prep_haze(self, h):
        g = torch.Generator(device="cpu").manual_seed(h.get("seed", 11))
        n = torch.rand((1, 1, 135, 240), generator=g)
        for k in (5, 9):
            n = F.avg_pool2d(F.pad(n, (k // 2,) * 4, mode="circular"), k, 1)
        n = (n - n.min()) / (n.max() - n.min() + 1e-6)
        n = F.interpolate(n, size=(H, W), mode="bicubic", align_corners=False)[0, 0].clamp(0, 1).to(self.dev)
        low = torch.clamp((self.ys - h.get("top", 0.35)) / 0.4, 0, 1) if h.get("low", True) else 1.0
        col = torch.tensor(h.get("color", [200, 190, 175]), device=self.dev, dtype=torch.float32)
        return n, (1 - 0.7 * self.haze_guard) * (1 - self.static) * low, col

    def _overlay(self, cfg, bars):
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        b = cfg["bars"]
        if bars and b["enabled"] and b["scrim"] > 0:
            from bars import BarStrip
            img, (x, y) = BarStrip(b).scrim()
            canvas.alpha_composite(img.convert("RGBA"), (int(x), int(y)))
        from effects import stamp
        for lc in (cfg["logo"], cfg["badge"]):
            if not lc["enabled"]:
                continue
            img, x, y = stamp(lc)
            if lc["opacity"] < 1:
                img.putalpha(img.getchannel("A").point(lambda v, o=lc["opacity"]: int(v * o)))
            canvas.alpha_composite(img, (x, y))
        a = np.asarray(canvas, np.float32) / 255
        return torch.from_numpy(a[..., :3] * 255).to(self.dev), torch.from_numpy(a[..., 3:]).to(self.dev)

    def _light_alpha(self, L, p):
        t = L["type"]
        breath = 1 + L.get("amp", 0.25) * math.sin(TAU * self._cyc(L.get("period", 11)) * p + L.get("phase", 0.0))
        s = L["strength"] * breath
        if t == "god_rays":
            drift = TAU * self._cyc(L.get("drift_period", 60)) * p
            st = sum(0.5 + 0.5 * torch.cos(n * L["theta"] + ph + sg * drift) for n, ph, sg in L["waves"])
            return L["mask"] * (st / len(L["waves"])) ** 1.6 * s
        if t in ("halo", "glow"):
            return L["mask"] * s
        if t == "spotlight":
            wv = TAU * self._cyc(L.get("path_period", 40)) * p
            cx = L["center"][0] + L["path"][0] * math.sin(wv)
            cy = L["center"][1] + L["path"][1] * math.sin(2 * wv)
            r = torch.hypot(self.X - cx * W / H, self.Y - cy)
            return torch.exp(-2.0 * (r / L["radius"]) ** 2) * self.light_gate * s
        u = (p * self._cyc(L["period"])) % 1.0
        duty = L.get("duty", 0.35)
        if u > duty:
            return None
        q0, q1 = L["q_range"]
        c = q0 - L["width"] + (q1 - q0 + 2 * L["width"]) * (u / duty)
        return torch.exp(-((L["q"] - c) / L["width"]) ** 2) * self.light_gate * L["strength"]

    def _add_lights(self, img, p):
        for L in self.lights:
            if L["type"] == "breathing":
                img *= 1 + L["amp"] * math.sin(TAU * self._cyc(L["period"]) * p) * (1 - self.static)[..., None]
                continue
            a = self._light_alpha(L, p)
            if a is None:
                continue
            rgb = L["rgb"]
            if "rgb2" in L:
                mix = 0.5 + 0.5 * math.sin(TAU * self._cyc(L.get("hue_period", 23)) * p)
                rgb = rgb * (1 - mix) + L["rgb2"] * mix
            img += (255 - img) * (a[..., None] * rgb)
        return img.clamp_(0, 255)

    def _warp(self, img, p):
        s, ox, oy = self.camera(p)
        z = 1 + self.cc["overscan"]
        se = 1 + (s - 1) * (1 + self.dd)
        grid = torch.stack([self.gx / (z * se) + 2 * ox * (1 + self.dd),
                            self.gy / (z * se) + 2 * oy * (1 + self.dd)], -1)[None]
        out = F.grid_sample(img.permute(2, 0, 1)[None], grid, mode="bilinear", padding_mode="border",
                            align_corners=False)[0].permute(1, 2, 0)
        st = self.static[..., None]
        return out * (1 - st) + self.base * st

    def _add_haze(self, out, p):
        n, gate, col = self.haze
        hz = self.cc["haze"]
        shift = int(round(p * max(1, int(round(hz.get("drift_cycles", 1)))) * W)) % W
        a = torch.roll(n, shifts=shift, dims=1) * gate * hz["opacity"]
        return out + (col - out) * a[..., None]

    def _add_particles(self, out, t):
        pb = torch.zeros((H, W, 3), device=self.dev)
        for layer, sprites in self.particles:
            self._splat(pb, layer, sprites, t)
        return out + pb * self.particle_gate[..., None]

    @torch.inference_mode()
    def frame_tensor(self, t):
        p = (t % self.loop) / self.loop
        img = (self.base_bg if self.tl else self.base).clone()
        self._draw_lantern(img, t)
        out = self._warp(self._add_lights(img, p), p)
        if self.tl:
            st = self.static[..., None]
            out = self._draw_text_layer(out, p) * (1 - st) + self.base * st
        if self.haze is not None:
            out = self._add_haze(out, p)
        if self.particles:
            out = self._add_particles(out, t)
        acc = out.clamp_(0, 255)
        acc = (acc * (1 - self.over_a) + self.over_rgb * self.over_a).contiguous()
        self._draw_subscribe(acc, t)
        return acc.clamp_(0, 255).to(torch.uint8)

    def edge_smear_px(self):
        z = 1 + self.cc["overscan"]
        worst = 0.0
        for i in range(720):
            s, ox, oy = self.camera(i / 720)
            for dd in self.dd_range:
                se = 1 + (s - 1) * (1 + dd)
                sx = 1 / (z * se) + 2 * abs(ox) * (1 + dd)
                sy = 1 / (z * se) + 2 * abs(oy) * (1 + dd)
                worst = max(worst, (sx - 1) * W / 2, (sy - 1) * H / 2)
        return max(0.0, worst)


def _gray_small(fr):
    x = torch.from_numpy(np.ascontiguousarray(fr)).float().mean(-1)[None, None]
    return F.interpolate(x, size=(540, 960), mode="area")[0, 0].numpy()


def _shift(a, b):
    A, B = np.fft.fft2(a - a.mean()), np.fft.fft2(b - b.mean())
    R = A * np.conj(B)
    r = np.fft.ifft2(R / (np.abs(R) + 1e-9)).real
    y, x = np.unravel_index(np.argmax(r), r.shape)
    y = y - a.shape[0] if y > a.shape[0] // 2 else y
    x = x - a.shape[1] if x > a.shape[1] // 2 else x
    return int(x), int(y)


def _corr(a, b, w=None):
    if w is None:
        return float(np.corrcoef(a.ravel(), b.ravel())[0, 1])
    w = w.ravel() / max(1e-9, float(w.sum()))
    a, b = a.ravel(), b.ravel()
    da, db = a - (w * a).sum(), b - (w * b).sum()
    return float((w * da * db).sum() / np.sqrt((w * da * da).sum() * (w * db * db).sum() + 1e-12))


def _rigid_match(ref, g, rect, weight=None):
    x0, y0, x1, y1 = rect
    crop = (slice(int(y0 * 540), int(y1 * 540)), slice(int(x0 * 960), int(x1 * 960)))
    a = ref[crop]
    w = None if weight is None else weight[crop]
    cx, cy = (x0 + x1) / 2 * 960, (y0 + y1) / 2 * 540
    best = (0, 0, -1.0)
    for sc in np.linspace(0.93, 1.07, 29):
        t = torch.from_numpy(g)[None, None].float()
        th = torch.tensor([[[1 / sc, 0, (cx / 480 - 1) * (1 - 1 / sc)], [0, 1 / sc, (cy / 270 - 1) * (1 - 1 / sc)]]],
                          dtype=torch.float32)
        gs = F.grid_sample(t, F.affine_grid(th, t.shape, align_corners=False), align_corners=False)[0, 0].numpy()
        b = gs[crop]
        dx, dy = _shift(b, a) if w is None else _shift(b * w, a * w)
        bb = np.roll(np.roll(b, -dy, 0), -dx, 1)
        m = (slice(14, -14), slice(14, -14))
        c = _corr(a[m], bb[m], None if w is None else w[m])
        if c > best[2]:
            best = (abs(dx) * 2, abs(dy) * 2, c)
    return best


def qa(image_path, cfg, samples=24):
    sc = CinemaScene(image_path, cfg)
    sc.subscribe = None
    loop, fps = cfg["loop_seconds"], cfg["fps"]
    f0 = sc.frame(0.0)
    ref = _gray_small(f0)
    join = float(np.abs(_gray_small(sc.frame(loop - 1 / fps)) - ref).mean())
    steps = [float(np.abs(_gray_small(sc.frame(t + 1 / fps)) - _gray_small(sc.frame(t))).mean())
             for t in np.linspace(5, loop - 5, 8)]
    seam = join / max(1e-6, float(np.median(steps)))
    if sc.tl:
        pad = 0.035
        x0, y0, x1, y1 = sc.tl["box"]
        rects = [(max(0.0, x0 - pad), max(0.0, y0 - pad), min(1.0, x1 + pad), min(1.0, y1 + pad))]
        weight = F.interpolate(sc.tl["alpha"].float().cpu()[None, None], size=(540, 960), mode="area")[0, 0].numpy()
    else:
        rects, weight = [r for r, _ in sc.text_depth], None
    text, static = [], []
    for t in np.linspace(3, min(loop, 120), samples):
        g = _gray_small(sc.frame(float(t)))
        for rect in rects:
            text.append(_rigid_match(ref, g, rect, weight))
        for (x0, y0, x1, y1) in sc.cc["static_zones"]:
            ys, xs = slice(int(y0 * 540) + 2, int(y1 * 540) - 2), slice(int(x0 * 960) + 2, int(x1 * 960) - 2)
            static.append(float(np.abs(ref[ys, xs] - g[ys, xs]).mean()))
    luma = [float(_gray_small(sc.frame(i / fps)).mean()) for i in range(fps * 6)]
    step = float(np.abs(np.diff(luma)).max())
    rep = {
        "seam_step_ratio": round(seam, 2),
        "text_move_px_1080p": max((max(a, b) for a, b, _ in text), default=0),
        "text_shape_corr_min": round(min((r for _, _, r in text), default=1.0), 3),
        "static_zone_diff": max(static, default=0.0),
        "edge_smear_px": round(sc.edge_smear_px(), 1),
        "camera_scale_for_text": round(sc.fit, 2),
        "luma_step_per_frame": round(step, 2),
    }
    checks = {
        "seam_step_ratio": rep["seam_step_ratio"] <= 2.5,
        "text_shape_corr_min": rep["text_shape_corr_min"] >= 0.95,
        "static_zone_diff": rep["static_zone_diff"] <= 2,
        "edge_smear_px": rep["edge_smear_px"] <= 2,
        "camera_scale_for_text": rep["camera_scale_for_text"] >= 0.8,
        "luma_step_per_frame": rep["luma_step_per_frame"] <= 3,
    }
    rep["pass"] = all(checks.values())
    rep["failed"] = [k for k, ok in checks.items() if not ok]
    return rep

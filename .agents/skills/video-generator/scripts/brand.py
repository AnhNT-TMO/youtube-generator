import math
import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
SERIF = os.path.join(FONTS, "Lora-Variable.ttf")
SANS_B = os.path.join(FONTS, "Poppins-Bold.ttf")

GOLD = (233, 189, 112)
GOLD_HI = (255, 232, 182)
CREAM = (250, 242, 228)
INK = (26, 17, 9)


def _font(path, size):
    return ImageFont.truetype(path, size)


def tracked_text(d, xy, text, font, fill, tracking=0, anchor_center=True):
    widths = [d.textlength(c, font=font) for c in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x = xy[0] - total / 2 if anchor_center else xy[0]
    for c, w in zip(text, widths):
        d.text((x, xy[1]), c, font=font, fill=fill, anchor="lm")
        x += w + tracking
    return total


def flame(size, warm=GOLD_HI, core=(255, 251, 236), lean=0.0):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def body(scale, colour, sway):
        pts_r, pts_l = [], []
        for i in range(61):
            s = i / 60.0
            w = (math.sin(math.pi * s) ** 0.85) * (0.30 + 0.70 * s) * 0.5
            w *= size * 0.46 * scale
            y = size * (0.10 + 0.80 * s)
            cx = size * 0.5 + math.sin(s * 2.4) * size * 0.035 * sway
            pts_r.append((cx + w, y))
            pts_l.append((cx - w, y))
        d.polygon(pts_r + pts_l[::-1], fill=colour)

    body(1.0, warm + (255,), lean + 1.0)
    body(0.50, core + (235,), lean + 0.6)
    return img.filter(ImageFilter.GaussianBlur(size * 0.012))


def badge(size, title, sub, glow=0.5):
    S = size * 3
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c, R = S / 2, S / 2 - S * 0.012

    d.ellipse([c - R, c - R, c + R, c + R], fill=INK + (150,))
    d.ellipse([c - R, c - R, c + R, c + R], outline=GOLD + (235,), width=int(S * 0.010))
    r2 = R * 0.915
    d.ellipse([c - r2, c - r2, c + r2, c + r2], outline=GOLD + (120,), width=int(S * 0.004))

    fl = flame(int(S * 0.29))
    fx, fy = int(c - fl.width / 2), int(S * 0.150)

    halo = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    halo.alpha_composite(fl, (fx, fy))
    halo = halo.filter(ImageFilter.GaussianBlur(S * 0.035))
    a = halo.split()[3].point(lambda p: int(p * (0.30 + 0.55 * glow)))
    warm = Image.new("RGBA", (S, S), GOLD_HI + (0,))
    warm.putalpha(a)
    img.alpha_composite(warm)
    img.alpha_composite(fl, (fx, fy))

    f1 = _font(SERIF, int(S * 0.105))
    f2 = _font(SERIF, int(S * 0.062))
    tracked_text(d, (c, S * 0.585), title, f1, CREAM + (255,), tracking=S * 0.012)
    d.line([(c - S * 0.16, S * 0.655), (c + S * 0.16, S * 0.655)],
           fill=GOLD + (180,), width=max(1, int(S * 0.004)))
    tracked_text(d, (c, S * 0.715), sub, f2, GOLD + (255,), tracking=S * 0.042)

    return img.resize((size, size), Image.LANCZOS)


def _bell(size, colour):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size
    d.pieslice([s * .22, s * .16, s * .78, s * .74], 180, 360, fill=colour)
    d.rectangle([s * .22, s * .45, s * .78, s * .66], fill=colour)
    d.rounded_rectangle([s * .14, s * .64, s * .86, s * .74], radius=s * .05, fill=colour)
    d.ellipse([s * .42, s * .74, s * .58, s * .88], fill=colour)
    d.ellipse([s * .44, s * .08, s * .56, s * .20], fill=colour)
    return img


def _thumb(size, colour):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size
    d.rounded_rectangle([s * .16, s * .46, s * .34, s * .84], radius=s * .05, fill=colour)
    d.polygon([(s * .40, s * .84), (s * .40, s * .46), (s * .58, s * .12),
               (s * .68, s * .16), (s * .62, s * .40), (s * .86, s * .40)], fill=colour)
    d.rounded_rectangle([s * .40, s * .40, s * .86, s * .84], radius=s * .09, fill=colour)
    return img


def drop_shadow(sprite, radius=16, spread=0.45, offset=(0, 5)):
    pad = int(radius * 3) + max(abs(offset[0]), abs(offset[1]))
    big = Image.new("RGBA", (sprite.width + pad * 2, sprite.height + pad * 2),
                    (0, 0, 0, 0))
    big.alpha_composite(sprite, (pad, pad))

    a = big.split()[3].filter(ImageFilter.GaussianBlur(radius))
    a = a.point(lambda p: int(p * spread))
    sh = Image.new("RGBA", big.size, (0, 0, 0, 0))
    sh.putalpha(a)

    out = Image.new("RGBA", big.size, (0, 0, 0, 0))
    out.alpha_composite(sh, (offset[0], offset[1]))
    out.alpha_composite(big)
    out.info["pad"] = pad
    return out


def arrow_cursor(height=46):
    S = 4
    h = height * S
    w = int(h * 0.579)
    pts = [(0.000, 0.000), (0.000, 0.842), (0.210, 0.658), (0.368, 1.000),
           (0.526, 0.921), (0.368, 0.579), (0.579, 0.579)]
    pts = [(x * h, y * h) for x, y in pts]

    m = int(h * 0.10)
    img = Image.new("RGBA", (w + m * 2, h + m * 2), (0, 0, 0, 0))
    p = [(x + m, y + m) for x, y in pts]

    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).polygon([(x + h * .035, y + h * .045) for x, y in p],
                               fill=(0, 0, 0, 150))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(h * 0.045)))

    d = ImageDraw.Draw(img)
    d.polygon(p, fill=(252, 250, 246, 255))
    d.line(p + [p[0]], fill=(24, 20, 16, 255), width=int(h * 0.050),
           joint="curve")

    out = img.resize((img.width // S, img.height // S), Image.LANCZOS)
    out.info["hotspot"] = (m // S, m // S)
    return out


def _ripple(size, strength):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    if strength <= 0:
        return img
    d = ImageDraw.Draw(img)
    r = size * 0.5 * strength
    a = int(190 * (1 - strength) ** 1.3)
    d.ellipse([size / 2 - r, size / 2 - r, size / 2 + r, size / 2 + r],
              outline=CREAM + (a,), width=max(2, int(size * 0.05)))
    return img


class SubscribeWidget:

    ACCENT = (176, 34, 38)
    DONE = (118, 106, 94)
    LIKED = (206, 150, 52)

    T_LIKE, T_SUB, T_BELL = 1.55, 3.05, 4.55
    MOVE = 0.62

    def __init__(self, height=80, label="SUBSCRIBE", label_done="SUBSCRIBED"):
        self.h = h = height
        self.f = _font(SANS_B, int(h * 0.335))
        pad, gap, icon = int(h * 0.30), int(h * 0.20), int(h * 0.62)
        self.icon = icon

        tmp = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
        w1 = sum(tmp.textlength(c, font=self.f) for c in label) + h * .045 * (len(label) - 1)
        w2 = sum(tmp.textlength(c, font=self.f) for c in label_done) + h * .045 * (len(label_done) - 1)
        self.pill_w = int(max(w1, w2) + h * 0.95)
        self.W = pad + icon + gap + self.pill_w + gap + icon + pad

        plate = Image.new("RGBA", (self.W, h), (0, 0, 0, 0))
        pd = ImageDraw.Draw(plate)
        pd.rounded_rectangle([0, 0, self.W - 1, h - 1], radius=h / 2, fill=CREAM + (242,))
        pd.rounded_rectangle([0, 0, self.W - 1, h - 1], radius=h / 2,
                             outline=GOLD + (220,), width=int(h * 0.035))
        self.plate = plate

        self.thumb_xy = (pad, int((h - icon) / 2))
        self.pill_x = pad + icon + gap
        self.bell_xy = (self.pill_x + self.pill_w + gap, int((h - icon) / 2))

        self.thumb = {False: _thumb(icon, INK + (235,)),
                      True: _thumb(icon, self.LIKED + (255,))}
        self.bell = {}
        for act in (False, True):
            col = (self.LIKED if act else INK) + (255 if act else 235,)
            b = _bell(icon, col)
            self.bell[act] = [b.rotate(ang, resample=Image.BICUBIC, expand=False)
                              for ang in (-14, -9, -4, 0, 4, 9, 14)]

        self.pill = {}
        for done in (False, True):
            p = Image.new("RGBA", (self.pill_w, int(h * 0.68)), (0, 0, 0, 0))
            dd = ImageDraw.Draw(p)
            dd.rounded_rectangle([0, 0, self.pill_w - 1, p.height - 1],
                                 radius=p.height / 2,
                                 fill=(self.DONE if done else self.ACCENT) + (255,))
            tracked_text(dd, (self.pill_w / 2, p.height / 2),
                         label_done if done else label, self.f,
                         CREAM + (235 if done else 255,), tracking=h * 0.045)
            self.pill[done] = p

        self.cursor = arrow_cursor(int(h * 0.62))
        self.hot = self.cursor.info.get("hotspot", (0, 0))
        self.margin = int(h * 0.55)
        self.size = (self.W + self.margin, h + self.margin)

    @staticmethod
    def _ease(u):
        u = max(0.0, min(1.0, u))
        return u * u * (3 - 2 * u)

    def _targets(self):
        i = self.icon
        return [(self.thumb_xy[0] + i * 0.5, self.thumb_xy[1] + i * 0.55),
                (self.pill_x + self.pill_w * 0.5, self.h * 0.5),
                (self.bell_xy[0] + i * 0.5, self.bell_xy[1] + i * 0.55)]

    def _cursor_pos(self, phase):
        tg = self._targets()
        rest = (self.W * 0.98, self.h * 1.45)
        keys = [(0.0, rest), (self.T_LIKE - self.MOVE, rest)]
        for k, t in zip((self.T_LIKE, self.T_SUB, self.T_BELL), tg):
            keys.append((k, t))
            keys.append((k + 0.55, t))
        keys.append((self.T_BELL + 1.5, rest))
        for (t0, p0), (t1, p1) in zip(keys, keys[1:]):
            if phase <= t1:
                u = self._ease((phase - t0) / max(1e-6, t1 - t0)) if phase > t0 else 0.0
                return (p0[0] + (p1[0] - p0[0]) * u, p0[1] + (p1[1] - p0[1]) * u)
        return keys[-1][1]

    def _press(self, phase, at):
        d = phase - at
        if -0.16 < d < 0.24:
            return math.cos(d / 0.20 * math.pi / 2) ** 2
        return 0.0

    def render(self, phase):
        img = Image.new("RGBA", self.size, (0, 0, 0, 0))
        img.alpha_composite(self.plate, (0, 0))

        liked = phase >= self.T_LIKE
        subbed = phase >= self.T_SUB
        belled = phase >= self.T_BELL

        p = self._press(phase, self.T_LIKE)
        th = self.thumb[liked]
        if p > 0.01:
            s = max(2, int(self.icon * (1 - 0.16 * p)))
            th = th.resize((s, s), Image.LANCZOS)
        img.alpha_composite(th, (self.thumb_xy[0] + (self.icon - th.width) // 2,
                                 self.thumb_xy[1] + (self.icon - th.height) // 2))

        p = self._press(phase, self.T_SUB)
        pill = self.pill[subbed]
        if p > 0.01:
            pill = pill.resize((max(2, int(pill.width * (1 - 0.035 * p))),
                                max(2, int(pill.height * (1 - 0.10 * p)))), Image.LANCZOS)
        img.alpha_composite(pill, (self.pill_x + (self.pill_w - pill.width) // 2,
                                   int((self.h - pill.height) / 2)))

        ring = 0
        if belled and phase < self.T_BELL + 0.9:
            ring = int(round(3 * math.sin((phase - self.T_BELL) * 22)
                             * math.exp(-(phase - self.T_BELL) * 2.4)))
        bl = self.bell[belled][3 + max(-3, min(3, ring))]
        img.alpha_composite(bl, self.bell_xy)

        for at, (cx, cy) in zip((self.T_LIKE, self.T_SUB, self.T_BELL), self._targets()):
            d = phase - at
            if 0 <= d < 0.45:
                s = int(self.icon * 2.2)
                rp = _ripple(s, d / 0.45)
                img.alpha_composite(rp, (int(cx - s / 2), int(cy - s / 2)))

        cx, cy = self._cursor_pos(phase)
        press = max(self._press(phase, self.T_LIKE), self._press(phase, self.T_SUB),
                    self._press(phase, self.T_BELL))
        cur, hx, hy = self.cursor, self.hot[0], self.hot[1]
        if press > 0.01:
            k = 1 - 0.10 * press
            cur = cur.resize((max(2, int(cur.width * k)),
                              max(2, int(cur.height * k))), Image.LANCZOS)
            hx, hy = hx * k, hy * k
        img.alpha_composite(cur, (int(cx - hx), int(cy - hy)))
        return img

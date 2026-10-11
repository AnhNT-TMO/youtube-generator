import json, math, os, shutil, sys
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../video-montage/fonts/CormorantGaramond.ttf")
FEAT = ["lnum", "kern"]
spec = json.load(open(sys.argv[1])); out = sys.argv[2]
os.makedirs(out, exist_ok=True)
K = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
W, H = round(1080 * K), round(1920 * K)
FPS = 30


def font(size, weight=None, path=None):
    f = ImageFont.truetype(path or FONT, size)
    if weight: f.set_variation_by_name(weight)
    return f


def line_width(d, text, f, tracking):
    widths = [d.textlength(c, font=f, features=FEAT) for c in text]
    return widths, sum(widths) + tracking * f.size * (len(text) - 1)


def draw_text(d, text, f, cx, y, fill, tracking=0.0, stroke=0, stroke_fill=None):
    if not tracking:
        d.text((cx, y), text, font=f, fill=fill, anchor="ms", features=FEAT, stroke_width=stroke, stroke_fill=stroke_fill or fill); return
    widths, total = line_width(d, text, f, tracking)
    x = cx - total / 2
    for c, w in zip(text, widths):
        d.text((x, y), c, font=f, fill=fill, anchor="ls", features=FEAT, stroke_width=stroke, stroke_fill=stroke_fill or fill); x += w + tracking * f.size


def gradient(top, bottom, y0, y1):
    g = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(g)
    for y in range(H):
        k = min(1.0, max(0.0, (y - y0) / max(1, y1 - y0)))
        d.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * k) for a, b in zip(top, bottom)) + (255,))
    return g


def render_line(ln):
    layer = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(layer)
    y = ln["y"] * H; cx = W * ln.get("x", 0.5); tr = ln.get("tracking", 0)
    color = tuple(ln.get("color", [255, 244, 222])) + (255,)
    if ln.get("star"):
        r = ln["star"] * K; c = tuple(ln.get("color", [255, 222, 160])) + (255,)
        d.polygon([(cx, y - r), (cx + r * 0.16, y - r * 0.16), (cx + r * 0.62, y), (cx + r * 0.16, y + r * 0.16), (cx, y + r * 0.7), (cx - r * 0.16, y + r * 0.16), (cx - r * 0.62, y), (cx - r * 0.16, y - r * 0.16)], fill=c)
        half = ln.get("line", 0) * K / 2
        if half:
            for sgn in (-1, 1):
                for i in range(int(half - r * 0.8)):
                    a = int(255 * (1 - i / (half - r * 0.8)))
                    x = cx + sgn * (r * 0.8 + i)
                    d.line([(x, y - K), (x, y + K)], fill=c[:3] + (a,))
        return layer, True
    if ln.get("image"):
        im = Image.open(ln["image"]).convert("RGBA")
        if ln.get("bell"):
            bl = ln["bell"]
            bell = Image.open(bl["image"]).convert("RGBA").rotate(ln.get("angle", 0.0), resample=Image.BICUBIC, center=tuple(bl["pivot"]))
            im = Image.alpha_composite(im, bell)
        im = im.crop(Image.open(ln["image"]).getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox())
        im = im.resize((round(ln["width"] * K), round(im.height * ln["width"] * K / im.width)), Image.LANCZOS)
        layer.paste(im, (round(cx - im.width / 2), round(y - im.height / 2)), im)
        return layer, False
    f = font(round(ln["size"] * K), ln.get("weight"), ln.get("font"))
    if ln.get("rotate"):
        sub = dict(ln); sub.pop("rotate")
        layer, glow = render_line(sub)
        return layer.rotate(ln["rotate"], resample=Image.BICUBIC, center=(cx, y)), glow
    if ln.get("pill"):
        _, tw = line_width(d, ln["text"], f, tr)
        asc = f.getmetrics()[0] * 0.72
        px, py = ln.get("pad", [0.55, 0.42])
        box = [cx - tw / 2 - px * f.size, y - asc - py * f.size, cx + tw / 2 + px * f.size, y + py * f.size * 0.75]
        shadow = Image.new("RGBA", (W, H)); ImageDraw.Draw(shadow).rounded_rectangle([box[0], box[1] + 8, box[2], box[3] + 8], radius=(box[3] - box[1]) / 2, fill=(0, 0, 0, 150))
        layer = Image.alpha_composite(layer, shadow.filter(ImageFilter.GaussianBlur(10)))
        d = ImageDraw.Draw(layer)
        d.rounded_rectangle(box, radius=(box[3] - box[1]) / 2, fill=tuple(ln["pill"]) + (255,))
        draw_text(d, ln["text"], f, cx, y, color, tr)
        return layer, False
    if ln.get("fill") == "gold":
        mask = Image.new("L", (W, H)); draw_text(ImageDraw.Draw(mask), ln["text"], f, cx, y, 255, tr)
        top = y - f.getmetrics()[0] * 0.75
        g = gradient((255, 246, 214), (226, 150, 58), top, y)
        rim = Image.new("L", (W, H)); draw_text(ImageDraw.Draw(rim), ln["text"], f, cx, y, 255, tr, stroke=round(ln.get("stroke", 3) * K), stroke_fill=255)
        layer.paste((92, 48, 12, 255), (0, 0), rim)
        layer.paste(g, (0, 0), mask)
        return layer, True
    rim = tuple(ln["rim"]) + (255,) if ln.get("rim") else None
    draw_text(d, ln["text"], f, cx, y, color, tr, round(ln.get("stroke", 0) * K), rim)
    return layer, True


def scrim(y0, y1, opacity):
    a = Image.new("L", (1, H)); px = a.load()
    mid = (y0 + y1) / 2 * H; half = (y1 - y0) / 2 * H
    for y in range(H):
        px[0, y] = int(255 * opacity * min(1.0, max(0.0, 1 - abs(y - mid) / half) * 1.6))
    s = Image.new("RGBA", (W, H), (8, 12, 28, 0)); s.putalpha(a.resize((W, H))); return s


def glow_of(img):
    g = Image.new("RGBA", (W, H), (8, 12, 28, 0))
    g.putalpha(img.getchannel("A").filter(ImageFilter.GaussianBlur(spec["glow_px"] * K)).point(lambda a: min(255, int(a * spec["glow_opacity"]))))
    return g


def ink_profile(alpha, bottom):
    a = np.asarray(alpha) > 40
    rows = np.arange(a.shape[0])[:, None]
    if bottom: return np.where(a, rows, -1).max(0)
    return np.where(a, rows, a.shape[0]).min(0)


def clear_below(ln, above, gap):
    if not above.any(): return ln, render_line(ln)
    bottom = ink_profile(above, True)
    reach = round(gap)
    padded = np.pad(bottom, reach, constant_values=-1)
    bottom = np.max([padded[i:i + len(bottom)] for i in range(2 * reach + 1)], 0)
    layer, glow = render_line(ln)
    top = ink_profile(layer.getchannel("A"), False)
    hit = (bottom >= 0) & (top < H)
    dy = int(max(0, (bottom[hit] + gap - top[hit]).max())) if hit.any() else 0
    if not dy: return ln, (layer, glow)
    moved = dict(ln, y=ln["y"] + dy / H)
    print(f"  '{ln['text']}' chạm dòng trên → xuống {dy}px (y {ln['y']:.4f} → {moved['y']:.4f})")
    return moved, render_line(moved)


def build(b):
    text = Image.new("RGBA", (W, H)); glowing = Image.new("RGBA", (W, H)); masks = []
    above = Image.new("L", (W, H)); gap = b.get("line_gap", spec.get("line_gap", 12)) * K
    for i, ln in enumerate(b["lines"]):
        if ln.get("text") and not ln.get("rotate"):
            b["lines"][i], (layer, wants_glow) = clear_below(ln, np.asarray(above), gap)
            above = ImageChops.lighter(above, layer.getchannel("A"))
        else:
            layer, wants_glow = render_line(ln)
        text = Image.alpha_composite(text, layer)
        if wants_glow: glowing = Image.alpha_composite(glowing, layer)
        masks.append(layer.getchannel("A"))
    fg = Image.alpha_composite(glow_of(glowing), text)
    base = scrim(*b["scrim"], b.get("scrim_opacity", spec["scrim_opacity"])) if b.get("scrim") else Image.new("RGBA", (W, H))
    return base, fg, masks


def shimmer_frame(fg, mask, bbox, k):
    x0, y0, x1, y1 = bbox; span = (x1 - x0) + 600 * K
    cx = x0 - 300 * K + span * k
    band = Image.new("L", (W, H)); d = ImageDraw.Draw(band)
    for j in range(-90, 91, 3):
        i = j * K; v = int(235 * math.exp(-(j / 45) ** 2))
        d.polygon([(cx + i - 120 * K, y1 + 40 * K), (cx + i + 3 * K - 120 * K, y1 + 40 * K), (cx + i + 3 * K + 120 * K, y0 - 40 * K), (cx + i + 120 * K, y0 - 40 * K)], fill=v)
    hl = Image.new("RGBA", (W, H), (255, 252, 238, 0)); hl.putalpha(ImageChops.multiply(band, mask))
    return Image.alpha_composite(fg, hl)


def pop_frame(base, fg, k, bbox):
    e = 1 - (1 - k) ** 3
    s = 0.72 + 0.28 * e + 0.07 * math.sin(math.pi * min(1.0, k * 1.15))
    cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
    sw, sh = int(W * s), int(H * s)
    scaled = fg.resize((sw, sh), Image.LANCZOS)
    frame = Image.new("RGBA", (W, H)); frame.paste(scaled, (int(cx - cx * s), int(cy - cy * s)))
    a = min(1.0, k * 2.2)
    frame.putalpha(frame.getchannel("A").point(lambda v: int(v * a)))
    sc = base.copy(); sc.putalpha(sc.getchannel("A").point(lambda v: int(v * min(1.0, k * 1.6))))
    return Image.alpha_composite(sc, frame)


def swing(rg, t):
    return rg["amp"] * math.exp(-t / rg["decay"]) * math.sin(2 * math.pi * rg["hz"] * t)


def ring_frames(base, b, rg):
    bell_line = next(ln for ln in b["lines"] if ln.get("bell"))
    frames = []
    for i in range(round(rg["dur"] * FPS)):
        bell_line["angle"] = swing(rg, i / FPS)
        _, fg, _ = build(b)
        frames.append(Image.alpha_composite(base, fg))
    bell_line["angle"] = 0.0
    hits = [((k + 0.5) / (2 * rg["hz"]), -rg.get("hit_drop_db", 3.5) * k) for k in range(rg.get("hits", 4))]
    return frames, hits


def write(name, b):
    base, fg, masks = build(b)
    still = Image.alpha_composite(base, fg)
    still.save(f"{out}/ov_{name}.png")
    seq = f"{out}/ov_{name}"
    if os.path.isdir(seq): shutil.rmtree(seq)
    frames = []
    if "pop" in b:
        bbox = fg.getchannel("A").point(lambda v: 255 if v > 40 else 0).getbbox()
        n = max(2, round(b["pop"] * FPS))
        frames = [pop_frame(base, fg, i / (n - 1), bbox) for i in range(n)]
    if "shimmer" in b:
        sh = b["shimmer"]; mask = masks[sh.get("line", 0)]; bbox = mask.getbbox()
        lead = round(sh["start"] * FPS); n = max(2, round(sh["dur"] * FPS))
        frames = [still] * lead + [Image.alpha_composite(base, shimmer_frame(fg, mask, bbox, i / (n - 1))) for i in range(n)] + [still]
    if "rings" in b:
        hits = []
        for rg in b["rings"]:
            at = round(rg["start"] * FPS)
            frames += [frames[-1] if frames else still] * max(0, at - len(frames))
            ring, ring_hits = ring_frames(base, b, rg)
            frames = frames[:at] + ring
            hits += [[round(at / FPS + t, 3), db] for t, db in ring_hits]
        frames.append(still)
        json.dump({"hits": hits}, open(f"{out}/sfx_{name}.json", "w"), indent=1)
    if frames:
        os.makedirs(seq)
        for i, fr in enumerate(frames): fr.save(f"{seq}/{i:03d}.png", compress_level=3)
    print(name, len(frames) or "still")


for name, b in spec["blocks"].items():
    write(name, b)

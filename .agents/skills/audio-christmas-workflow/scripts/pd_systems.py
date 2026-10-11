#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps


def load_gray(path):
    img = ImageOps.exif_transpose(Image.open(path)).convert("L")
    if img.width < 1600:
        scale = 1600 / img.width
        img = img.resize((1600, round(img.height * scale)), Image.LANCZOS)
    return img


def dark_mask(arr):
    hist = np.bincount(arr.ravel(), minlength=256).astype(float)
    total, levels = hist.sum(), np.arange(256)
    w0 = np.cumsum(hist)
    m0 = np.cumsum(hist * levels)
    w1 = total - w0
    with np.errstate(divide="ignore", invalid="ignore"):
        between = (m0[-1] * w0 / total - m0) ** 2 / (w0 * w1)
    return arr < int(np.nanargmax(between[:-1]))


def staff_lines(mask):
    h, w = mask.shape
    m = mask.astype(np.int8)
    long_runs = np.zeros(h)
    for y in range(h):
        d = np.diff(np.concatenate(([0], m[y], [0])))
        starts, ends = np.where(d == 1)[0], np.where(d == -1)[0]
        lens = ends - starts
        long_runs[y] = lens[lens >= 15].sum()
    smooth = long_runs + np.maximum(np.roll(long_runs, 1), np.roll(long_runs, -1))
    rows = np.where(smooth > w * 0.3)[0]
    lines = []
    for y in rows:
        if lines and y - lines[-1][-1] <= 2:
            lines[-1].append(y)
        else:
            lines.append([y])
    return [int(np.mean(l)) for l in lines]


def staves(lines):
    out = []
    i = 0
    while i + 4 < len(lines):
        group = lines[i:i + 5]
        gaps = np.diff(group)
        if gaps.max() <= 1.35 * gaps.min() and gaps.min() >= 5:
            out.append((group[0], group[-1], float(gaps.mean())))
            i += 5
        else:
            i += 1
    return out


def staff_left(mask, top, bottom):
    cols = mask[top:bottom + 1].sum(axis=0) >= 4
    xs = np.where(cols)[0]
    return int(xs[0]) if len(xs) else 0


def connected(mask, a, b):
    x0 = min(staff_left(mask, *a[:2]), staff_left(mask, *b[:2]))
    region = mask[a[1]:b[0], max(0, x0 - 40):x0 + 60]
    if region.size == 0:
        return False
    return bool((region.mean(axis=0) > 0.9).any())


def systems(mask):
    st = staves(staff_lines(mask))
    groups = []
    for s in st:
        if groups and connected(mask, groups[-1][-1], s):
            groups[-1].append(s)
        else:
            groups.append([s])
    return groups


def strips(img, out_dir, prefix, n=4, overlap=0.12):
    h = img.height
    step = h / n
    made = []
    for k in range(n):
        top = max(0, int(k * step - overlap * step))
        bottom = min(h, int((k + 1) * step + overlap * step))
        out = out_dir / f"{prefix}-band{k + 1}.png"
        img.crop((0, top, img.width, bottom)).save(out)
        made.append({"file": out.name, "band": k + 1, "y": [top, bottom]})
    return made


def sane(groups):
    sizes = {len(g) for g in groups}
    return len(groups) >= 2 and len(sizes) == 1


def crop_page(path, out_dir, prefix):
    img = load_gray(path)
    arr = np.asarray(img)
    groups = systems(dark_mask(arr))
    h = arr.shape[0]
    overview = out_dir / f"{prefix}-page.png"
    img.resize((1400, round(img.height * 1400 / img.width)), Image.LANCZOS).save(overview)
    if not sane(groups):
        return "bands", strips(img, out_dir, prefix)
    bounds = []
    for g in groups:
        sp = np.mean([s[2] for s in g])
        bounds.append([g[0][0] - 5 * sp, g[-1][1] + 6 * sp])
    for i in range(len(bounds) - 1):
        mid = (groups[i][-1][1] + groups[i + 1][0][0]) / 2
        if bounds[i][1] > mid + 2 * groups[i][-1][2]:
            bounds[i][1] = mid + 2 * groups[i][-1][2]
        if bounds[i + 1][0] < mid - 2 * groups[i + 1][0][2]:
            bounds[i + 1][0] = mid - 2 * groups[i + 1][0][2]
    made = []
    for n, (g, (top, bottom)) in enumerate(zip(groups, bounds), 1):
        top, bottom = max(0, int(top)), min(h, int(bottom))
        out = out_dir / f"{prefix}-s{n}.png"
        img.crop((0, top, img.width, bottom)).save(out)
        made.append({"file": out.name, "staves": len(g), "y": [top, bottom]})
    return "systems", made


def main():
    ap = argparse.ArgumentParser(description="Cut score pages into one image per system (staves joined by a left barline); 4 overlapping bands when systems are unclear")
    ap.add_argument("pages", nargs="+", help="page images, in reading order")
    ap.add_argument("--out", required=True, help="output folder for the system images + systems.json")
    args = ap.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    index = []
    for n, page in enumerate(args.pages, 1):
        mode, made = crop_page(page, out_dir, f"p{n}")
        index.append({"page": str(page), "overview": f"p{n}-page.png", "mode": mode, "crops": made})
        print(f"{page}: {mode} " + " ".join(m["file"] for m in made))
    (out_dir / "systems.json").write_text(json.dumps(index, indent=2))


if __name__ == "__main__":
    sys.exit(main())

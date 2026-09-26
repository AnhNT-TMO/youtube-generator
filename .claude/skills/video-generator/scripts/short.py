#!/usr/bin/env python3
USAGE = """Server side of `video.py short`: vertical Short = seamless loop as long as the clip + spectrum + lyric lines + hook + CTA.

    VG_FRAME=1080x1920 short.py IMAGE AUDIO SHORT_JSON PRESET_JSON OUTDIR [--jobs N] [--encoder nvenc]

SHORT_JSON (written by the youtube-shorts skill): in/out seconds in AUDIO, fade_in/fade_out, captions [{t0, t1, text}],
hook {text, t1}, cta {text, t0} (times from the Short's 0:00). PRESET_JSON: merged video config incl. the `short` block.
Writes OUTDIR/video.mp4 (+ loop.mp4, seg.wav, bars.mp4 along the way).
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import config  # noqa: E402
import encode  # noqa: E402
from config import H, W  # noqa: E402


def sh(cmd):
    print("$ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def font(name, size):
    from PIL import ImageFont
    f = ImageFont.truetype(os.path.join(HERE, "fonts", name), size)
    if "Variable" in name:
        try:
            f.set_variation_by_name("Bold")
        except (OSError, ValueError):
            pass
    return f


def wrap(draw, text, f, max_w):
    words = text.split()
    if draw.textlength(text, font=f) <= max_w:
        return [text]
    lines, cur = [], ""
    for word in words:
        trial = f"{cur} {word}".strip()
        if cur and draw.textlength(trial, font=f) > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    if len(lines) == 2:
        splits = [(" ".join(words[:i]), " ".join(words[i:])) for i in range(1, len(words))]
        fit = [sp for sp in splits if max(draw.textlength(x, font=f) for x in sp) <= max_w]
        if fit:
            lines = list(min(fit, key=lambda sp: max(draw.textlength(x, font=f) for x in sp)))
    return lines


def text_png(path, text, style, common):
    from PIL import Image, ImageDraw, ImageFilter
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = font(style["font"], style["size_px"])
    lines = wrap(d, text, f, common["max_width"] * W)
    step = style["size_px"] * common["line_spacing"]
    y0 = style["y"] * H - step * len(lines) / 2
    cx = common["center_x"] * W
    stroke = common["stroke_px"]
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    for i, line in enumerate(lines):
        x = cx - d.textlength(line, font=f) / 2
        y = y0 + i * step
        sd.text((x, y + stroke), line, font=f, fill=(0, 0, 0, int(255 * common["shadow_opacity"])))
        d.text((x, y), line, font=f, fill=tuple(style["color"]) + (255,), stroke_width=stroke,
               stroke_fill=tuple(common["stroke_color"]) + (255,))
    shadow = shadow.filter(ImageFilter.GaussianBlur(common["shadow_px"]))
    Image.alpha_composite(shadow, img).save(path)
    top, bottom = y0, y0 + step * len(lines)
    return {"lines": len(lines), "top": round(top / H, 3), "bottom": round(bottom / H, 3)}


def overlays(spec, cfg, work, dur):
    s = cfg["short"]
    items = []
    hook = spec.get("hook") or {}
    if hook.get("text"):
        t1 = hook.get("t1", s["hook"]["seconds"])
        items.append(("hook", hook["text"], 0.0, t1, s["hook"]))
    for i, c in enumerate(spec.get("captions", [])):
        items.append((f"cap{i:02d}", c["text"], c["t0"], min(dur, c["t1"]), s["captions"]))
    cta = spec.get("cta") or {}
    if cta.get("text"):
        t0 = cta.get("t0", dur - s["cta"]["seconds"])
        items.append(("cta", cta["text"], max(0.0, t0), dur, s["cta"]))
    out = []
    for name, text, t0, t1, style in items:
        if t1 - t0 < 0.3:
            continue
        png = os.path.join(work, f"ov_{name}.png")
        box = text_png(png, text, style, s["text"])
        out.append({"png": png, "t0": t0, "t1": t1, "fade": style["fade_seconds"], "name": name, **box})
    return out


def compose(bars_mp4, ovs, out, cfg, encoder, dur):
    fps = cfg["fps"]
    inputs = ["-i", bars_mp4]
    chains, last = [], "0:v"
    for i, o in enumerate(ovs, start=1):
        inputs += ["-loop", "1", "-framerate", str(fps), "-t", f"{o['t1'] - o['t0']:.3f}", "-i", o["png"]]
        fd = min(o["fade"], (o["t1"] - o["t0"]) / 3)
        chains.append(f"[{i}:v]format=rgba,setpts=PTS-STARTPTS+{o['t0']:.3f}/TB,"
                      f"fade=t=in:st={o['t0']:.3f}:d={fd:.3f}:alpha=1,"
                      f"fade=t=out:st={o['t1'] - fd:.3f}:d={fd:.3f}:alpha=1[o{i}]")
        chains.append(f"[{last}][o{i}]overlay=0:0:eof_action=pass:"
                      f"enable='between(t,{o['t0']:.3f},{o['t1']:.3f})'[v{i}]")
        last = f"v{i}"
    fc = ";".join(chains) if chains else "[0:v]null[v0]"
    last = last if chains else "v0"
    enc = cfg["encode"]
    br = cfg["short"]["video_bitrate"]
    rate = ["-maxrate", br, "-bufsize", str(int(br.rstrip("M")) * 2) + "M"] if br.endswith("M") else []
    sh(["ffmpeg", "-y", "-loglevel", "error"] + inputs + ["-filter_complex", fc, "-map", f"[{last}]", "-map", "0:a",
        "-t", f"{dur:.3f}"] + encode.codec_args(enc, fps, encoder) + rate
       + ["-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", out])


def main():
    ap = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("audio")
    ap.add_argument("short_json")
    ap.add_argument("preset")
    ap.add_argument("outdir")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--encoder", choices=encode.ENCODERS)
    a = ap.parse_args()

    spec = json.load(open(a.short_json))
    cfg = config.load(a.preset)
    dur = spec["out"] - spec["in"]
    if not 5 <= dur <= 180:
        sys.exit(f"Short dài {dur:.1f} s: phải trong 5–180 s")
    if (W, H) != tuple(cfg["short"]["frame"]):
        sys.exit(f"VG_FRAME {W}x{H} ≠ short.frame {cfg['short']['frame']}")
    os.makedirs(a.outdir, exist_ok=True)
    loop = os.path.join(a.outdir, "loop.mp4")
    seg = os.path.join(a.outdir, "seg.wav")
    bars_mp4 = os.path.join(a.outdir, "bars.mp4")
    enc = ["--encoder", a.encoder] if a.encoder else []

    sh([sys.executable, os.path.join(HERE, "make_loop.py"), a.image, loop, "--preset", a.preset,
        "--jobs", str(a.jobs)] + enc)
    fi, fo = spec.get("fade_in", 0.02), spec.get("fade_out", 0.5)
    sh(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{spec['in']:.3f}", "-t", f"{dur:.3f}", "-i", a.audio,
        "-af", f"afade=t=in:st=0:d={fi:.3f},afade=t=out:st={dur - fo:.3f}:d={fo:.3f},"
        f"loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000", "-ar", "48000", "-ac", "2", seg])
    sh([sys.executable, os.path.join(HERE, "extend.py"), loop, seg, bars_mp4, "--preset", a.preset,
        "--no-intro", "--jobs", "1"] + enc)
    work = os.path.join(a.outdir, "overlays")
    os.makedirs(work, exist_ok=True)
    ovs = overlays(spec, cfg, work, dur)
    out = os.path.join(a.outdir, "video.mp4")
    compose(bars_mp4, ovs, out, cfg, a.encoder, dur)
    json.dump([{k: o[k] for k in ("name", "t0", "t1", "lines", "top", "bottom")} for o in ovs],
              open(os.path.join(a.outdir, "overlays.json"), "w"), indent=1)
    print(f"done {out} ({dur:.1f} s, {len(ovs)} text overlays)", flush=True)


if __name__ == "__main__":
    main()

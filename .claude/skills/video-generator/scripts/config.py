"""Defaults for every effect, plus layered config loading.

Layers, later ones win. Dicts merge key by key, so `{"light": {"amount": 0.2}}`
keeps the rest of the light settings. `particles` merges layer by layer by
position (`[{"count": 100}]` tweaks the first layer; extra entries add layers;
`"enabled": false` drops one). Other lists (light shapes, waves) are replaced.

  1. DEFAULTS below: the layout every channel shares (logo top-right,
     like/subscribe bottom-right every 30-45 s, spectrum row, logo intro)
  2. channel/<name>/video.json: the channel's look (particle kind, colours,
     light, bar colours) and its logo in channel/<name>/image_source/
  3. <idea or album dir>/video.json (optional): what depends on that one
     image (where the light shaft falls, a lamp to flicker)

Colours are [R, G, B] 0-255. Positions are fractions of the frame
(0 = left/top, 1 = right/bottom) unless the key says `_px`. `_px` values are
written for a 1920×1080 frame and scaled to the output frame by load(), so
every video.json keeps working whatever W, H is. Relative paths in a config
(logo) start at the repo root.
"""
import copy
import json
import math
import os

W, H = 3840, 2160          # output frame: 4K UHD (YouTube gives 4K uploads a higher bitrate at every quality)
PX_SCALE = W / 1920        # `_px` settings are authored for 1920×1080


def _find_repo():
    """The repo root: $VG_REPO (set on the render server), else the nearest
    folder above this script that holds CLAUDE.md, else the working dir."""
    if os.environ.get("VG_REPO"):
        return os.path.abspath(os.path.expanduser(os.environ["VG_REPO"]))
    d = os.path.dirname(os.path.abspath(__file__))
    while d != os.path.dirname(d):
        if os.path.exists(os.path.join(d, "CLAUDE.md")):
            return d
        d = os.path.dirname(d)
    return os.getcwd()


REPO = _find_repo()

DEFAULTS = {
    "fps": 30,
    "loop_seconds": 300,

    # 1. breathing light shaft (and/or glow blobs) laid over the photo
    "light": {
        "enabled": True,
        # any mix of polygons [[x,y],...] and ellipses {"ellipse":[cx,cy,rx,ry]},
        # all fractions of the frame; they share one mask and one breath
        "shapes": [[[0.42, -0.10], [1.00, -0.10], [0.88, 0.95], [0.28, 0.80]]],
        "blur_px": 150,
        "color": [255, 231, 178],
        "floor": 0.02,          # how much colour sits in the shaft at its dimmest
        "amount": 0.17,         # extra colour at full breath, 0..1
        "levels": 24,           # precomputed brightness steps
        # breath(t) = base + sum(amp * sin(2*pi*t/period + phase)), clipped 0..1
        "base": 0.55,
        "waves": [{"period": 7.3, "amp": 0.30, "phase": 0.0},
                  {"period": 3.1, "amp": 0.15, "phase": 1.2}],
    },

    # optional warm flicker on a lamp/candle/fire that is in the photo
    "lantern": {
        "enabled": False,
        "center": [0.182, 0.650],
        "radius": 0.10,          # fraction of frame width
        "color": [255, 194, 102],
        "strength": 34,          # peak added brightness, 0-255
        "base": 0.52,
        "waves": [{"period": 0.83, "amp": 0.24, "phase": 0.0},
                  {"period": 0.37, "amp": 0.14, "phase": 1.1},
                  {"period": 0.19, "amp": 0.09, "phase": 2.3}],
    },

    # 2. particle layers: dust, snow, embers... each entry is one layer
    "particles": [{
        "enabled": True,
        "from": "bottom",        # top, top-right, right, bottom-right,
                                 # bottom, bottom-left, left, top-left
        "count": 440,
        "shape": "dot",          # dot | flake
        "color": [255, 237, 204],
        "intensity": 286,        # peak brightness added by the nearest particle
        "far_intensity": 0.30,   # farthest particle, as a share of intensity
        "size_px": [2, 11],      # radius range, far -> near
        "size_curve": 1.7,       # >1 means most particles stay small
        "cross_seconds": 35,     # time to cross the screen at average speed
        "speed_jitter": 0.55,    # +- share of random speed per particle
        "parallax": 0.0,         # 0..1, near particles move faster
        "sway_px": [12, 67],     # sideways drift amplitude range
        "sway_seconds": [6, 19], # sideways drift period range
        "twinkle_seconds": [4.75, 12.7],
        "twinkle_depth": 0.9,    # 0 = steady, 1 = fades fully out
        "lanes": None,           # [start, end] across the motion (straight
                                 # directions only), e.g. [0.30, 1.02]
        "lane_share": 0.65,      # share of particles kept inside `lanes`
        "seed": 5,
    }],

    # 3. channel logo, a PNG with transparency
    "logo": {
        "enabled": True,
        "path": None,            # set by the channel, e.g. channel/<name>/image_source/logo.png
        "width_px": 232,
        "corner": "tr",          # tl | tr | bl | br
        "margin_px": 40,
        "opacity": 1.0,
        "shadow": {"radius": 18, "spread": 0.42},
    },

    # 4. like / subscribe / bell with a clicking cursor
    "subscribe": {
        "enabled": True,
        "every_seconds": [30, 45],  # gap between appearances: a number, or
                                    # [min, max] for uneven gaps (fixed by seed)
        "first_at": 20,           # first appearance, seconds into the loop
        "at_seconds": None,       # explicit start times instead, e.g. [20, 170]
        "seed": 7,
        "show_seconds": 11.0,
        "height_px": 80,
        "corner": "br",
        "margin_px": 44,
        "label": "SUBSCRIBE",
        "label_done": "SUBSCRIBED",
    },

    # channel logo intro at the start of the video (audio starts under it)
    "intro": {
        "enabled": True,
        "seconds": 4.0,
        "fade_in_seconds": 0.8,
        "crossfade_seconds": 1.4,   # logo lifts away, photo fades in
        "logo_width_px": 460,
        "bg_blur_px": 28,           # background: the photo, blurred and dimmed
        "bg_dim": 0.30,
        "halo_color": [255, 209, 140],
        "halo_strength": 110,       # peak brightness added by the halo
        "shine_at": 1.2,            # when the sheen starts sweeping, seconds
    },

    # audio spectrum row, drawn over the full-length video by extend.py
    "bars": {
        "enabled": True,
        "bands": 72,
        "center": 0.50,
        "span": 0.41,
        "height_px": 106,
        "baseline_px": 58,
        "bar_width": 0.42,       # share of each slot that is bar
        "color_tip": [255, 238, 198],
        "color_base": [251, 184, 120],
        "opacity": 0.93,
        "glow_px": 7,
        "glow_color": [255, 209, 120],
        "glow_strength": 0.46,
        "scrim": 0.30,           # soft shade under the row, 0..1
        "attack": 0.55,
        "release": 0.13,
        "fmin": 45.0,
        "fmax": 11000.0,
    },

    "encode": {
        "encoder": "x264",       # x264 | nvenc (NVIDIA GPU) | videotoolbox (Mac)
        "crf": 19,
        "preset": "veryfast",
        "x264": "no-fast-pskip=1:no-dct-decimate=1:aq-mode=3",
        "grain": 0,              # ffmpeg film grain strength, 0 = off
        "gop_seconds": 10,       # a keyframe every N seconds, where cuts happen
        "nvenc_preset": "p5",
        "nvenc_cq": 19,
        "vt_bitrate": "10M",
    },
}

DIRECTIONS = {  # where particles come FROM -> unit step they move by
    "top": (0, 1), "top-right": (-1, 1), "right": (-1, 0), "bottom-right": (-1, -1),
    "bottom": (0, -1), "bottom-left": (1, -1), "left": (1, 0), "top-left": (1, 1),
}


def _merge(base, over):
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _merge(base[k], v)
        else:
            base[k] = v
    return base


def merge_files(paths):
    """DEFAULTS with each JSON file merged on top, paths left as written."""
    cfg = copy.deepcopy(DEFAULTS)
    if isinstance(paths, str):
        paths = [paths]
    for path in paths or []:
        with open(path) as fh:
            user = json.load(fh)
        user.pop("_comment", None)
        layers = user.pop("particles", None)
        _merge(cfg, user)
        for i, p in enumerate(layers or []):
            if i < len(cfg["particles"]):
                _merge(cfg["particles"][i], p)
            else:
                cfg["particles"].append(p)
    defaults_p = DEFAULTS["particles"][0]
    cfg["particles"] = [_merge(copy.deepcopy(defaults_p), p) for p in cfg["particles"]]
    for p in cfg["particles"]:
        if p["from"] not in DIRECTIONS:
            raise ValueError(f"particles.from must be one of {list(DIRECTIONS)}")
    return cfg


def _scale(v):
    return [_scale(x) for x in v] if isinstance(v, list) else round(v * PX_SCALE) if isinstance(v, int) else v * PX_SCALE


def scale_px(node):
    """Every `_px` value (written for 1920×1080) × PX_SCALE, in place. Only load() calls it, once per config:
    merge_files() output (the preset.json sent to the server) stays in 1080p units."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k.endswith("_px") and v is not None:
                node[k] = _scale(v)
            else:
                scale_px(v)
    elif isinstance(node, list):
        for v in node:
            scale_px(v)


def load(paths=None):
    """merge_files() plus `_px` values scaled to the output frame and paths resolved against the repo root."""
    cfg = merge_files(paths)
    scale_px(cfg)
    if cfg["logo"].get("shadow"):              # the one pixel size without the `_px` suffix
        cfg["logo"]["shadow"]["radius"] = _scale(cfg["logo"]["shadow"]["radius"])
    logo = cfg["logo"]
    if logo["enabled"] or cfg["intro"]["enabled"]:
        if not logo["path"]:
            raise ValueError("logo.path is not set; the channel's video.json should set it")
        if not os.path.isabs(logo["path"]):
            logo["path"] = os.path.join(REPO, logo["path"])
    return cfg


def cycles(period, loop):
    """Whole number of cycles that fit the loop, closest to `period` seconds.

    Every moving thing uses a whole number of cycles per loop, so the last
    frame of the loop flows straight into the first.
    """
    return max(1, round(loop / period))


def wave(t, waves, loop):
    """Sum of sines, each snapped to a whole number of cycles per loop."""
    return sum(w["amp"] * math.sin(2 * math.pi * cycles(w["period"], loop) * t / loop
                                   + w.get("phase", 0.0))
               for w in waves)

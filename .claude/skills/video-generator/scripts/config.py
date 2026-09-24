import copy
import json
import math
import os

W, H = 3840, 2160
PX_SCALE = W / 1920


def _find_repo():
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

    "light": {
        "enabled": True,
        "shapes": [[[0.42, -0.10], [1.00, -0.10], [0.88, 0.95], [0.28, 0.80]]],
        "blur_px": 150,
        "color": [255, 231, 178],
        "floor": 0.02,
        "amount": 0.17,
        "levels": 24,
        "base": 0.55,
        "waves": [{"period": 7.3, "amp": 0.30, "phase": 0.0},
                  {"period": 3.1, "amp": 0.15, "phase": 1.2}],
    },

    "lantern": {
        "enabled": False,
        "center": [0.182, 0.650],
        "radius": 0.10,
        "color": [255, 194, 102],
        "strength": 34,
        "base": 0.52,
        "waves": [{"period": 0.83, "amp": 0.24, "phase": 0.0},
                  {"period": 0.37, "amp": 0.14, "phase": 1.1},
                  {"period": 0.19, "amp": 0.09, "phase": 2.3}],
    },

    "particles": [{
        "enabled": True,
        "from": "bottom",
        "count": 440,
        "shape": "dot",
        "color": [255, 237, 204],
        "intensity": 286,
        "far_intensity": 0.30,
        "size_px": [2, 11],
        "size_curve": 1.7,
        "cross_seconds": 35,
        "speed_jitter": 0.55,
        "parallax": 0.0,
        "sway_px": [12, 67],
        "sway_seconds": [6, 19],
        "twinkle_seconds": [4.75, 12.7],
        "twinkle_depth": 0.9,
        "lanes": None,
        "lane_share": 0.65,
        "seed": 5,
    }],

    "logo": {
        "enabled": True,
        "path": None,
        "width_px": 232,
        "corner": "tr",
        "margin_px": 40,
        "opacity": 1.0,
        "shadow": {"radius": 18, "spread": 0.42},
    },

    "subscribe": {
        "enabled": True,
        "every_seconds": [30, 45],
        "first_at": 20,
        "at_seconds": None,
        "seed": 7,
        "show_seconds": 11.0,
        "height_px": 80,
        "corner": "br",
        "margin_px": 44,
        "label": "SUBSCRIBE",
        "label_done": "SUBSCRIBED",
    },

    "intro": {
        "enabled": True,
        "seconds": 4.0,
        "fade_in_seconds": 0.8,
        "crossfade_seconds": 1.4,
        "logo_width_px": 460,
        "bg_blur_px": 28,
        "bg_dim": 0.30,
        "halo_color": [255, 209, 140],
        "halo_strength": 110,
        "shine_at": 1.2,
    },

    "bars": {
        "enabled": True,
        "bands": 72,
        "center": 0.50,
        "span": 0.41,
        "height_px": 106,
        "baseline_px": 58,
        "bar_width": 0.42,
        "color_tip": [255, 238, 198],
        "color_base": [251, 184, 120],
        "opacity": 0.93,
        "glow_px": 7,
        "glow_color": [255, 209, 120],
        "glow_strength": 0.46,
        "scrim": 0.30,
        "attack": 0.55,
        "release": 0.13,
        "fmin": 45.0,
        "fmax": 11000.0,
    },

    "encode": {
        "encoder": "x264",
        "crf": 19,
        "preset": "veryfast",
        "x264": "no-fast-pskip=1:no-dct-decimate=1:aq-mode=3",
        "grain": 0,
        "gop_seconds": 10,
        "nvenc_preset": "p5",
        "nvenc_cq": 19,
        "vt_bitrate": "10M",
    },
}

DIRECTIONS = {
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
    cfg = merge_files(paths)
    scale_px(cfg)
    if cfg["logo"].get("shadow"):
        cfg["logo"]["shadow"]["radius"] = _scale(cfg["logo"]["shadow"]["radius"])
    logo = cfg["logo"]
    if logo["enabled"] or cfg["intro"]["enabled"]:
        if not logo["path"]:
            raise ValueError("logo.path is not set; the channel's video.json should set it")
        if not os.path.isabs(logo["path"]):
            logo["path"] = os.path.join(REPO, logo["path"])
    return cfg


def cycles(period, loop):
    return max(1, round(loop / period))


def wave(t, waves, loop):
    return sum(w["amp"] * math.sin(2 * math.pi * cycles(w["period"], loop) * t / loop
                                   + w.get("phase", 0.0))
               for w in waves)

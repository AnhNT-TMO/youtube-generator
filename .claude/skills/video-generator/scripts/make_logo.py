"""Draw the channel badge once and save it as a transparent PNG.

The video tools only ever read the PNG, so every video uses the exact same
mark. Re-run this only when the logo itself should change.

    python scripts/make_logo.py --channel lamplight_gospel   # channel/<name>/image_source/logo.png
    python scripts/make_logo.py --title LAMPLIGHT --sub GOSPEL --size 1024 --out path.png
"""
import argparse
import os

import brand

from config import REPO


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", default="LAMPLIGHT")
    ap.add_argument("--sub", default="GOSPEL")
    ap.add_argument("--size", type=int, default=1024, help="diameter in px")
    ap.add_argument("--glow", type=float, default=0.54, help="flame halo, 0..1")
    ap.add_argument("--channel", default="lamplight_gospel",
                    help="writes channel/<name>/image_source/logo.png")
    ap.add_argument("--out", help="explicit output path instead of --channel")
    a = ap.parse_args()
    a.out = a.out or os.path.join(REPO, "channel", a.channel, "image_source", "logo.png")
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    brand.badge(a.size, a.title, a.sub, glow=a.glow).save(a.out, optimize=True)
    print(a.out)


if __name__ == "__main__":
    main()

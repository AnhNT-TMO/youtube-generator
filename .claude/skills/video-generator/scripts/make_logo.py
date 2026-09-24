import argparse
import os

import brand

from config import REPO


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--sub", required=True)
    ap.add_argument("--size", type=int, default=1024, help="diameter in px")
    ap.add_argument("--glow", type=float, default=0.54, help="flame halo, 0..1")
    ap.add_argument("--channel", help="writes channel/<name>/image_source/logo.png")
    ap.add_argument("--out", help="explicit output path instead of --channel")
    a = ap.parse_args()
    if not (a.out or a.channel):
        ap.error("--channel or --out is required")
    a.out = a.out or os.path.join(REPO, "channel", a.channel, "image_source", "logo.png")
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    brand.badge(a.size, a.title, a.sub, glow=a.glow).save(a.out, optimize=True)
    print(a.out)


if __name__ == "__main__":
    main()

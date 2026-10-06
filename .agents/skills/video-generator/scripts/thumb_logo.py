import argparse
import io
import os

import numpy as np
from PIL import Image

import config
import effects


class Canvas:
    def __init__(self, img):
        self.plates = [np.asarray(img).copy()]

    def burn(self, rgb, alpha, x, y, opacity=1.0):
        effects.blit(self.plates[0], rgb, alpha, x, y, opacity)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    a = ap.parse_args()
    d = os.path.abspath(a.dir)
    layers = [os.path.join(config.REPO, "channel", os.path.relpath(d, os.path.join(config.REPO, "channel")).split(os.sep)[0], "video.json")]
    if os.path.exists(os.path.join(d, "video.json")):
        layers.append(os.path.join(d, "video.json"))
    cfg = config.load(layers)
    img = Image.open(os.path.join(d, "thumbnail.png")).convert("RGB").resize((config.W, config.H), Image.LANCZOS)
    c = Canvas(img)
    effects.add_logo(c, cfg)
    effects.add_stamp(c, cfg["badge"])
    out = Image.fromarray(c.plates[0])
    q = 92
    while True:
        buf = io.BytesIO()
        out.save(buf, "JPEG", quality=q, optimize=True)
        if buf.tell() <= 2_000_000 or q < 60:
            break
        q -= 3
    open(os.path.join(d, "thumbnail.jpg"), "wb").write(buf.getvalue())
    marks = [f"{k} ({cfg[k]['corner']})" for k in ("logo", "badge") if cfg[k]["enabled"]]
    print(f"thumbnail.jpg with {' + '.join(marks) or 'no logo'} q{q} {buf.tell() / 1e6:.2f} MB; "
          "thumbnail.png (video source) has none")


if __name__ == "__main__":
    main()

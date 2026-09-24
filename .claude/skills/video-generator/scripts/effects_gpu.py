"""GPU (torch CUDA) frame loop for effects.Scene: same layers, same maths, same pixels.

effects.Scene still builds everything once (light plates with the logo and the bar scrim burned in, lantern glow,
particle parameters, subscribe widget); only the per-frame work runs on the GPU: pick the plate, add the lantern,
splat every particle in one index_add_ per sprite size (instead of a Python loop over hundreds of particles),
alpha-blend the subscribe group. At 4K the CPU loop was the slowest step of a render (2026-09-24).

Opt-in: make_loop.py uses it only with VG_GPU=1 (needs torch cu128 in the server venv). Pixel-identical to effects.py
(compare() below: 0 differing pixels). One process: 256 frames/s vs 245 on the CPU, and NV12 on the GPU makes an encode
+57 % faster; but 16 render processes time-slice one GPU, so a 5-min 4K loop took 103-110 s against 52 s for CPU frames
+ NVENC (2026-09-24). Worth revisiting only with a single-process renderer (one CUDA context, streams).
`python effects_gpu.py IMAGE --preset ...` compares both on sample frames.
"""
import numpy as np
import torch

import effects
from config import H, W, wave


def available():
    try:
        return torch.cuda.is_available()
    except Exception:          # noqa: BLE001 - no usable CUDA runtime
        return False


class GpuScene:
    def __init__(self, image_path, cfg, bars=True, device="cuda"):
        self.cpu = effects.Scene(image_path, cfg, bars=bars)
        self.dev = torch.device(device)
        pl = self.cpu.plates
        self.plate_cfg, self.loop = pl.cfg, pl.loop
        self.plates = torch.from_numpy(np.stack(pl.plates)).to(self.dev)          # (n, H, W, 3) uint8
        self.lantern, self.particles, self.subscribe = None, [], None
        for layer in self.cpu.layers:
            if isinstance(layer, effects.Lantern):
                self.lantern = (layer, torch.from_numpy(layer.glow).to(self.dev))
            elif isinstance(layer, effects.Particles):
                self.particles.append((layer, self._sprites(layer)))
            elif isinstance(layer, effects.Subscribe):
                sh_rgb, sh_a = layer.sh
                self.subscribe = (layer, torch.from_numpy(sh_rgb).to(self.dev), torch.from_numpy(sh_a).to(self.dev))

    def _sprites(self, layer):
        """Per sprite radius: pixel offsets and sprite values, flattened."""
        out = {}
        for r, spr in layer.spr.items():
            yy, xx = np.mgrid[0:2 * r + 1, 0:2 * r + 1]
            out[r] = (torch.from_numpy(yy.ravel()).to(self.dev), torch.from_numpy(xx.ravel()).to(self.dev),
                      torch.from_numpy(spr.ravel().astype(np.float32)).to(self.dev))
        return out

    def _plate(self, t):
        n = self.plates.shape[0]
        if n == 1:
            return self.plates[0]
        lc = self.plate_cfg
        b = lc["base"] + wave(t, lc["waves"], self.loop)
        return self.plates[int(round(min(1.0, max(0.0, b)) * (n - 1)))]

    def _splat(self, acc, layer, sprites, t):
        xs, ys, vs = layer.positions(t)
        keep = vs >= 6
        if not keep.any():
            return
        tint = torch.from_numpy(layer.tint).to(self.dev)
        r_all = layer.r[keep]
        x0s = np.trunc(xs[keep]).astype(np.int64) - r_all
        y0s = np.trunc(ys[keep]).astype(np.int64) - r_all
        v_all = vs[keep].astype(np.float32)
        flat = acc.view(-1, 3)
        for r in np.unique(r_all):
            sel = r_all == r
            dy, dx, spr = sprites[int(r)]
            y = torch.from_numpy(y0s[sel]).to(self.dev)[:, None] + dy[None, :]
            x = torch.from_numpy(x0s[sel]).to(self.dev)[:, None] + dx[None, :]
            v = torch.from_numpy(v_all[sel]).to(self.dev)[:, None] * spr[None, :]
            ok = (x >= 0) & (x < W) & (y >= 0) & (y < H)
            add = torch.trunc(v[ok][:, None] * tint[None, :])                    # CPU: .astype(int16) per particle
            flat.index_add_(0, (y[ok] * W + x[ok]), add)

    @staticmethod
    def _blit(frame, rgb, alpha, x, y, opacity):
        h, w = alpha.shape
        sx, sy = max(0, -x), max(0, -y)
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(W, x + w), min(H, y + h)
        if x1 <= x0 or y1 <= y0 or opacity <= 0.003:
            return
        a = alpha[sy:sy + (y1 - y0), sx:sx + (x1 - x0)][:, :, None] * opacity
        c = rgb[sy:sy + (y1 - y0), sx:sx + (x1 - x0)]
        reg = frame[y0:y1, x0:x1]
        frame[y0:y1, x0:x1] = torch.trunc(reg * (1 - a) + c * a)

    @torch.inference_mode()
    def frame_tensor(self, t):
        acc = self._plate(t).float()
        if self.lantern:
            layer, glow = self.lantern
            f = layer.c["base"] + wave(t, layer.c["waves"], layer.loop)
            x0, y0 = layer.xy
            h, w = glow.shape[:2]
            sx, sy = max(0, -x0), max(0, -y0)
            cx0, cy0, cx1, cy1 = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
            if cx1 > cx0 and cy1 > cy0:
                g = glow[sy:sy + (cy1 - cy0), sx:sx + (cx1 - cx0)] * (layer.c["strength"] * max(0.0, f))
                acc[cy0:cy1, cx0:cx1] += torch.trunc(g)
                acc.clamp_(0, 255)
        for layer, sprites in self.particles:
            self._splat(acc, layer, sprites, t)
        acc.clamp_(0, 255)
        if self.subscribe:
            layer, sh_rgb, sh_a = self.subscribe
            o, dy, phase = layer.state(t)
            if o > 0.003:
                y = int(layer.y + dy)
                self._blit(acc, sh_rgb, sh_a, layer.x - layer.sh_off, y - layer.sh_off, o)
                rgb, al = effects.to_layers(layer.w.render(phase))
                self._blit(acc, torch.from_numpy(rgb).to(self.dev), torch.from_numpy(al).to(self.dev),
                           layer.x, y, o)
        return acc.to(torch.uint8)

    def frame(self, t):
        return self.frame_tensor(t).cpu().numpy()

    # BT.601 limited range, the matrix swscale uses for rgb24 -> yuv420p (43 dB from the CPU path after NVENC)
    _M = torch.tensor([[65.481, 128.553, 24.966], [-37.797, -74.203, 112.0], [112.0, -93.786, -18.214]]) / 255

    @torch.inference_mode()
    def frame_nv12(self, t):
        """The frame as NV12 bytes (Y plane + interleaved UV at half size), converted on the GPU: half the bytes of
        rgb24 through the pipe and no swscale in ffmpeg (+57 % frames/s per encode, 2026-09-24)."""
        m = self._M.to(self.dev)
        x = self.frame_tensor(t).float() @ m.T
        y = (x[..., 0] + 16).round_().clamp_(0, 255).to(torch.uint8)
        uv = x[..., 1:].reshape(H // 2, 2, W // 2, 2, 2).mean((1, 3)).add_(128).round_().clamp_(0, 255).to(torch.uint8)
        return torch.cat([y.reshape(-1), uv.reshape(-1)]).cpu().numpy().tobytes()


def compare(image, presets, times=(0.0, 7.3, 20.5, 25.0, 123.4, 299.9)):
    import config
    cfg = config.load(presets)
    cpu, gpu = effects.Scene(image, cfg), GpuScene(image, cfg)
    for t in times:
        a, b = cpu.frame(t).astype(np.float32), gpu.frame(t).astype(np.float32)
        mse = float(((a - b) ** 2).mean())
        psnr = 99.0 if mse == 0 else 10 * np.log10(255 ** 2 / mse)
        print(f"t={t:6.1f}s  max|diff| {np.abs(a - b).max():4.0f}  pixels differing {(a != b).any(-1).mean() * 100:6.3f} %  "
              f"PSNR {psnr:5.1f} dB")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--preset", action="append")
    a = ap.parse_args()
    compare(a.image, a.preset)

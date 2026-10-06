import numpy as np

SR = 48000


def _fft_size(n):
    return 1 << int(np.ceil(np.log2(n)))


def dark_reverb(x, seconds=2.6, wet=0.25, damping_hz=3500.0):
    rng = np.random.default_rng(7)
    n = int(seconds * SR)
    env = np.exp(-6.9 * np.arange(n) / n)
    ir = rng.standard_normal((n, 2)) * env[:, None]
    ir[: int(0.012 * SR)] = 0
    size = _fft_size(len(x) + n)
    freqs = np.fft.rfftfreq(size, 1 / SR)
    lowpass = 1.0 / (1.0 + (freqs / damping_hz) ** 2)
    ir_f = np.fft.rfft(ir, size, axis=0) * lowpass[:, None]
    ir = np.fft.irfft(ir_f, size, axis=0)[:n]
    ir /= np.sqrt((ir ** 2).sum(0))
    y = np.fft.irfft(np.fft.rfft(x, size, axis=0) * np.fft.rfft(ir, size, axis=0), size, axis=0)[: len(x) + n]
    dry = np.vstack([x, np.zeros((n, 2), dtype=x.dtype)])
    return (1 - wet) * dry + wet * y * (np.abs(dry).max() / (np.abs(y).max() + 1e-9))

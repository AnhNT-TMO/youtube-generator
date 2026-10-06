import json
import subprocess
import sys

import numpy as np
import torch
from demucs.apply import apply_model
from demucs.pretrained import get_model

WINDOW_S = 1.0
PROMINENT_DB = -15.0
SILENT_DB = -50.0


def db(x):
    return 20 * np.log10(np.maximum(x, 1e-9))


def check(model, path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(model.samplerate), "-"],
                         capture_output=True, check=True).stdout
    wav = torch.from_numpy(np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).T.copy())
    ref = wav.mean(0)
    x = (wav - ref.mean()) / (ref.std() + 1e-8)
    with torch.inference_mode():
        stems = apply_model(model, x[None].cuda(), device="cuda", split=True, overlap=0.25, progress=False)[0]
    stems = stems * (ref.std() + 1e-8) + ref.mean()
    vocals = stems[model.sources.index("vocals")].mean(0).cpu().numpy()
    mix = wav.mean(0).numpy()
    n = int(WINDOW_S * model.samplerate)
    k = len(mix) // n
    rms = lambda a: np.sqrt((a[: k * n].reshape(k, n) ** 2).mean(1))
    v, m = rms(vocals), rms(mix)
    active = db(m) > SILENT_DB + db(m.max())
    rel = db(v[active]) - db(m[active])
    return dict(
        file=path,
        vocal_to_mix_db=round(float(db(np.sqrt((vocals ** 2).mean())) - db(np.sqrt((mix ** 2).mean()))), 1),
        median_window_db=round(float(np.median(rel)), 1),
        prominent_vocal_share=round(float((rel > PROMINENT_DB).mean()), 3),
    )


if __name__ == "__main__":
    model = get_model("htdemucs").cuda().eval()
    print(json.dumps([check(model, p) for p in sys.argv[1:]], indent=2))

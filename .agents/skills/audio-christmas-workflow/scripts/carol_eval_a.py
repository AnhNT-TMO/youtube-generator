import glob
import json
import os
import subprocess
import sys

import numpy as np
import torch

sys.path.insert(0, os.path.expanduser("~/ace-step"))
from harsh import analyse
from seed_diff import features, tolerant
from ref_eval import SR, Clap, decode

REF_DIR = os.path.expanduser("~/ace-step/ref/christmas-relax")
REF_TRACKS = os.path.expanduser("~/ace-step/out/refsplit")
REF_CACHE = os.path.join(REF_TRACKS, "ref_tracks_clap.pt")


def decode48(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", "48000", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).astype(np.float64)


def buzz(x):
    m = x.mean(1)
    win = 48000 * 5
    shares, energy = [], []
    f = np.fft.rfftfreq(win, 1 / 48000)
    for i in range(0, len(m) - win, win):
        spec = np.abs(np.fft.rfft(m[i:i + win] * np.hanning(win))) ** 2
        energy.append(spec.sum())
        shares.append(10 * np.log10(spec[(f > 2000) & (f < 6000)].sum() / spec.sum()))
    inner = list(zip(shares, energy))[1:-2] or list(zip(shares, energy))
    loud = [s for s, e in inner if e > max(energy) * 1e-3]
    return float(np.median(loud)), float(max(loud))


def start_excess(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", "48000", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.float32)
    win = 4800
    n = len(x) // win
    frames = x[: n * win].reshape(n, win) * np.hanning(win)
    spec = np.abs(np.fft.rfft(frames, axis=1)) ** 2
    f = np.fft.rfftfreq(win, 1 / 48000)
    band = 10 * np.log10(spec[:, (f >= 3000) & (f < 10000)].sum(1) + 1e-12)
    total = 10 * np.log10(spec.sum(1) + 1e-12)
    active = total > total.max() - 40
    return round(float(band[:50][active[:50]].max() - np.percentile(band[active], 95)), 1) if active[:50].any() else None


def main(song_dir):
    from audiobox_aesthetics.infer import initialize_predictor
    clap = Clap()
    aes = initialize_predictor()
    chan = torch.load(os.path.join(REF_DIR, "channel-clap-centroid.pt")).cpu()
    tl = json.load(open(os.path.join(REF_DIR, "timeline-MdYsx0ZGqoQ.json")))
    video = torch.nn.functional.normalize(torch.tensor([r["emb"] for r in tl]).mean(0), dim=0)
    if os.path.exists(REF_CACHE):
        refs = torch.load(REF_CACHE)
    else:
        refs = {os.path.basename(p)[:-4]: torch.nn.functional.normalize(clap.embed_audio(decode(p)).mean(0), dim=0).cpu()
                for p in sorted(glob.glob(os.path.join(REF_TRACKS, "*_t*.wav")))}
        torch.save(refs, REF_CACHE)
    names = list(refs)
    ref_mat = torch.stack([refs[n] for n in names])
    out_path = os.path.join(song_dir, "eval_a.json")
    rows = json.load(open(out_path)) if os.path.exists(out_path) else {}
    src_feats = {}
    files = []
    for pat in ("src_*.wav", "vsrc_*.wav", "cov_*.flac", "vcov_*.flac"):
        files += glob.glob(os.path.join(song_dir, pat))
    for f in sorted(files):
        name = os.path.basename(f)
        if name in rows:
            continue
        variant = name.split("_")[1][0]
        melody_copy = None
        if name.startswith(("cov_", "vcov_")):
            key = ("v" if name.startswith("vcov_") else "") + variant
            src = os.path.join(song_dir, ("vsrc" if key.startswith("v") else "src") + f"_{variant}.wav")
            if key not in src_feats and os.path.exists(src):
                src_feats[key] = features(src)
            if key in src_feats:
                melody_copy = round(float(tolerant(src_feats[key], features(f))["sim"]), 3)
        wav = decode(f)
        emb = torch.nn.functional.normalize(clap.embed_audio(wav).mean(0), dim=0).cpu()
        sims = (ref_mat @ emb).numpy()
        sc = aes.forward([{"path": wav, "sample_rate": SR}])[0]
        x = decode48(f)
        bm, bx = buzz(x)
        h = analyse(f)
        rows[name] = dict(seconds=round(len(x) / 48000, 1), vibe_video=round(float(emb @ video), 3), vibe_channel=round(float(emb @ chan), 3),
                          CE=round(sc["CE"], 2), PQ=round(sc["PQ"], 2), PC=round(sc["PC"], 2), buzz_median_db=round(bm, 1),
                          buzz_max_db=round(bx, 1), hf_first5s_db=h["hf_first5s_vs_median_db"], spikes_per_min=h["spikes_per_min"],
                          copy_max_sim=round(float(sims.max()), 3), copy_nearest=names[int(sims.argmax())], melody_copy=melody_copy, hf_start_excess_db=start_excess(f))
    json.dump(rows, open(out_path, "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1])

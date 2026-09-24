#!/usr/bin/env python3
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import warnings

import numpy as np

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))

AST_KEEP = {"Male singing", "Female singing", "Singing", "Humming", "Speech"}


def qc_path(arg):
    repo = os.path.join(HERE, "..", "..", "..", "..")
    for p in (arg, os.environ.get("QC_TOOLS"), os.path.join(repo, ".claude", "skills", "verification-audio", "scripts"),
              os.path.expanduser("~/youtube-qc/.claude/skills/verification-audio/scripts")):
        if p and os.path.isdir(os.path.join(p, "qc")):
            return os.path.abspath(p)
    sys.exit("verification-audio scripts/qc not found: pass --qc-tools or set QC_TOOLS")


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def cut_songs(run, tracks, audio):
    d = os.path.join(run, "raw", "songs")
    os.makedirs(d, exist_ok=True)
    idx = os.path.join(d, "index.json")
    bounds = {"video": os.path.basename(audio) + ":" + str(os.path.getsize(audio)), "starts": [t["start_s"] for t in tracks]}
    if not os.path.exists(idx) or json.load(open(idx)) != bounds:
        for f in glob.glob(os.path.join(d, "*.wav")):
            os.remove(f)
        json.dump(bounds, open(idx, "w"))
    paths = []
    for i, t in enumerate(tracks):
        p = os.path.join(d, f"{i + 1:02d}.wav")
        end = tracks[i + 1]["start_s"] if i + 1 < len(tracks) else None
        if not os.path.exists(p):
            cmd = ["ffmpeg", "-v", "error", "-y", "-ss", str(t["start_s"])]
            if end is not None:
                cmd += ["-t", str(end - t["start_s"])]
            subprocess.run(cmd + ["-i", audio, "-ac", "2", "-ar", "44100", p], check=True)
        paths.append(p)
    return paths


_ast = None


def ast_tags(y16, starts, win=10):
    global _ast
    import torch
    from transformers import ASTFeatureExtractor, ASTForAudioClassification
    if _ast is None:
        name = "MIT/ast-finetuned-audioset-10-10-0.4593"
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        _ast = (ASTFeatureExtractor.from_pretrained(name), ASTForAudioClassification.from_pretrained(name).eval().to(dev))
    fe, m = _ast
    wins = [y16[int(s * 16000): int((s + win) * 16000)] for s in starts]
    wins = [w for w in wins if len(w) > 16000 * min(3, win * 0.6)]
    if not wins:
        return {}
    probs = []
    for i in range(0, len(wins), 8):
        x = fe(wins[i:i + 8], sampling_rate=16000, return_tensors="pt").to(m.device)
        with torch.no_grad():
            probs.append(torch.sigmoid(m(**x).logits).cpu().numpy())
    p = np.concatenate(probs).mean(0)
    lab = m.config.id2label
    return {lab[i]: round(float(p[i]), 3) for i in np.argsort(-p) if lab[i] in AST_KEEP and p[i] >= 0.02}


def lyric_numbers(path):
    from qc import lyrics, stems
    v, sr = stems.load_stem(path, "vocals", sr=16000)
    res = lyrics._transcribe(v.astype(np.float32), language="en", word_timestamps=True,
                             condition_on_previous_text=False, hallucination_silence_threshold=2.0, verbose=None)

    def rms_db(a, b):
        x = v[int(max(0, a) * sr): max(int(max(0, a) * sr) + 1, int(b * sr))]
        return 10 * np.log10(float(np.mean(x.astype(np.float64) ** 2)) + 1e-12)
    blk = int(0.5 * sr)
    lv = 10 * np.log10((v[: len(v) // blk * blk].astype(np.float64).reshape(-1, blk) ** 2).mean(1) + 1e-12)
    floor = float(np.percentile(lv, 90)) - 25
    segs = []
    for s in res.get("segments", []):
        if s.get("no_speech_prob", 0) >= 0.6 or not s["text"].strip():
            continue
        ws = [w for w in s.get("words") or [] if rms_db(w["start"] - 0.2, w["end"] + 0.2) > floor]
        if not ws and rms_db(s["start"], s["end"]) <= floor:
            continue
        a0, b0 = (ws[0]["start"], ws[-1]["end"]) if ws else (s["start"], s["end"])
        segs.append((a0, b0, re.sub(r"[^a-z' ]", " ", s["text"].lower()).split()))
    segs = [s for s in segs if len(s[2]) >= 2]
    if not segs:
        return {"words": 0}
    words = sum(len(w) for _, _, w in segs)
    return {"first_word_s": round(segs[0][0], 1), "words": words,
            "words_per_min_sung": round(words / max(1.0, segs[-1][1] - segs[0][0]) * 60, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--no-lyrics", action="store_true")
    ap.add_argument("--qc-tools")
    a = ap.parse_args()
    sys.path.insert(0, qc_path(a.qc_tools))
    from qc import pipeline, tempo
    from qc.common import load_array, load_audio

    A = json.load(open(os.path.join(a.run, "audio", "analysis.json")))
    audio = [f for f in sorted(glob.glob(os.path.join(a.run, "raw", "audio.*"))) if not f.endswith((".video_id", ".part"))][0]
    tracks = A["tracks"]
    log(f"cutting {len(tracks)} songs ...")
    paths = cut_songs(a.run, tracks, audio)
    log(f"qc modules (beat_this, Demucs, pYIN) on {len(paths)} songs ...")
    feats = pipeline.analyze_many(paths, ("rhythm", "stems", "tempo", "vocal"), verbose=True)

    def felt(p, rhythm):
        ac = load_array(p, "tempo_ac")
        if ac is None:
            return None, {}
        bar_s = 60 / rhythm["bar_bpm"] if rhythm and rhythm.get("bar_bpm") else None
        st = tempo.structural_felt(ac, bar_s)
        if st["bpm"]:
            info = {"meter": st["meter"], "uncertain": False}
        else:
            b, _ = tempo.pulse(ac, 45, 100)
            st, info = {"bpm": b}, {"meter": None, "uncertain": True}
        if info["meter"] != "compound":
            f, cf = tempo.pulse(ac, 100, 180)
            _, cs = tempo.pulse(ac, 45, 100)
            if f and cf is not None and cs is not None and cf >= 0.9 * cs:
                info["fast_candidate"] = round(f, 1)
        return (round(st["bpm"], 1) if st["bpm"] else None), info

    songs = []
    for i, (t, p) in enumerate(zip(tracks, paths)):
        f = feats[p]
        fb, fi = felt(p, f["rhythm"])
        v = f["vocal"]
        y16, _ = load_audio(p, sr=16000)
        dur = len(y16) / 16000
        from qc import stems
        vst, _ = stems.load_stem(p, "vocals", sr=16000)
        vt = ast_tags(vst, [x for x in (20, 60, 100, 140) if x + 10 < dur] or [0])
        m_, f_ = vt.get("Male singing", 0), vt.get("Female singing", 0)
        songs.append({
            "n": i + 1, "title": t.get("title"), "start_s": t["start_s"], "duration_s": round(dur, 1),
            "felt_bpm": fb, "meter": fi.get("meter"), "tempo_uncertain": fi.get("uncertain"),
            "felt_bpm_fast_candidate": fi.get("fast_candidate"),
            "f0_median_hz": None if v.get("f0_median_hz") is None else round(v["f0_median_hz"]),
            "voice": "male" if m_ > 1.5 * f_ and m_ >= 0.05 else "female" if f_ > 1.5 * m_ and f_ >= 0.05 else "unclear",
        })
        s = songs[-1]
        log(f"  song {i + 1}: felt {fb} {s['meter']} · f0 {s['f0_median_hz']} Hz · {s['voice']}")

    v1 = feats[paths[0]]["vocal"].get("vocal_start")
    track01 = {"vocal_start_s": None if v1 is None else round(v1, 1)}
    if not a.no_lyrics:
        try:
            track01["lyrics"] = lyric_numbers(paths[0])
        except Exception as e:
            track01["lyrics"] = {"error": str(e)[:120]}

    def med(key):
        v = [s[key] for s in songs if s.get(key) is not None]
        return round(float(np.median(v)), 1) if v else None
    album = {
        "felt_bpm_median": med("felt_bpm"),
        "felt_bpm_range": [min((s["felt_bpm"] for s in songs if s["felt_bpm"]), default=None),
                           max((s["felt_bpm"] for s in songs if s["felt_bpm"]), default=None)],
        "meter_counts": {k: sum(s["meter"] == k for s in songs) for k in ("compound", "simple")},
        "tempo_uncertain_songs": [s["n"] for s in songs if s.get("tempo_uncertain")],
        "f0_median_hz": med("f0_median_hz"),
        "voice_calls": {g: sum(s["voice"] == g for s in songs) for g in ("male", "female", "unclear")},
    }
    out = {"bounds_s": [t["start_s"] for t in tracks],
           "_about": "verification-audio qc: felt_bpm = qc.tempo.structural_felt (compound -> dotted quarter, simple -> quarter); "
                     "vocal_start_s = first sung run >= 1.5 s on the Demucs vocal stem (hums included); f0 = pYIN on that stem; "
                     "voice = AudioSet Male/Female singing on that stem; lyrics = Whisper numbers, no text kept.",
           "songs": songs, "album": album, "track01": track01}
    json.dump(out, open(os.path.join(a.run, "audio", "qc.json"), "w"), indent=1, ensure_ascii=False, default=float)
    log("done -> audio/qc.json")


if __name__ == "__main__":
    main()

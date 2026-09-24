from __future__ import annotations

import re
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np

from . import stems
from .common import load_cached, save_cached

MODEL = "mlx-community/whisper-large-v3-turbo"
MODEL_TORCH = "turbo"
_torch_model = None


def _transcribe(v: np.ndarray, **kw) -> dict:
    global _torch_model
    try:
        import mlx_whisper
        return mlx_whisper.transcribe(v, path_or_hf_repo=MODEL, **kw)
    except ImportError:
        import whisper
        from .common import device
        if _torch_model is None:
            _torch_model = whisper.load_model(MODEL_TORCH, device=device())
        return _torch_model.transcribe(v, fp16=device() == "cuda", **kw)


def analyze(path, force=False) -> dict:
    if not force and (c := load_cached(path, "lyrics")):
        return c
    v, sr = stems.load_stem(path, "vocals", sr=16000)
    res = _transcribe(
        v.astype(np.float32), language="en", word_timestamps=True,
        condition_on_previous_text=False, hallucination_silence_threshold=2.0, verbose=None)
    segs = [{"start": s["start"], "end": s["end"], "text": s["text"].strip(),
             "avg_logprob": s["avg_logprob"], "no_speech_prob": s["no_speech_prob"]}
            for s in res["segments"]]
    words = [{"w": w["word"].strip(), "s": w["start"], "e": w["end"], "p": w.get("probability")}
             for s in res["segments"] for w in s.get("words", [])]
    out = {"text": res["text"].strip(), "segments": segs, "words": words}
    if words:
        probs = np.array([w["p"] for w in words if w["p"] is not None])
        out["word_prob_mean"] = float(probs.mean()) if len(probs) else None
        out["low_conf_word_ratio"] = float(np.mean(probs < 0.4)) if len(probs) else None
        out["first_word_time"] = float(words[0]["s"])
        out["last_word_time"] = float(words[-1]["e"])
    return save_cached(path, "lyrics", out)


def read_lyrics(track_md: Path) -> str | None:
    if not track_md.exists():
        return None
    text = track_md.read_text()
    m = re.search(r"^##\s+Lyrics.*?$(.*)", text, re.M | re.S)
    if not m:
        return None
    b = re.search(r"```[a-z]*\n(.*?)```", m.group(1), re.S)
    if not b or len(b.group(1).strip().splitlines()) < 4:
        return None
    return b.group(1)


_TAG = re.compile(r"^\s*\[.*\]\s*$")


def expected_lines(lyrics_block: str) -> list[str]:
    lines, in_instr = [], False
    for raw in lyrics_block.splitlines():
        line = raw.strip()
        if not line:
            continue
        if _TAG.match(line):
            tag = line.lower()
            in_instr = any(k in tag for k in ("instrumental", "intro", "outro", "break", "solo", "interlude"))
            continue
        if in_instr:
            continue
        if _looks_like_direction(line):
            continue
        lines.append(line)
    return lines


_DIRECTION_WORDS = ("enters", "keep the", "gradually", "no additional", "no dramatic", "let the", "leave only",
                    "organ", "guitar", "choir", "drums", "piano", "vocal", "harmony", "sustain", "unhurried")


def _looks_like_direction(line: str) -> bool:
    low = line.lower()
    return line.endswith(".") and any(w in low for w in _DIRECTION_WORDS)


def norm_tokens(text: str) -> list[str]:
    text = text.lower().replace("’", "'")
    text = re.sub(r"[^a-z' ]+", " ", text)
    return [t for t in text.split() if t]


def compare(expected_block: str, transcript_words: list[str]) -> dict:
    lines = expected_lines(expected_block)
    hyp = norm_tokens(" ".join(transcript_words))
    if not lines:
        return {"n_lines": 0}
    vocab = set(t for l in lines for t in norm_tokens(l))
    found, per_line = 0, []
    uniq = list(dict.fromkeys(lines))
    for line in uniq:
        toks = norm_tokens(line)
        n = len(toks)
        best = 0.0
        for i in range(0, max(1, len(hyp) - n + 1)):
            win = hyp[i:i + n + 2]
            r = SequenceMatcher(None, toks, win).ratio()
            if r > best:
                best = r
                if best > 0.95:
                    break
        per_line.append((line, round(best, 2)))
        found += best >= 0.6
    precision = float(np.mean([t in vocab for t in hyp])) if hyp else 0.0
    return {"n_lines": len(uniq), "coverage": found / len(uniq), "precision": precision,
            "missing_lines": [l for l, s in per_line if s < 0.6], "n_hyp_words": len(hyp)}

#!/usr/bin/env python
import argparse
import json
from pathlib import Path

import torch
import whisper

MODEL = "turbo"
SR = 16000


def main():
    ap = argparse.ArgumentParser(description="Whisper word timestamps for song clips (GPU server, one model load)")
    ap.add_argument("--out", required=True, help="thư mục ghi <stem>.json")
    ap.add_argument("wavs", nargs="+")
    a = ap.parse_args()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = whisper.load_model(MODEL, device=device)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for wav in map(Path, a.wavs):
        audio = whisper.load_audio(str(wav))
        res = model.transcribe(audio, language="en", word_timestamps=True, condition_on_previous_text=False,
                               hallucination_silence_threshold=2.0, fp16=device == "cuda", verbose=None)
        words = [{"w": w["word"].strip(), "s": round(float(w["start"]), 3), "e": round(float(w["end"]), 3),
                  "p": round(float(w.get("probability") or 0.0), 3)}
                 for seg in res["segments"] for w in seg.get("words", [])]
        segments = [{"start": round(float(s["start"]), 3), "end": round(float(s["end"]), 3), "text": s["text"].strip()}
                    for s in res["segments"]]
        data = {"clip": wav.stem, "file_size": wav.stat().st_size, "model": MODEL, "whisper": whisper.__version__,
                "device": device, "audio_s": round(len(audio) / SR, 3), "words": words, "segments": segments}
        (out / f"{wav.stem}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1))
        first = f"{words[0]['s']:.1f} s" if words else "—"
        print(f"{wav.stem}: {len(words)} chữ, chữ đầu {first}", flush=True)


if __name__ == "__main__":
    main()

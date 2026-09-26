#!/usr/bin/env python3
import argparse
import sys
import wave
from pathlib import Path

import numpy as np

SR = 44100
PARTIALS = [(1.0, 1.0), (2.0, 0.45), (3.0, 0.2), (4.0, 0.1)]


def notes_from_score(path: Path, parts: str):
    from music21 import converter, tempo
    score = converter.parse(str(path))
    chosen = score.parts if parts == "all" else score.parts[:1]
    marks = score.flatten().getElementsByClass(tempo.MetronomeMark)
    src_bpm = float(marks[0].getQuarterBPM()) if marks else None
    out = []
    for part in chosen:
        for n in part.flatten().notesAndRests:
            if n.isRest:
                continue
            pitches = [p.frequency for p in (n.pitches if n.isChord else [n.pitch])]
            out.append((float(n.offset), float(n.quarterLength), pitches))
    if not out:
        sys.exit(f"no notes in {path}")
    return out, src_bpm


def render(notes, bpm: float, transpose: int, gain: float) -> np.ndarray:
    beat = 60.0 / bpm
    end = max(o + d for o, d, _ in notes) * beat + 1.5
    buf = np.zeros(int(end * SR) + 1, dtype=np.float64)
    ratio = 2 ** (transpose / 12)
    for off, dur, freqs in notes:
        n = max(int(dur * beat * SR), 1)
        t = np.arange(n) / SR
        env = np.minimum(1.0, t / 0.03) * np.minimum(1.0, (n - np.arange(n)) / (0.08 * SR))
        tone = sum(a * np.sin(2 * np.pi * f * ratio * k * t) for f in freqs for k, a in PARTIALS)
        start = int(off * beat * SR)
        buf[start:start + n] += env * tone / max(len(freqs), 1)
    peak = np.max(np.abs(buf)) or 1.0
    return (buf / peak * gain).astype(np.float32)


def write_wav(path: Path, x: np.ndarray):
    data = (np.clip(x, -1, 1) * 32767).astype("<i2")
    stereo = np.stack([data, data], axis=1).reshape(-1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(stereo.tobytes())


def main():
    ap = argparse.ArgumentParser(description="Render a public-domain score (MIDI / MusicXML / ABC) into a plain organ-like WAV: "
                                             "the own_rendition source of a Suno Cover (CLAUDE.md §5)")
    ap.add_argument("score", help="score file of the PD tune (.mid, .musicxml/.mxl/.xml, .abc)")
    ap.add_argument("out", help="output .wav (usually <album>/notes/suno/sNN-cover-source.wav)")
    ap.add_argument("--bpm", type=float, required=True, help="quarter-note tempo to render at (the slot's planned tempo)")
    ap.add_argument("--transpose", type=int, default=0, help="semitones (to fit the Voice's range)")
    ap.add_argument("--parts", choices=["melody", "all"], default="all", help="melody = first part only; all = full harmony")
    ap.add_argument("--repeat", type=int, default=1, help="play the tune N times (one verse per pass)")
    ap.add_argument("--gain", type=float, default=0.8)
    a = ap.parse_args()
    notes, src_bpm = notes_from_score(Path(a.score), a.parts)
    span = max(o + d for o, d, _ in notes)
    notes = [(o + i * span, d, f) for i in range(a.repeat) for o, d, f in notes]
    x = render(notes, a.bpm, a.transpose, a.gain)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_wav(out, x)
    print(f"wrote {out} · {len(x) / SR:.1f} s · {len(notes)} notes · {a.bpm} BPM (score marks {src_bpm or '—'}) · "
          f"transpose {a.transpose:+d} · parts {a.parts} × {a.repeat}")


if __name__ == "__main__":
    main()

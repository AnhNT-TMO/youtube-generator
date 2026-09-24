from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml

from measure import basic, grid, key, stems, tempo, vocal
from measure.common import frame_rms_db, load_array, load_audio, probe

HOP = 0.1


@dataclass
class Track:
    no: int
    id: str
    title: str
    md: Path
    audio: Path
    energy: float | None
    arc_role: str | None
    target_bpm: float | None
    duration: float = 0.0
    sample_rate: int = 0
    lead_silence: float = 0.0
    content_end: float = 0.0
    end_type: str = ""
    lufs_i: float | None = None
    true_peak: float | None = None
    vocal_start: float = 0.0
    vocal_end: float = 0.0
    vocal_runs: list[tuple[float, float]] = field(default_factory=list)
    downbeats: np.ndarray = field(default_factory=lambda: np.array([]))
    beats: np.ndarray = field(default_factory=lambda: np.array([]))
    env_db: np.ndarray = field(default_factory=lambda: np.array([]))
    drums_db: np.ndarray = field(default_factory=lambda: np.array([]))
    body_db: float = 0.0
    drums_body_db: float = 0.0
    camelot: str | None = None
    ending_camelot: str | None = None
    bpm: float | None = None

    @property
    def intro_len(self) -> float:
        return self.vocal_start

    @property
    def outro_len(self) -> float:
        return self.content_end - self.vocal_end

    def level(self, t0: float, t1: float) -> float:
        a, b = int(max(0, t0) / HOP), max(int(max(0, t0) / HOP) + 1, int(t1 / HOP))
        return float(np.mean(self.env_db[a:b]) - self.body_db)

    def drums_level(self, t0: float, t1: float) -> float:
        a, b = int(max(0, t0) / HOP), max(int(max(0, t0) / HOP) + 1, int(t1 / HOP))
        return float(np.mean(self.drums_db[a:b]) - self.drums_body_db)

    def sings_between(self, t0: float, t1: float) -> bool:
        return any(a < t1 and b > t0 for a, b in self.vocal_runs)


def front_matter(md: Path) -> dict:
    text = md.read_text()
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    return yaml.safe_load(m.group(1)) if m else {}


def load_tracks(album: Path) -> list[Track]:
    tracks = []
    for md in sorted((album / "tracks").glob("*.md")):
        if "." in md.stem:
            continue
        fm = front_matter(md)
        if not fm.get("audio"):
            raise SystemExit(f"{md.name}: thiếu field `audio`")
        audio = album / fm["audio"]
        if not audio.exists():
            raise SystemExit(f"{md.name}: không thấy file audio {audio}")
        no = fm.get("track_no") or int(md.name[:2])
        tracks.append(Track(no=int(no), id=str(fm.get("id") or md.stem), title=str(fm.get("title") or md.stem),
                            md=md, audio=audio, energy=_num(fm.get("energy")), arc_role=fm.get("arc_role"),
                            target_bpm=_num(fm.get("bpm"))))
    tracks.sort(key=lambda t: t.no)
    nos = [t.no for t in tracks]
    if nos != list(range(1, len(tracks) + 1)):
        raise SystemExit(f"track_no phải liên tục 1..N, đang là {nos}")
    return tracks


def load_single(single: Path) -> tuple[Track, Path]:
    fm = front_matter(single / "single.md")
    if not fm.get("track"):
        raise SystemExit(f"{single / 'single.md'}: thiếu field `track` (đường dẫn tới tracks/NN-*.md của album gốc)")
    md = (single / fm["track"]).resolve()
    if not md.exists():
        raise SystemExit(f"không thấy {md}")
    t = front_matter(md)
    audio = md.parent.parent / t["audio"]
    if not audio.exists():
        raise SystemExit(f"{md.name}: không thấy file audio {audio}")
    track = Track(no=1, id=str(t.get("id") or md.stem), title=str(t.get("title") or md.stem), md=md, audio=audio,
                  energy=_num(t.get("energy")), arc_role=t.get("arc_role"), target_bpm=_num(t.get("bpm")))
    return track, Path(os.path.relpath(audio, single))


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def measure(tracks: list[Track], verbose=True) -> None:
    for t in tracks:
        if verbose:
            print(f"  {t.no:02d} {t.title}", flush=True)
        stems.ensure(t.audio)
        tempo.analyze(t.audio)
        b = basic.analyze(t.audio)
        t.duration, t.sample_rate = b["duration"], probe(t.audio)["sample_rate"]
        t.lead_silence, t.content_end, t.end_type = b["lead_silence"], b["content_end"], b["end_type"]
        t.lufs_i, t.true_peak = b.get("lufs_i"), b.get("true_peak")

        v, vsr = stems.load_stem(t.audio, "vocals", sr=16000)
        act = vocal.vocal_activity(v, vsr)
        runs = [(a * vocal.HOP, e * vocal.HOP) for a, e in vocal.runs(act)]
        real = [r for r in runs if r[1] - r[0] >= 1.5]
        t.vocal_runs = runs
        t.vocal_start = real[0][0] if real else t.lead_silence
        t.vocal_end = real[-1][1] if real else t.content_end

        g = grid.analyze(t.audio)
        t.beats, t.downbeats = g["beats"], g["downbeats"]

        y, sr = load_audio(t.audio, sr=22050)
        t.env_db, _ = frame_rms_db(y, sr, hop_s=HOP, win_s=0.4)
        d, _ = stems.load_stem(t.audio, "drums", sr=22050)
        t.drums_db, _ = frame_rms_db(d, sr, hop_s=HOP, win_s=0.4)
        body = slice(int(t.vocal_start / HOP), int(t.vocal_end / HOP))
        t.body_db = float(np.median(t.env_db[body]))
        t.drums_body_db = float(np.median(t.drums_db[body]))

        k = key.analyze(t.audio)
        t.camelot, t.ending_camelot = k.get("camelot"), k.get("ending_camelot")
        ac = load_array(t.audio, "tempo_ac")
        if ac is not None and t.target_bpm:
            t.bpm = tempo.felt(ac, t.target_bpm)["bpm"]


def segment_lufs(path: Path, t0: float, t1: float) -> float | None:
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-ss", f"{t0:.3f}", "-to", f"{t1:.3f}", "-i", str(path),
                          "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    m = re.search(r"I:\s+(-?[\d.]+) LUFS", err[err.rfind("Summary:"):])
    return float(m.group(1)) if m else None


def loudness_curve(path: Path) -> tuple[np.ndarray, np.ndarray]:
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af",
                          "ebur128=metadata=1,ametadata=mode=print:file=-", "-f", "null", "-"],
                         capture_output=True, text=True).stdout
    m = np.array([float(x) for x in re.findall(r"lavfi\.r128\.M=(-?[\d.]+)", out)])
    s = np.array([float(x) for x in re.findall(r"lavfi\.r128\.S=(-?[\d.]+)", out)])
    return m, s

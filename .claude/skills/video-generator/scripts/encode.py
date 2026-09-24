"""Shared encoding helpers: codec arguments and splitting work at keyframes.

Keyframes are forced every `gop_seconds` (scene-cut detection off), so any
multiple of gop_seconds is a clean place to cut, join or start decoding.
"""
import os
import subprocess

ENCODERS = ["x264", "nvenc", "videotoolbox"]


def codec_args(enc, fps, encoder=None):
    encoder = encoder or enc["encoder"]
    gop = enc["gop_seconds"]
    keys = ["-g", str(int(gop * fps)), "-force_key_frames", f"expr:gte(t,n_forced*{gop})"]
    if encoder == "nvenc":
        return ["-c:v", "h264_nvenc", "-preset", enc["nvenc_preset"], "-tune", "hq",
                "-rc", "vbr", "-cq", str(enc["nvenc_cq"]), "-b:v", "0",
                "-profile:v", "high", "-no-scenecut", "1"] + keys
    if encoder == "videotoolbox":
        return ["-c:v", "h264_videotoolbox", "-b:v", enc["vt_bitrate"],
                "-profile:v", "high"] + keys
    return ["-c:v", "libx264", "-preset", enc["preset"], "-crf", str(enc["crf"]),
            "-x264-params", enc["x264"] + ":open-gop=0:scenecut=0"] + keys


def plan_segments(start, dur, grid, jobs, offset=0.0):
    """Split [start, start+dur) into at most `jobs` near-equal runs whose inner
    cuts fall on offset + multiples of `grid` seconds (keyframes; the offset is
    an intro in front of the loop). [(start, dur), ...]"""
    end = start + dur
    cuts = [start]
    for j in range(1, jobs):
        c = offset + round((start + dur * j / jobs - offset) / grid) * grid
        if cuts[-1] + grid / 2 < c < end - grid / 2:
            cuts.append(c)
    cuts.append(end)
    return [(a, b - a) for a, b in zip(cuts, cuts[1:])]


def join(parts, out, extra_inputs=(), extra_args=()):
    """Concatenate same-codec video files without re-encoding."""
    lst = out + ".parts.txt"
    with open(lst, "w") as fh:
        fh.writelines(f"file '{os.path.abspath(p)}'\n" for p in parts)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", lst] + list(extra_inputs) + list(extra_args) + [out], check=True)
    os.remove(lst)

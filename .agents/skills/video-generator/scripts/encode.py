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
    threads = ["-threads", os.environ["VG_ENC_THREADS"]] if os.environ.get("VG_ENC_THREADS") else []
    return ["-c:v", "libx264", "-preset", enc["preset"], "-crf", str(enc["crf"]),
            "-x264-params", enc["x264"] + ":open-gop=0:scenecut=0"] + threads + keys


def share_threads(jobs):
    os.environ["VG_ENC_THREADS"] = str(max(2, (os.cpu_count() or 8) // max(1, jobs)))


def plan_segments(start, dur, grid, jobs, offset=0.0):
    end = start + dur
    cuts = [start]
    for j in range(1, jobs):
        c = offset + round((start + dur * j / jobs - offset) / grid) * grid
        if cuts[-1] + grid / 2 < c < end - grid / 2:
            cuts.append(c)
    cuts.append(end)
    return [(a, b - a) for a, b in zip(cuts, cuts[1:])]


def join(parts, out, extra_inputs=(), extra_args=()):
    lst = out + ".parts.txt"
    with open(lst, "w") as fh:
        fh.writelines(f"file '{os.path.abspath(p)}'\n" for p in parts)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", lst] + list(extra_inputs) + list(extra_args) + [out], check=True)
    os.remove(lst)

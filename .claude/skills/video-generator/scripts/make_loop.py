"""Render the seamless video loop for one image: light, particles, logo,
like/subscribe. Video only; extend.py adds the audio and the spectrum bars.

    python make_loop.py IMAGE.png OUT.mp4 --preset channel/<name>/video.json [--preset DIR/video.json]
    python make_loop.py IMAGE.png test.mp4 --preset ... --seconds 20     # quick look
    python make_loop.py IMAGE.png frame.png --preset ... --frame 30      # one still
    python make_loop.py IMAGE.png OUT.mp4 --preset ... --seam-check      # + OUT_seam.mp4
    python make_loop.py IMAGE.png OUT.mp4 --preset ... --jobs 8 --encoder nvenc
    python make_loop.py IMAGE.png OUT.mp4 --preset ... --intro-only      # just OUT_intro.mp4

When the preset's intro is enabled, the logo intro is rendered too, as
OUT_intro.mp4; extend.py picks it up from there.

With --jobs N the loop is cut at keyframes into N parts rendered by separate
processes, then joined without re-encoding. Every frame is a pure function of
its time, so the parts line up exactly.
"""
import argparse
import multiprocessing as mp
import os
import subprocess
import sys
import tempfile
import time

import config
import encode
from config import H, W


def encode_cmd(out, fps, enc, encoder, pix_fmt="rgb24"):
    vf = ["-vf", f"noise=alls={enc['grain']}:allf=t+u"] if enc["grain"] > 0 else []
    return (["ffmpeg", "-y", "-loglevel", "error",
             "-f", "rawvideo", "-pix_fmt", pix_fmt, "-s", f"{W}x{H}", "-r", str(fps),
             "-i", "-"] + vf + encode.codec_args(enc, fps, encoder)
            + ["-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart", out])


def render_part(job):
    """Render [start, start+dur) of the loop to `out`. Runs in a worker process."""
    image, preset, bars, encoder, start, dur, out, report = job
    cfg = config.load(preset)
    fps = cfg["fps"]
    scene = None
    # Opt-in (VG_GPU=1): the frame loop on the GPU (effects_gpu.py). Measured 2026-09-24, 5-min 4K loop, 16 parts:
    # CPU frames + NVENC 52 s; GPU frames + NV12 + NVENC 103-110 s: many processes time-slice one GPU, while the
    # CPU loop is cheap (~245 frames/s per core). NVENC/NVDEC already take the heavy part off the CPU.
    if os.environ.get("VG_GPU", "0") == "1":
        try:
            import effects_gpu
            if effects_gpu.available():
                scene = effects_gpu.GpuScene(image, cfg, bars=bars)
        except ImportError:                             # no torch (e.g. the Mac venv): CPU path below
            pass
    if scene is None:
        from effects import Scene
        scene = Scene(image, cfg, bars=bars)
    gpu = hasattr(scene, "frame_nv12")
    ff = subprocess.Popen(encode_cmd(out, fps, cfg["encode"], encoder, "nv12" if gpu else "rgb24"),
                          stdin=subprocess.PIPE)
    grab = scene.frame_nv12 if gpu else (lambda t: scene.frame(t).tobytes())
    n = int(round(dur * fps))
    t1 = time.time()
    for i in range(n):
        ff.stdin.write(grab(start + i / fps))
        if report and i % (fps * 30) == 0 and i:
            el = time.time() - t1
            print(f"  {i / fps:5.0f}s / {dur:.0f}s   {i / el:5.1f} fps   "
                  f"eta {(n - i) * el / i:4.0f}s", flush=True)
    ff.stdin.close()
    if ff.wait():
        raise RuntimeError(f"ffmpeg failed on part at {start}s")
    return out


def seam_check(loop_path, loop_seconds, around=4.0):
    """Two copies back to back, cut around the join: watch it for a jump."""
    out = os.path.splitext(loop_path)[0] + "_seam.mp4"
    lst = out + ".txt"
    with open(lst, "w") as fh:
        fh.write(f"file '{os.path.abspath(loop_path)}'\n" * 2)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", lst, "-ss", str(loop_seconds - around), "-t", str(2 * around),
                    "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", out], check=True)
    os.remove(lst)
    print(f"seam preview: {out} (join at {around:.0f}s)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("out")
    ap.add_argument("--preset", action="append",
                    help="config JSON layered over config.DEFAULTS; repeat for more layers "
                         "(channel video.json, then the idea's)")
    ap.add_argument("--seconds", type=float, help="render only this much (not seamless)")
    ap.add_argument("--start", type=float, default=0.0, help="loop time to start at")
    ap.add_argument("--frame", type=float, help="write the single frame at this time as PNG")
    ap.add_argument("--seam-check", action="store_true")
    ap.add_argument("--no-bars", action="store_true",
                    help="leave out the shade under the spectrum row (for extend --no-bars)")
    ap.add_argument("--jobs", type=int, default=1, help="parts rendered in parallel")
    ap.add_argument("--encoder", choices=encode.ENCODERS, help="overrides encode.encoder")
    ap.add_argument("--intro-only", action="store_true",
                    help="only (re)render the logo intro, <out>_intro.mp4")
    a = ap.parse_args()

    cfg = config.load(a.preset)
    fps, loop = cfg["fps"], cfg["loop_seconds"]
    bars = not a.no_bars
    t0 = time.time()

    if a.frame is not None:
        from PIL import Image
        from effects import Scene
        Image.fromarray(Scene(a.image, cfg, bars=bars).frame(a.frame)).save(a.out)
        print(a.out)
        return

    intro_out = os.path.splitext(a.out)[0] + "_intro.mp4"
    if cfg["intro"]["enabled"] and not a.seconds:
        import intro
        ctx = mp.get_context("spawn")
        ipool = ctx.Pool(1)                     # renders alongside the loop parts
        ijob = ipool.apply_async(intro.render, (a.image, a.preset, bars, a.encoder, intro_out))
    else:
        ipool = None
    if a.intro_only:
        if not ipool:
            sys.exit("intro is disabled in this preset")
        ijob.get()
        ipool.close()
        print(f"done {intro_out}")
        return

    if cfg["subscribe"]["enabled"]:
        from effects import subscribe_times
        ts = subscribe_times(cfg["subscribe"], loop)
        print("subscribe at " + ", ".join(f"{int(t) // 60}:{t % 60:04.1f}" for t in ts)
              + f" of every {loop}s loop", flush=True)
    dur = a.seconds if a.seconds else loop
    parts = encode.plan_segments(a.start, dur, cfg["encode"]["gop_seconds"], a.jobs)
    encode.share_threads(len(parts))
    if len(parts) == 1:
        render_part((a.image, a.preset, bars, a.encoder, a.start, dur, a.out, True))
    else:
        work = tempfile.mkdtemp(prefix="loop_")
        jobs = [(a.image, a.preset, bars, a.encoder, s, d,
                 os.path.join(work, f"part{i:02d}.mp4"), False)
                for i, (s, d) in enumerate(parts)]
        print(f"{len(parts)} parts of ~{dur / len(parts):.0f}s", flush=True)
        with mp.get_context("spawn").Pool(len(jobs)) as pool:
            outs = pool.map(render_part, jobs)
        encode.join(outs, a.out, extra_args=["-c", "copy", "-movflags", "+faststart"])
        for o in outs:
            os.remove(o)
        os.rmdir(work)
    print(f"done {a.out}: {int(round(dur * fps))} frames in {time.time() - t0:.0f}s",
          flush=True)
    if ipool:
        ijob.get()
        ipool.close()
        print(f"intro: {intro_out}", flush=True)
    if a.seam_check and not a.seconds:
        seam_check(a.out, loop)


if __name__ == "__main__":
    sys.exit(main())

import argparse
import math
import multiprocessing as mp
import os
import subprocess
import sys
import tempfile
import time

import config
import encode


def probe(path, entry, stream=None):
    cmd = ["ffprobe", "-v", "error"]
    if stream:
        cmd += ["-select_streams", stream]
    cmd += ["-show_entries", entry, "-of", "default=nw=1:nk=1", path]
    return subprocess.run(cmd, stdout=subprocess.PIPE, check=True, text=True).stdout.strip()


_done = None


def _init(counter):
    global _done
    _done = counter


def render_segment(job):
    import numpy as np
    import bars
    from intro import bars_gain
    loop, intro, D, preset, encoder, spec, seg_start, seg_dur, loop_len, work, idx = job
    cfg = config.load(preset)
    fps, enc = cfg["fps"], cfg["encode"]
    strip = bars.BarStrip(cfg["bars"])
    lst = os.path.join(work, f"list{idx}.txt")
    lt = seg_start - D
    with open(lst, "w") as fh:
        if lt < 0:
            fh.write(f"file '{os.path.abspath(intro)}'\n")
            off = key = 0.0
            copies = math.ceil((seg_dur + lt) / loop_len) + 1
            skip = seg_start
        else:
            off = lt % loop_len
            key = math.floor(off / enc["gop_seconds"]) * enc["gop_seconds"]
            copies = math.ceil((off + seg_dur) / loop_len) + 1
            skip = off - key
        for i in range(copies):
            fh.write(f"file '{os.path.abspath(loop)}'\n")
            if i == 0 and key > 0:
                fh.write(f"inpoint {key}\n")

    hw = ["-hwaccel", "cuda"] if (encoder or enc["encoder"]) == "nvenc" else []
    inputs, vin, n_in = hw + ["-f", "concat", "-safe", "0", "-i", lst], "0:v", 1
    pre = []
    if skip > 1e-6:
        pre = [f"[0:v]trim=start={skip:.4f},setpts=PTS-STARTPTS[bg]"]
        vin = "bg"
    inputs += ["-i", os.path.join(work, "gradient.png")]
    pre.append(f"[{n_in}:v]loop=loop=-1:size=1,setpts=N/{fps}/TB[grad]")
    n_in += 1
    inputs += ["-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{strip.w}x{strip.h}",
               "-r", str(fps), "-i", "-"]
    fc = ";".join(pre + [strip.filters(fps, vin, "grad", f"{n_in}:v", "v")])

    out = os.path.join(work, f"seg{idx:02d}.mp4")
    cmd = (["ffmpeg", "-y", "-loglevel", "error"] + inputs
           + ["-filter_complex", fc, "-map", "[v]", "-t", f"{seg_dur:.4f}", "-an"]
           + encode.codec_args(enc, fps, encoder) + ["-pix_fmt", "yuv420p", out])
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for i, row in enumerate(spec):
            m = strip.mask(row)
            t = seg_start + i / fps
            if intro and t < D:
                m = (m * bars_gain(t, cfg)).astype(np.uint8)
            ff.stdin.write(m.tobytes())
            if i % 300 == 299:
                with _done.get_lock():
                    _done.value += 300
        ff.stdin.close()
    except BrokenPipeError:
        pass
    if ff.wait():
        raise RuntimeError(f"segment {idx} failed")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("loop")
    ap.add_argument("audio")
    ap.add_argument("out")
    ap.add_argument("--preset", action="append",
                    help="same config layers the loop was made with (repeatable)")
    ap.add_argument("--no-bars", action="store_true", help="skip the spectrum row")
    ap.add_argument("--start", type=float, default=0.0, help="preview from this second")
    ap.add_argument("--seconds", type=float, help="preview only this long")
    ap.add_argument("--jobs", type=int, default=4, help="segments encoded in parallel")
    ap.add_argument("--encoder", choices=encode.ENCODERS, help="overrides encode.encoder")
    ap.add_argument("--intro", help="logo intro to put in front (default: LOOP_intro.mp4 "
                                    "when the preset enables it)")
    ap.add_argument("--no-intro", action="store_true")
    a = ap.parse_args()

    cfg = config.load(a.preset)
    fps = cfg["fps"]
    loop_len = float(probe(a.loop, "format=duration"))
    if abs(loop_len - cfg["loop_seconds"]) > 0.5:
        print(f"warning: loop is {loop_len:.1f}s, preset says {cfg['loop_seconds']}s",
              file=sys.stderr)
    total = float(probe(a.audio, "format=duration"))
    dur = a.seconds if a.seconds else total - a.start
    bars_on = cfg["bars"]["enabled"] and not a.no_bars

    intro = None
    if not a.no_intro:
        guess = os.path.splitext(a.loop)[0] + "_intro.mp4"
        intro = a.intro or (guess if cfg["intro"]["enabled"] else None)
        if intro and not os.path.exists(intro):
            print(f"warning: no intro at {intro}, starting straight on the loop",
                  file=sys.stderr)
            intro = None
    D = round(float(probe(intro, "format=duration")) * fps) / fps if intro else 0.0

    seek = ["-ss", str(a.start)] if a.start else []
    work = tempfile.mkdtemp(prefix="extend_")
    t0 = time.time()

    audio_in, aenc = a.audio, None
    if probe(a.audio, "stream=codec_name", "a:0") != "aac":
        audio_in = os.path.join(work, "audio.m4a")
        aenc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error"] + seek
                                + ["-i", a.audio, "-t", str(dur), "-vn", "-c:a", "aac",
                                   "-b:a", "320k", "-ar", "48000", audio_in])
        seek_audio = []
    else:
        seek_audio = seek

    def audio_ready():
        if aenc and aenc.wait():
            sys.exit("audio encode failed")

    if not bars_on:
        lst = os.path.join(work, "list.txt")
        with open(lst, "w") as fh:
            if intro:
                fh.write(f"file '{os.path.abspath(intro)}'\n")
            fh.write(f"file '{os.path.abspath(a.loop)}'\n"
                     * (math.ceil((a.start + dur - D) / loop_len) + 1))
        print(f"{dur / 60:.1f} min, bars off: joining {'intro + ' if intro else ''}loop copies",
              flush=True)
        audio_ready()
        cmd = (["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0"]
               + seek + ["-i", lst] + seek_audio + ["-i", audio_in, "-t", str(dur),
               "-map", "0:v", "-map", "1:a", "-c", "copy", "-movflags", "+faststart", a.out])
        subprocess.run(cmd, check=True)
    else:
        import bars
        n = int(round(dur * fps))
        spec = bars.spectrum_track(bars.load_audio(a.audio, a.start, dur), n, fps, cfg["bars"])
        bars.BarStrip(cfg["bars"]).gradient().save(os.path.join(work, "gradient.png"))

        gop = cfg["encode"]["gop_seconds"]
        grid = gop if cfg["loop_seconds"] % gop == 0 else loop_len
        segs = encode.plan_segments(a.start, dur, grid, a.jobs, offset=D)
        encode.share_threads(len(segs))
        print(f"{dur / 60:.1f} min, spectrum ready ({time.time() - t0:.0f}s), "
              f"{len(segs)} segment(s) of ~{dur / len(segs) / 60:.1f} min", flush=True)
        jobs = []
        for i, (s, d) in enumerate(segs):
            f0 = int(round((s - a.start) * fps))
            jobs.append((a.loop, intro, D, a.preset, a.encoder,
                         spec[f0:f0 + int(round(d * fps))], s, d, loop_len, work, i))

        ctx = mp.get_context("spawn")
        counter = ctx.Value("l", 0)
        t1 = time.time()
        with ctx.Pool(len(jobs), _init, (counter,)) as pool:
            res = pool.map_async(render_segment, jobs)
            while not res.ready():
                res.wait(15)
                done, el = counter.value, time.time() - t1
                if done and not res.ready():
                    print(f"  {done / fps / 60:5.1f} / {n / fps / 60:.1f} min   "
                          f"{done / el:4.0f} fps   eta {(n - done) * el / done / 60:4.1f} min",
                          flush=True)
            outs = res.get()
        print(f"segments done ({time.time() - t0:.0f}s), joining", flush=True)
        audio_ready()
        encode.join(outs, a.out, seek_audio + ["-i", audio_in],
                    ["-t", str(dur), "-map", "0:v", "-map", "1:a", "-c", "copy",
                     "-movflags", "+faststart"])

    for f in os.listdir(work):
        os.remove(os.path.join(work, f))
    os.rmdir(work)
    print(f"done {a.out} in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()

import json
import subprocess
import sys
from pathlib import Path

def build(job, root, audio_out=None):
    W, H = job.get("size", [1080, 1920])
    cuts = job["cuts"]
    xf = job.get("xfade", 0.8)
    head = job.get("head", 1.0)
    total = cuts[-1]
    clips = [] if audio_out else job["clips"]
    assert audio_out or len(clips) == len(cuts) - 1, "clips must match cut intervals"
    inputs, filters = [], []
    for i, c in enumerate(clips):
        seg = cuts[i + 1] - cuts[i]
        length = seg + (xf if i < len(clips) - 1 else 0) + (xf / 2 if i else 0)
        start = c.get("in", head)
        inputs += ["-ss", f"{start:.3f}", "-t", f"{length + 0.1:.3f}", "-i", str(root / c["file"])]
        filters.append(
            f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},fps=30,format=yuv420p,"
            f"setpts=PTS-STARTPTS,trim=duration={length:.3f}[v{i}]"
        )
    prev, offset = "v0", 0.0
    for i in range(1, len(clips)):
        offset = cuts[i] - xf / 2
        out = f"x{i}"
        filters.append(f"[{prev}][v{i}]xfade=transition=fade:duration={xf:.3f}:offset={offset:.3f}[{out}]")
        prev = out
    if not audio_out:
        filters.append(f"[{prev}]trim=duration={total:.3f}[base]")
    n = len(clips)
    a = job["audio"]
    inputs += ["-ss", f"{a['start']:.3f}", "-t", f"{total:.3f}", "-i", str(root / a["file"])]
    ai = n
    n += 1
    cur = "base"
    sfx = []
    for k, ov in enumerate(job["overlays"]):
        t0 = ov["t0"] if ov["t0"] >= 0 else total + ov["t0"]
        hold = ov["t1"] <= 0
        t1 = total if hold else ov["t1"]
        if ov.get("sfx"):
            hits = json.loads((root / ov["sfx"]["hits"]).read_text())["hits"]
            sfx.append((ov["sfx"], [(t0 + t, db) for t, db in hits]))
        if audio_out:
            continue
        fd = ov.get("fade", 0.35)
        seq = root / ov["file"].removesuffix(".png")
        if ov.get("seq") and seq.is_dir():
            inputs += ["-framerate", "30", "-i", str(seq / "%03d.png")]
            shift = f",setpts=PTS-STARTPTS+{t0:.3f}/TB"
        else:
            inputs += ["-loop", "1", "-t", f"{total:.3f}", "-i", str(root / ov["file"])]
            shift = ""
        fd_in = ov.get("fade_in", fd)
        fade_in = f",fade=t=in:st={t0:.3f}:d={fd_in:.3f}:alpha=1" if fd_in > 0 else ""
        fade_out = "" if hold else f",fade=t=out:st={t1 - fd:.3f}:d={fd:.3f}:alpha=1"
        filters.append(f"[{n}:v]format=rgba{shift}{fade_in}{fade_out}[o{k}]")
        bn = ov.get("bounce")
        y = f"'{bn['amp']}*abs(sin(PI*{bn['hz']}*(t-{t0:.3f})))'" if bn else "0"
        filters.append(f"[{cur}][o{k}]overlay=0:{y}:enable='between(t,{t0:.3f},{t1:.3f})':format=auto[c{k}]")
        cur = f"c{k}"
        n += 1
    fo = a.get("fade_out", 1.2)
    filters.append(
        f"[{ai}:a]atrim=duration={total:.3f},asetpts=PTS-STARTPTS,afade=t=in:st=0:d={a.get('fade_in', 0.25)},"
        f"afade=t=out:st={total - fo:.3f}:d={fo},loudnorm=I={a.get('lufs', -14)}:TP=-1.5:LRA=11,"
        f"volume={a.get('music_db', 0)}dB,aresample=48000[{'am' if sfx else 'aout'}]"
    )
    if sfx:
        voices = []
        for s, hits in sfx:
            files = s["file"] if isinstance(s["file"], list) else [s["file"]]
            for j, f in enumerate(files):
                mine = hits[j::len(files)]
                inputs += ["-i", str(root / f)]
                labels = [f"s{n}h{i}" for i in range(len(mine))]
                filters.append(f"[{n}:a]aresample=48000,asplit={len(mine)}" + "".join(f"[{l}i]" for l in labels))
                for l, (t, db) in zip(labels, mine):
                    ms = round(t * 1000)
                    filters.append(f"[{l}i]adelay={ms}|{ms},volume={s.get('gain_db', 0) + db:.1f}dB[{l}]")
                voices += labels
                n += 1
            starts = [t for t, db in hits if db == 0]
            for a in s.get("accents", []):
                at = [starts[r] for r in a["rings"]] if "rings" in a else starts
                inputs += ["-i", str(root / a["file"])]
                labels = [f"s{n}a{i}" for i in range(len(at))]
                filters.append(f"[{n}:a]aresample=48000,asplit={len(at)}" + "".join(f"[{l}i]" for l in labels))
                for l, t in zip(labels, at):
                    ms = round(max(0.0, t + a.get("offset", 0.0)) * 1000)
                    filters.append(f"[{l}i]adelay={ms}|{ms},volume={s.get('gain_db', 0) + a.get('gain_db', 0):.1f}dB[{l}]")
                voices += labels
                n += 1
        verb = next((s["reverb"] for s, _ in sfx if s.get("reverb")), None)
        bus = "".join(f"[{v}]" for v in voices) + f"amix=inputs={len(voices)}:normalize=0"
        if verb:
            inputs += ["-i", str(root / verb["ir"])]
            filters.append(bus + "[bus]")
            filters.append(f"[bus]asplit[bdry][bsend]")
            filters.append(f"[bsend][{n}:a]afir=gtype=-1:dry=1:wet=1,volume={verb.get('wet_db', -6)}dB[bwet]")
            filters.append("[bdry][bwet]amix=inputs=2:normalize=0,asplit[bkey][bmix]")
            n += 1
        else:
            filters.append(bus + ",asplit[bkey][bmix]")
        duck = job["audio"].get("duck", {"threshold": 0.125, "ratio": 2, "attack": 5, "release": 350})
        filters.append("[bkey]apad[bkeyp]")
        filters.append(f"[am][bkeyp]sidechaincompress=threshold={duck['threshold']}:ratio={duck['ratio']}:attack={duck['attack']}:release={duck['release']}[ducked]")
        filters.append("[ducked][bmix]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.8:level=false[aout]")
    if audio_out:
        return ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filters),
                "-map", "[aout]", "-c:a", "pcm_s16le", "-ar", "48000", "-t", f"{total:.3f}", str(audio_out)]
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *inputs,
           "-filter_complex", ";".join(filters), "-map", f"[{cur}]", "-map", "[aout]",
           "-c:v", job.get("vcodec", "h264_nvenc"), "-preset", "p6", "-cq", "18", "-b:v", "0",
           *job.get("vargs", []), "-pix_fmt", job.get("pix_fmt", "yuv420p"), "-r", "30", "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
           "-movflags", "+faststart", "-t", f"{total:.3f}", str(root / job["out"])]
    return cmd


def main():
    job_path = Path(sys.argv[1])
    job = json.loads(job_path.read_text())
    audio_out = sys.argv[sys.argv.index("--audio") + 1] if "--audio" in sys.argv else None
    cmd = build(job, job_path.parent, audio_out)
    if "--print" in sys.argv:
        print(" ".join(cmd))
        return
    subprocess.run(cmd, check=True)
    print("rendered", audio_out or job["out"])


if __name__ == "__main__":
    main()

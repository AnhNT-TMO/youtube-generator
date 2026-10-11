#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
REPO = SKILL.parents[2]
GUARD = REPO / ".claude/skills/pm-production/scripts/server_guard/guard.sh"
MEASURE_VERSION = 1
SKIP_FAMILIES = {"cozy-loop"}
LIBRARY_ROOT = "video_sources"


def env():
    cfg = {"VM_KEY": str(Path.home() / ".ssh/id_rsa"), "VM_DIR": "video-montage"}
    f = SKILL / "remote.env"
    if f.exists():
        for line in f.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                cfg[k.strip()] = os.path.expandvars(v.strip())
    cfg.update({k: v for k, v in os.environ.items() if k.startswith("VM_")})
    if "VM_REMOTE" not in cfg:
        sys.exit(f"set VM_REMOTE=user@host in {SKILL / 'remote.env'} (copy remote.env.example)")
    return cfg


def ssh_args(cfg):
    return ["ssh", "-i", cfg["VM_KEY"], "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", cfg["VM_REMOTE"]]


def ssh(cfg, cmd, check=True):
    return subprocess.run([*ssh_args(cfg), cmd], check=check)


def guarded(cfg, cmd):
    env_ = dict(os.environ, GUARD_REMOTE=cfg["VM_REMOTE"], GUARD_KEY=cfg["VM_KEY"])
    return subprocess.run(["bash", str(GUARD), "run", cmd], env=env_).returncode


def rsync(cfg, args):
    rsh = f"ssh -i {cfg['VM_KEY']} -o BatchMode=yes -o ConnectTimeout=10"
    subprocess.run(["rsync", "-a", "-e", rsh, *args], check=True)


def set_dir(name):
    d = REPO / name
    if not (d / "resource.json").exists():
        sys.exit(f"{d} is not a resource set (no resource.json)")
    return d


def library(name):
    lib = json.loads((set_dir(name) / "resource.json").read_text()).get("library")
    if not lib:
        sys.exit(f"{name}/resource.json has no \"library\" (folder name under ~/video_sources on the server)")
    return lib


def accepted(sdir):
    for card in sorted(sdir.glob("*/*/*.json")):
        if card.name == "shots.json":
            continue
        try:
            c = json.loads(card.read_text())
        except json.JSONDecodeError:
            continue
        v = c.get("video") or {}
        if v.get("status") != "ok":
            continue
        yield card, c, card.with_name(v.get("file") or f"{card.stem}.mp4")


def clip_id(card, sdir):
    return str(card.relative_to(sdir).with_suffix(""))


def src_stamp(mp4):
    st = mp4.stat()
    return {"size": st.st_size, "mtime": int(st.st_mtime)}


def is_fresh(c, mp4):
    m = c.get("measure") or {}
    if m.get("v") != MEASURE_VERSION or "luma" not in m:
        return False
    return not mp4.exists() or m.get("src") == src_stamp(mp4)


def stage(cfg, set_name, sdir, ids):
    rel = f"stage/{set_name}"
    dest = f"{cfg['VM_DIR']}/{rel}"
    lib = f"$HOME/{LIBRARY_ROOT}/{library(set_name)}"
    script = (f'd={shlex.quote(dest)}; lib="{lib}"; mkdir -p "$d"; while IFS= read -r c; do [ -n "$c" ] || continue; '
              f'if [ -f "$lib/$c.mp4" ]; then mkdir -p "$d/$(dirname "$c")" && ln -sfn "$lib/$c.mp4" "$d/$c.mp4"; '
              f'else echo "$c"; fi; done')
    out = subprocess.run([*ssh_args(cfg), script], input="\n".join(ids) + "\n", capture_output=True, text=True, check=True)
    missing = out.stdout.split()
    local = [c for c in missing if (sdir / f"{c}.mp4").exists()]
    if local:
        with tempfile.TemporaryDirectory() as tmp:
            lst = Path(tmp) / "files.txt"
            lst.write_text("\n".join(f"{c}.mp4" for c in local) + "\n")
            rsync(cfg, ["-W", f"--files-from={lst}", f"{sdir}/", f"{cfg['VM_REMOTE']}:{dest}/"])
    print(f"staged {len(ids) - len(missing)} clips from ~/{LIBRARY_ROOT}/{library(set_name)}, {len(local)} pushed from the Mac")
    return rel, [c for c in missing if c not in local]


def cmd_setup(a):
    cfg = env()
    rdir = cfg["VM_DIR"]
    ssh(cfg, f"mkdir -p {rdir}/scripts {rdir}/clips {rdir}/state {rdir}/out")
    rsync(cfg, [str(SKILL / "scripts/measure_server.py"), str(SKILL / "requirements-server.txt"),
                f"{cfg['VM_REMOTE']}:{rdir}/scripts/"])
    install = (f"cd {rdir} && (test -x .venv/bin/python || uv venv --python 3.12 .venv) && "
               f"VIRTUAL_ENV=.venv uv pip install --index-strategy unsafe-best-match "
               f"--extra-index-url https://download.pytorch.org/whl/cu128 -r scripts/requirements-server.txt")
    sys.exit(guarded(cfg, install))


def cmd_status(a):
    sdir = set_dir(a.set)
    fresh, stale = [], []
    for card, c, mp4 in accepted(sdir):
        (fresh if is_fresh(c, mp4) else stale).append(clip_id(card, sdir))
    print(json.dumps({"set": a.set, "accepted": len(fresh) + len(stale), "measured": len(fresh),
                      "to_measure": len(stale), "measure_version": MEASURE_VERSION}, indent=1))
    if a.list:
        print("\n".join(stale))


def cmd_measure(a):
    cfg = env()
    sdir = set_dir(a.set)
    rdir = cfg["VM_DIR"]
    clips = list(accepted(sdir))
    todo = [(card, c, mp4) for card, c, mp4 in clips if a.force or not is_fresh(c, mp4)]
    if a.limit:
        todo = todo[:a.limit]
    current = [clip_id(card, sdir) for card, _, _ in clips]
    print(f"{len(clips)} accepted clips, {len(todo)} to measure")
    root, gone = stage(cfg, a.set, sdir, [clip_id(card, sdir) for card, _, _ in todo]) if todo else (f"stage/{a.set}", [])
    if gone:
        print(f"warning: {len(gone)} clips neither upscaled on the server nor on the Mac, not measured: {', '.join(gone[:10])}")
    job = {"measure": [[cid, f"{cid}.mp4"] for cid in (clip_id(card, sdir) for card, _, _ in todo) if cid not in gone],
           "current": current}
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    safe = a.set.replace("/", "__")
    with tempfile.TemporaryDirectory() as tmp:
        jf = Path(tmp) / f"job-{stamp}.json"
        jf.write_text(json.dumps(job))
        rsync(cfg, [str(jf), str(SKILL / "scripts/measure_server.py"), f"{cfg['VM_REMOTE']}:{rdir}/scripts/"])
    out = f"out/measure-{safe}-{stamp}.json"
    run = (f"cd {rdir} && OMP_NUM_THREADS=2 MEASURE_TORCH_THREADS={a.torch_threads} .venv/bin/python scripts/measure_server.py "
           f"--root {shlex.quote(root)} --list scripts/job-{stamp}.json --store state/{shlex.quote(safe)}-embed.npz "
           f"--out {out} --jobs {a.jobs}")
    if guarded(cfg, run) != 0:
        sys.exit("server measure failed; check `guard.sh kills` before re-running")
    local = SKILL / "cache" / Path(out).name
    local.parent.mkdir(exist_ok=True)
    rsync(cfg, [f"{cfg['VM_REMOTE']}:{rdir}/{out}", str(local)])
    res = json.loads(local.read_text())
    write_cards(sdir, clips, res)
    print(json.dumps({"measured": len(res["measured"]), "errors": res["errors"],
                      "missing_embedding": len(res["missing_embedding"]),
                      "pair_sim_quantiles": res["pair_sim_quantiles"], "server_seconds": res["seconds"]}, indent=1))


def write_cards(sdir, clips, res):
    now = dt.datetime.now().isoformat(timespec="seconds")
    for card, c, mp4 in clips:
        cid = clip_id(card, sdir)
        m = dict(c.get("measure") or {})
        if cid in res["measured"]:
            m = {"v": MEASURE_VERSION, "src": src_stamp(mp4) if mp4.exists() else m.get("src"), "at": now,
                 **res["measured"][cid]}
        if not m:
            continue
        nb = res["neighbours"].get(cid)
        if nb:
            m.update(near=nb["near"], distinct=nb["distinct"], crowd=nb["crowd"], neighbours_at=now)
        c["measure"] = m
        card.write_text(json.dumps(c, ensure_ascii=False, indent=1) + "\n")


def load_clips(sdir):
    sys.path.insert(0, str(SKILL / "scripts"))
    from pick import Clip
    clips, stale = [], []
    for card, c, mp4 in accepted(sdir):
        cid = clip_id(card, sdir)
        if cid.split("/")[0] in SKIP_FAMILIES:
            continue
        if not is_fresh(c, mp4):
            stale.append(cid)
            continue
        clips.append(Clip(cid, c, mp4))
    return clips, stale


def cmd_pick(a):
    sys.path.insert(0, str(SKILL / "scripts"))
    import pick
    sdir = set_dir(a.set)
    clips, stale = load_clips(sdir)
    if stale:
        print(f"warning: {len(stale)} accepted clips not measured yet (run `montage.py measure`), left out")
    out = montage_dir(a)
    root = out.parent
    cast, hero, seq, checks, pool_n = pick.build(clips, sdir, root, a)
    out.mkdir(parents=True, exist_ok=True)
    doc = {
        "name": a.name, "set": a.set, "created": dt.datetime.now().isoformat(timespec="seconds"),
        "mood": a.mood, "lead": a.lead, "music": a.music,
        "params": {"cast": a.cast, "minutes": a.minutes, "xfade": a.xfade, "block_s": a.block, "seed": a.seed},
        "rules": pick.RULES, "pool": pool_n,
        "cast": [c.id for c in cast], "hero": [c.id for c in hero],
        "sequence": seq, "checks": checks,
    }
    (out / "montage.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    (out / "clips.txt").write_text("\n".join(str(c.mp4.relative_to(REPO)) for c in cast) + "\n")
    print(json.dumps({k: v for k, v in checks.items() if k != "unused_cast"}, ensure_ascii=False, indent=1))
    print(f"wrote {out / 'montage.json'} and {out / 'clips.txt'} ({len(cast)} clips)")


def montage_dir(a):
    if a.root:
        return REPO / a.root / a.name
    if a.channel:
        return REPO / "channel" / a.channel / "albums" / a.name
    sys.exit("give --channel <ch> (montage lives in channel/<ch>/albums/<name>/) or --root")


def cmd_preview(a):
    cfg = env()
    rdir = cfg["VM_DIR"]
    mdir = montage_dir(a)
    mj = mdir / "montage.json"
    if not mj.exists():
        sys.exit(f"no {mj}; run `montage.py pick {a.name}` first")
    doc = json.loads(mj.read_text())
    sdir = set_dir(doc["set"])
    root, gone = stage(cfg, doc["set"], sdir, doc["cast"])
    if gone:
        sys.exit(f"{len(gone)} cast clips neither upscaled on the server nor on the Mac: {', '.join(gone[:10])}")
    rsync(cfg, [str(mj), str(SKILL / "scripts/preview_server.py"), f"{cfg['VM_REMOTE']}:{rdir}/scripts/"])
    ssh(cfg, f"mkdir -p {rdir}/out/{shlex.quote(a.name)}")
    rel = f"out/{a.name}/preview-{'first' + str(a.first) + '-' if a.first else ''}{a.height}p.mp4"
    run = (f"cd {rdir} && OMP_NUM_THREADS=4 .venv/bin/python scripts/preview_server.py --montage scripts/montage.json "
           f"--root {shlex.quote(root)} --out {shlex.quote(rel)} --height {a.height} "
           f"--xfade {doc['params']['xfade']}" + (" --labels" if a.labels else "") + (f" --first {a.first}" if a.first else ""))
    if guarded(cfg, run) != 0:
        sys.exit("server preview render failed; check `guard.sh kills`")
    rsync(cfg, ["--progress", f"{cfg['VM_REMOTE']}:{rdir}/{rel}", str(mdir) + "/"])
    lines = []
    for i, s in enumerate(doc["sequence"], 1):
        t = int(s["start_s"])
        lines.append(f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}  {i:4d}  {s['clip']}{'  flip' if s['flip'] else ''}")
    (mdir / "timeline.txt").write_text("\n".join(lines) + "\n")
    print(f"wrote {mdir / Path(rel).name} and {mdir / 'timeline.txt'}")


RENDER_UNIT = "montage-render"
START_GUARD = ("systemctl --user is-active --quiet youtube-guard || systemd-run --user --unit=youtube-guard --collect "
               "-p MemoryMax=256M python3 ~/youtube-guard/guard.py >/dev/null 2>&1")


def cmd_render(a):
    cfg = env()
    rdir = cfg["VM_DIR"]
    mj = montage_dir(a) / "montage.json"
    if not mj.exists():
        sys.exit(f"no {mj}; run `montage.py pick {a.name}` first")
    doc = json.loads(mj.read_text())
    if ssh(cfg, f"systemctl --user is-active --quiet {RENDER_UNIT}", check=False).returncode == 0:
        sys.exit(f"{RENDER_UNIT} is already running on the server (`systemctl --user status {RENDER_UNIT}`)")
    ssh(cfg, f"mkdir -p {rdir}/out/{shlex.quote(a.name)} {rdir}/jobs")
    rsync(cfg, [str(mj), f"{cfg['VM_REMOTE']}:{rdir}/jobs/{a.name}.json"])
    rsync(cfg, [str(SKILL / "scripts/preview_server.py"), str(SKILL / "scripts/intro_server.py"),
                f"{cfg['VM_REMOTE']}:{rdir}/scripts/"])
    intro = ""
    if a.channel:
        cf = REPO / "channel" / a.channel / "intro.json"
        if not cf.exists():
            sys.exit(f"no {cf}")
        ic = json.loads(cf.read_text())
        a.intro_logo = a.intro_logo or ic["logo"]
        a.intro_title = a.intro_title or ic.get("title", "")
        a.intro_tagline = a.intro_tagline or ic.get("tagline", "")
        a.intro_font = ic.get("font", a.intro_font)
    if a.intro_logo:
        logo = REPO / a.intro_logo
        if not logo.exists():
            sys.exit(f"no {logo}")
        rsync(cfg, [str(logo), f"{cfg['VM_REMOTE']}:{rdir}/jobs/{a.name}-logo.png"])
        rsync(cfg, [str(SKILL / "fonts" / a.intro_font), f"{cfg['VM_REMOTE']}:{rdir}/jobs/"])
        intro = (f" --intro-logo jobs/{shlex.quote(a.name)}-logo.png --intro-font jobs/{shlex.quote(a.intro_font)}"
                 f" --intro-title {shlex.quote(a.intro_title)} --intro-tagline {shlex.quote(a.intro_tagline)}")
    out = f"out/{a.name}/{a.name}-{a.size.split('x')[1]}p-silent.mp4"
    log = f"out/{a.name}/render.log"
    render = (f".venv/bin/python -u scripts/preview_server.py --montage jobs/{shlex.quote(a.name)}.json "
              f"--root {shlex.quote(a.clips_root + '/' + library(doc['set']))} --out {shlex.quote(out)} --height {a.work_height} "
              f"--size {a.size} --hevc --cq {a.cq} --xfade {doc['params']['xfade']} --require-all "
              f"--wait-clips {a.wait_clips:g}{intro}")
    mux = ""
    if a.audio:
        final = f"out/{a.name}/{a.name}-{a.size.split('x')[1]}p.mp4"
        mux = (f" && test -s {shlex.quote(out)} && ffmpeg -nostdin -v error -y -i {shlex.quote(out)} -i {shlex.quote(a.audio)} "
               f"-map 0:v -map 1:a -c:v copy -c:a aac -b:a 320k -movflags +faststart {shlex.quote(final)} "
               f"&& echo \"$(date '+%T') muxed -> {final}\" >> {log}")
    wait = (f"while systemctl --user is-active --quiet {shlex.quote(a.after_unit)}; do sleep 60; done; "
            if a.after_unit else "")
    inner = (f"cd ~/{rdir} && echo \"== $(date '+%F %T') render {a.name}\" >> {log} && {wait}"
             f"echo \"$(date '+%T') start\" >> {log} && {START_GUARD}; "
             f"systemd-run --user --scope --quiet --collect --slice=youtube.slice --unit=montage-render-{a.name}-$$ "
             f"-- bash -c {shlex.quote('OMP_NUM_THREADS=4 ' + render + mux)} >> {log} 2>&1; "
             f"echo \"$(date '+%T') exit $?\" >> {log}")
    ssh(cfg, f"systemctl --user reset-failed {RENDER_UNIT} 2>/dev/null; systemd-run --user --unit={RENDER_UNIT} "
             f"--collect -p MemoryMax=1G bash -c {shlex.quote(inner)}")
    print(f"queued on the server ({'after ' + a.after_unit if a.after_unit else 'now'}): ~/{rdir}/{out}; "
          f"log ~/{rdir}/{log}; waits until every cast clip is upscaled"
          + (f", then muxes the audio -> out/{a.name}/{a.name}-{a.size.split('x')[1]}p.mp4" if a.audio else ""))


def main():
    ap = argparse.ArgumentParser(description="measure resource clips and build long-video montages (MONTAGE.md)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("setup", help="create the server dir + venv")
    p.set_defaults(fn=cmd_setup)
    p = sub.add_parser("status", help="how many accepted clips are measured / still to measure")
    p.add_argument("set", nargs="?", default="image_source")
    p.add_argument("--list", action="store_true", help="print the ids still to measure")
    p.set_defaults(fn=cmd_status)
    p = sub.add_parser("measure", help="measure every accepted clip not measured yet (server), write card.measure")
    p.add_argument("set", nargs="?", default="image_source")
    p.add_argument("--force", action="store_true", help="re-measure every clip")
    p.add_argument("--jobs", type=int, default=8, help="parallel decode processes on the server")
    p.add_argument("--torch-threads", type=int, default=8)
    p.add_argument("--limit", type=int, help="measure at most N clips (trial run)")
    p.set_defaults(fn=cmd_measure)
    p = sub.add_parser("pick", help="choose the cast + order of a long video (MONTAGE.md) -> montage.json, clips.txt")
    p.add_argument("name", help="montage folder name, e.g. 001-christmas-eve-home")
    p.add_argument("--set", default="image_source")
    p.add_argument("--channel", help="album folder channel/<ch>/albums/<name>/ holds montage.json + clips.txt")
    p.add_argument("--root", help="repo-relative folder holding every montage, instead of the channel's albums/")
    p.add_argument("--lead", required=True, help="lead family, or two adjacent ones joined by + (e.g. nature+travel)")
    p.add_argument("--mood", default="eve", choices=["eve", "indoor", "town", "winter", "morning"])
    p.add_argument("--cast", type=int, default=200)
    p.add_argument("--minutes", type=float, default=180, help="video length (= music master length once chosen)")
    p.add_argument("--xfade", type=float, default=1.0)
    p.add_argument("--block", type=float, default=210, help="seconds per scene block (= one song when music is set)")
    p.add_argument("--music", default="pending", help="music source note: pending / carol / suno")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--keep-cast", help="montage.json whose cast + hero to keep (re-sequence only, no new upscale)")
    p.set_defaults(fn=cmd_pick)
    p = sub.add_parser("preview", help="render a silent low-res review video of montage.json on the server + timeline.txt")
    p.add_argument("name")
    p.add_argument("--channel", help="album folder channel/<ch>/albums/<name>/")
    p.add_argument("--root")
    p.add_argument("--height", type=int, default=720)
    p.add_argument("--labels", action="store_true", help="burn clip id into the corner")
    p.add_argument("--first", type=int, help="render only the first N slots (e.g. the hero opening)")
    p.set_defaults(fn=cmd_preview)
    p = sub.add_parser("render", help="final video on the server from upscaled clips: waits until every cast clip is upscaled, compose 1080p, "
                                      "Lanczos to --size on the GPU, HEVC NVENC, optional --audio mux; stays on the server")
    p.add_argument("name")
    p.add_argument("--root")
    p.add_argument("--clips-root", default="../video_sources", help="server folder (relative to the montage dir) holding <library>/<clip id>.mp4; library = \"library\" in <set>/resource.json")
    p.add_argument("--work-height", type=int, default=1080)
    p.add_argument("--size", default="3840x2160")
    p.add_argument("--cq", type=int, default=24)
    p.add_argument("--channel", help="album folder channel/<ch>/albums/<name>/ + opening intro (logo, name, tagline, font) from channel/<ch>/intro.json")
    p.add_argument("--intro-logo", help="repo path of the channel's RGBA round logo: opening logo pop-up over clip 1")
    p.add_argument("--intro-title", default="", help="channel name drawn under the logo")
    p.add_argument("--intro-tagline", default="", help="small line under the name")
    p.add_argument("--intro-font", default="CormorantGaramond.ttf", help="font file in the skill's fonts/")
    p.add_argument("--after-unit", default="", help="also wait until this user unit ends first ('' = no)")
    p.add_argument("--wait-clips", type=float, default=300,
                   help="seconds between checks while cast clips are still being upscaled; renders once all exist (0 = exit if missing)")
    p.add_argument("--audio", help="server path (from ~/video-montage) of the album master: mux it as AAC 320k into <name>-<h>p.mp4")
    p.set_defaults(fn=cmd_render)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

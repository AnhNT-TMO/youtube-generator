#!/usr/bin/env python3
import argparse
import fnmatch
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TASKS = ROOT / "production" / "codex"
DEFAULT_MODEL = "cx/gpt-6.1-sol"
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", "cache", ".cache"}
ALWAYS_ALLOWED = ["production/codex/*"]


def task_dir(name):
    return TASKS / name


def load_meta(name):
    path = task_dir(name) / "meta.json"
    if not path.exists():
        sys.exit(f"no task {name} in {TASKS}")
    return json.loads(path.read_text())


def alive(pid):
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    try:
        out = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
    except OSError:
        return True
    return bool(out) and not out.startswith("Z")


def start(args):
    d = task_dir(args.task)
    if (d / "meta.json").exists() and alive(load_meta(args.task)["pid"]):
        sys.exit(f"task {args.task} is still running")
    d.mkdir(parents=True, exist_ok=True)
    brief = Path(args.brief).read_text()
    footer = (
        "\n\n## Task rules (PM)\n"
        f"- You are a worker. Task id: {args.task}. Write files only inside: "
        + ", ".join(args.allow + [f"production/codex/{args.task}/*"])
        + ". Anything else is out of scope: stop and say so in your final message.\n"
        f"- Append one progress line per finished item to production/codex/{args.task}/progress.md "
        "(`<item> | <result> | <one-line note>`), as you finish each one.\n"
        "- Your final message is your report to the PM: what you did per item, every doubt, "
        "every rule you could not follow and why. Do not claim work you did not do.\n"
    )
    (d / "brief.md").write_text(brief + footer)
    for f in ["log.jsonl", "err.log", "result.md", "progress.md"]:
        if (d / f).exists():
            (d / f).rename(d / f"{f}.{int(time.time())}.old")
    cmd = [
        "codex", "exec", "-m", args.model, "-c", f"model_reasoning_effort={args.effort}",
        "--dangerously-bypass-approvals-and-sandbox", "--skip-git-repo-check", "--json",
        "-o", str(d / "result.md"),
    ]
    for img in args.image:
        cmd += ["-i", str(Path(img).resolve())]
    cmd.append("-")
    with open(d / "brief.md") as stdin, open(d / "log.jsonl", "w") as out, open(d / "err.log", "w") as err:
        proc = subprocess.Popen(cmd, cwd=ROOT, stdin=stdin, stdout=out, stderr=err, start_new_session=True)
    meta = {"task": args.task, "pid": proc.pid, "started": time.time(), "model": args.model,
            "effort": args.effort, "allow": args.allow, "forbid": args.forbid, "images": args.image,
            "brief": str(Path(args.brief).resolve())}
    (d / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"started {args.task} pid {proc.pid} ({args.model}, {args.effort})")


def events(name):
    path = task_dir(name) / "log.jsonl"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(errors="replace").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return rows


def summary(name, tail):
    meta = load_meta(name)
    rows = events(name)
    run = alive(meta["pid"])
    mins = (time.time() - meta["started"]) / 60
    cmds = [r["item"] for r in rows if r.get("type") == "item.completed" and r["item"].get("type") == "command_execution"]
    msgs = [r["item"]["text"] for r in rows if r.get("type") == "item.completed" and r["item"].get("type") == "agent_message"]
    usage = [r["usage"] for r in rows if r.get("type") == "turn.completed"]
    failed = any(r.get("type") in ("turn.failed", "error") for r in rows)
    state = "RUNNING" if run else ("FAILED" if failed else "DONE")
    progress = task_dir(name) / "progress.md"
    nprog = len([l for l in progress.read_text().splitlines() if l.strip()]) if progress.exists() else 0
    print(f"== {name}: {state} {mins:.0f} min, {len(cmds)} commands, {nprog} progress lines")
    if usage:
        print(f"   tokens in {sum(u.get('input_tokens', 0) for u in usage)} out {sum(u.get('output_tokens', 0) for u in usage)}")
    for c in (cmds[-tail:] if tail else []):
        print(f"   $ {c.get('command', '')[:160]} -> {c.get('exit_code')}")
    for c in cmds:
        hit = next((f for f in meta.get("forbid", []) if re.search(f, c.get("command", ""))), None)
        if hit:
            print(f"   VIOLATION /{hit}/: {c.get('command', '')[:220]}")
    if msgs and tail:
        print(f"   says: {msgs[-1][:400]}")
    if failed:
        for r in rows:
            if r.get("type") in ("turn.failed", "error"):
                print(f"   error: {json.dumps(r)[:300]}")


def status(args):
    names = [args.task] if args.task else sorted(p.name for p in TASKS.iterdir() if (p / "meta.json").exists())
    for n in names:
        if args.running and not alive(load_meta(n)["pid"]):
            continue
        summary(n, args.tail)


def changed_files(since):
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            p = Path(dirpath) / f
            try:
                if p.stat().st_mtime >= since:
                    yield p.relative_to(ROOT).as_posix()
            except OSError:
                pass


def matches(path, globs):
    return any(fnmatch.fnmatch(path, g) for g in globs)


def audit(args):
    names = args.tasks or sorted(p.name for p in TASKS.iterdir() if (p / "meta.json").exists())
    metas = [load_meta(n) for n in names]
    if not metas:
        sys.exit("no tasks")
    since = min(m["started"] for m in metas)
    bad = 0
    for path in sorted(changed_files(since)):
        owners = [m["task"] for m in metas if matches(path, m["allow"] + [f"production/codex/{m['task']}/*"])]
        if matches(path, ALWAYS_ALLOWED + args.ignore) and not owners:
            continue
        if not owners:
            bad += 1
            print(f"OUT-OF-SCOPE {path}")
        elif args.verbose:
            print(f"ok {','.join(owners)} {path}")
    print(f"{bad} out-of-scope file(s) changed since {time.strftime('%Y-%m-%d %H:%M', time.localtime(since))}"
          " (other sessions editing the repo also show here)")


def stop(args):
    meta = load_meta(args.task)
    if alive(meta["pid"]):
        os.killpg(meta["pid"], signal.SIGTERM)
        print(f"stopped {args.task}")
    else:
        print(f"{args.task} not running")


def main():
    ap = argparse.ArgumentParser(description="Run Codex workers for the PM and keep them in check")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start", help="start one Codex worker in the background on a brief file")
    s.add_argument("task", help="task id, e.g. pd-b-w1")
    s.add_argument("--brief", required=True, help="markdown brief with the whole job")
    s.add_argument("--allow", nargs="+", default=[], help="repo-relative globs the worker may write")
    s.add_argument("--forbid", nargs="+", default=[], help="regexes no worker command may match (status flags each hit)")
    s.add_argument("--image", nargs="+", default=[], help="images attached to the prompt; the only way the worker sees an image")
    s.add_argument("--model", default=DEFAULT_MODEL)
    s.add_argument("--effort", default="high", choices=["low", "medium", "high", "xhigh"])
    s.set_defaults(fn=start)
    s = sub.add_parser("status", help="state, last commands and last message of tasks")
    s.add_argument("task", nargs="?")
    s.add_argument("--tail", type=int, default=3)
    s.add_argument("--running", action="store_true")
    s.set_defaults(fn=status)
    s = sub.add_parser("audit", help="files changed since the tasks started that no task was allowed to write")
    s.add_argument("tasks", nargs="*")
    s.add_argument("--ignore", nargs="*", default=[], help="globs written by other known sessions")
    s.add_argument("-v", "--verbose", action="store_true")
    s.set_defaults(fn=audit)
    s = sub.add_parser("stop", help="kill a running task")
    s.add_argument("task")
    s.set_defaults(fn=stop)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()

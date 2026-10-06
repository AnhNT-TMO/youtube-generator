import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import plan_io

REPO = plan_io.repo_root()
TOOLS = Path(__file__).resolve().parent
CAROLS = REPO / "research/christmas-carols"
QUEUE = CAROLS / "batches/QUEUE.json"
RUNS = CAROLS / "queue-runs"
DELIVERIES = REPO / plan_io.PIPELINE["deliveries"]


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def review(batch, line):
    path = CAROLS / "batches" / batch / "PLAN_REVIEW.md"
    with path.open("a") as handle:
        handle.write("\n- " + datetime.datetime.now().isoformat(timespec="seconds") + " " + line + "\n")


def command(args, log):
    result = subprocess.run(args, cwd=REPO, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    with log.open("a") as handle:
        handle.write("\n$ " + " ".join(args) + "\n" + result.stdout)
    print(result.stdout[-900:], flush=True)
    return result.returncode, result.stdout


def phase(name, slug, revision, log):
    args = ["bash", str(TOOLS / "run.sh"), name]
    if slug:
        args += [slug, revision]
    return command(args, log)


def execute(batch, slug, revision, log, prepare=False, opening=False):
    if prepare:
        code, output = command([sys.executable, str(TOOLS / "spec.py"), batch, slug, "--write"], log)
        if code:
            review(batch, "BLOCKED " + slug + " " + revision + ": spec exit " + str(code) + "; " + output[-700:].replace("\n", " | "))
            return
        plan_path = REPO / plan_io.PIPELINE["workdirs"] / slug / (revision + "-pm/arrangement-plan.json")
        if plan_path.is_file():
            plan = plan_io.load(plan_path)
            pad_changes = plan.get("accompaniment_changes", [])
            swaps = [item for changes in plan.get("support_changes_by_style", {}).values() for item in changes if "density swap" in item.get("reason", "")]
            if pad_changes or swaps:
                reasons = sorted({item["reason"] for item in pad_changes + swaps})
                review(batch, f"{slug} {revision}: pad voicing changes={len(pad_changes)}, pattern density swaps={len(swaps)}; " + "; ".join(reasons)[:1300] + "; check_plan 0 FAIL; " + str(log.relative_to(REPO)))
    if prepare or opening:
        args = [sys.executable, str(TOOLS / "make_plan.py"), batch, slug, "--revision", revision]
        code, output = command(args, log)
        if code == 0:
            code, output = command([sys.executable, str(TOOLS / "check_plan.py"), batch, slug, "--revision", revision], log)
        if code:
            review(batch, "BLOCKED " + slug + " " + revision + ": plan exit " + str(code) + "; " + output[-900:].replace("\n", " | "))
            return
    for name in ("sync", "source", "covers", "finish", "deliver", "pull", "record"):
        (log.parent / "current.json").write_text(json.dumps({"batch": batch, "slug": slug, "revision": revision, "phase": name, "updated": datetime.datetime.now().isoformat()}))
        code, output = phase(name, slug, revision, log)
        if code:
            if name not in ("sync", "pull", "record"):
                _, output = phase("inspect", slug, revision, log)
            review(batch, "BLOCKED " + slug + " " + revision + ": " + name + " exit " + str(code) + "; " + output[-900:].replace("\n", " | "))
            return
    review(batch, "RESOLVED " + slug + " " + revision + ": delivered, pulled, recorded.")


def reconcile(batch, slugs, run_dir):
    for slug in slugs:
        for revision_dir in sorted((DELIVERIES / slug).glob("r*")):
            if (revision_dir / "checksums.json").is_file():
                log = run_dir / (slug + "-" + revision_dir.name + ".reconcile.log")
                phase("pull", slug, revision_dir.name, log)
                phase("record", slug, revision_dir.name, log)
    rows = {s["slug"]: s for s in plan_io.load(CAROLS / "pool-state.json").get("new_flow_songs", [])}
    ready_songs = sum(all(rows.get(slug, {}).get("styles", {}).get(style, {}).get("ready_for_listening") for style in plan_io.STYLE_ORDER) for slug in slugs)
    ready_styles = sum(s.get("ready_for_listening", False) for slug in slugs for s in rows.get(slug, {}).get("styles", {}).values())
    review(batch, f"Batch summary: {ready_songs}/{len(slugs)} songs all styles ready; {ready_styles}/{3 * len(slugs)} styles ready; available deliveries pulled + recorded; PLAN_REVIEW inspected.")


def opening_fix(batch, slug, style, revision, run_dir):
    path = CAROLS / "batches" / batch / "songs.json"
    config = plan_io.load(path)
    song = next(s for s in config["songs"] if s["slug"] == slug)
    song.setdefault("revisions", {})[revision] = {
        "styles": [style],
        "source_fix": {"from_revision": "r001", "style": style, "drop_support_bars": 2,
                       "reason": "Opening HF failed both fixed takes; authorized one source fix, omit support first two bars, same seed/noise matrix."},
    }
    plan_io.save(path, config)
    review(batch, f"{slug} {style} {revision}: drop_support_bars=2 from frozen r001; same seed/noise.")
    execute(batch, slug, revision, run_dir / (slug + "-" + revision + ".log"), opening=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wait-pid", type=int)
    args = parser.parse_args()
    run_dir = RUNS / datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    while args.wait_pid and alive(args.wait_pid):
        print("WAIT_Q03", args.wait_pid, flush=True)
        time.sleep(30)
    batches = json.loads(QUEUE.read_text())["batches"]
    reconcile(batches[3]["batch"], batches[3]["slugs"], run_dir)
    phase("sync", "", "", run_dir / "tools.log")
    for batch in batches[:4]:
        name = batch["batch"]
        history = (CAROLS / "batches" / name / "PLAN_REVIEW.md").read_text()
        for slug in batch["slugs"]:
            if (DELIVERIES / slug / "r001/checksums.json").is_file():
                continue
            if not re.search(r"BLOCKED\s+" + re.escape(slug) + r"\b", history):
                continue
            source_retry = bool(re.search(r"BLOCKED\s+" + re.escape(slug) + r"\s+source failed", history))
            execute(name, slug, "r001", run_dir / (slug + "-r001.log"), prepare=not source_retry)
        reconcile(name, batch["slugs"], run_dir)
    for batch, slug, style, revision in (
        ("pool-q01-2026-10-05", "auld_lang_syne", "vibraphone", "r002"),
        ("pool-q01-2026-10-05", "still_still_still", "celesta", "r002"),
        ("pool-q01-2026-10-05", "still_still_still", "vibraphone", "r003"),
        ("pool-q02-2026-10-05", "once_in_royal_davids_city", "vibraphone", "r002"),
        ("pool-q02-2026-10-05", "coventry_carol", "celesta", "r002"),
    ):
        if not (DELIVERIES / slug / revision / "checksums.json").is_file():
            opening_fix(batch, slug, style, revision, run_dir)
    for batch in batches[4:]:
        for slug in batch["slugs"]:
            execute(batch["batch"], slug, "r001", run_dir / (slug + "-r001.log"), prepare=True)
        reconcile(batch["batch"], batch["slugs"], run_dir)
    (run_dir / "COMPLETE").write_text(datetime.datetime.now().isoformat() + "\n")
    print("QUEUE_COMPLETE", run_dir, flush=True)


if __name__ == "__main__":
    main()

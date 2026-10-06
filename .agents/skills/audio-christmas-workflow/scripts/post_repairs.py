import json
import os
import subprocess
import sys
import time
from pathlib import Path

import plan_io

REPO = plan_io.repo_root()
TOOLS = Path(__file__).resolve().parent


def wait(pid):
    while True:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(30)


def main():
    wait(int(sys.argv[1]))
    batch = "album1-2026-10-05"
    path = REPO / "research/christmas-carols/batches" / batch / "songs.json"
    data = plan_io.load(path)
    song = next(s for s in data["songs"] if s["slug"] == "hark_the_herald_angels_sing")
    song.setdefault("revisions", {})["r002"] = {"styles": ["plain", "celesta", "vibraphone"]}
    plan_io.save(path, data)
    log = REPO / "research/christmas-carols/queue-runs/post-hark-r002.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    def run(args):
        out = subprocess.run(args, cwd=REPO, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        with log.open("a") as handle:
            handle.write("\n$ " + " ".join(args) + "\n" + out.stdout)
        return out.returncode
    for args in (
        ["python3", str(TOOLS / "make_plan.py"), batch, song["slug"], "--revision", "r002"],
        ["python3", str(TOOLS / "check_plan.py"), batch, song["slug"], "--revision", "r002"],
        ["bash", str(TOOLS / "run.sh"), "sync", song["slug"], "r002"],
        ["bash", str(TOOLS / "run.sh"), "source", song["slug"], "r002"],
        ["bash", str(TOOLS / "run.sh"), "covers", song["slug"], "r002"],
        ["bash", str(TOOLS / "run.sh"), "finish", song["slug"], "r002"],
        ["bash", str(TOOLS / "run.sh"), "deliver", song["slug"], "r002"],
        ["bash", str(TOOLS / "run.sh"), "pull", song["slug"], "r002"],
        ["bash", str(TOOLS / "run.sh"), "record", song["slug"], "r002"],
    ):
        if run(args):
            break
    with (REPO / "research/christmas-carols/batches" / batch / "PLAN_REVIEW.md").open("a") as handle:
        handle.write("\n- Hark r002 stale-server retry: regenerated layout plan, check_plan and full pipeline attempted after r001 server run conflict; see queue-runs/post-hark-r002.log.\n")
    log = REPO / "research/christmas-carols/queue-runs/post-ding-dong-r001.log"
    with log.open("a") as handle:
        for args in (
            ["bash", str(TOOLS / "run.sh"), "sync", "ding_dong_merrily_on_high", "r001"],
            ["bash", str(TOOLS / "run.sh"), "source", "ding_dong_merrily_on_high", "r001"],
            ["bash", str(TOOLS / "run.sh"), "covers", "ding_dong_merrily_on_high", "r001"],
            ["bash", str(TOOLS / "run.sh"), "finish", "ding_dong_merrily_on_high", "r001"],
            ["bash", str(TOOLS / "run.sh"), "deliver", "ding_dong_merrily_on_high", "r001"],
            ["bash", str(TOOLS / "run.sh"), "pull", "ding_dong_merrily_on_high", "r001"],
            ["bash", str(TOOLS / "run.sh"), "record", "ding_dong_merrily_on_high", "r001"],
        ):
            result = subprocess.run(args, cwd=REPO, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            handle.write("\n$ " + " ".join(args) + "\n" + result.stdout)
            if result.returncode:
                break


if __name__ == "__main__":
    main()

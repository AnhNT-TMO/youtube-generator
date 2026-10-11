#!/usr/bin/env python3
import argparse
import json
import random
import subprocess
import sys
import tomllib
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
AGENTS = REPO / ".codex" / "agents"
OUT = REPO / "production" / "codex"
RESQ = REPO / "production" / "resq"


def agent_config(name):
    path = AGENTS / f"{name}.toml"
    if not path.exists():
        sys.exit(f"không có agent Codex {path.relative_to(REPO)}")
    return tomllib.loads(path.read_text())


def usage_from(log_path):
    total = None
    for line in log_path.read_text().splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        usage = event.get("usage") or (event.get("msg") or {}).get("info", {}).get("total_token_usage")
        if isinstance(usage, dict):
            total = usage
    return total


def cmd_run(args):
    config = agent_config(args.agent)
    OUT.mkdir(parents=True, exist_ok=True)
    scratch = OUT / args.name
    scratch.mkdir(exist_ok=True)
    last = OUT / f"{args.name}.md"
    log_path = OUT / f"{args.name}.jsonl"
    prompt = f"{args.prompt}\nTên của bạn: {args.name}. Thư mục tạm của bạn: {scratch.relative_to(REPO)}/."
    command = ["codex", "exec", "-C", str(REPO), "-s", "workspace-write", "--ephemeral", "--disable", "apps", "--json",
               "-o", str(last),
               "-m", args.model or config["model"],
               "-c", f"model_reasoning_effort={json.dumps(args.effort or config.get('model_reasoning_effort', 'medium'))}",
               "-c", f"developer_instructions={json.dumps(config['developer_instructions'])}",
               prompt]
    with open(log_path, "w") as log, open(OUT / f"{args.name}.err", "w") as err:
        try:
            code = subprocess.run(command, stdout=log, stderr=err, stdin=subprocess.DEVNULL, timeout=args.timeout).returncode
        except subprocess.TimeoutExpired:
            print(f"TIMEOUT sau {args.timeout} s: {args.name} (log {log_path.relative_to(REPO)})")
            return 4
    print(f"== codex {args.agent} {args.name} exit {code}")
    usage = usage_from(log_path)
    if usage:
        print(f"token: {json.dumps(usage)}")
    print(last.read_text().strip() if last.exists() else f"không có báo cáo cuối; xem {log_path.relative_to(REPO)}")
    return code


def verdicts(lane, reviewer):
    rows = []
    for line in (RESQ / lane / "events.jsonl").read_text().splitlines():
        row = json.loads(line)
        if row["by"] == reviewer and row["from"] == "reviewing":
            rows.append(row)
    return rows


def evidence(lane, job_id, attempt):
    path = next((RESQ / lane).glob(f"*/{job_id.replace('/', '__')}.json"), None) \
        or next((RESQ / lane).glob(f"*/*/{job_id.replace('/', '__')}.json"), None)
    if not path:
        return None
    job = json.loads(path.read_text())
    entry = next((h for h in job.get("history", []) if h.get("attempt") == attempt), None)
    output = (entry or {}).get("output") or job.get("output")
    if lane == "images":
        final = job.get("final") if job.get("state") == "done" else output
        return final
    return str((RESQ / "videos" / "check" / Path(output).stem / "sheet.jpg").relative_to(REPO)) if output else None


def cmd_audit(args):
    rows = verdicts(args.lane, args.reviewer)
    if not rows:
        sys.exit(f"{args.reviewer} chưa có verdict nào ở lane {args.lane}")
    results = Counter(row["to"] for row in rows)
    print(f"== {args.reviewer} ({args.lane}): {len(rows)} verdict · " + " · ".join(f"{k} {v}" for k, v in results.items()))
    for row in rows:
        if row["to"] != "done":
            print(f"- {row['to']}: {row['job']} try{row['attempt']}: {row.get('note', '')}")
    accepted = [row for row in rows if row["to"] == "done"]
    picks = random.sample(accepted, min(args.sample, len(accepted)))
    print(f"mẫu ok để PM tự xem ({len(picks)}/{len(accepted)}):")
    for row in picks:
        print(f"- {row['job']} try{row['attempt']} → {evidence(args.lane, row['job'], row['attempt'])}")
        print(f"  note: {row.get('note', '')}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="PM giao việc cho Codex (codex exec, không cần người trông) và kiểm lại đầu ra của nó.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="codex_agent.py run resource_reviewer images-c1012 --prompt 'Lane images. Bộ: image_source. Một lô ≤ 12 job.'\n"
               "codex_agent.py audit images images-c1012 --sample 2")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="chạy một agent .codex/agents/<agent>.toml; báo cáo cuối → production/codex/<name>.md")
    run.add_argument("agent")
    run.add_argument("name", help="tên lượt, cũng là tên reviewer/worker trong queue (mới mỗi lượt)")
    run.add_argument("--prompt", required=True)
    run.add_argument("--model")
    run.add_argument("--effort")
    run.add_argument("--timeout", type=int, default=3600)
    run.set_defaults(func=cmd_run)
    audit = sub.add_parser("audit", help="verdict của một reviewer: mọi redo + mẫu ok ngẫu nhiên để PM tự xem")
    audit.add_argument("lane", choices=("images", "videos"))
    audit.add_argument("reviewer")
    audit.add_argument("--sample", type=int, default=2)
    audit.set_defaults(func=cmd_audit)
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()

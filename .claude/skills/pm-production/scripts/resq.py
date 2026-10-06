#!/usr/bin/env python3
USAGE = """Resource queue: một thư mục mỗi trạng thái, chuyển trạng thái bằng os.rename (nguyên tử, không lock).

  production/resq/<lane>/{input,regen,working/<worker>,review,reviewing/<reviewer>,needs_fix,done,failed,stuck}/<job>.json
  lane = images | videos. Mỗi bước chuyển chỉ một vai được làm:
    PM        add → input · requeue needs_fix → regen · fail · resolve stuck
    generator claim (regen trước, rồi input) → working/<worker> → submit → review | no-output → needs_fix | stuck | release
    reviewer  next-review → reviewing/<reviewer> → verdict ok → done (đưa file vào kho + thẻ cảnh) | redo → needs_fix | failed

  resq.py board [LANE]
  resq.py list LANE STATE [--full]
  resq.py show LANE JOB
  resq.py add LANE JOBS.json|JOBS.jsonl
  resq.py claim LANE --worker W
  resq.py mine LANE --worker W
  resq.py submit LANE JOB --worker W [--meta JSON]
  resq.py no-output LANE JOB --worker W --note TEXT
  resq.py release LANE JOB --worker W --note TEXT       chứng minh chưa gửi: trả job, không tốn lượt
  resq.py stuck LANE JOB --worker W --note TEXT         không rõ đã gửi/đã tạo: PM xử lý
  resq.py next-review LANE --reviewer R [--wait SECONDS] [--batch N]
  resq.py verdict LANE JOB --reviewer R ok|redo --note TEXT [--codes a,b] [--trim-head S] [--trim-tail S] [--card JSON|@FILE]
  resq.py requeue LANE JOB --prompt-file FILE [--note TEXT]
  resq.py reprompt LANE JOB --prompt-file FILE [--note TEXT]   đổi prompt job còn ở input (không tốn lượt)
  resq.py fail LANE JOB --note TEXT
  resq.py resolve LANE JOB --to input|regen|review|needs_fix|failed [--output FILE] [--note TEXT]
  resq.py watch [--review N] [--needs-fix N] [--low LANE=N] [--started LANE] [--max-wait S]   PM chạy nền: thoát khi có việc cho PM
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
ROOT = Path(os.environ.get("RESQ_ROOT", REPO / "production" / "resq"))
LANES = ("images", "videos")
SECTION = {"images": "image", "videos": "video"}
STATES = ("input", "regen", "working", "review", "reviewing", "needs_fix", "done", "failed", "stuck")
PER_ACTOR = ("working", "reviewing")
MAX_ATTEMPTS = 3
MIN_TRIMMED_SECONDS = 7.0


class QueueError(RuntimeError):
    pass


def now():
    return datetime.now().isoformat(timespec="seconds")


def lane_root(lane):
    if lane not in LANES:
        raise QueueError(f"lane phải là {'/'.join(LANES)}")
    return ROOT / lane


def state_dir(lane, state, actor=None):
    if state in PER_ACTOR:
        if not actor:
            raise QueueError(f"{state} cần tên worker/reviewer")
        return lane_root(lane) / state / actor
    return lane_root(lane) / state


def file_name(job_id):
    return job_id.replace("/", "__") + ".json"


def at(path):
    path = Path(path)
    return path if path.is_absolute() else REPO / path


def read(path):
    return json.loads(Path(path).read_text())


def write(path, job):
    path = Path(path)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(job, ensure_ascii=False, indent=1) + "\n")
    os.replace(temporary, path)


def log(lane, job, source, target, actor, note=None):
    entry = {"t": now(), "job": job["id"], "attempt": job.get("attempt"), "from": source, "to": target, "by": actor}
    if note:
        entry["note"] = note
    with open(lane_root(lane) / "events.jsonl", "a") as stream:
        stream.write(json.dumps(entry, ensure_ascii=False) + "\n")


def locate(lane, job_id):
    name = file_name(job_id)
    root = lane_root(lane)
    for state in STATES:
        if state in PER_ACTOR:
            for path in (root / state).glob(f"*/{name}"):
                return state, path.parent.name, path
        elif (root / state / name).exists():
            return state, None, root / state / name
    return None, None, None


def require(lane, job_id, state, actor=None):
    found, owner, path = locate(lane, job_id)
    if found != state or (actor and owner != actor):
        where = f"{found}/{owner}" if owner else found
        raise QueueError(f"{job_id}: đang ở {where or 'không có'}, cần {state}{'/' + actor if actor else ''}")
    return path, read(path)


def move(lane, path, job, state, actor, note=None, owner=None):
    source = job.get("state")
    job.update(state=state, updated=now())
    write(path, job)
    target_dir = state_dir(lane, state, owner)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / path.name
    if target.exists():
        raise QueueError(f"{target} đã tồn tại")
    os.rename(path, target)
    log(lane, job, source, state, actor, note)
    if state in ("done", "failed"):
        purge_tries(job)
    return target


def purge_tries(job):
    final = at(job["final"])
    for attempt in range(1, job["max_attempts"] + 1):
        at(job["final"]).with_name(f"{final.stem}.try{attempt}{final.suffix}").unlink(missing_ok=True)


def attempt_output(job):
    final = Path(job["final"])
    return str(final.with_name(f"{final.stem}.try{job['attempt']}{final.suffix}"))


def prompt_hash(prompt):
    return hashlib.sha256(prompt.encode()).hexdigest()


def new_job(lane, spec):
    for key in ("set", "theme", "shot", "prompt", "final", "card"):
        if not spec.get(key):
            raise QueueError(f"job thiếu {key}: {spec}")
    job = {"id": f"{spec['set']}/{spec['theme']}/{spec['shot']}", "lane": lane, "set": spec["set"],
           "theme": spec["theme"], "shot": spec["shot"], "prompt": spec["prompt"].strip(),
           "prompt_sha256": prompt_hash(spec["prompt"].strip()), "input": spec.get("input"),
           "final": spec["final"], "card": spec["card"], "card_seed": spec.get("card_seed"),
           "attempt": int(spec.get("attempt", 1)), "max_attempts": int(spec.get("max_attempts", MAX_ATTEMPTS)),
           "history": spec.get("history", []), "feedback": spec.get("feedback"), "queued": now(), "state": None}
    job["output"] = attempt_output(job)
    return job


def add(lane, specs, actor="pm", state="input"):
    added, skipped = [], []
    for spec in specs:
        job = new_job(lane, spec)
        found, _, _ = locate(lane, job["id"])
        if found:
            skipped.append(f"{job['id']} ({found})")
            continue
        directory = state_dir(lane, state)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / file_name(job["id"])
        job["state"] = state
        write(path, job)
        log(lane, job, None, state, actor)
        added.append(job["id"])
    return added, skipped


def queued_order(path):
    try:
        job = read(path)
    except (OSError, ValueError):
        return ("9", str(path))
    return (job.get("queued", ""), str(path))


def claim(lane, worker):
    target_dir = state_dir(lane, "working", worker)
    target_dir.mkdir(parents=True, exist_ok=True)
    for state in ("regen", "input"):
        for path in sorted(state_dir(lane, state).glob("*.json"), key=queued_order):
            target = target_dir / path.name
            try:
                os.rename(path, target)
            except FileNotFoundError:
                continue
            job = read(target)
            job.update(state="working", worker=worker, phase="claimed", claimed=now(), updated=now())
            job.pop("phase_note", None)
            write(target, job)
            log(lane, job, state, "working", worker)
            return target, job
    return None, None


def mine(lane, worker):
    directory = state_dir(lane, "working", worker)
    return [(path, read(path)) for path in sorted(directory.glob("*.json"))] if directory.exists() else []


def update(path, job, **values):
    job.update(values, updated=now())
    write(path, job)
    return job


def history_entry(job, **values):
    entry = {"attempt": job["attempt"], "worker": job.get("worker"), "prompt_sha256": job["prompt_sha256"],
             "output": job.get("output"), "at": now()}
    entry.update(values)
    job.setdefault("history", []).append(entry)


def submit(lane, job_id, worker, meta=None):
    path, job = require(lane, job_id, "working", worker)
    if not at(job["output"]).is_file():
        raise QueueError(f"chưa có file {job['output']}")
    job["meta"] = {**(job.get("meta") or {}), **(meta or {}), "sha256": hashlib.sha256(at(job["output"]).read_bytes()).hexdigest()}
    job.update(phase="submitted", submitted=now())
    return move(lane, path, job, "review", worker)


def no_output(lane, job_id, worker, note):
    path, job = require(lane, job_id, "working", worker)
    history_entry(job, result="no-output", note=note)
    job["feedback"] = note
    if job["attempt"] >= job["max_attempts"]:
        mark_card_failed(job, note)
        return move(lane, path, job, "failed", worker, note)
    return move(lane, path, job, "needs_fix", worker, note)


def release(lane, job_id, worker, note):
    path, job = require(lane, job_id, "working", worker)
    job.update(phase=None, phase_note=note, releases=job.get("releases", 0) + 1)
    return move(lane, path, job, "regen" if job["attempt"] > 1 else "input", worker, note)


def stuck(lane, job_id, worker, note):
    path, job = require(lane, job_id, "working", worker)
    job["phase_note"] = note
    return move(lane, path, job, "stuck", worker, note)


def claimed_by(lane, reviewer):
    return sum(1 for row in events(lane) if row["by"] == reviewer and row["to"] == "reviewing")


def next_review(lane, reviewer, wait=0, batch=0):
    deadline = time.time() + wait
    target_dir = state_dir(lane, "reviewing", reviewer)
    target_dir.mkdir(parents=True, exist_ok=True)
    held = sorted(target_dir.glob("*.json"))
    if held:
        return held[0], read(held[0])
    if batch and claimed_by(lane, reviewer) >= batch:
        raise QueueError(f"BATCH_DONE: {reviewer} đã nhận {batch} job, dừng và báo cáo")
    while True:
        candidates = sorted(state_dir(lane, "review").glob("*.json"),
                            key=lambda path: (read(path).get("submitted", ""), str(path)))
        for path in candidates:
            target = target_dir / path.name
            try:
                os.rename(path, target)
            except FileNotFoundError:
                continue
            job = read(target)
            job.update(state="reviewing", reviewer=reviewer, updated=now())
            write(target, job)
            log(lane, job, "review", "reviewing", reviewer)
            return target, job
        if time.time() >= deadline:
            return None, None
        time.sleep(10)


def resource_config(job):
    path = REPO / job["set"] / "resource.json"
    return json.loads(path.read_text()) if path.exists() else {}


def media_info(path):
    output = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                             "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(path)],
                            capture_output=True, text=True, check=True).stdout
    data = json.loads(output)
    stream = data["streams"][0]
    numerator, denominator = stream["r_frame_rate"].split("/")
    return {"width": stream["width"], "height": stream["height"],
            "fps": round(float(numerator) / float(denominator), 3), "seconds": round(float(data["format"]["duration"]), 3)}


def trim_clip(source, target, head, tail, minimum):
    info = media_info(source)
    end = info["seconds"] - tail
    if end - head < minimum:
        raise QueueError(f"cắt xong còn {end - head:.1f} s < {minimum:g} s: chọn redo thay vì cắt")
    descriptor, temporary = tempfile.mkstemp(prefix=f".{Path(target).stem}.", suffix=".mp4", dir=Path(target).parent)
    os.close(descriptor)
    try:
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", str(head), "-to", str(end), "-i", str(source),
                        "-c:v", "libx264", "-crf", "16", "-preset", "slow", "-pix_fmt", "yuv420p", "-c:a", "aac",
                        "-b:a", "128k", "-movflags", "+faststart", temporary], check=True)
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)


def place_final(job, head, tail):
    source, final = at(job["output"]), at(job["final"])
    if final.exists():
        raise QueueError(f"{final} đã có: không ghi đè bản đã duyệt")
    if head or tail:
        if job["lane"] != "videos":
            raise QueueError("chỉ cắt được video")
        minimum = float(resource_config(job).get("video", {}).get("min_seconds_after_trim", MIN_TRIMMED_SECONDS))
        trim_clip(source, final, head, tail, minimum)
    else:
        shutil.copy2(source, final)


def update_card(job, reviewer, note, head, tail, extra=None):
    card_path = at(job["card"])
    card = read(card_path) if card_path.exists() else dict(job.get("card_seed") or {})
    card.update(extra or {})
    final = at(job["final"])
    meta = job.get("meta") or {}
    tries = [{key: entry.get(key) for key in ("attempt", "output", "result", "note", "codes", "at")} for entry in job["history"]]
    if job["lane"] == "images":
        card["image"] = {"file": final.name, "width": meta.get("width"), "height": meta.get("height"),
                         "source": meta.get("source", "chatgpt"), "conversation": meta.get("conversation"),
                         "made": job.get("submitted"), "prompt": job["prompt"], "tries": tries}
        card["qc"] = {"status": "ok", "note": note, "reviewer": reviewer, "at": now()}
        card.setdefault("video", {"file": None})
    else:
        video = {"file": final.name, "source": meta.get("source", "muse.ai"), "made": job.get("submitted"),
                 "thread": meta.get("thread"), "prompt_sent": job["prompt"], "status": "ok", "note": note,
                 "reviewer": reviewer, "at": now(), "tries": tries, **media_info(final)}
        if head or tail:
            video["trim"] = {"head": head, "tail": tail}
        card["video"] = video
    write(card_path, card)


def mark_card_failed(job, note):
    card_path = at(job["card"])
    if job["lane"] != "videos" or not card_path.exists():
        return
    card = read(card_path)
    video = card.setdefault("video", {})
    video.update(status="failed", note=note, file=None)
    video["tries"] = [{key: entry.get(key) for key in ("attempt", "output", "result", "note", "codes", "at")}
                      for entry in job["history"]]
    write(card_path, card)


def verdict(lane, job_id, reviewer, result, note, codes=None, head=0.0, tail=0.0, extra=None):
    path, job = require(lane, job_id, "reviewing", reviewer)
    if result == "ok":
        required = resource_config(job).get(SECTION[lane], {}).get("card_fields", [])
        missing = [field for field in required if not (extra or {}).get(field)]
        if missing:
            raise QueueError(f"ok cần --card có {', '.join(missing)} (xem luật của bộ)")
        place_final(job, head, tail)
        history_entry(job, result="ok", note=note, codes=codes or [], trim=[head, tail] if head or tail else None)
        update_card(job, reviewer, note, head, tail, extra)
        return move(lane, path, job, "done", reviewer, note)
    if not note:
        raise QueueError("redo cần --note mô tả lỗi")
    history_entry(job, result="redo", note=note, codes=codes or [])
    job["feedback"] = note
    if job["attempt"] >= job["max_attempts"]:
        mark_card_failed(job, note)
        return move(lane, path, job, "failed", reviewer, note)
    return move(lane, path, job, "needs_fix", reviewer, note)


def auto_redo(lane, job_id, actor, note, codes):
    path, job = require(lane, job_id, "review")
    target_dir = state_dir(lane, "reviewing", actor)
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.rename(path, target_dir / path.name)
    except FileNotFoundError:
        raise QueueError(f"{job_id}: reviewer vừa nhận job")
    job.update(state="reviewing", reviewer=actor, updated=now())
    write(target_dir / path.name, job)
    log(lane, job, "review", "reviewing", actor)
    return verdict(lane, job_id, actor, "redo", note, codes)


def requeue(lane, job_id, prompt, note=None):
    path, job = require(lane, job_id, "needs_fix")
    if job["attempt"] >= job["max_attempts"]:
        raise QueueError(f"{job_id}: đã dùng {job['attempt']}/{job['max_attempts']} lượt")
    prompt = prompt.strip()
    if prompt_hash(prompt) == job["prompt_sha256"]:
        raise QueueError("prompt sửa phải khác prompt lượt trước")
    job.update(prompt=prompt, prompt_sha256=prompt_hash(prompt), attempt=job["attempt"] + 1, worker=None, phase=None,
               reviewer=None, meta=None, queued=now(), pm_note=note)
    job["output"] = attempt_output(job)
    return move(lane, path, job, "regen", "pm", note)


def reopen(lane, job_id, note):
    path, job = require(lane, job_id, "regen")
    previous = dict(job, attempt=job["attempt"] - 1)
    output = attempt_output(previous)
    if previous["attempt"] < 1 or not at(output).exists():
        raise QueueError(f"{job_id}: không còn bản lượt {previous['attempt']} để duyệt lại")
    hidden = path.with_name(f".{path.name}.reopen")
    try:
        os.rename(path, hidden)
    except FileNotFoundError:
        raise QueueError(f"{job_id}: generator vừa nhận job")
    job.update(attempt=previous["attempt"], output=output, state="review", reviewer=None, submitted=now(), pm_note=note)
    write(hidden, job)
    target = state_dir(lane, "review") / path.name
    os.rename(hidden, target)
    log(lane, job, "regen", "review", "pm", note)
    return target


def reprompt(lane, job_id, prompt, note=None):
    state, _, path = locate(lane, job_id)
    if state not in ("input", "regen"):
        raise QueueError(f"{job_id}: reprompt chỉ từ input/regen (đang {state or 'không có'})")
    hidden = path.with_name(f".{path.name}.reprompt")
    try:
        os.rename(path, hidden)
    except FileNotFoundError:
        raise QueueError(f"{job_id}: generator vừa nhận job, giữ prompt cũ")
    job = read(hidden)
    prompt = prompt.strip()
    job.update(prompt=prompt, prompt_sha256=prompt_hash(prompt), updated=now(), pm_note=note)
    write(hidden, job)
    os.rename(hidden, path)
    log(lane, job, state, state, "pm", note or "reprompt")
    return path


def fail(lane, job_id, note):
    state, _, path = locate(lane, job_id)
    if state not in ("needs_fix", "stuck", "input", "regen"):
        raise QueueError(f"{job_id}: fail chỉ từ needs_fix/stuck/input/regen (đang {state})")
    job = read(path)
    job["feedback"] = note
    mark_card_failed(job, note)
    return move(lane, path, job, "failed", "pm", note)


def resolve(lane, job_id, target, output=None, note=None):
    path, job = require(lane, job_id, "stuck")
    if target == "review":
        if output and Path(output).resolve() != at(job["output"]).resolve():
            shutil.copy2(output, at(job["output"]))
        if not at(job["output"]).is_file():
            raise QueueError(f"chưa có file {job['output']}")
        job["meta"] = {**(job.get("meta") or {}), "sha256": hashlib.sha256(at(job["output"]).read_bytes()).hexdigest()}
        job["submitted"] = now()
    elif target == "needs_fix":
        history_entry(job, result="lost", note=note)
        job["feedback"] = note
    elif target in ("input", "regen"):
        job.update(phase=None, worker=None)
    elif target == "failed":
        job["feedback"] = note
        mark_card_failed(job, note)
    else:
        raise QueueError("--to phải là input/regen/review/needs_fix/failed")
    return move(lane, path, job, target, "pm", note)


def jobs_in(lane, state):
    root = lane_root(lane) / state
    pattern = "*/*.json" if state in PER_ACTOR else "*.json"
    found = []
    for path in sorted(root.glob(pattern)) if root.exists() else []:
        try:
            found.append((path, read(path)))
        except FileNotFoundError:
            continue
    return found


def age(stamp):
    if not stamp:
        return "-"
    minutes = (datetime.now() - datetime.fromisoformat(stamp)).total_seconds() / 60
    return f"{minutes:.0f}m"


def events(lane, since=None):
    path = lane_root(lane) / "events.jsonl"
    if not path.exists():
        return []
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return [row for row in rows if not since or row["t"] >= since]


def board(lanes):
    hour_ago = (datetime.now() - timedelta(hours=1)).isoformat(timespec="seconds")
    for lane in lanes:
        counts = {state: len(jobs_in(lane, state)) for state in STATES}
        print(f"== {lane}: " + " · ".join(f"{state} {count}" for state, count in counts.items()))
        for state in PER_ACTOR:
            for path, job in jobs_in(lane, state):
                stamp = job.get("claimed") if state == "working" else job.get("updated")
                print(f"   {state:9} {path.parent.name:16} {job['id']} try{job['attempt']} {job.get('phase') or ''} {age(stamp)}")
        for path, job in jobs_in(lane, "stuck"):
            print(f"   stuck     {job.get('worker') or '-':16} {job['id']} try{job['attempt']}: {job.get('phase_note', '')[:120]}")
        recent = events(lane, hour_ago)
        verdicts = [row for row in events(lane) if row["to"] in ("done", "needs_fix", "failed") and row["by"] != "pm"]
        first = [row for row in verdicts if row.get("attempt") == 1]
        accepted_first = sum(1 for row in first if row["to"] == "done")
        print(f"   1 giờ qua: nộp {sum(1 for row in recent if row['to'] == 'review')}, đạt {sum(1 for row in recent if row['to'] == 'done')}"
              f" · đạt ngay lượt 1: {accepted_first}/{len(first)}")
        codes = Counter()
        for _, job in jobs_in(lane, "needs_fix") + jobs_in(lane, "done") + jobs_in(lane, "failed"):
            for entry in job.get("history", []):
                codes.update(entry.get("codes") or [])
        if codes:
            print("   mã lỗi: " + ", ".join(f"{code} {count}" for code, count in codes.most_common(8)))


def reviewer_active(lane, seconds):
    since = (datetime.now() - timedelta(seconds=seconds)).isoformat(timespec="seconds")
    return bool(jobs_in(lane, "reviewing")) or any("reviewing" in (row["from"], row["to"]) for row in events(lane, since))


def watch_reasons(review, needs_fix, low, idle_seconds, starting=()):
    reasons = []
    busy = 0
    for lane in LANES:
        counts = {state: len(jobs_in(lane, state)) for state in STATES}
        busy += sum(counts[state] for state in ("input", "regen", "working", "review", "reviewing"))
        if counts["stuck"]:
            reasons.append(f"STUCK {lane} {counts['stuck']}")
        if needs_fix and counts["needs_fix"] >= needs_fix:
            reasons.append(f"FIX {lane} {counts['needs_fix']}")
        if review and counts["review"] >= review and lane not in starting and not reviewer_active(lane, idle_seconds):
            reasons.append(f"REVIEW {lane} {counts['review']}")
        if lane in low and counts["input"] + counts["regen"] < low[lane]:
            reasons.append(f"LOW {lane} {counts['input'] + counts['regen']}")
    if not busy:
        reasons.append("IDLE")
    return reasons


def watch(review, needs_fix, low, idle_seconds, max_wait, started=()):
    began = time.time()
    deadline = began + max_wait
    while True:
        starting = started if time.time() - began < idle_seconds else ()
        reasons = watch_reasons(review, needs_fix, low, idle_seconds, starting)
        if reasons or time.time() >= deadline:
            return reasons or ["TIMEOUT"]
        time.sleep(20)


def card_extra(value):
    if not value:
        return None
    text = Path(value[1:]).read_text() if value.startswith("@") else value
    extra = json.loads(text)
    if not isinstance(extra, dict):
        raise QueueError("--card phải là một JSON object")
    return extra


def load_specs(path):
    text = Path(path).read_text().strip()
    if text.startswith("["):
        return json.loads(text)
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def emit(path, job):
    print(json.dumps({"file": str(path), **job}, ensure_ascii=False, indent=1))


def main():
    parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("board")
    command.add_argument("lane", nargs="?")
    command = commands.add_parser("list")
    command.add_argument("lane")
    command.add_argument("state", choices=STATES)
    command.add_argument("--full", action="store_true")
    command = commands.add_parser("show")
    command.add_argument("lane")
    command.add_argument("job")
    command = commands.add_parser("add")
    command.add_argument("lane")
    command.add_argument("jobs")
    for name in ("claim", "mine"):
        command = commands.add_parser(name)
        command.add_argument("lane")
        command.add_argument("--worker", required=True)
    for name in ("submit", "no-output", "release", "stuck"):
        command = commands.add_parser(name)
        command.add_argument("lane")
        command.add_argument("job")
        command.add_argument("--worker", required=True)
        command.add_argument("--note", required=name != "submit")
        if name == "submit":
            command.add_argument("--meta", default="{}")
    command = commands.add_parser("next-review")
    command.add_argument("lane")
    command.add_argument("--reviewer", required=True)
    command.add_argument("--wait", type=float, default=0)
    command.add_argument("--batch", type=int, default=0, help="dừng khi tên reviewer này đã nhận đủ N job (tên mới mỗi lượt spawn)")
    command = commands.add_parser("verdict")
    command.add_argument("lane")
    command.add_argument("job")
    command.add_argument("result", choices=("ok", "redo"))
    command.add_argument("--reviewer", required=True)
    command.add_argument("--note", default="")
    command.add_argument("--codes", default="")
    command.add_argument("--trim-head", type=float, default=0.0)
    command.add_argument("--trim-tail", type=float, default=0.0)
    command.add_argument("--card", help="JSON object (hoặc @file) gộp vào thẻ cảnh khi ok; trường bắt buộc: resource.json → <lane>.card_fields")
    command = commands.add_parser("requeue")
    command.add_argument("lane")
    command.add_argument("job")
    command.add_argument("--prompt-file", required=True)
    command.add_argument("--note")
    command = commands.add_parser("reopen")
    command.add_argument("lane")
    command.add_argument("job")
    command.add_argument("--note", required=True)
    command = commands.add_parser("reprompt")
    command.add_argument("lane")
    command.add_argument("job")
    command.add_argument("--prompt-file", required=True)
    command.add_argument("--note")
    command = commands.add_parser("fail")
    command.add_argument("lane")
    command.add_argument("job")
    command.add_argument("--note", required=True)
    command = commands.add_parser("resolve")
    command.add_argument("lane")
    command.add_argument("job")
    command.add_argument("--to", required=True, choices=("input", "regen", "review", "needs_fix", "failed"))
    command.add_argument("--output")
    command.add_argument("--note")
    command = commands.add_parser("watch")
    command.add_argument("--review", type=int, default=8, help="review chờ ≥ N và không reviewer nào đang chạy")
    command.add_argument("--needs-fix", type=int, default=5)
    command.add_argument("--low", action="append", default=[], help="LANE=N: input+regen < N")
    command.add_argument("--idle", type=int, default=240, help="reviewer coi là đang chạy nếu có hoạt động trong N giây")
    command.add_argument("--max-wait", type=int, default=4 * 3600)
    command.add_argument("--started", action="append", default=[], help="LANE vừa spawn reviewer: không báo REVIEW lane đó trong --idle giây đầu")
    args = parser.parse_args()
    try:
        if args.command == "board":
            board([args.lane] if args.lane else LANES)
        elif args.command == "list":
            for path, job in jobs_in(args.lane, args.state):
                if args.full:
                    emit(path, job)
                else:
                    owner = f" {path.parent.name}" if args.state in PER_ACTOR else ""
                    print(f"{job['id']} try{job['attempt']}{owner} {job.get('feedback') or ''}"[:220])
        elif args.command == "show":
            state, _, path = locate(args.lane, args.job)
            if not path:
                raise QueueError(f"không có {args.job}")
            emit(path, read(path))
        elif args.command == "add":
            added, skipped = add(args.lane, load_specs(args.jobs))
            print(f"thêm {len(added)} job vào {args.lane}/input" + (f"; bỏ qua {len(skipped)} đã có: {', '.join(skipped[:10])}" if skipped else ""))
        elif args.command == "claim":
            path, job = claim(args.lane, args.worker)
            if not job:
                print("EMPTY")
                sys.exit(1)
            emit(path, job)
        elif args.command == "mine":
            for path, job in mine(args.lane, args.worker):
                emit(path, job)
        elif args.command == "submit":
            print(submit(args.lane, args.job, args.worker, json.loads(args.meta)))
        elif args.command == "no-output":
            print(no_output(args.lane, args.job, args.worker, args.note))
        elif args.command == "release":
            print(release(args.lane, args.job, args.worker, args.note))
        elif args.command == "stuck":
            print(stuck(args.lane, args.job, args.worker, args.note))
        elif args.command == "next-review":
            path, job = next_review(args.lane, args.reviewer, args.wait, args.batch)
            if not job:
                print("EMPTY")
                sys.exit(1)
            emit(path, job)
        elif args.command == "verdict":
            codes = [code for code in args.codes.split(",") if code]
            print(verdict(args.lane, args.job, args.reviewer, args.result, args.note, codes, args.trim_head, args.trim_tail,
                          card_extra(args.card)))
        elif args.command == "requeue":
            print(requeue(args.lane, args.job, Path(args.prompt_file).read_text(), args.note))
        elif args.command == "reopen":
            print(reopen(args.lane, args.job, args.note))
        elif args.command == "reprompt":
            print(reprompt(args.lane, args.job, Path(args.prompt_file).read_text(), args.note))
        elif args.command == "fail":
            print(fail(args.lane, args.job, args.note))
        elif args.command == "resolve":
            print(resolve(args.lane, args.job, args.to, args.output, args.note))
        elif args.command == "watch":
            low = {lane: int(count) for lane, count in (item.split("=", 1) for item in args.low)}
            print("\n".join(watch(args.review, args.needs_fix, low, args.idle, args.max_wait, tuple(args.started))))
    except (QueueError, OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"LỖI: {error}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()

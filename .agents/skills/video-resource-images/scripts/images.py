#!/usr/bin/env python3
USAGE = """Ảnh resource bằng ChatGPT qua queue images (pm-production/scripts/resq.py). Chạy từ gốc repo.

  PM:
    images.py prompt SET THEME SHOT                   in prompt ảnh ghép từ blocks.json + shots.json
    images.py fill SET [--target 60] [--groups a,b]   nạp input tới đủ TARGET job chờ, lấy xoay vòng qua các đề tài
    images.py add SET JOBS.jsonl                      job prompt tự viết: {"theme","shot","prompt"} mỗi dòng
    images.py reconcile JOB --port P [--page-id ID]   job stuck đã có chat: chờ/tải ảnh trong đúng chat → review
  Generator:
    images.py work --port 9223 --port 9225 [--seconds 420] [--max-jobs N] [--exit-when-empty] [--refill SET [--target 60]]
      mỗi cổng = một vòng lặp, worker images-<cổng>; claim → chat mới → gửi đúng prompt → tải PNG → submit review
      --refill: queue chờ < target/3 thì tự fill SET tới target (prompt ghép sẵn, không tốn PM)
      ChatGPT lỗi tạm (không tạo được ảnh) → trả job, không tốn lượt; 3 lần liền ở một cổng → dừng (mã 3)
      hết --seconds thì không nhận job mới, làm xong job đang dở rồi thoát; chạy lại là làm tiếp
"""
import argparse
import json
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS.parents[1] / "pm-production" / "scripts"))
import resq
from resource_set import ResourceSet
from cdp import websocket_module
from chatgpt import Blocked, ChatGPT, NoImage, NotSent, Quota, Unavailable, Uncertain, conversation, png_size

LANE = "images"
PRINT = threading.Lock()
FILL = threading.Lock()
MAX_UNAVAILABLE = 3


def say(worker, message):
    with PRINT:
        print(f"{datetime.now():%H:%M:%S} [{worker}] {message}", flush=True)


def sentence(text):
    text = text.strip()
    return text if text.endswith((".", "!", "?", ":")) else text + "."


def image_prompt(blocks, shot):
    block = blocks["image"]
    lead = block.get("lead", {}).get(shot.get("tags", {}).get("people"))
    parts = [block["head"]] + ([lead] if lead else []) + [sentence(shot["subject"])]
    if shot.get("composition"):
        parts.append(sentence(shot["composition"]))
    parts += [block["realism"].format(lens=shot.get("lens") or "24mm lens at f/8"), block["look"][shot.get("look") or "interior-bright"]]
    tags = shot.get("tags", {})
    if tags.get("season") in block.get("season", {}):
        parts.append(block["season"][tags["season"]])
    snowing = tags.get("snow") == "falling" and tags.get("place") == "outdoor" and "snowing" in block
    if shot.get("lights") is not False:
        parts.append(block["lights_snowing" if snowing else "lights"])
    elif "wild" in block:
        parts.append(block["wild"])
    if snowing:
        parts.append(block["snowing"])
    if shot.get("motion_elements"):
        parts.append(block["motion_ready"].format(motion_elements=shot["motion_elements"]))
    clean = block["clean"]
    if isinstance(clean, dict):
        clean = clean[tags.get("people", "none")]
    parts += [clean, block["tail"]]
    return " ".join(parts)


def job_spec(resources, theme, shot, prompt=None):
    return {"set": resources.name, "theme": theme, "shot": shot["id"],
            "prompt": prompt or image_prompt(resources.blocks, shot),
            "final": resources.path(theme, shot["id"], ".png"), "card": resources.path(theme, shot["id"], ".json"),
            "card_seed": {"id": shot["id"], "theme": theme, "subject": shot.get("subject"), "tags": shot.get("tags", {}),
                          "camera": shot.get("camera")}}


def cmd_prompt(args):
    resources = ResourceSet(args.set)
    print(image_prompt(resources.blocks, resources.shot(args.theme, args.shot)))


def waiting_count():
    return len(resq.jobs_in(LANE, "input")) + len(resq.jobs_in(LANE, "regen"))


def fill(set_name, target, groups=()):
    resources = ResourceSet(set_name)
    waiting = waiting_count()
    pending = []
    for theme in resources.themes(set(groups)):
        todo = [shot for shot in resources.shots(theme)
                if not resources.exists(theme, shot["id"], ".png")
                and not resq.locate(LANE, f"{resources.name}/{theme}/{shot['id']}")[0]]
        if todo:
            pending.append((theme, todo))
    specs = []
    while pending and len(specs) < target - waiting:
        theme, todo = pending.pop(0)
        specs.append(job_spec(resources, theme, todo.pop(0)))
        if todo:
            pending.append((theme, todo))
    added, _ = resq.add(LANE, specs) if specs else ([], [])
    return waiting, len(added)


def cmd_fill(args):
    waiting, added = fill(args.set, args.target, filter(None, (args.groups or "").split(",")))
    print(f"images: đang chờ {waiting}, thêm {added} → {waiting + added} (đích {args.target})")


def cmd_add(args):
    resources = ResourceSet(args.set)
    specs = []
    for row in resq.load_specs(args.jobs):
        specs.append(job_spec(resources, row["theme"], resources.shot(row["theme"], row["shot"]), row["prompt"]))
    added, skipped = resq.add(LANE, specs)
    print(f"thêm {len(added)}; bỏ qua {len(skipped)} đã có: {', '.join(skipped[:10])}")


def save_png(job, raw):
    width, height = png_size(raw)
    output = resq.at(job["output"])
    temporary = output.with_name(f".{output.name}.tmp")
    temporary.write_bytes(raw)
    temporary.replace(output)
    config = resq.resource_config(job).get("image", {})
    warnings = []
    low, high = config.get("ratio", [1.70, 1.85])
    if width < config.get("min_width", 1600) or not low <= width / height <= high:
        warnings.append(f"cỡ {width}×{height}")
    return {"width": width, "height": height, "warnings": warnings}


def finish(chat, path, job, worker):
    try:
        file_id = chat.wait_image()
    except Quota as error:
        resq.release(LANE, job["id"], worker, f"ChatGPT hết lượt ảnh: {error}")
        raise Blocked(f"QUOTA: {error}")
    except Unavailable as error:
        resq.release(LANE, job["id"], worker, f"ChatGPT lỗi tạm, không tạo ảnh: {error}")
        say(worker, f"↺ {job['id']}: ChatGPT lỗi tạm → trả queue")
        return "unavailable"
    except NoImage as error:
        resq.no_output(LANE, job["id"], worker, f"ChatGPT không trả ảnh: {error}")
        say(worker, f"✗ {job['id']}: không có ảnh → needs_fix")
        return
    except Uncertain as error:
        resq.stuck(LANE, job["id"], worker, str(error))
        say(worker, f"? {job['id']}: {error} → stuck")
        return
    raw = chat.fetch(file_id)
    meta = save_png(job, raw)
    meta.update(source="chatgpt", conversation=job["conversation"], file_id=file_id, hidden=chat.hide(job["conversation"]))
    resq.submit(LANE, job["id"], worker, meta)
    say(worker, f"✓ {job['id']} try{job['attempt']} {meta['width']}×{meta['height']} → review" +
        (f" ⚠ {', '.join(meta['warnings'])}" if meta["warnings"] else ""))


def run_job(chat, path, job, worker):
    phase = job.get("phase")
    if phase == "sent":
        chat.open(job["conversation"])
        return finish(chat, path, job, worker)
    if phase == "sending":
        resq.stuck(LANE, job["id"], worker, "lần chạy trước dừng giữa lúc gửi; không rõ đã gửi chưa")
        return
    try:
        chat.open()
        resq.update(path, job, phase="sending", send_started=resq.now())
        conv = chat.send(job["prompt"])
    except NotSent as error:
        resq.update(path, job, phase="claimed")
        resq.release(LANE, job["id"], worker, f"chưa gửi: {error}")
        say(worker, f"↺ {job['id']}: chưa gửi ({error}) → trả lại queue")
        return
    except Uncertain as error:
        resq.update(path, job, conversation=conversation(chat.page.url()))
        resq.stuck(LANE, job["id"], worker, str(error))
        say(worker, f"? {job['id']}: {error} → stuck")
        return
    resq.update(path, job, phase="sent", conversation=conv, sent=resq.now())
    return finish(chat, path, job, worker)


def work_port(port, page_id, args, results):
    worker = f"images-{port}"
    try:
        chat = ChatGPT(port, page_id)
        deadline = time.time() + args.seconds
        done = unavailable = 0
        for path, job in resq.mine(LANE, worker):
            say(worker, f"làm tiếp {job['id']} ({job.get('phase')})")
            run_job(chat, path, job, worker)
            done += 1
        while time.time() < deadline and (not args.max_jobs or done < args.max_jobs):
            if args.refill and waiting_count() < args.target // 3:
                with FILL:
                    waiting, added = fill(args.refill, args.target)
                if added:
                    say(worker, f"refill: {waiting} chờ, thêm {added}")
            path, job = resq.claim(LANE, worker)
            if not job:
                if args.exit_when_empty:
                    say(worker, "queue trống")
                    break
                time.sleep(15)
                continue
            say(worker, f"→ {job['id']} try{job['attempt']}")
            unavailable = unavailable + 1 if run_job(chat, path, job, worker) == "unavailable" else 0
            if unavailable >= MAX_UNAVAILABLE:
                raise Blocked(f"UNAVAILABLE: ChatGPT {MAX_UNAVAILABLE} lần liền không tạo được ảnh")
            done += 1
        results[worker] = f"DONE {done} job"
    except Blocked as error:
        results[worker] = f"BLOCKED {error}"
    except Exception as error:
        held = [job["id"] for _, job in resq.mine(LANE, worker)]
        results[worker] = f"ERROR {type(error).__name__}: {error}" + (f" (giữ {', '.join(held)} để chạy lại)" if held else "")
    say(worker, f"cổng dừng: {results.get(worker)}")


def cmd_work(args):
    websocket_module()
    page_ids = dict(item.split("=", 1) for item in args.page_id)
    results, threads = {}, []
    for port in args.port:
        thread = threading.Thread(target=work_port, args=(port, page_ids.get(port), args, results))
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()
    for worker, result in sorted(results.items()):
        print(f"{worker}: {result}")
    if any(result.startswith(("BLOCKED", "ERROR")) for result in results.values()):
        sys.exit(3)


def cmd_reconcile(args):
    websocket_module()
    path, job = resq.require(LANE, args.job, "stuck")
    if not job.get("conversation"):
        sys.exit("job không có conversation: dùng resq.py resolve (input/needs_fix) theo bằng chứng")
    chat = ChatGPT(args.port, args.page_id)
    chat.open(job["conversation"])
    file_id = chat.wait_image(timeout=60)
    meta = save_png(job, chat.fetch(file_id))
    meta.update(source="chatgpt", conversation=job["conversation"], file_id=file_id, hidden=chat.hide(job["conversation"]))
    job["meta"] = meta
    resq.write(path, job)
    print(resq.resolve(LANE, args.job, "review", note="reconcile: ảnh có trong chat"))


def main():
    parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("prompt")
    command.add_argument("set")
    command.add_argument("theme")
    command.add_argument("shot")
    command = commands.add_parser("fill")
    command.add_argument("set")
    command.add_argument("--target", type=int, default=60)
    command.add_argument("--groups")
    command = commands.add_parser("add")
    command.add_argument("set")
    command.add_argument("jobs")
    command = commands.add_parser("work")
    command.add_argument("--port", action="append", required=True)
    command.add_argument("--page-id", action="append", default=[], help="PORT=TARGET_ID khi cổng có nhiều tab ChatGPT")
    command.add_argument("--seconds", type=int, default=420)
    command.add_argument("--max-jobs", type=int)
    command.add_argument("--exit-when-empty", action="store_true")
    command.add_argument("--refill", metavar="SET", help="tự fill SET khi queue chờ < target/3")
    command.add_argument("--target", type=int, default=60)
    command = commands.add_parser("reconcile")
    command.add_argument("job")
    command.add_argument("--port", required=True)
    command.add_argument("--page-id")
    args = parser.parse_args()
    try:
        {"prompt": cmd_prompt, "fill": cmd_fill, "add": cmd_add, "work": cmd_work, "reconcile": cmd_reconcile}[args.command](args)
    except (resq.QueueError, Blocked, NoImage, Unavailable, Uncertain) as error:
        print(f"LỖI: {error}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()

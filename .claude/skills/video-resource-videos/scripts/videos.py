#!/usr/bin/env python3
USAGE = """Clip resource bằng muse.ai (ảnh → video) qua queue videos (pm-production/scripts/resq.py). Chạy từ gốc repo.

  PM:
    videos.py candidates SET [--groups a,b] [--limit N] [--json] [--missing-clip]   ảnh đã duyệt chưa có clip, chưa vào queue
    videos.py clip SET CLIPS.jsonl                                 ghi trường clip vào thẻ cảnh: {"theme","shot","clip":{…}} mỗi dòng
    videos.py draft SET [--limit 40] [--groups a,b] [--dry-run]    ghép prompt từ <set>/<video.prompt> + trường clip, chọn kiểu máy cân bằng → input
    videos.py refix SET [--codes camera-far] [--dry-run]           needs_fix chỉ có mã trong --codes → ghép lại từ khuôn, đảo hướng máy, requeue
    videos.py add SET JOBS.jsonl                                   {"theme","shot","prompt"} mỗi dòng, prompt PM tự viết (prompt sửa, cảnh đặc biệt)
    videos.py reconcile JOB --port P --page-id ID                  job stuck có thread: mở đúng thread, có video thì tải → review
  Generator:
    videos.py work --port 9224 --port 9226 [--seconds 300] [--drain 900] [--exit-when-empty]
      một vòng lặp lo mọi tab muse.ai của các cổng (mỗi tab = một slot), worker videos-<cổng>;
      slot trống → claim → thread mới → đính PNG → gửi → poll → tải MP4 → submit review → slot trống
      hết --seconds thì không nhận job mới; chờ job đang chạy tối đa --drain giây rồi thoát (job dở làm tiếp lần sau)
  Reviewer:
    videos.py check JOB|CLIP [--out DIR]   ảnh soi + số đo: sheet, edges, từng giây, khung đầy đủ 3.5/8 s, độ sáng, cắt cảnh
"""
import argparse
import json
import re
import subprocess
from collections import Counter
import sys
import time
from datetime import datetime
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS.parents[1] / "pm-production" / "scripts"))
import resq
from resource_set import ResourceSet
from cdp import websocket_module
from muse import Blocked, FetchFailed, MuseTab, NotSent, Uncertain, muse_tabs

LANE = "videos"
MOTION_PYTHON = SCRIPTS.parent / ".venv" / "bin" / "python"
MOTION_ACTOR = "auto-motion"
GENERATION_TIMEOUT = 15 * 60
UNDELIVERED_LIMIT = 6
FETCH_RETRIES = 3
EDGE_FRAMES = (0, 12, 24, 36, 48, 60, 72, 84, 192, 210, 228, 239)


def say(worker, message):
    print(f"{datetime.now():%H:%M:%S} [{worker}] {message}", flush=True)


def camera_motion(clip):
    if not MOTION_PYTHON.exists():
        return None
    result = subprocess.run([str(MOTION_PYTHON), str(SCRIPTS / "motion.py"), str(clip)], capture_output=True, text=True)
    return json.loads(result.stdout) if result.returncode == 0 else None


def motion_gate(job, motion):
    config = resq.resource_config(job).get("video", {})
    limit, zoom_limit = config.get("motion_reject"), config.get("zoom_reject")
    shift, scale = (motion or {}).get("camera_shift"), (motion or {}).get("scale")
    too_far = bool(limit and shift is not None and shift > limit)
    too_close = bool(zoom_limit and scale and max(scale, 1 / scale) > zoom_limit)
    if not too_far and not too_close:
        return None
    note = (f"đo tự động: khung dời {shift:.0%} bề ngang (ngưỡng {limit:.0%}), zoom ×{scale} (ngưỡng ×{zoom_limit}); "
            f"từng giây {motion['per_second']}")
    resq.auto_redo(LANE, job["id"], MOTION_ACTOR, note, ["camera-far"])
    return note


def elapsed(stamp):
    return (datetime.now() - datetime.fromisoformat(stamp)).total_seconds() if stamp else 0


def pending_clips(resources, groups=()):
    for theme in resources.themes(set(groups)):
        for shot in resources.shots(theme):
            card = resources.card(theme, shot["id"]) or {}
            video = card.get("video") or {}
            if (card.get("qc") or {}).get("status") != "ok" or not resources.exists(theme, shot["id"], ".png"):
                continue
            if video.get("status") or resources.exists(theme, shot["id"], ".mp4"):
                continue
            if resq.locate(LANE, f"{resources.name}/{theme}/{shot['id']}")[0]:
                continue
            yield theme, shot, card


def cmd_candidates(args):
    resources = ResourceSet(args.set)
    rows = []
    for theme, shot, card in pending_clips(resources, filter(None, (args.groups or "").split(","))):
        if args.missing_clip and card.get("clip"):
            continue
        rows.append({"theme": theme, "shot": shot["id"], "image": resources.path(theme, shot["id"], ".png"),
                     "subject": shot.get("subject"), "tags": shot.get("tags"), "clip": card.get("clip"),
                     "earlier": [entry.get("note") for entry in (card.get("video") or {}).get("tries", []) if entry.get("note")]})
    rows = rows[:args.limit] if args.limit else rows
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return
    for row in rows:
        print(f"{row['theme']}/{row['shot']} {row['tags']}\n   {row['subject']}"
              + (f"\n   lần trước: {' | '.join(row['earlier'])}" if row["earlier"] else ""))
    print(f"{len(rows)} cảnh chờ clip")


def template(resources):
    name = resources.config.get("video", {}).get("prompt")
    if not name:
        raise resq.QueueError(f"{resources.name}/resource.json thiếu video.prompt (khuôn ghép prompt clip)")
    return json.loads((resources.root / name).read_text())


def check_clip(spec, clip):
    missing = [key for key in ("shot", "motion", "lock", "light", "sound") if not clip.get(key)]
    if missing:
        raise resq.QueueError(f"clip thiếu {', '.join(missing)}")
    unknown = set(clip) - set(spec.get("fields", clip))
    if unknown:
        raise resq.QueueError(f"clip có trường lạ {', '.join(sorted(unknown))}")


def sentences(value):
    items = value if isinstance(value, list) else [value] if value else []
    return [item.strip() if item.strip().endswith((".", "!", "?")) else item.strip() + "." for item in items if item.strip()]


def spoken_list(value):
    if not isinstance(value, list):
        return value
    items = [str(item) for item in value]
    return ", ".join(items[:-1]) + " and " + items[-1] if len(items) > 1 else "".join(items)


def compose(spec, card, move):
    clip = card["clip"]
    facts = {**clip, "indoor": (card.get("tags") or {}).get("place") == "indoor", "move": move}
    facts["outdoor"] = not facts["indoor"]
    facts["close"] = str(clip.get("shot") or "").strip().lower() == "close"
    parts = []
    for block in spec["sequence"]:
        condition = block.get("if")
        if condition and not (not facts.get(condition[1:]) if condition.startswith("!") else facts.get(condition)):
            continue
        if "field" in block:
            parts += sentences(clip.get(block["field"]))
        else:
            parts.append(block["text"].format(**{key: spoken_list(value) for key, value in facts.items() if value is not None}))
    prompt = " ".join(parts)
    for condition, words in spec.get("forbid", {}).items():
        if facts.get(condition):
            hits = [word for word in words if re.search(word, prompt, re.I)]
            if hits:
                raise resq.QueueError(f"{card.get('id')}: prompt có chữ cấm khi {condition}: {', '.join(hits)} (sửa trường clip)")
    return prompt


def used_moves(spec, resources):
    moves = sorted({move for group in spec["moves"].values() for move in group}, key=len, reverse=True)
    def found(prompt):
        return next((move for move in moves if move in (prompt or "")), None)
    by_theme, overall = {}, Counter()
    for state in resq.STATES:
        for _, job in resq.jobs_in(LANE, state):
            if job.get("set") == resources.name and found(job.get("prompt")):
                by_theme.setdefault(job["theme"], Counter())[found(job["prompt"])] += 1
                overall[found(job["prompt"])] += 1
    for theme in resources.themes():
        for shot in resources.shots(theme):
            card = resources.card(theme, shot["id"]) or {}
            move = found((card.get("video") or {}).get("prompt_sent"))
            if move:
                by_theme.setdefault(theme, Counter())[move] += 1
                overall[move] += 1
    return by_theme, overall


def pick_move(spec, clip, theme_counts, overall):
    options = spec["moves"]["deep" if clip.get(spec.get("deep_field", "deep")) else "default"]
    return min(options, key=lambda move: (theme_counts[move], overall[move], options.index(move)))


def cmd_clip(args):
    resources = ResourceSet(args.set)
    spec = template(resources)
    written = 0
    for row in resq.load_specs(args.clips):
        check_clip(spec, row["clip"])
        path = resources.root / row["theme"] / f"{row['shot']}.json"
        card = json.loads(path.read_text()) if path.exists() else None
        if not card:
            raise resq.QueueError(f"{row['theme']}/{row['shot']}: chưa có thẻ cảnh")
        card["clip"] = row["clip"]
        compose(spec, card, spec["moves"]["default"][0])
        resq.write(path, card)
        written += 1
    print(f"ghi clip cho {written} cảnh")


def theme_results(resources):
    results = {}
    for row in resq.events(LANE, ""):
        if row.get("from") != "reviewing" or not row["job"].startswith(resources.name + "/"):
            continue
        theme = row["job"][len(resources.name) + 1:].rsplit("/", 1)[0]
        results.setdefault(theme, Counter())["ok" if row["to"] == "done" else "redo"] += 1
    return results


def held_themes(resources, minimum, rate):
    held = {}
    for theme, counts in theme_results(resources).items():
        total = counts["ok"] + counts["redo"]
        if total >= minimum and counts["ok"] / total < rate:
            held[theme] = f"{counts['ok']}/{total}"
    return held


def cmd_draft(args):
    resources = ResourceSet(args.set)
    spec = template(resources)
    held = held_themes(resources, args.hold_min, args.hold_below)
    by_theme, overall = used_moves(spec, resources)
    specs, missing = [], []
    rows = [row for row in pending_clips(resources, filter(None, (args.groups or "").split(","))) if row[0] not in held]
    themes = {}
    for theme, shot, card in rows:
        themes.setdefault(theme, []).append((shot, card))
    order = []
    while themes and len(order) < len(rows):
        for theme in list(themes):
            order.append((theme, *themes[theme].pop(0)))
            if not themes[theme]:
                del themes[theme]
    rejected = []
    for theme, shot, card in order:
        if len(specs) >= args.limit:
            break
        if not card.get("clip"):
            missing.append(f"{theme}/{shot['id']}")
            continue
        counts = by_theme.setdefault(theme, Counter())
        move = pick_move(spec, card["clip"], counts, overall)
        try:
            prompt = compose(spec, card, move)
        except resq.QueueError as error:
            rejected.append(str(error))
            continue
        counts[move] += 1
        overall[move] += 1
        specs.append({"set": resources.name, "theme": theme, "shot": shot["id"], "prompt": prompt,
                      "input": resources.path(theme, shot["id"], ".png"), "final": resources.path(theme, shot["id"], ".mp4"),
                      "card": resources.path(theme, shot["id"], ".json")})
    if args.dry_run:
        for item in specs[:3]:
            print(f"{item['theme']}/{item['shot']}: {item['prompt']}\n")
        print(f"sẽ thêm {len(specs)}")
    else:
        added, skipped = resq.add(LANE, specs) if specs else ([], [])
        print(f"thêm {len(added)} job clip; bỏ qua {len(skipped)}")
    for line in rejected:
        print(f"PM sửa trường clip: {line}")
    print(f"kiểu máy đã dùng: {dict(overall.most_common())}")
    if held:
        print(f"giữ lại (tỉ lệ đạt clip thấp, không thêm job): {', '.join(f'{theme} {ratio}' for theme, ratio in sorted(held.items()))}")
    if missing:
        print(f"{len(missing)} cảnh chưa có trường clip (videos.py candidates {resources.name} --missing-clip): {', '.join(missing[:8])}")


def cmd_redraft(args):
    resources = ResourceSet(args.set)
    spec = template(resources)
    by_theme, overall = used_moves(spec, resources)
    changed = kept = 0
    for _, job in resq.jobs_in(LANE, "input"):
        if job.get("set") != resources.name:
            continue
        card = resources.card(job["theme"], job["shot"]) or {}
        if not card.get("clip"):
            continue
        composed = re.search(r"\b(slide to the (?:left|right))\b", job.get("prompt", ""))
        if not composed:
            continue
        current = composed.group(1)
        options = spec["moves"]["deep" if card["clip"].get(spec.get("deep_field", "deep")) else "default"]
        move = current if current in options else None
        if not move:
            counts = by_theme.setdefault(job["theme"], Counter())
            move = pick_move(spec, card["clip"], counts, overall)
            counts[move] += 1
            overall[move] += 1
        prompt = compose(spec, card, move)
        if prompt == job.get("prompt"):
            kept += 1
            continue
        if args.dry_run:
            print(f"{job['id']}: {current} → {move}")
        else:
            try:
                resq.reprompt(LANE, job["id"], prompt, f"redraft: khuôn mới ({current} → {move})")
            except resq.QueueError as error:
                print(error)
                continue
        changed += 1
    print(f"{'sẽ đổi' if args.dry_run else 'đã đổi'} {changed} job; giữ {kept}")


def flipped(move):
    for side, other in (("left", "right"), ("right", "left")):
        if side in move:
            return move.replace(side, other)
    return move


def cmd_refix(args):
    resources = ResourceSet(args.set)
    spec = template(resources)
    codes = set(args.codes.split(","))
    for _, job in resq.jobs_in(LANE, "needs_fix"):
        if job.get("set") != resources.name:
            continue
        last = (job.get("history") or [{}])[-1]
        card = resources.card(job["theme"], job["shot"]) or {}
        composed = re.search(r"\b(slide to the (?:left|right))\b", job.get("prompt", ""))
        if not set(last.get("codes") or []) <= codes or not card.get("clip") or not composed:
            print(f"PM: {job['id']} {last.get('codes')}")
            continue
        options = spec["moves"]["deep" if card["clip"].get(spec.get("deep_field", "deep")) else "default"]
        move = flipped(composed.group(1).strip())
        if move not in options:
            move = options[0]
        steady = f"steady {composed.group(1).strip()} that keeps going"
        prompt = (job["prompt"].replace(steady, f"steady {move} that keeps going", 1) if steady in job["prompt"]
                  else compose(spec, card, move))
        if args.dry_run:
            print(f"{job['id']}: {composed.group(1).strip()} → {move}")
            continue
        try:
            resq.requeue(LANE, job["id"], prompt, f"refix {','.join(last.get('codes') or [])}: {composed.group(1).strip()} → {move}")
            print(f"{job['id']}: → {move} (lượt {job['attempt'] + 1})")
        except resq.QueueError as error:
            print(error)


def cmd_add(args):
    resources = ResourceSet(args.set)
    specs = []
    for row in resq.load_specs(args.jobs):
        theme, shot = row["theme"], row["shot"]
        if not resources.exists(theme, shot, ".png"):
            raise resq.QueueError(f"{theme}/{shot}: chưa có ảnh đã duyệt")
        specs.append({"set": resources.name, "theme": theme, "shot": shot, "prompt": row["prompt"],
                      "input": resources.path(theme, shot, ".png"), "final": resources.path(theme, shot, ".mp4"),
                      "card": resources.path(theme, shot, ".json"), "attempt": row.get("attempt", 1),
                      "history": row.get("history", []), "feedback": row.get("feedback")})
    added, skipped = resq.add(LANE, specs)
    print(f"thêm {len(added)}; bỏ qua {len(skipped)} đã có: {', '.join(skipped[:10])}")


def save_clip(job, raw, url, src):
    output = resq.at(job["output"])
    temporary = output.with_name(f".{output.name}.tmp")
    temporary.write_bytes(raw)
    temporary.replace(output)
    return {**resq.media_info(output), "source": "muse.ai", "thread": url, "src": src}


class Slot:
    def __init__(self, port, page_id):
        self.port, self.page_id = port, page_id
        self.worker = f"videos-{port}"
        self.tab = MuseTab(port, page_id)
        self.path = self.job = None

    def name(self):
        return f"{self.worker}/{self.page_id[:8]}"

    def adopt(self, path, job):
        self.path, self.job = path, job

    def clear(self):
        self.path = self.job = None

    def update(self, **values):
        resq.update(self.path, self.job, **values)

    def start(self):
        job = self.job
        say(self.name(), f"→ {job['id']} try{job['attempt']}")
        try:
            self.update(port=self.port, page=self.page_id)
            self.tab.new_thread()
            self.tab.attach(resq.at(job["input"]))
            message = self.tab.send(job["prompt"])
            self.update(phase="sending", send_started=resq.now())
            url = self.tab.press_send(message)
        except NotSent as error:
            self.update(phase="claimed")
            resq.release(LANE, job["id"], self.worker, f"chưa gửi: {error}")
            say(self.name(), f"↺ {job['id']}: chưa gửi ({error}) → trả queue")
            return self.clear()
        except Uncertain as error:
            return self.to_stuck(str(error))
        self.update(phase="sent", sent=resq.now(), thread=None if url.startswith("https://muse.ai/thread/new") else url)

    def to_stuck(self, note):
        resq.stuck(LANE, self.job["id"], self.worker, note)
        say(self.name(), f"? {self.job['id']}: {note} → stuck")
        self.clear()

    def resume(self):
        job = self.job
        say(self.name(), f"làm tiếp {job['id']} ({job.get('phase')})")
        if job.get("phase") == "claimed":
            return self.start()
        if job.get("phase") != "sent":
            return self.to_stuck("lần chạy trước dừng giữa lúc gửi; không rõ đã gửi chưa")
        if job.get("thread"):
            self.tab.open(job["thread"])
        elif not self.tab.page.url().startswith("https://muse.ai/thread/"):
            self.to_stuck("chưa ghi thread và tab đã rời thread")

    def step(self):
        job = self.job
        state = self.tab.poll()
        if not job.get("thread") and not state["url"].startswith("https://muse.ai/thread/new"):
            self.update(thread=state["url"])
        if state["video"]:
            try:
                raw = self.tab.fetch(state["video"]["src"])
            except Exception as error:
                failures = job.get("fetch_failures", 0) + 1
                if failures >= FETCH_RETRIES:
                    return self.to_stuck(f"video có trong thread nhưng {failures} lần tải lỗi: {str(error)[-300:]}")
                self.update(fetch_failures=failures)
                say(self.name(), f"! {job['id']}: tải video lỗi lần {failures}/{FETCH_RETRIES}, thử lại vòng sau: {str(error)[-200:]}")
                return "fetch_failed"
            meta = save_clip(job, raw, state["url"], state["video"]["src"])
            meta["motion"] = camera_motion(resq.at(job["output"]))
            resq.submit(LANE, job["id"], self.worker, meta)
            say(self.name(), f"✓ {job['id']} try{job['attempt']} {meta['width']}×{meta['height']} {meta['seconds']} s → review")
            try:
                rejected = motion_gate(job, meta["motion"])
            except resq.QueueError as error:
                rejected = None
                say(self.name(), f"  đo máy bỏ qua: {error}")
            if rejected:
                say(self.name(), f"✗ {job['id']}: {rejected}")
            self.clear()
            return "video"
        if state["undelivered"]:
            resq.release(LANE, job["id"], self.worker, "muse: Delivery not confirmed")
            say(self.name(), f"↺ {job['id']}: Delivery not confirmed → trả queue")
            self.clear()
            return "undelivered"
        if state["reused"]:
            return self.to_stuck("muse không tạo lại vì ảnh + prompt trùng lần trước và không trả file: PM đổi prompt (vd. đảo hướng máy) rồi requeue")
        if elapsed(job.get("sent")) > GENERATION_TIMEOUT:
            if job.get("timeouts"):
                return self.to_stuck(f"lần thứ hai quá {GENERATION_TIMEOUT // 60} phút chưa có video: {state['tail'][-150:]}")
            self.update(timeouts=1)
            resq.release(LANE, job["id"], self.worker, f"quá {GENERATION_TIMEOUT // 60} phút chưa có video")
            say(self.name(), f"↺ {job['id']}: quá hạn → trả queue")
            self.clear()


def slots_for(args):
    wanted = {}
    for item in args.page_id:
        port, page = item.split("=", 1)
        wanted.setdefault(port, []).append(page)
    slots = []
    for port in args.port:
        pages = wanted.get(port) or muse_tabs(port)
        if not pages:
            raise Blocked(f"cổng {port}: không có tab muse.ai")
        slots += [Slot(port, page) for page in pages]
    return slots


def cmd_work(args):
    websocket_module()
    slots = slots_for(args)
    by_page = {slot.page_id: slot for slot in slots}
    for port in args.port:
        for path, job in resq.mine(LANE, f"videos-{port}"):
            if args.only and job.get("set") not in args.only:
                continue
            slot = by_page.get(job.get("page")) or next((s for s in slots if s.port == port and not s.job), None)
            if not slot or slot.job:
                sys.exit(f"{job['id']}: tab {job.get('page')} không còn; PM reconcile trước khi chạy")
            slot.adopt(path, job)
    deadline = time.time() + args.seconds
    stop_at = deadline + args.drain
    done = undelivered = 0
    try:
        for slot in slots:
            if slot.job:
                slot.resume()
        while time.time() < stop_at:
            accepting = time.time() < deadline
            empty = False
            for slot in slots:
                if slot.job and slot.job.get("phase") == "sent":
                    before = slot.job["id"]
                    outcome = slot.step()
                    done += slot.job is None and resq.locate(LANE, before)[0] == "review"
                    undelivered = 0 if outcome == "video" else undelivered + (outcome == "undelivered")
                    if undelivered >= UNDELIVERED_LIMIT:
                        raise Blocked(f"muse: {undelivered} lần liên tiếp Delivery not confirmed, không có video nào; dừng để không dồn thêm yêu cầu")
                if not slot.job and accepting and not empty:
                    path, job = resq.claim(LANE, slot.worker, args.only)
                    if job:
                        slot.adopt(path, job)
                        slot.start()
                    else:
                        empty = True
            if not any(slot.job for slot in slots) and (not accepting or (empty and args.exit_when_empty)):
                break
            time.sleep(10)
    except Blocked as error:
        for slot in slots:
            if slot.job and slot.job.get("phase") == "claimed":
                resq.release(LANE, slot.job["id"], slot.worker, f"dừng: {error}")
        print(f"BLOCKED {error}")
        sys.exit(3)
    held = [f"{slot.job['id']} ({slot.job.get('phase')})" for slot in slots if slot.job]
    print(f"DONE {done} clip nộp review" + (f"; đang chạy, làm tiếp lần sau: {', '.join(held)}" if held else ""))


def cmd_reconcile(args):
    websocket_module()
    path, job = resq.require(LANE, args.job, "stuck")
    thread = job.get("thread") or args.thread
    if not thread:
        sys.exit("job không có thread: truyền --thread URL nếu tìm được trong muse, hoặc resq.py resolve theo bằng chứng")
    tab = MuseTab(args.port, args.page_id)
    tab.open(thread)
    state = tab.poll()
    if not state["video"]:
        print(f"chưa có video trong {thread}: {state['tail'][-300:]}")
        sys.exit(1)
    job["meta"] = save_clip(job, tab.fetch(state["video"]["src"]), state["url"], state["video"]["src"])
    resq.write(path, job)
    print(resq.resolve(LANE, args.job, "review", note="reconcile: video có trong thread"))


def ffmpeg(*arguments):
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", *arguments], check=True)


def series(clip, filters):
    output = subprocess.run(["ffprobe", "-v", "error", "-f", "lavfi", "-i", f"movie={clip},{filters}", "-show_entries",
                             "frame_tags=lavfi.signalstats.YAVG", "-of", "csv=p=0"], capture_output=True, text=True).stdout
    return [float(value.strip(",")) for value in output.split() if value.strip(",")]


def luma_per_second(clip, fps):
    values = series(clip, "signalstats")
    step = max(1, round(fps))
    return [round(sum(values[i:i + step]) / len(values[i:i + step])) for i in range(0, len(values), step)]


def scene_cuts(clip, fps, skip=30):
    values = series(clip, "scale=156:88,format=gray,tblend=all_mode=difference,signalstats")
    cuts = []
    for index in range(skip, len(values)):
        previous = sorted(values[max(0, index - 12):index])
        if values[index] > 15 and values[index] > 3 * max(1.0, previous[len(previous) // 2]):
            cuts.append(round((index + 1) / fps, 2))
    return cuts


def cmd_check(args):
    job = None
    if Path(args.target).is_file():
        clip = Path(args.target)
    else:
        state, _, path = resq.locate(LANE, args.target)
        if not state:
            sys.exit(f"không thấy job {args.target}")
        job = resq.read(path)
        clip = resq.at(job["output"])
    name = clip.stem
    out = Path(args.out or resq.lane_root(LANE) / "check" / name)
    out.mkdir(parents=True, exist_ok=True)
    info = resq.media_info(clip)
    fps = info["fps"]
    last = int(info["seconds"] * fps) - 1
    sheet = [int(fps * s) for s in (0.5, 3.5, 6.5)] + [last - 11]
    ffmpeg("-i", str(clip), "-vf", f"select='{'+'.join(f'eq(n,{n})' for n in sheet)}',scale=624:-2,tile=2x2",
           "-frames:v", "1", "-fps_mode", "passthrough", str(out / "sheet.jpg"))
    edges = [min(n, last) for n in EDGE_FRAMES]
    ffmpeg("-i", str(clip), "-vf", f"select='{'+'.join(f'eq(n,{n})' for n in edges)}',scale=416:-2,tile=4x3",
           "-frames:v", "1", "-fps_mode", "passthrough", str(out / "edges.jpg"))
    ffmpeg("-i", str(clip), "-vf", f"select='not(mod(n,{round(fps)}))',scale=312:-2,tile=5x2",
           "-frames:v", "1", "-fps_mode", "passthrough", str(out / "seconds.jpg"))
    for second in ("3.5", "8"):
        ffmpeg("-ss", second, "-i", str(clip), "-frames:v", "1", str(out / f"full{second}.jpg"))
    motion = camera_motion(clip)
    if motion:
        print(f"máy dời (so giây 1): lớn nhất {motion['camera_shift']:.0%} bề ngang, tỉ lệ ×{motion['scale']}, từng giây {motion['per_second']}")
    luma = luma_per_second(clip, fps)
    reference = sorted(luma[1:])[len(luma[1:]) // 2] if len(luma) > 1 else luma[0]
    drift = [index for index, value in enumerate(luma) if index and abs(value - reference) > 6]
    print(f"{clip}: {info['width']}×{info['height']} {fps} fps {info['seconds']} s")
    print(f"độ sáng/giây {luma} · lệch > 6 ở giây {drift or '-'} · cắt cảnh ở {scene_cuts(clip, fps) or '-'} s")
    print(f"ảnh: {out}/sheet.jpg (0.5/3.5/6.5 s/cuối) · edges.jpg (12 khung đầu/cuối) · seconds.jpg (mỗi giây) · full3.5.jpg full8.jpg")
    if job:
        print(f"job {job['id']} try{job['attempt']}/{job['max_attempts']} · ảnh nguồn {job['input']}")
        print(f"prompt: {job['prompt']}")
        for entry in job.get("history", []):
            print(f"   try{entry['attempt']} {entry.get('result')}: {entry.get('note')}")


def main():
    parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("candidates")
    command.add_argument("set")
    command.add_argument("--groups")
    command.add_argument("--limit", type=int)
    command.add_argument("--json", action="store_true")
    command.add_argument("--missing-clip", action="store_true", help="chỉ cảnh chưa có trường clip")
    command = commands.add_parser("clip")
    command.add_argument("set")
    command.add_argument("clips")
    command = commands.add_parser("draft")
    command.add_argument("set")
    command.add_argument("--limit", type=int, default=40)
    command.add_argument("--groups")
    command.add_argument("--dry-run", action="store_true")
    command.add_argument("--hold-min", type=int, default=4, help="đề tài đã duyệt ≥ N lượt clip…")
    command.add_argument("--hold-below", type=float, default=0.2, help="…và tỉ lệ đạt < R thì không thêm job mới")
    command = commands.add_parser("redraft")
    command.add_argument("set")
    command.add_argument("--dry-run", action="store_true")
    command = commands.add_parser("refix")
    command.add_argument("set")
    command.add_argument("--codes", default="camera-far", help="chỉ requeue job có mọi mã lỗi trong danh sách này")
    command.add_argument("--dry-run", action="store_true")
    command = commands.add_parser("add")
    command.add_argument("set")
    command.add_argument("jobs")
    command = commands.add_parser("work")
    command.add_argument("--port", action="append", required=True)
    command.add_argument("--page-id", action="append", default=[], help="PORT=TARGET_ID, lặp lại để chọn đúng các tab slot")
    command.add_argument("--seconds", type=int, default=300)
    command.add_argument("--drain", type=int, default=900)
    command.add_argument("--exit-when-empty", action="store_true")
    command.add_argument("--only", action="append", help="chỉ nhận / làm tiếp job của bộ này (lặp lại được); job bộ khác đang giữ để lần chạy sau")
    command = commands.add_parser("reconcile")
    command.add_argument("job")
    command.add_argument("--port", required=True)
    command.add_argument("--page-id", required=True)
    command.add_argument("--thread")
    command = commands.add_parser("check")
    command.add_argument("target")
    command.add_argument("--out")
    args = parser.parse_args()
    try:
        {"candidates": cmd_candidates, "clip": cmd_clip, "draft": cmd_draft, "redraft": cmd_redraft, "refix": cmd_refix, "add": cmd_add, "work": cmd_work, "reconcile": cmd_reconcile,
         "check": cmd_check}[args.command](args)
    except (resq.QueueError, Blocked, Uncertain, FetchFailed) as error:
        print(f"LỖI: {error}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()

---
name: video-resource-videos
description: Animate accepted resource images into short clips with muse.ai in existing Chrome tabs, through the shared resource queue - PM drafts one clip prompt per accepted image from the set's prompt template and the clip fields the image reviewer recorded, a generator loop drives every muse tab as a slot (new thread, attach PNG, send, poll, download native MP4, submit review), a reviewer checks frames and accepts, trims or sends back. Use when the PM or owner says "muse.ai", "tạo clip resource", "animate ảnh", "video từ ảnh", or asks to run/refill the video queue. Images come from video-resource-images.
---

# video-resource-videos

Clip cho một **bộ resource** bằng muse.ai, qua queue `videos`. Quy trình, vai và vòng PM / generator / reviewer:
[pm-production/references/resource-queue.md](../pm-production/references/resource-queue.md). Luật viết prompt và duyệt
clip của bộ: `<set>/resource.json` → `video.rules`.

```bash
V=.claude/skills/video-resource-videos/scripts/videos.py   # Codex: .agents/skills/…
python3 $V candidates <set> [--groups a,b] [--limit N] [--json] [--missing-clip]   # ảnh đạt chưa có clip, chưa vào queue
python3 $V draft <set> [--limit 40] [--groups a,b] [--dry-run]   # PM: ghép prompt từ trường clip + khuôn → input
python3 $V redraft <set> [--dry-run]                              # PM: khuôn đổi → ghép lại job clip còn ở input
python3 $V refix <set> [--codes camera-far] [--dry-run]           # PM: needs_fix chỉ có mã trong --codes → khuôn, đảo hướng máy, requeue
python3 $V clip <set> clips.jsonl                                 # ghi trường clip cho ảnh cũ {"theme","shot","clip"}
python3 $V add <set> jobs.jsonl                                   # PM: prompt tự viết {"theme","shot","prompt"}
python3 $V work --port 9224 --port 9226 --seconds 14400 --drain 900  # tiến trình nền: mọi tab muse.ai = một slot
python3 $V check <job|clip.mp4> [--out DIR]                       # reviewer: ảnh soi + số đo
python3 $V reconcile <job> --port P --page-id ID [--thread URL]   # PM: job stuck có thread → tải video → review
```

## Prompt clip

`draft` đọc khuôn `<set>/resource.json` → `video.prompt` (moves, sequence, forbid, fields) và trường `clip` trong thẻ
cảnh; chọn kiểu máy ít dùng nhất trong đề tài (cân bằng đa dạng; cảnh `deep` chỉ slide/arc); kiểm `forbid`. Ảnh thiếu
trường clip được báo ra để PM giao ghi bổ sung. Đề tài đã duyệt ≥ `--hold-min` lượt clip mà tỉ lệ đạt < `--hold-below`
thì `draft` không thêm job mới (báo "giữ lại"): loại cảnh muse làm hỏng thì không đốt thêm lượt + token duyệt.
`refix` lo lượt sửa của lỗi máy/khóa: đảo hướng máy ngay trong prompt cũ (giữ câu PM đã sửa); prompt không theo khuôn
thì ghép lại từ khuôn hiện hành (sửa câu chữ không làm muse nghe lời hơn); job có mã ngoài `--codes` được in ra để PM tự viết prompt sửa. PM chỉ tự viết prompt sửa đặc biệt.

## Một job (mỗi slot)

1. `claim` → tab về `muse.ai/thread/new` → đính PNG nguồn (đợi ảnh hiện trong ô chat) → gửi prompt bọc lời dặn
   image-to-video, một lượt; xác nhận tin nhắn trong thread, ghi `port`, `page`, `thread` vào job.
2. Vòng lặp chung poll mọi slot mỗi 10 s; có video → tải blob gốc → `<id>.tryN.mp4` (đo cỡ/fps/giây + máy dời) →
   `submit` → slot rảnh.
3. **Cổng đo máy:** `scripts/motion.py` (ORB + similarity, giây 1 so với từng giây sau, độ dời lớn nhất của 4 góc khung
   / bề ngang, và tỉ lệ zoom) ghi `meta.motion`; dời > `video.motion_reject` hoặc zoom > `video.zoom_reject` của bộ → `resq.py` cho redo `camera-far` ngay với tên
   `auto-motion` (note ghi số đo), không tốn lượt reviewer. Bộ không đặt `motion_reject` hoặc thiếu venv → bỏ qua cổng.
4. `Delivery not confirmed` → trả queue; quá 15 phút → trả queue, lần hai → `stuck`; không rõ đã gửi → `stuck`;
   rate limit / captcha / đăng xuất → dừng (mã 3), job đã gửi giữ nguyên để chạy lại làm tiếp.
   6 lần `Delivery not confirmed` liên tiếp không xen video nào (muse im) → dừng (mã 3) thay vì gửi lại mãi; PM chờ
   muse hồi rồi chạy lại. Mỗi tài khoản muse chạy tối đa 3 tab/cổng (4 tab làm muse ngừng trả lời).

Hết `--seconds` thì không nhận job mới, chờ job đang chạy tối đa `--drain` giây rồi thoát; chạy lại tự làm tiếp.

## Duyệt (reviewer)

`check` ghi `sheet.jpg` (0,5 / 3,5 / 6,5 s / cuối), `edges.jpg` (12 khung đầu/cuối), `seconds.jpg` (mỗi giây),
`full3.5.jpg`, `full8.jpg` và in máy dời (so giây 1), độ sáng từng giây, điểm cắt cảnh, prompt, các lượt trước. Ảnh nào reviewer phải
mở do `video.rules` của bộ quy định (mặc định ít ảnh nhất, mở thêm khi nghi). Đạt có thể kèm cắt
(`resq.py verdict … ok --trim-head S --trim-tail S`); queue từ chối nếu còn < `video.min_seconds_after_trim` giây.
Bản đạt (đã cắt) thành `<id>.mp4`; thẻ cảnh ghi `video` (status, trim, tries, thread).

## Môi trường

- Chrome muse 9224 và 9226 (qua proxy Mỹ, `us-proxy status` phải ra `US`), mỗi Chrome các tab muse.ai đã đăng nhập.
  `--page-id PORT=ID` (lặp lại) để chỉ dùng một số tab. Script không tạo/đóng tab, không đổi profile/proxy.
- `scripts/muse-chrome.sh` (CEO/PM mở Chrome muse khi cần), `scripts/window_snow.sh` (hậu kỳ trên GPU server: loop +
  tuyết chỉ trong ô kính cho cảnh trong nhà; không thuộc queue).
- `.venv` của skill (numpy, opencv-python-headless) cho `motion.py`: `python3 -m venv .venv && .venv/bin/pip install
  numpy opencv-python-headless`; đo một clip 10 s < 1 s trên Mac (12 khung 312 px). `ffmpeg`/`ffprobe` trên Mac.

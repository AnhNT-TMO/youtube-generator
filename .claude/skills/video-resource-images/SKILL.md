---
name: video-resource-images
description: Generate still images for a resource set (a folder with resource.json, shots.json and blocks.json) with ChatGPT in existing Chrome tabs, through the shared resource queue - PM fills the images queue with composed prompts, a generator loop claims jobs, sends one prompt per new chat, downloads the native PNG and submits it for review; a reviewer accepts or sends it back. Use when the PM or owner asks to create resource images, scene images, "tạo ảnh resource", "tạo ảnh cảnh", or to run/refill the image queue. Clips from the accepted images are video-resource-videos.
---

# video-resource-images

Ảnh cho một **bộ resource** bằng ChatGPT, qua queue `images`. Quy trình, vai và vòng PM / generator / reviewer:
[pm-production/references/resource-queue.md](../pm-production/references/resource-queue.md). Nội dung (cảnh, khối câu,
luật duyệt) nằm trong thư mục bộ: đọc `<set>/resource.json` trước.

```bash
I=.claude/skills/video-resource-images/scripts/images.py   # Codex: .agents/skills/…
python3 $I prompt <set> <nhóm/đề tài> <id>          # xem prompt ghép từ blocks.json + shots.json
python3 $I fill <set> --target 60 [--groups a,b]     # nạp input tới đủ 60 job chờ, xoay vòng qua các đề tài
python3 $I add <set> jobs.jsonl                      # PM: prompt tự viết {"theme","shot","prompt"}
python3 $I work --port 9223 --port 9225 --seconds 14400 --refill <set> --target 60   # tiến trình nền, tự fill khi < target/3
python3 $I reconcile <job> --port P                  # PM: job stuck đã có chat → tải ảnh trong chat đó → review
```

## Một job

1. `claim` (regen trước input) → điều hướng tab chatgpt.com về chat mới, chờ ô chat sẵn sàng.
2. Dán đúng prompt của job, kiểm chữ trong ô khớp từng ký tự, bấm Send; xác nhận tin nhắn + `/c/<id>` (ghi vào job).
3. Chờ ảnh sinh (tối đa 8 phút); tải PNG gốc trong trang → `<id>.tryN.png`; đo cỡ, cảnh báo nếu < `min_width` hoặc
   sai `ratio`; ẩn chat; `submit` → review. Không fit/upscale.
4. Lỗi: chưa gửi được → trả queue (không tốn lượt); ChatGPT không trả ảnh → `needs_fix`; không rõ đã gửi / quá giờ →
   `stuck`; hết lượt ảnh → trả job rồi dừng (mã 3); chưa đăng nhập / tab không đúng → dừng (mã 3); ChatGPT lỗi tạm
   ("Image generation failed / unavailable") → trả job, không tốn lượt; 3 lần liền ở một cổng → dừng (mã 3).
5. Reviewer cho đạt kèm các trường `image.card_fields` của bộ (vd. `clip`, để `videos.py draft` ghép prompt clip mà
   không ai phải mở lại ảnh).

Hết `--seconds` thì không nhận job mới, làm xong job đang dở rồi thoát; chạy lại tự làm tiếp job của chính worker.

## Môi trường

- Chrome ChatGPT 9223 và 9225, mỗi Chrome đúng một tab chatgpt.com đã đăng nhập (`--page-id PORT=ID` nếu có nhiều
  tab). Script chỉ gắn vào tab có sẵn qua CDP: không tạo/đóng tab, không đổi profile.
- `scripts/.venv` (websocket-client) tự dùng; thiếu thì script in lệnh tạo.
- Tài khoản dùng chung: chat được ẩn sau khi tải (`meta.hidden`); không xóa chat của người khác.

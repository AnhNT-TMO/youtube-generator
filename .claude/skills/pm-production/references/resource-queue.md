# Resource queue: tạo ảnh / clip nền bằng trình duyệt

Quy trình dùng chung cho mọi **bộ resource** (một thư mục có `resource.json`, ví dụ bộ cảnh mùa đông, mùa xuân…).
Skill chỉ giữ cách làm; nội dung (cảnh, khối câu, luật duyệt) nằm trong thư mục của bộ. Bộ mới = thư mục mới + `resource.json`.
Mục tiêu vận hành: ít token, chất lượng không đổi; lý do từng quyết định ghi trong file ghi chú tối ưu của bộ (nếu có).

## Bộ resource

```
<set>/
├── resource.json        # shots (glob); image {rules, review_section, min_width, ratio, codes, card_fields};
│                        # video {rules, prompt, min_seconds_after_trim, codes}
├── blocks.json          # khối câu ghép prompt ảnh (images.py prompt/fill)
├── <video.prompt>       # khuôn ghép prompt clip: moves, sequence, forbid, fields (videos.py draft)
├── <nhóm>/<đề tài>/shots.json   # defaults + danh sách cảnh {id, subject, …}
└── <nhóm>/<đề tài>/<id>.png|.mp4|.json   # bản đạt + thẻ cảnh; bản thử <id>.tryN.* tự xóa khi job done/failed
```

Ảnh đạt mới được làm clip. Thẻ cảnh `<id>.json` do queue ghi khi reviewer cho đạt (`image` + `qc` + các trường
`image.card_fields`, vd. `clip`; hoặc `video`).

## Queue

`production/resq/<lane>/` với lane `images` | `videos`; mỗi trạng thái một thư mục, mỗi job một file JSON, chuyển bằng
rename nguyên tử (không lock, các vai chạy song song như microservice). Nhật ký: `events.jsonl`; log generator:
`work.log`. Engine: `pm-production/scripts/resq.py` (`--help`).

```
PM/refill/draft ─▶ input ─┐                         ┌──▶ done      (bản đạt + thẻ cảnh)
PM requeue ─────▶ regen ──┴▶ working/<worker> ─▶ review ─▶ reviewing/<reviewer> ─┼──▶ needs_fix ─▶ PM requeue (prompt mới) ─▶ regen
                              │  │                                           └──▶ failed    (hết 3 lượt)
                              │  └─ release (chưa gửi / dịch vụ lỗi tạm) ─▶ input|regen
                              └──── stuck (không rõ đã gửi / đã tạo) ─▶ PM resolve
```

- Generator lấy `regen` trước `input`, cũ trước mới. Tối đa **3 lượt tạo** một cảnh; lượt N lưu `<id>.tryN.<ext>`.
- Nộp review xong là slot rảnh, nhận job tiếp ngay; review chạy song song, không chặn generate.
- Chỉ một vai được làm mỗi bước: PM `add/reprompt/requeue/reopen/fail/resolve` (`reopen`: job ở regen mà bản lượt trước
  vẫn còn và nay đạt luật mới → đưa bản đó về review, không tốn lượt); generator `claim/submit/no-output/release/stuck`;
  reviewer `next-review/verdict`. Không ai sửa file queue bằng tay.

## Vai

| Vai | Là gì | Token | Việc |
|---|---|---|---|
| Generator ảnh | tiến trình nền `images.py work --refill <set>` | 0 | hai Chrome ChatGPT, tự nạp queue từ `blocks.json` |
| Generator clip | tiến trình nền `videos.py work` | 0 | mọi tab muse.ai của hai Chrome, mỗi tab một slot |
| Reviewer ảnh / clip | sub-agent `resource-reviewer` (Opus, medium), **mỗi lượt một lô** | có | duyệt FIFO, verdict; ảnh đạt kèm trường clip |
| Ghi trường clip (ảnh cũ) | sub-agent `resource-reviewer`, lô ~30 | có | chỉ cho ảnh đã đạt trước khi có trường clip |
| PM | phiên chính | có | `draft`, prompt sửa, stuck, spawn reviewer, báo cáo |

Generator là script thuần (claim → gửi → tải → nộp), nên chạy thẳng bằng tiến trình nền, không cần agent LLM trông.
Codex hoặc môi trường không chạy nền được: dùng agent `resource_generator` chạy lặp lệnh `work` (như cũ).
Định nghĩa agent: `.claude/agents/resource-*.md`, `.codex/agents/resource_*.toml`.

`S` = thư mục skills đang dùng (`.claude/skills` hoặc `.agents/skills`); lệnh chạy từ gốc repo.

## PM

**Khởi động** (mỗi cổng chỉ một tiến trình `work`; kiểm `pgrep -fl "images.py work|videos.py work"` trước):

```bash
python3 $S/video-resource-images/scripts/images.py work --port 9223 --port 9225 --seconds 14400 --refill <set> --target 60 >> production/resq/images/work.log 2>&1
python3 $S/video-resource-videos/scripts/videos.py work --port 9224 --port 9226 --seconds 14400 --drain 900 >> production/resq/videos/work.log 2>&1
python3 $S/pm-production/scripts/resq.py watch --review 8 --needs-fix 5 --low videos=10
```

Cả ba chạy nền (Claude: Bash `run_in_background`); PM chỉ thức dậy khi một lệnh thoát.

**Khi `watch` thoát**, nó in lý do; xử lý đúng lý do đó rồi chạy lại `watch`:

- `REVIEW <lane> N` (review chờ ≥ 8 và không reviewer nào chạy) → spawn một reviewer cho lane đó (mục *Spawn*), rồi chạy
  lại `watch … --started <lane>` (reviewer mới chưa kịp nhận job thì không báo lại).
- `LOW videos N` → `videos.py draft <set> --limit 40` (ghép prompt từ trường clip, kiểu máy cân bằng). Báo thiếu trường
  clip → spawn agent ghi trường clip cho ảnh cũ (`candidates --missing-clip`, lô ~30).
- Sửa khuôn prompt của bộ (lỗi lặp lại ở nhiều job) → `videos.py redraft <set>` ghép lại mọi job clip còn ở input theo
  khuôn mới (`resq.py reprompt`, không tốn lượt; job generator vừa nhận thì giữ nguyên).
- `FIX videos N` → trước hết `videos.py refix <set> --codes camera-far,camera-still,morph,indoor-particles,people` (ghép lại từ
  khuôn, đảo hướng máy; câu khóa của khuôn đã cấm các lỗi này); job nó in `PM:` mới xử lý tay như dưới. Note
  reviewer gợi ý câu sửa cụ thể (vd. phố vắng người) → sau refix sửa thêm bằng `resq.py reprompt` (nhận cả job ở regen).
- `FIX <lane> N` → `resq.py list <lane> needs_fix --full` → đọc note + codes (không mở ảnh/clip trừ khi note không rõ) →
  viết prompt sửa: khác prompt cũ, chỉ đổi câu gây lỗi (luật sửa trong `video.rules` / `image.rules` của bộ) →
  `resq.py requeue <lane> <job> --prompt-file F --note "…"`. Lỗi không sửa được bằng prompt → `resq.py fail`.
- `STUCK <lane> N` → đọc `phase_note`. Có conversation/thread → `images.py reconcile` / `videos.py reconcile` (chỉ khi
  generator của cổng đó đã dừng, vì reconcile dùng chung tab). Chứng minh chưa gửi → `resq.py resolve --to input|regen`.
  Đã tạo nhưng mất → `--to needs_fix`.
- `IDLE` → hết việc: báo CEO.

**Khi generator thoát:** mã 3 (`BLOCKED`: đăng nhập, captcha, hết lượt, ChatGPT lỗi tạm 3 lần liền, tab mất) → báo CEO
nguyên văn, không chạy lại tới khi CEO xử lý; thoát bình thường (hết giờ) → chạy lại nếu queue còn việc.

**Báo CEO** ngắn: đạt / chờ / làm lại / hỏng mỗi lane (`resq.py board`), mã lỗi chính, việc cần CEO.
PM không tự duyệt thay reviewer; PM chịu chất lượng qua khuôn prompt và prompt sửa.

## Generator (tiến trình)

- `work` tự làm tiếp job dở của chính worker, nên chạy lại bao nhiêu lần cũng an toàn; job đang chạy trong muse vẫn được
  nhận về ở lần chạy sau.
- `images.py work --refill <set>`: queue chờ < target/3 thì tự `fill` tới target, lấy xoay vòng qua các đề tài (đa dạng).
- ChatGPT lỗi tạm ("Image generation failed / unavailable") → trả job, không tốn lượt; 3 lần liền ở một cổng → mã 3.
- Không viết/sửa prompt, không duyệt, không mở/đóng tab, không đổi Chrome/profile/proxy.

## Reviewer

Mỗi lượt spawn duyệt **một lô tối đa 12 job** rồi thoát (queue chặn bằng `--batch`, đếm theo tên reviewer nên PM đặt
tên mới mỗi lượt spawn, vd. `videos-r<giờphút>`) (ngữ cảnh mới mỗi lô, không cộng dồn ảnh của các lô trước).

1. `python3 $S/pm-production/scripts/resq.py next-review <lane> --reviewer <tên> --wait 120 --batch 12` → in job (hoặc `BATCH_DONE` / thoát
   không có gì → dừng, báo cáo).
2. **Ảnh:** Read file `output` của job; so với `card_seed.subject`, README của đề tài và mục `image.review_section` trong
   `image.rules` của `resource.json`; `meta.warnings` (cỡ/tỉ lệ) là lỗi `format`.
   **Clip:** `python3 $S/video-resource-videos/scripts/videos.py check <job>` rồi Read các ảnh soi mà `video.rules` yêu cầu.
3. Verdict, mỗi job một lệnh:

```bash
resq.py verdict images <job> --reviewer <tên> ok --note "<mô tả ngắn>" --card '{"clip": {…}}'   # trường theo image.card_fields
resq.py verdict videos <job> --reviewer <tên> ok --note "…" --trim-head 1 [--trim-tail S]
resq.py verdict <lane> <job> --reviewer <tên> redo --note "<lỗi gì, ở đâu, gợi ý sửa>" --codes a,b
```

- Cắt chỉ khi phần còn lại ≥ `video.min_seconds_after_trim` (script từ chối nếu ít hơn → chọn redo).
- `codes` lấy từ `resource.json` của lane. Không viết prompt, không requeue.

## Spawn (PM)

Claude (Agent tool, chạy nền):

```
subagent_type: resource-reviewer · prompt: "Lane images, reviewer images-r<HHMM>. Bộ: <set>. Một lô ≤ 12 job."
subagent_type: resource-reviewer · prompt: "Lane videos, reviewer videos-r<HHMM>. Bộ: <set>. Một lô ≤ 12 job."
subagent_type: resource-reviewer · prompt: "Ghi trường clip cho ≤ 30 ảnh cũ của bộ <set>: videos.py candidates <set>
  --missing-clip --json --limit 30 → Read từng ảnh → jsonl {theme, shot, clip} → videos.py clip <set> <file>."
```

Mỗi lane tối đa một reviewer cùng lúc (`watch` chỉ báo `REVIEW` khi lane không có reviewer chạy).
Clip có cổng đo máy tự động (`video.motion_reject` của bộ): clip dời quá ngưỡng thành redo `camera-far` dưới tên
`auto-motion` trước khi reviewer thấy; reviewer chỉ duyệt clip qua cổng.
Codex: `agent_type="resource_reviewer"` (và `resource_generator` khi không chạy nền được), cùng prompt; skills ở `.agents/skills`.

## Trình duyệt

- Chrome ảnh 9223 / 9225 (mỗi Chrome đúng một tab chatgpt.com); Chrome muse 9224 / 9226 (tab muse.ai = slot). CEO mở và
  đăng nhập; script không tạo/đóng tab, không đổi profile/proxy. Muse cần IP Mỹ (`us-proxy status`).
- ChatGPT: một chat mới mỗi job; tải PNG gốc; ẩn chat sau khi tải. Hết lượt ảnh → generator ảnh dừng (mã 3).
- Muse: một thread mới mỗi job, đính PNG, gửi prompt kèm lời dặn image-to-video; `Delivery not confirmed` → trả queue;
  quá 15 phút → trả queue một lần, lần hai → stuck.
- Không rõ đã gửi hay chưa → stuck, không bao giờ tự gửi lại.

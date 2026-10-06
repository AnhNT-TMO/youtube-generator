---
name: video-upscale
description: Upscale short video clips (resource library clips, any folder in the repo) to 1920×1080 with SeedVR2 3B on the GPU server, in batches of ~10 clips per model load, with a thermal watchdog that pauses the job while the GPU is hot. Outputs land in the server library ~/video_sources/<library>/<path inside the resource set> (library from the set's resource.json, e.g. christmas), same tree as the Mac. Use when the PM or owner says "upscale video", "upscale clip", "nâng clip lên 1080p", "SeedVR2 video", or asks for status/stop/pull of an upscale run. Choosing WHICH clips to upscale is a PM decision made before running this skill.
---

# video-upscale

Upscale clip lên **1920×1080** bằng **SeedVR2 3B fp16** trên GPU server. Chỉ là bước kỹ thuật: clip nào cần upscale,
upscale lúc nào là PM quyết (brief / queue), skill không tự chọn. Lý do chọn model, config và số đo:
[references/benchmark.md](references/benchmark.md).

```bash
U=.claude/skills/video-upscale/scripts/upscale.py   # Codex: .agents/skills/video-upscale/scripts/upscale.py
python3 $U setup                                     # một lần / khi hỏng (repo SeedVR2 đã vá, .venv, model 3B)
python3 $U run image_source/travel image_source/grand/grand-library   # push + chạy nền; chạy lại = làm tiếp
python3 $U night --first production/montage/<album>/clips.txt   # lượt đêm (mặc định cách chạy, xem dưới)
python3 $U status                                    # tiến độ, nhiệt độ, cụm đang chạy, clip lỗi, guard kills
python3 $U log 60                                    # log tổng
python3 $U stop                                      # dừng; clip đã xong giữ nguyên
python3 $U pull image_source/travel --dest ~/Desktop/upscaled   # kéo kết quả về Mac, giữ cây thư mục
```

`PATH` là đường dẫn tương đối từ gốc repo (file hoặc thư mục; chạy từ thư mục khác cũng được, script tự đổi). Bản gốc
lên server ở `~/video-upscale/src/PATH` (tạm, xóa khi đạt). **Bản 1080p ở kho `~/video_sources/<library>/<đường dẫn trong
bộ>`**: mỗi bộ resource ghi `"library"` trong `resource.json` (vd. `image_source` → `christmas`, sau này `winter`,
`nature`…), nên `image_source/home/bedroom/bedroom-04.mp4` → `~/video_sources/christmas/home/bedroom/bedroom-04.mp4`
(cây thư mục như Mac). Clip ngoài bộ có `library` → `~/video_sources/_other/PATH`. Mỗi lần chạy, Mac ghi bản đồ bộ →
library vào `~/video-upscale/libraries.json`. Chỉ lấy `*.mp4`; bỏ `*.try*` và thư mục `_rejected/`. Bộ mới: thêm
`"library"` vào `resource.json` trước lượt upscale đầu.

## Một lượt `run`

1. `push`: rsync clip lên `src/` (chỉ file mới/đổi). `--no-push` khi clip đã ở server.
2. Server chạy nền unit `video-upscale` (ngoài `youtube.slice`, chỉ điều phối, ≤ 2 GB RAM). Clip đã có bản 1080p trong `~/video_sources` thì bỏ qua,
   nên chạy lại sau khi dừng/lỗi là làm tiếp.
3. Gom clip theo **batch tối ưu cho độ dài** (batch 4n+1 ≤ 113, ít frame phải tính nhất; 216 frame → 113, 192 → 101,
   120 → 65), chia **cụm ≤ `--per-run` clip** (mặc định 10). Mỗi cụm = một lần nạp model = một scope trong `youtube.slice`
   (lính canh `youtube-guard` canh như mọi job; scope ngắn nên không chạm trần 4 giờ).
4. Trong scope: ffmpeg Lanczos phủ 1920×1080 + cắt giữa (lossless, bỏ audio) → SeedVR2 (`--cache_dit --cache_vae
   --compile_vae`, không chunk, overlap 4, prepend 4, màu `lab`) → NVENC HEVC 10-bit cq 14.
5. Kiểm từng clip: 1920×1080 và **số frame bằng bản gốc** → chuyển vào `~/video_sources/<library>/…`; sai thì ghi lỗi vào
   `log/clips.jsonl`, lượt sau làm lại. Hai cụm liền không ra clip nào → dừng hẳn (xem `log/chunk-NNN.log`,
   `guard.sh kills`).
6. **Server dùng chung, nhường người khác (CEO 2026-10-06):** cụm chỉ bắt đầu khi GPU trống ≥ `--need-free-gb` (80 GB;
   job dùng ~74 GB). Thiếu = người khác đang dùng GPU → chờ (`status` phase `waiting_gpu`, kiểm mỗi `--gpu-poll` 60 s,
   đủ 2 lần liền mới chạy). Cụm hỏng vì hết VRAM (người khác chiếm giữa chừng) không tính là lỗi: chờ rồi chạy lại đúng
   cụm đó. Không bao giờ dừng hay kill job của người khác; lính canh giữ nguyên.

## Lượt đêm (`night`) — cách chạy mặc định

Upscale chạy **ban đêm, độc lập với Mac**: unit systemd user trên server + `loginctl enable-linger` (lệnh `night` kiểm
`Linger=yes`, thiếu thì dừng), không cần giữ ssh hay mở máy.

- Mỗi đêm **200 clip** (`--batches 20` × `--per-run 10`, ~140 s/clip ≈ 8–10 giờ). Clip gom theo độ dài (batch) nên số
  cụm thực tế thường > 20 (vd. 24); lượt đêm chạy hết mọi cụm của 200 clip đó.
- **GPU nghỉ `--rest 60` s sau mỗi cụm**, cộng điều kiện ≤ 60 °C trước cụm mới.
- **Album trước, kho sau (CEO 2026-10-06):** clip trong `--first` (cast album đang làm) là **tầng 1**: luôn chạy hết
  (không tính vào trần 200), gom cụm riêng, không trộn với clip kho. Xong tầng 1 thì runner **nhường GPU cho unit
  `montage-render`** (video 4K album, `montage.py render` xếp sẵn và tự chờ đủ clip) tới khi render xong, rồi mới upscale
  tầng 2. Clip tầng 1 nào lỗi thì không chờ render, lượt sau làm lại. Mỗi ngày: `night --first <clips.txt của album>` +
  `montage.py render <album> --channel <ch> --audio <master>` (thứ tự bất kỳ).
- Thứ tự: clip trong các file `--first` (cast album đang làm, theo thứ tự file) rồi **mọi clip đạt**
  (`video.status` ok) của `--set` (mặc định `image_source`) theo đường dẫn; clip đã có trong `~/video_sources` bị bỏ. Chạy đủ các đêm
  thì server có bản 1080p của toàn bộ kho.
- Server **chỉ giữ bản 1080p** ở `~/video_sources/<library>/` (cây thư mục như Mac): clip đạt thì xóa bản gốc ở `src/` (`--keep-src` để giữ).
- Danh sách của đêm: `~/video-upscale/log/night-<giờ>.txt`. Sau khi chạy, kiểm 3 cụm đầu (`status`, `log`): 10/10 đạt,
  có nghỉ 60 s, `src/` giảm, `~/video_sources/<library>/` đúng cây; lỗi thì sửa ngay trước khi để chạy cả đêm.

## Lính canh nhiệt

Luồng canh đọc nhiệt GPU mỗi 3 s: **≥ `--pause-c` (83 °C)** → `SIGSTOP` cả scope (SeedVR2 + ffmpeg) → chờ **≤
`--resume-c` (70 °C)** → `SIGCONT`. **Cụm mới chỉ bắt đầu khi GPU ≤ `--start-c` (60 °C)**; `--rest S` thêm giây nghỉ cố
định giữa hai cụm. `setup` đặt `gpu_temp_c` của `youtube-guard` lên 88 °C để lính canh upscale luôn nghỉ trước khi guard
kill; guard đặt thấp hơn thì ngưỡng nghỉ tự hạ xuống `gpu_temp_c − 2` và log báo. `status` ghi số lần nghỉ và tổng giây nghỉ.

## Bao nhiêu clip một cụm

Nạp model + compile VAE ≈ 30–40 s mỗi cụm; một clip 9 s ≈ 140 s. Cụm 10 clip → phí nạp ~3 %, cụm 20 → ~1,5 %. Cụm lớn
hơn không nhanh thêm đáng kể nhưng mất nhiều việc hơn khi bị kill và giữ RAM lâu hơn → **mặc định 10**; muốn ít cụm hơn
dùng 15–20. Không vượt ~80 (trần 4 giờ/scope của lính canh).

## Môi trường

- `remote.env` (chép `remote.env.example`): `VU_REMOTE`, `VU_KEY`. Server: `~/video-upscale/` chỉ là công cụ (`seedvr2/` đã vá,
  `.venv/`, `models/seedvr2/`, `src/` + `work/` tạm, `log/master.log`, `log/clips.jsonl`, `status.json`, `libraries.json`);
  kết quả ở `~/video_sources/`.
- `setup` clone SeedVR2 commit cố định, vá (NVENC writer, bỏ 4 frame prepend bị sót, VAE `conv/norm_max_mem` 8 GB), cài
  `.venv` torch cu128, model hard-link từ `~/thumbnail-prompt/models/seedvr2` nếu có (không tải lại), đặt
  `gpu_mem_gb ≥ 90` và `gpu_temp_c ≥ 88` cho `youtube-guard` (job dùng ~74 GB VRAM; mặc định 60 sẽ kill).
- GPU chỉ chạy **một** lượt `run` một lúc (unit `video-upscale`); không chạy song song với render/upscale nặng khác.
- Server không kết nối được → job chờ, không chạy trên Mac.

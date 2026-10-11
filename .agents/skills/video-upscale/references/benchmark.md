# video-upscale: vì sao config này

Đo trên GPU server (RTX PRO 6000 Blackwell 96 GB, trần công suất 450 W) ngày 2026-10-04, clip muse 1248×704, 24 fps,
216 frame (9 s). Lab: `~/upscale-lab/video/` (`bench.sh`, `results.jsonl`, bản vá thử `seedvr2-lab/`).

## Quyết định

- **3B fp16, ra 1080p** (CEO 2026-10-04): clip là cảnh không người, vibe hơn độ nét; mắt thường không phân biệt 3B và 7B
  ở 1080p. 7B chỉ đều khung hơn chút, chậm hơn ~9 % và cùng config chạm trần RAM 40 GB/job của lính canh.
- Lên 1440p/4K khi đăng là bước Lanczos riêng sau này, không thuộc skill.

## Số đo (1 process, 1 clip trừ khi ghi)

| Config | Giây | VRAM đỉnh |
|---|---|---|
| Pilot 7B 1440p, batch 121, chunk 121 (bản Codex đầu tiên) | ~570 | gần đầy |
| 3B b113, VAE mem 0,5 GB mặc định | 190 | 49 GB |
| 3B b221 | 191 | 97 GB |
| 3B b113, VAE mem 8 GB | 164 | 72 GB |
| + sageattn_2 | 166 | 72 GB |
| + cuDNN benchmark | 602 | 97 GB |
| 4 clip/process, `--cache_dit --cache_vae` | 640 (160/clip) | 72 GB |
| + `--compile_vae` | 602 (150/clip) | 73 GB |
| + NVENC writer | 582 (~140/clip, ~139 khi nạp xong) | 74 GB |
| + `--compile_dit` | crash ở clip 2 (CompatibleDiT len) | — |

- Ở 1080p **VAE là cổ chai** (encode ~30 s + decode ~70–80 s mỗi clip; DiT ~25–30 s), nên đổi model hay attention
  gần như không đổi thời gian; VAE mem 8 GB và compile VAE mới có lợi.
- **Không dùng `--chunk_size`** với clip ngắn: chunk + prepend làm 216 frame thành 363 frame phải tính.
- Batch phải 4n+1; số frame thật phải tính = `b·ceil(frames / (b − 4))` (prepend 4 = overlap 4). Clip ngắn chọn batch
  nhỏ hơn (192 → 101, 120 → 65) thay vì đệm lên 226.
- Bỏ audio không nhanh hơn (mux audio < 1 s), nhưng clip resource không cần audio nên bỏ luôn.
- Muốn VRAM < 60 GB (để chạy song song việc GPU khác): VAE mem 0,5 GB, chậm hơn ~16 %.

## ≤ 30 GB VRAM (CEO 2026-10-06, config hiện hành)

Server dùng chung: job 74 GB phải chờ người khác (đêm 10-05 chờ 2,4 giờ). Đo 2 clip 216 frame/process, trần 28,5 GiB,
mọi config có offload DiT/VAE/tensor về CPU + `expandable_segments` (thiếu nó clip thứ 2 OOM vì phân mảnh). SSIM so với
bản production 1080p (Lanczos so với production = 0,90); soi crop: production, b61, b45 giống nhau, Lanczos mềm hẳn.

| Config 1080p | VRAM đỉnh | s/clip | SSIM |
|---|---|---|---|
| b113 / b77 + tile VAE | OOM ở DiT | — | — |
| **b77 + tile VAE + swap 16** (chọn) | 28,4 GiB | ~208 | 0,96 |
| b61 + tile VAE | 27,6 GiB | ~215 | 0,955 |
| b45 + tile VAE | 23,4 GiB | ~240 | 0,95 |
| b61 + tile + `--compile_vae` / tile 1536 + VAE mem 2 GB | OOM | — | — |

| Config 2K (2560×1440) | VRAM đỉnh | s/clip |
|---|---|---|
| b41 + tile + swap 24 | 26,9 GiB | ~386 |
| b33 + tile | 26,5 GiB | ~430 |
| b25 + tile | 23,6 GiB | ~432 |

- Cổ chai mới là VAE decode có tile (~116 s/clip 1080p; encode ~50 s, DiT ~32 s). 2K ≈ 2× thời gian 1080p.
- Bảng dưới (74 GB) là config cũ, giữ để so; nay là profile `full`.
- Các config dùng được đã thành `--profile` (`shared`, `low`, `full`, `2k`) trong `upscale_server.py`.
- Bench lại: chép `scripts/bench_server.py` + `bench-configs.json` lên `~/upscale-lab/vram/`, chép repo
  `~/video-upscale/seedvr2` sang `~/upscale-lab/vram/seedvr2`, đặt clip gốc ở `src/`, rồi
  `python3 bench_server.py bench-configs.json ~/video_sources/<library> <đường dẫn clip trong bộ>... [--only TÊN]`
  (chạy trong youtube.slice). Mỗi config ghi một dòng `results.jsonl`: s, VRAM đỉnh (nvidia-smi), số frame, SSIM so production.
- Trần công suất GPU 450 W là do mình đặt (`sudo nvidia-smi -pl 450`, 2026-10-04, lúc thử nhiệt); mặc định của card 600 W.
  Lên 600 W ước nhanh thêm ~5–10 % (VAE decode phụ thuộc băng thông bộ nhớ) nhưng nóng hơn, dễ chạm ngưỡng nghỉ 83 °C.

## Lỗi của SeedVR2 commit 4490bd1f đã vá

- Đường single-GPU (`_stream_video_chunks`) không bao giờ cắt 4 frame prepend → output dư 4 frame đầu (220 thay vì
  216), lệch thời gian với bản gốc. Vá: cắt `prepend_frames` sau chunk đầu (trừ worker multi-GPU, nhánh đó đã tự cắt).
- Writer ffmpeg dùng libx265 medium crf 12 trên CPU → đổi sang `hevc_nvenc` p5 hq cq 14 10-bit, tag `hvc1`.

## Nhiệt

Chạy liên tục GPU đứng ở 78–79 °C (bị giới hạn công suất 450 W), ngưỡng hãm xung của card ~93 °C. Lính canh nhiệt
nghỉ ở 83 °C, chạy lại ở 70 °C, cụm mới chờ ≤ 60 °C (CEO 2026-10-04: phòng server mát, về 60 °C nhanh); guard kill ở 88 °C.

## Thời lượng ước tính

~140 s/clip 9 s → ~25 clip/giờ → 432 clip ≈ 17 giờ (pilot 7B 1440p ≈ 68 giờ).

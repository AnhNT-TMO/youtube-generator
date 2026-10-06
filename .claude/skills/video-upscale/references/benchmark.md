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

## Lỗi của SeedVR2 commit 4490bd1f đã vá

- Đường single-GPU (`_stream_video_chunks`) không bao giờ cắt 4 frame prepend → output dư 4 frame đầu (220 thay vì
  216), lệch thời gian với bản gốc. Vá: cắt `prepend_frames` sau chunk đầu (trừ worker multi-GPU, nhánh đó đã tự cắt).
- Writer ffmpeg dùng libx265 medium crf 12 trên CPU → đổi sang `hevc_nvenc` p5 hq cq 14 10-bit, tag `hvc1`.

## Nhiệt

Chạy liên tục GPU đứng ở 78–79 °C (bị giới hạn công suất 450 W), ngưỡng hãm xung của card ~93 °C. Lính canh nhiệt
nghỉ ở 83 °C, chạy lại ở 70 °C, cụm mới chờ ≤ 60 °C (CEO 2026-10-04: phòng server mát, về 60 °C nhanh); guard kill ở 88 °C.

## Thời lượng ước tính

~140 s/clip 9 s → ~25 clip/giờ → 432 clip ≈ 17 giờ (pilot 7B 1440p ≈ 68 giờ).

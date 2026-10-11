---
name: upscale-lab
description: "4K thumbnail upscaler research (2026-09-24) → SeedVR2 7B chosen and wired into thumbnail-prompt `thumb.py fit`; why, pitfalls, open 1080p-video question"
metadata:
  node_type: memory
  type: project
  originSessionId: 86cf104b-a030-4e6f-bfc0-52a91b2f77ef
  modified: 2026-10-11T03:05:58.765Z
---

2026-09-24: tested GPU upscalers for ChatGPT thumbnails (1672×941 → 3840×2160) on the server; owner approved
**SeedVR2 7B fp16** and it is now the default in thumbnail-prompt: `thumb.py fit` crops 16:9 on the Mac, upscales on the
server in `~/thumbnail-prompt/` (`upscale_server.py`, repo pinned 4490bd1f, own .venv, models/seedvr2 7B + VAE),
pulls back a 4K `thumbnail.png` (kept on the Mac) + `thumbnail.jpg` ≤ 2 MB. `--no-upscale` = 1080p Lanczos fallback.
~1 min per image (≈35 s is model load). `thumb.py upscale-setup` reinstalls.

- Why 7B: most new detail, keeps colour/tone, the singer's identity on small faces, crisp text without halos.
  3B / 7B-sharp: "wormy" skin; UltraSharpV2: cross-hatch skin grain + dark halo on letters; Real-ESRGAN: plastic skin,
  tone shift; SUPIR (SDXL): softer and ~230 s/img. Diffusion scores low on synthetic PSNR tests — expected, judge by eye.
- SeedVR2 rounds odd sizes → feed it input pre-resized to the exact even target.
- Server HF downloads: single connections ~1 MB/s and hang → parallel Range downloader with retries (in upscale_server.py).
- Lab leftovers: `~/upscale-lab/` holds only scripts + results.json; models/venvs deleted.
- Video is 4K too (owner 2026-09-24): video-generator renders 3840×2160; `_px` settings stay in 1080p units and
  `config.load()` scales them ×2. Encode = NVENC on the server GPU (x264 4K ate ~100 GB RAM); frame compositing stays on
  CPU (GPU version `effects_gpu.py` is pixel-identical but slower with 16 processes, opt-in `VG_GPU=1`). See [[gpu-first-resource-cap]].
- First real run (album 002 + singles 004–006, 2026-09-24): ChatGPT gen ~4 min/image set (sequential, one Chrome tab),
  fit+upscale ~30 s, 4K zips on S3 (album 2.0 GB).

- Video clip upscale bench (2026-10-04, `~/upscale-lab/video/`: bench.sh, results.jsonl, patched copy `seedvr2-lab/`):
  at 1080p the VAE (encode ~30 s + decode ~70–80 s per 9 s clip) is the bottleneck, DiT only ~25 s → 3B vs 7B, sageattn
  barely matter. Wins: no `--chunk_size` (chunk+prepend padded 216 → 363 frames), batch 113, VAE conv/norm_max_mem 0.5→8,
  `--compile_vae`, one process per folder with `--cache_dit --cache_vae`, NVENC writer → ~140 s/clip (pilot 7B 1440p ~570 s).
  Losers: cuDNN benchmark (602 s), `--compile_dit` + cache crashes. Non-chunk mode keeps the 4 prepend frames → trim start_frame=4.
  Quality comparison for owner: `research/upscale-video/`.
- CEO decision 2026-10-04: resource clips → SeedVR2 **3B @1080p** (scenes, no people; vibe over sharpness; 7B only
  marginally steadier, +9 % time, hit the guard's 40 GB job-RAM cap). Christmas video upload res still open: 1440p vs
  4K (lanczos from the 1080p clips either way); PM leans 4K (TV viewers, pipeline already 4K) unless disk/upload pinches.

- Skill `video-upscale` (2026-10-04): `upscale.py setup/push/run/status/stop/pull`, server ~/video-upscale/{src,out}/<repo path>,
  cụm 10 clip/lần nạp, batch theo độ dài, vá prepend + NVENC, lính canh nhiệt SIGSTOP (≥83 °C hoặc guard−2, chạy lại ≤70).
  Clip nào upscale = PM/CEO chọn ở session khác (album 1).
- CEO 2026-10-06: shared GPU → upscale must stay ~≤30 GB VRAM, slower OK. Config now b≤77 + VAE tile + blocks_to_swap 16 +
  offload cpu + VAE mem 0.5 + expandable_segments (~28.4 GiB, ~210 s/clip; old 74 GB/140 s). Guard gpu_mem_gb = 40 (CEO OK'd
  global). `night --until "YYYY-MM-DD HH:MM"` = continuous run of all missing clips to a deadline; goal: whole library at
  1080p within 1–2 days then free the server. 2K numbers in references/benchmark.md (b41+swap24 ~386 s/clip, 27 GiB).
  Researched configs saved as `--profile shared|low|full|2k` (run/night/status/pull) + scripts/bench_server.py and
  references/bench-configs.json. GPU power cap 450 W was set by OUR account (sudo nvidia-smi -pl 450, 2026-10-04);
  CEO 10-06: run at 600 W (default). Solo shared profile: 83/70 °C ≈ 204 s/clip, 86/80 °C ≈ 187 s/clip. Full profile at
  600 W spikes 82→88 °C in 2 s → guard killed a chunk at 3 s poll; now poll 1 s, pause 84/resume 78. CEO rule: if guard
  kills on heat → drop to 500 W for the night, restore 600 W when the run ends.

- CEO 2026-10-04 night-run rule: upscale runs overnight via `upscale.py night` (20 cụm × 10 clip, GPU rests 60 s after
  each cụm, album cast first then all accepted clips in path order), unit survives Mac off (server linger=yes); server keeps
  only 1080p, since CEO 10-05 in ~/video_sources/<library>/ (library field in the set resource.json: image_source → christmas; future winter/, nature/ for Everstill) mirroring the Mac tree (src deleted on success); goal = whole library (~1000) upscaled; PM checks the
  first 3 cụm each night and fixes fast. Same pattern for future nights.
- Montage final (CEO 2026-10-04): `montage.py render <name> --intro-logo channel/<ch>/branding/avatar-circle-2560.png`
  queues after video-upscale, refuses if any cast clip missing, composes 1080p → Lanczos scale_cuda 4K, HEVC cq 24, silent,
  stays on server (no S3 until music). Opening = CEO-approved 'time stands still' intro (clock-sweep ring reveals logo, star flare, name letter-by-letter, gold line, tagline; ~4.8 s) from channel/<ch>/intro.json via `--channel <ch>`; reuse for every long album. Guard job RAM cap now 50 GB.
- 2026-10-11 Short 4K (vertical, ad-hoc outside runner): `full` profile (no offload, vae_mem 8) with batch 85 on
  240-frame clips peaked 93.6 GB → guard kill (>90); batch 45 holds ~88.5 GB. Without the runner's thermal pause the GPU
  hits 88 °C → guard kill; ad-hoc runs need their own STOP ≥83 / CONT ≤70 loop, one clip per process (~3 min/clip).
  Short 4K flow used: SeedVR2 clips → 1080×1920, render at 2160×3840 with overlays drawn at 2× (cd_text.py arg 3).

Related: [[gpu-render-server]] [[heavy-work-on-server]] [[run-flow-before-improving]]

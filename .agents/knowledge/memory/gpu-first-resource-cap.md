---
name: gpu-first-resource-cap
description: "On the shared GPU server, heavy work runs on the GPU whenever it can; all project tasks together stay under ~60 % CPU and 60–70 % RAM (youtube.slice)"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 86cf104b-a030-4e6f-bfc0-52a91b2f77ef
  modified: 2026-09-28T02:17:37.758Z
---

On the LAN server, every heavy task that can run on the GPU must run on the GPU (encode with NVENC, models on CUDA,
image/video compositing on torch CUDA where feasible); the GPU is mostly idle and few people use it.
All tasks of this project together may use at most ~50–70 % of the server's CPU and RAM: every skill's heavy remote
command runs inside the systemd user slice `youtube.slice` (CPUQuota 60 % of cores, MemoryHigh 60 %, MemoryMax 70 %),
added by the `LIMIT` prefix in each runner (video.py, thumb.py, the three remote.sh).

**Why:** (owner, 2026-09-24) two parallel 4K x264 renders pushed load to 600+ and ate ~100 GB RAM on a server shared
with other users, while the GPU sat at 0 %.
Per job (owner, 2026-09-28): the server has 48 cores, one job may use up to 24 (`systemd-run … -p CPUQuota=2400%` inside
the slice + `OMP/OPENBLAS/MKL_NUM_THREADS` ≤ 24). An ad-hoc numpy script without a thread cap spawned 142 threads and took
the whole 28.8-core slice for 12 min (load 46/48); capped + vectorised it took 43 s on 4 cores.

**How to apply:** new heavy scripts get a GPU path first and run through the slice; don't fan out parallel jobs that
bypass it; say when something must stay on CPU and why.

Related: [[heavy-work-on-server]] [[gpu-render-server]] [[upscale-lab]]

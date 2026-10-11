---
name: shared-gpu-yield
description: "CEO 10-06 — server is shared; when other users occupy the GPU our jobs wait for them, never kill/stop theirs; guard stays as is"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 4168c5ca-072c-425d-850c-01a77092ff22
  modified: 2026-10-05T23:51:37.471Z
---

The GPU server is shared with other people. When someone else's job holds the GPU, our jobs pause and wait until it is freed, then continue; never stop, kill or ask to kill their job. Keep youtube-guard unchanged.

**Why:** CEO 2026-10-06 after an upscale night run died from OOM because another user's job took 52 GB VRAM — "dùng chung nên không thể tránh được".

**How to apply:** GPU runners check free VRAM before each unit of work and wait (video-upscale: `--need-free-gb 80`, phase `waiting_gpu`; OOM chunk = wait + retry, not a failure). New GPU scripts should do the same. Related: [[server-guard]], [[gpu-first-resource-cap]].

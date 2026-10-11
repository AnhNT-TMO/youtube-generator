---
name: thumb-generation-tool
description: "~/Desktop/thumb-generation — standalone tool outside the repo: low-res image → SeedVR2 4K upscale → 5-min effect video (snow directions, spectrum if audio) on the GPU server"
metadata:
  node_type: memory
  type: reference
  originSessionId: 1d8541ba-e866-45c8-9b14-78daaa9bb7e0
  modified: 2026-09-25T14:21:41.762Z
---

Built 2026-09-25 on user request: `~/Desktop/thumb-generation/gen.py` (upscale / frame / render / upscale-setup).
Engine = copy of video-generator scripts + thumbnail-prompt `upscale_server.py` (SEEDVR_ROOT env, reuses server's
`~/thumbnail-prompt` SeedVR2 install). Server dir `~/thumb-generation`, config `remote.env` with `TG_` prefix, runs in
`youtube.slice`. Presets snow / snow-heavy / dust / still; `--from` direction per video. Not part of the repo's skills —
skill fixes to the engine are not synced automatically. Related: [[gpu-render-server]], [[upscale-lab]].

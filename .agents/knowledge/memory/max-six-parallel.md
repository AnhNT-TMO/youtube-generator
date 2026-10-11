---
name: max-six-parallel
description: "CEO 2026-09-30: never run more than 6 sub-agents / parallel workers at once on the Mac (machine hangs)"
metadata:
  node_type: memory
  type: feedback
  originSessionId: db13b1db-18f0-49d7-93de-aa79774fee47
  modified: 2026-09-30T06:48:41.458Z
---

Spawn at most 6 sub-agents at a time; parallel Chrome windows for ChatGPT (scene_images.py gen --parallel) stay ≤ 4, and do not add new agents while 6 are running.

**Why:** the CEO's Mac hangs with more (Chrome windows + agents share one machine).
**How to apply:** queue extra work and start it only when a running agent finishes; see [[christmas-scene-library]].

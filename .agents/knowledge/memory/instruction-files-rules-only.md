---
name: instruction-files-rules-only
description: "CLAUDE.md and channel guide files hold only general rules, never per-video results, view counts or status of specific uploads"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 5e042587-5ac7-490e-b123-327cc356d348
  modified: 2026-09-25T02:45:24.105Z
---

Instruction files (root CLAUDE.md, channel/<ch>/CLAUDE.md, publish.md, visual.md…) must contain only general, reusable rules and very common info. Do not write per-video status, view counts, dated incidents or "lessons from album 001" into them.

**Why:** they are loaded in every session, so specific data biases later work; the repo will serve many channels (owner 2026-09-25).

**How to apply:** turn a lesson into a short general rule (no numbers, no album names) in the matching channel file; put measured results and per-video history in data files (e.g. experiments/results.yaml, the album's own youtube.md / notes). Related: [[sourced-rules-over-invention]].

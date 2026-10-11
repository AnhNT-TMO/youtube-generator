---
name: muse-stuck-restart-now
description: "CEO 10-10: when a muse job hangs/refuses (e.g. reused-prompt reply), stop it and rerun at once with a changed prompt; never wait out 2×15-min timeouts"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 4d3ada23-1de2-4e13-8e31-27ff91f7fbc4
  modified: 2026-10-10T00:26:57.356Z
---

When a muse clip job is clearly not coming back (muse says it won't regenerate / serves an "existing delivery", or the thread shows no progress), stop that job right away and rerun it with a new prompt (e.g. flipped slide direction). Do not let the 15-min timeout fire twice.

**Why:** CEO 2026-10-10 — wizard pilot lost ~1 h waiting on stuck jobs; muse render itself is 2–6 min/clip.

**How to apply:** videos.py now sends muse "no-regeneration" replies straight to stuck; PM then resolves → needs_fix → requeue with a changed prompt immediately. See [[muse-clip-production]], [[resource-queue-workflow]].

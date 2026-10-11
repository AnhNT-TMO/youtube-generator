---
name: clip-camera-far-plan
description: "CEO 2026-10-04 muse clip camera rules: slide ≤35 %, zoom ≤1.2×, edge exits OK; the real target is \"not looking AI\" (objects popping in/out in frame); never static camera + post motion"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 29f4a079-0b21-4544-ae0c-464bb65417dc
  modified: 2026-10-04T02:22:21.347Z
---

CEO 2026-10-04 after watching sample clips at 11–40 % movement:
- Accept slide movement up to ~35 % of frame width (even 40 % looked OK to CEO), zoom up to ~1.2×. Main subject sliding out at the edge in the camera's direction is fine — don't be rigid about it.
- **What matters most: the clip must not look AI** — an object appearing, vanishing or changing shape inside the frame (e.g. a bush popping in/out). Reviewers must target this carefully (`morph`).
- Never use a locked/static camera with motion added in post (quality bad).
- Auto motion gate in `videos.py work` (`motion.py`, `video.motion_reject` / `zoom_reject` in the set's resource.json) enforces the numeric part.

**Why:** too-strict camera limits wasted most muse tries; AI artifacts are what viewers notice.
**How to apply:** review rules live in `image_source/VIDEO.md` (Duyệt); see [[resource-queue-workflow]], [[pm-owns-experiments]].

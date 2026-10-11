---
name: muse-clip-production
description: "CEO 2026-10-02 muse.ai clip run for image_source/ — slow camera + per-image motion, Sonnet workers per tab, Opus QCs and trims every clip; status file + worker.md"
metadata:
  node_type: memory
  type: project
  originSessionId: 4ca8a3eb-75bb-4a36-89c9-553d821974b6
  modified: 2026-10-02T08:14:13.429Z
---

CEO 2026-10-02: animate every `qc ok` image in image_source/ into a 10 s muse.ai clip saved as `<id>.mp4` next to `<id>.png` (source footage for long Christmas videos, see [[christmas-scene-library]]).

- CEO wants: barely moving slow camera + motion that fits each image, variety, animals OK outdoors (cows/hens on farms…); "ổn" quality is enough.
- Tooling since 2026-10-04: skill `video-resource-videos` (videos.py candidates/add/work/check/reconcile) via the shared resource queue, see [[resource-queue-workflow]]. Prompt + review rules live in `image_source/VIDEO.md`. Old `video-muse-generate` / muse_queue.py / worker.md are retired (tgz in production/_retired/).
- CEO rules from this run: cut the AI-looking start (≥ 1 s; ~2 s when added animals pop in); keep only the final clip — no raw originals, no rejected tries (disk); zero snow particles inside rooms (CEO saw indoor snow even in "faint specks OK" clips; old approved ones stay, new ones strict); if Muse keeps failing an indoor window scene, regenerate the image without falling snow and add GPU snow on the server (`window_snow.sh --track`, untested).
- CEO 2026-10-02: ≤ 3 Muse tabs per session (drop to 2 if "Delivery not confirmed" appears); a second PM session takes nature/travel/village.
- Status: `resq.py board` (old _muse_status.md moved to production/_retired/).

**Why:** footage library for 1-h videos; CEO judges by "không quá AI". **How to apply:** resume from `resq.py board`; reviewer runs `videos.py check` on every clip before verdict; trim only if ≥ 7 s remains (CEO 10-04), else redo.

CEO 2026-10-02 (camera): camera must move slowly but visibly; ~10–15 % faster than christmas-garden-03.mp4. A still camera = photo with snow → redo. Never prompt "locked tripod".

- 2026-10-09: muse remembers past jobs ("no-regeneration rule"): same still + byte-identical prompt → it replies "serving the existing delivery" but the new thread has NO video → job goes stuck again. Every retry of a stuck clip needs a changed prompt (e.g. flipped slide direction); `resolve --to regen` alone is useless. resolve does not use up an attempt.

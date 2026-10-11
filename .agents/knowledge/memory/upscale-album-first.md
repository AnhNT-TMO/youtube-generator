---
name: upscale-album-first
description: "CEO 10-06 — nightly upscale does the current album's cast first, then the album's 4K video renders, then the rest of the library"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 4168c5ca-072c-425d-850c-01a77092ff22
  modified: 2026-10-05T23:59:32.413Z
---

Every night: the current album's montage cast (clips.txt) is upscaled first, then that album's 4K video is rendered (with the master audio muxed), and only then does upscaling continue on the rest of the library.

**Why:** CEO 2026-10-06; the old run mixed album clips into length-grouped chunks with library clips, so album 002 was still missing 86/150 clips after a night.

**How to apply:** `upscale.py night --first production/montage/<album>/clips.txt` (tier 1, not capped by 200) + `montage.py render <album> --channel <ch> --audio <server master.wav>`. The render unit waits for all clips; the upscale runner yields to `montage-render` before tier 2. Related: [[upscale-lab]], [[shared-gpu-yield]].

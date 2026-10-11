---
name: cleanup-quarantine
description: "2026-10-07 cleanup moved retired/ACE files to quarantine folders (Mac ~/youtube-cleanup-20261007, server ~/cleanup-20261007) instead of deleting; CEO empties them"
metadata:
  node_type: memory
  type: project
  originSessionId: b19ed8dd-7a30-4f88-94c6-c291ae7ebe84
  modified: 2026-10-07T08:34:16.557Z
---

CEO 2026-10-07 asked to clean everything unused or ACE-Step related, keep what is needed or research history. Direct `rm` is blocked by the auto-mode classifier, so items were moved (same relative paths) to `/Users/tienanh/youtube-cleanup-20261007` (Mac, ~2.4 GB + ACE code/docs) and `~/cleanup-20261007` on the server (~39 GB: 002 old-audio final, tmp/test folders, _old renders, pip cache, ACE-only HF models).

**Why:** reversible; the CEO deletes the folders himself when sure.
**How to apply:** never read these folders for current work; restore a file from there only if something current turns out to need it. Later the same day (CEO: Mac = source of truth, server only executes) the 4K silent + audio videos of albums 001/002/004 also went to server quarantine (~186 GB total there; CEO had the whole server quarantine deleted 2026-10-07, so only the Mac quarantine remains) after album masters, montage.json/clips.txt/timeline.txt were put in `channel/<ch>/albums/<album>/` on the Mac. Kept on purpose: research history (tempo, popularity, PD list, VIBE_RESEARCH, upscale comparison, research/yt), `research/christmas-carols/work/` until the full re-render, WORKFLOW.json (config read by plan_io). See [[christmas-music-direction]], [[pd-tool-verification]].

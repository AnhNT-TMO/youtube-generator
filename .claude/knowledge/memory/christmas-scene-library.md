---
name: christmas-scene-library
description: "CEO 2026-09-30 image_source/ Christmas scene library (48 themes × 20 + cozy-loop 50): ChatGPT image → muse.ai 10 s clip → Claude assembles 1-h videos; parallel ChatGPT windows, mandatory Claude QC"
metadata:
  node_type: memory
  type: project
  originSessionId: db13b1db-18f0-49d7-93de-aa79774fee47
  modified: 2026-09-30T06:48:30.371Z
---

CEO 2026-09-30: build ~1000 ten-second Christmas clips for a Christmas channel (music = PD carols / instrumental, see [[christmas-instrumental-brainstorm]]). Flow: ChatGPT still image → muse.ai animates it with a prompt (friend's out-and-back camera formula, only as reference; CEO wants creativity) → Claude (not the CEO) picks and joins clips into ~1-hour videos by vibe. Each clip may play 2× in a row + transitions (≈190 clips per hour).

- Library at repo root `image_source/<family>/<theme>/` (families home, village, nature, magic, grand, travel, detail + `cozy-loop/living-room-fireplace` 50 static shots: fire + twinkling tree + steaming coffee + snow window, one scene per 1–2 h instrumental video). README per level; `shots.json` per theme; prompts composed from `image_source/blocks.json`. Media + `_threads.json` + `_gen.log` are gitignored.
- Tool since 2026-10-04: skill `video-resource-images` (images.py fill/add/work/reconcile) via the shared resource queue, see [[resource-queue-workflow]]; `image_source/resource.json` declares the set. Old scene_images.py / _threads.json retired. Note: the new flow opens one new chat per image job (hidden after download), which differs from the 10-02 one-chat-per-family rule below — reported to CEO 10-04.
- CEO allowed: parallel ChatGPT tabs; one chat per theme with many images; delete threads only at the end (`cleanup`).
- CEO rule: Claude must QC every image (criteria in image_source/README.md "Duyệt ảnh"); no spam of junk — only `qc ok` images go to muse.
- **ChatGPT Business plan image limit:** hit on 2026-09-30 14:13 after ~95 image requests in ~40 min (13:33–14:12), "resets in 23 hours". It is the shared company account, so the limit also blocks other users and the Stone thumbnails. ⇒ ~100 images/day via the UI; gen now stops all windows on the limit message. 1000 images ≈ 10 days, or another route (API) needs a CEO budget decision.
- CEO 2026-09-30: make ~100 first for the CEO to review before scaling (do not run all 1000). Keep 4 fixed windows, new chat per theme inside the same window (no window open/close churn).
- CEO 2026-10-02: **one ChatGPT chat per big family** (home, magic, nature…), not per theme/image — never close/reopen tabs to start new sessions (spams sessions). gen now keeps one chat per family, resumes it on errors and on later runs (redo). Split work as one Sonnet sub-agent = one window = one or two families; cozy-loop paused.
- CEO 2026-10-02: sub-agents only generate; Opus (main session) must look at every image itself and `qc redo` anything weak — no poor images kept.
- CEO 2026-10-02: from now on generate with BOTH ChatGPT accounts: account 1 Chrome port 9223 (~/.chatgpt-chrome/profile), account 2 Chrome port 9225 (~/.chatgpt-chrome-2/profile); `gen --port`, threads in _threads.json carry `port`, family chat resume is per account; total windows still ≤ 4.
- 2026-10-02 run: limit hit 12:37 after 168 images returned + ~46 failed requests since 10:34 (so the daily cap is not a fixed ~100; it varies). 146 new theme images passed Opus QC, 21 rejected (fake text on trains/signs/icing, people reflected in mirror baubles, snow inside greenhouses/windowless sills, tree touching chandelier, near-duplicates of an earlier ok shot). Fixes went into shots.json subjects. Sub-agents need Bash timeout 7200000 for gen (default 30 min kills it).
- 2026-10-02 afternoon (account 2): limit hit 15:19 after ~95 more images. Root cause of indoor 'floating sparkles/snow' rejects = the word 'gentle bokeh' in blocks.json `lights`; removed and replaced with 'the air is perfectly clear…' → indoor shots clean since. ChatGPT also drifts to Prague skylines (castle, St Vitus, Charles Bridge, Týn) in town themes and paints fake text on toy trains/signs/gingerbread icing/piano fallboards — subjects now say anonymous town / plain unlettered; QC must zoom floors, air, signs and skylines. Sub-agent gen runs need Bash timeout 7200000.
- Measured: first image in a chat ~2 min, later images in the same chat ~45–60 s; 3 windows in parallel worked with no limit hit (first test).

**Why:** CEO wants volume fast but usable. **How to apply:** keep running gen per theme in parallel, review every pending image before muse, record verdicts with `qc`.

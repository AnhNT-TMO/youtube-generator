---
name: pm-owns-length-and-pictures
description: "CEO 2026-09-26 — PM makes album length and picture calls alone: add pool songs until the master is long enough; ChatGPT 1 image/round, PM reviews every image and orders redraws"
metadata:
  node_type: memory
  type: feedback
  originSessionId: bf98b055-3b54-48b0-8e13-5ecb5b380d81
  modified: 2026-09-28T13:43:12.494Z
---

- Album too short for the channel's `album_rules.md` length window → the PM adds songs from the pool (or orders a Suno batch); no need to ask the CEO.
- ChatGPT returns 1 image per request; 1 image per round is fine. The PM looks at each image against the brief and the album's mood and orders another round if it doesn't fit; no fixed round cap.

**Why:** the CEO holds the PM accountable for each album's result; these are PM judgement calls, not CEO questions.
**How to apply:** workers return the image for review before `thumb.py fit`; `album.py check` shows the estimated length. Related: [[company-model]], [[pool-production-flow]].

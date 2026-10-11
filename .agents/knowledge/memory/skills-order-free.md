---
name: skills-order-free
description: "User wants the pipeline skills independent and runnable in batches / any order, not a strict sequence"
metadata:
  node_type: memory
  type: feedback
  originSessionId: bf98b055-3b54-48b0-8e13-5ecb5b380d81
  modified: 2026-09-28T13:43:08.894Z
---

User (2026-09-23, still valid after the 2026-09-28 refactor): the skills are deliberately independent and run in batches, in any order, in separate sessions.

**Why:** a skill that assumes the previous step just ran breaks batch work across sessions.

**How to apply:** skills talk only through files and must handle input made earlier / later / elsewhere. Lanes today: song pool (audio-suno-generate ∥ audio-song-naming, separate writers: manifest.json vs songs/*.md), album music (album.md → album.py build → audio-album-assembly), picture (thumbnail-prompt → video-generator loop), meeting at the full video, then upload-youtube-publish and video-shorts. Status view: `pm-production/scripts/album.py board --channel <ch>`. Related: [[pool-production-flow]], [[skills-own-their-code]]

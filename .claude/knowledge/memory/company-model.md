---
name: company-model
description: "Repo runs as a music company - CEO (owner), PM (pm-production, source of truth, spawns sub-agents and QCs them), groups R&D / Audio / Video / Upload; CEO and PM plan albums together"
metadata:
  node_type: memory
  type: project
  originSessionId: bf98b055-3b54-48b0-8e13-5ecb5b380d81
  modified: 2026-09-28T13:43:05.825Z
---

Owner (CEO) 2026-09-25, updated 2026-09-28: treat the project as a music production company. Root CLAUDE.md §0 has the roles.
- PM (`pm-production`) is the single source of truth and accountable for every video: discusses topics and albums with the CEO, picks songs, writes each album's brief in `album.md`, spawns sub-agents for the work and checks their output against the brief, reads results at 48 h / 7 d.
- Groups under the PM: R&D (`rnd-youtube-api`: YouTube API guide + phrase bank; the CEO does R&D with the PM), Audio (`audio-*`), Video (thumbnail-prompt, video-generator, video-shorts), Upload (`upload-*`).
- CEO decides: new channel, Suno prompt changes, channel contract, budget / Suno plan, process or skill changes beyond blockers; uploads, logins, `auth`. CEO judges the PM on two things: follows trend / CEO brief, views vs channel median at 48 h / 7 d. After a batch the PM proposes ≤ 5 process changes (value / effort / risk).

**Why:** the CEO wants to discuss and decide the creative direction with one accountable PM, and see only results and worthwhile proposals.
**How to apply:** any session asked about production answers as the PM; workers ask the PM, never the CEO. When the CEO asks for work, spawn sub-agents and QC them instead of doing everything in the main context. Related: [[pool-production-flow]], [[run-flow-before-improving]].

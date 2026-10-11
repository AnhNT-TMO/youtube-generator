---
name: run-flow-before-improving
description: User wants the full pipeline tried end-to-end for real (the next new album) before any more skill improvements; fix only blockers
metadata:
  node_type: memory
  type: feedback
  originSessionId: 0f90737b-4b21-432a-86ce-6caa811aede8
  modified: 2026-09-23T07:36:27.818Z
---

User (2026-09-23): "các skill analyze, plan chỉ cần đủ để hoạt động được là được, tôi muốn thử luồng trước đã rồi sẽ cải tiến sau". Stop polishing skills; get one new album through analyze → idea → plan → Suno → verify → assemble → video → publish for real, then improve from what actually breaks. (The first attempt, idea 001 / Album 002 "Psalms by Lamplight", was deleted on 2026-09-23 before any generation: the user restarted from scratch with the 6-criteria analyzer.)

**Why:** 15k lines of tooling were built in one day with no end-to-end run; they want evidence before more work ("tránh trường hợp cứ cải tiến liên tục mà còn chưa thử").

**How to apply:** when a skill has a flaw, fix it only if it blocks or corrupts the current run (wrong files, spent credits, lost lyrics, wrong numbers); otherwise note it for later and keep going. Don't propose refactors mid-run. Related: [[pool-production-flow]]

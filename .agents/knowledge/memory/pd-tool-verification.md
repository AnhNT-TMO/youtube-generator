---
name: pd-tool-verification
description: "2026-10-07 PD proof standard = independent scan transcription + pd_audit compare; Codex transcribes well only with PM-cropped system images attached via -i (95-100% calibrated); PM checks every difference"
metadata:
  node_type: memory
  type: project
  originSessionId: b19ed8dd-7a30-4f88-94c6-c291ae7ebe84
  modified: 2026-10-07T06:56:14.955Z
---

Since 2026-10-07 a Christmas melody counts as "PD-exact" only when someone transcribed a ≤1930 scan independently (without looking at our melody) into `pd-audit/_work/<slug>/print-<year>.abc`, ran `pd_audit.py compare`, and every remaining difference is on the allowed list (pd-audit.md) with pitch ≥ 96 % (or covered note for note by a second PD scan). Evidence (scan image, ABC, compare txt) stays in `_work/<slug>/` on the Mac for Content ID disputes. CEO 2026-10-07: the real folder is `pd-evidence/christmas-carols/` at the repo root (outside research, gitignored, never delete, no server/S3 backup); `pd-audit/_work` is a symlink to it.

**Why:** CEO steers the channel and claim disputes on this count; a wrong PASS is worse than a FAIL. Older "tool 100%" checks against Open Hymnal + eye-only scan checks were found to hide errors (auld, angels_we, jingle, evening_prayer).

**How to apply:** Codex workers that open scans themselves never see them (shell output is text only): they scored 22–38 % and fabricated "prints" from our melodies. With PM-cropped per-system images attached via `codex exec -i` (read-only, empty dir) Codex scored 95/98/100 % on sussex, gloucestershire_wassail, dou_viens_tu_bergere (2026-10-07); whole-page images read badly. Famous tunes may be recalled from memory, so the PM opens the scan at every difference and spot-checks PASSes of popular tunes. The earlier wave's files are all its files are quarantined in `_work/<slug>/NOT-EVIDENCE-*`, `NOT-INDEPENDENT-*`, `FABRICATED-*` (never compare against them). This morning's Codex results in `CODEX-RESULTS.md` are untrusted until Claude re-verifies. Codex may do non-visual parts (scan search/download, OMR jobs, exact melody fixes from audit `fix` text, tool runs), checked by machine; see [[codex-delegation]]. Melody batch for make_plan is the batch whose songs.json lists the slug (grep), not pdfix. Related: [[pd-audit-content-id]], [[unfamiliar-cap]].

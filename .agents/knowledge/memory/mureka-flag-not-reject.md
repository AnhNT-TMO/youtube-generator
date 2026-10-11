---
name: mureka-flag-not-reject
description: "CEO 10-09: Mureka takes failing checks (drums, voice, key, opening) are listed for CEO to listen, deleted only on CEO's word; later policy keep-one"
metadata:
  type: feedback
---

CEO 2026-10-09: during the Mureka trial nothing is auto-rejected. Every take flagged by mureka_pick.py (percussion, unrecognizable opening, key moved, any voice) is listed for the CEO to listen to, also when only one of v1/v2 is flagged. Delete (`mureka_web.py drop`) or rename an old `_choir` take to instrumental (`as-instrumental`) only when the CEO says.

**Why:** avoid wrong deletions wasting Gold while the checks are still being calibrated.

**How to apply:** report flagged takes with reasons, wait for CEO. Regenerate only when both versions are flagged and dropped. After several rounds without CEO corrections the policy becomes: drop the flagged version, keep the clean one, no regeneration. Rules live in MUREKA-ALBUM.json `takes` + SKILL.md. Related: [[mureka-voice-accent]], [[mureka-recognizable-opening]].

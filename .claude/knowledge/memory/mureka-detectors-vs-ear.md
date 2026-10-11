---
name: mureka-detectors-vs-ear
description: "CEO 10-09: Demucs guitar stem is unreliable (flag removed); the drum stem missed soft drums in Auld Lang Syne V9 v3; V9 not cleaner than V9.5; stem drum removal approved"
metadata:
  node_type: memory
  type: project
  originSessionId: 1556f934-3493-4c52-a3d7-924c1cf38192
  modified: 2026-10-09T14:32:13.364Z
---

On 2026-10-09 the CEO listened to the Auld Lang Syne takes (m019, model V9, prompt v5):
- **Guitar:** neither take has guitar, although the htdemucs_6s guitar stem measured 5–16 %. The guitar flag was removed; guitar is judged by ear only.
- **Drums:** both takes have drums.
  - v3 measured 0.01 % drums (4-stem) and 0.24 % (6-stem).
  - HPSS percussive share was 0.89 %, the same as the piano-only source (0.87 %).
  - Onset pulse also failed to separate it from the clean takes.
  - So the measurements cannot see this kind of soft drum. "Clean" from the tool does not mean clean to the ear.
- **V9:** drums in 2 of 2 takes, and the opening margin was lower (+10/+11 vs +16–41 on V9.5). V9 is not better.
- **Drum removal:** the CEO approved removing drums by summing every stem except drums. This only works when Demucs actually puts the drums in its drums stem.

**Why:** measurement errs both ways (false guitar, missed drums), so the CEO's ears stay the final gate.

**How to apply:** keep using the stem numbers as hints, but list takes for the CEO to listen to before an album. Don't claim a take is clean from the stems alone. Related: [[mureka-percussion-open]], [[mureka-flag-not-reject]], [[thin-piano-accompaniment]].

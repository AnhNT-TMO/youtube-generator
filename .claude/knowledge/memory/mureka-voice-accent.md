---
name: mureka-voice-accent
description: "CEO 10-09 (final): choir dropped from the Mureka flow — every style instrumental, any voice = flag; We Wish You = CEO exception"
metadata:
  type: project
---

CEO 2026-10-09 (later the same day) dropped the wordless choir "ahh/ooh" accent from the Mureka flow: every one of the three styles runs Instrumental on with no lyrics, and any voice found by mureka_stems.py is a flag like drums. Earlier that day the plan was a choir in 1 of 3 styles per song (MUREKA-VOICE.json, now marked retired). We Wish You a Merry Christmas stays allowlisted as a CEO exception (no ≤1930 print): max 1 per album, never track 1, never the Short.

**Why:** Mureka placed the choir unreliably (it skipped it with Instrumental on and drifted between passes with it off), and the CEO wants fewer parameters to control.

**How to apply:** don't re-add choir or lyrics to prompts or album rules unless the CEO asks. All 5 old `_choir` takes had voice and were dropped on the CEO's word (10-09); the as-instrumental command was removed. Related: [[mureka-album-rules]], [[mureka-flag-not-reject]], [[thin-piano-accompaniment]].

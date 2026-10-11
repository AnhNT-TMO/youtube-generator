---
name: pd-audit-content-id
description: "CEO 10-07 after a Content ID melody claim on album 002 (What Child Is This): every Christmas melody needs a PD-print audit; only clean songs go into albums"
metadata:
  node_type: memory
  type: project
  originSessionId: b19ed8dd-7a30-4f88-94c6-c291ae7ebe84
  modified: 2026-10-07T00:19:31.711Z
---

2026-10-07: album 002 (everstill) got a "Melody or lyrics" claim at 55:13 (What Child Is This / Greensleeves; LatinAutor, SonyATV, WCM, Songtrust). CEO disputed as public domain. CEO wants proof per song that notes come from a public-domain print (≤1930) and chords from PD harmony or our own — not a modern transcription — and expects many more claims.

**Why:** claims on PD carols will recur; a clean provenance makes disputes winnable and catches songs copied from modern sources.

**How to apply:** `pd_audit.py` in audio-christmas-workflow (compare/check/summary/dispute), audits in `research/christmas-carols/pd-audit/<slug>.json`, rules in `references/pd-audit.md`; album uses only `clean` songs; answer a claim with `pd_audit.py dispute <slug>`. Related: [[christmas-ambient-standard]].

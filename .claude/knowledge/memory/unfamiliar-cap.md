---
name: unfamiliar-cap
description: CEO 10-07: songs whose PD melody sounds unlike today's commonly sung version are tagged unfamiliar; max 2 per album
metadata:
  type: feedback
---

CEO 2026-10-07: "lạ tai" (unfamiliar by ear) is a separate tag from the PD verdict. A clean PD melody can differ from the version listeners know (often a later, still-copyrighted arrangement). Such songs are not bad, but an album holds at most 2 of them.

**Why:** listeners recognise the familiar version; too many odd-sounding carols hurt the album, a couple is fine.

**How to apply:** audit field `familiar` (familiar/unfamiliar/unchecked; unchecked counts as unfamiliar), checked by tool compare against ≥2 popular modern versions (reference only, never a source); VIBES.json `rounds.max_unfamiliar: 2`, enforced by ambient_keychain render/album. Prefer the ≤1930 print closest to the familiar version when transcribing. Related: [[pd-audit-content-id]].

CEO 2026-10-07 listened to the samples and approved jingle_bells and o_christmas_tree (PD-exact, unfamiliar) for normal use at any position: audit `familiar.approved` set, so they no longer count toward the cap. Other unfamiliar songs still follow the 2-per-album cap until the CEO approves them the same way.

---
name: christmas-ambient-standard
description: CEO 2026-10-06 ambient standard (option C): each carol in a familiar hymnal key, no key change inside a song, passes vary by timbre only; adjacent songs same key or one fifth apart; tier I then II
metadata:
  type: project
---

CEO 2026-10-06 chose "option C" after learning ambient principles: the old in-song lift (+2/+4 over 3 passes) was a climax device that contradicted ambient and caused key jumps between songs.

- Key per song: only keys listed in `research/christmas-carols/allowed_keys.json` (hymnary.org share ≥ 10 % with ≥ 20 printings; else printed keys; else source key). CEO: "chỉ dùng những key phổ biến mà mọi người hay nghe".
- Inside a song: one key for all 3 passes; variety by layers/octave double/density, 0/+0.5/+1 dB.
- Between songs: same key or one step on the circle of fifths; flow check (no loudness/brightness jolt) on the joined file.
- Order: tier I first (≥ 25 min), then I+II; tier III only to fill length.
- 3-hour album (CEO 10-06 approved for album 002): ~20 fitting songs rendered once, reshuffled rounds (`ambient_keychain.py render` → `rounds --target <video s>` → `album --target`), crossfade solved 1–4 s to match the montage video; rules in VIBES.json `rounds`. CEO said more songs are OK if needed.
- Spec: `research/christmas-carols/STANDARD.md`; tool `ambient_keychain.py`.

**Why:** CEO wants rules from external standards (music theory, hymnal data, research), not from his or Claude's ears.

**How to apply:** never reintroduce key lifts or melody-register shifting; grounding for any new rule must be cited. The earlier melody-register rule (VIBES.json `register`) is retired.

Related: [[ambient-even-passes]] [[one-vibe-per-album]] [[piano-channel-lead]] [[sourced-rules-over-invention]]

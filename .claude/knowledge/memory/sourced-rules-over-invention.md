---
name: sourced-rules-over-invention
description: "Owner prefers vetted, sourced guides + established practice (e.g. tempos famous recordings use) + our measurements over rules Claude invents"
metadata:
  node_type: memory
  type: feedback
  originSessionId: ae6ff78b-129f-4b73-be2d-d931f1f1565b
  modified: 2026-09-23T10:07:22.811Z
---

Owner (2026-09-23): a proven guide for writing Style/lyrics is "value hơn là để claude tự nghĩ". Chose the bitwize Suno docs (v6, cited sources, CC0) as the base; its useful rules were condensed into each channel's `channel/<ch>/rules.md` (§5–§9, each line tagged Suno / cộng đồng / đo) on 2026-09-23; `suno-rules.md` and the `suno-upstream/` copy were deleted at the owner's request to avoid two conflicting rule sources.

**Why:** the owner can't judge music by ear, so rules must come from somewhere checkable, not from Claude's taste.

**How to apply:** when writing Style/lyrics or proposing a new craft rule, cite where it comes from (Suno docs, tester reports, or our measurements) and label unverified tips as "try" to be tested via slot-1 variants. Measured channel data beats any guide. Related: [[user-developer-no-music-ear]] [[no-suno-behavior-assumptions]]

CEO 2026-09-30 (carols): "cứ dùng tầm BPM mà những người nổi tiếng đã dùng, không việc gì phải tự nghĩ ra dải BPM mới". My invented note-rate tempo bands made Jingle Bells ~half speed, so they were replaced by per-song tempos taken from well-known recordings, sheet-music markings and BPM databases (`research/christmas-carols/TEMPO_SPEC.md`, `tempo_refs/`). Whenever an established practice exists, follow it; invent only where nothing can be followed, and say so.

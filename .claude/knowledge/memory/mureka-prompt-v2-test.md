---
name: mureka-prompt-v2-test
description: "2026-10-09 PM test: short affirmative 'beatless lullaby' Mureka prompt (no meter/BPM) was not better than v1 (8 takes: 3 drums, 2 key moved, 1 clean) → reverted to v1"
metadata:
  node_type: memory
  type: project
  originSessionId: 1556f934-3493-4c52-a3d7-924c1cf38192
  modified: 2026-10-09T08:14:17.699Z
---

On 2026-10-09 the CEO asked the PM to research Mureka prompting and tighten the prompt. Findings:
- Official Mureka guide: keep prompts short, describe each instrument's role, and use only 1–3 negative lines.
- Remix is a "reinterpretation" that keeps the melodic contour, not the exact note order.
- CLAP-style text encoders barely tell "X" from "no X".

The PM tested a v2 template on m009–m012 (Away in a Manger s1 choir, Bleak Midwinter s2, O Little Town s1, Auld Lang Syne s2). v2 was about 450 characters, affirmative only, opened with "Beatless ambient piano lullaby", and dropped meter and BPM.

Result (8 takes):
- drums in 3 takes
- key moved in 2
- opening not recognizable in 2
- only 1 clean take

v1 had drums in 5 of 15 takes, so v2 is no better.

The prompt was reverted to v1 (`mureka_source.prompt_text`, PROMPT_VERSION v1). The drums show up mostly on the style-1 pad bed: Deck pad_celesta 4/4 takes, O Little Town pad_glockenspiel 2/2.

**Why:** the prompt is not the lever for drums or note order. Gold is better spent on selection.

**How to apply:** don't re-run prompt rewrites without a new hypothesis. A possible next test is a single targeted negation line in style 1, but that needs the CEO, because the no-exclusion rule is theirs. Related: [[mureka-percussion-open]], [[thin-piano-accompaniment]], [[mureka-flag-not-reject]].

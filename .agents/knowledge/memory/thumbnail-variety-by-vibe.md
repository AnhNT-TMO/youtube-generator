---
name: thumbnail-variety-by-vibe
description: "Thumbnails - amber lamp + singer's face are the default constants (experiments may drop them, 2026-09-25); agent picks wardrobe/framing/light/palette by the song's vibe; no anti-duplicate tooling"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 59ca5edb-cbaf-4828-953c-8cae5bbe7ead
  modified: 2026-09-24T01:48:55.734Z
---

Thumbnail images: only two constants — the amber lamp flame (brightest point) and the singer's face. Everything else
(framing e.g. face filling half the frame with blurred background, light, palette, weather, setting, wardrobe from 5
families: work / farm / traveler / sunday-or-choir-robe / biblical homespun) varies. Title lettering also varies per album (serif / brush / letterpress / bible / glow, owner 2026-09-24:
"tránh lạc quẻ"); only the small "Lamplight Gospel" line + gold rule stay fixed. Each album keeps lettering + a 2–3-axis
visual signature shared by its singles. Axes + English snippets live in `channel/<ch>/channel.md` → "Biến thể hình ảnh".

**Why:** owner (2026-09-24) saw that reading every old image to avoid repeats cannot scale to 100 albums + 200 singles, and
that images looked samey (all 8 were medium shots, blue palette, same fixed LOOK line). The many combinations already
prevent duplicates.

**How to apply:** choose axes from the song's lyrics/imagery/emotion and say why — never random, never a tool that picks
(owner explicitly rejected `suggest`/`similar` anti-duplicate tooling). Don't open all earlier images; `thumb.py list`
(text) is enough to see the previous album's signature. Since 2026-09-25 lamp + face are defaults only: a packaging
experiment may use e.g. a still life without a person (channel contract in `channel.md`). Related: [[pool-production-flow]].

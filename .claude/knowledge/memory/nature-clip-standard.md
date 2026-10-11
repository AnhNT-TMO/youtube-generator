---
name: nature-clip-standard
description: "CEO 2026-10-09 nature clip standard — real-looking + no AI look; natural motion OK, first≠last frame OK; mid/wide camera moves (Christmas range), close static + server move at montage"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 61a4b910-941b-4acb-8b67-c7421fcce26b
  modified: 2026-10-09T06:33:56.973Z
---

Nature resource clips (resource/nature): the bar is "đẹp, giống thật, không AI look, ghép vào ổn".

- Reject only AI look (objects appear/vanish/morph, landform changes), jumps/scene cuts, time-lapse-speed clouds, light flicker or time-of-day jump. Natural cloud/mist/light change is fine; first frame need not equal last.
- Album = clips joined by crossfade like slides; a clip may play several times per album and be mirrored to look different. Muse gives 10 s clips.
- Camera: CEO prefers moving camera (static 10 s felt monotonous). mid/wide = muse "almost still" slide/arc ("less than a tenth"; the "thirtieth" wording overshot 31/42), gate 2–35 % shift, zoom ≤ 1.2×; camera-far on almost-still → static + code move. Close = muse static (muse overshoots 40–137 % on close) + slow camera move added on the server at montage (CEO OK'd the test: push-in 1.00→1.08, after 1080p upscale). CEO 10-09: redo every old static mid/wide with a moving camera, don't save muse tokens (old static kept as `.static.mp4` fallback).

**Why:** CEO challenged my self-imposed "first frame = last frame / sky frozen" rule — it rejected natural clips and wasn't needed for crossfade montage.
**How to apply:** don't invent strict joinability rules; ask how the montage works before constraining clips. Related: [[clip-camera-far-plan]], [[beauty-over-flawless]].

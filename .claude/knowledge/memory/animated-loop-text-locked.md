---
name: animated-loop-text-locked
description: "CEO 2026-09-26: animated loops (Google Flow / Veo) must never change the thumbnail's lettering — video = thumbnail; prompt it + paste the 4K text back + check"
metadata:
  node_type: memory
  type: feedback
  originSessionId: c145d6e4-51c5-4945-9546-0e6ac89c5ea3
  modified: 2026-09-26T02:11:59.594Z
---

CEO is testing Google Flow (Veo 3.1, image-to-video, 8 s, 1280×720) to animate album thumbnails: lamp flame + ~1–2 other
moving things (album 004: coffee-mug steam; gentle motion of the man and rain on glass also accepted). Rule from the CEO:
**the lettering in the video must be identical to the thumbnail** (thumbnail must never differ from the video).

**Why:** first Flow test turned "LORD," into "LORD, IT" from 0.5 s on, and added a "Veo" watermark bottom-right; Veo's end
frame also did not match the start frame (seam diff 4.4 vs 0.22 per normal frame step).

**How to apply:** prompt Veo to keep the text area frozen, but never rely on the prompt alone — paste the right-third text
panel back from the 4K thumbnail.png (feathered edge on the window-frame column ≈ x 0.645–0.67 for album 004), check every
frame's text region against the thumbnail, crossfade the last 1.5 s into the first for the seam. Upscale 720p/1080p → 4K
with SeedVR2 (video model, already on the server for [[upscale-lab]]). `video.py loop` only takes stills today; a
"loop from Flow clip" mode is a new capability awaiting CEO approval (turn off `lantern` flicker when Veo animates the flame).

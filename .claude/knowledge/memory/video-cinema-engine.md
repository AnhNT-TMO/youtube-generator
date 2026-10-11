---
name: video-cinema-engine
description: video-generator "cinema" mode (2026-09-28, CEO-ordered): GPU 2.5D camera + lights + stars/dust/embers/bokeh/mist, per-video variant picker; first used by Shelter Stone Gospel
metadata:
  type: project
---

CEO 2026-09-28 ordered a varied video-effect engine for Shelter Stone Gospel (audience: US, 65+), allowed extending video-generator.
Built as `cinema` mode inside video-generator (scripts/cinema.py, depth.py, variants.py; docs in references/config.md → `cinema`), not Remotion/Three.js: keeps the seamless 5-min loop → extend → NVENC → S3 chain; Remotion needs a company licence.
Depth = Depth Anything V2 **Small** (Apache-2.0; Base/Large are CC-BY-NC, not usable commercially). 5-min 4K loop ≈ 139 s on the GPU server (8 parts).

**Why:** varied motion per video (756 combos from the channel's cinema_pool; `video.py variant` avoids the channel's last videos) against inauthentic-content look, calm for elderly viewers.
**How to apply:** per image set cinema.anchors (window/cross/head) + text_zones, then `variant`, `frame`, `loop`. Camera ~1 % frame at periods 4.5–9 s (not 40–75 s: too slow per CEO); title block ≥ 7 % from edges or cinema auto-shrinks the camera. Motion makes files big: cq 19 = 34 Mbps (1 h ≈ 15 GB) → Stone uses nvenc_cq 24 (~11–13 Mbps, 1 h ≈ 5–6 GB). CEO 2026-09-28: first pool was far too slow/faint; target motion speed = 1/2–2/3 of Mercy Harbor (their figure-8 2.5 s, zoom 4–9 %/2.5–5 s), clearly visible effects. Retuned pool measured on video: camera median 20 px/s, p90 33 px/s @1080p vs Harbor ~32/50 → ~0.65×. Logo (small, 100 px@1080) + subscribe overlays sit on the lettering side; video source has no logo, YouTube jpg gets it via scripts/thumb_logo.py. Not yet tested: `album` step (extend + real spectrum) on a cinema loop. Related: [[mercyharbor-clone-candidate]] [[gpu-first-resource-cap]] [[animated-loop-text-locked]]

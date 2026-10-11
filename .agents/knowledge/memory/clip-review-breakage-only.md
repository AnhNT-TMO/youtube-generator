---
name: clip-review-breakage-only
description: "CEO 10-10: muse clips judged only for breakage (0.5 s frame-pair check for AI pop-in/jumps) + correct motion; no zoom/camera-shift gates"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 4d3ada23-1de2-4e13-8e31-27ff91f7fbc4
  modified: 2026-10-10T00:42:36.296Z
---

Clip review = is the clip broken? Sample a frame every 0.5 s and compare consecutive pairs: anything popping in/out, jumping or changing shape/material (AI look) is a defect; objects entering from the edge due to camera motion are fine. Also check things move correctly (fire/smoke/snow natural, still things stay still, train runs). Do NOT measure or reject on zoom, camera shift, pull-back, or last frame ≠ first frame.

**Why:** CEO 2026-10-10 after the wizard pilot: muse's camera is basically fine; auto zoom/shift gates rejected clips the CEO found acceptable. Focus effort on good images + good prompts.

**How to apply:** wizard-christmas resource.json has no motion_reject/zoom_reject and no camera-far code; set CLAUDE.md "Luật clip" holds the rule. Supersedes the zoom/shift limits in [[clip-camera-far-plan]] for this set; ask before extending to other sets. `resq.py resolve --to review --output` can revive failed jobs after a rule change.

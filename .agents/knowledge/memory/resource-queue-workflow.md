---
name: resource-queue-workflow
description: "CEO 2026-10-04 resource queue (images/videos lanes) optimized for low tokens: generators = background `work` processes, image refill 60, reviewers Opus batches ≤12, image ok writes clip fields, videos.py draft composes clip prompts, PM wakes on resq.py watch"
metadata:
  node_type: memory
  type: project
  originSessionId: 29f4a079-0b21-4544-ae0c-464bb65417dc
  modified: 2026-10-04T01:07:57.563Z
---

CEO 2026-10-04: resource generation (ChatGPT stills, muse.ai clips) runs as a microservice-like queue, reusable for any set (new folder with `resource.json`; skills hold only workflow). CEO then asked to cut tokens without losing quality/diversity; decisions logged in `image_source/OPTIMIZATION.md`.

- Engine `pm-production/scripts/resq.py`, state dirs `production/resq/<images|videos>/`; doc `pm-production/references/resource-queue.md`. Skills `video-resource-images`, `video-resource-videos`; Codex copy via `.agents/sync-skills.sh`.
- Generators: PM runs `images.py work --refill <set> --target 60` and `videos.py work` as background Bash processes (4 h), logs in `production/resq/<lane>/work.log`. Agent `resource-generator` only where background runs are impossible.
- Reviewers: `resource-reviewer` (Opus) one batch ≤ 12 then exit; ≤ 1 per lane. Image ok must pass `--card '{"clip":…}'` (fields in `image_source/video_prompt.json`).
- Clip prompts: `videos.py draft <set> --limit 40` from clip fields + template, balanced camera moves; PM writes only fix prompts. Legacy images get clip fields via `videos.py clip` batches (~30).
- PM wakes via `resq.py watch --review 8 --needs-fix 5 --low videos=10` (REVIEW/FIX/LOW/STUCK/IDLE).
- Rules: max 3 attempts; trim only if ≥ 7 s remains; uncertain delivery → stuck, never resend. ChatGPT DOM has a hidden duplicate `<main>` — scope to visible.

**Why:** CEO wants regen and generation coordinated cheaply without babysitting. **How to apply:** follow resource-queue.md PM loop; see [[muse-clip-production]], [[christmas-scene-library]].

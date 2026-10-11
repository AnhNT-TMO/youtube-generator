---
name: server-guard
description: CEO 2026-09-28: every server job is watched by youtube-guard (kills abnormal RAM/CPU/GPU/temp/runtime jobs); ad-hoc server commands go through guard.sh run
metadata:
  type: feedback
---

CEO (after the server looked unhealthy during cinema renders): every action on the server must be supervised and an abnormal process killed immediately — a broken shared server is serious.
Built `production-manager/scripts/server_guard/` (now `pm-production/scripts/server_guard/`) (guard.py on the server at ~/youtube-guard, started by every runner's LIMIT prefix; guard.sh install/status/log/kills/run/test). Tested 2026-09-28: a 3 GB job with a 2 GB test threshold was killed in ~2–4 s.

**Why:** the GPU box is shared with other people; my earlier ad-hoc scripts once took 142 threads / the whole slice, and youtube.slice peaked at 81 GB.
**How to apply:** never ssh-run ad-hoc heavy scripts directly — use `guard.sh run '<cmd>'` (slice + guard + 24-core cap); check `guard.sh status` when starting a batch and `guard.sh kills` after any job dies; stop my jobs at once when the CEO says the server looks wrong. Related: [[gpu-first-resource-cap]] [[heavy-work-on-server]]

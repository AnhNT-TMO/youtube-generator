---
name: heavy-work-on-server
description: Music analysis / CPU-RAM-heavy scripts run only on the GPU server; Mac only if server unreachable AND user says yes
metadata:
  type: feedback
---

Every script that analyses music (Whisper, Demucs, beat tracking, whole-track tempo/loudness) or uses a lot of CPU/RAM
(album mix, video render) runs on the GPU server by default. Run it on the Mac (`--local`, `run.sh`) only when the server
cannot be reached AND the user agreed after being asked. New heavy scripts must get a server path from the start.
Parallel work = one batched command (e.g. `verify.py check --slot all`), not several subagents pushing/writing one album.
On the server, heavier-but-better options are welcome when they measurably help; don't add them when they don't
(2026-09-23: Whisper on the Demucs vocal stem was tested for first-lyric time and was WORSE, hallucinating words in the silent intro).

**Why:** (user, 2026-09-23) local runs heat the Mac and freeze other work; server resources are not a concern.
**How to apply:** default remote in verify.py / assemble.py / video.py (CLAUDE.md §3–§4); if ssh fails, stop and ask.
Related: [[gpu-render-server]] [[pool-production-flow]]

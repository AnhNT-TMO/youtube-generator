---
name: skills-own-their-code
description: Repo convention - each skill keeps its own code/venv/cache inside .claude/skills/<name>/; tools/ retired (only README)
metadata:
  type: feedback
---

User decided (2026-09-23) that code belongs to the skill that uses it: put scripts, venv and caches under `.claude/skills/<skill>/` (like youtube-music-analyzer, video-generator, verification-audio) instead of the shared `tools/` folder, which will be removed.

**Why:** the user wants each skill self-contained ("skill nào dùng gì thì tự thêm vào chỗ của nó"). **How to apply:** new tooling goes into the owning skill's `scripts/`; don't add to `tools/`. If another skill needs shared code, point at the owning skill's path (or copy a slim version, as album-assembly did with `measure/`) rather than recreating a shared folder. The compat symlinks in `tools/` were removed on 2026-09-23 (analyzer and suno-generate point at verification-audio directly); `tools/` holds only README.md. Related: [[pool-production-flow]]

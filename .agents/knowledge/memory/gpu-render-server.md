---
name: gpu-render-server
description: "User's LAN GPU server (192.168.100.131) approved for heavy video rendering AND audio analysis; access, specs, CUDA 12.8 driver limit, dirs used"
metadata:
  node_type: memory
  type: reference
  originSessionId: 9f7a12a4-976d-46f7-9d7e-4fa09e74478b
  modified: 2026-09-23T03:28:01.319Z
---

User's training server, which the user asked to use for rendering (2026-09-23): `ssh -i ~/.ssh/id_rsa nguyentienanh@192.168.100.131`.
Threadripper PRO 7965WX (24C/48T), 251GB RAM, RTX PRO 6000 Blackwell 96GB, Ubuntu, ffmpeg 6.1 with h264_nvenc, Python 3.12. /home disk ~83% full, so clean up big outputs.

- Skill `video-generator` (`.claude/skills/video-generator/scripts/video.py ... --remote`, host in its `remote.env`) renders there; state in `~/video-generator/` (scripts/, .venv/, repo/channel/*/image_source/, in/<job>/, out/<job>/).
- LAN transfer is only ~10–17 MB/s, so WAV upload (~870MB) takes ~80s. Transfers are a big share of the ~4 min round trip.
- zsh gotcha when scripting: `"$R:loop..."` triggers the `:l` modifier, so write `"${R}:..."`. macOS rsync 2.6.9 rejects multiple remote sources, so use scp one file at a time.

- Also used for all audio analysis. Mirror `~/youtube-qc/` (same layout as the repo): verification-audio (`verify.py check` → `scripts/remote.sh push/exec/pull`, venv `.claude/skills/verification-audio/.venv`, also used by youtube-music-analyzer) and album-assembly (`assemble.py plan/set/render/single` → its own `scripts/remote.sh`, own venv). Feature caches live on the server; verify pulls back only the small json cache. Album 002: 18 clips verified in 41 s.
- openai-whisper (CUDA) on the server gives more reliable first-lyric times than mlx-whisper on the Mac (Mac said 7.7 s where vocal-stem energy and server Whisper said ~35 s).
- NVIDIA driver only supports CUDA 12.8: default PyPI torch (CUDA 13) fails → install `torch==2.11.0+cu128 torchaudio==2.11.0+cu128` from download.pytorch.org/whl/cu128 (torchaudio needs `--reinstall-package`).

- `~/thumbnail-prompt/`: SeedVR2 7B upscaler for `thumb.py fit` (23 GB incl. venv + model), see [[upscale-lab]].

Related: [[suno-automation-constraints]] [[pool-production-flow]]
